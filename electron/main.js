const { app, BrowserWindow, globalShortcut, desktopCapturer, ipcMain, Menu, dialog, shell, Notification } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { promisify } = require('util');
const writeFile = promisify(fs.writeFile);
const unlink = promisify(fs.unlink);
const { createWriteStream } = require('fs');
const https = require('https');
const http = require('http');

// 🚨 恢复 GPU 加速（有些系统禁用后反而黑屏）
// app.disableHardwareAcceleration();

let mainWindow = null;
let overlayWindow = null;
let oauthWindow = null;
let currentScreenshot = null;

const isDev = !app.isPackaged;

// 📝 设置日志文件
const logDir = path.join(app.getPath('userData'), 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}
const logFile = path.join(logDir, `main-${new Date().toISOString().replace(/:/g, '-').split('.')[0]}.log`);
const logStream = createWriteStream(logFile, { flags: 'a' });

// 重定向 console 到文件和控制台
const originalLog = console.log;
const originalError = console.error;
const originalWarn = console.warn;

function logToFile(level, ...args) {
  const timestamp = new Date().toISOString();
  const message = `[${timestamp}] [${level}] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)).join(' ')}\n`;
  logStream.write(message);
  // 同时输出到控制台
  if (level === 'ERROR') {
    originalError(...args);
  } else if (level === 'WARN') {
    originalWarn(...args);
      } else {
    originalLog(...args);
  }
}

console.log = (...args) => logToFile('INFO', ...args);
console.error = (...args) => logToFile('ERROR', ...args);
console.warn = (...args) => logToFile('WARN', ...args);

console.log('='.repeat(60));
console.log('🚀 Electron 应用启动');
console.log(`   环境: ${isDev ? 'Development' : 'Production'}`);
console.log(`   日志文件: ${logFile}`);
console.log(`   应用路径: ${app.getAppPath()}`);
console.log(`   资源路径: ${process.resourcesPath || 'N/A'}`);
console.log(`   打包状态: ${app.isPackaged ? '已打包' : '未打包'}`);
console.log('='.repeat(60));

// Desktop version architecture:
// - UI runs locally from dist/ folder (built by Vite)
// - All API requests go to Vercel backend (no local FastAPI)
// - No API keys stored locally, all managed on Vercel

// 🎯 获取场景配置（从渲染进程）
async function getSceneConfig() {
  if (!mainWindow) return null;
  try {
    const config = await mainWindow.webContents.executeJavaScript(`
      (() => {
        try {
          const stored = localStorage.getItem('ai_assistant_scenes');
          if (stored) {
            const parsed = JSON.parse(stored);
            return parsed.scenes || [];
          }
        } catch (e) {
          console.error('Error reading scene config:', e);
        }
        return [];
      })()
    `);
    return config;
  } catch (error) {
    console.error('Error getting scene config:', error);
    return [];
  }
}

// 🎯 获取所有场景（包括内置和自定义）
async function getAllScenes() {
  const customScenes = await getSceneConfig();
  
  // 内置场景
  const builtInScenes = [
    {
      id: 'coding',
      name: 'Coding Interview',
      isBuiltIn: true,
      presets: [
        {
          id: 'default',
          name: 'Default',
          prompt: 'You are a coding interview assistant. Help the user practice coding interview questions. Provide clear explanations, code examples, and best practices.'
        }
      ]
    },
    {
      id: 'behavioral',
      name: 'Behavioral Interview',
      isBuiltIn: true,
      presets: [
        {
          id: 'default',
          name: 'Default',
          prompt: 'You are a behavioral interview coach. Help the user prepare for behavioral questions using the STAR method (Situation, Task, Action, Result). Provide feedback on their answers.'
        }
      ]
    }
  ];
  
  const generalScene = {
    id: 'general',
    name: 'General Chat',
    isBuiltIn: true,
    presets: [
      {
        id: 'default',
        name: 'Default',
        prompt: 'You are a friendly and helpful conversation partner. Engage in natural, professional conversation to help the user practice their communication skills.'
      }
    ]
  };
  
  return {
    builtIn: builtInScenes,
    general: generalScene,
    custom: customScenes
  };
}

