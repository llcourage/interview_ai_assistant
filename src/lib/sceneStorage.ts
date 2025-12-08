// Local storage management for scene and Prompt configuration (compatible with Electron and Web)

import { Scene, SceneConfig, PromptPreset } from '../types/scenes';

const STORAGE_KEY = 'ai_assistant_scenes';

// Default built-in scenes
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
 * Get scene configuration
 */
export function getSceneConfig(): SceneConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const config: SceneConfig = JSON.parse(stored);
      
      // Ensure all built-in scenes exist (merge default scenes)
      const mergedScenes = [...DEFAULT_SCENES];
      const customScenes = config.scenes.filter(s => !s.isBuiltIn);
      
      // Merge custom scenes, but preserve built-in scene updates
      customScenes.forEach(customScene => {
        const existingIndex = mergedScenes.findIndex(s => s.id === customScene.id);
        if (existingIndex >= 0) {
          // If it's a built-in scene, preserve isBuiltIn flag
          mergedScenes[existingIndex] = { ...customScene, isBuiltIn: true };
        } else {
          mergedScenes.push(customScene);
        }
      });
      
      // Ensure currently selected scene and preset exist
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
  
  // Return default configuration
  return {
    scenes: DEFAULT_SCENES,
    currentSceneId: DEFAULT_SCENES[0].id,
    currentPresetId: DEFAULT_SCENES[0].presets[0].id
  };
}

/**
 * Save scene configuration
 */
export function saveSceneConfig(config: SceneConfig): void {
  try {
    // Only save custom scenes and current selection
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
 * Add new scene
 */
export function addScene(scene: Scene): void {
  const config = getSceneConfig();
  config.scenes.push(scene);
  saveSceneConfig(config);
  // Notify Electron to update menu
  if (typeof window !== 'undefined' && window.aiShot?.notifyScenarioUpdated) {
    window.aiShot.notifyScenarioUpdated();
  }
}

/**
 * Update scene
 */
export function updateScene(sceneId: string, updates: Partial<Scene>): void {
  const config = getSceneConfig();
  const sceneIndex = config.scenes.findIndex(s => s.id === sceneId);
  if (sceneIndex >= 0) {
    config.scenes[sceneIndex] = { ...config.scenes[sceneIndex], ...updates };
    saveSceneConfig(config);
    // Notify Electron to update menu
    if (typeof window !== 'undefined' && window.aiShot?.notifyScenarioUpdated) {
      window.aiShot.notifyScenarioUpdated();
    }
  }
}

/**
 * Delete scene (can only delete custom scenes)
 */
export function deleteScene(sceneId: string): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene && !scene.isBuiltIn) {
    config.scenes = config.scenes.filter(s => s.id !== sceneId);
    // If deleted scene is current scene, switch to first scene
    if (config.currentSceneId === sceneId) {
      config.currentSceneId = config.scenes[0]?.id || DEFAULT_SCENES[0].id;
      config.currentPresetId = config.scenes[0]?.presets[0]?.id || DEFAULT_SCENES[0].presets[0].id;
    }
    saveSceneConfig(config);
    // Notify Electron to update menu
    if (typeof window !== 'undefined' && window.aiShot?.notifyScenarioUpdated) {
      window.aiShot.notifyScenarioUpdated();
    }
  }
}

/**
 * Add preset to scene
 */
export function addPresetToScene(sceneId: string, preset: PromptPreset): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene) {
    scene.presets.push(preset);
    saveSceneConfig(config);
    // Notify Electron to update menu
    if (typeof window !== 'undefined' && window.aiShot?.notifyScenarioUpdated) {
      window.aiShot.notifyScenarioUpdated();
    }
  }
}

/**
 * Update preset
 */
export function updatePreset(sceneId: string, presetId: string, updates: Partial<PromptPreset>): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene) {
    const presetIndex = scene.presets.findIndex(p => p.id === presetId);
    if (presetIndex >= 0) {
      const preset = scene.presets[presetIndex];
      // If it's a built-in scene's default preset, modification is not allowed
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
 * Delete preset
 */
export function deletePreset(sceneId: string, presetId: string): void {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === sceneId);
  if (scene && scene.presets.length > 1) {
    // If it's a built-in scene's default preset, deletion is not allowed
    if (scene.isBuiltIn && presetId === 'default') {
      console.warn('Cannot delete default preset of built-in scenes');
      return;
    }
    // Keep at least one preset
    scene.presets = scene.presets.filter(p => p.id !== presetId);
    // If deleted preset is current preset, switch to first preset
    if (config.currentPresetId === presetId && config.currentSceneId === sceneId) {
      config.currentPresetId = scene.presets[0]?.id || '';
    }
    saveSceneConfig(config);
  }
}

/**
 * Set current scene and preset
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
 * Get current Prompt template (includes custom default prompt)
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
 * Get current scene name
 */
export function getCurrentSceneName(): string {
  const config = getSceneConfig();
  const scene = config.scenes.find(s => s.id === config.currentSceneId);
  return scene?.name || 'General Chat';
}

