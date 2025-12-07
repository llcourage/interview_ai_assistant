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

// 🚨 Restore GPU acceleration (some systems may show black screen when disabled)
// app.disableHardwareAcceleration();

let mainWindow = null;
let overlayWindow = null;
let oauthWindow = null;
let currentScreenshot = null;

const isDev = !app.isPackaged;

// 📝 Setup log file
const logDir = path.join(app.getPath('userData'), 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}
const logFile = path.join(logDir, `main-${new Date().toISOString().replace(/:/g, '-').split('.')[0]}.log`);
const logStream = createWriteStream(logFile, { flags: 'a' });

// Redirect console to file and console
const originalLog = console.log;
const originalError = console.error;
const originalWarn = console.warn;

function logToFile(level, ...args) {
  const timestamp = new Date().toISOString();
  const message = `[${timestamp}] [${level}] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)).join(' ')}\n`;
  logStream.write(message);
  // Also output to console
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
console.log('🚀 Electron app starting');
console.log(`   Environment: ${isDev ? 'Development' : 'Production'}`);
console.log(`   Log file: ${logFile}`);
console.log(`   App path: ${app.getAppPath()}`);
console.log(`   Resources path: ${process.resourcesPath || 'N/A'}`);
console.log(`   Packaged: ${app.isPackaged ? 'Yes' : 'No'}`);
console.log('='.repeat(60));

// Desktop version architecture:
// - UI runs locally from dist/ folder (built by Vite)
// - All API requests go to Vercel backend (no local FastAPI)
// - No API keys stored locally, all managed on Vercel

// 🎯 Get scene configuration (from renderer process)
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

// 🎯 Get all scenes (including built-in and custom)
async function getAllScenes() {
  const customScenes = await getSceneConfig();
  
  // Built-in scenes
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

// 🎯 Create Application Scenario menu
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

// 🎨 Create modern menu
async function createMenu() {
  // Menu has been removed, using empty menu
  const template = [];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// 🎯 Update Application Scenario menu (removed, no longer needed)
async function updateApplicationScenarioMenu() {
  // Menu has been simplified, no longer need to update scene menu
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    frame: true,
    backgroundColor: '#f5f7fa',
    autoHideMenuBar: false, // Show menu bar
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      // Disable webSecurity in development to allow cross-origin requests (development only)
      // ⚠️ Note: This is for development only, production should keep webSecurity enabled
      webSecurity: !isDev // Disabled in development, enabled in production
    },
    icon: path.join(__dirname, '../resources/icon.png')
  });

  if (isDev) {
    // Development: connect to Vite dev server
    const devPort = process.env.VITE_DEV_SERVER_PORT || '5173';
    const devUrl = `http://localhost:${devPort}`;
    console.log(`🔧 Development mode: connecting to ${devUrl}`);
    mainWindow.loadURL(devUrl);
    // mainWindow.webContents.openDevTools(); // 🚨 Close DevTools
  } else {
    // Production: load from dist/ folder (static files built by Vite)
    // All API requests will be forwarded to Vercel backend
    // ✅ Key: Must point to specific index.html file
    const indexHtml = path.join(__dirname, '../dist/index.html');
    console.log(`📦 Production mode: loading file ${indexHtml}`);
    console.log(`   File exists: ${fs.existsSync(indexHtml)}`);
    console.log(`   __dirname: ${__dirname}`);
    console.log(`   Full path: ${path.resolve(indexHtml)}`);
    
    // ✅ Use loadFile to load specific HTML file
    mainWindow.loadFile(indexHtml);
    
    // 🚨 Temporarily enable DevTools for debugging
    mainWindow.webContents.openDevTools();
  }

  // 🚨 Add error listener
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    console.error('🚨 Main window load failed:', {
      errorCode,
      errorDescription,
      validatedURL,
      isMainFrame,
      timestamp: new Date().toISOString()
    });
    
    // Display error message
    const errorHtml = `
      <div style="padding: 40px; font-family: Arial; text-align: center; background: #f5f7fa; min-height: 100vh; display: flex; align-items: center; justify-content: center;">
        <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 600px;">
          <h2 style="color: #e74c3c;">❌ Page Load Failed</h2>
          <p><strong>Error Code:</strong> ${errorCode}</p>
          <p><strong>Error Description:</strong> ${errorDescription}</p>
          <p><strong>URL:</strong> <code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">${validatedURL}</code></p>
          <p><strong>Log File Location:</strong></p>
          <p><code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px; word-break: break-all;">${logFile}</code></p>
          <p style="margin-top: 20px; color: #666;">Please check the log file for more information</p>
        </div>
      </div>
    `;
    mainWindow.webContents.executeJavaScript(`
      document.body.innerHTML = ${JSON.stringify(errorHtml)};
    `).catch(err => console.error('Failed to display error message:', err));
  });
  
  // Listen to console messages
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[Renderer ${level}] ${message} (${sourceId}:${line})`);
  });
  
  // Listen to renderer process crash
  mainWindow.webContents.on('render-process-gone', (event, details) => {
    console.error('🚨 Renderer process crashed:', details);
  });
  
  // Listen to uncaught exceptions
  mainWindow.webContents.on('unresponsive', () => {
    console.error('🚨 Window unresponsive');
  });
  
  mainWindow.webContents.on('responsive', () => {
    console.log('✅ Window responsive again');
  });

  // 🚨 Show window after loading completes (avoid white screen flash)
  mainWindow.once('ready-to-show', () => {
    console.log('Main window ready, showing window');
    mainWindow.show();
    mainWindow.focus();
  });

  // Add console message listener (for debugging)
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    if (level === 3) { // error level
      console.error('Frontend error:', message);
    }
  });

  // 🔗 Intercept external links, open in system default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // Check if it's an external link
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // Not localhost, open in system default browser
      if (!url.includes('localhost') && !url.includes('127.0.0.1')) {
        shell.openExternal(url);
        return { action: 'deny' }; // Prevent opening in app
      }
    }
    return { action: 'allow' }; // Allow local links to open in app
  });

  // 🔗 Intercept navigation to external links and invalid file:// paths
  mainWindow.webContents.on('will-navigate', (event, url) => {
    // Intercept invalid file:// paths (e.g., file:///D:/, file:///D:/? etc.)
    // Pattern: file:/// + single drive letter + :/ + optional query params
    if (url.startsWith('file:///') && /^file:\/\/\/[A-Z]:\/\??/i.test(url)) {
      console.warn(`🚫 Intercepting invalid file:// navigation: ${url}`);
      event.preventDefault();
      return;
    }
    
    // Check if it's an external link
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // Not localhost, open in system default browser
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
  // Get screen size
  const { screen } = require('electron');
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
  
  // Calculate window size (half screen width, small initial height)
  const windowWidth = Math.floor(screenWidth / 2);
  // 🎯 Increase max height to 80% to accommodate more content
  const maxHeight = Math.floor(screenHeight * 0.8);
  const initialHeight = 80; // Initial height, only show button
  
  overlayWindow = new BrowserWindow({
    width: windowWidth,
    height: initialHeight,
    maxHeight: maxHeight,
    minHeight: initialHeight,
    frame: false,
    transparent: true,
    // 🚨 Try giving a very faint background color instead of completely transparent
    // Sometimes #00000000 causes render layer to be ignored
    backgroundColor: '#01000000', 
    alwaysOnTop: true,
    skipTaskbar: false,
    resizable: true,
    focusable: true,
    hasShadow: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      // Disable webSecurity in development to allow cross-origin requests (development only)
      webSecurity: !isDev // Disabled in development, enabled in production
    },
    show: false
  });

  // Remove DevTools
  // overlayWindow.webContents.openDevTools({ mode: 'detach' });

  if (isDev) {
    // Development: connect to Vite dev server
    const devPort = process.env.VITE_DEV_SERVER_PORT || '5173';
    overlayWindow.loadURL(`http://localhost:${devPort}/?type=overlay#/overlay`);
  } else {
    // Production: load from dist/ folder (static files built by Vite)
    // All API requests will be forwarded to Vercel backend
    // ✅ Key: Must point to specific index.html file
    const indexHtml = path.join(__dirname, '../dist/index.html');
    console.log(`📦 Overlay production mode: loading file ${indexHtml}`);
    overlayWindow.loadFile(indexHtml, {
      hash: '/overlay',
      search: 'type=overlay'
    });
  }

  // Set window position (top center)
  const x = Math.floor((screenWidth - windowWidth) / 2);
  const y = 0; // Top
  overlayWindow.setPosition(x, y);
  
  // No need to set opacity separately, already set above
  // overlayWindow.setOpacity(1.0);

  overlayWindow.on('closed', () => {
    overlayWindow = null;
  });

  // 🚨 Debug: load failure listener
  overlayWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('🚨 Page load failed:', errorCode, errorDescription);
  });

  // 🔗 Intercept external links, open in system default browser
  overlayWindow.webContents.setWindowOpenHandler(({ url }) => {
    // Check if it's an external link
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // Not localhost, open in system default browser
      if (!url.includes('localhost') && !url.includes('127.0.0.1')) {
        shell.openExternal(url);
        return { action: 'deny' }; // Prevent opening in app
      }
    }
    return { action: 'allow' }; // Allow local links to open in app
  });

  // 🔗 Intercept navigation to external links and invalid file:// paths
  overlayWindow.webContents.on('will-navigate', (event, url) => {
    // Intercept invalid file:// paths (e.g., file:///D:/, file:///D:/? etc.)
    // Pattern: file:/// + single drive letter + :/ + optional query params
    if (url.startsWith('file:///') && /^file:\/\/\/[A-Z]:\/\??/i.test(url)) {
      console.warn(`🚫 Intercepting invalid file:// navigation: ${url}`);
      event.preventDefault();
      return;
    }
    
    // Check if it's an external link
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // Not localhost, open in system default browser
      if (!url.includes('localhost') && !url.includes('127.0.0.1')) {
        event.preventDefault();
        shell.openExternal(url);
      }
    }
  });

  // 🚨 Debug: load complete listener
  overlayWindow.webContents.on('did-finish-load', () => {
    console.log('✅ Page load complete');
    
    // Show window
    overlayWindow.show();
    overlayWindow.focus();
    
    // 🚨 Initial state: not click-through, wait for frontend mousemove to take over then dynamically switch
    overlayWindow.setIgnoreMouseEvents(false);
    console.log('✅ Window initially set to not click-through, waiting for frontend to take over');
  });
}

