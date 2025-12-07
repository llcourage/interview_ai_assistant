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
      console.log('🔐 AuthCallback: window.location.search:', window.location.search);
      console.log('🔐 AuthCallback: window.location.hash:', window.location.hash);
      
      // For Electron with HashRouter: if we're at /auth/callback (path route from Supabase),
      // convert it to hash route #/auth/callback
      if (isElectron() && window.location.pathname === '/auth/callback' && !window.location.hash.includes('/auth/callback')) {
        const search = window.location.search;
        const hash = `#/auth/callback${search}`;
        console.log('🔐 AuthCallback: Converting path route to hash route:', window.location.pathname + search, '->', hash);
        window.location.hash = hash;
        // Wait a bit for hash change to take effect
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // 对于 Web 环境（BrowserRouter），参数在 search 中
      // 对于 Electron 环境（HashRouter），参数可能在 hash 中
      // Supabase OAuth 回调可能返回 access_token 在 hash 中（URL hash 模式）
      let code: string | null = null;
      let state: string | null = null;
      let errorParam: string | null = null;
      let oauthUrl: string | null = null;
      let accessToken: string | null = null;
      let refreshToken: string | null = null;
      
      // 首先检查 hash 中是否有 access_token（Supabase URL hash 回调模式）
      if (window.location.hash) {
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        accessToken = hashParams.get('access_token');
        refreshToken = hashParams.get('refresh_token');
        if (accessToken) {
          console.log('🔐 AuthCallback: 检测到 URL hash 中的 access_token（Supabase 直接回调模式）');
        }
      }
      
      if (isElectron()) {
        // Electron 使用 HashRouter，参数在 hash 中
        // hash 格式可能是: #/auth/callback?code=xxx&state=yyy
        const hashMatch = window.location.hash.match(/\?([^#]+)/);
        if (hashMatch) {
          const hashParams = new URLSearchParams(hashMatch[1]);
          if (!code) code = hashParams.get('code');
          if (!state) state = hashParams.get('state');
          if (!errorParam) errorParam = hashParams.get('error');
          if (!oauthUrl) oauthUrl = hashParams.get('oauth_url');
        }
        // 也尝试从 searchParams 获取（如果 React Router 已经解析了）
        if (!code) code = searchParams.get('code');
        if (!state) state = searchParams.get('state');
        if (!errorParam) errorParam = searchParams.get('error');
        if (!oauthUrl) oauthUrl = searchParams.get('oauth_url');
      } else {
        // Web 使用 BrowserRouter，参数在 search 中
        if (!code) code = searchParams.get('code');
        if (!state) state = searchParams.get('state');
        if (!errorParam) errorParam = searchParams.get('error');
        if (!oauthUrl) oauthUrl = searchParams.get('oauth_url');
      }
      
      console.log('🔐 AuthCallback: URL params:', {
        oauth_url: oauthUrl ? 'present' : 'missing',
        code: code ? 'present' : 'missing',
        state: state ? 'present' : 'missing',
        error: errorParam ? 'present' : 'missing',
        isElectron: isElectron()
      });
      
      // 检查是否是 Electron OAuth 窗口（有 oauth_url 参数）
      if (oauthUrl && isElectron()) {
        // Electron OAuth 窗口：跳转到 OAuth URL
        console.log('🔐 Electron OAuth 窗口：检测到 oauth_url 参数，跳转到 OAuth URL');
        console.log('🔐 OAuth URL:', oauthUrl.substring(0, 100) + '...');
        
        // 保存 Supabase 配置到 localStorage（如果 API 返回了的话）
        // 这些配置会在 handleOAuthCallback 中使用
        // 对于 Electron，参数可能在 hash 中
        let supabaseUrl: string | null = null;
        let supabaseAnonKey: string | null = null;
        if (isElectron()) {
          const hashMatch = window.location.hash.match(/\?([^#]+)/);
          if (hashMatch) {
            const hashParams = new URLSearchParams(hashMatch[1]);
            supabaseUrl = hashParams.get('supabase_url');
            supabaseAnonKey = hashParams.get('supabase_anon_key');
          }
        }
        if (!supabaseUrl) supabaseUrl = searchParams.get('supabase_url');
        if (!supabaseAnonKey) supabaseAnonKey = searchParams.get('supabase_anon_key');
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

      // code, state, errorParam 已经在上面获取了

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

      // 如果 hash 中有 access_token，直接使用（Supabase URL hash 回调模式）
      if (accessToken) {
        console.log('🔐 AuthCallback: 使用 URL hash 中的 access_token');
        try {
          // 直接使用 access_token 创建 session
          const session = {
            access_token: accessToken,
            refresh_token: refreshToken || '',
            token_type: 'bearer',
            user: null as any // 稍后从 token 中解析
          };
          
          // 解析 JWT token 获取用户信息
          try {
            const payload = JSON.parse(atob(accessToken.split('.')[1]));
            session.user = {
              id: payload.sub,
              email: payload.email || ''
            };
          } catch (e) {
            console.warn('无法解析 JWT token，稍后从 API 获取用户信息');
          }
          
          // 保存 token
          const { saveToken } = await import('./lib/auth');
          saveToken(session);
          
          // 调用后端 API 设置 session cookie
          try {
            console.log('🔐 AuthCallback: 调用后端 API 设置 session cookie');
            const { API_BASE_URL } = await import('./lib/api');
            const response = await fetch(`${API_BASE_URL}/api/auth/set-session`, {
              method: 'POST',
              credentials: 'include',
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
          } catch (e) {
            console.error('🔐 AuthCallback: 设置 session cookie 失败:', e);
          }
          
          // 触发认证状态变化事件
          window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
          
          // 检查是否有待处理的 plan 和 redirect
          const pendingPlan = localStorage.getItem('pendingPlan');
          const pendingRedirect = localStorage.getItem('pendingRedirect');

          if (pendingPlan && pendingRedirect) {
            localStorage.removeItem('pendingPlan');
            localStorage.removeItem('pendingRedirect');
            navigate(`${pendingRedirect}?plan=${pendingPlan}`);
          } else {
            if (isElectron()) {
              navigate('/app');
            } else {
              navigate('/profile');
            }
          }
          return;
        } catch (err: any) {
          console.error('处理 access_token 失败:', err);
          setError(err.message || 'Failed to process authentication');
          setLoading(false);
          setTimeout(() => {
            navigate('/login');
          }, 3000);
          return;
        }
      }
      
      if (!code) {
        const errorMsg = 'No authorization code or access_token received';
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
        console.log('🔐 AuthCallback: code length:', code ? code.length : 0);
        console.log('🔐 AuthCallback: state:', state || 'N/A');
        
        const session = await handleOAuthCallback(code, state || undefined);
        console.log('🔐 AuthCallback: OAuth 回调处理成功');
        console.log('🔐 AuthCallback: session access_token length:', session?.access_token ? session.access_token.length : 0);
        console.log('🔐 AuthCallback: session user:', session?.user?.email || 'N/A');
        
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
        if (isElectron()) {
          try {
            console.log('🔐 AuthCallback: 检测到 Electron 环境，准备通过 IPC 发送 OAuth 结果');
            console.log('🔐 AuthCallback: code length:', code ? code.length : 0);
            console.log('🔐 AuthCallback: state:', state || 'N/A');
            
            // 尝试多种方式发送 OAuth 结果
            const oauthResult = { 
              success: true, 
              code, 
              state: state || undefined 
            };
            console.log('🔐 AuthCallback: 准备发送 oauth-result 消息:', JSON.stringify({
              success: oauthResult.success,
              hasCode: !!oauthResult.code,
              hasState: !!oauthResult.state
            }));
            
            // 方法 1: 使用 aiShot.sendOAuthResult（如果可用）
            if ((window as any).aiShot?.sendOAuthResult) {
              console.log('🔐 AuthCallback: 使用 aiShot.sendOAuthResult');
              (window as any).aiShot.sendOAuthResult(oauthResult);
            }
            // 方法 2: 直接使用 ipcRenderer（如果暴露）
            else if ((window as any).ipcRenderer) {
              console.log('🔐 AuthCallback: 使用 ipcRenderer.send');
              (window as any).ipcRenderer.send('oauth-result', oauthResult);
            }
            // 方法 3: 尝试通过 window.postMessage（降级方案）
            else {
              console.warn('🔐 AuthCallback: 无法找到 IPC 方法，尝试 postMessage');
              window.postMessage({ type: 'oauth-result', ...oauthResult }, '*');
            }
            
            console.log('🔐 AuthCallback: IPC 消息已发送，等待主进程处理');
            
            // 显示成功消息
            setLoading(false);
            setError(''); // 清除错误
            return; // 不导航，让 Electron 主进程处理
          } catch (e: any) {
            console.error('🔐 AuthCallback: 无法发送 OAuth 结果到主进程:', e);
            console.error('🔐 AuthCallback: 错误详情:', e?.message || String(e), e?.stack);
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

