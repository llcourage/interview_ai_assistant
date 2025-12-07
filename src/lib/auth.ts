/**
 * 认证工具 - 通过 Vercel API 进行认证，不直接连接 Supabase
 */
import { API_BASE_URL } from './api';

export interface AuthToken {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user?: {
    id: string;
    email: string;
  };
}

export interface User {
  id: string;
  email: string;
}

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

/**
 * 保存认证 token
 */
export const saveToken = (token: AuthToken): void => {
  localStorage.setItem(TOKEN_KEY, JSON.stringify(token));
};

/**
 * 获取认证 token
 */
export const getToken = (): AuthToken | null => {
  const tokenStr = localStorage.getItem(TOKEN_KEY);
  if (!tokenStr) return null;
  try {
    return JSON.parse(tokenStr);
  } catch {
    return null;
  }
};

/**
 * 清除认证 token
 */
export const clearToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

/**
 * 获取 Authorization header
 */
export const getAuthHeader = (): string | null => {
  const token = getToken();
  if (!token) return null;
  // 确保 token_type 格式正确（HTTP 标准要求首字母大写）
  const tokenType = token.token_type 
    ? token.token_type.charAt(0).toUpperCase() + token.token_type.slice(1).toLowerCase()
    : 'Bearer';
  return `${tokenType} ${token.access_token}`;
};

/**
 * 用户注册
 */
export const register = async (email: string, password: string): Promise<AuthToken> => {
  const response = await fetch(`${API_BASE_URL}/api/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(error.detail || 'Registration failed');
  }

  const token: AuthToken = await response.json();
  saveToken(token);
  return token;
};

/**
 * 用户登录
 */
export const login = async (email: string, password: string): Promise<AuthToken> => {
  const response = await fetch(`${API_BASE_URL}/api/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  const token: AuthToken = await response.json();
  saveToken(token);
  return token;
};

/**
 * 用户登出
 */
export const logout = async (): Promise<void> => {
  // 清除本地 token
  clearToken();
  
  // 尝试清除服务器端的 session cookie
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include', // 携带 Cookie
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (response.ok) {
      console.log('✅ 服务器 session cookie 已清除');
    } else {
      console.warn('⚠️ 清除服务器 session cookie 失败，但继续登出流程');
    }
  } catch (error) {
    console.warn('⚠️ 清除服务器 session cookie 时出错，但继续登出流程:', error);
    // 即使清除服务器 cookie 失败，也继续登出流程
  }
  
  // 触发认证状态变化事件，通知其他组件
  window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: false } }));
  
  console.log('🚪 用户已登出');
};

/**
 * 获取当前用户信息
 */
export const getCurrentUser = async (): Promise<User | null> => {
  const token = getToken();
  if (!token) {
    // No token found
    return null;
  }

  try {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      console.log('🔒 getCurrentUser: 无 auth header');
      return null;
    }

    // Calling API to get current user
    // 注意：在开发环境中，需要 credentials: 'include' 来携带 Cookie
    const apiUrl = `${API_BASE_URL}/api/me`;
    console.log('🌐 getCurrentUser: 请求 API:', apiUrl);
    console.log('🌐 getCurrentUser: 请求头:', { 
      'Authorization': authHeader.substring(0, 20) + '...',
      'credentials': 'include'
    });
    
    const response = await fetch(apiUrl, {
      credentials: 'include', // 携带 Cookie（用于跨域请求）
      headers: {
        'Authorization': authHeader,
      },
    });

    console.log('🌐 getCurrentUser: 响应状态:', response.status, response.statusText);

    if (!response.ok) {
      console.error('🔒 getCurrentUser: API error', response.status, response.statusText);
      // Token 可能已过期
      if (response.status === 401) {
        // 401 Unauthorized, clearing token
        clearToken();
      }
      return null;
    }

    const user: User = await response.json();
    // User authenticated successfully
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  } catch (error) {
    console.error('🔒 getCurrentUser: Exception', error);
    return null;
  }
};

/**
 * 检查是否已登录
 * 优先检查 localStorage 中的 token，如果没有则检查服务器 Cookie 会话
 */