// 🎯 创建 Application Scenario 菜单
async function createApplicationScenarioMenu() {
  const scenes = await getAllScenes();
  
  const interviewSubmenu = scenes.builtIn.map(scene => ({
    label: scene.name,
    click: async () => {
      if (mainWindow) {
        const preset = scene.presets[0];
        mainWindow.webContents.send('scenario-selected', {
          sceneId: scene.id,
          presetId: preset.id,
          prompt: preset.prompt
        });
      }
    }
  }));
  
  const customSubmenu = [
    ...scenes.custom.map(scene => ({
      label: scene.name,
      click: async () => {
        if (mainWindow) {
          const preset = scene.presets[0];
          mainWindow.webContents.send('scenario-selected', {
            sceneId: scene.id,
            presetId: preset.id,
            prompt: preset.prompt
          });
        }
      }
    })),
    { type: 'separator' },
    {
      label: 'Create New Custom Scenario...',
      click: async () => {
        if (mainWindow) {
          mainWindow.webContents.send('open-scenario-editor', { mode: 'create' });
        }
      }
    }
  ];
  
  return {
    label: 'Application Scenario',
    submenu: [
      {
        label: 'Interview',
        submenu: interviewSubmenu
      },
      {
        label: 'General',
        click: async () => {
          if (mainWindow) {
            const preset = scenes.general.presets[0];
            mainWindow.webContents.send('scenario-selected', {
              sceneId: scenes.general.id,
              presetId: preset.id,
              prompt: preset.prompt
            });
          }
        }
      },
      {
        label: 'Custom',
        submenu: customSubmenu.length > 1 ? customSubmenu : [
          {
            label: 'Create New Custom Scenario...',
            click: async () => {
              if (mainWindow) {
                mainWindow.webContents.send('open-scenario-editor', { mode: 'create' });
              }
            }
          }
        ]
      }
    ]
  };
}

