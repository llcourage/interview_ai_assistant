# 场景和 Prompt 模板功能

## 功能概述

本功能允许用户在 UI 中创建和管理不同的应用场景（模式），每个场景包含多个 Prompt 模板预设。所有配置存储在本地（localStorage），不依赖后端或 Supabase。

## 主要功能

### 1. 场景管理
- **内置场景**（不可删除）：
  - Interview Assistant
  - Coding Interview（包含 Algorithm、System Design 等预设）
  - Behavioral (BQ)（包含 Leadership 等预设）
  - General Talking

- **自定义场景**：
  - 用户可以创建、重命名、删除自定义场景
  - 每个场景可以包含多个预设（Preset）

### 2. Prompt 模板编辑
- 每个预设包含一个 Prompt 模板
- 用户可以在 UI 中直接编辑 Prompt 模板
- Prompt 模板会在发送消息时自动添加到用户输入前

### 3. 自动应用
- **文字对话**：Prompt 模板 + 用户输入 → 发送给后端
- **图片分析**：Prompt 模板作为 `prompt` 参数传递给后端

## 使用方法

### 选择场景和预设
1. 在顶部场景选择器中选择场景
2. 如果场景有多个预设，点击预设按钮选择具体预设

### 编辑 Prompt
1. 在 Prompt 编辑器中点击"编辑"按钮
2. 修改 Prompt 模板内容
3. 点击"保存"保存更改

### 管理场景
1. 点击场景选择器旁边的 ⚙️ 按钮
2. 在场景管理对话框中：
   - 点击"+ 新建场景"创建新场景
   - 点击场景名称旁的"重命名"修改场景名称
   - 点击"删除"删除自定义场景（内置场景不可删除）
   - 在场景内点击"+ 添加预设"添加新的 Prompt 预设
   - 点击预设旁的"编辑"修改预设名称和 Prompt
   - 点击预设旁的"删除"删除预设（至少保留一个）

## 技术实现

### 数据存储
- 使用 `localStorage` 存储场景配置
- 存储键：`ai_assistant_scenes`
- 只存储自定义场景，内置场景在代码中定义

### 组件结构
- `SceneSelector.tsx` - 场景选择器组件
- `PromptEditor.tsx` - Prompt 编辑器组件
- `SceneManager.tsx` - 场景管理对话框
- `sceneStorage.ts` - 存储管理工具函数
- `types/scenes.ts` - 类型定义

### 集成位置
- 在 `Overlay.tsx` 中集成，位于顶部快捷键栏上方
- 支持折叠/展开 Prompt 编辑器

## 数据格式

```typescript
interface SceneConfig {
  scenes: Scene[];  // 所有场景（包括内置和自定义）
  currentSceneId: string;
  currentPresetId: string;
}

interface Scene {
  id: string;
  name: string;
  presets: PromptPreset[];
  isBuiltIn: boolean;
}

interface PromptPreset {
  id: string;
  name: string;
  prompt: string;
}
```

## 注意事项

1. **内置场景保护**：内置场景无法删除，但可以编辑其预设
2. **至少一个预设**：每个场景必须至少保留一个预设
3. **跨窗口同步**：使用 `localStorage` 的 `storage` 事件和自定义事件实现跨窗口同步
4. **默认场景**：首次使用时，默认选择第一个内置场景的第一个预设

