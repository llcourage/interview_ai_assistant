// 场景和 Prompt 模板的类型定义

export interface PromptPreset {
  id: string;
  name: string;
  prompt: string;
}

export interface Scene {
  id: string;
  name: string;
  presets: PromptPreset[];
  isBuiltIn: boolean; // 是否为内置场景（不可删除）
}

export interface SceneConfig {
  scenes: Scene[];
  currentSceneId: string;
  currentPresetId: string;
}

