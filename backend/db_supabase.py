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

# Create Supabase client
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Note: Module-level print removed to avoid Windows console encoding issues
# Configuration check will be handled by logging system at application startup


def get_supabase() -> Client:
    """Get Supabase client instance
    
    Note: This client uses SERVICE_ROLE_KEY, can bypass RLS restrictions
    Only for backend server-side operations, must never expose to frontend
    """
    if not supabase_client:
        raise Exception("Supabase client not initialized, please check environment variable configuration")
    
    # Debug: Log which key is being used (only first time to avoid spam)
    if not hasattr(get_supabase, '_logged'):
        using_service_role = bool(SUPABASE_SERVICE_ROLE_KEY)
        print(f"🔍 DEBUG get_supabase: Using {'SERVICE_ROLE_KEY' if using_service_role else 'ANON_KEY'} (RLS bypass: {using_service_role})")
        get_supabase._logged = True
    
    return supabase_client