// Dynamically adjust overlay window height
function resizeOverlayWindow(height) {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    const { screen } = require('electron');
    const primaryDisplay = screen.getPrimaryDisplay();
    const { height: screenHeight } = primaryDisplay.workAreaSize;
    // 🎯 Increase max height to 80%
    const maxHeight = Math.floor(screenHeight * 0.8);
    
    // Limit max height to 70% of screen height
    const newHeight = Math.min(Math.max(height, 80), maxHeight); // At least 80px
    const currentSize = overlayWindow.getSize();
    const currentWidth = currentSize[0];
    const currentHeight = currentSize[1];
    
    console.log(`Resize overlay height: current=${currentHeight}px, requested=${height}px, actual=${newHeight}px, max=${maxHeight}px`);
    
    // Use setBounds instead of setSize, more reliable
    const bounds = overlayWindow.getBounds();
    overlayWindow.setBounds({
      x: bounds.x,
      y: bounds.y,
      width: currentWidth,
      height: newHeight
    });
    
    // Force refresh window
    overlayWindow.setSize(currentWidth, newHeight);
  }
}

// Send message to all windows
function sendToWindows(channel, ...args) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, ...args);
  }
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send(channel, ...args);
  }
}

// Screenshot function
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
      
      // 🚨 Add data URL prefix so browser can recognize it
      const dataUrl = `data:image/png;base64,${base64Image}`;
      currentScreenshot = dataUrl;
      
      sendToWindows('screenshot-taken', dataUrl);
      
      // Focus overlay window
      if (overlayWindow && !overlayWindow.isDestroyed()) {
        overlayWindow.show();
        overlayWindow.focus();
      }
      
      return dataUrl;
    }
  } catch (error) {
    console.error('Screenshot failed:', error);
    sendToWindows('screenshot-error', error.message);
  }
  return null;
}