// 🎨 创建现代化菜单
async function createMenu() {
  // 菜单已全部删除，使用空菜单
  const template = [];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// 🎯 更新 Application Scenario 菜单（已删除，不再需要）
async function updateApplicationScenarioMenu() {
  // 菜单已简化，不再需要更新场景菜单
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

  if (isDev) {
    // Development: connect to Vite dev server
    const devPort = process.env.VITE_DEV_SERVER_PORT || '5173';
    const devUrl = `http://localhost:${devPort}`;
    console.log(`🔧 开发模式: 连接到 ${devUrl}`);
    mainWindow.loadURL(devUrl);
    // mainWindow.webContents.openDevTools(); // 🚨 关闭开发者工具
  } else {
    // Production: load from dist/ folder (static files built by Vite)
    // All API requests will be forwarded to Vercel backend
    // ✅ 关键：必须指向具体的 index.html 文件
    const indexHtml = path.join(__dirname, '../dist/index.html');
    console.log(`📦 生产模式: 加载文件 ${indexHtml}`);
    console.log(`   文件是否存在: ${fs.existsSync(indexHtml)}`);
    console.log(`   __dirname: ${__dirname}`);
    console.log(`   完整路径: ${path.resolve(indexHtml)}`);
    
    // ✅ 使用 loadFile 加载具体的 HTML 文件
    mainWindow.loadFile(indexHtml);
    
    // 🚨 临时启用 DevTools 以便调试
    mainWindow.webContents.openDevTools();
  }

  // 🚨 添加错误监听
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    console.error('🚨 主窗口加载失败:', {
      errorCode,
      errorDescription,
      validatedURL,
      isMainFrame,
      timestamp: new Date().toISOString()
    });
    
    // 显示错误信息
    const errorHtml = `
      <div style="padding: 40px; font-family: Arial; text-align: center; background: #f5f7fa; min-height: 100vh; display: flex; align-items: center; justify-content: center;">
        <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 600px;">
          <h2 style="color: #e74c3c;">❌ 页面加载失败</h2>
          <p><strong>错误代码:</strong> ${errorCode}</p>
          <p><strong>错误描述:</strong> ${errorDescription}</p>
          <p><strong>URL:</strong> <code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">${validatedURL}</code></p>
          <p><strong>日志文件位置:</strong></p>
          <p><code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px; word-break: break-all;">${logFile}</code></p>
          <p style="margin-top: 20px; color: #666;">请查看日志文件获取更多信息</p>
        </div>
      </div>
    `;
    mainWindow.webContents.executeJavaScript(`
      document.body.innerHTML = ${JSON.stringify(errorHtml)};
    `).catch(err => console.error('显示错误信息失败:', err));
  });
  
  // 监听控制台消息
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[Renderer ${level}] ${message} (${sourceId}:${line})`);
  });
  
  // 监听渲染进程崩溃
  mainWindow.webContents.on('render-process-gone', (event, details) => {
    console.error('🚨 渲染进程崩溃:', details);
  });
  
  // 监听未捕获的异常
  mainWindow.webContents.on('unresponsive', () => {
    console.error('🚨 窗口无响应');
  });
  
  mainWindow.webContents.on('responsive', () => {
    console.log('✅ 窗口恢复响应');
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

  // 🔗 拦截导航到外部链接和无效的 file:// 路径
  mainWindow.webContents.on('will-navigate', (event, url) => {
    // 拦截无效的 file:// 路径（如 file:///D:/, file:///D:/? 等）
    // 匹配模式：file:/// + 单个驱动器字母 + :/ + 可选查询参数
    if (url.startsWith('file:///') && /^file:\/\/\/[A-Z]:\/\??/i.test(url)) {
      console.warn(`🚫 拦截无效的 file:// 导航: ${url}`);
      event.preventDefault();
      return;
    }
    
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

  if (isDev) {
    // Development: connect to Vite dev server
    const devPort = process.env.VITE_DEV_SERVER_PORT || '5173';
    overlayWindow.loadURL(`http://localhost:${devPort}/?type=overlay#/overlay`);
  } else {
    // Production: load from dist/ folder (static files built by Vite)
    // All API requests will be forwarded to Vercel backend
    // ✅ 关键：必须指向具体的 index.html 文件
    const indexHtml = path.join(__dirname, '../dist/index.html');
    console.log(`📦 悬浮窗生产模式: 加载文件 ${indexHtml}`);
    overlayWindow.loadFile(indexHtml, {
      hash: '/overlay',
      search: 'type=overlay'
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

  // 🔗 拦截导航到外部链接和无效的 file:// 路径
  overlayWindow.webContents.on('will-navigate', (event, url) => {
    // 拦截无效的 file:// 路径（如 file:///D:/, file:///D:/? 等）
    // 匹配模式：file:/// + 单个驱动器字母 + :/ + 可选查询参数
    if (url.startsWith('file:///') && /^file:\/\/\/[A-Z]:\/\??/i.test(url)) {
      console.warn(`🚫 拦截无效的 file:// 导航: ${url}`);
      event.preventDefault();
      return;
    }
    
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

// 辅助函数：在 Node.js 中发送 HTTP 请求
function httpRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const isHttps = urlObj.protocol === 'https:';
    const httpModule = isHttps ? https : http;
    
    const requestOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port || (isHttps ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: options.headers || {}
    };
    
    console.log('🔐 发送 HTTP 请求:', requestOptions.method, requestOptions.hostname + requestOptions.path);
    
    const req = httpModule.request(requestOptions, (res) => {
      let data = '';
      
      console.log('🔐 收到响应:', res.statusCode, res.statusMessage);
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        console.log('🔐 响应数据长度:', data.length);
        console.log('🔐 响应数据预览:', data.substring(0, Math.min(200, data.length)));
        
        try {
          const jsonData = JSON.parse(data);
          resolve({ status: res.statusCode, ok: res.statusCode >= 200 && res.statusCode < 300, json: () => Promise.resolve(jsonData), text: () => Promise.resolve(data) });
        } catch (e) {
          console.error('🔐 JSON 解析失败:', e.message);
          resolve({ status: res.statusCode, ok: res.statusCode >= 200 && res.statusCode < 300, json: () => Promise.reject(new Error('Not JSON')), text: () => Promise.resolve(data) });
        }
      });
    });
    
    req.on('error', (error) => {
      console.error('🔐 HTTP 请求错误:', error.message);
      reject(error);
    });
    
    // 设置超时
    req.setTimeout(10000, () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });
    
    if (options.body) {
      req.write(options.body);
    }
    
    req.end();
  });
}

