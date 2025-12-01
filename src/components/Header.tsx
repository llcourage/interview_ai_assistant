import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Header.css';

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

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

