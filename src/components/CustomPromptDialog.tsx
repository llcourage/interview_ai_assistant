import React, { useState, useEffect } from 'react';
import { Scene, PromptPreset } from '../types/scenes';
import { addPresetToScene, getSceneConfig } from '../lib/sceneStorage';
import './CustomPromptDialog.css';

interface CustomPromptDialogProps {
  scene: Scene;
  onClose: () => void;
  onSave: () => void;
}

export const CustomPromptDialog: React.FC<CustomPromptDialogProps> = ({
  scene,
  onClose,
  onSave
}) => {
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');

  const handleSave = () => {
    if (!name.trim() || !prompt.trim()) {
      alert('Please enter both preset name and prompt text.');
      return;
    }

    const newPreset: PromptPreset = {
      id: `preset-${Date.now()}`,
      name: name.trim(),
      prompt: prompt.trim()
    };

    addPresetToScene(scene.id, newPreset);
    onSave();
  };

  return (
    <div className="custom-prompt-overlay" onClick={onClose}>
      <div className="custom-prompt-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="custom-prompt-header">
          <h2>Add Custom Prompt for "{scene.name}"</h2>
          <button className="custom-prompt-close" onClick={onClose}>×</button>
        </div>

        <div className="custom-prompt-content">
          <div className="custom-prompt-field">
            <label htmlFor="preset-name">Preset Name</label>
            <input
              id="preset-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., My Custom Style, Advanced Mode..."
              autoFocus
            />
          </div>

          <div className="custom-prompt-field">
            <label htmlFor="preset-prompt">Custom Prompt</label>
            <textarea
              id="preset-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter your custom prompt that will be used for this scenario..."
              rows={10}
            />
          </div>

          <div className="custom-prompt-hint">
            💡 This custom prompt will be added as a new preset option for "{scene.name}". The default prompt will remain unchanged.
          </div>
        </div>

        <div className="custom-prompt-actions">
          <button className="custom-prompt-btn custom-prompt-btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button className="custom-prompt-btn custom-prompt-btn-save" onClick={handleSave}>
            Add Custom Prompt
          </button>
        </div>
      </div>
    </div>
  );
};

