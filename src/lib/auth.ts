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
  clearToken();
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
      // No auth header
      return null;
    }

    // Calling API to get current user
    const response = await fetch(`${API_BASE_URL}/api/me`, {
      headers: {
        'Authorization': authHeader,
      },
    });

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
 */
export const isAuthenticated = async (): Promise<boolean> => {
  const token = getToken();
  if (!token) {
    // No token found
    return false;
  }

  // 验证 token 是否有效
  try {
    const user = await getCurrentUser();
    const authenticated = user !== null;
    // Authentication check completed
    return authenticated;
  } catch (error) {
    console.error('🔒 isAuthenticated error:', error);
    return false;
  }
};

/**
 * 获取 Google OAuth 授权 URL
 */
export const getGoogleOAuthUrl = async (redirectTo?: string): Promise<string> => {
  const params = new URLSearchParams();
  if (redirectTo) {
    params.append('redirect_to', redirectTo);
  }
  
  const response = await fetch(`${API_BASE_URL}/api/auth/google/url?${params.toString()}`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to get Google OAuth URL' }));
    throw new Error(error.detail || 'Failed to get Google OAuth URL');
  }
  
  const data = await response.json();
  return data.url;
};

/**
 * 使用 Google OAuth 登录
 */
export const loginWithGoogle = async (): Promise<void> => {
  try {
    // 检查是否是 Electron 环境
    if (typeof window !== 'undefined' && (window as any).aiShot?.loginWithGoogle) {
      // Electron 环境：使用 Electron OAuth 窗口
      const result = await (window as any).aiShot.loginWithGoogle();
      if (result.success && result.code) {
        // 使用 code 和 state 交换 token
        const token = await handleOAuthCallback(result.code, result.state);
        // 触发认证状态变化事件
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        // 重定向到主页面
        window.location.href = '/';
        return;
      } else {
        throw new Error(result.error || 'Failed to get OAuth code from Electron');
      }
    } else {
      // Web 环境：跳转到 Google 授权页面
      const redirectTo = window.location.origin;
      const authUrl = await getGoogleOAuthUrl(redirectTo);
      // 跳转到 Google 授权页面
      window.location.href = authUrl;
    }
  } catch (error: any) {
    console.error('Google OAuth error:', error);
    throw new Error(error.message || 'Failed to initiate Google login');
  }
};

/**
 * 处理 OAuth 回调
 */
export const handleOAuthCallback = async (code: string, state?: string): Promise<AuthToken> => {
  const params = new URLSearchParams({ code });
  if (state) {
    params.append('state', state);
  }
  
  const response = await fetch(`${API_BASE_URL}/api/auth/callback?${params.toString()}`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'OAuth callback failed' }));
    throw new Error(error.detail || 'OAuth callback failed');
  }
  
  const token: AuthToken = await response.json();
  saveToken(token);
  return token;
};

