import React, { useState, useEffect } from 'react';
import { Scene, PromptPreset } from '../types/scenes';
import { addScene, updateScene, getSceneConfig } from '../lib/sceneStorage';
import './ScenarioEditDialog.css';

interface ScenarioEditDialogProps {
  mode: 'create' | 'edit';
  scenario?: Scene | null;
  onClose: () => void;
  onSave: () => void;
}

export const ScenarioEditDialog: React.FC<ScenarioEditDialogProps> = ({
  mode,
  scenario,
  onClose,
  onSave
}) => {
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');

  useEffect(() => {
    if (mode === 'edit' && scenario) {
      setName(scenario.name);
      const defaultPreset = scenario.presets[0];
      setPrompt(defaultPreset?.prompt || '');
    } else {
      setName('');
      setPrompt('');
    }
  }, [mode, scenario]);

  const handleSave = () => {
    if (!name.trim() || !prompt.trim()) {
      alert('Please enter both scenario name and prompt text.');
      return;
    }

    if (mode === 'create') {
      const newScene: Scene = {
        id: `scene-${Date.now()}`,
        name: name.trim(),
        isBuiltIn: false,
        presets: [
          {
            id: 'default',
            name: 'Default',
            prompt: prompt.trim()
          }
        ]
      };
      addScene(newScene);
    } else if (scenario) {
      updateScene(scenario.id, {
        name: name.trim(),
        presets: [
          {
            id: 'default',
            name: 'Default',
            prompt: prompt.trim()
          }
        ]
      });
    }

    onSave();
  };

  return (
    <div className="scenario-edit-overlay" onClick={onClose}>
      <div className="scenario-edit-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="scenario-edit-header">
          <h2>{mode === 'create' ? 'Create New Custom Scenario' : 'Edit Custom Scenario'}</h2>
          <button className="scenario-edit-close" onClick={onClose}>×</button>
        </div>

        <div className="scenario-edit-content">
          <div className="scenario-edit-field">
            <label htmlFor="scenario-name">Scenario Name</label>
            <input
              id="scenario-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter scenario name..."
              autoFocus
            />
          </div>

          <div className="scenario-edit-field">
            <label htmlFor="scenario-prompt">System Prompt</label>
            <textarea
              id="scenario-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter the system prompt that will be used for this scenario..."
              rows={10}
            />
          </div>
        </div>

        <div className="scenario-edit-actions">
          <button className="scenario-edit-btn scenario-edit-btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button className="scenario-edit-btn scenario-edit-btn-save" onClick={handleSave}>
            {mode === 'create' ? 'Create' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};

