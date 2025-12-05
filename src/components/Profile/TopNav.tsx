import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { logout } from '../../lib/auth';
import './TopNav.css';

export const TopNav: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/');
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

