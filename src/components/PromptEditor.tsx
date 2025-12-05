import React, { useState, useEffect } from 'react';
import { getCurrentPrompt, getSceneConfig, updatePreset } from '../lib/sceneStorage';
import './PromptEditor.css';

interface PromptEditorProps {
  onPromptChange?: (prompt: string) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const PromptEditor: React.FC<PromptEditorProps> = ({
  onPromptChange,
  collapsed = false,
  onToggleCollapse
}) => {
  const [prompt, setPrompt] = useState<string>('');
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [hasChanges, setHasChanges] = useState<boolean>(false);

  // 加载当前 Prompt
  useEffect(() => {
    const loadPrompt = () => {
      const currentPrompt = getCurrentPrompt();
      setPrompt(currentPrompt);
      setHasChanges(false);
    };

    loadPrompt();

    // 监听场景变化
    const handleSceneChange = () => {
      loadPrompt();
      setIsEditing(false);
    };

    window.addEventListener('sceneConfigChanged', handleSceneChange);
    window.addEventListener('storage', handleSceneChange);

    return () => {
      window.removeEventListener('sceneConfigChanged', handleSceneChange);
      window.removeEventListener('storage', handleSceneChange);
    };
  }, []);

  const handlePromptChange = (newPrompt: string) => {
    setPrompt(newPrompt);
    setHasChanges(true);
    onPromptChange?.(newPrompt);
  };

  const handleSave = () => {
    const config = getSceneConfig();
    updatePreset(config.currentSceneId, config.currentPresetId, { prompt });
    setHasChanges(false);
    setIsEditing(false);
    // 触发更新事件
    window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
  };

  const handleCancel = () => {
    const currentPrompt = getCurrentPrompt();
    setPrompt(currentPrompt);
    setHasChanges(false);
    setIsEditing(false);
  };

  if (collapsed) {
    return (
      <div className="prompt-editor-collapsed">
        <button
          className="prompt-editor-toggle"
          onClick={onToggleCollapse}
          title="展开 Prompt 编辑器"
        >
          <span>📝</span>
          <span>Prompt Template</span>
          <span>▶</span>
        </button>
      </div>
    );
  }

  return (
    <div className="prompt-editor">
      <div className="prompt-editor-header">
        <div className="prompt-editor-title">
          <span>📝</span>
          <span>Prompt Template</span>
        </div>
        <div className="prompt-editor-actions">
          {isEditing ? (
            <>
              <button
                className="prompt-editor-btn prompt-editor-btn-save"
                onClick={handleSave}
                disabled={!hasChanges}
              >
                保存
              </button>
              <button
                className="prompt-editor-btn prompt-editor-btn-cancel"
                onClick={handleCancel}
              >
                取消
              </button>
            </>
          ) : (
            <button
              className="prompt-editor-btn prompt-editor-btn-edit"
              onClick={() => setIsEditing(true)}
            >
              编辑
            </button>
          )}
          {onToggleCollapse && (
            <button
              className="prompt-editor-btn prompt-editor-btn-collapse"
              onClick={onToggleCollapse}
              title="折叠"
            >
              ▼
            </button>
          )}
        </div>
      </div>
      
      <div className="prompt-editor-content">
        {isEditing ? (
          <textarea
            className="prompt-editor-textarea"
            value={prompt}
            onChange={(e) => handlePromptChange(e.target.value)}
            placeholder="输入 Prompt 模板..."
            rows={6}
          />
        ) : (
          <div className="prompt-editor-display">
            {prompt || <span className="prompt-editor-empty">暂无 Prompt 模板</span>}
          </div>
        )}
      </div>
      
      {!isEditing && prompt && (
        <div className="prompt-editor-hint">
          💡 此 Prompt 会在发送消息时自动添加到用户输入前
        </div>
      )}
    </div>
  );
};

