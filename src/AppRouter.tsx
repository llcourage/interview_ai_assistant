import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Landing } from './Landing';
import { Plans } from './Plans';
import { Help } from './Help';
import { Checkout } from './Checkout';
import { Success } from './Success';
import { Profile } from './Profile';
import App from './App';
import { Login } from './Login';
import { AuthCallback } from './AuthCallback';
import Overlay from './Overlay';
import { isElectron } from './utils/isElectron';
import { isAuthenticated } from './lib/auth';

// Electron client default page component (check login status, show App if logged in, show Login if not logged in)
const ElectronDefaultPage: React.FC = () => {
  const [authStatus, setAuthStatus] = React.useState<boolean | null>(null);
  
  React.useEffect(() => {
    let isMounted = true;
    let lastAuthStatus: boolean | null = null;
    
    const checkAuth = async () => {
      try {
        const authenticated = await isAuthenticated();
        
        // Only notify Electron when status changes to avoid duplicate calls
        if (!isMounted) return;
        
        if (lastAuthStatus !== authenticated) {
          console.log('🔒 AppRouter - Auth status changed:', lastAuthStatus, '->', authenticated);
          lastAuthStatus = authenticated;
          setAuthStatus(authenticated);
          
          // If logged in, notify Electron to create overlay window
          if (authenticated && window.aiShot?.userLoggedIn) {
            console.log('🔒 AppRouter - Calling userLoggedIn');
            await window.aiShot.userLoggedIn();
          } else if (!authenticated && window.aiShot?.userLoggedOut) {
            console.log('🔒 AppRouter - Calling userLoggedOut');
            await window.aiShot.userLoggedOut();
          }
        }
      } catch (error) {
        console.error('Auth check error:', error);
        if (isMounted) {
          setAuthStatus(false);
        }
      }
    };
    
    checkAuth();
    
    // Listen to authentication state change events (triggered on login/logout)
    const handleAuthStateChange = () => {
      console.log('🔒 AppRouter - Auth state change event received');
      checkAuth();
    };
    window.addEventListener('auth-state-changed', handleAuthStateChange);
    
    // Listen to Electron IPC auth:refresh event (triggered when OAuth window closes)
    // Note: Don't remove listener in cleanup to avoid listener deletion in React StrictMode
    if (isElectron()) {
      const api = (window as any).aiShot;
      if (api?.onAuthRefresh) {
        console.log('🔒 AppRouter - Registering auth:refresh listener');
        api.onAuthRefresh(() => {
          console.log('🔄 AppRouter - Received auth:refresh from Electron, calling checkAuth()');
          checkAuth();
        });
      } else {
        console.warn('⚠️ AppRouter - aiShot.onAuthRefresh does not exist, cannot listen to auth:refresh');
      }
    }
    
    // Periodically check authentication status (replacement for Supabase real-time listening)
    const interval = setInterval(checkAuth, 5000);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
      window.removeEventListener('auth-state-changed', handleAuthStateChange);
      // Note: Don't remove Electron IPC listener in cleanup
      // Avoid listener deletion caused by cleanup in React StrictMode
      // Even if registered multiple times, it will only trigger multiple callbacks, won't cause listener loss
    };
  }, []);
  
  if (authStatus === null) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontSize: '1.2rem'
      }}>
        <p>Loading...</p>
      </div>
    );
  }
  
  if (!authStatus) {
    return <Navigate to="/login" replace />;
  }
  
  return <Navigate to="/app" replace />;
};

export const AppRouter: React.FC = () => {
  const isElectronClient = isElectron();
  
  return (
    <Routes>
      <Route path="/" element={isElectronClient ? <ElectronDefaultPage /> : <Landing />} />
      <Route path="/plans" element={<Plans />} />
      <Route path="/help" element={<Help />} />
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/checkout" element={<Checkout />} />
      <Route path="/success" element={<Success />} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/app" element={<App />} />
      <Route path="/overlay" element={<Overlay />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