export const isAuthenticated = async (): Promise<boolean> => {
  console.log('🔑 isAuthenticated: 开始检查登录状态');
  
  // 1. 先检查 localStorage 中的 token（支持 Web 端的 token 登录）
  const token = getToken();
  if (token) {
    console.log('🔑 isAuthenticated: 找到 token，验证 token 有效性');
  try {
    const user = await getCurrentUser();
    const authenticated = user !== null;
      console.log('🔑 isAuthenticated: Token 验证完成，结果:', authenticated, user ? `用户: ${user.email}` : '无用户');
      return authenticated;
    } catch (error) {
      console.error('🔑 isAuthenticated: Token 验证失败:', error);
      // Token 无效，继续检查服务器会话
    }
  }
  
  // 2. 没有 token 或 token 无效，检查服务器 Cookie 会话（Electron OAuth 流程）
  console.log('🔑 isAuthenticated: 未找到有效 token，调用 /api/me 检查服务器会话');
  try {
    // 尝试获取 token（即使之前验证失败，也可能有无效的 token）
    const token = getToken();
    const authHeader = token ? getAuthHeader() : null;
    
    // 检查是否是 Electron 环境
    const isElectronEnv = typeof window !== 'undefined' && (window as any).aiShot !== undefined;
    
    // 构建请求头
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    // 对于 Electron 应用，优先使用 Authorization header（因为 Cookie 可能无法正确工作）
    // 对于 Web 应用，同时发送 Cookie 和 Authorization header（双重保险）
    if (authHeader) {
      headers['Authorization'] = authHeader;
      if (isElectronEnv) {
        console.log('🔑 isAuthenticated: Electron 环境，优先使用 Authorization header');
      } else {
        console.log('🔑 isAuthenticated: 同时发送 Cookie 和 Authorization header');
      }
    } else {
      if (isElectronEnv) {
        console.log('🔑 isAuthenticated: Electron 环境，无 token，仅尝试 Cookie');
      } else {
        console.log('🔑 isAuthenticated: 仅发送 Cookie（无 Authorization header）');
      }
    }
    
    // 直接调用 API 检查服务器会话，使用 credentials: 'include' 携带 Cookie
    const response = await fetch(`${API_BASE_URL}/api/me`, {
      credentials: 'include', // 携带 Cookie（用于跨域请求）
      headers,
    });
    
    console.log('🌐 isAuthenticated: /api/me 响应状态:', response.status, response.statusText);
    
    if (response.ok) {
      const user = await response.json();
      console.log('🔑 isAuthenticated: 服务器返回已登录用户:', user.email || user.id);
      
      // 如果服务器返回用户信息，保存到 localStorage（可选，用于后续请求）
      if (user && user.id) {
        // 注意：这里不保存完整的 token，因为服务器使用 Cookie 管理会话
        // 但可以保存用户信息
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      }
      
      return true;
    } else {
      console.log('🔑 isAuthenticated: 服务器会话检查失败，状态码:', response.status);
      if (response.status === 401) {
        // 401 Unauthorized，清除可能存在的无效 token
        clearToken();
      }
      return false;
    }
  } catch (error) {
    console.error('🔑 isAuthenticated: 服务器会话检查异常:', error);
    return false;
  }
};

/**
 * 获取 Google OAuth 授权 URL
 * 同时获取 Supabase 配置（用于 OAuth 回调）
 */
