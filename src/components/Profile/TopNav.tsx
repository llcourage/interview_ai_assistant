import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { logout } from '../../lib/auth';
import { isElectron } from '../../utils/isElectron';
import './TopNav.css';

export const TopNav: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    // 登出后，在 Electron 环境中导航到 /login，在 Web 环境中导航到 /
    // 这样可以避免 ElectronDefaultPage 的认证检查延迟
    if (isElectron()) {
      navigate('/login', { replace: true });
    } else {
      navigate('/', { replace: true });
    }
  };

  return (
    <header className="top-nav">
      <div className="nav-left">
        <h1 className="logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          🔥 Desktop AI
        </h1>
        <span className="nav-badge">Profile</span>
      </div>

      <div className="nav-right">
        <button
          className={`nav-button ${location.pathname === '/' ? 'active' : ''}`}
          onClick={() => navigate('/')}
        >
          Overview
        </button>
        <button
          className={`nav-button ${location.pathname === '/plans' ? 'active' : ''}`}
          onClick={() => navigate('/plans')}
        >
          Plans
        </button>
        <button
          className="nav-button nav-button-secondary"
          onClick={handleLogout}
        >
          Logout
        </button>
      </div>
    </header>
  );
};

