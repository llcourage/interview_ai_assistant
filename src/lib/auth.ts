/**
 * Authentication utility - Authenticate via Vercel API, not directly connecting to Supabase
 */
import { API_BASE_URL } from './api';

export interface AuthToken {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user?: {
    id: string;
    email: string;
  };
}

export interface User {
  id: string;
  email: string;
}

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

/**
 * Save authentication token
 */
export const saveToken = (token: AuthToken): void => {
  localStorage.setItem(TOKEN_KEY, JSON.stringify(token));
};

/**
 * Get authentication token
 */
export const getToken = (): AuthToken | null => {
  const tokenStr = localStorage.getItem(TOKEN_KEY);
  if (!tokenStr) return null;
  try {
    return JSON.parse(tokenStr);
  } catch {
    return null;
  }
};

/**
 * Clear authentication token
 */
export const clearToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

/**
 * Get Authorization header
 */
export const getAuthHeader = (): string | null => {
  const token = getToken();
  if (!token) return null;
  // Ensure token_type format is correct (HTTP standard requires first letter uppercase)
  const tokenType = token.token_type 
    ? token.token_type.charAt(0).toUpperCase() + token.token_type.slice(1).toLowerCase()
    : 'Bearer';
  return `${tokenType} ${token.access_token}`;
};

/**
 * User registration
 */
export const register = async (email: string, password: string): Promise<AuthToken> => {
  const response = await fetch(`${API_BASE_URL}/api/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(error.detail || 'Registration failed');
  }

  const token: AuthToken = await response.json();
  saveToken(token);
  return token;
};

/**
 * User login
 */
export const login = async (email: string, password: string): Promise<AuthToken> => {
  const response = await fetch(`${API_BASE_URL}/api/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  const token: AuthToken = await response.json();
  saveToken(token);
  return token;
};

/**
 * User logout
 */
export const logout = async (): Promise<void> => {
  // Clear local token
  clearToken();
  
  // Try to clear server-side session cookie
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include', // Include Cookie
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (response.ok) {
      console.log('✅ Server session cookie cleared');
    } else {
      console.warn('⚠️ Failed to clear server session cookie, but continuing logout flow');
    }
  } catch (error) {
    console.warn('⚠️ Error clearing server session cookie, but continuing logout flow:', error);
    // Continue logout flow even if clearing server cookie fails
  }
  
  // Trigger authentication state change event to notify other components
  window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: false } }));
  
  console.log('🚪 User logged out');
};

/**
 * Get current user information
 */
export const getCurrentUser = async (): Promise<User | null> => {
  const token = getToken();
  if (!token) {
    // No token found
    return null;
  }

  try {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      console.log('🔒 getCurrentUser: No auth header');
      return null;
    }

    // Calling API to get current user
    // Note: In development environment, credentials: 'include' is needed to carry Cookie
    const apiUrl = `${API_BASE_URL}/api/me`;
    console.log('🌐 getCurrentUser: Requesting API:', apiUrl);
    console.log('🌐 getCurrentUser: Request headers:', { 
      'Authorization': authHeader.substring(0, 20) + '...',
      'credentials': 'include'
    });
    
    const response = await fetch(apiUrl, {
      credentials: 'include', // Include Cookie (for cross-origin requests)
      headers: {
        'Authorization': authHeader,
      },
    });

    console.log('🌐 getCurrentUser: Response status:', response.status, response.statusText);

    if (!response.ok) {
      console.error('🔒 getCurrentUser: API error', response.status, response.statusText);
      // Token may have expired
      if (response.status === 401) {
        // 401 Unauthorized, clearing token
        clearToken();
      }
      return null;
    }

    const user: User = await response.json();
    // User authenticated successfully
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  } catch (error) {
    console.error('🔒 getCurrentUser: Exception', error);
    return null;
  }
};

/**
 * Check if user is authenticated
 * First check token in localStorage, if not found then check server Cookie session
 */