export const getGoogleOAuthUrl = async (redirectTo?: string): Promise<{ url: string; supabaseUrl?: string; supabaseAnonKey?: string }> => {
  const params = new URLSearchParams();
  if (redirectTo) {
    params.append('redirect_to', redirectTo);
  }
  
  const response = await fetch(`${API_BASE_URL}/api/auth/google/url?${params.toString()}`);
  
  if (!response.ok) {
    let errorMessage = 'Failed to get Google OAuth URL';
    try {
      const error = await response.json();
      // 处理不同的错误格式
      if (error.detail) {
        errorMessage = error.detail;
      } else if (error.msg) {
        errorMessage = error.msg;
      } else if (error.message) {
        errorMessage = error.message;
      } else if (error.error) {
        errorMessage = error.error;
      }
      console.error('Google OAuth URL 错误:', {
        status: response.status,
        statusText: response.statusText,
        error: error,
        apiUrl: `${API_BASE_URL}/api/auth/google/url`
      });
    } catch (e) {
      console.error('解析错误响应失败:', e);
      errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }
  
  const data = await response.json();
  
  // 确保返回的数据包含必要的字段
  if (!data.url) {
    throw new Error('API 返回的数据中缺少 url 字段');
  }
  
  return {
    url: data.url,
    supabaseUrl: data.supabase_url || data.supabaseUrl,
    supabaseAnonKey: data.supabase_anon_key || data.supabaseAnonKey
  };
};

/**
 * 使用 Google OAuth 登录
 */
export const loginWithGoogle = async (): Promise<void> => {
  try {
    // 检查是否是 Electron 环境
    if (typeof window !== 'undefined' && (window as any).aiShot?.loginWithGoogle) {
      // Electron 环境：使用 Electron OAuth 窗口，通过后端 API 处理
      console.log('🔐 Electron environment: Handling OAuth login via Electron IPC');
      
      // Setup IPC listener as backup (in case main process sends token via IPC before promise resolves)
      let ipcTokenReceived = false;
      const ipcHandler = (data: any) => {
        if (ipcTokenReceived) return; // Only handle once
        ipcTokenReceived = true;
        
        console.log('🔐 Electron: Received token via IPC event:', {
          hasAccessToken: !!data.access_token,
          hasRefreshToken: !!data.refresh_token,
          hasUser: !!data.user
        });
        
        // Create token object from IPC data
        const token: AuthToken = {
          access_token: data.access_token,
          refresh_token: data.refresh_token || '',
          token_type: data.token_type || 'bearer',
          user: data.user ? {
            id: data.user.id || '',
            email: data.user.email || ''
          } : undefined
        };
        
        // Save token to localStorage
        console.log('🔐 Electron: Saving token to localStorage (from IPC)');
        saveToken(token);
        
        // Verify token was saved
        const savedToken = getToken();
        if (savedToken) {
          console.log('✅ Electron: Token saved successfully (from IPC), user:', savedToken.user?.email);
        } else {
          console.error('❌ Electron: Token save failed (from IPC)!');
        }
        
        // Trigger auth state change event
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        console.log('🔐 Electron: Triggered auth-state-changed event (from IPC)');
        
        // Force reload to ensure AppRouter re-checks auth status and navigates correctly
        // This simulates "closing and reopening the app" behavior
        console.log('🔐 Electron: Reloading page to refresh auth state (from IPC)');
        setTimeout(() => {
          window.location.reload();
        }, 50);
      };
      
      // Register IPC listener
      if ((window as any).aiShot?.onOAuthComplete) {
        (window as any).aiShot.onOAuthComplete(ipcHandler);
      }
      
      // Call main process loginWithGoogle (this may resolve with token or trigger IPC event)
      console.log('🔐 Electron: Calling main process loginWithGoogle');
      const result = await (window as any).aiShot.loginWithGoogle();
      console.log('🔐 Electron: Received result from main process:', { 
        success: result.success, 
        hasAccessToken: !!result.access_token, 
        hasUser: !!result.user,
        error: result.error 
      });
      
      // If promise already resolved with token data, use it
      if (result.success && result.access_token && !ipcTokenReceived) {
        console.log('🔐 Electron: Received token data from promise result');
        
        // Create token object from result
        const token: AuthToken = {
          access_token: result.access_token,
          refresh_token: result.refresh_token || '',
          token_type: 'bearer',
          user: result.user ? {
            id: result.user.id || '',
            email: result.user.email || ''
          } : undefined
        };
        
        // Save token to localStorage
        console.log('🔐 Electron: Saving token to localStorage (from promise)');
        saveToken(token);
        
        // Verify token was saved
        const savedToken = getToken();
        if (savedToken) {
          console.log('✅ Electron: Token saved successfully (from promise), user:', savedToken.user?.email);
        } else {
          console.error('❌ Electron: Token save failed (from promise)!');
        }
        
        // Trigger auth state change event
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        console.log('🔐 Electron: Triggered auth-state-changed event (from promise)');
        
        // Force reload to ensure AppRouter re-checks auth status and navigates correctly
        // This simulates "closing and reopening the app" behavior
        console.log('🔐 Electron: Reloading page to refresh auth state (from promise)');
        setTimeout(() => {
          window.location.reload();
        }, 50);
        return;
      } else if (!result.success && !ipcTokenReceived) {
        const errorMsg = result.error || 'Failed to get OAuth token from Electron';
        console.error('❌ Electron: OAuth failed:', errorMsg);
        throw new Error(errorMsg);
      }
      // If ipcTokenReceived is true, the IPC handler already handled everything
      return;
    } else {
      // Web 环境：直接使用 Supabase JS SDK 生成 OAuth URL
      // 这样 code_verifier 会保存在浏览器存储中，PKCE 流程才能正常工作
      console.log('🔐 Web 环境：使用 Supabase JS SDK 生成 OAuth URL');
      
      // 先定义 redirectTo（在动态导入之前）
      const redirectTo = `${window.location.origin}/auth/callback`;
      
      // 动态导入 Supabase 客户端
      let createClient: any;
      try {
        const supabaseModule = await import('@supabase/supabase-js');
        createClient = supabaseModule.createClient;
      } catch (importError: any) {
        console.error('🔐 动态导入 Supabase SDK 失败:', importError);
        // 如果动态导入失败，降级到使用后端 API 获取 OAuth URL
        console.log('🔐 降级：使用后端 API 获取 OAuth URL');
        const { url } = await getGoogleOAuthUrl(redirectTo);
        // 直接跳转到后端返回的 OAuth URL
        window.location.href = url;
        return;
      }
      
      // 获取 Supabase 配置
      let supabaseUrl = localStorage.getItem('supabase_url');
      let supabaseAnonKey = localStorage.getItem('supabase_anon_key');
      
      // 如果 localStorage 中没有，从 API 获取
      if (!supabaseUrl || !supabaseAnonKey) {
        try {
          const { API_BASE_URL } = await import('./api');
          const configResponse = await fetch(`${API_BASE_URL}/api/config/supabase`);
          if (configResponse.ok) {
            const config = await configResponse.json();
            supabaseUrl = config.supabase_url;
            supabaseAnonKey = config.supabase_anon_key;
            if (supabaseUrl && supabaseAnonKey) {
              localStorage.setItem('supabase_url', supabaseUrl);
              localStorage.setItem('supabase_anon_key', supabaseAnonKey);
            }
          }
        } catch (e) {
          console.error('🔐 从 API 获取 Supabase 配置失败:', e);
        }
      }
      
      // 如果还是没有，使用环境变量或默认值
      if (!supabaseUrl) {
        supabaseUrl = (import.meta.env as any).VITE_SUPABASE_URL || 'https://cjrblsalpfhugeatrhrr.supabase.co';
      }
      if (!supabaseAnonKey) {
        supabaseAnonKey = (import.meta.env as any).VITE_SUPABASE_ANON_KEY || '';
      }
      
      if (!supabaseAnonKey) {
        throw new Error('Supabase ANON_KEY 未配置。请确保 VITE_SUPABASE_ANON_KEY 环境变量已设置，或 API 返回了配置。');
      }
      
      // 创建 Supabase 客户端
      const supabase = createClient(supabaseUrl, supabaseAnonKey);
      
      // 使用 Supabase JS SDK 生成 OAuth URL（这样 code_verifier 会保存在浏览器存储中）
      console.log('🔐 Web 环境：redirectTo:', redirectTo);
      
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectTo
        }
      });
      
      if (error) {
        throw new Error(error.message || 'Failed to get OAuth URL');
      }
      
      if (!data?.url) {
        throw new Error('Failed to get OAuth URL from Supabase');
      }
      
      console.log('🔐 Web 环境：跳转到 OAuth URL');
      // 跳转到 Google 授权页面
      window.location.href = data.url;
    }
  } catch (error: any) {
    console.error('Google OAuth error:', error);
    throw new Error(error.message || 'Failed to initiate Google login');
  }
};

