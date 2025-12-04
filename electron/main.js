const { app, BrowserWindow, globalShortcut, desktopCapturer, ipcMain, Menu, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { promisify } = require('util');
const writeFile = promisify(fs.writeFile);
const unlink = promisify(fs.unlink);

// 🚨 恢复 GPU 加速（有些系统禁用后反而黑屏）
// app.disableHardwareAcceleration();

let mainWindow = null;
let overlayWindow = null;
let currentScreenshot = null;

const isDev = !app.isPackaged;
// Check if running in desktop mode (backend serves static files on port 8000)
const isDesktopMode = process.env.DESKTOP_MODE === 'true' || process.argv.includes('--desktop-mode');

// API Key management removed - Desktop version forwards all requests to Vercel
// All users use server API keys configured in Vercel

// 🎨 创建现代化菜单
function createMenu() {
  const template = [
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About',
          click: async () => {
            await dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About',
              message: 'AI Interview Assistant',
              detail: 'Version 1.0.0\n\nAn intelligent interview preparation tool'
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    frame: true,
    backgroundColor: '#f5f7fa',
    autoHideMenuBar: false, // 显示菜单栏
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '../resources/icon.png')
  });

  if (isDesktopMode) {
    // Desktop mode: backend serves static files on port 8000
    mainWindow.loadURL('http://127.0.0.1:8000');
  } else if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    // mainWindow.webContents.openDevTools(); // 🚨 关闭开发者工具
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // 🚨 添加错误监听
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    console.error('🚨 主窗口加载失败:', {
      errorCode,
      errorDescription,
      validatedURL
    });
    // 显示错误信息
    mainWindow.webContents.executeJavaScript(`
      document.body.innerHTML = '<div style="padding: 20px; font-family: Arial; text-align: center;">
        <h2>❌ 页面加载失败</h2>
        <p>错误代码: ${errorCode}</p>
        <p>错误描述: ${errorDescription}</p>
        <p>URL: ${validatedURL}</p>
        <p>请检查：</p>
        <ul style="text-align: left; display: inline-block;">
          <li>Vite 开发服务器是否正在运行</li>
          <li>端口是否正确（应该是 5173）</li>
          <li>查看控制台获取更多信息</li>
        </ul>
      </div>';
    `).catch(err => console.error('显示错误信息失败:', err));
  });

  // 🚨 加载完成后显示（避免白屏闪烁）
  mainWindow.once('ready-to-show', () => {
    console.log('主窗口准备就绪，显示窗口');
    mainWindow.show();
    mainWindow.focus();
  });

  // 添加控制台消息监听（用于调试）
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    if (level === 3) { // error level
      console.error('前端错误:', message);
    }
  });

  // 🔗 拦截外部链接，在系统默认浏览器中打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // 检查是否为外部链接
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // 不是 localhost，在系统默认浏览器中打开
      if (!url.includes('localhost') && !url.includes('127.0.0.1')) {
        shell.openExternal(url);
        return { action: 'deny' }; // 阻止在应用内打开
      }
    }
    return { action: 'allow' }; // 允许本地链接在应用内打开
  });

  // 🔗 拦截导航到外部链接
  mainWindow.webContents.on('will-navigate', (event, url) => {
    // 检查是否为外部链接
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // 不是 localhost，在系统默认浏览器中打开
      if (!url.includes('localhost') && !url.includes('127.0.0.1')) {
        event.preventDefault();
        shell.openExternal(url);
      }
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createOverlayWindow() {
  // 获取屏幕尺寸
  const { screen } = require('electron');
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
  
  // 计算窗口尺寸（屏幕的一半宽度，初始高度较小）
  const windowWidth = Math.floor(screenWidth / 2);
  // 🎯 增加最大高度到 80%，以容纳更多内容
  const maxHeight = Math.floor(screenHeight * 0.8);
  const initialHeight = 80; // 初始高度，只显示按钮
  
  overlayWindow = new BrowserWindow({
    width: windowWidth,
    height: initialHeight,
    maxHeight: maxHeight,
    minHeight: initialHeight,
    frame: false,
    transparent: true,
    // 🚨 尝试给一个极其微弱的背景色，而不是完全透明
    // 有时 #00000000 会导致渲染层被忽略
    backgroundColor: '#01000000', 
    alwaysOnTop: true,
    skipTaskbar: false,
    resizable: true,
    focusable: true,
    hasShadow: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    show: false
  });

  // 移除 DevTools
  // overlayWindow.webContents.openDevTools({ mode: 'detach' });

  if (isDesktopMode) {
    // Desktop mode: backend serves static files on port 8000
    overlayWindow.loadURL('http://127.0.0.1:8000/?type=overlay#/overlay');
  } else if (isDev) {
    // 添加 ?type=overlay 参数，确保前端能识别
    overlayWindow.loadURL('http://localhost:5173/?type=overlay#/overlay');
  } else {
    overlayWindow.loadFile(path.join(__dirname, '../dist/index.html'), {
      hash: '/overlay',
      search: 'type=overlay' // 生产环境也加上
    });
  }

  // 设置窗口位置（顶部居中）
  const x = Math.floor((screenWidth - windowWidth) / 2);
  const y = 0; // 置顶
  overlayWindow.setPosition(x, y);
  
  // 不需要再单独设置 opacity，上面已经设置了
  // overlayWindow.setOpacity(1.0);

  overlayWindow.on('closed', () => {
    overlayWindow = null;
  });

  // 🚨 调试：加载失败监听
  overlayWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('🚨 页面加载失败:', errorCode, errorDescription);
  });

  // 🔗 拦截外部链接，在系统默认浏览器中打开
  overlayWindow.webContents.setWindowOpenHandler(({ url }) => {
    // 检查是否为外部链接
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // 不是 localhost，在系统默认浏览器中打开
      if (!url.includes('localhost') && !url.includes('127.0.0.1')) {
        shell.openExternal(url);
        return { action: 'deny' }; // 阻止在应用内打开
      }
    }
    return { action: 'allow' }; // 允许本地链接在应用内打开
  });

  // 🔗 拦截导航到外部链接
  overlayWindow.webContents.on('will-navigate', (event, url) => {
    // 检查是否为外部链接
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // 不是 localhost，在系统默认浏览器中打开
      if (!url.includes('localhost') && !url.includes('127.0.0.1')) {
        event.preventDefault();
        shell.openExternal(url);
      }
    }
  });

  // 🚨 调试：完成加载监听
  overlayWindow.webContents.on('did-finish-load', () => {
    console.log('✅ 页面加载完成');
    
    // 显示窗口
    overlayWindow.show();
    overlayWindow.focus();
    
    // 🚨 初始状态：不穿透，等前端 mousemove 接管后再动态切换
    overlayWindow.setIgnoreMouseEvents(false);
    console.log('✅ 窗口初始设为不穿透，等待前端接管');
  });
}

