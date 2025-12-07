# ========== Must load environment variables before all imports ==========
from pathlib import Path
from dotenv import load_dotenv
import os

# Only load .env file in development environment (local)
# In production environment (Vercel), should read from system environment variables
is_production = os.getenv("VERCEL") or os.getenv("ENVIRONMENT") == "production"
if not is_production:
    # Explicitly specify .env file path to ensure it can be found regardless of where it's started
    backend_dir = Path(__file__).parent.resolve()
    env_path = backend_dir / ".env"
    # Don't use override, prioritize system environment variables (Vercel environment variables)
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path), override=False)

# ========== Now can import other modules ==========
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
import os
import sys
import json
import platform
from typing import Optional, Union
from datetime import datetime
import stripe  # Import stripe for error handling

# Import existing modules - use absolute imports (backend as package)
from backend.vision import analyze_image
from backend.token_estimator import estimate_tokens_for_request
from openai import AsyncOpenAI

# Import authentication module
from backend.auth_supabase import (
    User, UserRegister, UserLogin, Token,
    register_user, login_user, get_current_active_user, verify_token
)

# Import new database modules
from backend.db_models import PlanType, PLAN_LIMITS, MODEL_PRICING
from backend.db_operations import (
    get_user_plan, get_user_quota, increment_user_quota, check_rate_limit, log_usage
)
from backend.payment_stripe import (
    create_checkout_session, handle_checkout_completed,
    handle_subscription_updated, handle_subscription_deleted,
    cancel_subscription, get_subscription_info
)

# ========== FastAPI App ==========

app = FastAPI(
    title="Desktop AI API",
    description="Desktop AI Backend Service - Your AI assistant for daily usage, interviews, and productivity",
    version="2.0.0"
)

# Add startup logs
@app.on_event("startup")
async def startup_event():
    import os
    is_vercel = os.getenv("VERCEL")
    is_desktop = getattr(sys, 'frozen', False)  # Detect if it's a packaged desktop version
    
    print("=" * 60)
    print("🚀 FastAPI application starting")
    if is_vercel:
        print(f"   Environment: Vercel (Cloud)")
        print(f"   ✅ All API Keys in cloud")
    elif is_desktop:
        print(f"   Environment: Desktop (Desktop version)")
        print(f"   ⚠️  Desktop mode: No configuration or API Keys included")
        print(f"   ✅ All API requests will be forwarded to Vercel (including auth, database, AI, payment)")
        vercel_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        print(f"   Cloud API: {vercel_url}")
        print(f"   ✅ Desktop version does not directly connect to Supabase or any external services")
    else:
        print(f"   Environment: Local (Local development)")
        print(f"   OPENAI_API_KEY configured: {bool(os.getenv('OPENAI_API_KEY'))}")
    print("=" * 60)

# Configure CORS
# Note: When allow_credentials=True, cannot use allow_origins=["*"]
# Must explicitly specify allowed origins, otherwise browser will reject cross-origin requests with cookies
# Electron apps may send requests without Origin header (file:// protocol or custom protocol)
origins = [
    "http://localhost:5173",      # Vite dev server
    "http://127.0.0.1:5173",     # Vite dev server (alternative)
    "https://www.desktopai.org", # Production web
    "http://localhost:3000",      # Alternative development port
    None,                         # Allow requests without Origin (Electron apps, file:// protocol)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # ⭐ Cannot use "*", must explicitly specify (None allows no Origin)
    allow_credentials=True,       # ⭐ Must be True to allow cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Static file service (Desktop version) ==========
# Only provide static file service in desktop mode

def find_ui_directory():
    """Find UI directory"""
    import sys
    possible_dirs = []
    
    # If it's a packaged exe, UI may be in multiple locations
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent.resolve()
        # 1. ui/ folder in same directory as exe
        possible_dirs.append(exe_dir / "ui")
        # 2. ui/ folder in parent directory (for release_root structure)
        parent_dir = exe_dir.parent.resolve()
        possible_dirs.append(parent_dir / "ui")
    else:
        # Development environment
        backend_dir = Path(__file__).parent.resolve()
        project_root = backend_dir.parent.resolve()
        possible_dirs.append(project_root / "dist")
        possible_dirs.append(project_root / "ui")
    
    for dir_path in possible_dirs:
        if dir_path.exists() and (dir_path / "index.html").exists():
            return dir_path
    return None

# Find and set UI directory
ui_directory = find_ui_directory()
if ui_directory:
    print(f"📁 Detected UI directory: {ui_directory}")
    
    # Mount static resources directory
    assets_dir = ui_directory / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        print(f"✅ Mounted static resources: /assets")
else:
    print("ℹ️  UI directory not detected, API service only")

# ========== Request/Response Models ==========

class ChatRequest(BaseModel):
    """Unified Chat request model"""
    user_input: Optional[str] = None  # Text input
    image_base64: Optional[Union[str, list[str]]] = None  # Image input (single or multiple)
    context: Optional[str] = None  # Conversation context
    prompt: Optional[str] = None  # Custom prompt (for image analysis)


class ChatResponse(BaseModel):
    """Unified Chat response model"""
    answer: str
    success: bool = True
    error: Optional[str] = None
    usage: Optional[dict] = None  # Token usage


class PlanResponse(BaseModel):
    """User Plan information"""
    plan: str
    weekly_token_limit: Optional[int] = None
    weekly_tokens_used: Optional[int] = None
    features: list[str]
    subscription_info: Optional[dict] = None


class ApiKeyRequest(BaseModel):
    """API Key request"""
    api_key: str
    provider: str = "openai"


class CheckoutRequest(BaseModel):
    """Create payment session request"""
    plan: str
    success_url: str
    cancel_url: str


# ========== Helper Functions ==========

async def get_api_client_for_user(user_id: str, plan: PlanType) -> tuple[AsyncOpenAI, str]:
    """Get corresponding OpenAI client and model based on user Plan
    
    Note: This function is only called in non-desktop environments (Vercel/local development)
    All desktop version requests will be directly forwarded to Vercel API, this function won't be called
    
    Returns:
        (AsyncOpenAI, model_name)
    """
    # All plans use server API Key
    server_api_key = os.getenv("OPENAI_API_KEY")
    if not server_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not configured. Please configure it in Vercel Dashboard -> Settings -> Environment Variables"
        )
    
    client = AsyncOpenAI(
        api_key=server_api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    
    # Select model based on plan
    # Start Plan: uses gpt-4o-mini
    # Normal Plan: uses gpt-4o-mini
    # High Plan: uses gpt-5-mini
    # Ultra Plan: uses gpt-4o
    if plan == PlanType.START:
        model = "gpt-4o-mini"  # Start Plan uses mini
    elif plan == PlanType.NORMAL:
        model = "gpt-4o-mini"  # Normal Plan uses mini
    elif plan == PlanType.HIGH:
        model = "gpt-5-mini"  # High Plan uses gpt-5-mini
    elif plan == PlanType.ULTRA:
        model = "gpt-4o"  # Ultra Plan uses gpt-4o
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported plan type: {plan}")
    
    return client, model


# ========== API Endpoints ==========

@app.get("/")
async def root():
    """Root path - health check or return UI"""
    # Try to find UI directory
    ui_dir = None
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent.resolve()
        ui_dir = exe_dir / "ui"
    else:
        backend_dir = Path(__file__).parent.resolve()
        project_root = backend_dir.parent.resolve()
        ui_dir = project_root / "ui"
    
    if ui_dir and (ui_dir / "index.html").exists():
        return FileResponse(str(ui_dir / "index.html"))
    else:
        # Otherwise return API information
        return {
            "status": "running",
            "message": "Desktop AI API v2.0",
            "version": "2.0.0"
        }


@app.get("/health")
@app.get("/api/health")  # Support both /health and /api/health
async def health_check():
    """Health check endpoint - includes environment variable status"""
    is_vercel = os.getenv("VERCEL")
    env_status = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
        "STRIPE_SECRET_KEY": bool(os.getenv("STRIPE_SECRET_KEY")),
        "STRIPE_WEBHOOK_SECRET": bool(os.getenv("STRIPE_WEBHOOK_SECRET"))
    }
    
    all_configured = all(env_status.values())
    
    return {
        "status": "healthy" if all_configured else "warning",
        "environment": "Vercel" if is_vercel else "Local",
        "message": "All environment variables configured" if all_configured else "Some environment variables are missing",
        "environment_variables": env_status,
        "ready": all_configured
    }