export const isAuthenticated = async (): Promise<boolean> => {
  console.log('🔑 isAuthenticated: Starting authentication check');
  
  // 1. First check token in localStorage (supports Web token login)
  const token = getToken();
  if (token) {
    console.log('🔑 isAuthenticated: Found token, validating token');
  try {
    const user = await getCurrentUser();
    const authenticated = user !== null;
      console.log('🔑 isAuthenticated: Token validation complete, result:', authenticated, user ? `User: ${user.email}` : 'No user');
      return authenticated;
    } catch (error) {
      console.error('🔑 isAuthenticated: Token validation failed:', error);
      // Token invalid, continue checking server session
    }
  }
  
  // 2. No token or token invalid, check server Cookie session (Electron OAuth flow)
  console.log('🔑 isAuthenticated: No valid token found, calling /api/me to check server session');
  try {
    // Try to get token (even if previous validation failed, there might be an invalid token)
    const token = getToken();
    const authHeader = token ? getAuthHeader() : null;
    
    // Check if Electron environment
    const isElectronEnv = typeof window !== 'undefined' && (window as any).aiShot !== undefined;
    
    // Build request headers
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    // For Electron apps, prioritize Authorization header (because Cookie may not work correctly)
    // For Web apps, send both Cookie and Authorization header (double insurance)
    if (authHeader) {
      headers['Authorization'] = authHeader;
      if (isElectronEnv) {
        console.log('🔑 isAuthenticated: Electron environment, prioritizing Authorization header');
      } else {
        console.log('🔑 isAuthenticated: Sending both Cookie and Authorization header');
      }
    } else {
      if (isElectronEnv) {
        console.log('🔑 isAuthenticated: Electron environment, no token, only trying Cookie');
      } else {
        console.log('🔑 isAuthenticated: Only sending Cookie (no Authorization header)');
      }
    }
    
    // Directly call API to check server session, use credentials: 'include' to carry Cookie
    const response = await fetch(`${API_BASE_URL}/api/me`, {
      credentials: 'include', // Include Cookie (for cross-origin requests)
      headers,
    });
    
    console.log('🌐 isAuthenticated: /api/me response status:', response.status, response.statusText);
    
    if (response.ok) {
      const user = await response.json();
      console.log('🔑 isAuthenticated: Server returned logged-in user:', user.email || user.id);
      
      // If server returns user info, save to localStorage (optional, for subsequent requests)
      if (user && user.id) {
        // Note: Don't save full token here, as server uses Cookie to manage session
        // But can save user info
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      }
      
      return true;
    } else {
      console.log('🔑 isAuthenticated: Server session check failed, status code:', response.status);
      if (response.status === 401) {
        // 401 Unauthorized, clear any invalid token that may exist
        clearToken();
      }
      return false;
    }
  } catch (error) {
    console.error('🔑 isAuthenticated: Server session check exception:', error);
    return false;
  }
};

/**
 * Get Google OAuth authorization URL
 * Also get Supabase configuration (for OAuth callback)
 */
