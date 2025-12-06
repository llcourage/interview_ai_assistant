import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { register, login, loginWithGoogle } from './lib/auth';
import { isElectron } from './utils/isElectron';
import './Login.css';

interface LoginProps {
  onLoginSuccess?: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Check URL parameters
  useEffect(() => {
    const mode = searchParams.get('mode');
    const plan = searchParams.get('plan');
    const redirect = searchParams.get('redirect');

    if (mode === 'signup') {
      setIsRegister(true);
    }

    // If plan and redirect exist, save to localStorage
    if (plan && redirect) {
      localStorage.setItem('pendingPlan', plan);
      localStorage.setItem('pendingRedirect', redirect);
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      if (isRegister) {
        // Register
        await register(email, password);
          setMessage('Registration successful! Signing in...');
          setTimeout(() => {
            handleLoginSuccess();
          }, 1000);
      } else {
        // Login
        const token = await login(email, password);
        console.log('✅ Login successful, token saved:', !!token);
          setMessage('Login successful!');
        
        // 触发自定义事件，通知其他组件认证状态已改变
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        
          setTimeout(() => {
            handleLoginSuccess();
          }, 500);
      }
    } catch (err: any) {
      console.error('Auth error:', err);
      setError(err.message || 'Operation failed. Please check your email and password.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    // Check if there's a pending plan and redirect
    const pendingPlan = localStorage.getItem('pendingPlan');
    const pendingRedirect = localStorage.getItem('pendingRedirect');

    if (pendingPlan && pendingRedirect) {
      // Clear temporary data
      localStorage.removeItem('pendingPlan');
      localStorage.removeItem('pendingRedirect');
      // Navigate to checkout
      navigate(`${pendingRedirect}?plan=${pendingPlan}`);
    } else if (onLoginSuccess) {
      // Use the provided callback
      onLoginSuccess();
    } else {
      // In Electron client, redirect to /app; in web browser, redirect to /profile
      if (isElectron()) {
        navigate('/app');
      } else {
        navigate('/profile');
      }
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setLoading(true);
    try {
      await loginWithGoogle();
      // Electron: 在 OAuth 窗口关闭后会自动处理
      // Web: 用户将被重定向到 Google 授权页面
      
      // 对于 Electron，等待一下让 OAuth 流程完成
      if (isElectron()) {
        // Electron 环境下的处理在 auth.ts 中已包含
        // 这里只需要等待一下
        setTimeout(() => {
          setLoading(false);
        }, 1000);
      }
    } catch (err: any) {
      console.error('Google login error:', err);
      setError(err.message || 'Failed to initiate Google login');
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>🔥 Desktop AI</h1>
        <h2>{isRegister ? 'Create Account' : 'Welcome Back'}</h2>
        
        {error && <div className="error-message">❌ {error}</div>}
        {message && <div className="success-message">✅ {message}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={loading}
              autoComplete="email"
            />
          </div>
          
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              required
              disabled={loading}
              minLength={6}
              autoComplete={isRegister ? "new-password" : "current-password"}
            />
          </div>
          
          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? '⏳ Processing...' : (isRegister ? 'Sign Up' : 'Sign In')}
          </button>
        </form>

        <div className="oauth-divider">
          <span>or</span>
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={loading}
          className="google-login-btn"
        >
          <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>
        
        <p className="toggle-mode">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}
          <button 
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError('');
              setMessage('');
            }}
            className="toggle-btn"
            disabled={loading}
          >
            {isRegister ? 'Sign In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  );
};

