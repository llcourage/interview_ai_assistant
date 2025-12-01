/**
 * API 配置
 * 根据环境自动选择 API URL
 */
export const getApiBaseUrl = (): string => {
  // 开发环境
  if (import.meta.env.DEV) {
    return import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  }
  
  // 生产环境
  if (import.meta.env.MODE === 'production') {
    return import.meta.env.VITE_API_URL || window.location.origin;
  }
  
  // 默认
  return import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
};

export const API_BASE_URL = getApiBaseUrl();