export const getGoogleOAuthUrl = async (redirectTo?: string): Promise<{ url: string; supabaseUrl?: string; supabaseAnonKey?: string }> => {
  const params = new URLSearchParams();
  if (redirectTo) {
    params.append('redirect_to', redirectTo);
  }
  
  const response = await fetch(`${API_BASE_URL}/api/auth/google/url?${params.toString()}`);
  
  if (!response.ok) {
    let errorMessage = 'Failed to get Google OAuth URL';
    try {
      const error = await response.json();
      // Handle different error formats
      if (error.detail) {
        errorMessage = error.detail;
      } else if (error.msg) {
        errorMessage = error.msg;
      } else if (error.message) {
        errorMessage = error.message;
      } else if (error.error) {
        errorMessage = error.error;
      }
      console.error('Google OAuth URL error:', {
        status: response.status,
        statusText: response.statusText,
        error: error,
        apiUrl: `${API_BASE_URL}/api/auth/google/url`
      });
    } catch (e) {
      console.error('Failed to parse error response:', e);
      errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }
  
  const data = await response.json();
  
  // Ensure returned data contains necessary fields
  if (!data.url) {
    throw new Error('API returned data missing url field');
  }
  
  return {
    url: data.url,
    supabaseUrl: data.supabase_url || data.supabaseUrl,
    supabaseAnonKey: data.supabase_anon_key || data.supabaseAnonKey
  };
};

/**
 * Login with Google OAuth
 */
export const loginWithGoogle = async (): Promise<void> => {
  try {
    // Check if Electron environment
    if (typeof window !== 'undefined' && (window as any).aiShot?.loginWithGoogle) {
      // Electron environment: Use Electron OAuth window, handled via backend API
      console.log('🔐 Electron environment: Handling OAuth login via Electron IPC');
      
      // Setup IPC listener as backup (in case main process sends token via IPC before promise resolves)
      let ipcTokenReceived = false;
      const ipcHandler = (data: any) => {
        if (ipcTokenReceived) return; // Only handle once
        ipcTokenReceived = true;
        
        console.log('🔐 Electron: Received token via IPC event:', {
          hasAccessToken: !!data.access_token,
          hasRefreshToken: !!data.refresh_token,
          hasUser: !!data.user
        });
        
        // Create token object from IPC data
        const token: AuthToken = {
          access_token: data.access_token,
          refresh_token: data.refresh_token || '',
          token_type: data.token_type || 'bearer',
          user: data.user ? {
            id: data.user.id || '',
            email: data.user.email || ''
          } : undefined
        };
        
        // Save token to localStorage
        console.log('🔐 Electron: Saving token to localStorage (from IPC)');
        saveToken(token);
        
        // Verify token was saved
        const savedToken = getToken();
        if (savedToken) {
          console.log('✅ Electron: Token saved successfully (from IPC), user:', savedToken.user?.email);
        } else {
          console.error('❌ Electron: Token save failed (from IPC)!');
        }
        
        // Trigger auth state change event
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        console.log('🔐 Electron: Triggered auth-state-changed event (from IPC)');
        
        // Note: Navigation should be handled by the calling component (e.g., Login.tsx)
        // Do not reload here, let React Router handle navigation
      };
      
      // Register IPC listener
      if ((window as any).aiShot?.onOAuthComplete) {
        (window as any).aiShot.onOAuthComplete(ipcHandler);
      }
      
      // Call main process loginWithGoogle (this may resolve with token or trigger IPC event)
      console.log('🔐 Electron: Calling main process loginWithGoogle');
      const result = await (window as any).aiShot.loginWithGoogle();
      console.log('🔐 Electron: Received result from main process:', { 
        success: result.success, 
        hasAccessToken: !!result.access_token, 
        hasUser: !!result.user,
        error: result.error 
      });
      
      // If promise already resolved with token data, use it
      if (result.success && result.access_token && !ipcTokenReceived) {
        console.log('🔐 Electron: Received token data from promise result');
        
        // Create token object from result
        const token: AuthToken = {
          access_token: result.access_token,
          refresh_token: result.refresh_token || '',
          token_type: 'bearer',
          user: result.user ? {
            id: result.user.id || '',
            email: result.user.email || ''
          } : undefined
        };
        
        // Save token to localStorage
        console.log('🔐 Electron: Saving token to localStorage (from promise)');
        saveToken(token);
        
        // Verify token was saved
        const savedToken = getToken();
        if (savedToken) {
          console.log('✅ Electron: Token saved successfully (from promise), user:', savedToken.user?.email);
        } else {
          console.error('❌ Electron: Token save failed (from promise)!');
        }
        
        // Trigger auth state change event
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        console.log('🔐 Electron: Triggered auth-state-changed event (from promise)');
        
        // Note: Navigation should be handled by the calling component (e.g., Login.tsx)
        // Do not reload here, let React Router handle navigation
        return;
      } else if (!result.success && !ipcTokenReceived) {
        const errorMsg = result.error || 'Failed to get OAuth token from Electron';
        console.error('❌ Electron: OAuth failed:', errorMsg);
        throw new Error(errorMsg);
      }
      // If ipcTokenReceived is true, the IPC handler already handled everything
      return;
    } else {
      // Web environment: Directly use Supabase JS SDK to generate OAuth URL
      // This way code_verifier will be saved in browser storage, PKCE flow can work properly
      console.log('🔐 Web environment: Using Supabase JS SDK to generate OAuth URL');
      
      // Define redirectTo first (before dynamic import)
      const redirectTo = `${window.location.origin}/auth/callback`;
      
      // Dynamically import Supabase client
      let createClient: any;
      try {
        const supabaseModule = await import('@supabase/supabase-js');
        createClient = supabaseModule.createClient;
      } catch (importError: any) {
        console.error('🔐 Failed to dynamically import Supabase SDK:', importError);
        // If dynamic import fails, fallback to using backend API to get OAuth URL
        console.log('🔐 Fallback: Using backend API to get OAuth URL');
        const { url } = await getGoogleOAuthUrl(redirectTo);
        // Directly redirect to OAuth URL returned by backend
        window.location.href = url;
        return;
      }
      
      // Get Supabase configuration
      let supabaseUrl = localStorage.getItem('supabase_url');
      let supabaseAnonKey = localStorage.getItem('supabase_anon_key');
      
      // If not in localStorage, get from API
      if (!supabaseUrl || !supabaseAnonKey) {
        try {
          const { API_BASE_URL } = await import('./api');
          const configResponse = await fetch(`${API_BASE_URL}/api/config/supabase`);
          if (configResponse.ok) {
            const config = await configResponse.json();
            supabaseUrl = config.supabase_url;
            supabaseAnonKey = config.supabase_anon_key;
            if (supabaseUrl && supabaseAnonKey) {
              localStorage.setItem('supabase_url', supabaseUrl);
              localStorage.setItem('supabase_anon_key', supabaseAnonKey);
            }
          }
        } catch (e) {
          console.error('🔐 Failed to get Supabase configuration from API:', e);
        }
      }
      
      // If still not available, use environment variables or default values
      if (!supabaseUrl) {
        supabaseUrl = (import.meta.env as any).VITE_SUPABASE_URL || 'https://cjrblsalpfhugeatrhrr.supabase.co';
      }
      if (!supabaseAnonKey) {
        supabaseAnonKey = (import.meta.env as any).VITE_SUPABASE_ANON_KEY || '';
      }
      
      if (!supabaseAnonKey) {
        throw new Error('Supabase ANON_KEY not configured. Please ensure VITE_SUPABASE_ANON_KEY environment variable is set, or API returned configuration.');
      }
      
      // Create Supabase client
      const supabase = createClient(supabaseUrl, supabaseAnonKey);
      
      // Use Supabase JS SDK to generate OAuth URL (this way code_verifier will be saved in browser storage)
      console.log('🔐 Web environment: redirectTo:', redirectTo);
      
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectTo
        }
      });
      
      if (error) {
        throw new Error(error.message || 'Failed to get OAuth URL');
      }
      
      if (!data?.url) {
        throw new Error('Failed to get OAuth URL from Supabase');
      }
      
      console.log('🔐 Web environment: Redirecting to OAuth URL');
      // Redirect to Google authorization page
      window.location.href = data.url;
    }
  } catch (error: any) {
    console.error('Google OAuth error:', error);
    throw new Error(error.message || 'Failed to initiate Google login');
  }
};

