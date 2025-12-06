import React, { useState, useEffect } from 'react';
import './SettingsDialog.css';

interface SettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Shortcut {
  key: string;
  description: string;
}

const SHORTCUTS: Shortcut[] = [
  { key: 'Ctrl+H', description: 'Take Screenshot' },
  { key: 'Ctrl+Enter', description: 'Send screenshot for analysis' },
  { key: 'Ctrl+B', description: 'Toggle overlay window show/hide' },
  { key: 'Ctrl+Up', description: 'Scroll up in AI response' },
  { key: 'Ctrl+Down', description: 'Scroll down in AI response' },
  { key: 'Ctrl+Left', description: 'Move overlay window left' },
  { key: 'Ctrl+Right', description: 'Move overlay window right' },
  { key: 'Ctrl+S', description: 'Toggle focus/transparent mode' },
  { key: 'Ctrl+N', description: 'Create new session' },
  { key: 'Ctrl+D', description: 'Clear all screenshots' },
  { key: 'Ctrl+T', description: 'Start/Stop voice recording' },
];

export const SettingsDialog: React.FC<SettingsDialogProps> = ({ isOpen, onClose }) => {
  const [promptStoragePath, setPromptStoragePath] = useState('');
  const [sessionStoragePath, setSessionStoragePath] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isElectron, setIsElectron] = useState(false);

  useEffect(() => {
    // Check if running in Electron - just check for window.aiShot existence
    // selectFolder might not be immediately available but we're still in Electron
    const checkElectron = () => {
      const hasAiShot = typeof window !== 'undefined' && (window as any).aiShot !== undefined;
      console.log('🔍 Electron check:', { 
        hasAiShot, 
        aiShotKeys: hasAiShot ? Object.keys((window as any).aiShot) : [],
        hasSelectFolder: hasAiShot && typeof (window as any).aiShot?.selectFolder === 'function'
      });
      // If window.aiShot exists, we're in Electron (even if selectFolder isn't ready yet)
      setIsElectron(hasAiShot);
    };
    
    // Check immediately
    checkElectron();
    
    // Also check after a short delay in case window.aiShot loads later
    const timeout = setTimeout(checkElectron, 500);
    const timeout2 = setTimeout(checkElectron, 1000);
    
    // Load settings from localStorage
    const savedPromptPath = localStorage.getItem('promptStoragePath') || '';
    const savedSessionPath = localStorage.getItem('sessionStoragePath') || '';

    setPromptStoragePath(savedPromptPath);
    setSessionStoragePath(savedSessionPath);
    
    return () => {
      clearTimeout(timeout);
      clearTimeout(timeout2);
    };
  }, []);

  const handleSave = () => {
    try {
      // Save storage paths
      localStorage.setItem('promptStoragePath', promptStoragePath);
      localStorage.setItem('sessionStoragePath', sessionStoragePath);

      setMessage({ type: 'success', text: 'Settings saved successfully!' });
      
      // Trigger event to notify other components
      window.dispatchEvent(new CustomEvent('settingsUpdated'));
      
      setTimeout(() => {
        setMessage(null);
      }, 2000);
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save settings: ' + (error as Error).message });
    }
  };

  const handleSelectPromptPath = async () => {
    // Check Electron environment again at runtime
    const hasAiShot = typeof window !== 'undefined' && (window as any).aiShot !== undefined;
    const hasSelectFolder = hasAiShot && typeof (window as any).aiShot?.selectFolder === 'function';
    
    console.log('🔍 Checking Electron environment:', {
      isElectron,
      hasAiShot,
      hasSelectFolder,
      aiShotKeys: hasAiShot ? Object.keys((window as any).aiShot) : [],
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'N/A'
    });

    if (!hasAiShot) {
      setMessage({ 
        type: 'error', 
        text: 'Electron API not detected. Please restart the app.' 
      });
      setTimeout(() => setMessage(null), 5000);
      return;
    }

    if (!hasSelectFolder) {
      setMessage({ 
        type: 'error', 
        text: 'Folder selection API is not available. Please restart the app to load all features.' 
      });
      setTimeout(() => setMessage(null), 5000);
      return;
    }

    try {
      const result = await (window as any).aiShot.selectFolder({
        title: 'Select Folder for Prompts',
        defaultPath: promptStoragePath || undefined
      });

      if (!result.canceled && result.path) {
        setPromptStoragePath(result.path);
        setMessage({ type: 'success', text: 'Prompt storage path selected successfully!' });
        setTimeout(() => setMessage(null), 2000);
      }
    } catch (error) {
      console.error('Failed to select folder:', error);
      setMessage({ type: 'error', text: 'Failed to select folder: ' + (error as Error).message });
      setTimeout(() => setMessage(null), 5000);
    }
  };

  const handleSelectSessionPath = async () => {
    // Check Electron environment again at runtime
    const hasAiShot = typeof window !== 'undefined' && (window as any).aiShot !== undefined;
    const hasSelectFolder = hasAiShot && typeof (window as any).aiShot?.selectFolder === 'function';
    
    console.log('🔍 Checking Electron environment:', {
      isElectron,
      hasAiShot,
      hasSelectFolder,
      aiShotKeys: hasAiShot ? Object.keys((window as any).aiShot) : [],
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'N/A'
    });

    if (!hasAiShot) {
      setMessage({ 
        type: 'error', 
        text: 'Electron API not detected. Please restart the app.' 
      });
      setTimeout(() => setMessage(null), 5000);
      return;
    }

    if (!hasSelectFolder) {
      setMessage({ 
        type: 'error', 
        text: 'Folder selection API is not available. Please restart the app to load all features.' 
      });
      setTimeout(() => setMessage(null), 5000);
      return;
    }

    try {
      const result = await (window as any).aiShot.selectFolder({
        title: 'Select Folder for Chat Sessions',
        defaultPath: sessionStoragePath || undefined
      });

      if (!result.canceled && result.path) {
        setSessionStoragePath(result.path);
        setMessage({ type: 'success', text: 'Session storage path selected successfully!' });
        setTimeout(() => setMessage(null), 2000);
      }
    } catch (error) {
      console.error('Failed to select folder:', error);
      setMessage({ type: 'error', text: 'Failed to select folder: ' + (error as Error).message });
      setTimeout(() => setMessage(null), 5000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="settings-dialog-overlay" onClick={onClose}>
      <div className="settings-dialog-content" onClick={(e) => e.stopPropagation()}>
        <div className="settings-dialog-header">
          <h2>⚙️ Settings</h2>
          <button className="settings-close-btn" onClick={onClose}>×</button>
        </div>

        {message && (
          <div className={`settings-message settings-message-${message.type}`}>
            {message.text}
          </div>
        )}

        <div className="settings-dialog-body">
          {/* Keyboard Shortcuts Section */}
          <section className="settings-section">
            <h3>⌨️ Keyboard Shortcuts</h3>
            <div className="shortcuts-list">
              {SHORTCUTS.map((shortcut, index) => (
                <div key={index} className="shortcut-item">
                  <kbd className="shortcut-key">{shortcut.key}</kbd>
                  <span className="shortcut-description">{shortcut.description}</span>
                </div>
              ))}
            </div>
            {!isElectron && (
              <p className="settings-hint">
                Note: Global shortcuts are only available in Electron desktop app.
              </p>
            )}
          </section>

          {/* Prompt Storage Path Section */}
          <section className="settings-section">
            <h3>📝 Prompt Storage Location</h3>
            <p className="settings-description">
              Choose where to store custom prompts and prompt templates.
              {!isElectron && ' Folder selection is only available in Electron desktop app.'}
            </p>
            <div className="settings-path-input">
              <input
                type="text"
                value={promptStoragePath}
                onChange={(e) => setPromptStoragePath(e.target.value)}
                placeholder={isElectron ? "Enter folder path for prompts..." : "Not available in web version"}
                className="settings-input"
                disabled={!isElectron}
              />
              <button 
                className="settings-btn settings-btn-secondary" 
                onClick={handleSelectPromptPath}
                disabled={!isElectron}
                title={isElectron ? "Select folder for storing prompts" : "Only available in Electron desktop app"}
              >
                Browse...
              </button>
            </div>
            {!promptStoragePath && (
              <p className="settings-hint">
                Leave empty to use default location (localStorage for web, app userData for Electron).
              </p>
            )}
          </section>

          {/* Session Storage Path Section */}
          <section className="settings-section">
            <h3>💾 Chat Session Storage Location</h3>
            <p className="settings-description">
              Choose where to store chat conversation history.
              {!isElectron && ' Folder selection is only available in Electron desktop app.'}
            </p>
            <div className="settings-path-input">
              <input
                type="text"
                value={sessionStoragePath}
                onChange={(e) => setSessionStoragePath(e.target.value)}
                placeholder={isElectron ? "Enter folder path for chat sessions..." : "Not available in web version"}
                className="settings-input"
                disabled={!isElectron}
              />
              <button 
                className="settings-btn settings-btn-secondary" 
                onClick={handleSelectSessionPath}
                disabled={!isElectron}
                title={isElectron ? "Select folder for storing chat sessions" : "Only available in Electron desktop app"}
              >
                Browse...
              </button>
            </div>
            {!sessionStoragePath && (
              <p className="settings-hint">
                Leave empty to use default location ({isElectron ? 'app userData folder' : 'localStorage'}).
              </p>
            )}
          </section>
        </div>

        <div className="settings-dialog-footer">
          <button className="settings-btn settings-btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="settings-btn settings-btn-primary" onClick={handleSave}>
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
};