// Register global shortcuts
function registerShortcuts() {
  // Ctrl+H: Screenshot
  globalShortcut.register('CommandOrControl+H', async () => {
    console.log('Shortcut triggered: Ctrl+H (Screenshot)');
    await captureScreen();
  });

  // Ctrl+Enter: Send screenshot to backend
  globalShortcut.register('CommandOrControl+Enter', () => {
    console.log('Shortcut triggered: Ctrl+Enter (Send screenshot)');
    if (currentScreenshot) {
      sendToWindows('send-screenshot-request', currentScreenshot);
    } else {
      sendToWindows('screenshot-error', 'No screenshot available, please press Ctrl+H to capture first');
    }
  });

  // Ctrl+B: Toggle overlay window show/hide
  globalShortcut.register('CommandOrControl+B', () => {
    console.log('Shortcut triggered: Ctrl+B (Toggle overlay)');
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      if (overlayWindow.isVisible()) {
        overlayWindow.hide();
        console.log('Overlay window hidden');
      } else {
        overlayWindow.show();
        console.log('Overlay window shown');
      }
    }
  });

  // Ctrl+Shift+I or F12: Toggle DevTools
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    console.log('Shortcut triggered: Ctrl+Shift+I (Toggle DevTools)');
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools();
        console.log('DevTools closed');
      } else {
        mainWindow.webContents.openDevTools();
        console.log('DevTools opened');
      }
    }
  });

  // F12: Toggle DevTools (alternative)
  globalShortcut.register('F12', () => {
    console.log('Shortcut triggered: F12 (Toggle DevTools)');
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools();
        console.log('DevTools closed');
      } else {
        mainWindow.webContents.openDevTools();
        console.log('DevTools opened');
      }
    }
  });

  // 🚨 Ctrl+Up/Down: Scroll content (only scroll internal content of single reply box)
  const upRegistered = globalShortcut.register('CommandOrControl+Up', () => {
    console.log('Shortcut triggered: Ctrl+Up (Scroll up)');
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.webContents.executeJavaScript(`
        (function() {
          try {
            // 🚨 Only find reply box, don't scroll conversation history area
            const el = document.querySelector('.overlay-response');
            
            if (!el) return '❌ .overlay-response not found';
            
            // Check if scrollable
            if (el.scrollHeight <= el.clientHeight) {
              return '⚠️ .overlay-response content does not need scrolling [scrollHeight: ' + el.scrollHeight + ', clientHeight: ' + el.clientHeight + ']';
            }
            
            const start = el.scrollTop;
            el.scrollTop -= 100;
            const end = el.scrollTop;
            
            return '✅ Scrolled up (.overlay-response): ' + start + ' -> ' + end + 
                   ' [scrollHeight: ' + el.scrollHeight + ', clientHeight: ' + el.clientHeight + ']';
          } catch (e) {
            return '❌ JS Error: ' + e.message;
          }
        })()
      `).then(result => console.log(result)).catch(err => console.error('ExecJS Failed:', err));
    }
  });
  console.log('Ctrl+Up registration result:', upRegistered ? 'Success' : 'Failed (may be occupied)');

  const downRegistered = globalShortcut.register('CommandOrControl+Down', () => {
    console.log('Shortcut triggered: Ctrl+Down (Scroll down)');
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.webContents.executeJavaScript(`
        (function() {
          try {
            // 🚨 Only find reply box, don't scroll conversation history area
            const el = document.querySelector('.overlay-response');
            
            if (!el) return '❌ .overlay-response not found';
            
            // Check if scrollable
            if (el.scrollHeight <= el.clientHeight) {
              return '⚠️ .overlay-response content does not need scrolling [scrollHeight: ' + el.scrollHeight + ', clientHeight: ' + el.clientHeight + ']';
            }
            
            const start = el.scrollTop;
            el.scrollTop += 100;
            const end = el.scrollTop;
            
            return '✅ Scrolled down (.overlay-response): ' + start + ' -> ' + end + 
                   ' [scrollHeight: ' + el.scrollHeight + ', clientHeight: ' + el.clientHeight + ']';
          } catch (e) {
            return '❌ JS Error: ' + e.message;
          }
        })()
      `).then(result => console.log(result)).catch(err => console.error('ExecJS Failed:', err));
    }
  });
  console.log('Ctrl+Down registration result:', downRegistered ? 'Success' : 'Failed (may be occupied)');

  // Move overlay window (Ctrl + Arrow Keys)
  const moveStep = 20; // Move 20px each time

  const moveWindow = (dx, dy, name) => {
    console.log(`Attempting to move window (${name}): dx=${dx}, dy=${dy}`);
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      if (!overlayWindow.isVisible()) {
        console.log('Window not visible, forcing show');
        overlayWindow.show();
      }
      
      const bounds = overlayWindow.getBounds();
      console.log(`Current position: x=${bounds.x}, y=${bounds.y}`);
      
      overlayWindow.setBounds({
        x: bounds.x + dx,
        y: bounds.y + dy,
        width: bounds.width,
        height: bounds.height
      });
      console.log(`New position: x=${bounds.x + dx}, y=${bounds.y + dy}`);
    } else {
      console.log('Window does not exist or has been destroyed');
    }
  };

  // Register move shortcuts - removed, changed to frontend listener (Local Shortcut)
  // This only works when overlay window has focus, doesn't affect system
  /*
  // Option C: Ctrl + Alt + WASD (absolutely no conflict)
  registerMoveKey('CommandOrControl+Alt+W', 0, -moveStep, 'Up');
  registerMoveKey('CommandOrControl+Alt+S', 0, moveStep, 'Down');
  registerMoveKey('CommandOrControl+Alt+A', -moveStep, 0, 'Left');
  registerMoveKey('CommandOrControl+Alt+D', moveStep, 0, 'Right');
  */

  console.log('Global shortcuts registered:');
  console.log('  Ctrl+H: Screenshot');
  console.log('  Ctrl+Enter: Send screenshot for analysis');
  console.log('  Ctrl+B: Toggle overlay window show/hide');
  console.log('  Ctrl+Shift+I or F12: Toggle DevTools');
  console.log('  Ctrl+Up: Scroll up');
  console.log('  Ctrl+Down: Scroll down');
  console.log('  Ctrl+Left: Move left');
  console.log('  Ctrl+Right: Move right');
}

