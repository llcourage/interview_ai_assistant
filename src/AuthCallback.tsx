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
      console.log('🔐 AuthCallback: 开始处理回调');
      console.log('🔐 AuthCallback: 当前 URL:', window.location.href);
      console.log('🔐 AuthCallback: URL params:', {
        oauth_url: searchParams.get('oauth_url') ? 'present' : 'missing',
        code: searchParams.get('code') ? 'present' : 'missing',
        state: searchParams.get('state') ? 'present' : 'missing',
        error: searchParams.get('error') ? 'present' : 'missing',
        isElectron: isElectron()
      });
      
      // 检查是否是 Electron OAuth 窗口（有 oauth_url 参数）
      const oauthUrl = searchParams.get('oauth_url');
      if (oauthUrl && isElectron()) {
        // Electron OAuth 窗口：跳转到 OAuth URL
        console.log('🔐 Electron OAuth 窗口：检测到 oauth_url 参数，跳转到 OAuth URL');
        console.log('🔐 OAuth URL:', oauthUrl.substring(0, 100) + '...');
        
        // 保存 Supabase 配置到 localStorage（如果 API 返回了的话）
        // 这些配置会在 handleOAuthCallback 中使用
        const supabaseUrl = searchParams.get('supabase_url');
        const supabaseAnonKey = searchParams.get('supabase_anon_key');
        if (supabaseUrl && supabaseAnonKey) {
          localStorage.setItem('supabase_url', supabaseUrl);
          localStorage.setItem('supabase_anon_key', supabaseAnonKey);
          console.log('🔐 已保存 Supabase 配置到 localStorage');
        } else {
          // 如果没有从 URL 参数获取，尝试从 API 获取
          console.log('🔐 未从 URL 参数获取 Supabase 配置，尝试从 API 获取');
          try {
            const { API_BASE_URL } = await import('./lib/api');
            const configResponse = await fetch(`${API_BASE_URL}/api/config/supabase`);
            if (configResponse.ok) {
              const config = await configResponse.json();
              localStorage.setItem('supabase_url', config.supabase_url);
              localStorage.setItem('supabase_anon_key', config.supabase_anon_key);
              console.log('🔐 从 API 获取并保存 Supabase 配置');
            }
          } catch (e) {
            console.error('🔐 从 API 获取 Supabase 配置失败:', e);
          }
        }
        
        // 跳转到 OAuth URL
        console.log('🔐 跳转到 OAuth URL...');
        window.location.href = oauthUrl;
        return;
      }

      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const errorParam = searchParams.get('error');

      if (errorParam) {
        const errorMsg = `OAuth error: ${errorParam}`;
        setError(errorMsg);
        setLoading(false);
        
        // 如果是 Electron OAuth 窗口，通过 IPC 发送错误
        if (isElectron() && (window as any).ipcRenderer) {
          try {
            (window as any).ipcRenderer.send('oauth-result', { success: false, error: errorMsg });
          } catch (e) {
            console.error('无法发送 OAuth 错误到主进程:', e);
          }
        } else {
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
        return;
      }

      if (!code) {
        const errorMsg = 'No authorization code received';
        setError(errorMsg);
        setLoading(false);
        
        // 如果是 Electron OAuth 窗口，通过 IPC 发送错误
        if (isElectron() && (window as any).ipcRenderer) {
          try {
            (window as any).ipcRenderer.send('oauth-result', { success: false, error: errorMsg });
          } catch (e) {
            console.error('无法发送 OAuth 错误到主进程:', e);
          }
        } else {
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
        return;
      }

      try {
        console.log('🔐 AuthCallback: 开始处理 OAuth code');
        const session = await handleOAuthCallback(code, state || undefined);
        console.log('🔐 AuthCallback: OAuth 回调处理成功');
        
        // 处理完 OAuth 回调后，调用后端 API 设置 session cookie
        try {
          console.log('🔐 AuthCallback: 调用后端 API 设置 session cookie');
          const { API_BASE_URL } = await import('./lib/api');
          const accessToken = session?.access_token || (typeof session === 'string' ? session : null);
          
          if (accessToken) {
            const response = await fetch(`${API_BASE_URL}/api/auth/set-session`, {
              method: 'POST',
              credentials: 'include', // 携带 Cookie
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                access_token: accessToken,
              }),
            });
            
            if (response.ok) {
              console.log('🔐 AuthCallback: 后端 session cookie 设置成功');
            } else {
              console.warn('🔐 AuthCallback: 后端 session cookie 设置失败，但继续流程');
            }
          }
        } catch (e) {
          console.error('🔐 AuthCallback: 设置 session cookie 失败:', e);
          // 继续流程，即使设置 cookie 失败
        }
        
        // 如果是 Electron OAuth 窗口，通过 IPC 发送成功结果
        if (isElectron() && (window as any).ipcRenderer) {
          try {
            console.log('🔐 AuthCallback: 通过 IPC 发送 OAuth 结果到主进程');
            // 通过 IPC 发送成功结果
            (window as any).ipcRenderer.send('oauth-result', { 
              success: true, 
              code, 
              state: state || undefined 
            });
            console.log('🔐 AuthCallback: IPC 消息已发送');
            // 显示成功消息
            setLoading(false);
            setError(''); // 清除错误
            return; // 不导航，让 Electron 主进程处理
          } catch (e) {
            console.error('🔐 AuthCallback: 无法发送 OAuth 结果到主进程:', e);
            // 降级到正常流程
          }
        }
        
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
        const errorMsg = err.message || 'Failed to complete authentication';
        setError(errorMsg);
        setLoading(false);
        
        // 如果是 Electron OAuth 窗口，通过 IPC 发送错误
        if (isElectron() && (window as any).ipcRenderer) {
          try {
            (window as any).ipcRenderer.send('oauth-result', { success: false, error: errorMsg });
          } catch (e) {
            console.error('无法发送 OAuth 错误到主进程:', e);
          }
        } else {
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
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

