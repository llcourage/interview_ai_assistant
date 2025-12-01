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

  // 🔑 API Key 相关
  getApiKey: () => {
    return ipcRenderer.invoke('get-api-key');
  },

  saveApiKey: (apiKey) => {
    return ipcRenderer.invoke('save-api-key', apiKey);
  },

  deleteApiKey: () => {
    return ipcRenderer.invoke('delete-api-key');
  },

  // 监听打开 API Key 对话框事件
  onOpenApiKeyDialog: (callback) => {
    ipcRenderer.on('open-api-key-dialog', (event, data) => {
      callback(data);
    });
  },

  // 监听 API Key 删除事件
  onApiKeyDeleted: (callback) => {
    ipcRenderer.on('api-key-deleted', () => {
      callback();
    });
  },

  // 🔒 用户登录/登出事件
  userLoggedIn: () => {
    return ipcRenderer.invoke('user-logged-in');
  },

  userLoggedOut: () => {
    return ipcRenderer.invoke('user-logged-out');
  }
});

console.log('Preload script loaded');