// 动态调整悬浮窗高度
function resizeOverlayWindow(height) {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    const { screen } = require('electron');
    const primaryDisplay = screen.getPrimaryDisplay();
    const { height: screenHeight } = primaryDisplay.workAreaSize;
    // 🎯 增加最大高度到 80%
    const maxHeight = Math.floor(screenHeight * 0.8);
    
    // 限制最大高度为屏幕高度的 70%
    const newHeight = Math.min(Math.max(height, 80), maxHeight); // 至少 80px
    const currentSize = overlayWindow.getSize();
    const currentWidth = currentSize[0];
    const currentHeight = currentSize[1];
    
    console.log(`调整悬浮窗高度: 当前=${currentHeight}px, 请求=${height}px, 实际=${newHeight}px, 最大=${maxHeight}px`);
    
    // 使用 setBounds 而不是 setSize，更可靠
    const bounds = overlayWindow.getBounds();
    overlayWindow.setBounds({
      x: bounds.x,
      y: bounds.y,
      width: currentWidth,
      height: newHeight
    });
    
    // 强制刷新窗口
    overlayWindow.setSize(currentWidth, newHeight);
  }
}

// 发送消息到所有窗口
function sendToWindows(channel, ...args) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, ...args);
  }
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send(channel, ...args);
  }
}

// 截屏功能
async function captureScreen() {
  try {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: {
        width: 1920,
        height: 1080
      }
    });

    if (sources.length > 0) {
      const image = sources[0].thumbnail.toPNG();
      const base64Image = image.toString('base64');
      
      // 🚨 添加 data URL 前缀，让浏览器能识别
      const dataUrl = `data:image/png;base64,${base64Image}`;
      currentScreenshot = dataUrl;
      
      sendToWindows('screenshot-taken', dataUrl);
      
      // 聚焦悬浮窗
      if (overlayWindow && !overlayWindow.isDestroyed()) {
        overlayWindow.show();
        overlayWindow.focus();
      }
      
      return dataUrl;
    }
  } catch (error) {
    console.error('截屏失败:', error);
    sendToWindows('screenshot-error', error.message);
  }
  return null;
}

