// Type definitions for scenes and Prompt templates

export interface PromptPreset {
  id: string;
  name: string;
  prompt: string;
}

export interface Scene {
  id: string;
  name: string;
  presets: PromptPreset[];
  isBuiltIn: boolean; // Whether it's a built-in scene (cannot be deleted)
}

export interface SceneConfig {
  scenes: Scene[];
  currentSceneId: string;
  currentPresetId: string;
}

