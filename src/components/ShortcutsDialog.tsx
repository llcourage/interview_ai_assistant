import React from 'react';
import './ShortcutsDialog.css';

interface ShortcutsDialogProps {
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

export const ShortcutsDialog: React.FC<ShortcutsDialogProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="shortcuts-dialog-overlay" onClick={onClose}>
      <div className="shortcuts-dialog-content" onClick={(e) => e.stopPropagation()}>
        <div className="shortcuts-dialog-header">
          <h2>⌨️ Keyboard Shortcuts</h2>
          <button className="shortcuts-close-btn" onClick={onClose}>×</button>
        </div>

        <div className="shortcuts-dialog-body">
          <div className="shortcuts-list">
            {SHORTCUTS.map((shortcut, index) => (
              <div key={index} className="shortcut-item">
                <kbd className="shortcut-key">{shortcut.key}</kbd>
                <span className="shortcut-description">{shortcut.description}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="shortcuts-dialog-footer">
          <button className="shortcuts-btn shortcuts-btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

