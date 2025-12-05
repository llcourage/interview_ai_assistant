import React, { useState, useEffect } from 'react';
import { Scene, PromptPreset } from '../types/scenes';
import {
  getSceneConfig,
  addScene,
  updateScene,
  deleteScene,
  addPresetToScene,
  updatePreset,
  deletePreset
} from '../lib/sceneStorage';
import './SceneManager.css';

interface SceneManagerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SceneManager: React.FC<SceneManagerProps> = ({ isOpen, onClose }) => {
  const [config, setConfig] = useState(getSceneConfig());
  const [editingScene, setEditingScene] = useState<Scene | null>(null);
  const [editingPreset, setEditingPreset] = useState<{ sceneId: string; preset: PromptPreset } | null>(null);
  const [showAddScene, setShowAddScene] = useState(false);
  const [showAddPreset, setShowAddPreset] = useState<string | null>(null);
  const [newSceneName, setNewSceneName] = useState('');
  const [newPresetName, setNewPresetName] = useState('');
  const [newPresetPrompt, setNewPresetPrompt] = useState('');

  useEffect(() => {
    if (isOpen) {
      setConfig(getSceneConfig());
    }
  }, [isOpen]);

  const handleAddScene = () => {
    if (!newSceneName.trim()) return;

    const newScene: Scene = {
      id: `scene-${Date.now()}`,
      name: newSceneName.trim(),
      isBuiltIn: false,
      presets: [
        {
          id: 'default',
          name: 'Default',
          prompt: 'You are a helpful assistant.'
        }
      ]
    };

    addScene(newScene);
    setConfig(getSceneConfig());
    setNewSceneName('');
    setShowAddScene(false);
    window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
  };

  const handleUpdateScene = (sceneId: string, name: string) => {
    updateScene(sceneId, { name });
    setConfig(getSceneConfig());
    setEditingScene(null);
    window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
  };

  const handleDeleteScene = (sceneId: string) => {
    const scene = config.scenes.find(s => s.id === sceneId);
    if (scene && !scene.isBuiltIn && window.confirm(`确定要删除场景 "${scene.name}" 吗？`)) {
      deleteScene(sceneId);
      setConfig(getSceneConfig());
      window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
    }
  };

  const handleAddPreset = (sceneId: string) => {
    if (!newPresetName.trim() || !newPresetPrompt.trim()) return;

    const newPreset: PromptPreset = {
      id: `preset-${Date.now()}`,
      name: newPresetName.trim(),
      prompt: newPresetPrompt.trim()
    };

    addPresetToScene(sceneId, newPreset);
    setConfig(getSceneConfig());
    setNewPresetName('');
    setNewPresetPrompt('');
    setShowAddPreset(null);
    window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
  };

  const handleUpdatePreset = (sceneId: string, presetId: string, name: string, prompt: string) => {
    updatePreset(sceneId, presetId, { name, prompt });
    setConfig(getSceneConfig());
    setEditingPreset(null);
    window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
  };