// 🔒 IPC: User logged in successfully, create overlay window
ipcMain.handle('user-logged-in', () => {
  console.log('🔐 User logged in, creating overlay window');
  if (!overlayWindow || overlayWindow.isDestroyed()) {
    createOverlayWindow();
  } else {
    overlayWindow.show();
  }
  return { success: true };
});

// 🔒 IPC: User logged out, close overlay window
ipcMain.handle('user-logged-out', () => {
  console.log('🚪 User logged out, closing overlay window');
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.close();
    overlayWindow = null;
  }
  return { success: true };
});

// Helper function: Send HTTP request in Node.js
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
    
    console.log('🔐 Sending HTTP request:', requestOptions.method, requestOptions.hostname + requestOptions.path);
    
    const req = httpModule.request(requestOptions, (res) => {
      let data = '';
      
      console.log('🔐 Received response:', res.statusCode, res.statusMessage);
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        console.log('🔐 Response data length:', data.length);
        console.log('🔐 Response status code:', res.statusCode);
        console.log('🔐 Response headers:', res.headers);
        console.log('🔐 Response data preview:', data.substring(0, Math.min(500, data.length)));
        
        try {
          const jsonData = JSON.parse(data);
          resolve({ 
            status: res.statusCode, 
            ok: res.statusCode >= 200 && res.statusCode < 300, 
            json: () => Promise.resolve(jsonData), 
            text: () => Promise.resolve(data) 
          });
        } catch (e) {
          console.error('🔐 JSON parse failed:', e.message);
          console.error('🔐 Raw data:', data);
          // Even if JSON parse fails, return response object for caller to handle
          resolve({ 
            status: res.statusCode, 
            ok: res.statusCode >= 200 && res.statusCode < 300, 
            json: () => Promise.reject(new Error(`JSON parse error: ${e.message}. Data: ${data.substring(0, 200)}`)), 
            text: () => Promise.resolve(data) 
          });
        }
      });
    });
    
    req.on('error', (error) => {
      console.error('🔐 HTTP request error:', error.message);
      reject(error);
    });
    
    // Set timeout
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

