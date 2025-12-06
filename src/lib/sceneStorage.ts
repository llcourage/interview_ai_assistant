// 场景和 Prompt 配置的本地存储管理（兼容 Electron 和 Web）

import { Scene, SceneConfig, PromptPreset } from '../types/scenes';

const STORAGE_KEY = 'ai_assistant_scenes';

// 默认内置场景
const DEFAULT_SCENES: Scene[] = [
  {
    id: 'interview-assistant',
    name: 'Daily Assistant',
    isBuiltIn: true,
    presets: [
      {
        id: 'default',
        name: 'Default',
        prompt: 'You are a helpful AI assistant for daily usage. Help the user with their daily tasks, questions, and productivity needs. Provide thoughtful assistance and suggestions.'
      }
    ]
  },
  {
    id: 'coding',
    name: 'Coding Interview',
    isBuiltIn: true,
    presets: [
      {
        id: 'default',
        name: 'Default',
        prompt: `Please carefully read the problem in the screenshot.

Please strictly follow these 5 sections in your response, without any extra descriptions:

1) Problem Explanation (Brief)
Briefly summarize the problem requirements. Be concise.

2) Clarification Questions
List 3-5 key clarifying questions about the problem details (e.g., edge cases, input constraints, exceptions). Keep them brief.

3) Approach
Explain the optimal solution step by step, clearly and concisely.

4) Code
\`\`\`python
# Provide complete Python code here with key comments
\`\`\`

5) Explanation
Briefly explain the key logic of the code, including time/space complexity analysis.

⚠️ Prohibited:
- Do not write "Problem Description", "Examples", "Constraints" sections.
- Do not write phrases like "This image shows..." or other unnecessary text.
- Keep the response professional and concise.`
      },
      {
        id: 'algorithm',
        name: 'Algorithm',
        prompt: 'You are an algorithm interview expert. Help the user understand algorithms, data structures, and problem-solving techniques. Focus on time and space complexity analysis.'
      },
      {
        id: 'system-design',
        name: 'System Design',
        prompt: 'You are a system design interview expert. Help the user practice system design questions. Cover scalability, reliability, performance, and architecture patterns.'
      }
    ]
  },
  {
    id: 'behavioral',
    name: 'Behavioral (BQ)',
    isBuiltIn: true,
    presets: [
      {
        id: 'default',
        name: 'Default',
        prompt: `Please carefully read the behavioral interview question in the screenshot or conversation.

Please strictly follow these sections in your response, without any extra descriptions:

1) Question Analysis (Brief)
Briefly summarize what the interviewer is asking for. Identify the key competencies or skills being assessed.

2) STAR Method Structure
Break down the question into STAR components:
- Situation: What context is needed?
- Task: What was the goal or challenge?
- Action: What specific actions should be described?
- Result: What outcomes or learnings should be highlighted?

3) Sample Answer Framework
Provide a structured framework for answering, including:
- Opening statement
- Situation setup
- Task description
- Actions taken (with specific examples)
- Results and impact
- Reflection or learning

4) Key Points to Emphasize
List 3-5 important points the candidate should highlight in their answer.

5) Common Mistakes to Avoid
List 2-3 common mistakes candidates make when answering this type of question.

⚠️ Prohibited:
- Do not write overly generic responses.
- Do not write phrases like "This question shows..." or other unnecessary text.
- Keep the response professional, actionable, and concise.`
      },
      {
        id: 'leadership',
        name: 'Leadership',
        prompt: 'You are a leadership interview coach. Help the user prepare for leadership-related behavioral questions. Focus on examples of leading teams, making decisions, and handling conflicts.'
      }
    ]
  },
  {
    id: 'general-talking',
    name: 'General Talking',
    isBuiltIn: true,
    presets: [
      {
        id: 'default',
        name: 'Default',
        prompt: 'You are a friendly and helpful conversation partner. Engage in natural, professional conversation to help the user practice their communication skills.'
      }
    ]
  }
];

/**
 * 获取场景配置
 */
export function getSceneConfig(): SceneConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const config: SceneConfig = JSON.parse(stored);
      
      // 确保所有内置场景都存在（合并默认场景）
      const mergedScenes = [...DEFAULT_SCENES];
      const customScenes = config.scenes.filter(s => !s.isBuiltIn);
      
      // 合并自定义场景，但保留内置场景的更新
      customScenes.forEach(customScene => {
        const existingIndex = mergedScenes.findIndex(s => s.id === customScene.id);
        if (existingIndex >= 0) {
          // 如果是内置场景，保留 isBuiltIn 标志
          mergedScenes[existingIndex] = { ...customScene, isBuiltIn: true };
        } else {
          mergedScenes.push(customScene);
        }
      });
      
      // 确保当前选中的场景和预设存在
      let currentSceneId = config.currentSceneId || DEFAULT_SCENES[0].id;
      let currentPresetId = config.currentPresetId || DEFAULT_SCENES[0].presets[0].id;
      
      const currentScene = mergedScenes.find(s => s.id === currentSceneId);
      if (!currentScene) {
        currentSceneId = DEFAULT_SCENES[0].id;
        currentPresetId = DEFAULT_SCENES[0].presets[0].id;
      } else {
        const currentPreset = currentScene.presets.find(p => p.id === currentPresetId);
        if (!currentPreset) {
          currentPresetId = currentScene.presets[0].id;
        }
      }
      
      return {
        scenes: mergedScenes,
        currentSceneId,
        currentPresetId
      };
    }
  } catch (error) {
    console.error('Failed to load scene config:', error);
  }
  
  // 返回默认配置
  return {
    scenes: DEFAULT_SCENES,
    currentSceneId: DEFAULT_SCENES[0].id,
    currentPresetId: DEFAULT_SCENES[0].presets[0].id
  };
}