// 注册全局快捷键
function registerShortcuts() {
  // Ctrl+H: 截屏
  globalShortcut.register('CommandOrControl+H', async () => {
    console.log('快捷键触发: Ctrl+H (截屏)');
    await captureScreen();
  });

  // Ctrl+Enter: 发送截图到后端
  globalShortcut.register('CommandOrControl+Enter', () => {
    console.log('快捷键触发: Ctrl+Enter (发送截图)');
    if (currentScreenshot) {
      sendToWindows('send-screenshot-request', currentScreenshot);
    } else {
      sendToWindows('screenshot-error', '没有截图可发送，请先按 Ctrl+H 截屏');
    }
  });

  // Ctrl+B: 切换悬浮窗显示/隐藏
  globalShortcut.register('CommandOrControl+B', () => {
    console.log('快捷键触发: Ctrl+B (切换悬浮窗)');
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      if (overlayWindow.isVisible()) {
        overlayWindow.hide();
        console.log('悬浮窗已隐藏');
      } else {
        overlayWindow.show();
        console.log('悬浮窗已显示');
      }
    }
  });

  // 🚨 Ctrl+Up/Down: 滚动内容 (只滚动单个回复框的内部内容)
  const upRegistered = globalShortcut.register('CommandOrControl+Up', () => {
    console.log('快捷键触发: Ctrl+Up (向上滚动)');
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.webContents.executeJavaScript(`
        (function() {
          try {
            // 🚨 只寻找回复框，不滚动对话历史区域
            const el = document.querySelector('.overlay-response');
            
            if (!el) return '❌ 未找到 .overlay-response';
            
            // 检查是否可滚动
            if (el.scrollHeight <= el.clientHeight) {
              return '⚠️ .overlay-response 内容不需要滚动 [scrollHeight: ' + el.scrollHeight + ', clientHeight: ' + el.clientHeight + ']';
            }
            
            const start = el.scrollTop;
            el.scrollTop -= 100;
            const end = el.scrollTop;
            
            return '✅ 向上滚动 (.overlay-response): ' + start + ' -> ' + end + 
                   ' [scrollHeight: ' + el.scrollHeight + ', clientHeight: ' + el.clientHeight + ']';
          } catch (e) {
            return '❌ JS Error: ' + e.message;
          }
        })()
      `).then(result => console.log(result)).catch(err => console.error('ExecJS Failed:', err));
    }
  });
  console.log('Ctrl+Up 注册结果:', upRegistered ? '成功' : '失败（可能被占用）');

  const downRegistered = globalShortcut.register('CommandOrControl+Down', () => {
    console.log('快捷键触发: Ctrl+Down (向下滚动)');
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.webContents.executeJavaScript(`
        (function() {
          try {
            // 🚨 只寻找回复框，不滚动对话历史区域
            const el = document.querySelector('.overlay-response');
            
            if (!el) return '❌ 未找到 .overlay-response';
            
            // 检查是否可滚动
            if (el.scrollHeight <= el.clientHeight) {
              return '⚠️ .overlay-response 内容不需要滚动 [scrollHeight: ' + el.scrollHeight + ', clientHeight: ' + el.clientHeight + ']';
            }
            
            const start = el.scrollTop;
            el.scrollTop += 100;
            const end = el.scrollTop;
            
            return '✅ 向下滚动 (.overlay-response): ' + start + ' -> ' + end + 
                   ' [scrollHeight: ' + el.scrollHeight + ', clientHeight: ' + el.clientHeight + ']';
          } catch (e) {
            return '❌ JS Error: ' + e.message;
          }
        })()
      `).then(result => console.log(result)).catch(err => console.error('ExecJS Failed:', err));
    }
  });
  console.log('Ctrl+Down 注册结果:', downRegistered ? '成功' : '失败（可能被占用）');
  console.log('Ctrl+Down 注册结果:', downRegistered ? '成功' : '失败（可能被占用）');

  // 移动悬浮窗 (Ctrl + Arrow Keys)
  const moveStep = 20; // 每次移动 20px

  const moveWindow = (dx, dy, name) => {
    console.log(`尝试移动窗口 (${name}): dx=${dx}, dy=${dy}`);
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      if (!overlayWindow.isVisible()) {
        console.log('窗口不可见，强制显示');
        overlayWindow.show();
      }
      
      const bounds = overlayWindow.getBounds();
      console.log(`当前位置: x=${bounds.x}, y=${bounds.y}`);
      
      overlayWindow.setBounds({
        x: bounds.x + dx,
        y: bounds.y + dy,
        width: bounds.width,
        height: bounds.height
      });
      console.log(`新位置: x=${bounds.x + dx}, y=${bounds.y + dy}`);
    } else {
      console.log('窗口不存在或已销毁');
    }
  };

  // 注册移动快捷键 - 已移除，改为前端监听 (Local Shortcut)
  // 这样只在悬浮窗获得焦点时生效，不影响系统
  /*
  // 方案 C: Ctrl + Alt + WASD (绝对不冲突)
  registerMoveKey('CommandOrControl+Alt+W', 0, -moveStep, 'Up');
  registerMoveKey('CommandOrControl+Alt+S', 0, moveStep, 'Down');
  registerMoveKey('CommandOrControl+Alt+A', -moveStep, 0, 'Left');
  registerMoveKey('CommandOrControl+Alt+D', moveStep, 0, 'Right');
  */

  console.log('全局快捷键已注册:');
  console.log('  Ctrl+H: 截屏');
  console.log('  Ctrl+Enter: 发送截图分析');
  console.log('  Ctrl+B: 切换悬浮窗显示/隐藏');
  console.log('  Ctrl+Up: 向上滚动');
  console.log('  Ctrl+Down: 向下滚动');
  console.log('  Ctrl+Left: 向左移动');
  console.log('  Ctrl+Right: 向右移动');
}

