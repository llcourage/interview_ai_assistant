import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { isAuthenticated, getCurrentUser, logout } from '../lib/auth';
import { DOWNLOAD_CONFIG } from '../constants/download';
import './Header.css';

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [authStatus, setAuthStatus] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 检查认证状态
    const checkAuth = async () => {
      const authenticated = await isAuthenticated();
      setAuthStatus(authenticated);
      if (authenticated) {
        const user = await getCurrentUser();
        setUserEmail(user?.email || null);
      } else {
        setUserEmail(null);
      }
      setLoading(false);
    };

    checkAuth();

    // 定期检查认证状态（替代 Supabase 的实时监听）
    const interval = setInterval(checkAuth, 5000);

    return () => {
      clearInterval(interval);
    };
  }, []);

  const handleLogout = async () => {
    await logout();
    setAuthStatus(false);
    setUserEmail(null);
    // 登出后导航到登录页面或首页
    navigate('/', { replace: true });
  };

  return (
    <header className="landing-header">
      <div className="header-top">
        <div className="header-container">
          <div className="header-left">
            <h1 className="logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
              🔥 Desktop AI
            </h1>
          </div>
          <div className="header-right">
            {loading ? (
              <span style={{ color: '#666' }}>Loading...</span>
            ) : authStatus ? (
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
                <a
                  href={DOWNLOAD_CONFIG.windows.url}
                  className="header-btn download-btn"
                  download={DOWNLOAD_CONFIG.windows.filename}
                >
                  <svg className="download-icon-small" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Free Download
                </a>
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