/**
 * 处理 OAuth 回调
 * Electron 环境：通过后端 API 处理，不直接连接 Supabase
 * Web 环境：使用前端 Supabase 客户端直接处理，避免 PKCE code_verifier 问题
 */
export const handleOAuthCallback = async (code: string, state?: string, codeVerifier?: string): Promise<AuthToken> => {
  // 检查是否是 Electron 环境
  const isElectronEnv = typeof window !== 'undefined' && (window as any).aiShot !== undefined;
  
  if (isElectronEnv) {
    // NEW ARCHITECTURE: Electron OAuth is now handled entirely via backend callback
    // Token is received through postMessage from /api/auth/callback page
    // This function should not be called in Electron environment anymore
    console.error('❌ handleOAuthCallback called in Electron environment - this should not happen');
    console.error('❌ Electron OAuth flow should receive token via postMessage from backend callback page');
    throw new Error('Electron OAuth callback handling has been moved to backend callback endpoint. This function is deprecated for Electron.');
  } else {
    // Web 环境：使用前端 Supabase 客户端直接处理
    console.log('🔐 Web 环境：使用 Supabase JS SDK 处理 OAuth 回调');
    
    // 动态导入 Supabase 客户端
    let createClient: any;
    try {
      const supabaseModule = await import('@supabase/supabase-js');
      createClient = supabaseModule.createClient;
    } catch (importError: any) {
      console.error('🔐 动态导入 Supabase SDK 失败:', importError);
      throw new Error(`无法加载 Supabase SDK: ${importError.message || importError}. 请检查网络连接或刷新页面重试。`);
    }
    
    // 从 localStorage 获取 Supabase 配置（如果之前保存过）
    let supabaseUrl = localStorage.getItem('supabase_url');
    let supabaseAnonKey = localStorage.getItem('supabase_anon_key');
    
    // 如果 localStorage 中没有，尝试从 API 获取
    if (!supabaseUrl || !supabaseAnonKey) {
      try {
        const configResponse = await fetch(`${API_BASE_URL}/api/config/supabase`);
        if (configResponse.ok) {
          const config = await configResponse.json();
          supabaseUrl = config.supabase_url;
          supabaseAnonKey = config.supabase_anon_key;
          // 保存到 localStorage 供下次使用
          if (supabaseUrl && supabaseAnonKey) {
            localStorage.setItem('supabase_url', supabaseUrl);
            localStorage.setItem('supabase_anon_key', supabaseAnonKey);
          }
        }
      } catch (error) {
        console.warn('无法从 API 获取 Supabase 配置，使用环境变量或默认值', error);
      }
    }
    
    // 如果还是没有，使用环境变量或默认值
    if (!supabaseUrl) {
      supabaseUrl = (import.meta.env as any).VITE_SUPABASE_URL || 'https://cjrblsalpfhugeatrhrr.supabase.co';
    }
    
    if (!supabaseAnonKey) {
      supabaseAnonKey = (import.meta.env as any).VITE_SUPABASE_ANON_KEY || '';
    }
    
    if (!supabaseAnonKey) {
      console.error('❌ Supabase 配置获取失败:', {
        fromLocalStorage: !!localStorage.getItem('supabase_anon_key'),
        fromEnv: !!(import.meta.env as any).VITE_SUPABASE_ANON_KEY,
        supabaseUrl,
        supabaseAnonKey: supabaseAnonKey ? '***' : '(empty)'
      });
      throw new Error('Supabase ANON_KEY 未配置。请确保 VITE_SUPABASE_ANON_KEY 环境变量已设置，或 API 返回了配置。');
    }
    
    if (!supabaseUrl) {
      throw new Error('Supabase URL 未配置。');
    }
    
    console.log('✅ 使用 Supabase 配置创建客户端:', {
      url: supabaseUrl,
      keyLength: supabaseAnonKey.length
    });
    
    // 创建 Supabase 客户端（使用动态配置）
    const supabase = createClient(supabaseUrl, supabaseAnonKey);
    
    // 使用 Supabase JS SDK 的 exchangeCodeForSession
    // 这样可以从浏览器存储中自动获取 code_verifier
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);
    
    if (error) {
      console.error('Supabase exchangeCodeForSession error:', error);
      throw new Error(error.message || 'OAuth callback failed');
    }
    
    if (!data.session || !data.user) {
      throw new Error('OAuth callback failed: No session or user data received');
    }
    
    // 转换为我们的 AuthToken 格式
    const token: AuthToken = {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      token_type: 'bearer',
      user: {
        id: data.user.id,
        email: data.user.email || ''
      }
    };
    
    saveToken(token);
    return token;
  }
};

