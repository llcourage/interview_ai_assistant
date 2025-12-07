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


async def get_google_oauth_url(redirect_to: str = None) -> str:
    """Get Google OAuth authorization URL"""
    try:
        # For OAuth, we need to use ANON_KEY instead of SERVICE_ROLE_KEY
        # Because OAuth is a user authentication flow, requires normal Supabase authentication
        import os
        from supabase import create_client
        
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
        
        # Build redirect URL
        if not redirect_to:
            # Default redirect to frontend login page
            redirect_to = os.getenv("FRONTEND_URL", "https://www.desktopai.org")
        
        # Ensure redirect_to is a complete URL
        if not redirect_to.startswith("http"):
            redirect_to = f"https://{redirect_to}" if not redirect_to.startswith("localhost") else f"http://{redirect_to}"
        
        # Build callback URL
        # Note: For both Electron and Web, OAuth callback should point to frontend page (/auth/callback)
        # Frontend will use Supabase JS SDK to handle PKCE, then call backend API to set session cookie
        # Don't change to /api/auth/callback, because backend cannot handle PKCE (no code_verifier)
        if redirect_to.endswith("/auth/callback"):
            callback_url = redirect_to
        else:
            # If redirect_to doesn't include /auth/callback, add it
            callback_url = f"{redirect_to}/auth/callback" if not redirect_to.endswith("/") else f"{redirect_to}auth/callback"
        
        # Get Google OAuth URL
        # Note: Supabase Python SDK uses PKCE by default
        # Since callback will be handled by frontend (using Supabase JS SDK), PKCE will be handled correctly
        # Frontend will get code_verifier from browser storage
        print(f"🔐 Preparing to call Supabase OAuth, provider: google, redirect_to: {callback_url}")
        try:
            response = supabase.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": callback_url
                }
            })
            print(f"🔐 Supabase OAuth response type: {type(response)}")
            print(f"🔐 Supabase OAuth response content: {response}")
            
            if not response:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get Google OAuth URL: Supabase returned empty response"
                )
            
            # Supabase Python SDK may return dict or object
            url = None
            if isinstance(response, dict):
                url = response.get("url") or response.get("data", {}).get("url")
            elif hasattr(response, "url"):
                # If it's an object, directly get url attribute
                url = response.url
            elif hasattr(response, "data"):
                # If it has data attribute, try to get from data
                data = response.data
                if isinstance(data, dict):
                    url = data.get("url")
                elif hasattr(data, "url"):
                    url = data.url
            
            # If still not found, try to convert to string and parse (last resort)
            if not url:
                response_str = str(response)
                print(f"🔐 Attempting to extract URL from response string: {response_str[:200]}")
                # Can add more parsing logic here, but usually shouldn't reach here
            
            if not url:
                print(f"❌ No URL found in Supabase OAuth response, response content: {response}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get Google OAuth URL: No URL in Supabase response. Response type: {type(response)}, Response content: {str(response)[:200]}"
                )
            
            print(f"✅ Successfully got Google OAuth URL: {url[:100]}...")
            return url
        except Exception as oauth_error:
            import traceback
            oauth_trace = traceback.format_exc()
            print(f"❌ Supabase OAuth call exception: {oauth_error}")
            print(f"Detailed error information:\n{oauth_trace}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to call Supabase OAuth API: {str(oauth_error)}"
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

