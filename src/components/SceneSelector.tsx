import React, { useState, useEffect } from 'react';
import { Scene, SceneConfig } from '../types/scenes';
import { getSceneConfig, setCurrentScene } from '../lib/sceneStorage';
import './SceneSelector.css';

interface SceneSelectorProps {
  onSceneChange?: (sceneId: string, presetId: string) => void;
}

export const SceneSelector: React.FC<SceneSelectorProps> = ({ onSceneChange }) => {
  const [config, setConfig] = useState<SceneConfig>(getSceneConfig());
  const [showPresets, setShowPresets] = useState<boolean>(false);

  // 监听 localStorage 变化（跨窗口同步）
  useEffect(() => {
    const handleStorageChange = () => {
      setConfig(getSceneConfig());
    };
    
    window.addEventListener('storage', handleStorageChange);
    // 也监听自定义事件（同窗口内更新）
    window.addEventListener('sceneConfigChanged', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('sceneConfigChanged', handleStorageChange);
    };
  }, []);

  const currentScene = config.scenes.find(s => s.id === config.currentSceneId);
  const currentPreset = currentScene?.presets.find(p => p.id === config.currentPresetId);

  const handleSceneSelect = (sceneId: string) => {
    const scene = config.scenes.find(s => s.id === sceneId);
    if (scene) {
      setCurrentScene(sceneId, scene.presets[0]?.id);
      const newConfig = getSceneConfig();
      setConfig(newConfig);
      onSceneChange?.(sceneId, newConfig.currentPresetId);
      // 触发自定义事件
      window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
    }
  };

  const handlePresetSelect = (presetId: string) => {
    setCurrentScene(config.currentSceneId, presetId);
    const newConfig = getSceneConfig();
    setConfig(newConfig);
    onSceneChange?.(config.currentSceneId, presetId);
    setShowPresets(false);
    // 触发自定义事件
    window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
  };

  return (
    <div className="scene-selector">
      <div className="scene-selector-main">
        <select
          className="scene-select"
          value={config.currentSceneId}
          onChange={(e) => handleSceneSelect(e.target.value)}
        >
          {config.scenes.map(scene => (
            <option key={scene.id} value={scene.id}>
              {scene.name}
            </option>
          ))}
        </select>
        
        {currentScene && currentScene.presets.length > 1 && (
          <div className="preset-selector-wrapper">
            <button
              className="preset-select-button"
              onClick={() => setShowPresets(!showPresets)}
              title="选择预设"
            >
              {currentPreset?.name || 'Select Preset'}
              <span className="preset-arrow">▼</span>
            </button>
            
            {showPresets && (
              <div className="preset-dropdown">
                {currentScene.presets.map(preset => (
                  <button
                    key={preset.id}
                    className={`preset-option ${preset.id === config.currentPresetId ? 'active' : ''}`}
                    onClick={() => handlePresetSelect(preset.id)}
                  >
                    {preset.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      
      {showPresets && (
        <div
          className="preset-dropdown-overlay"
          onClick={() => setShowPresets(false)}
        />
      )}
    </div>
  );
};