// 🔒 IPC: 用户登录成功，创建悬浮窗
ipcMain.handle('user-logged-in', () => {
  console.log('🔐 用户已登录，创建悬浮窗');
  if (!overlayWindow || overlayWindow.isDestroyed()) {
    createOverlayWindow();
  } else {
    overlayWindow.show();
  }
  return { success: true };
});

// 🔒 IPC: 用户登出，关闭悬浮窗
ipcMain.handle('user-logged-out', () => {
  console.log('🚪 用户已登出，关闭悬浮窗');
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.close();
    overlayWindow = null;
  }
  return { success: true };
});

// IPC 事件处理
ipcMain.handle('capture-screen', async () => {
  return await captureScreen();
});

ipcMain.handle('send-to-backend', async (event, imageBase64) => {
  // 这里前端会自己调用后端 API，这个 handler 可以用于未来扩展
  return { success: true };
});

ipcMain.on('minimize-overlay', () => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.hide();
  }
});

ipcMain.on('show-overlay', () => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.show();
  }
});

// 控制点击穿透（根据鼠标位置动态切换）
ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    const winOptions = options || { forward: true };
    overlayWindow.setIgnoreMouseEvents(ignore, winOptions);
    // console.log(`穿透更新: ${ignore} (forward: ${winOptions.forward})`);
  }
});

// 打开主窗口
ipcMain.on('open-main-window', () => {
  console.log('🔔 收到打开主窗口请求');
  console.log('当前 mainWindow 状态:', mainWindow ? '存在' : '不存在', mainWindow && !mainWindow.isDestroyed() ? '未销毁' : '已销毁');
  
  if (mainWindow && !mainWindow.isDestroyed()) {
    console.log('显示现有主窗口');
    
    // 🚨 确保窗口可见
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
      console.log('从最小化状态恢复');
    }
    
    mainWindow.show();
    mainWindow.focus();
    mainWindow.moveTop(); // 🚨 置于最前
    
    console.log('✅ 主窗口已显示并聚焦');
    console.log('窗口是否可见:', mainWindow.isVisible());
    console.log('窗口是否聚焦:', mainWindow.isFocused());
  } else {
    console.log('创建新的主窗口');
    createMainWindow();
    console.log('✅ 新主窗口已创建');
  }
});

// 接收前端的移动请求
ipcMain.on('move-overlay', (event, { direction, step }) => {
  console.log(`IPC收到移动请求: direction=${direction}, step=${step}`);
  const moveStep = step || 20;
  let dx = 0;
  let dy = 0;
  
  switch (direction) {
    case 'up': dy = -moveStep; break;
    case 'down': dy = moveStep; break;
    case 'left': dx = -moveStep; break;
    case 'right': dx = moveStep; break;
  }
  
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    const bounds = overlayWindow.getBounds();
    const { screen } = require('electron');
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
    
    console.log(`屏幕尺寸: ${screenWidth}x${screenHeight}`);
    console.log(`当前窗口: x=${bounds.x}, y=${bounds.y}, width=${bounds.width}, height=${bounds.height}`);
    
    // 计算新位置
    let newX = bounds.x + dx;
    let newY = bounds.y + dy;
    
    console.log(`计算新位置（边界检查前）: x=${newX}, y=${newY}`);
    
    // 边界检查：防止窗口移出屏幕
    // 左边界
    if (newX < 0) {
      console.log(`触碰左边界，限制 x 从 ${newX} 到 0`);
      newX = 0;
    }
    // 右边界（窗口右边缘不能超出屏幕右边缘）
    if (newX + bounds.width > screenWidth) {
      console.log(`触碰右边界，限制 x 从 ${newX} 到 ${screenWidth - bounds.width}`);
      newX = screenWidth - bounds.width;
    }
    // 上边界
    if (newY < 0) {
      console.log(`触碰上边界，限制 y 从 ${newY} 到 0`);
      newY = 0;
    }
    // 下边界（窗口下边缘不能超出屏幕下边缘）
    if (newY + bounds.height > screenHeight) {
      console.log(`触碰下边界，限制 y 从 ${newY} 到 ${screenHeight - bounds.height}`);
      newY = screenHeight - bounds.height;
    }
    
    console.log(`最终位置（边界检查后）: x=${newX}, y=${newY}`);
    
    overlayWindow.setBounds({
      x: newX,
      y: newY,
      width: bounds.width,
      height: bounds.height
    });
  }
});