/**
 * 保存场景配置
 */
export function saveSceneConfig(config: SceneConfig): void {
  try {
    // 只保存自定义场景和当前选择
    const customScenes = config.scenes.filter(s => !s.isBuiltIn);
    const dataToSave: SceneConfig = {
      scenes: customScenes,
      currentSceneId: config.currentSceneId,
      currentPresetId: config.currentPresetId
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave));
  } catch (error) {
    console.error('Failed to save scene config:', error);
  }
}

/**
 * 添加新场景
 */
export function addScene(scene: Scene): void {
  const config = getSceneConfig();
  config.scenes.push(scene);
  saveSceneConfig(config);
  // 通知 Electron 更新菜单
  if (typeof window !== 'undefined' && window.aiShot?.notifyScenarioUpdated) {
    window.aiShot.notifyScenarioUpdated();
  }
}

/**
 * 更新场景
 */
export function updateScene(sceneId: string, updates: Partial<Scene>): void {
  const config = getSceneConfig();
  const sceneIndex = config.scenes.findIndex(s => s.id === sceneId);
  if (sceneIndex >= 0) {
    config.scenes[sceneIndex] = { ...config.scenes[sceneIndex], ...updates };
    saveSceneConfig(config);
    // 通知 Electron 更新菜单
    if (typeof window !== 'undefined' && window.aiShot?.notifyScenarioUpdated) {
      window.aiShot.notifyScenarioUpdated();
    }
  }
}

/**
 * 删除场景（只能删除自定义场景）
 */
export function deleteScene(sceneId: string): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene && !scene.isBuiltIn) {
    config.scenes = config.scenes.filter(s => s.id !== sceneId);
    // 如果删除的是当前场景，切换到第一个场景
    if (config.currentSceneId === sceneId) {
      config.currentSceneId = config.scenes[0]?.id || DEFAULT_SCENES[0].id;
      config.currentPresetId = config.scenes[0]?.presets[0]?.id || DEFAULT_SCENES[0].presets[0].id;
    }
    saveSceneConfig(config);
    // 通知 Electron 更新菜单
    if (typeof window !== 'undefined' && window.aiShot?.notifyScenarioUpdated) {
      window.aiShot.notifyScenarioUpdated();
    }
  }
}

/**
 * 添加预设到场景
 */
export function addPresetToScene(sceneId: string, preset: PromptPreset): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene) {
    scene.presets.push(preset);
    saveSceneConfig(config);
    // 通知 Electron 更新菜单
    if (typeof window !== 'undefined' && window.aiShot?.notifyScenarioUpdated) {
      window.aiShot.notifyScenarioUpdated();
    }
  }
}

/**
 * 更新预设
 */
export function updatePreset(sceneId: string, presetId: string, updates: Partial<PromptPreset>): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene) {
    const presetIndex = scene.presets.findIndex(p => p.id === presetId);
    if (presetIndex >= 0) {
      const preset = scene.presets[presetIndex];
      // 如果是内置场景的默认 preset，不允许修改
      if (scene.isBuiltIn && preset.id === 'default') {
        console.warn('Cannot modify default preset of built-in scenes');
        return;
      }
      scene.presets[presetIndex] = { ...preset, ...updates };
      saveSceneConfig(config);
    }
  }
}

/**
 * 删除预设
 */
export function deletePreset(sceneId: string, presetId: string): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene && scene.presets.length > 1) {
    // 如果是内置场景的默认 preset，不允许删除
    if (scene.isBuiltIn && presetId === 'default') {
      console.warn('Cannot delete default preset of built-in scenes');
      return;
    }
    // 至少保留一个预设
    scene.presets = scene.presets.filter(p => p.id !== presetId);
    // 如果删除的是当前预设，切换到第一个预设
    if (config.currentPresetId === presetId && config.currentSceneId === sceneId) {
      config.currentPresetId = scene.presets[0]?.id || '';
    }
    saveSceneConfig(config);
  }
}

/**
 * 设置当前场景和预设
 */
export function setCurrentScene(sceneId: string, presetId?: string): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene) {
    config.currentSceneId = sceneId;
    if (presetId) {
      const preset = scene.presets.find(p => p.id === presetId);
      if (preset) {
        config.currentPresetId = presetId;
      }
    } else {
      config.currentPresetId = scene.presets[0]?.id || '';
    }
    saveSceneConfig(config);
  }
}

/**
 * Get custom default prompt from settings (if set)
 */
export function getCustomDefaultPrompt(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('customDefaultPrompt') || '';
}

/**
 * 获取当前 Prompt 模板（包含自定义默认 prompt）
 */
export function getCurrentPrompt(): string {
  // Check if custom default prompt is set
  const customPrompt = getCustomDefaultPrompt();
  if (customPrompt) {
    return customPrompt;
  }
  
  // Otherwise use scene-specific prompt
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === config.currentSceneId);
  if (scene) {
    const preset = scene.presets.find(p => p.id === config.currentPresetId);
    return preset?.prompt || '';
  }
  return '';
}

/**
 * 获取当前场景名称
 */
export function getCurrentSceneName(): string {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === config.currentSceneId);
  return scene?.name || 'General Chat';
}

