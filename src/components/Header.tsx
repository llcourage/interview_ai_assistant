import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import './Header.css';

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 检查认证状态
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setIsAuthenticated(!!session);
      setUserEmail(session?.user?.email || null);
      setLoading(false);
    };

    checkAuth();

    // 监听认证状态变化
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsAuthenticated(!!session);
      setUserEmail(session?.user?.email || null);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate('/');
  };

  return (
    <header className="landing-header">
      <div className="header-top">
        <div className="header-container">
          <div className="header-left">
            <h1 className="logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
              🔥 AI Interview Assistant
            </h1>
          </div>
          <div className="header-right">
            {loading ? (
              <span style={{ color: '#666' }}>Loading...</span>
            ) : isAuthenticated ? (
              <>
                <button 
                  className="header-btn"
                  onClick={() => navigate('/profile')}
                  style={{ marginRight: '10px' }}
                >
                  Profile
                </button>
                <button 
                  className="header-btn login-btn"
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <button 
                  className="header-btn login-btn"
                  onClick={() => navigate('/login')}
                >
                  Login
                </button>
                <button 
                  className="header-btn signup-btn"
                  onClick={() => navigate('/login?mode=signup')}
                >
                  Sign Up
                </button>
              </>
            )}
          </div>
        </div>
      </div>
      <nav className="header-nav">
        <div className="header-container">
          <div className="nav-links">
            <button 
              className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
              onClick={() => navigate('/')}
            >
              Overview
            </button>
            <button 
              className={`nav-link ${location.pathname === '/plans' ? 'active' : ''}`}
              onClick={() => navigate('/plans')}
            >
              Plans
            </button>
            <button 
              className={`nav-link ${location.pathname === '/help' ? 'active' : ''}`}
              onClick={() => navigate('/help')}
            >
              Helps
            </button>
          </div>
        </div>
      </nav>
    </header>
  );
};


