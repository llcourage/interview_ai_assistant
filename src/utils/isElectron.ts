/**
 * Detect if running in Electron desktop client
 */
export const isElectron = (): boolean => {
  // Electron environment will have window.aiShot object
  return typeof window !== 'undefined' && window.aiShot !== undefined;
};

/**
 * Detect if running in web browser
 */
export const isWebBrowser = (): boolean => {
  return !isElectron();
};

