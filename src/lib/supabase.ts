/**
 * Supabase client configuration
 * Note: This client is only used for frontend OAuth flow (exchangeCodeForSession)
 * All other operations are performed via Vercel API
 * 
 * ⚠️ This file is deprecated, no longer exports supabase client
 * All Supabase clients are dynamically created in handleOAuthCallback
 * This ensures configuration is obtained from API
 * 
 * This file is kept only for backward compatibility to avoid import errors
 */

// No longer export anything, all Supabase operations are dynamically handled in auth.ts