# ========== Authentication related API ==========

@app.post("/api/register", response_model=Token, tags=["Authentication"])
async def register(user_data: UserRegister, http_request: Request):
    """User registration"""
    # If desktop version, forward to Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/register",
                    json={"email": user_data.email, "password": user_data.password},
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Non-desktop version: normal processing
    return await register_user(user_data.email, user_data.password)


@app.post("/api/login", response_model=Token, tags=["Authentication"])
async def login(user_data: UserLogin, http_request: Request):
    """User login"""
    # If desktop version, forward to Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/login",
                    json={"email": user_data.email, "password": user_data.password},
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Non-desktop version: normal processing
    return await login_user(user_data.email, user_data.password)


@app.get("/api/config/supabase", tags=["Configuration"])
async def get_supabase_config():
    """Get Supabase configuration (for frontend OAuth use)"""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    
    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase configuration missing"
        )
    
    return {
        "supabase_url": supabase_url,
        "supabase_anon_key": supabase_anon_key
    }


def clean_url(s: str | None) -> str:
    """Clean URL: strip whitespace"""
    return (s or "").strip()

def require_clean_url(name: str, s: str | None) -> str:
    """Require clean URL: strip and validate no internal whitespace"""
    v = clean_url(s)
    if not v:
        return v
    # Critical: prohibit any internal whitespace (prevent multi-line/indentation)
    if v != v.strip() or "\n" in v or "\r" in v or "\t" in v:
        raise ValueError(f"{name} contains whitespace: {repr(s)}")
    return v

@app.get("/api/auth/google/url", tags=["Authentication"])
async def get_google_oauth_url_endpoint(
    redirect_to: Optional[str] = None, 
    platform: Optional[str] = None,
    http_request: Request = None
):
    """Get Google OAuth authorization URL"""
    from backend.auth_supabase import get_google_oauth_url
    from urllib.parse import urlparse
    
    # CRITICAL FIX: For desktop platform, always use Vercel backend callback URL
    # Desktop OAuth callback must go to Vercel backend, not localhost
    is_desktop_platform = platform == "desktop"
    
    if is_desktop_platform:
        # Force desktop platform to use Vercel backend callback URL
        vercel_base_url = require_clean_url("VERCEL_API_URL fallback", os.getenv("VERCEL_API_URL", "https://www.desktopai.org"))
        redirect_to = f"{vercel_base_url}/api/auth/callback?platform=desktop"
        print(f"🔐 Desktop platform detected: forcing redirect_to to Vercel backend: {redirect_to}")
    else:
        # Force normalization: clean all URL-related values for web platform
        try:
            # Clean FRONTEND_URL fallback
            frontend_url_fallback = require_clean_url("FRONTEND_URL fallback", "https://www.desktopai.org")
            
            # Clean redirect_to from request
            if redirect_to is not None:
                redirect_to = require_clean_url("redirect_to parameter", redirect_to)
                # Reverse validation: parse redirect_to origin
                u = urlparse(redirect_to)
                if u.scheme not in ("http", "https") or not u.netloc:
                    raise ValueError(f"Invalid redirect_to: {redirect_to}")
            
            # Clean FRONTEND_URL environment variable
            frontend_url_env = os.getenv("FRONTEND_URL")
            if frontend_url_env:
                frontend_url_env = require_clean_url("FRONTEND_URL env", frontend_url_env)
        except ValueError as e:
            print(f"❌ URL validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # If redirect_to is not provided, use request origin
        if not redirect_to and http_request:
            origin = http_request.headers.get("Origin") or http_request.headers.get("Referer", "").rsplit("/", 1)[0]
            redirect_to = origin if origin else None
            if redirect_to:
                redirect_to = require_clean_url("redirect_to from request", redirect_to)
    
    # If desktop version (local FastAPI), forward to Vercel
    is_desktop_local = getattr(sys, 'frozen', False)
    if is_desktop_local:
        import httpx
        vercel_api_url = require_clean_url("VERCEL_API_URL", os.getenv("VERCEL_API_URL", "https://www.desktopai.org"))
        async with httpx.AsyncClient() as http_client:
            try:
                params = {"platform": "desktop"}  # Always pass platform=desktop
                if redirect_to:
                    params["redirect_to"] = redirect_to
                response = await http_client.get(
                    f"{vercel_api_url}/api/auth/google/url",
                    params=params,
                    timeout=30.0
                )
                
                # Check response status before parsing JSON
                if response.status_code != 200:
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("detail", error_json.get("error", error_text))
                    except:
                        error_detail = error_text
                    
                    print(f"❌ Vercel API returned error: {response.status_code} - {error_detail}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Cloud API error: {error_detail}"
                    )
                
                data = response.json()
                # Verify returned data format
                if not isinstance(data, dict) or 'url' not in data:
                    raise HTTPException(
                        status_code=502, 
                        detail=f"Cloud API returned invalid format: {data}"
                    )
                return data
            except HTTPException:
                raise
            except httpx.HTTPStatusError as e:
                # Handle HTTP status errors (4xx, 5xx)
                error_text = e.response.text if hasattr(e.response, 'text') else str(e)
                try:
                    error_json = e.response.json()
                    error_detail = error_json.get("detail", error_json.get("error", error_text))
                except:
                    error_detail = error_text
                print(f"❌ Vercel API HTTP error: {e.response.status_code} - {error_detail}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Cloud API error: {error_detail}"
                )
            except httpx.HTTPError as e:
                print(f"❌ Unable to connect to Vercel API: {e}")
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Vercel backend processing: use the redirect_to we set above
    result = await get_google_oauth_url(redirect_to)
    
    # Also return Supabase configuration for frontend OAuth callback use
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    
    # NEW ARCHITECTURE: Only return URL, no code_verifier needed
    # Backend callback handles OAuth exchange with service key
    return {
        "url": result.get("url") if isinstance(result, dict) else result,
        "supabase_url": supabase_url,
        "supabase_anon_key": supabase_anon_key
    }


@app.get("/api/auth/callback", tags=["Authentication"])
async def oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, platform: Optional[str] = None):
    """
    Handle OAuth callback from Supabase
    Supports both Web browser (code in query) and Electron desktop app (tokens in hash)
    """
    # Read platform from query params (not from function signature default)
    platform = request.query_params.get("platform", platform)
    code = request.query_params.get("code", code)
    state = request.query_params.get("state", state)
    
    print(f"🔍 /api/auth/callback received request: platform={platform}, has_code={bool(code)}, has_state={bool(state)}")
    
    # CRITICAL FIX: For desktop platform, Supabase redirects with tokens in hash, not code in query
    # Return HTML that extracts tokens from hash and sends via postMessage
    if platform == "desktop":
        print(f"🔍 Desktop platform detected: returning HTML to extract tokens from hash")
        # Desktop callback HTML: extracts tokens from window.location.hash and sends via postMessage
        desktop_callback_html = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Desktop OAuth Callback</title>
  </head>
  <body>
    <script>
      (function () {
        // Extract tokens from hash (#access_token=...&refresh_token=...)
        const hash = window.location.hash || '';
        const search = window.location.search || '';
        
        // Parse hash parameters (format: #access_token=xxx&refresh_token=yyy&type=bearer&expires_in=...)
        const hashParams = {};
        if (hash.startsWith('#')) {
          const hashPart = hash.substring(1);
          hashPart.split('&').forEach(param => {
            const [key, value] = param.split('=');
            if (key && value) {
              hashParams[decodeURIComponent(key)] = decodeURIComponent(value);
            }
          });
        }
        
        // Parse search parameters (?platform=desktop&state=...)
        const searchParams = {};
        if (search.startsWith('?')) {
          const searchPart = search.substring(1);
          searchPart.split('&').forEach(param => {
            const [key, value] = param.split('=');
            if (key && value) {
              searchParams[decodeURIComponent(key)] = decodeURIComponent(value);
            }
          });
        }
        
        // Prepare message for Electron
        const message = {
          type: 'desktop-oauth-success',
          hash: hash,
          search: search,
          // Extract specific tokens if available
          access_token: hashParams.access_token || null,
          refresh_token: hashParams.refresh_token || null,
          token_type: hashParams.type || 'bearer',
          expires_in: hashParams.expires_in || null,
          provider_token: hashParams.provider_token || null,
          provider_refresh_token: hashParams.provider_refresh_token || null,
          // Include raw hash/search for fallback parsing
          _raw: {
            hash: hash,
            search: search
          }
        };
        
        console.log('🔐 Desktop OAuth callback: Extracted tokens from hash', {
          hasAccessToken: !!message.access_token,
          hasRefreshToken: !!message.refresh_token,
          hashLength: hash.length
        });
        
        // Send message to opener (Electron OAuth window's opener)
        try {
          if (window.opener) {
            window.opener.postMessage(message, '*');
            console.log('🔐 Desktop OAuth callback: Message sent to window.opener');
          } else if (window.parent && window.parent !== window) {
            window.parent.postMessage(message, '*');
            console.log('🔐 Desktop OAuth callback: Message sent to window.parent');
          } else {
            console.error('❌ Desktop OAuth callback: No window.opener or window.parent found');
            document.body.innerHTML = '<p>OAuth completed. You can close this window.</p>';
            return;
          }
        } catch (e) {
          console.error('❌ Desktop OAuth callback: postMessage error', e);
          document.body.innerHTML = '<p>Error sending OAuth data. You can close this window.</p>';
          return;
        }
        
        // Close window after a short delay (give Electron time to receive message)
        setTimeout(() => {
          window.close();
        }, 500);
      })();
    </script>
    <p>OAuth completed. You can close this window.</p>
  </body>
