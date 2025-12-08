import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { handleOAuthCallback } from './lib/auth';
import { isElectron } from './utils/isElectron';
import './Login.css';

export const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const processCallback = async () => {
      console.log('🔐 AuthCallback: Starting callback processing');
      console.log('🔐 AuthCallback: Current URL:', window.location.href);
      console.log('🔐 AuthCallback: window.location.search:', window.location.search);
      console.log('🔐 AuthCallback: window.location.hash:', window.location.hash);
      
      // For Electron with HashRouter: if we're at /auth/callback (path route from Supabase),
      // convert it to hash route #/auth/callback
      if (isElectron() && window.location.pathname === '/auth/callback' && !window.location.hash.includes('/auth/callback')) {
        const search = window.location.search;
        const hash = `#/auth/callback${search}`;
        console.log('🔐 AuthCallback: Converting path route to hash route:', window.location.pathname + search, '->', hash);
        window.location.hash = hash;
        // Wait a bit for hash change to take effect
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // For Web environment (BrowserRouter), parameters are in search
      // For Electron environment (HashRouter), parameters may be in hash
      // Supabase OAuth callback may return access_token in hash (URL hash mode)
      let code: string | null = null;
      let state: string | null = null;
      let errorParam: string | null = null;
      let oauthUrl: string | null = null;
      let accessToken: string | null = null;
      let refreshToken: string | null = null;
      
      // First check if there's access_token in hash (Supabase URL hash callback mode)
      if (window.location.hash) {
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        accessToken = hashParams.get('access_token');
        refreshToken = hashParams.get('refresh_token');
        if (accessToken) {
          console.log('🔐 AuthCallback: Detected access_token in URL hash (Supabase direct callback mode)');
        }
      }
      
      if (isElectron()) {
        // Electron uses HashRouter, parameters are in hash
        // Hash format may be: #/auth/callback?code=xxx&state=yyy
        const hashMatch = window.location.hash.match(/\?([^#]+)/);
        if (hashMatch) {
          const hashParams = new URLSearchParams(hashMatch[1]);
          if (!code) code = hashParams.get('code');
          if (!state) state = hashParams.get('state');
          if (!errorParam) errorParam = hashParams.get('error');
          if (!oauthUrl) oauthUrl = hashParams.get('oauth_url');
        }
        // Also try to get from searchParams (if React Router has already parsed)
        if (!code) code = searchParams.get('code');
        if (!state) state = searchParams.get('state');
        if (!errorParam) errorParam = searchParams.get('error');
        if (!oauthUrl) oauthUrl = searchParams.get('oauth_url');
      } else {
        // Web uses BrowserRouter, parameters are in search
        if (!code) code = searchParams.get('code');
        if (!state) state = searchParams.get('state');
        if (!errorParam) errorParam = searchParams.get('error');
        if (!oauthUrl) oauthUrl = searchParams.get('oauth_url');
      }
      
      console.log('🔐 AuthCallback: URL params:', {
        oauth_url: oauthUrl ? 'present' : 'missing',
        code: code ? 'present' : 'missing',
        state: state ? 'present' : 'missing',
        error: errorParam ? 'present' : 'missing',
        isElectron: isElectron()
      });
      
      // Check if Electron OAuth window (has oauth_url parameter)
      if (oauthUrl && isElectron()) {
        // Electron OAuth window: Redirect to OAuth URL
        console.log('🔐 Electron OAuth window: Detected oauth_url parameter, redirecting to OAuth URL');
        console.log('🔐 OAuth URL:', oauthUrl.substring(0, 100) + '...');
        
        // Save Supabase configuration to localStorage (if API returned it)
        // These configurations will be used in handleOAuthCallback
        // For Electron, parameters may be in hash
        let supabaseUrl: string | null = null;
        let supabaseAnonKey: string | null = null;
        if (isElectron()) {
          const hashMatch = window.location.hash.match(/\?([^#]+)/);
          if (hashMatch) {
            const hashParams = new URLSearchParams(hashMatch[1]);
            supabaseUrl = hashParams.get('supabase_url');
            supabaseAnonKey = hashParams.get('supabase_anon_key');
          }
        }
        if (!supabaseUrl) supabaseUrl = searchParams.get('supabase_url');
        if (!supabaseAnonKey) supabaseAnonKey = searchParams.get('supabase_anon_key');
        if (supabaseUrl && supabaseAnonKey) {
          localStorage.setItem('supabase_url', supabaseUrl);
          localStorage.setItem('supabase_anon_key', supabaseAnonKey);
          console.log('🔐 Saved Supabase configuration to localStorage');
        } else {
          // If not obtained from URL parameters, try to get from API
          console.log('🔐 Supabase configuration not obtained from URL parameters, trying to get from API');
          try {
            const { API_BASE_URL } = await import('./lib/api');
            const configResponse = await fetch(`${API_BASE_URL}/api/config/supabase`);
            if (configResponse.ok) {
              const config = await configResponse.json();
              localStorage.setItem('supabase_url', config.supabase_url);
              localStorage.setItem('supabase_anon_key', config.supabase_anon_key);
              console.log('🔐 Obtained and saved Supabase configuration from API');
            }
          } catch (e) {
            console.error('🔐 Failed to get Supabase configuration from API:', e);
          }
        }
        
        // Redirect to OAuth URL
        console.log('🔐 Redirecting to OAuth URL...');
        window.location.href = oauthUrl;
        return;
      }

      // code, state, errorParam have been obtained above

      if (errorParam) {
        const errorMsg = `OAuth error: ${errorParam}`;
        setError(errorMsg);
        setLoading(false);
        
        // If Electron OAuth window, send error via IPC
        if (isElectron() && (window as any).ipcRenderer) {
          try {
            (window as any).ipcRenderer.send('oauth-result', { success: false, error: errorMsg });
          } catch (e) {
            console.error('Failed to send OAuth error to main process:', e);
          }
        } else {
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
        return;
      }

      // If access_token is in hash, use it directly (Supabase URL hash callback mode)
      if (accessToken) {
        console.log('🔐 AuthCallback: Using access_token from URL hash');
        try {
          // Directly use access_token to create session
          const session = {
            access_token: accessToken,
            refresh_token: refreshToken || '',
            token_type: 'bearer',
            user: null as any // Will parse from token later
          };
          
          // Parse JWT token to get user information
          try {
            const payload = JSON.parse(atob(accessToken.split('.')[1]));
            session.user = {
              id: payload.sub,
              email: payload.email || ''
            };
          } catch (e) {
            console.warn('Failed to parse JWT token, will get user info from API later');
          }
          
          // Save token
          const { saveToken } = await import('./lib/auth');
          saveToken(session);
          
          // Call backend API to set session cookie
          try {
            console.log('🔐 AuthCallback: Calling backend API to set session cookie');
            const { API_BASE_URL } = await import('./lib/api');
            const response = await fetch(`${API_BASE_URL}/api/auth/set-session`, {
              method: 'POST',
              credentials: 'include',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                access_token: accessToken,
              }),
            });
            
            if (response.ok) {
              console.log('🔐 AuthCallback: Backend session cookie set successfully');
            } else {
              console.warn('🔐 AuthCallback: Backend session cookie set failed, but continuing flow');
            }
          } catch (e) {
            console.error('🔐 AuthCallback: Failed to set session cookie:', e);
          }
          
          // Trigger authentication state change event
          window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
          
          // Check if there's a pending plan and redirect
          const pendingPlan = localStorage.getItem('pendingPlan');
          const pendingRedirect = localStorage.getItem('pendingRedirect');

          if (pendingPlan && pendingRedirect) {
            localStorage.removeItem('pendingPlan');
            localStorage.removeItem('pendingRedirect');
            navigate(`${pendingRedirect}?plan=${pendingPlan}`);
          } else {
            if (isElectron()) {
              navigate('/app');
            } else {
              navigate('/profile');
            }
          }
          return;
        } catch (err: any) {
          console.error('Failed to process access_token:', err);
          setError(err.message || 'Failed to process authentication');
          setLoading(false);
          setTimeout(() => {
            navigate('/login');
          }, 3000);
          return;
        }
      }
      
      if (!code) {
        const errorMsg = 'No authorization code or access_token received';
        setError(errorMsg);
        setLoading(false);
        
        // If Electron OAuth window, send error via IPC
        if (isElectron() && (window as any).ipcRenderer) {
          try {
            (window as any).ipcRenderer.send('oauth-result', { success: false, error: errorMsg });
          } catch (e) {
            console.error('Failed to send OAuth error to main process:', e);
          }
        } else {
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
        return;
      }

      try {
        console.log('🔐 AuthCallback: Starting OAuth code processing');
        console.log('🔐 AuthCallback: code length:', code ? code.length : 0);
        console.log('🔐 AuthCallback: state:', state || 'N/A');
        
        const session = await handleOAuthCallback(code, state || undefined);
        console.log('🔐 AuthCallback: OAuth callback processing successful');
        console.log('🔐 AuthCallback: session access_token length:', session?.access_token ? session.access_token.length : 0);
        console.log('🔐 AuthCallback: session user:', session?.user?.email || 'N/A');
        
        // After processing OAuth callback, call backend API to set session cookie
        try {
          console.log('🔐 AuthCallback: Calling backend API to set session cookie');
          const { API_BASE_URL } = await import('./lib/api');
          const accessToken = session?.access_token || (typeof session === 'string' ? session : null);
          
          if (accessToken) {
            const response = await fetch(`${API_BASE_URL}/api/auth/set-session`, {
              method: 'POST',
              credentials: 'include', // Include Cookie
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                access_token: accessToken,
              }),
            });
            
            if (response.ok) {
              console.log('🔐 AuthCallback: Backend session cookie set successfully');
            } else {
              console.warn('🔐 AuthCallback: Backend session cookie set failed, but continuing flow');
            }
          }
        } catch (e) {
          console.error('🔐 AuthCallback: Failed to set session cookie:', e);
          // Continue flow even if setting cookie fails
        }
        
        // If Electron OAuth window, send success result via IPC
        if (isElectron()) {
          try {
            console.log('🔐 AuthCallback: Detected Electron environment, preparing to send OAuth result via IPC');
            console.log('🔐 AuthCallback: code length:', code ? code.length : 0);
            console.log('🔐 AuthCallback: state:', state || 'N/A');
            
            // Try multiple ways to send OAuth result
            const oauthResult = { 
              success: true, 
              code, 
              state: state || undefined 
            };
            console.log('🔐 AuthCallback: Preparing to send oauth-result message:', JSON.stringify({
              success: oauthResult.success,
              hasCode: !!oauthResult.code,
              hasState: !!oauthResult.state
            }));
            
            // Method 1: Use aiShot.sendOAuthResult (if available)
            if ((window as any).aiShot?.sendOAuthResult) {
              console.log('🔐 AuthCallback: Using aiShot.sendOAuthResult');
              (window as any).aiShot.sendOAuthResult(oauthResult);
            }
            // Method 2: Directly use ipcRenderer (if exposed)
            else if ((window as any).ipcRenderer) {
              console.log('🔐 AuthCallback: Using ipcRenderer.send');
              (window as any).ipcRenderer.send('oauth-result', oauthResult);
            }
            // Method 3: Try window.postMessage (fallback)
            else {
              console.warn('🔐 AuthCallback: Cannot find IPC method, trying postMessage');
              window.postMessage({ type: 'oauth-result', ...oauthResult }, '*');
            }
            
            console.log('🔐 AuthCallback: IPC message sent, waiting for main process to handle');
            
            // Show success message
            setLoading(false);
            setError(''); // Clear error
            return; // Don't navigate, let Electron main process handle
          } catch (e: any) {
            console.error('🔐 AuthCallback: Failed to send OAuth result to main process:', e);
            console.error('🔐 AuthCallback: Error details:', e?.message || String(e), e?.stack);
            // Fallback to normal flow
          }
        }
        
        // Trigger custom event to notify other components that authentication state has changed
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        
        // Check if there's a pending plan and redirect
        const pendingPlan = localStorage.getItem('pendingPlan');
        const pendingRedirect = localStorage.getItem('pendingRedirect');

        if (pendingPlan && pendingRedirect) {
          localStorage.removeItem('pendingPlan');
          localStorage.removeItem('pendingRedirect');
          navigate(`${pendingRedirect}?plan=${pendingPlan}`);
        } else {
          // Redirect based on environment
          if (isElectron()) {
            navigate('/app');
          } else {
            navigate('/profile');
          }
        }
      } catch (err: any) {
        console.error('OAuth callback error:', err);
        const errorMsg = err.message || 'Failed to complete authentication';
        setError(errorMsg);
        setLoading(false);
        
        // If Electron OAuth window, send error via IPC
        if (isElectron() && (window as any).ipcRenderer) {
          try {
            (window as any).ipcRenderer.send('oauth-result', { success: false, error: errorMsg });
          } catch (e) {
            console.error('Failed to send OAuth error to main process:', e);
          }
        } else {
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
      }
    };

    processCallback();
  }, [searchParams, navigate]);

  if (loading) {
    return (
      <div className="login-container">
        <div className="login-box">
          <h1>🔥 Desktop AI</h1>
          <h2>Completing authentication...</h2>
          <div style={{ textAlign: 'center', marginTop: '2rem' }}>
            <p>Please wait while we sign you in...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>🔥 Desktop AI</h1>
        {error && (
          <>
            <div className="error-message">❌ {error}</div>
            <p style={{ textAlign: 'center', marginTop: '1rem', color: 'var(--color-text-secondary)' }}>
              Redirecting to login page...
            </p>
          </>
        )}
      </div>
    </div>
  );
};

