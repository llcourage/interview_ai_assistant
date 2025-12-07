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

// Electron 客户端默认页面组件（检测登录状态，已登录显示 App，未登录显示 Login）
const ElectronDefaultPage: React.FC = () => {
  const [authStatus, setAuthStatus] = React.useState<boolean | null>(null);
  
  React.useEffect(() => {
    let isMounted = true;
    let lastAuthStatus: boolean | null = null;
    
    const checkAuth = async () => {
      try {
        const authenticated = await isAuthenticated();
        
        // 只在状态变化时通知 Electron，避免重复调用
        if (!isMounted) return;
        
        if (lastAuthStatus !== authenticated) {
          console.log('🔒 AppRouter - Auth status changed:', lastAuthStatus, '->', authenticated);
          lastAuthStatus = authenticated;
          setAuthStatus(authenticated);
          
          // 如果已登录，通知 Electron 创建悬浮窗
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
    
    // 监听认证状态变化事件（登录/登出时触发）
    const handleAuthStateChange = () => {
      console.log('🔒 AppRouter - Auth state change event received');
      checkAuth();
    };
    window.addEventListener('auth-state-changed', handleAuthStateChange);
    
    // 监听 Electron IPC 的 auth:refresh 事件（OAuth 窗口关闭时触发）
    // 注意：不要在 cleanup 中移除监听器，避免 React StrictMode 下监听器被删除
    if (isElectron()) {
      const api = (window as any).aiShot;
      if (api?.onAuthRefresh) {
        console.log('🔒 AppRouter - Registering auth:refresh listener');
        api.onAuthRefresh(() => {
          console.log('🔄 AppRouter - Received auth:refresh from Electron, calling checkAuth()');
          checkAuth();
        });
      } else {
        console.warn('⚠️ AppRouter - aiShot.onAuthRefresh 不存在，无法监听 auth:refresh');
      }
    }
    
    // 定期检查认证状态（替代 Supabase 的实时监听）
    const interval = setInterval(checkAuth, 5000);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
      window.removeEventListener('auth-state-changed', handleAuthStateChange);
      // 注意：不在 cleanup 中移除 Electron IPC 监听器
      // 避免 React StrictMode 下 cleanup 导致监听器被删除
      // 即使重复注册，也只是会触发多次回调，不会导致监听器丢失
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

