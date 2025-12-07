const { contextBridge, ipcRenderer } = require('electron');

// Expose safe API to renderer process
contextBridge.exposeInMainWorld('aiShot', {
  // Listen to screenshot event
  onScreenshotTaken: (callback) => {
    ipcRenderer.on('screenshot-taken', (event, base64Image) => {
      callback(base64Image);
    });
  },

  // Listen to send screenshot request
  onSendScreenshotRequest: (callback) => {
    ipcRenderer.on('send-screenshot-request', (event, base64Image) => {
      callback(base64Image);
    });
  },

  // Listen to screenshot error
  onScreenshotError: (callback) => {
    ipcRenderer.on('screenshot-error', (event, errorMessage) => {
      callback(errorMessage);
    });
  },

  // Manually trigger screenshot
  captureScreen: () => {
    return ipcRenderer.invoke('capture-screen');
  },

  // Send to backend
  sendToBackend: (imageBase64) => {
    return ipcRenderer.invoke('send-to-backend', imageBase64);
  },

  // Minimize overlay window
  minimizeOverlay: () => {
    ipcRenderer.send('minimize-overlay');
  },

  // Show overlay window
  showOverlay: () => {
    ipcRenderer.send('show-overlay');
  },

  // Resize overlay window
  resizeOverlay: (height) => {
    ipcRenderer.send('resize-overlay', height);
  },

  // Move overlay window (triggered by frontend)
  moveOverlay: (direction, step) => {
    ipcRenderer.send('move-overlay', { direction, step });
  },

  // Control click-through
  setIgnoreMouseEvents: (ignore) => {
    ipcRenderer.send('set-ignore-mouse-events', ignore);
  },

  // Open main window
  openMainWindow: () => {
    ipcRenderer.send('open-main-window');
  },

  // Google OAuth login
  loginWithGoogle: () => {
    return ipcRenderer.invoke('oauth-google');
  },

  // Listen to scroll request
  onScrollContent: (callback) => {
    ipcRenderer.on('scroll-content', (event, direction) => {
      callback(direction);
    });
  },

  // Remove event listener
  removeListener: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },

  // 🔒 User login/logout events
  userLoggedIn: () => {
    return ipcRenderer.invoke('user-logged-in');
  },

  userLoggedOut: () => {
    return ipcRenderer.invoke('user-logged-out');
  },

  // 🎤 Local speech-to-text (using local Whisper)
  speechToTextLocal: (audioData, language = 'zh') => {
    return ipcRenderer.invoke('speech-to-text-local', audioData, language);
  },

  // 🎯 Scene-related IPC
  getAllScenes: () => {
    return ipcRenderer.invoke('get-all-scenes');
  },

  selectScenario: (sceneId, presetId) => {
    return ipcRenderer.invoke('select-scenario', { sceneId, presetId });
  },

  notifyScenarioUpdated: () => {
    ipcRenderer.send('scenario-updated');
  },

  // Listen to scenario selection event
  onScenarioSelected: (callback) => {
    ipcRenderer.on('scenario-selected', (event, data) => {
      callback(data);
    });
  },

  // Listen to open scenario editor event
  onOpenScenarioEditor: (callback) => {
    ipcRenderer.on('open-scenario-editor', (event, data) => {
      callback(data);
    });
  },

  // 📁 Select folder
  selectFolder: (options) => {
    return ipcRenderer.invoke('select-folder', options);
  },

  // ⚠️ Show Token usage warning
  showTokenWarning: (message, usagePercentage) => {
    ipcRenderer.send('show-token-warning', message, usagePercentage);
  },

  // 🔐 OAuth result (for OAuth window)
  sendOAuthResult: (result) => {
    ipcRenderer.send('oauth-result', result);
  },

  // 🔄 Listen to login status refresh event
  onAuthRefresh: (callback) => {
    console.log('[preload] Registering auth:refresh listener');
    // Note: Don't remove old listeners to avoid React StrictMode cleanup deleting listeners
    // Even if registered multiple times, it will only trigger callbacks multiple times, won't cause listener loss
    ipcRenderer.on('auth:refresh', () => {
      console.log('[preload] Received auth:refresh event, calling callback');
      try {
        callback();
      } catch (e) {
        console.error('[preload] auth:refresh callback exception:', e);
      }
    });
  },

  // Remove event listener (temporarily disabled to avoid React StrictMode cleanup causing listener loss)
  removeAuthRefreshListener: () => {
    console.log('[preload] removeAuthRefreshListener called (temporarily doing nothing to avoid listener loss in StrictMode)');
    // Temporarily don't execute removeAllListeners to avoid React StrictMode cleanup deleting listeners
    // ipcRenderer.removeAllListeners('auth:refresh');
  }
});

// Expose ipcRenderer for OAuth window use (only for sending OAuth result)
if (window.location.hash.includes('auth/callback') || window.location.search.includes('oauth_url')) {
  contextBridge.exposeInMainWorld('ipcRenderer', {
    send: (channel, data) => {
      if (channel === 'oauth-result') {
        ipcRenderer.send('oauth-result', data);
      }
    }
  });
}

console.log('Preload script loaded');

