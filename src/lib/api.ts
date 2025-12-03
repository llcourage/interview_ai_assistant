/**
 * API 配置
 * 所有应用统一使用 Vercel API
 */
import { isElectron } from '../utils/isElectron';

// 默认 Vercel API URL（所有应用统一使用）
const DEFAULT_VERCEL_API_URL = 'https://www.desktopai.org';

export const getApiBaseUrl = (): string => {
  // 如果设置了环境变量，优先使用
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // 开发环境：可以使用本地服务器或 Vercel
  if (import.meta.env.DEV) {
    // 开发时可以设置环境变量切换到本地，否则默认使用 Vercel
    return DEFAULT_VERCEL_API_URL;
  }
  
  // 生产环境：网页版使用当前域名，Electron 使用 Vercel URL
  if (import.meta.env.MODE === 'production') {
    // 如果是 Electron 客户端，使用 Vercel URL
    if (isElectron()) {
      return DEFAULT_VERCEL_API_URL;
    }
    // 网页版使用当前域名（如果部署在 Vercel，会自动使用 Vercel 域名）
    return window.location.origin;
  }
  
  // 默认使用 Vercel URL
  return DEFAULT_VERCEL_API_URL;
};

export const API_BASE_URL = getApiBaseUrl();