/**
 * Handle OAuth callback
 * Electron environment: Handled via backend API, not directly connecting to Supabase
 * Web environment: Use frontend Supabase client to handle directly, avoiding PKCE code_verifier issues
 */
export const handleOAuthCallback = async (code: string, state?: string, codeVerifier?: string): Promise<AuthToken> => {
  // Check if Electron environment
  const isElectronEnv = typeof window !== 'undefined' && (window as any).aiShot !== undefined;
  
  if (isElectronEnv) {
    // NEW ARCHITECTURE: Electron OAuth is now handled entirely via backend callback
    // Token is received through postMessage from /api/auth/callback page
    // This function should not be called in Electron environment anymore
    console.error('❌ handleOAuthCallback called in Electron environment - this should not happen');
    console.error('❌ Electron OAuth flow should receive token via postMessage from backend callback page');
    throw new Error('Electron OAuth callback handling has been moved to backend callback endpoint. This function is deprecated for Electron.');
  } else {
    // Web environment: Use frontend Supabase client to handle directly
    console.log('🔐 Web environment: Using Supabase JS SDK to handle OAuth callback');
    
    // Dynamically import Supabase client
    let createClient: any;
    try {
      const supabaseModule = await import('@supabase/supabase-js');
      createClient = supabaseModule.createClient;
    } catch (importError: any) {
      console.error('🔐 Failed to dynamically import Supabase SDK:', importError);
      throw new Error(`Failed to load Supabase SDK: ${importError.message || importError}. Please check network connection or refresh page and try again.`);
    }
    
    // Get Supabase configuration from localStorage (if previously saved)
    let supabaseUrl = localStorage.getItem('supabase_url');
    let supabaseAnonKey = localStorage.getItem('supabase_anon_key');
    
    // If not in localStorage, try to get from API
    if (!supabaseUrl || !supabaseAnonKey) {
      try {
        const configResponse = await fetch(`${API_BASE_URL}/api/config/supabase`);
        if (configResponse.ok) {
          const config = await configResponse.json();
          supabaseUrl = config.supabase_url;
          supabaseAnonKey = config.supabase_anon_key;
          // Save to localStorage for next use
          if (supabaseUrl && supabaseAnonKey) {
            localStorage.setItem('supabase_url', supabaseUrl);
            localStorage.setItem('supabase_anon_key', supabaseAnonKey);
          }
        }
      } catch (error) {
        console.warn('Failed to get Supabase configuration from API, using environment variables or default values', error);
      }
    }
    
    // If still not available, use environment variables or default values
    if (!supabaseUrl) {
      supabaseUrl = (import.meta.env as any).VITE_SUPABASE_URL || 'https://cjrblsalpfhugeatrhrr.supabase.co';
    }
    
    if (!supabaseAnonKey) {
      supabaseAnonKey = (import.meta.env as any).VITE_SUPABASE_ANON_KEY || '';
    }
    
    if (!supabaseAnonKey) {
      console.error('❌ Supabase configuration fetch failed:', {
        fromLocalStorage: !!localStorage.getItem('supabase_anon_key'),
        fromEnv: !!(import.meta.env as any).VITE_SUPABASE_ANON_KEY,
        supabaseUrl,
        supabaseAnonKey: supabaseAnonKey ? '***' : '(empty)'
      });
      throw new Error('Supabase ANON_KEY not configured. Please ensure VITE_SUPABASE_ANON_KEY environment variable is set, or API returned configuration.');
    }
    
    if (!supabaseUrl) {
      throw new Error('Supabase URL not configured.');
    }
    
    console.log('✅ Creating client with Supabase configuration:', {
      url: supabaseUrl,
      keyLength: supabaseAnonKey.length
    });
    
    // Create Supabase client (using dynamic configuration)
    const supabase = createClient(supabaseUrl, supabaseAnonKey);
    
    // Use Supabase JS SDK's exchangeCodeForSession
    // This way can automatically get code_verifier from browser storage
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);
    
    if (error) {
      console.error('Supabase exchangeCodeForSession error:', error);
      throw new Error(error.message || 'OAuth callback failed');
    }
    
    if (!data.session || !data.user) {
      throw new Error('OAuth callback failed: No session or user data received');
    }
    
    // Convert to our AuthToken format
    const token: AuthToken = {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      token_type: 'bearer',
      user: {
        id: data.user.id,
        email: data.user.email || ''
      }
    };
    
    saveToken(token);
    return token;
  }
};