// 🔐 IPC: Google OAuth login
ipcMain.handle('oauth-google', async () => {
  console.log('🔐 [MAIN] oauth-google handler called');
  return new Promise(async (resolve, reject) => {
    try {
      console.log('🔐 [MAIN] Starting OAuth flow...');
      // Get OAuth URL (needs to be fetched from API)
      // Desktop architecture: All API requests go directly to Vercel (no local backend dependency)
      // If local backend is needed, can specify via LOCAL_API_URL environment variable
      const isDev = !app.isPackaged;
      
      // Hard clean function: ensure URL has no leading/trailing whitespace
      const clean = (s) => (s ?? "").trim();
      
      // Alert-level logging: print raw environment variable values (for troubleshooting configuration issues)
      console.log("🔍 LOCAL_API_URL raw:", JSON.stringify(process.env.LOCAL_API_URL));
      console.log("🔍 VERCEL_API_URL raw:", JSON.stringify(process.env.VERCEL_API_URL));
      
      const API_BASE_URL = clean(process.env.LOCAL_API_URL) 
        || clean(process.env.VERCEL_API_URL) 
        || clean('https://www.desktopai.org');
      // NEW ARCHITECTURE: Desktop platform always uses Vercel backend callback
      // Backend will automatically set redirect_to to Vercel /api/auth/callback?platform=desktop
      // No need to pass redirect_to - backend handles it based on platform parameter
      const apiUrl = `${API_BASE_URL}/api/auth/google/url?platform=desktop`;
      console.log('🔐 Requesting OAuth URL for desktop platform:', apiUrl);
      console.log('🔐 API_BASE_URL:', API_BASE_URL);
      console.log('🔐 Platform: desktop (backend will set correct callback URL)');
      console.log('🔐 isDev:', isDev);
      console.log('🔐 isPackaged:', app.isPackaged);
      
      let response;
      try {
        console.log('🔐 [MAIN] Sending HTTP request to:', apiUrl);
        response = await httpRequest(apiUrl);
        console.log('🔐 [MAIN] API response status:', response.status, 'OK:', response.ok);
      } catch (httpError) {
        console.error('🔐 [MAIN] HTTP request failed:', httpError);
        console.error('🔐 [MAIN] Error details:', httpError.message);
        console.error('🔐 [MAIN] Error stack:', httpError.stack);
        reject(new Error(`HTTP request failed: ${httpError.message}`));
        return;
      }
      
      if (!response.ok) {
        let errorText = 'Unknown error';
        let errorJson = null;
        try {
          errorText = await response.text();
          // Try to parse as JSON
          try {
            errorJson = JSON.parse(errorText);
            console.error('🔐 API error response (JSON):', JSON.stringify(errorJson, null, 2));
          } catch (e) {
            // Not JSON, use raw text
            console.error('🔐 API error response (text):', errorText);
          }
        } catch (e) {
          console.error('🔐 Unable to read error response:', e);
        }
        console.error('🔐 API error response status:', response.status);
        const errorMessage = errorJson?.detail || errorJson?.error || errorText;
        throw new Error(`Failed to get OAuth URL: HTTP ${response.status} - ${errorMessage}`);
      }
      
      let data;
      try {
        data = await response.json();
        console.log('🔐 API response data:', JSON.stringify(data, null, 2));
      } catch (jsonError) {
        const errorText = await response.text();
        console.error('🔐 JSON parse failed, raw response:', errorText);
        throw new Error(`Failed to parse API response: ${jsonError.message}. Response: ${errorText.substring(0, 200)}`);
      }
      
      if (!data) {
        throw new Error('Invalid response: response is null or undefined');
      }
      
      if (!data.url) {
        console.error('🔐 Response missing url field, full response:', JSON.stringify(data, null, 2));
        
        // Check if it's an error response
        if (data.error || data.details) {
          const errorMsg = data.details || data.error || 'Unknown error';
          const errorDetails = data.traceback ? `\n\nDetails:\n${data.traceback.substring(0, 500)}` : '';
          throw new Error(`API returned error: ${errorMsg}${errorDetails}`);
        }
        
        throw new Error(`Invalid response: missing url field. Response keys: ${Object.keys(data).join(', ')}`);
      }
      
      const authUrl = data.url;
      
      console.log('🔐 [MAIN] Got OAuth URL, length:', authUrl.length);
      // No code_verifier needed - backend handles OAuth callback directly
      
      console.log('🔐 [MAIN] Opening Google OAuth window...');
      
      // Create OAuth window
      // Note: OAuth window needs to load frontend page so frontend can use Supabase JS SDK to handle PKCE
      try {
        oauthWindow = new BrowserWindow({
          width: 500,
          height: 600,
          modal: true,
          parent: mainWindow,
          show: false,
          webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),  // Need preload so frontend can communicate
            // Disable webSecurity in development to allow cross-origin requests (development only)
            webSecurity: !isDev // Disabled in development, enabled in production
          }
        });
        console.log('🔐 [MAIN] OAuth window created successfully');
      } catch (windowError) {
        console.error('🔐 [MAIN] Failed to create OAuth window:', windowError);
        reject(new Error(`Failed to create OAuth window: ${windowError.message}`));
        return;
      }
      
      // Listen to window ready to show
      oauthWindow.once('ready-to-show', () => {
        console.log('🔐 [MAIN] OAuth window ready to show');
        oauthWindow.show();
      });
      
      // Listen to window errors
      oauthWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        console.error('🔐 [MAIN] OAuth window failed to load:', errorCode, errorDescription);
        reject(new Error(`OAuth window failed to load: ${errorDescription}`));
      });
      
      // NEW ARCHITECTURE: Load OAuth URL directly
      // OAuth flow: Google → Supabase → /api/auth/callback?platform=desktop
      // Backend callback returns HTML with postMessage to send token back
      console.log('🔐 Loading OAuth URL directly:', authUrl.substring(0, 100) + '...');
      oauthWindow.loadURL(authUrl);
      
      // Listen for postMessage from OAuth callback page
      console.log('🔐 Setting up postMessage listener for OAuth callback...');
      
      // Inject script into OAuth window after callback page loads
      // Callback page will extract tokens from hash and send via postMessage
      oauthWindow.webContents.on('did-finish-load', () => {
        const currentUrl = oauthWindow.webContents.getURL();
        console.log('🔐 OAuth window loaded:', currentUrl.substring(0, 100) + '...');
        
        // Check if we're on the callback page
        if (currentUrl.includes('/api/auth/callback')) {
          console.log('🔐 Detected callback page, callback HTML should handle postMessage');
          // Backend HTML already has script to extract tokens and send postMessage
          // Main window's preload script will receive it and forward via IPC
        }
      });
      
      // Listen for IPC message from OAuth window's preload script
      // OAuth window receives postMessage from callback page and forwards via IPC
      ipcMain.once('oauth-desktop-success', (event, data) => {
        console.log('🔐 Received OAuth success from callback page:', {
          hasAccessToken: !!data.access_token,
          hasUser: !!data.user
        });
        
        if (oauthWindow && !oauthWindow.isDestroyed()) {
          console.log('🔐 Closing OAuth window');
          oauthWindow.close();
        }
        
        if (data && data.access_token && data.user) {
          console.log('🔐 OAuth success, resolving with token data');
          resolve({
            success: true,
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            user: data.user
          });
        } else {
          const errorMsg = 'OAuth callback failed: missing token or user data';
          console.error('🔐 OAuth failed:', errorMsg);
          reject(new Error(errorMsg));
        }
      });
      
      // Add timeout to prevent hanging forever
      setTimeout(() => {
        if (oauthWindow && !oauthWindow.isDestroyed()) {
        console.warn('🔐 OAuth timeout: No result received after 5 minutes, closing window');
        oauthWindow.close();
        reject(new Error('OAuth timeout: No response from OAuth callback'));
        }
      }, 5 * 60 * 1000); // 5 minutes timeout
      
      // Listen to window close
      oauthWindow.on('closed', () => {
        console.log('🔐 OAuth window closed');
        oauthWindow = null;
        
        // Notify main window to refresh login status
        // Whether login succeeds or fails, should check again
        if (mainWindow && !mainWindow.isDestroyed()) {
          console.log('🔐 Notifying main window to refresh login status');
          mainWindow.webContents.send('auth:refresh');
        }
        
        // If window closes without receiving result, user may have cancelled
        // But don't reject, as frontend might still be processing
      });
      
      // Listen to navigation, capture callback URL (when Google redirects to callback URL)
      // NOTE: In dev mode, redirect_to now uses hash route (#/auth/callback), so we let navigation happen naturally
      // No need to intercept and modify hash, as OAuth callback will directly navigate to the correct hash URL
      oauthWindow.webContents.on('will-navigate', (event, url) => {
        console.log('🔐 OAuth window navigating to:', url);
        // Check if it's a callback URL (contains code)
        try {
          const urlObj = new URL(url);
          console.log('🔐 URL parse result:', {
            hostname: urlObj.hostname,
            pathname: urlObj.pathname,
            hash: urlObj.hash,
            hasCode: urlObj.searchParams.has('code') || urlObj.hash.includes('code='),
            hasError: urlObj.searchParams.has('error') || urlObj.hash.includes('error=')
          });
          
          // Only handle errors, let successful callbacks navigate naturally
          const error = urlObj.searchParams.get('error') || (urlObj.hash.includes('error=') ? new URLSearchParams(urlObj.hash.split('?')[1] || '').get('error') : null);
          if (error) {
            console.error('🔐 OAuth error:', error);
            event.preventDefault();
            if (oauthWindow && !oauthWindow.isDestroyed()) {
              oauthWindow.close();
            }
            reject(new Error(`OAuth error: ${error}`));
          }
          // Let all other navigation proceed naturally, especially hash-based callbacks
        } catch (e) {
          // URL parse failed, ignore and let navigation proceed
          console.error('🔐 URL parse failed:', e);
        }
      });
      
      // Listen to did-navigate to detect when OAuth callback completes
      // CRITICAL: Parse hash directly from URL (Supabase puts tokens in hash, not query)
      oauthWindow.webContents.on('did-navigate', (event, url) => {
        console.log('🔐 OAuth window navigated to:', url);
        try {
          const urlObj = new URL(url);
          const hostname = urlObj.hostname;
          const pathname = urlObj.pathname;
          const hash = urlObj.hash || '';
          
          console.log('🔐 did-navigate URL parse result:', {
            hostname,
            pathname,
            hash: hash.substring(0, 100) + (hash.length > 100 ? '...' : ''),
          });
          
          // Check if this is the backend callback URL
          const isBackendCallback = (
            (hostname === 'localhost' || hostname === '127.0.0.1') && 
            urlObj.port === '5173' &&
            pathname === '/api/auth/callback'
          ) || (
            hostname === 'www.desktopai.org' &&
            pathname === '/api/auth/callback'
          );
          
          if (isBackendCallback && hash.startsWith('#')) {
            console.log('🔐 [MAIN] Detected backend callback URL with hash - parsing tokens');
            
            // Parse hash parameters (#access_token=xxx&refresh_token=yyy&...)
            const hashParams = new URLSearchParams(hash.substring(1)); // Remove '#'
            const accessToken = hashParams.get('access_token');
            const refreshToken = hashParams.get('refresh_token');
            const expiresAt = hashParams.get('expires_at');
            const expiresIn = hashParams.get('expires_in');
            const tokenType = hashParams.get('token_type') || 'bearer';
            
            console.log('🔐 Parsed tokens from hash:', {
              hasAccessToken: !!accessToken,
              hasRefreshToken: !!refreshToken,
              expiresAt,
              expiresIn,
              tokenType,
            });
            
            if (accessToken) {
              // Extract user info from access token (JWT payload)
              let user = null;
              try {
                // JWT format: header.payload.signature
                // We only need the payload part (middle section)
                const parts = accessToken.split('.');
                if (parts.length === 3) {
                  const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
                  user = {
                    id: payload.sub || payload.user_id || null,
                    email: payload.email || null,
                  };
                }
              } catch (e) {
                console.warn('🔐 Could not parse user from JWT:', e);
              }
              
              // Send token to renderer via IPC
              if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('auth:oauth-complete', {
                  access_token: accessToken,
                  refresh_token: refreshToken,
                  expires_at: expiresAt ? parseInt(expiresAt, 10) : undefined,
                  expires_in: expiresIn ? parseInt(expiresIn, 10) : undefined,
                  token_type: tokenType,
                  user: user,
                });
                console.log('🔐 Sent auth:oauth-complete to renderer');
              }
              
              // Close OAuth window
              setTimeout(() => {
                if (oauthWindow && !oauthWindow.isDestroyed()) {
                  console.log('🔐 Closing OAuth window after successful token extraction');
                  oauthWindow.close();
                }
              }, 500);
              
              // Resolve OAuth promise
              resolve({
                success: true,
                access_token: accessToken,
                refresh_token: refreshToken,
                user: user,
              });
            } else {
              console.warn('❌ No access_token found in hash, cannot complete login');
            }
          }
        } catch (e) {
          console.error('🔐 did-navigate URL parse failed:', e);
        }
      });
      
    } catch (error) {
      console.error('🔐 OAuth error:', error);
      console.error('🔐 Error stack:', error.stack);
      reject(new Error(error.message || 'Failed to initiate Google OAuth'));
    }
  });
});

