/**
 * 检测是否运行在 Electron 桌面客户端中
 */
export const isElectron = (): boolean => {
  // Electron 环境中会有 window.aiShot 对象
  return typeof window !== 'undefined' && window.aiShot !== undefined;
};

/**
 * 检测是否运行在网页浏览器中
 */
export const isWebBrowser = (): boolean => {
  return !isElectron();
};

