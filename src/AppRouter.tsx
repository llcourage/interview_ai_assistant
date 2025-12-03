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
import Overlay from './Overlay';
import { isElectron } from './utils/isElectron';

// Electron 客户端默认页面组件（检测登录状态，已登录显示 App，未登录显示 Login）
const ElectronDefaultPage: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = React.useState<boolean | null>(null);
  
  React.useEffect(() => {
    let subscription: any = null;
    
    const checkAuth = async () => {
      try {
        const { supabase } = await import('./lib/supabase');
        const { data: { session } } = await supabase.auth.getSession();
        setIsAuthenticated(!!session);
        
        // 如果已登录，通知 Electron 创建悬浮窗
        if (session && window.aiShot?.userLoggedIn) {
          await window.aiShot.userLoggedIn();
        }
        
        // 监听认证状态变化
        const { data: { subscription: authSubscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
          setIsAuthenticated(!!session);
          
          if (session && window.aiShot?.userLoggedIn) {
            await window.aiShot.userLoggedIn();
          } else if (!session && window.aiShot?.userLoggedOut) {
            await window.aiShot.userLoggedOut();
          }
        });
        
        subscription = authSubscription;
      } catch (error) {
        console.error('Auth check error:', error);
        setIsAuthenticated(false);
      }
    };
    
    checkAuth();
    
    return () => {
      if (subscription) {
        subscription.unsubscribe();
      }
    };
  }, []);
  
  if (isAuthenticated === null) {
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
  
  if (!isAuthenticated) {
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
      <Route path="/checkout" element={<Checkout />} />
      <Route path="/success" element={<Success />} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/app" element={<App />} />
      <Route path="/overlay" element={<Overlay />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

