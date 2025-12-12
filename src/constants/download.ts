/**
 * Download configuration
 * Update this file when releasing new versions
 */

export const DOWNLOAD_CONFIG = {
  windows: {
    url: 'https://apps.microsoft.com/detail/9n1t252cwfn6?hl=en-us&gl=US&ocid=pdpshare',
    version: '1.0.0',
    platform: 'Windows',
    filename: 'Desktop AI Setup 1.0.0.exe'
  },
  windowsStore: {
    url: 'https://apps.microsoft.com/detail/9n1t252cwfn6?hl=en-us&gl=US&ocid=pdpshare',
    version: '1.0.0',
    platform: 'Windows Store'
  },
  mac: {
    url: '#',
    version: 'Coming Soon',
    platform: 'macOS'
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

