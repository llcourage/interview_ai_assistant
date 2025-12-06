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
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const errorParam = searchParams.get('error');

      if (errorParam) {
        setError(`OAuth error: ${errorParam}`);
        setLoading(false);
        setTimeout(() => {
          navigate('/login');
        }, 3000);
        return;
      }

      if (!code) {
        setError('No authorization code received');
        setLoading(false);
        setTimeout(() => {
          navigate('/login');
        }, 3000);
        return;
      }

      try {
        await handleOAuthCallback(code, state || undefined);
        
        // 触发自定义事件，通知其他组件认证状态已改变
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        
        // 检查是否有待处理的 plan 和 redirect
        const pendingPlan = localStorage.getItem('pendingPlan');
        const pendingRedirect = localStorage.getItem('pendingRedirect');

        if (pendingPlan && pendingRedirect) {
          localStorage.removeItem('pendingPlan');
          localStorage.removeItem('pendingRedirect');
          navigate(`${pendingRedirect}?plan=${pendingPlan}`);
        } else {
          // 根据环境重定向
          if (isElectron()) {
            navigate('/app');
          } else {
            navigate('/profile');
          }
        }
      } catch (err: any) {
        console.error('OAuth callback error:', err);
        setError(err.message || 'Failed to complete authentication');
        setLoading(false);
        setTimeout(() => {
          navigate('/login');
        }, 3000);
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