// 处理 OAuth 回调
function handleOAuthCallback(url, resolve, reject) {
  try {
    const urlObj = new URL(url);
    
    // 检查是否是回调 URL（包含 code 参数）
    if (urlObj.pathname.includes('/auth/callback') || urlObj.searchParams.has('code')) {
      const code = urlObj.searchParams.get('code');
      const error = urlObj.searchParams.get('error');
      
      if (error) {
        console.error('🔐 OAuth 错误:', error);
        if (oauthWindow && !oauthWindow.isDestroyed()) {
          oauthWindow.close();
        }
        reject(new Error(`OAuth error: ${error}`));
        return;
      }
      
      if (code) {
        const state = urlObj.searchParams.get('state');
        console.log('🔐 获取到 OAuth code:', code.substring(0, 20) + '...');
        if (state) {
          console.log('🔐 获取到 OAuth state:', state.substring(0, 20) + '...');
        }
        
        // 关闭 OAuth 窗口
        if (oauthWindow && !oauthWindow.isDestroyed()) {
          oauthWindow.close();
        }
        
        // 返回 code 和 state 给前端
        resolve({ code, state: state || undefined, success: true });
      }
    }
  } catch (error) {
    console.error('🔐 处理 OAuth 回调错误:', error);
    // 不 reject，因为可能只是中间页面导航
  }
}

// 🔐 IPC: Google OAuth 登录
ipcMain.handle('oauth-google', async () => {
  return new Promise(async (resolve, reject) => {
    try {
      // 获取 OAuth URL（需要从 API 获取）
      // 桌面版架构：所有 API 请求都直接到 Vercel（不依赖本地后端）
      // 如果需要使用本地后端，可以通过环境变量 LOCAL_API_URL 指定
      const isDev = !app.isPackaged;
      const API_BASE_URL = process.env.LOCAL_API_URL 
        || process.env.VERCEL_API_URL 
        || 'https://www.desktopai.org';
      // 对于 Electron 桌面应用，使用应用网站的 callback URL
      // 这样 Supabase 可以正确验证 OAuth flow state
      const redirectTo = 'https://www.desktopai.org/auth/callback';
      const apiUrl = `${API_BASE_URL}/api/auth/google/url?redirect_to=${encodeURIComponent(redirectTo)}`;
      console.log('🔐 请求 OAuth URL:', apiUrl);
      console.log('🔐 API_BASE_URL:', API_BASE_URL);
      
      let response;
      try {
        response = await httpRequest(apiUrl);
        console.log('🔐 API 响应状态:', response.status, 'OK:', response.ok);
      } catch (httpError) {
        console.error('🔐 HTTP 请求失败:', httpError);
        console.error('🔐 错误详情:', httpError.message);
        console.error('🔐 错误堆栈:', httpError.stack);
        throw new Error(`HTTP request failed: ${httpError.message}`);
      }
      
      if (!response.ok) {
        let errorText = 'Unknown error';
        try {
          errorText = await response.text();
        } catch (e) {
          console.error('🔐 无法读取错误响应:', e);
        }
        console.error('🔐 API 错误响应状态:', response.status);
        console.error('🔐 API 错误响应内容:', errorText);
        throw new Error(`Failed to get OAuth URL: HTTP ${response.status} - ${errorText}`);
      }
      
      const data = await response.json();
      console.log('🔐 API 响应数据:', data);
      
      if (!data || !data.url) {
        throw new Error('Invalid response: missing url field');
      }
      
      const authUrl = data.url;
      
      console.log('🔐 打开 Google OAuth 窗口:', authUrl);
      
      // 创建 OAuth 窗口
      oauthWindow = new BrowserWindow({
        width: 500,
        height: 600,
        modal: true,
        parent: mainWindow,
        show: false,
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true
        }
      });
      
      // 监听窗口准备显示
      oauthWindow.once('ready-to-show', () => {
        oauthWindow.show();
      });
      
      // 监听窗口导航，捕获回调 URL
      oauthWindow.webContents.on('will-navigate', (event, url) => {
        console.log('🔐 OAuth 窗口导航到:', url);
        handleOAuthCallback(url, resolve, reject);
      });
      
      // 也监听 did-navigate（某些情况下用这个）
      oauthWindow.webContents.on('did-navigate', (event, url) => {
        console.log('🔐 OAuth 窗口已导航到:', url);
        handleOAuthCallback(url, resolve, reject);
      });
      
      // 监听窗口关闭
      oauthWindow.on('closed', () => {
        oauthWindow = null;
      });
      
      // 加载 OAuth URL
      oauthWindow.loadURL(authUrl);
      
    } catch (error) {
      console.error('🔐 OAuth 错误:', error);
      console.error('🔐 错误堆栈:', error.stack);
      reject(new Error(error.message || 'Failed to initiate Google OAuth'));
    }
  });
});