</html>
"""
        return HTMLResponse(content=desktop_callback_html)
    
    # If desktop version (local FastAPI), forward to Vercel
    is_desktop_local = getattr(sys, 'frozen', False)
    if is_desktop_local:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                params = {"platform": platform or "web"}
                if code:
                    params["code"] = code
                if state:
                    params["state"] = state
                response = await http_client.get(
                    f"{vercel_api_url}/api/auth/callback",
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                # Return HTML for Electron, or response content for web
                return HTMLResponse(content=response.text) if platform == "desktop" else response
            except httpx.HTTPError as e:
                print(f"❌ Desktop version forwarding failed: {e}")
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Web browser callback: requires code parameter for exchange
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code parameter. For desktop platform, use platform=desktop query parameter."
        )
    
    # Non-desktop version: normal processing with code exchange
    try:
        from supabase import create_client
        import os
        
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        
        if not supabase_url or not supabase_service_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase configuration missing: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set"
            )
        
        # Create Supabase client with SERVICE_ROLE_KEY (bypasses RLS and can exchange code)
        supabase = create_client(supabase_url, supabase_service_key)
        
        print(f"🔍 Exchanging OAuth code for session using service key: {code[:20]}...")
        
        # Use Supabase SDK to exchange code for session (works with service key, no PKCE needed)
        response = supabase.auth.exchange_code_for_session({
            "code": code
        })
        
        if not response or not response.session or not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth callback failed: Unable to get session or user information from Supabase"
            )
        
        user = response.user
        access_token = response.session.access_token
        refresh_token = response.session.refresh_token
        
        print(f"✅ OAuth callback successful, User ID: {user.id}, Email: {user.email}")
        
        # For Web browser: set cookie and redirect to success page
        frontend_url_env = os.getenv("FRONTEND_URL")
        frontend_url = require_clean_url("FRONTEND_URL env", frontend_url_env) if frontend_url_env else require_clean_url("FRONTEND_URL fallback", "https://www.desktopai.org")
        redirect_url = f"{frontend_url}/auth/success"
        
        # Create redirect response and set session cookie
        response_obj = RedirectResponse(url=redirect_url, status_code=302)
        
        # Set session cookie
        origin = request.headers.get("Origin", "") if request else ""
        is_localhost = "localhost" in origin or "127.0.0.1" in origin or not origin
        
        if is_localhost:
            # Development environment: don't set domain, allow localhost use
            response_obj.set_cookie(
                key="da_session",
                value=access_token,
                httponly=True,
                secure=False,  # Development environment may use http
                samesite="lax",  # localhost uses lax
                max_age=60 * 60 * 24 * 7,  # 7 days
                path="/",
            )
        else:
            # Production environment: set domain
            response_obj.set_cookie(
                key="da_session",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="none",
                domain=".desktopai.org",
                max_age=60 * 60 * 24 * 7,  # 7 days
                path="/",
            )
        
        print(f"✅ Session cookie set (origin: {origin}, is_localhost: {is_localhost}), redirecting to: {redirect_url}")
        
        return response_obj
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ OAuth callback error: {e}")
        print(f"❌ Error traceback:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback processing failed: {str(e)}"
        )
        
        # Debug logs
        print(f"🔍 OAuth callback response type: {type(response)}")
        
        if not response.user:
            print(f"❌ OAuth callback failed: response.user is empty")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth callback failed: Unable to get user information"
            )
        
        if not response.session:
            print(f"❌ OAuth callback failed: response.session is empty")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth callback failed: Unable to get session information"
            )
        
        # Return token information - use same method as login_user
        token = Token(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email
            }
        )
        
        return token
    except HTTPException:
        raise
    except AttributeError as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ OAuth callback attribute error: {e}")
        print(f"Error stack:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback processing failed: Response format incorrect - {str(e)}"
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ OAuth callback processing error: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error stack:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback processing failed: {str(e)}"
        )


@app.post("/api/auth/exchange-code", tags=["Authentication"])
async def exchange_oauth_code(request: Request):
    """
    LEGACY endpoint: Previously used for direct PKCE exchange.
    DEPRECATED: OAuth is now handled via /api/auth/callback with service key.
    This endpoint is kept for backward compatibility but returns 410 Gone.
    """
    print(f"⚠️ /api/auth/exchange-code: LEGACY endpoint called - this should not be used anymore")
    print(f"⚠️ OAuth is now handled via /api/auth/callback with service key")
    raise HTTPException(
        status_code=410,  # Gone - indicates the resource is no longer available
        detail="This endpoint is deprecated. OAuth is now handled via /api/auth/callback. Please update your client code."
    )
    
    # If desktop version, forward to Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                body = await request.json()
                print(f"🔐 /api/auth/exchange-code: Forwarding to Vercel (desktop version)")
                response = await http_client.post(
                    f"{vercel_api_url}/api/auth/exchange-code",
                    json=body,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                print(f"✅ /api/auth/exchange-code: Successfully exchanged code, user: {result.get('user', {}).get('email', 'N/A')}")
                return result
            except httpx.HTTPError as e:
                print(f"❌ /api/auth/exchange-code: Failed to forward to Vercel: {e}")
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Non-desktop version: normal processing
    try:
        body = await request.json()
        print(f"🔐 /api/auth/exchange-code: Received request body keys: {list(body.keys())}")
        print(f"🔐 /api/auth/exchange-code: Full request body (sanitized): {json.dumps({k: (v[:20] + '...' if isinstance(v, str) and len(v) > 20 else ('***' if k == 'code_verifier' and v else v)) for k, v in body.items()}, indent=2)}")
        
        code = body.get("code")
        state = body.get("state")  # Get state for flow_state_id (fallback only)
        code_verifier = body.get("code_verifier")  # REQUIRED for PKCE flow
        
        # Validate code
        if not code or not isinstance(code, str) or not code.strip():
            raise HTTPException(status_code=400, detail="Missing or invalid code parameter")
        
        # PRIORITY 1: Use code_verifier from request body (preferred - stateless approach)
        # This works in Vercel/serverless environments where memory storage doesn't persist
        # ✅ If code_verifier exists, use it directly without accessing flow_state dictionary
        if code_verifier and isinstance(code_verifier, str) and code_verifier.strip():
            code_verifier = code_verifier.strip()
            print(f"✅ /api/auth/exchange-code: Using code_verifier from request body (length: {len(code_verifier)})")
            print(f"✅ /api/auth/exchange-code: Skipping flow_state dictionary lookup (using provided code_verifier)")
        else:
            # PRIORITY 2: Fallback to memory storage (ONLY works in single-process environments)
            # Note: This will fail in Vercel/serverless as different requests may hit different instances
            # Only attempt this if code_verifier is truly missing
            print(f"⚠️ /api/auth/exchange-code: code_verifier not found in request body, attempting fallback...")
            if state:
                print(f"⚠️ /api/auth/exchange-code: Attempting fallback to memory storage (may fail in serverless)...")
                try:
                    # Decode state JWT to get flow_state_id
                    import base64
                    parts = state.split('.')
                    if len(parts) >= 2:
                        # Decode payload (second part)
                        payload_b64 = parts[1]
                        # Add padding if needed
                        payload_b64 += '=' * (4 - len(payload_b64) % 4)
                        payload_bytes = base64.urlsafe_b64decode(payload_b64)
                        payload = json.loads(payload_bytes)
                        flow_state_id = payload.get('flow_state_id')
                        if flow_state_id:
                            from backend.auth_supabase import _pkce_storage
                            stored_verifier = _pkce_storage.get(flow_state_id)
                            if stored_verifier:
                                code_verifier = stored_verifier
                                print(f"✅ Retrieved code_verifier from memory storage using flow_state_id: {flow_state_id[:20]}...")
                            else:
                                print(f"❌ No code_verifier found in memory storage for flow_state_id: {flow_state_id[:20]}...")
                                print(f"❌ This is expected in Vercel/serverless environments where requests may hit different instances")
                except Exception as e:
                    print(f"⚠️ Failed to extract flow_state_id from state: {e}")
        
        # Final validation: code_verifier is REQUIRED for PKCE flow
        if not code_verifier or not isinstance(code_verifier, str) or not code_verifier.strip():
            error_detail = {
                "code": "code_verifier_missing",
                "msg": "code_verifier is required for PKCE OAuth flow. Please ensure the client sends code_verifier in the request body.",
                "hint": "In Electron environment, code_verifier should be retrieved from localStorage and included in the exchange-code request."
            }
            print(f"❌ /api/auth/exchange-code: ERROR - code_verifier is missing or invalid!")
            print(f"❌ Error detail: {json.dumps(error_detail, indent=2)}")
            raise HTTPException(status_code=400, detail=error_detail)
        
        # Use Supabase Python SDK to exchange code for session
        # Note: OAuth exchange should use ANON_KEY, not SERVICE_ROLE_KEY
        import os
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        
        if not supabase_url or not supabase_anon_key:
            raise HTTPException(
                status_code=500,
                detail="Supabase configuration missing: SUPABASE_URL or SUPABASE_ANON_KEY not set"
            )
        
        # Create Supabase client with ANON_KEY for OAuth (not SERVICE_ROLE_KEY)
        supabase = create_client(supabase_url, supabase_anon_key)
        
        print(f"🔐 Exchanging OAuth code for session (code: {code[:20]}...)")
        if code_verifier:
            print(f"🔐 Using PKCE flow with code_verifier (length: {len(code_verifier)})")
        else:
            print(f"🔐 Using non-PKCE flow (no code_verifier)")
        
        # Exchange code for session
        # Note: Supabase Python SDK may have issues with PKCE, so we'll try direct REST API call
        if code_verifier:
            # Use PKCE flow - try direct REST API call instead of SDK
            import httpx
            print(f"🔐 Calling Supabase REST API directly for PKCE exchange")
            async with httpx.AsyncClient() as client:
                token_url = f"{supabase_url}/auth/v1/token?grant_type=pkce"
                
                # Validate code and code_verifier before sending (state is optional for now)
                if not code or not isinstance(code, str) or not code.strip():
                    raise HTTPException(status_code=400, detail=f"Invalid code: code is empty or not a string (type: {type(code)})")
                if not code_verifier or not isinstance(code_verifier, str) or not code_verifier.strip():
                    raise HTTPException(status_code=400, detail=f"Invalid code_verifier: code_verifier is empty or not a string (type: {type(code_verifier)})")
                
                # Strip whitespace to ensure clean values
                code = code.strip()
                code_verifier = code_verifier.strip()
                # State is kept for logging but not used in token request for now
                if state:
                    state = state.strip()
                
                print(f"🔐 Token URL: {token_url}")
                print(f"🔐 Code (after strip): {code[:20]}... (length: {len(code)}, type: {type(code)})")
                print(f"🔐 Code verifier (after strip): {code_verifier[:20]}... (length: {len(code_verifier)}, type: {type(code_verifier)})")
                if state:
                    print(f"🔐 State (after strip): {state[:50]}... (length: {len(state)}, type: {type(state)})")
                print(f"🔐 SUPABASE_URL: {supabase_url[:50]}...")
                print(f"🔐 SUPABASE_ANON_KEY: {'***' + supabase_anon_key[-10:] if supabase_anon_key else 'NOT SET'}")
                
                # Supabase PKCE token exchange requires "auth_code" parameter (not "code")
                # The grant_type=pkce endpoint expects "auth_code" in the JSON body
                # Start with minimal required fields: auth_code and code_verifier only
                # auth_flow_type and auth_flow_state may not be needed and could cause issues
                token_data = {
                    "auth_code": code,  # Supabase PKCE endpoint expects "auth_code" key
                    "code_verifier": code_verifier
                    # Removed auth_flow_type and auth_flow_state - test with minimal fields first
                }
                print(f"🔐 Token data keys: {list(token_data.keys())}")
                print(f"🔐 Request body (full JSON): {json.dumps(token_data, indent=2)}")
                # Preview with truncated values
                preview_data = {}
                for k, v in token_data.items():
                    if isinstance(v, str):
                        preview_data[k] = v[:20] + "..." if len(v) > 20 else v
                    else:
                        preview_data[k] = v
                print(f"🔐 Request body preview: {json.dumps(preview_data)}")
                
                # Supabase PKCE token exchange requires JSON format with "code" parameter
                # Log the actual request body that will be sent
                request_body_json = json.dumps(token_data)
                print(f"🔐 Request body JSON (that will be sent): {request_body_json}")
                print(f"🔐 Request body JSON length: {len(request_body_json)}")
                
                # CRITICAL: Include both apikey and Authorization headers (matching Supabase SDK behavior)
                # This ensures Supabase can properly identify the request and find the flow state
                request_headers = {
                    "apikey": supabase_anon_key,
                    "Authorization": f"Bearer {supabase_anon_key}",  # Required: matches Supabase SDK behavior
                    "Content-Type": "application/json"
                }
                print(f"🔐 Request headers (sanitized): apikey={'***' + supabase_anon_key[-10:] if supabase_anon_key else 'NOT SET'}, Authorization=Bearer ***{supabase_anon_key[-10:] if supabase_anon_key else 'NOT SET'}, Content-Type=application/json")
                
                token_response = await client.post(
                    token_url,
                    json=token_data,
                    headers=request_headers,
                    timeout=30.0
                )
                print(f"🔐 Supabase REST API response status: {token_response.status_code}")
                print(f"🔐 Supabase REST API response text: {token_response.text[:500]}")
                
                if token_response.status_code != 200:
                    error_text = token_response.text
                    print(f"❌ Supabase REST API error: {error_text}")
                    raise HTTPException(
                        status_code=token_response.status_code,
                        detail=f"Failed to exchange code: {error_text}"
                    )
                
                token_json = token_response.json()
                print(f"🔐 Supabase REST API response keys: {list(token_json.keys())}")
                
                # Convert REST API response to match SDK response format
                if "access_token" in token_json and "user" in token_json:
                    # Create a mock response object
                    class MockResponse:
                        def __init__(self, data):
                            self.session = type('Session', (), {
                                'access_token': data.get('access_token'),
                                'refresh_token': data.get('refresh_token'),
                                'expires_in': data.get('expires_in'),
                                'token_type': data.get('token_type', 'bearer')
                            })()
                            self.user = type('User', (), data.get('user', {}))()
                    
                    response = MockResponse(token_json)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid response from Supabase: missing access_token or user"
                    )
        else:
            # Try non-PKCE flow using SDK (may not work if OAuth URL was generated with PKCE)
            print(f"🔐 Using Supabase Python SDK for non-PKCE exchange")
            response = supabase.auth.exchange_code_for_session({
                "code": code
            })
        
        if not response or not response.session or not response.user:
            raise HTTPException(
                status_code=400,
                detail="Failed to exchange code for session: Invalid response from Supabase"
            )
        
        # Return token information
        token = Token(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            user={
                "id": response.user.id,
                "email": response.user.email or ""
            }
        )
        
        print(f"✅ Successfully exchanged code for session, user: {response.user.email}")
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Failed to exchange OAuth code: {e}")
        print(f"Error stack:\n{error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange OAuth code: {str(e)}"
        )


@app.post("/api/auth/set-session", tags=["Authentication"])
async def set_session(request: Request):
    """Set session cookie (called by frontend after OAuth callback)"""
    print(f"🔐 /api/auth/set-session: Received request")
    
    # If desktop version, forward to Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                body = await request.json()
                print(f"🔐 /api/auth/set-session: Forwarding to Vercel (desktop version)")
                response = await http_client.post(
                    f"{vercel_api_url}/api/auth/set-session",
                    json=body,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                print(f"✅ /api/auth/set-session: Successfully set session, user: {result.get('user', {}).get('email', 'N/A')}")
                return result
            except httpx.HTTPError as e:
                print(f"❌ /api/auth/set-session: Failed to forward to Vercel: {e}")
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Non-desktop version: normal processing
    try:
        # Get access_token from request body
        body = await request.json()
        access_token = body.get("access_token")
        if not access_token:
            print(f"❌ /api/auth/set-session: Missing access_token")
            raise HTTPException(status_code=400, detail="Missing access_token")
        
        print(f"🔐 /api/auth/set-session: Processing session setup (token length: {len(access_token)})")
        
        # Verify token
        from backend.auth_supabase import verify_token
        user = await verify_token(access_token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Create response and set cookie
        from fastapi.responses import JSONResponse
        response_obj = JSONResponse({"success": True, "user": {"id": user.id, "email": user.email}})
        
        # Determine cookie domain based on request origin
        origin = request.headers.get("Origin", "")
        user_agent = request.headers.get("User-Agent", "")
        is_electron = "Electron" in user_agent if user_agent else False
        is_localhost = "localhost" in origin or "127.0.0.1" in origin or not origin
        
        # For Electron apps, try to set cookie with both localhost and production settings
        # Electron apps may use file:// protocol, so we need to handle both cases
        if is_electron or not origin:
            # Electron app: try to set cookie without domain first (for file:// protocol)
            # Also set with domain for cross-domain requests
            print(f"🔐 Electron app detected, setting cookie with multiple configurations")
            
            # 1. Set cookie without domain (for file:// protocol compatibility)
            response_obj.set_cookie(
                key="da_session",
                value=access_token,
                httponly=True,
                secure=True,  # Use secure for HTTPS
                samesite="none",  # Allow cross-site requests
                max_age=60 * 60 * 24 * 7,  # 7 days
                path="/",
            )
            
            # 2. Also set with domain for production (in case Electron can use it)
            response_obj.set_cookie(
                key="da_session",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="none",
                domain=".desktopai.org",
                max_age=60 * 60 * 24 * 7,  # 7 days
                path="/",
            )
            
            print(f"✅ Session cookie set (Electron app), user: {user.email}")
        elif is_localhost:
            # Development environment: don't set domain, allow localhost use
            response_obj.set_cookie(
                key="da_session",
                value=access_token,
                httponly=True,
                secure=False,  # Development environment may use http
                samesite="lax",  # localhost uses lax
                max_age=60 * 60 * 24 * 7,  # 7 days
                path="/",
            )
            print(f"✅ Session cookie set (localhost), user: {user.email}")
        else:
            # Production environment: set domain
            response_obj.set_cookie(
                key="da_session",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="none",
                domain=".desktopai.org",
                max_age=60 * 60 * 24 * 7,  # 7 days
                path="/",
            )
            print(f"✅ Session cookie set (production), user: {user.email}")
        
        return response_obj
    except Exception as e:
        print(f"❌ Failed to set session cookie: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set session: {str(e)}")


@app.post("/api/auth/logout", tags=["Authentication"])
async def logout_endpoint(http_request: Request):
    """User logout, clear session cookie"""
    from fastapi.responses import JSONResponse
    
    # Create response
    response_obj = JSONResponse({"success": True, "message": "Logged out successfully"})
    
    # Determine cookie domain based on request origin
    origin = http_request.headers.get("Origin", "")
    is_localhost = "localhost" in origin or "127.0.0.1" in origin or not origin
    
    # Clear session cookie - try multiple ways to ensure clearing
    # 1. Clear cookie with domain (production environment)
    response_obj.set_cookie(
        key="da_session",
        value="",
        httponly=True,
        secure=True,
        samesite="none",
        domain=".desktopai.org",
        max_age=0,
        path="/",
    )
    
    # 2. Clear cookie without domain (development environment)
    response_obj.set_cookie(
        key="da_session",
        value="",
        httponly=True,
        secure=False,  # Development environment may use http
        samesite="lax",
        max_age=0,
        path="/",
    )
    
    print(f"✅ Session cookie cleared (origin: {origin}, is_localhost: {is_localhost})")
    return response_obj


@app.get("/api/me", response_model=User, tags=["Authentication"])
async def read_users_me(http_request: Request):
    """Get current user information"""
    # If desktop version, forward to Vercel (don't verify token, let Vercel verify)
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing authentication token")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.get(
                    f"{vercel_api_url}/api/me",
                    headers={"Authorization": auth_header},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Non-desktop version: normal processing
    # Prioritize getting session token from Cookie (set after OAuth login)
    session_token = http_request.cookies.get("da_session")
    
    # Log request details for debugging
    origin = http_request.headers.get("Origin", "")
    referer = http_request.headers.get("Referer", "")
    user_agent = http_request.headers.get("User-Agent", "")
    has_cookie = bool(session_token)
    auth_header = http_request.headers.get("Authorization", "")
    has_auth_header = bool(auth_header and auth_header.startswith("Bearer "))
    
    # Check if it's an Electron app request
    is_electron = "Electron" in user_agent if user_agent else False
    
    print(f"🔍 /api/me: Request details - Origin: {origin or 'N/A'}, Referer: {referer or 'N/A'}, User-Agent: {user_agent[:50] if user_agent else 'N/A'}...")
    print(f"🔍 /api/me: Authentication - Has Cookie: {has_cookie}, Has Auth Header: {has_auth_header}, Is Electron: {is_electron}")
    
    # For Electron apps, if no Origin, that's normal (file:// protocol)
    if not origin and is_electron:
        print(f"ℹ️  /api/me: Electron app request without Origin header (normal for file:// protocol)")
    
    if session_token:
        # Use token in session cookie to verify user
        print(f"🔍 /api/me: Getting session token from Cookie (length: {len(session_token)})")
        try:
            # Use Supabase to verify token
            from backend.auth_supabase import verify_token
            user = await verify_token(session_token)
            if user:
                print(f"✅ /api/me: Cookie session verification successful, user: {user.email}")
                return user
        except Exception as e:
            print(f"❌ /api/me: Cookie session verification failed: {e}")
            import traceback
            print(f"❌ /api/me: Error traceback:\n{traceback.format_exc()}")
            # Cookie invalid, continue trying Authorization header
    
    # If no Cookie or Cookie invalid, try getting token from Authorization header
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        print(f"🔍 /api/me: Getting token from Authorization header (length: {len(token)})")
        try:
            from backend.auth_supabase import verify_token
            user = await verify_token(token)
            if user:
                print(f"✅ /api/me: Authorization header verification successful, user: {user.email}")
                return user
        except Exception as e:
            print(f"❌ /api/me: Authorization header verification failed: {e}")
            import traceback
            print(f"❌ /api/me: Error traceback:\n{traceback.format_exc()}")
    
    # Neither available, return 401
    print(f"❌ /api/me: No valid authentication found - Cookie: {has_cookie}, Auth Header: {has_auth_header}")
    raise HTTPException(status_code=401, detail="Unauthenticated: Missing valid session cookie or Authorization token")


# ========== User Plan related API ==========

@app.get("/api/plan", response_model=PlanResponse, tags=["Plan Management"])
async def get_plan(http_request: Request):
    """Get user current Plan information"""
    # If desktop version, forward to Vercel (don't verify token, let Vercel verify)
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing authentication token")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.get(
                    f"{vercel_api_url}/api/plan",
                    headers={"Authorization": auth_header},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Non-desktop version: normal processing (need to verify token)
    auth_header = http_request.headers.get("Authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    token = auth_header.replace("Bearer ", "")
    current_user = await verify_token(token)
    user_plan = await get_user_plan(current_user.id)
    quota = await get_user_quota(current_user.id)
    
    # Ensure plan field exists
    if not user_plan or not user_plan.plan:
        # If plan doesn't exist, use default NORMAL plan
        print(f"⚠️ User {current_user.id} plan is empty, using default NORMAL plan")
        user_plan.plan = PlanType.NORMAL
    
    limits = PLAN_LIMITS[user_plan.plan]
    
    # Get subscription information
    # Get subscription info for all plans (both NORMAL and HIGH have subscriptions)
    # Start plan has no subscription info (one-time purchase)
    subscription_info = None
    if user_plan.plan != PlanType.START:
        subscription_info = await get_subscription_info(current_user.id)
    
    # Support weekly quota and lifetime quota
    weekly_token_limit = limits.get("weekly_token_limit")
    lifetime_token_limit = limits.get("lifetime_token_limit")
    is_lifetime = limits.get("is_lifetime", False)
    
    # For start plan, use lifetime_token_limit as token_limit
    if is_lifetime and lifetime_token_limit is not None:
        weekly_token_limit = lifetime_token_limit
    
    weekly_tokens_used = getattr(quota, 'weekly_tokens_used', 0)
    
    return PlanResponse(
        plan=user_plan.plan.value,
        weekly_token_limit=weekly_token_limit,
        weekly_tokens_used=weekly_tokens_used,
        features=limits["features"],
        subscription_info=subscription_info
    )


@app.post("/api/plan/checkout", tags=["Plan Management"])
async def create_checkout(
    request: CheckoutRequest,
    http_request: Request
):
    """Create Stripe payment session"""
    # If desktop version, forward to Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing authentication token")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/plan/checkout",
                    json={
                        "plan": request.plan,
                        "success_url": request.success_url,
                        "cancel_url": request.cancel_url
                    },
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Non-desktop version: normal processing
    try:
        # Verify token and get user information
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authentication token")
        
        token = auth_header.replace("Bearer ", "")
        current_user = await verify_token(token)
        
        # Create payment session
        plan = PlanType(request.plan)
        
        # Start plan is one-time purchase, doesn't need Stripe subscription
        # Temporarily directly update user plan (can add one-time payment logic later)
        if plan == PlanType.START:
            from backend.db_operations import update_user_plan
            await update_user_plan(current_user.id, plan=plan)
            return {
                "checkout_url": request.success_url,
                "message": "Start plan activated"
            }
        
        # Normal and High plan need Stripe subscription
        checkout_data = await create_checkout_session(
            user_id=current_user.id,
            plan=plan,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            user_email=current_user.email  # Pass user email
        )
        
        return checkout_data
    except ValueError as e:
        # Configuration error, return 400
        print(f"❌ Checkout configuration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except AttributeError as e:
        # AttributeError is usually None.data error
        error_msg = f"Data access error: {str(e)}"
        print(f"❌ Checkout AttributeError: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)
    except stripe.error.StripeError as e:
        # Stripe API error
        error_msg = f"Stripe API error: {e.user_message if hasattr(e, 'user_message') else str(e)}"
        print(f"❌ Stripe API error: {e}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        # Other errors
        error_msg = f"Failed to create payment session: {str(e)}"
        print(f"❌ Checkout error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/api/plan/cancel", tags=["Plan Management"])
async def cancel_plan(http_request: Request):
    """Cancel current subscription"""
    # If desktop version, forward to Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing authentication token")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/plan/cancel",
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Unable to connect to cloud API: {str(e)}")
    
    # Non-desktop version: normal processing (need to verify token)
    auth_header = http_request.headers.get("Authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    token = auth_header.replace("Bearer ", "")
    current_user = await verify_token(token)
    success = await cancel_subscription(current_user.id)
    
    if success:
        return {"message": "Subscription will be cancelled at the end of current period"}
    else:
        raise HTTPException(status_code=400, detail="Failed to cancel subscription")


# ========== API Key management removed ==========
# All users use server API Key


# ========== Unified Chat API (Core interface) ==========

@app.post("/api/chat", response_model=ChatResponse, tags=["AI Features"])
async def chat(
    request: ChatRequest,
    http_request: Request
):
    """Unified Chat interface - supports text conversation and image analysis
    
    - If image_base64 exists: perform image analysis
    - If only user_input: perform text conversation
    - Automatically select corresponding API Key and model based on user Plan
    - Automatically perform rate limiting check
    - Automatically record usage statistics
    """
    # If desktop version, directly forward to Vercel (don't verify token, let Vercel verify)
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing authentication token, unable to forward request to cloud")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/chat",
                    json={
                        "user_input": request.user_input,
                        "image_base64": request.image_base64,
                        "context": request.context,
                        "prompt": request.prompt
                    },
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"Unable to connect to cloud API: {str(e)}"
                )
    
    # Non-desktop version: normal processing (need to verify token)
    try:
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authentication token")
        
        token = auth_header.replace("Bearer ", "")
        current_user = await verify_token(token)
        
        # 1. Get user Plan
        user_plan = await get_user_plan(current_user.id)
        
        # 2. Estimate tokens that will be used for this request
        estimated_tokens = estimate_tokens_for_request(
            user_input=request.user_input,
            context=request.context,
            prompt=request.prompt,
            images=request.image_base64 if isinstance(request.image_base64, list) else [request.image_base64] if request.image_base64 else None,
            max_output_tokens=3000 if request.image_base64 else 2000
        )
        
        # 3. Check rate limit (including token quota)
        allowed, error_msg = await check_rate_limit(current_user.id, estimated_tokens=estimated_tokens)
        if not allowed:
            raise HTTPException(status_code=429, detail=error_msg)
        
        # 4. Get corresponding API client and model
        client, model = await get_api_client_for_user(current_user.id, user_plan.plan)
        
        # 5. Process request
        if request.image_base64:
            # Image analysis
            print(f"🖼️ User {current_user.id} ({user_plan.plan.value}) requesting image analysis")
            
            answer, token_usage = await analyze_image(
                image_base64=request.image_base64,
                prompt=request.prompt,
                client=client,
                model=model
            )
            
            # Use actual token usage
            estimated_input_tokens = token_usage["input_tokens"]
            estimated_output_tokens = token_usage["output_tokens"]
            
        elif request.user_input:
            # Text conversation
            print(f"💬 User {current_user.id} ({user_plan.plan.value}) requesting text conversation")
            
            messages = []
            
            # Add system prompt
            messages.append({
                "role": "system",
                "content": """You are a professional technical interview assistant. Your tasks are:
