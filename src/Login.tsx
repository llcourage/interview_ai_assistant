import React, { useState } from 'react';
import { supabase } from './lib/supabase';
import './Login.css';

interface LoginProps {
  onLoginSuccess: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      if (isRegister) {
        // 注册
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        });
        
        if (error) throw error;
        
        if (data.session) {
          // Auto login after registration
          setMessage('Registration successful! Signing in...');
          setTimeout(() => {
            onLoginSuccess();
          }, 1000);
        } else if (data.user && !data.session) {
          // Email verification required
          setMessage('Registration successful! Please check your email to verify (if email verification is enabled)');
          setTimeout(() => {
            setIsRegister(false);
          }, 3000);
        }
      } else {
        // Login
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        
        if (error) throw error;
        
        if (data.session) {
          setMessage('Login successful!');
          setTimeout(() => {
            onLoginSuccess();
          }, 500);
        }
      }
    } catch (err: any) {
      console.error('Auth error:', err);
      setError(err.message || 'Operation failed. Please check your email and password.');
    } finally {
      setLoading(false);
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

