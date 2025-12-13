"""
Supabase client configuration
Provides Supabase authentication and database services

⚠️ Important: Backend uses SERVICE_ROLE_KEY to bypass RLS (Row Level Security)
This ensures database operations (INSERT/UPDATE) won't be blocked by RLS policies
"""
import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Explicitly specify .env file path
backend_dir = Path(__file__).parent.resolve()
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)


# Supabase configuration
# Backend uses SERVICE_ROLE_KEY to bypass RLS restrictions
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Prioritize SERVICE_ROLE_KEY, if not available use ANON_KEY (but will cause RLS errors)
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY

# Debug: check which key is being used
if SUPABASE_SERVICE_ROLE_KEY:
    # Check if key is really service_role (not anon)
    # service_role key's JWT payload should have role field as "service_role"
    import base64
    import json
    try:
        # JWT format: header.payload.signature
        parts = SUPABASE_SERVICE_ROLE_KEY.split('.')
        if len(parts) >= 2:
            # Decode payload (add padding if needed)
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)  # Add padding
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            role = decoded.get('role', 'unknown')
            if role != 'service_role':
                print(f"⚠️ WARNING: SUPABASE_SERVICE_ROLE_KEY appears to have role='{role}', not 'service_role'!")
                print(f"   This will cause RLS policy violations. Please check your .env file.")
    except Exception:
        pass  # If decode fails, ignore (may be format issue)

# Create Supabase client (for read operations, can use ANON_KEY if needed)
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Create admin client (for write operations, MUST use SERVICE_ROLE_KEY to bypass RLS)
supabase_admin_client: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    # Note: print removed to avoid Windows console encoding issues, will log at function call time
elif SUPABASE_URL and SUPABASE_KEY:
    # Fallback: use regular client if service_role not available (will cause RLS errors)
    supabase_admin_client = supabase_client
    print(f"⚠️ WARNING: Using regular Supabase client for admin operations (RLS bypass NOT enabled)")
    print(f"   This will cause RLS policy violations. Please set SUPABASE_SERVICE_ROLE_KEY in environment variables.")

# Note: Module-level print removed to avoid Windows console encoding issues
# Configuration check will be handled by logging system at application startup


def get_supabase() -> Client:
    """Get Supabase client instance (for read operations)
    
    Note: This client may use ANON_KEY or SERVICE_ROLE_KEY depending on configuration
    """
    if not supabase_client:
        raise Exception("Supabase client not initialized, please check environment variable configuration")
    
    # Debug: Log which key is being used (only first time to avoid spam)
    if not hasattr(get_supabase, '_logged'):
        using_service_role = bool(SUPABASE_SERVICE_ROLE_KEY) and SUPABASE_KEY == SUPABASE_SERVICE_ROLE_KEY
        print(f"🔍 DEBUG get_supabase: Using {'SERVICE_ROLE_KEY' if using_service_role else 'ANON_KEY'} (RLS bypass: {using_service_role})")
        get_supabase._logged = True
    
    return supabase_client


def get_supabase_admin() -> Client:
    """Get Supabase admin client instance (for write operations)
    
    Note: This client MUST use SERVICE_ROLE_KEY to bypass RLS restrictions
    Only for backend server-side operations, must never expose to frontend
    """
    if not supabase_admin_client:
        raise Exception("Supabase admin client not initialized. SUPABASE_SERVICE_ROLE_KEY must be set in environment variables.")
    
    # Debug: Log which key is being used (only first time to avoid spam)
    if not hasattr(get_supabase_admin, '_logged'):
        using_service_role = bool(SUPABASE_SERVICE_ROLE_KEY)
        if using_service_role:
            print(f"✅ Supabase admin client using SERVICE_ROLE_KEY (RLS bypass enabled)")
        else:
            print(f"⚠️ WARNING: Supabase admin client NOT using SERVICE_ROLE_KEY (RLS bypass NOT enabled)")
            print(f"   This will cause RLS policy violations. Please set SUPABASE_SERVICE_ROLE_KEY in environment variables.")
        get_supabase_admin._logged = True
    
    return supabase_admin_client


