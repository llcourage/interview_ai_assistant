# 调试白屏问题

## 日志文件位置

Electron 应用会在以下位置创建日志文件：

**Windows:**
```
%APPDATA%\AI Interview Assistant\logs\main-YYYY-MM-DDTHH-MM-SS.log
```

例如：
```
C:\Users\YourUsername\AppData\Roaming\AI Interview Assistant\logs\main-2024-01-15T10-30-45.log
```

## 如何查看日志

### 方法 1: 通过文件资源管理器

1. 按 `Win + R` 打开运行对话框
2. 输入 `%APPDATA%\AI Interview Assistant\logs`
3. 按回车打开日志文件夹
4. 找到最新的日志文件（按修改时间排序）
5. 用记事本打开查看

### 方法 2: 通过 PowerShell

```powershell
# 打开日志文件夹
explorer "$env:APPDATA\AI Interview Assistant\logs"

# 或者直接查看最新日志
Get-Content "$env:APPDATA\AI Interview Assistant\logs\*.log" -Tail 50
```

### 方法 3: 通过命令行

```cmd
# 打开日志文件夹
start %APPDATA%\AI Interview Assistant\logs

# 查看最新日志（需要先 cd 到日志目录）
cd %APPDATA%\AI Interview Assistant\logs
type main-*.log
```

## 常见问题排查

### 1. 文件路径问题

如果日志显示 "找不到 index.html 文件"，检查：

- `dist/` 文件夹是否包含在打包文件中
- `package.json` 中的 `files` 配置是否正确：
  ```json
  "files": [
    "electron/**/*",
    "dist/**/*"
  ]
  ```

### 2. 白屏但无错误

如果日志中没有错误，但窗口是白屏：

1. **检查 DevTools**: 应用会自动打开 DevTools（临时调试功能）
2. **查看控制台**: 在 DevTools 的 Console 标签查看前端错误
3. **检查网络**: 查看 Network 标签，确认 API 请求是否正常

### 3. 路径问题

打包后的路径结构应该是：
```
app.asar (或解压后的文件夹)
├── electron/
│   ├── main.js
│   └── preload.js
└── dist/
    ├── index.html
    └── assets/
        └── ...
```

如果路径不对，日志会显示尝试的路径和实际路径。

## 临时调试功能

为了帮助调试，当前版本会：

1. **自动打开 DevTools**: 生产环境也会打开开发者工具
2. **详细日志**: 所有操作都会记录到日志文件
3. **错误页面**: 如果加载失败，会显示详细的错误信息

## 禁用调试功能

调试完成后，可以：

1. 移除 `mainWindow.webContents.openDevTools()` 行
2. 减少日志输出（可选）

## 日志内容示例

日志文件包含：
- 应用启动信息
- 文件路径检查
- 窗口加载状态
- 错误信息
- 渲染进程消息

示例日志：
```
[2024-01-15T10:30:45.123Z] [INFO] ============================================================
[2024-01-15T10:30:45.124Z] [INFO] 🚀 Electron 应用启动
[2024-01-15T10:30:45.125Z] [INFO]    环境: Production
[2024-01-15T10:30:45.126Z] [INFO]    日志文件: C:\Users\...\logs\main-2024-01-15T10-30-45.log
[2024-01-15T10:30:45.127Z] [INFO]    应用路径: C:\Program Files\AI Interview Assistant
[2024-01-15T10:30:45.128Z] [INFO] ============================================================
[2024-01-15T10:30:45.200Z] [INFO] 📦 生产模式: 加载文件 D:\...\dist\index.html
[2024-01-15T10:30:45.201Z] [INFO]    文件是否存在: true
```

## 联系支持

如果问题仍然存在，请提供：
1. 完整的日志文件内容
2. DevTools 控制台的错误信息
3. 操作系统版本
4. Electron 版本（在日志中可以看到）

