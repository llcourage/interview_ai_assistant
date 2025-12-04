import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { register, login } from './lib/auth';
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

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>🔥 AI Interview Assistant</h1>
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