// 🎯 IPC 处理器：场景相关
ipcMain.handle('get-all-scenes', async () => {
  return await getAllScenes();
});

ipcMain.handle('select-scenario', async (event, { sceneId, presetId }) => {
  const scenes = await getAllScenes();
  let selectedPrompt = '';
  
  // 查找场景
  const allScenes = [...scenes.builtIn, scenes.general, ...scenes.custom];
  const scene = allScenes.find(s => s.id === sceneId);
  if (scene) {
    const preset = scene.presets.find(p => p.id === presetId);
    if (preset) {
      selectedPrompt = preset.prompt;
    }
  }
  
  // 通知所有窗口场景已选择
  if (mainWindow) {
    mainWindow.webContents.send('scenario-selected', {
      sceneId,
      presetId,
      prompt: selectedPrompt
    });
  }
  if (overlayWindow) {
    overlayWindow.webContents.send('scenario-selected', {
      sceneId,
      presetId,
      prompt: selectedPrompt
    });
  }
  
  return { success: true, prompt: selectedPrompt };
});

ipcMain.on('scenario-updated', async () => {
  // 当场景更新时，刷新菜单
  await updateApplicationScenarioMenu();
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

// 📁 IPC: 选择文件夹
ipcMain.handle('select-folder', async (event, options = {}) => {
  try {
    const win = BrowserWindow.fromWebContents(event.sender);
    const result = await dialog.showOpenDialog(win || mainWindow, {
      properties: ['openDirectory'],
      title: options.title || 'Select Folder',
      defaultPath: options.defaultPath || app.getPath('documents')
    });

    if (result.canceled || result.filePaths.length === 0) {
      return { canceled: true, path: null };
    }

    return { canceled: false, path: result.filePaths[0] };
  } catch (error) {
    console.error('❌ 选择文件夹失败:', error);
    return { canceled: true, path: null, error: error.message };
  }
});

// ⚠️ IPC: 显示 Token 使用率警告
ipcMain.on('show-token-warning', (event, message, usagePercentage) => {
  try {
    // 使用 Electron 原生通知
    if (Notification.isSupported()) {
      const notification = new Notification({
        title: '⚠️ Token 使用率警告',
        body: `您已使用 ${usagePercentage}% 的 Token 配额，剩余配额有限。请合理使用。`,
        icon: path.join(__dirname, '../resources/icon.png'),
        urgency: 'normal',
        timeoutType: 'never' // 不自动消失，让用户手动关闭
      });

      notification.show();

      // 可选：点击通知时聚焦主窗口
      notification.on('click', () => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.focus();
        }
      });
    } else {
      // 降级到对话框
      const win = BrowserWindow.fromWebContents(event.sender);
      dialog.showMessageBox(win || mainWindow, {
        type: 'warning',
        title: '⚠️ Token 使用率警告',
        message: `您已使用 ${usagePercentage}% 的 Token 配额`,
        detail: message,
        buttons: ['知道了'],
        defaultId: 0
      });
    }
    
    console.warn('⚠️ Token 使用率警告:', message);
  } catch (error) {
    console.error('❌ 显示 Token 警告失败:', error);
  }
});

// 全局错误处理
process.on('uncaughtException', (error) => {
  console.error('🚨 未捕获的异常:', error);
  logStream.end();
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('🚨 未处理的 Promise 拒绝:', reason);
  logStream.end();
});

app.whenReady().then(async () => {
  createMainWindow();
  // 🔒 不要自动创建悬浮窗，等待主窗口通知用户已登录
  // createOverlayWindow();
  await createMenu(); // 🔑 创建菜单
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
  // 关闭日志流
  logStream.end();
  console.log('📝 日志已保存到:', logFile);
});

app.on('before-quit', () => {
  console.log('🛑 应用即将退出');
});