// 🎯 IPC handlers: Scene related
ipcMain.handle('get-all-scenes', async () => {
  return await getAllScenes();
});

ipcMain.handle('select-scenario', async (event, { sceneId, presetId }) => {
  const scenes = await getAllScenes();
  let selectedPrompt = '';
  
  // Find scene
  const allScenes = [...scenes.builtIn, scenes.general, ...scenes.custom];
  const scene = allScenes.find(s => s.id === sceneId);
  if (scene) {
    const preset = scene.presets.find(p => p.id === presetId);
    if (preset) {
      selectedPrompt = preset.prompt;
    }
  }
  
  // Notify all windows that scene has been selected
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
  // When scene is updated, refresh menu
  await updateApplicationScenarioMenu();
});

// IPC event handlers
ipcMain.handle('capture-screen', async () => {
  return await captureScreen();
});

ipcMain.handle('send-to-backend', async (event, imageBase64) => {
  // Frontend will call backend API itself, this handler can be used for future extensions
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

// Control click-through (dynamically switch based on mouse position)
ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    const winOptions = options || { forward: true };
    overlayWindow.setIgnoreMouseEvents(ignore, winOptions);
    // console.log(`Click-through updated: ${ignore} (forward: ${winOptions.forward})`);
  }
});

// Open main window
ipcMain.on('open-main-window', () => {
  console.log('🔔 Received open main window request');
  console.log('Current mainWindow status:', mainWindow ? 'Exists' : 'Does not exist', mainWindow && !mainWindow.isDestroyed() ? 'Not destroyed' : 'Destroyed');
  
  if (mainWindow && !mainWindow.isDestroyed()) {
    console.log('Showing existing main window');
    
    // 🚨 Ensure window is visible
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
      console.log('Restored from minimized state');
    }
    
    mainWindow.show();
    mainWindow.focus();
    mainWindow.moveTop(); // 🚨 Bring to front
    
    console.log('✅ Main window shown and focused');
    console.log('Window visible:', mainWindow.isVisible());
    console.log('Window focused:', mainWindow.isFocused());
  } else {
    console.log('Creating new main window');
    createMainWindow();
    console.log('✅ New main window created');
  }
});

