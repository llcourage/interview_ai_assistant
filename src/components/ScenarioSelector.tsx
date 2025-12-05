import React, { useState, useEffect } from 'react';
import { Scene, SceneConfig } from '../types/scenes';
import {
  getSceneConfig,
  setCurrentScene,
  getCurrentSceneName
} from '../lib/sceneStorage';
import { ScenarioEditDialog } from './ScenarioEditDialog';
import { CustomPromptDialog } from './CustomPromptDialog';
import './ScenarioSelector.css';

interface ScenarioSelectorProps {
  onBack: () => void;
  onScenarioSelected?: () => void;
}

export const ScenarioSelector: React.FC<ScenarioSelectorProps> = ({
  onBack,
  onScenarioSelected
}) => {
  const [config, setConfig] = useState<SceneConfig>(getSceneConfig());
  const [showScenarioEditor, setShowScenarioEditor] = useState(false);
  const [scenarioEditorMode, setScenarioEditorMode] = useState<'create' | 'edit'>('create');
  const [editingScenario, setEditingScenario] = useState<Scene | null>(null);
  const [showCustomPromptDialog, setShowCustomPromptDialog] = useState(false);
  const [selectedSceneForCustomPrompt, setSelectedSceneForCustomPrompt] = useState<Scene | null>(null);

  // 监听场景配置变化
  useEffect(() => {
    const handleSceneConfigChange = () => {
      setConfig(getSceneConfig());
    };
    
    window.addEventListener('sceneConfigChanged', handleSceneConfigChange);
    window.addEventListener('storage', handleSceneConfigChange);
    
    return () => {
      window.removeEventListener('sceneConfigChanged', handleSceneConfigChange);
      window.removeEventListener('storage', handleSceneConfigChange);
    };
  }, []);

  // 内置场景
  const builtInScenes = config.scenes.filter(s => s.isBuiltIn);
  const customScenes = config.scenes.filter(s => !s.isBuiltIn);

  // 各个场景
  const codingScene = builtInScenes.find(s => s.id === 'coding');
  const behavioralScene = builtInScenes.find(s => s.id === 'behavioral');
  const generalScene = builtInScenes.find(s => 
    s.id === 'general-talking' || s.id === 'general' || s.name.toLowerCase().includes('general')
  );

  const handleSelectScene = (sceneId: string, presetId?: string) => {
    setCurrentScene(sceneId, presetId);
    setConfig(getSceneConfig());
    window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
    onScenarioSelected?.();
    // 延迟返回，让用户看到选择反馈
    setTimeout(() => {
      onBack();
    }, 300);
  };

  const handleEditScenario = (scenario: Scene) => {
    setEditingScenario(scenario);
    setScenarioEditorMode('edit');
    setShowScenarioEditor(true);
  };

  const handleCreateScenario = () => {
    setEditingScenario(null);
    setScenarioEditorMode('create');
    setShowScenarioEditor(true);
  };

  const handleAddCustomPrompt = (scene: Scene) => {
    setSelectedSceneForCustomPrompt(scene);
    setShowCustomPromptDialog(true);
  };

  const currentSceneName = getCurrentSceneName();
  const currentScene = config.scenes.find(s => s.id === config.currentSceneId);

  // 获取场景的简短描述
  const getSceneDescription = (scene: Scene): string => {
    if (scene.id === 'coding') {
      return 'Your assistance in mock coding interviews';
    } else if (scene.id === 'behavioral') {
      return 'Your assistance in mock behavioral interviews';
    } else if (scene.id === 'general-talking' || scene.id === 'general') {
      return 'Your assistance in general conversation practice';
    } else {
      // 自定义场景使用名称或简短描述
      return scene.name;
    }
  };

  return (
    <div className="scenario-selector-page">
      <div className="scenario-selector-header">
        <button className="scenario-selector-back-btn" onClick={onBack}>
          ← Back
        </button>
        <h1>Choose Application Scenario</h1>
        <div className="scenario-selector-current">
          Current: <strong>{currentSceneName}</strong>
        </div>
      </div>

      <div className="scenario-selector-content">
        {/* Interview - Coding */}
        <section className="scenario-section">
          <h2 className="scenario-section-title">
            <span className="scenario-section-icon">💼</span>
            Interview - Coding
          </h2>
          <div className="scenario-grid">
            {codingScene ? (
              <div
                className={`scenario-card ${currentScene?.id === codingScene.id ? 'active' : ''}`}
                onClick={() => handleSelectScene(codingScene.id, codingScene.presets[0]?.id)}
              >
                <div className="scenario-card-header">
                  <h3>{codingScene.name}</h3>
                  {currentScene?.id === codingScene.id && (
                    <span className="scenario-card-badge">Current</span>
                  )}
                </div>
                <p className="scenario-card-description">
                  {getSceneDescription(codingScene)}
                </p>
              </div>
            ) : (
              <div className="scenario-empty">
                <p>Not available</p>
              </div>
            )}
          </div>
        </section>

        {/* Interview - BQ */}
        <section className="scenario-section">
          <h2 className="scenario-section-title">
            <span className="scenario-section-icon">💼</span>
            Interview - BQ
          </h2>
          <div className="scenario-grid">
            {behavioralScene ? (
              <div
                className={`scenario-card ${currentScene?.id === behavioralScene.id ? 'active' : ''}`}
                onClick={() => handleSelectScene(behavioralScene.id, behavioralScene.presets[0]?.id)}
              >
                <div className="scenario-card-header">
                  <h3>{behavioralScene.name}</h3>
                  {currentScene?.id === behavioralScene.id && (
                    <span className="scenario-card-badge">Current</span>
                  )}
                </div>
                <p className="scenario-card-description">
                  {getSceneDescription(behavioralScene)}
                </p>
              </div>
            ) : (
              <div className="scenario-empty">
                <p>Not available</p>
              </div>
            )}
          </div>
        </section>

        {/* General Talking */}
        <section className="scenario-section">
          <h2 className="scenario-section-title">
            <span className="scenario-section-icon">💬</span>
            General Talking
          </h2>
          <div className="scenario-grid">
            {generalScene ? (
              <div
                className={`scenario-card ${currentScene?.id === generalScene.id ? 'active' : ''}`}
                onClick={() => handleSelectScene(generalScene.id, generalScene.presets[0]?.id)}
              >
                <div className="scenario-card-header">
                  <h3>{generalScene.name}</h3>
                  {currentScene?.id === generalScene.id && (
                    <span className="scenario-card-badge">Current</span>
                  )}
                </div>
                <p className="scenario-card-description">
                  {getSceneDescription(generalScene)}
                </p>
              </div>
            ) : (
              <div className="scenario-empty">
                <p>Not available</p>
              </div>
            )}
          </div>
        </section>

        {/* Customized */}
        <section className="scenario-section">
          <div className="scenario-section-header">
            <h2 className="scenario-section-title">
              <span className="scenario-section-icon">⭐</span>
              Customized
            </h2>
            <button
              className="scenario-create-btn"
              onClick={handleCreateScenario}
            >
              + New
            </button>
          </div>
          <div className="scenario-grid">
            {customScenes.length > 0 ? (
              customScenes.map(scene => (
                <div
                  key={scene.id}
                  className={`scenario-card ${currentScene?.id === scene.id ? 'active' : ''}`}
                  onClick={() => handleSelectScene(scene.id, scene.presets[0]?.id)}
                >
                  <div className="scenario-card-header">
                    <h3>{scene.name}</h3>
                    {currentScene?.id === scene.id && (
                      <span className="scenario-card-badge">Current</span>
                    )}
                    <button
                      className="scenario-edit-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditScenario(scene);
                      }}
                      title="Edit scenario"
                    >
                      ✏️
                    </button>
                  </div>
                  <p className="scenario-card-description">
                    {scene.name}
                  </p>
                </div>
              ))
            ) : (
              <div className="scenario-empty">
                <p>No custom scenarios yet.</p>
                <button
                  className="scenario-create-btn-inline"
                  onClick={handleCreateScenario}
                >
                  Create your first custom scenario
                </button>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Scenario Edit Dialog */}
      {showScenarioEditor && (
        <ScenarioEditDialog
          mode={scenarioEditorMode}
          scenario={editingScenario}
          onClose={() => {
            setShowScenarioEditor(false);
            setEditingScenario(null);
          }}
          onSave={() => {
            setShowScenarioEditor(false);
            setEditingScenario(null);
            setConfig(getSceneConfig());
            window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
          }}
        />
      )}

      {/* Custom Prompt Dialog */}
      {showCustomPromptDialog && selectedSceneForCustomPrompt && (
        <CustomPromptDialog
          scene={selectedSceneForCustomPrompt}
          onClose={() => {
            setShowCustomPromptDialog(false);
            setSelectedSceneForCustomPrompt(null);
          }}
          onSave={() => {
            setShowCustomPromptDialog(false);
            setSelectedSceneForCustomPrompt(null);
            setConfig(getSceneConfig());
            window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
          }}
        />
      )}
    </div>
  );
};