1. Answer technical questions, provide clear explanations and code examples
2. Help users understand interview problem-solving approaches
3. Provide best practices and optimization suggestions
4. Maintain concise, professional response style

Please answer in Chinese, code defaults to Python."""
            })
            
            # Add context (if exists)
            if request.context:
                messages.append({
                    "role": "system",
                    "content": f"The following is previous conversation history:\n\n{request.context}"
                })
            
            # Add user input
            messages.append({
                "role": "user",
                "content": request.user_input
            })
            
            # Call LLM
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            # Get actual token usage
            estimated_input_tokens = response.usage.prompt_tokens
            estimated_output_tokens = response.usage.completion_tokens
            
        else:
            raise HTTPException(
                status_code=400,
                detail="Please provide user_input (text) or image_base64 (image)"
            )
        
        # 6. Calculate total token usage (use actual values returned by OpenAI)
        total_tokens = estimated_input_tokens + estimated_output_tokens
        
        # 7. Increment quota count (allow slight overage, clamp to limit)
        # Once OpenAI returns success, must return result to user and deduct tokens
        limits = PLAN_LIMITS[user_plan.plan]
        weekly_token_limit = limits.get("weekly_token_limit")
        lifetime_token_limit = limits.get("lifetime_token_limit")
        is_lifetime = limits.get("is_lifetime", False)
        
        # For lifetime quota, use lifetime_token_limit
        if is_lifetime and lifetime_token_limit is not None:
            weekly_token_limit = lifetime_token_limit
        
        # Get current quota, calculate billable tokens (clamp to remaining quota)
        quota_before = await get_user_quota(current_user.id)
        current_tokens_used = getattr(quota_before, 'weekly_tokens_used', 0)
        
        if weekly_token_limit is not None and weekly_token_limit > 0:
            remaining_quota = weekly_token_limit - current_tokens_used
            # Clamp: if exceeds remaining quota, only deduct remaining quota portion
            billable_tokens = min(total_tokens, max(0, remaining_quota))
        else:
            billable_tokens = total_tokens
        
        # 8. Record usage log (use actual tokens, success=True)
        await log_usage(
            user_id=current_user.id,
            plan=user_plan.plan,
            api_endpoint="/api/chat",
            model_used=model,
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
            success=True
        )
        
        # 9. Increment quota count (use billable tokens)
        await increment_user_quota(current_user.id, tokens_used=billable_tokens)
        
        # 10. Always return result to user (even if slightly over quota)
        return ChatResponse(
            answer=answer,
            success=True,
            usage={
                "input_tokens": estimated_input_tokens,
                "output_tokens": estimated_output_tokens,
                "total_tokens": total_tokens,
                "model": model
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        print(f"❌ Chat API failed: {error_message}")
        
        # Record failure log
        try:
            user_plan = await get_user_plan(current_user.id)
            await log_usage(
                user_id=current_user.id,
                plan=user_plan.plan,
                api_endpoint="/api/chat",
                model_used="unknown",
                success=False,
                error_message=error_message
            )
        except:
            pass
        
        return ChatResponse(
            answer=f"Processing failed: {error_message}",
            success=False,
            error=error_message
        )


# ========== Stripe Webhook ==========

@app.get("/api/webhooks/stripe", tags=["Webhooks"])
async def stripe_webhook_get():
    """Webhook endpoint health check (for testing)"""
    # Check necessary environment variables
    env_status = {
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
        "STRIPE_WEBHOOK_SECRET": bool(os.getenv("STRIPE_WEBHOOK_SECRET"))
    }
    
    all_configured = all(env_status.values())
    
    return {
        "status": "ok" if all_configured else "warning",
        "message": "Stripe Webhook endpoint is active. Use POST method for actual webhook events." if all_configured else "Endpoint is active but some environment variables are missing.",
        "endpoint": "/api/webhooks/stripe",
        "methods": ["POST", "GET"],
        "environment_variables": env_status,
        "ready": all_configured
    }

@app.post("/api/webhooks/stripe", tags=["Webhooks"])
async def stripe_webhook(request: Request):
    """Stripe Webhook Handler with signature verification and database updates"""
    
    body = await request.body()
    event_type = "unknown"
    event_id = "unknown"
    
    try:
        # Step 1: Get signature (body already retrieved above)
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            error_msg = "Missing stripe-signature header"
            print(f"ERROR: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Step 2: Get webhook secret from environment
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        if not webhook_secret:
            error_msg = "STRIPE_WEBHOOK_SECRET not configured"
            print(f"ERROR: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Step 3: Verify Stripe signature
        try:
            event = stripe.Webhook.construct_event(
                body, sig_header, webhook_secret
            )
        except ValueError as e:
            error_msg = f"Invalid payload: {str(e)}"
            print(f"ERROR: Webhook signature verification failed - {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        except stripe.error.SignatureVerificationError as e:
            error_msg = f"Invalid signature: {str(e)}"
            print(f"ERROR: Webhook signature verification failed - {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Step 4: Extract event info
        event_type = event.get("type", "unknown")
        event_id = event.get("id", "unknown")
        
        print(f"Received webhook event: {event_type} [id: {event_id}]")
        
        # Step 5: Handle different event types
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            await handle_checkout_completed(session)
            print(f"Successfully processed {event_type} [id: {event_id}]")
            
        elif event_type == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await handle_subscription_updated(subscription)
            print(f"Successfully processed {event_type} [id: {event_id}]")
            
        elif event_type == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await handle_subscription_deleted(subscription)
            print(f"Successfully processed {event_type} [id: {event_id}]")
            
        else:
            # Log unhandled events but return success (Stripe expects 200 for all received events)
            print(f"Unhandled event type: {event_type} [id: {event_id}] - returning success")
        
        # Step 6: Return success response
        return {
            "status": "success",
            "event_type": event_type,
            "event_id": event_id
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        # Catch all other exceptions and return 500 with details
        error_msg = f"Error processing webhook event {event_type} [id: {event_id}]: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


# ========== Backward compatible APIs (gradually deprecated) ==========

@app.post("/api/vision_query", tags=["Deprecated - Please use /api/chat"])
async def vision_query_legacy(
    request: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Old image analysis interface (backward compatible)"""
    chat_request = ChatRequest(
        image_base64=request.get("image_base64"),
        prompt=request.get("prompt", "")
    )
    return await chat(chat_request, current_user)