  const handleDeletePreset = (sceneId: string, presetId: string) => {
    const scene = config.scenes.find(s => s.id === sceneId);
    const preset = scene?.presets.find(p => p.id === presetId);
    if (preset && scene && scene.presets.length > 1 && window.confirm(`确定要删除预设 "${preset.name}" 吗？`)) {
      deletePreset(sceneId, presetId);
      setConfig(getSceneConfig());
      window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="scene-manager-overlay" onClick={onClose}>
      <div className="scene-manager-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="scene-manager-header">
          <h2>场景管理</h2>
          <button className="scene-manager-close" onClick={onClose}>×</button>
        </div>

        <div className="scene-manager-content">
          {showAddScene ? (
            <div className="scene-manager-add-scene">
              <input
                type="text"
                placeholder="场景名称"
                value={newSceneName}
                onChange={(e) => setNewSceneName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddScene()}
                autoFocus
              />
              <div className="scene-manager-actions">
                <button onClick={handleAddScene}>添加</button>
                <button onClick={() => { setShowAddScene(false); setNewSceneName(''); }}>取消</button>
              </div>
            </div>
          ) : (
            <button className="scene-manager-add-btn" onClick={() => setShowAddScene(true)}>
              + 新建场景
            </button>
          )}

          <div className="scene-manager-scenes">
            {config.scenes.map(scene => (
              <div key={scene.id} className="scene-manager-scene">
                <div className="scene-manager-scene-header">
                  {editingScene?.id === scene.id ? (
                    <input
                      type="text"
                      value={editingScene.name}
                      onChange={(e) => setEditingScene({ ...editingScene, name: e.target.value })}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          handleUpdateScene(scene.id, editingScene.name);
                        } else if (e.key === 'Escape') {
                          setEditingScene(null);
                        }
                      }}
                      autoFocus
                    />
                  ) : (
                    <h3>{scene.name} {scene.isBuiltIn && <span className="built-in-badge">内置</span>}</h3>
                  )}
                  <div className="scene-manager-scene-actions">
                    {!scene.isBuiltIn && (
                      <>
                        {editingScene?.id === scene.id ? (
                          <>
                            <button onClick={() => handleUpdateScene(scene.id, editingScene.name)}>保存</button>
                            <button onClick={() => setEditingScene(null)}>取消</button>
                          </>
                        ) : (
                          <>
                            <button onClick={() => setEditingScene(scene)}>重命名</button>
                            <button onClick={() => handleDeleteScene(scene.id)} className="delete-btn">删除</button>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>

                <div className="scene-manager-presets">
                  {showAddPreset === scene.id ? (
                    <div className="scene-manager-add-preset">
                      <input
                        type="text"
                        placeholder="预设名称"
                        value={newPresetName}
                        onChange={(e) => setNewPresetName(e.target.value)}
                      />
                      <textarea
                        placeholder="Prompt 模板"
                        value={newPresetPrompt}
                        onChange={(e) => setNewPresetPrompt(e.target.value)}
                        rows={4}
                      />
                      <div className="scene-manager-actions">
                        <button onClick={() => handleAddPreset(scene.id)}>添加</button>
                        <button onClick={() => { setShowAddPreset(null); setNewPresetName(''); setNewPresetPrompt(''); }}>取消</button>
                      </div>
                    </div>
                  ) : (
                    <button
                      className="scene-manager-add-preset-btn"
                      onClick={() => setShowAddPreset(scene.id)}
                    >
                      + 添加预设
                    </button>
                  )}

                  {scene.presets.map(preset => {
                    const isEditing = editingPreset?.sceneId === scene.id && editingPreset.preset.id === preset.id;
                    return (
                      <div key={preset.id} className="scene-manager-preset">
                        {isEditing ? (
                          <div className="scene-manager-preset-edit">
                            <input
                              type="text"
                              value={editingPreset.preset.name}
                              onChange={(e) => setEditingPreset({ ...editingPreset, preset: { ...editingPreset.preset, name: e.target.value } })}
                            />
                            <textarea
                              value={editingPreset.preset.prompt}
                              onChange={(e) => setEditingPreset({ ...editingPreset, preset: { ...editingPreset.preset, prompt: e.target.value } })}
                              rows={4}
                            />
                            <div className="scene-manager-actions">
                              <button onClick={() => handleUpdatePreset(scene.id, preset.id, editingPreset.preset.name, editingPreset.preset.prompt)}>保存</button>
                              <button onClick={() => setEditingPreset(null)}>取消</button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div className="scene-manager-preset-header">
                              <strong>{preset.name}</strong>
                              <div className="scene-manager-preset-actions">
                                <button onClick={() => setEditingPreset({ sceneId: scene.id, preset })}>编辑</button>
                                {scene.presets.length > 1 && (
                                  <button onClick={() => handleDeletePreset(scene.id, preset.id)} className="delete-btn">删除</button>
                                )}
                              </div>
                            </div>
                            <div className="scene-manager-preset-content">{preset.prompt}</div>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

