const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('aiShot', {
  // 监听截屏事件
  onScreenshotTaken: (callback) => {
    ipcRenderer.on('screenshot-taken', (event, base64Image) => {
      callback(base64Image);
    });
  },

  // 监听发送截图请求
  onSendScreenshotRequest: (callback) => {
    ipcRenderer.on('send-screenshot-request', (event, base64Image) => {
      callback(base64Image);
    });
  },

  // 监听截图错误
  onScreenshotError: (callback) => {
    ipcRenderer.on('screenshot-error', (event, errorMessage) => {
      callback(errorMessage);
    });
  },

  // 手动触发截屏
  captureScreen: () => {
    return ipcRenderer.invoke('capture-screen');
  },

  // 发送到后端
  sendToBackend: (imageBase64) => {
    return ipcRenderer.invoke('send-to-backend', imageBase64);
  },

  // 最小化悬浮窗
  minimizeOverlay: () => {
    ipcRenderer.send('minimize-overlay');
  },

  // 显示悬浮窗
  showOverlay: () => {
    ipcRenderer.send('show-overlay');
  },

  // 调整悬浮窗大小
  resizeOverlay: (height) => {
    ipcRenderer.send('resize-overlay', height);
  },

  // 移动悬浮窗 (前端触发)
  moveOverlay: (direction, step) => {
    ipcRenderer.send('move-overlay', { direction, step });
  },

  // 控制点击穿透
  setIgnoreMouseEvents: (ignore) => {
    ipcRenderer.send('set-ignore-mouse-events', ignore);
  },

  // 打开主窗口
  openMainWindow: () => {
    ipcRenderer.send('open-main-window');
  },

  // Google OAuth 登录
  loginWithGoogle: () => {
    return ipcRenderer.invoke('oauth-google');
  },

  // 监听滚动请求
  onScrollContent: (callback) => {
    ipcRenderer.on('scroll-content', (event, direction) => {
      callback(direction);
    });
  },

  // 移除事件监听器
  removeListener: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },

  // 🔒 用户登录/登出事件
  userLoggedIn: () => {
    return ipcRenderer.invoke('user-logged-in');
  },

  userLoggedOut: () => {
    return ipcRenderer.invoke('user-logged-out');
  },

  // 🎤 本地语音转文字（使用本地 Whisper）
  speechToTextLocal: (audioData, language = 'zh') => {
    return ipcRenderer.invoke('speech-to-text-local', audioData, language);
  },

  // 🎯 场景相关 IPC
  getAllScenes: () => {
    return ipcRenderer.invoke('get-all-scenes');
  },

  selectScenario: (sceneId, presetId) => {
    return ipcRenderer.invoke('select-scenario', { sceneId, presetId });
  },

  notifyScenarioUpdated: () => {
    ipcRenderer.send('scenario-updated');
  },

  // 监听场景选择事件
  onScenarioSelected: (callback) => {
    ipcRenderer.on('scenario-selected', (event, data) => {
      callback(data);
    });
  },

  // 监听打开场景编辑器事件
  onOpenScenarioEditor: (callback) => {
    ipcRenderer.on('open-scenario-editor', (event, data) => {
      callback(data);
    });
  },

  // 📁 选择文件夹
  selectFolder: (options) => {
    return ipcRenderer.invoke('select-folder', options);
  },

  // ⚠️ 显示 Token 使用率警告
  showTokenWarning: (message, usagePercentage) => {
    ipcRenderer.send('show-token-warning', message, usagePercentage);
  },

  // 🔐 OAuth 结果（用于 OAuth 窗口）
  sendOAuthResult: (result) => {
    ipcRenderer.send('oauth-result', result);
  },

  // 🔄 监听登录状态刷新事件
  onAuthRefresh: (callback) => {
    console.log('[preload] 注册 auth:refresh 监听');
    // 注意：不移除旧监听器，避免 React StrictMode 下 cleanup 导致监听器被删除
    // 即使重复注册，也只是会触发多次回调，不会导致监听器丢失
    ipcRenderer.on('auth:refresh', () => {
      console.log('[preload] 收到 auth:refresh 事件，调用回调');
      try {
        callback();
      } catch (e) {
        console.error('[preload] auth:refresh 回调异常：', e);
      }
    });
  },

  // 移除事件监听器（暂时禁用，避免 React StrictMode 下 cleanup 导致监听器丢失）
  removeAuthRefreshListener: () => {
    console.log('[preload] removeAuthRefreshListener 调用（暂时不做任何事情，避免 StrictMode 下监听器丢失）');
    // 暂时不执行 removeAllListeners，避免 React StrictMode 下 cleanup 导致监听器被删除
    // ipcRenderer.removeAllListeners('auth:refresh');
  }
});

// 暴露 ipcRenderer 给 OAuth 窗口使用（仅用于发送 OAuth 结果）
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