// Receive move request from frontend
ipcMain.on('move-overlay', (event, { direction, step }) => {
  console.log(`IPC received move request: direction=${direction}, step=${step}`);
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
    
    console.log(`Screen size: ${screenWidth}x${screenHeight}`);
    console.log(`Current window: x=${bounds.x}, y=${bounds.y}, width=${bounds.width}, height=${bounds.height}`);
    
    // Calculate new position
    let newX = bounds.x + dx;
    let newY = bounds.y + dy;
    
    console.log(`Calculated new position (before boundary check): x=${newX}, y=${newY}`);
    
    // Boundary check: prevent window from moving off screen
    // Left boundary
    if (newX < 0) {
      console.log(`Hit left boundary, limiting x from ${newX} to 0`);
      newX = 0;
    }
    // Right boundary (window right edge cannot exceed screen right edge)
    if (newX + bounds.width > screenWidth) {
      console.log(`Hit right boundary, limiting x from ${newX} to ${screenWidth - bounds.width}`);
      newX = screenWidth - bounds.width;
    }
    // Top boundary
    if (newY < 0) {
      console.log(`Hit top boundary, limiting y from ${newY} to 0`);
      newY = 0;
    }
    // Bottom boundary (window bottom edge cannot exceed screen bottom edge)
    if (newY + bounds.height > screenHeight) {
      console.log(`Hit bottom boundary, limiting y from ${newY} to ${screenHeight - bounds.height}`);
      newY = screenHeight - bounds.height;
    }
    
    console.log(`Final position (after boundary check): x=${newX}, y=${newY}`);
    
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

// 🎤 IPC: Local speech-to-text (using local Whisper)
ipcMain.handle('speech-to-text-local', async (event, audioData, language = 'zh') => {
  try {
    // Get Python interpreter path
    const isDev = !app.isPackaged;
    let pythonPath;
    let whisperScriptPath;
    
    if (isDev) {
      // Development: use system Python or venv
      pythonPath = process.platform === 'win32' ? 'python' : 'python3';
      whisperScriptPath = path.join(__dirname, 'whisper_local.py');
    } else {
      // Production: use packaged Python (needs configuration)
      // Here assumes Python is in system PATH, or you need to configure specific path
      pythonPath = process.platform === 'win32' ? 'python' : 'python3';
      whisperScriptPath = path.join(process.resourcesPath, 'whisper_local.py');
    }
    
    // Create temporary audio file
    const tempDir = require('os').tmpdir();
    const tempAudioPath = path.join(tempDir, `audio_${Date.now()}.webm`);
    
    // Write base64 or Buffer to file
    let audioBuffer;
    if (typeof audioData === 'string') {
      // Base64 string
      audioBuffer = Buffer.from(audioData, 'base64');
    } else if (Buffer.isBuffer(audioData)) {
      audioBuffer = audioData;
    } else {
      throw new Error('Unsupported audio data format');
    }
    
    await writeFile(tempAudioPath, audioBuffer);
    
    console.log('🎤 Starting local speech-to-text, audio file:', tempAudioPath);
    
    // Call Python script
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
        // Print progress info to console
        console.log('Whisper:', data.toString().trim());
      });
      
      pythonProcess.on('close', async (code) => {
        // Clean up temporary file
        try {
          await unlink(tempAudioPath);
        } catch (err) {
          console.error('Failed to clean up temporary file:', err);
        }
        
        if (code !== 0) {
          console.error('Whisper processing failed, exit code:', code);
          console.error('stderr:', stderr);
          reject(new Error(`Whisper processing failed: ${stderr || 'Unknown error'}`));
          return;
        }
        
        try {
          // Parse JSON output
          const result = JSON.parse(stdout.trim());
          console.log('✅ Local speech-to-text completed:', result);
          resolve(result);
        } catch (err) {
          console.error('Failed to parse Whisper output:', err);
          console.error('stdout:', stdout);
          reject(new Error('Failed to parse Whisper output'));
        }
      });
      
      pythonProcess.on('error', async (err) => {
        // Clean up temporary file
        try {
          await unlink(tempAudioPath);
        } catch (unlinkErr) {
          console.error('Failed to clean up temporary file:', unlinkErr);
        }
        
        console.error('Failed to start Whisper process:', err);
        reject(new Error(`Unable to start Whisper: ${err.message}`));
      });
    });
  } catch (error) {
    console.error('❌ Local speech-to-text failed:', error);
    return {
      success: false,
      error: error.message,
      text: '',
      language: '',
      duration: 0.0
    };
  }
});

