/**
 * API 配置
 * Desktop version: All API requests go to Vercel backend
 * Web version: Uses current origin (Vercel) or Vercel API URL
 */
import { isElectron } from '../utils/isElectron';

// Vercel API URL (used by Desktop version and as fallback)
const DEFAULT_VERCEL_API_URL = 'https://www.desktopai.org';

export const getApiBaseUrl = (): string => {
  // If environment variable is set, use it (highest priority)
  if (import.meta.env.VITE_API_URL) {
    console.log('🔧 API_BASE_URL: Using VITE_API_URL from env:', import.meta.env.VITE_API_URL);
    return import.meta.env.VITE_API_URL;
  }
  
  // Production mode
  if (import.meta.env.MODE === 'production') {
    // Electron desktop version: always use Vercel API
    if (isElectron()) {
      console.log('🔧 API_BASE_URL: Production Electron, using Vercel:', DEFAULT_VERCEL_API_URL);
      return DEFAULT_VERCEL_API_URL;
    }
    // Web version: use current origin (if deployed on Vercel, will use Vercel domain)
    const origin = window.location.origin;
    console.log('🔧 API_BASE_URL: Production Web, using origin:', origin);
    return origin;
  }
  
  // Development mode: use Vercel API (can be overridden with VITE_API_URL)
  console.log('🔧 API_BASE_URL: DEV mode, using Vercel:', DEFAULT_VERCEL_API_URL);
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



