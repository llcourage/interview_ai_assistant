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

# HTTP Bearer token
security = HTTPBearer()


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
                detail="Registration failed"
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
        
        # Build callback URL
        # Note: For both Electron and Web, OAuth callback should point to frontend page (/auth/callback)
        # Frontend will use Supabase JS SDK to handle PKCE, then call backend API to set session cookie
        # Don't change to /api/auth/callback, because backend cannot handle PKCE (no code_verifier)
        if redirect_to.endswith("/auth/callback"):
            callback_url = redirect_to
        else:
            # If redirect_to doesn't include /auth/callback, add it
            callback_url = f"{redirect_to}/auth/callback" if not redirect_to.endswith("/") else f"{redirect_to}auth/callback"
        
        # Generate PKCE parameters manually for Electron environment
        # Electron needs code_verifier to exchange code for session
        import secrets
        import base64
        import hashlib
        
        # Generate code_verifier (43-128 characters, URL-safe base64)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code_challenge (SHA256 hash of code_verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        print(f"🔐 Generated PKCE parameters:")
        print(f"   - code_verifier length: {len(code_verifier)}")
        print(f"   - code_challenge length: {len(code_challenge)}")
        
        # Directly call Supabase REST API to initialize flow state with our PKCE parameters
        # This ensures the flow state stored on Supabase server uses our code_challenge
        print(f"🔐 Calling Supabase REST API directly to initialize flow state with our PKCE parameters")
        print(f"🔐 Using code_challenge: {code_challenge[:20]}...")
        print(f"🔐 Using code_verifier: {code_verifier[:20]}...")
        
        try:
            import httpx
            
            # Call Supabase REST API /auth/v1/authorize endpoint to initialize flow state
            # This will create the flow state on Supabase server with our code_challenge
            authorize_url = f"{supabase_url}/auth/v1/authorize"
            authorize_params = {
                "provider": "google",
                "redirect_to": callback_url,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            }
            
            print(f"🔐 Calling Supabase authorize endpoint: {authorize_url}")
            print(f"🔐 With params: provider=google, redirect_to={callback_url[:50]}..., code_challenge={code_challenge[:20]}...")
            
            # Make GET request to initialize flow state
            # Supabase will redirect to the OAuth provider, but we just need the URL
            async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
                response = await client.get(
                    authorize_url,
                    params=authorize_params,
                    headers={
                        "apikey": supabase_anon_key,
                        "Accept": "application/json"
                    }
                )
                
                print(f"🔐 Supabase authorize response status: {response.status_code}")
                print(f"🔐 Supabase authorize response headers: {dict(response.headers)}")
                
                # Supabase should return a redirect (302) or the OAuth URL
                if response.status_code == 302:
                    # Extract redirect URL from Location header
                    url = response.headers.get("Location")
                    print(f"🔐 Got redirect URL from Location header: {url[:150] if url else 'None'}...")
                elif response.status_code == 200:
                    # Try to extract URL from response body
                    try:
                        response_data = response.json()
                        url = response_data.get("url") or response_data.get("data", {}).get("url")
                        print(f"🔐 Got URL from response body: {url[:150] if url else 'None'}...")
                    except:
                        # If not JSON, try to extract from text
                        response_text = response.text
                        import re
                        url_match = re.search(r'url[=:]\s*["\']?([^"\'\s]+)["\']?', response_text, re.IGNORECASE)
                        if url_match:
                            url = url_match.group(1)
                            print(f"🔐 Extracted URL from response text: {url[:150]}...")
                else:
                    error_text = response.text[:500]
                    print(f"❌ Supabase authorize endpoint error: {response.status_code} - {error_text}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to initialize OAuth flow state: {response.status_code} - {error_text}"
                    )
            
            if not url:
                # Fallback: build URL directly (but this won't initialize flow state)
                from urllib.parse import urlencode
                url = f"{authorize_url}?{urlencode(authorize_params)}"
                print(f"⚠️ Could not get URL from Supabase response, building directly: {url[:150]}...")
            
            final_url = url
            
            if not url:
                error_detail = f"Failed to build Google OAuth URL"
                print(f"❌ {error_detail}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
                )
            
            final_url = url
            print(f"✅ Successfully built Google OAuth URL with PKCE: {final_url[:150]}...")
            
            # Return both URL and code_verifier for Electron to use
            return {
                "url": final_url,
                "code_verifier": code_verifier
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