// 📁 IPC: Select folder
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
    console.error('❌ Failed to select folder:', error);
    return { canceled: true, path: null, error: error.message };
  }
});

// ⚠️ IPC: Show Token usage warning
ipcMain.on('show-token-warning', (event, message, usagePercentage) => {
  try {
    // Use Electron native notification
    if (Notification.isSupported()) {
      const notification = new Notification({
        title: '⚠️ Token Usage Warning',
        body: `You have used ${usagePercentage}% of your Token quota. Remaining quota is limited. Please use wisely.`,
        icon: path.join(__dirname, '../resources/icon.png'),
        urgency: 'normal',
        timeoutType: 'never' // Don't auto-dismiss, let user close manually
      });

      notification.show();

      // Optional: Focus main window when notification is clicked
      notification.on('click', () => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.focus();
        }
      });
    } else {
      // Fallback to dialog
      const win = BrowserWindow.fromWebContents(event.sender);
      dialog.showMessageBox(win || mainWindow, {
        type: 'warning',
        title: '⚠️ Token Usage Warning',
        message: `You have used ${usagePercentage}% of your Token quota`,
        detail: message,
        buttons: ['Got it'],
        defaultId: 0
      });
    }
    
    console.warn('⚠️ Token usage warning:', message);
  } catch (error) {
    console.error('❌ Failed to show Token warning:', error);
  }
});

// Global error handling
process.on('uncaughtException', (error) => {
  console.error('🚨 Uncaught exception:', error);
  logStream.end();
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('🚨 Unhandled Promise rejection:', reason);
  logStream.end();
});

app.whenReady().then(async () => {
  createMainWindow();
  // 🔒 Don't auto-create overlay window, wait for main window to notify user is logged in
  // createOverlayWindow();
  await createMenu(); // 🔑 Create menu
  registerShortcuts();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
      // 🔒 Don't auto-create overlay window
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
  // Unregister all shortcuts
  globalShortcut.unregisterAll();
  // Close log stream
  logStream.end();
  console.log('📝 Log saved to:', logFile);
});

app.on('before-quit', () => {
  console.log('🛑 App is about to quit');
});

