"""
Supabase authentication module
Provides user login, registration, token verification and other functions
"""
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from backend.db_supabase import get_supabase
import base64
import json

# HTTP Bearer token
security = HTTPBearer()

# In-memory storage for PKCE code_verifier (keyed by flow_state_id)
# In production, use Redis or database instead
_pkce_storage: dict[str, str] = {}


class UserRegister(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class User(BaseModel):
    id: str
    email: str
    created_at: Optional[str] = None


# ========== Authentication functions ==========

async def register_user(email: str, password: str) -> Token:
    """Register new user"""
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed: No user returned"
            )
        
        # Check if session exists (may be None if email confirmation is required)
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration successful, but email verification is required. Please check your email to verify your account before logging in."
            )
        
        return Token(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


async def login_user(email: str, password: str) -> Token:
    """User login"""
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email or password incorrect"
            )
        
        return Token(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )


async def verify_token(token: str) -> User:
    """Verify token and return user information
    
    Use Supabase REST API to directly verify token
    """
    try:
        import httpx
        
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase configuration not set"
            )
        
        # Use Supabase REST API to verify token
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": supabase_key
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Supabase auth returned status code: {response.status_code}")
                print(f"Response content: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token verification failed: Invalid token or token expired"
                )
            
            user_data = response.json()
            
            # Check if user data exists
            if not user_data or not user_data.get("id"):
                print(f"❌ User data is empty: {user_data}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token verification failed: User does not exist"
                )
            
            return User(
                id=user_data["id"],
                email=user_data.get("email", ""),
                created_at=user_data.get("created_at")
            )
            
    except httpx.HTTPError as e:
        print(f"❌ HTTP request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: Unable to connect to authentication service"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Token verification error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


# ========== Dependencies: Get current user ==========

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current logged in user (dependency)"""
    token = credentials.credentials
    return await verify_token(token)


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    return current_user


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

async def get_google_oauth_url(redirect_to: str = None) -> dict:
    """Get Google OAuth authorization URL"""
    try:
        # For OAuth, we need to use ANON_KEY instead of SERVICE_ROLE_KEY
        # Because OAuth is a user authentication flow, requires normal Supabase authentication
        import os
        from supabase import create_client
        from urllib.parse import urlparse
        
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        
        print(f"🔐 Checking Supabase configuration:")
        print(f"   SUPABASE_URL: {'Set' if supabase_url else 'Not set'} ({supabase_url[:50] if supabase_url else 'N/A'}...)")
        print(f"   SUPABASE_ANON_KEY: {'Set' if supabase_anon_key else 'Not set'} ({'***' + supabase_anon_key[-10:] if supabase_anon_key else 'N/A'})")
        
        if not supabase_url or not supabase_anon_key:
            error_msg = "Supabase configuration missing: "
            if not supabase_url:
                error_msg += "SUPABASE_URL not set; "
            if not supabase_anon_key:
                error_msg += "SUPABASE_ANON_KEY not set; "
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg.strip()
            )
        
        # Create Supabase client using ANON_KEY (for OAuth)
        supabase = create_client(supabase_url, supabase_anon_key)
        
        # Force normalization: clean all URL-related values
        try:
            # Build redirect URL
            if not redirect_to:
                # Default redirect to frontend login page
                frontend_url_env = os.getenv("FRONTEND_URL")
                redirect_to = require_clean_url("FRONTEND_URL env", frontend_url_env) if frontend_url_env else require_clean_url("FRONTEND_URL fallback", "https://www.desktopai.org")
            else:
                redirect_to = require_clean_url("redirect_to parameter", redirect_to)
            
            # Reverse validation: parse redirect_to origin
            u = urlparse(redirect_to)
            if u.scheme not in ("http", "https") or not u.netloc:
                raise ValueError(f"Invalid redirect_to: {redirect_to}")
            
            # Supabase doesn't accept hash URLs in redirect_to, so convert hash route to path route
            # For Electron dev: http://localhost:5173/#/auth/callback -> http://localhost:5173/auth/callback
            if u.fragment and u.fragment.startswith('/auth/callback'):
                # Extract hash route and convert to path
                hash_route = u.fragment
                # Remove hash and use path instead
                redirect_to = f"{u.scheme}://{u.netloc}/auth/callback"
                if u.query:
                    redirect_to += f"?{u.query}"
                print(f"🔐 Converted hash URL to path URL: {u.geturl()} -> {redirect_to}")
            
            # Ensure redirect_to is a complete URL
            if not redirect_to.startswith("http"):
                redirect_to = f"https://{redirect_to}" if not redirect_to.startswith("localhost") else f"http://{redirect_to}"
        except ValueError as e:
            print(f"❌ URL validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Build callback URL - point to backend /api/auth/callback
        # Backend will handle OAuth callback using service key (no PKCE needed)
        # 
        # IMPORTANT: If redirect_to already contains platform=desktop (from main.py),
        # we should use it directly. Otherwise, extract base URL and construct callback URL.
        if redirect_to and "platform=desktop" in redirect_to:
            # redirect_to is already set to backend callback URL with platform=desktop
            # Use it directly as the backend_callback_url
            backend_callback_url = redirect_to
            print(f"🔐 Using provided backend callback URL (already contains platform=desktop): {backend_callback_url}")
        else:
            # Extract base URL from redirect_to or use environment variable
            if redirect_to:
                u = urlparse(redirect_to)
                base_url = f"{u.scheme}://{u.netloc}"
            else:
                frontend_url_env = os.getenv("FRONTEND_URL")
                base_url = require_clean_url("FRONTEND_URL env", frontend_url_env) if frontend_url_env else require_clean_url("FRONTEND_URL fallback", "https://www.desktopai.org")
            
            # For web platform: use frontend callback URL
            # For desktop platform: this path should not be reached (handled above)
            backend_callback_url = f"{base_url}/api/auth/callback"
            
            print(f"🔐 Constructed backend callback URL: {backend_callback_url}")
        
        # Call Supabase REST API /auth/v1/authorize (standard OAuth flow, no PKCE)
        print(f"🔐 Calling Supabase REST API /auth/v1/authorize (standard OAuth flow)")
        
        try:
            import httpx
            
            # Call Supabase REST API /auth/v1/authorize endpoint
            # Use standard OAuth flow (no PKCE) - backend will handle callback with service key
            # According to Supabase GoTrue API docs, we need:
            # - response_type=code (for OAuth code flow)
            # - provider=google (OAuth provider)
            # - redirect_uri (where to redirect after OAuth, Supabase's callback URL)
            # - redirect_to (where Supabase should redirect after processing, our backend callback URL)
            authorize_url = f"{supabase_url}/auth/v1/authorize"
            
            # Get Supabase's callback URL (where OAuth provider redirects to)
            supabase_callback_url = f"{supabase_url}/auth/v1/callback"
            
            authorize_params = {
                "response_type": "code",
                "provider": "google",
                "redirect_uri": supabase_callback_url,  # Where OAuth provider redirects to
                "redirect_to": backend_callback_url  # Where Supabase redirects to after processing (backend endpoint)
            }
            
            print(f"🔐 Calling: {authorize_url}")
            print(f"🔐 Params: response_type=code, provider=google, redirect_uri={supabase_callback_url[:50]}..., redirect_to={backend_callback_url[:50]}...")
            
            # Try POST request first (some OAuth endpoints require POST)
            # If that fails with 405, fall back to GET
            async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
                # First try POST with JSON body
                try:
                    response = await client.post(
                        authorize_url,
                        json=authorize_params,
                        headers={
                            "apikey": supabase_anon_key,
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        }
                    )
                    print(f"🔐 POST request response status: {response.status_code}")
                    # If POST returns 405 Method Not Allowed, fall back to GET
                    if response.status_code == 405:
                        print(f"⚠️ POST request returned 405 Method Not Allowed, trying GET...")
                        response = await client.get(
                            authorize_url,
                            params=authorize_params,
                            headers={
                                "apikey": supabase_anon_key,
                                "Accept": "application/json"
                            }
                        )
                except Exception as post_error:
                    print(f"⚠️ POST request failed: {post_error}, trying GET...")
                    # Fall back to GET request
                    response = await client.get(
                        authorize_url,
                        params=authorize_params,
                        headers={
                            "apikey": supabase_anon_key,
                            "Accept": "application/json"
                        }
                    )
                
                print(f"🔐 Response status: {response.status_code}")
                print(f"🔐 Response headers: {dict(response.headers)}")
                print(f"🔐 Response text (first 500 chars): {response.text[:500]}")
                
                # Supabase should return 302 redirect with Location header containing OAuth URL
                url = None
                if response.status_code == 302:
                    url = response.headers.get("Location")
                    print(f"🔐 Got redirect URL from Location header: {url[:150] if url else 'None'}...")
                elif response.status_code == 200:
                    # Try JSON response
                    try:
                        data = response.json()
                        url = data.get("url") or data.get("data", {}).get("url")
                        print(f"🔐 Got URL from JSON: {url[:150] if url else 'None'}...")
                    except:
                        # Try to extract from text
                        text = response.text
                        import re
                        match = re.search(r'url[=:]\s*["\']?([^"\'\s]+)["\']?', text, re.IGNORECASE)
                        if match:
                            url = match.group(1)
                            print(f"🔐 Extracted URL from text: {url[:150]}...")
                else:
                    error_text = response.text[:500]
                    print(f"❌ Error: {response.status_code} - {error_text}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to initialize flow state: {response.status_code} - {error_text}"
                    )
            
            if not url:
                # Fallback: build URL directly (won't initialize flow state, but might work)
                from urllib.parse import urlencode
                url = f"{authorize_url}?{urlencode(authorize_params)}"
                print(f"⚠️ No URL from response, building directly: {url[:150]}...")
            
            if not url:
                error_detail = f"Failed to build Google OAuth URL"
                print(f"❌ {error_detail}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
                )
            
            print(f"✅ Successfully built Google OAuth URL: {url[:150]}...")
            
            # Return OAuth URL (no code_verifier needed for non-PKCE flow)
            return {
                "url": url
            }
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as oauth_error:
            import traceback
            oauth_trace = traceback.format_exc()
            error_msg = f"Failed to call Supabase OAuth API: {str(oauth_error)}"
            print(f"❌ Supabase OAuth call exception: {oauth_error}")
            print(f"❌ Error type: {type(oauth_error).__name__}")
            print(f"❌ Detailed error information:\n{oauth_trace}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
    except HTTPException:
        # Re-raise HTTPException
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Failed to get Google OAuth URL: {e}")
        print(f"Detailed error information:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Google OAuth URL: {str(e)}"
        )

