/**
 * Download configuration
 * Update this file when releasing new versions
 */

export const DOWNLOAD_CONFIG = {
  windows: {
    url: 'https://pub-a61da80dd0b7435fb2f7e5e92999b324.r2.dev/Desktop%20AI%20Setup%201.0.0.exe',
    version: '1.0.0',
    platform: 'Windows',
    filename: 'Desktop AI Setup 1.0.0.exe'
  }
  // Add other platforms here when available
  // mac: { ... },
  // linux: { ... }
};

export const getDownloadUrl = (platform: 'windows' | 'mac' | 'linux' = 'windows'): string => {
  return DOWNLOAD_CONFIG[platform]?.url || DOWNLOAD_CONFIG.windows.url;
};

export const getDownloadVersion = (platform: 'windows' | 'mac' | 'linux' = 'windows'): string => {
  return DOWNLOAD_CONFIG[platform]?.version || DOWNLOAD_CONFIG.windows.version;
};

