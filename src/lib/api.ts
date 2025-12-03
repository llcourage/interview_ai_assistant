/**
 * API 配置
 * 支持云端 API 和本地桌面版 API
 */
import { isElectron } from '../utils/isElectron';

// 默认 Vercel API URL（云端）
const DEFAULT_VERCEL_API_URL = 'https://www.desktopai.org';
// 本地桌面版 API URL
const LOCAL_DESKTOP_API_URL = 'http://127.0.0.1:8000';

/**
 * 检测是否为本地桌面版模式
 * 通过检查当前 URL 是否为 127.0.0.1:8000 来判断
 */
const isLocalDesktopMode = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  const hostname = window.location.hostname;
  const port = window.location.port;
  
  // 如果是 127.0.0.1:8000 或 localhost:8000，认为是本地桌面版
  if ((hostname === '127.0.0.1' || hostname === 'localhost') && port === '8000') {
    return true;
  }
  
  // 检查 URL 参数
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mode') === 'desktop' || urlParams.get('local') === 'true') {
    return true;
  }
  
  return false;
};

export const getApiBaseUrl = (): string => {
  // 如果设置了环境变量，优先使用
  if (import.meta.env.VITE_API_URL) {
    console.log('🔧 API_BASE_URL: Using VITE_API_URL from env:', import.meta.env.VITE_API_URL);
    return import.meta.env.VITE_API_URL;
  }
  
  // 检测本地桌面版模式
  if (isLocalDesktopMode()) {
    console.log('🔧 API_BASE_URL: Local Desktop mode detected, using:', LOCAL_DESKTOP_API_URL);
    return LOCAL_DESKTOP_API_URL;
  }
  
  // 开发环境：可以使用本地服务器或 Vercel
  if (import.meta.env.DEV) {
    // 开发时可以设置环境变量切换到本地，否则默认使用 Vercel
    console.log('🔧 API_BASE_URL: DEV mode, using Vercel:', DEFAULT_VERCEL_API_URL);
    return DEFAULT_VERCEL_API_URL;
  }
  
  // 生产环境：网页版使用当前域名，Electron 使用 Vercel URL
  if (import.meta.env.MODE === 'production') {
    // 如果是 Electron 客户端，使用 Vercel URL
    if (isElectron()) {
      console.log('🔧 API_BASE_URL: Production Electron, using Vercel:', DEFAULT_VERCEL_API_URL);
      return DEFAULT_VERCEL_API_URL;
    }
    // 网页版使用当前域名（如果部署在 Vercel，会自动使用 Vercel 域名）
    const origin = window.location.origin;
    console.log('🔧 API_BASE_URL: Production Web, using origin:', origin);
    return origin;
  }
  
  // 默认使用 Vercel URL
  console.log('🔧 API_BASE_URL: Default, using Vercel:', DEFAULT_VERCEL_API_URL);
  return DEFAULT_VERCEL_API_URL;
};

export const API_BASE_URL = getApiBaseUrl();

// 打印最终使用的 API URL（仅一次）
console.log('🌐 API Base URL configured:', API_BASE_URL);
console.log('🌐 Environment:', {
  DEV: import.meta.env.DEV,
  MODE: import.meta.env.MODE,
  VITE_API_URL: import.meta.env.VITE_API_URL,
  isElectron: isElectron(),
  origin: typeof window !== 'undefined' ? window.location.origin : 'N/A'
});



