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
        
        # Get Google OAuth URL
        # Note: We need to manually add PKCE parameters to the OAuth URL
        # because Supabase Python SDK doesn't return code_verifier
        print(f"🔐 Preparing to call Supabase OAuth, provider: google, redirect_to: {callback_url}")
        try:
            # Call Supabase OAuth API (this will generate its own PKCE, but we'll override)
            response = supabase.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": callback_url,
                    "query_params": {
                        "code_challenge": code_challenge,
                        "code_challenge_method": "S256"
                    }
                }
            })
            
            print(f"🔐 Supabase OAuth response type: {type(response)}")
            print(f"🔐 Supabase OAuth response attributes: {dir(response) if hasattr(response, '__dict__') else 'N/A'}")
            
            if not response:
                print(f"❌ Supabase OAuth returned None or empty response")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get Google OAuth URL: Supabase returned empty response"
                )
            
            # Supabase Python SDK may return different formats
            # Try multiple ways to extract URL
            url = None
            
            # Method 1: Check if response is a dict
            if isinstance(response, dict):
                url = response.get("url") or response.get("data", {}).get("url")
                print(f"🔐 Response is dict, extracted URL: {'Found' if url else 'Not found'}")
            
            # Method 2: Check if response has url attribute directly
            if not url and hasattr(response, "url"):
                try:
                    url = response.url
                    print(f"🔐 Response has url attribute: {'Found' if url else 'None'}")
                except Exception as e:
                    print(f"⚠️ Error accessing response.url: {e}")
            
            # Method 3: Check if response has data attribute
            if not url and hasattr(response, "data"):
                try:
                    data = response.data
                    if isinstance(data, dict):
                        url = data.get("url")
                    elif hasattr(data, "url"):
                        url = data.url
                    print(f"🔐 Response has data attribute, extracted URL: {'Found' if url else 'Not found'}")
                except Exception as e:
                    print(f"⚠️ Error accessing response.data: {e}")
            
            # Method 4: Try to access as a response object with model attribute
            if not url and hasattr(response, "model"):
                try:
                    model = response.model
                    if hasattr(model, "url"):
                        url = model.url
                    print(f"🔐 Response has model attribute, extracted URL: {'Found' if url else 'Not found'}")
                except Exception as e:
                    print(f"⚠️ Error accessing response.model: {e}")
            
            # If still not found, log full response for debugging
            if not url:
                response_str = str(response)
                response_repr = repr(response)
                print(f"❌ No URL found in Supabase OAuth response")
                print(f"🔐 Response string (first 500 chars): {response_str[:500]}")
                print(f"🔐 Response repr (first 500 chars): {response_repr[:500]}")
                
                # Try to extract URL from string representation (last resort)
                import re
                url_match = re.search(r'url[=:]\s*["\']?([^"\'\s]+)["\']?', response_str, re.IGNORECASE)
                if url_match:
                    url = url_match.group(1)
                    print(f"🔐 Extracted URL from string representation: {url[:100]}...")
            
            if not url:
                error_detail = f"Failed to get Google OAuth URL: No URL in Supabase response. Response type: {type(response)}, Response content: {str(response)[:200]}"
                print(f"❌ {error_detail}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
                )
            
            # Ensure the URL contains our code_challenge (in case Supabase SDK overrides it)
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # Add/override PKCE parameters
            query_params['code_challenge'] = [code_challenge]
            query_params['code_challenge_method'] = ['S256']
            
            # Rebuild URL with PKCE parameters
            new_query = urlencode(query_params, doseq=True)
            final_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
            
            print(f"✅ Successfully got Google OAuth URL with PKCE: {final_url[:100]}...")
            
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