@app.post("/api/text_chat", tags=["Deprecated - Please use /api/chat"])
async def text_chat_legacy(
    request: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Old text conversation interface (backward compatible)"""
    chat_request = ChatRequest(
        user_input=request.get("user_input"),
        context=request.get("context", "")
    )
    return await chat(chat_request, current_user)


# ========== SPA route support (must be defined last, as catch-all) ==========
# Only add SPA routes when UI directory is detected
if ui_directory:
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Provide SPA route support"""
        # Exclude API and documentation paths
        if (full_path.startswith("api/") or 
            full_path in ["docs", "redoc", "openapi.json"]):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Return index.html
        index_path = ui_directory / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="UI not found")


# ========== Start service ==========

if __name__ == "__main__":
    # If running directly (not via uvicorn backend.main:app), need to handle import paths
    import sys
    from pathlib import Path
    
    # Get absolute path of backend directory and add to sys.path
    backend_dir = Path(__file__).parent.resolve()
    project_root = backend_dir.parent.resolve()
    
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print("Desktop AI Backend Service v2.0")
    print("=" * 60)
    print(f"Service URL: http://{host}:{port}")
    print(f"API Docs: http://{host}:{port}/docs")
    print(f"Health Check: http://{host}:{port}/health")
    print("=" * 60)
    print("Features:")
    print("  - Unified /api/chat endpoint")
    print("  - Plan subscription management")
    print("  - Usage statistics and rate limiting")
    print("  - Stripe payment integration")
    print("=" * 60)
    print("Tip: Use 'uvicorn backend.main:app --port 8000' from project root")
    print("=" * 60)
    
    uvicorn.run(
        app,  # Directly pass app object, not string (PyInstaller packaged version cannot use string import)
        host=host,
        port=port,
        reload=False,  # Temporarily disable reload when running directly, avoid path issues
        log_level="info"
    )