ipcMain.on('resize-overlay', (event, height) => {
  resizeOverlayWindow(height);
});

// 🎤 IPC: 本地语音转文字（使用本地 Whisper）
ipcMain.handle('speech-to-text-local', async (event, audioData, language = 'zh') => {
  try {
    // 获取 Python 解释器路径
    const isDev = !app.isPackaged;
    let pythonPath;
    let whisperScriptPath;
    
    if (isDev) {
      // 开发环境：使用系统 Python 或 venv
      pythonPath = process.platform === 'win32' ? 'python' : 'python3';
      whisperScriptPath = path.join(__dirname, 'whisper_local.py');
    } else {
      // 生产环境：使用打包的 Python（需要配置）
      // 这里假设 Python 在系统 PATH 中，或者您需要配置具体路径
      pythonPath = process.platform === 'win32' ? 'python' : 'python3';
      whisperScriptPath = path.join(process.resourcesPath, 'whisper_local.py');
    }
    
    // 创建临时音频文件
    const tempDir = require('os').tmpdir();
    const tempAudioPath = path.join(tempDir, `audio_${Date.now()}.webm`);
    
    // 将 base64 或 Buffer 写入文件
    let audioBuffer;
    if (typeof audioData === 'string') {
      // Base64 字符串
      audioBuffer = Buffer.from(audioData, 'base64');
    } else if (Buffer.isBuffer(audioData)) {
      audioBuffer = audioData;
    } else {
      throw new Error('不支持的音频数据格式');
    }
    
    await writeFile(tempAudioPath, audioBuffer);
    
    console.log('🎤 开始本地语音转文字，音频文件:', tempAudioPath);
    
    // 调用 Python 脚本
    return new Promise((resolve, reject) => {
      const pythonProcess = spawn(pythonPath, [whisperScriptPath, tempAudioPath, language], {
        stdio: ['ignore', 'pipe', 'pipe']
      });
      
      let stdout = '';
      let stderr = '';
      
      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
        // 打印进度信息到控制台
        console.log('Whisper:', data.toString().trim());
      });
      
      pythonProcess.on('close', async (code) => {
        // 清理临时文件
        try {
          await unlink(tempAudioPath);
        } catch (err) {
          console.error('清理临时文件失败:', err);
        }
        
        if (code !== 0) {
          console.error('Whisper 处理失败，退出码:', code);
          console.error('stderr:', stderr);
          reject(new Error(`Whisper 处理失败: ${stderr || '未知错误'}`));
          return;
        }
        
        try {
          // 解析 JSON 输出
          const result = JSON.parse(stdout.trim());
          console.log('✅ 本地语音转文字完成:', result);
          resolve(result);
        } catch (err) {
          console.error('解析 Whisper 输出失败:', err);
          console.error('stdout:', stdout);
          reject(new Error('解析 Whisper 输出失败'));
        }
      });
      
      pythonProcess.on('error', async (err) => {
        // 清理临时文件
        try {
          await unlink(tempAudioPath);
        } catch (unlinkErr) {
          console.error('清理临时文件失败:', unlinkErr);
        }
        
        console.error('启动 Whisper 进程失败:', err);
        reject(new Error(`无法启动 Whisper: ${err.message}`));
      });
    });
  } catch (error) {
    console.error('❌ 本地语音转文字失败:', error);
    return {
      success: false,
      error: error.message,
      text: '',
      language: '',
      duration: 0.0
    };
  }
});

app.whenReady().then(() => {
  createMainWindow();
  // 🔒 不要自动创建悬浮窗，等待主窗口通知用户已登录
  // createOverlayWindow();
  createMenu(); // 🔑 创建菜单
  registerShortcuts();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
      // 🔒 不要自动创建悬浮窗
      // createOverlayWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  // 注销所有快捷键
  globalShortcut.unregisterAll();
});

