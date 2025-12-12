# MSIX 证书设置指南

## 问题说明

当你使用 `electron-builder` 构建 MSIX/APPX 安装包时，如果使用自签名证书，Windows 会报错：

```
publisher certificate could not be verified (0x800B010A)
```

这是因为 Windows 默认不信任自签名证书。

## 解决方案

需要在本地机器上安装并信任这个证书。

## 快速设置（推荐）

### 方法 1：一键设置脚本

1. **以管理员身份运行** PowerShell 或命令提示符
2. 执行：
   ```batch
   scripts\setup-msix-certificate.bat
   ```

这个脚本会自动：
- 生成自签名证书
- 安装到 Trusted Root Certification Authorities

### 方法 2：分步执行

#### 步骤 1：生成证书

以管理员身份运行：
```powershell
scripts\generate-certificate.ps1
```

这会生成：
- `certificates/DesktopAI_MSIX_Certificate.pfx` - 用于签名
- `certificates/DesktopAI_MSIX_Certificate.cer` - 用于安装

#### 步骤 2：安装证书

以管理员身份运行：
```powershell
scripts\install-certificate.ps1
```

这会自动找到 `.cer` 文件并安装到 Local Machine 的 Trusted Root CA。

### 方法 3：使用 electron-builder 生成的证书

如果你已经构建了 MSIX 包，`electron-builder` 可能已经生成了 `.cer` 文件：

1. 查找 `dist-electron` 目录中的 `.cer` 文件
2. 以管理员身份运行：
   ```powershell
   scripts\find-and-install-certificate.ps1
   ```

## 手动安装证书（如果脚本失败）

1. **找到证书文件**
   - 在 `certificates/` 目录中找到 `.cer` 文件
   - 或在 `dist-electron/` 目录中查找

2. **双击 `.cer` 文件**
   - 点击 "安装证书" (Install Certificate)

3. **选择存储位置**
   - ⚠️ **必须选择 "本地计算机" (Local Machine)**
   - 不要选择 "当前用户" (Current User)

4. **选择证书存储**
   - 选择 "将所有证书放入以下存储" (Place all certificates in the following store)
   - 点击 "浏览" (Browse)
   - 选择 **"受信任的根证书颁发机构" (Trusted Root Certification Authorities)**
   - 点击 "确定"

5. **完成安装**
   - 点击 "完成" (Finish)
   - 确认安全警告

## 验证安装

安装完成后，你可以：

1. 双击你的 `.msix` 或 `.appx` 文件
2. 应该不再出现 `0x800B010A` 错误
3. 可以正常安装应用

## 配置 electron-builder 使用证书

在 `package.json` 中配置证书路径：

```json
{
  "build": {
    "win": {
      "certificateFile": "certificates/DesktopAI_MSIX_Certificate.pfx",
      "certificatePassword": "DesktopAI2024!"
    }
  }
}
```

⚠️ **注意**：不要将证书密码提交到 Git！

## 常见问题

### Q: 脚本提示需要管理员权限
A: 右键点击 PowerShell 或命令提示符，选择 "以管理员身份运行"

### Q: 证书已安装但仍然报错
A: 
1. 确认证书安装到了 **Local Machine** 而不是 Current User
2. 确认安装到了 **Trusted Root Certification Authorities**
3. 重启电脑后再试

### Q: 如何查看已安装的证书？
A: 运行：
```powershell
Get-ChildItem -Path "Cert:\LocalMachine\Root" | Where-Object { $_.Subject -like "*Desktop AI*" }
```

### Q: 如何删除已安装的证书？
A: 
1. 打开 `certlm.msc` (证书管理器)
2. 导航到：受信任的根证书颁发机构 > 证书
3. 找到你的证书并删除

## 生产环境注意事项

⚠️ **自签名证书仅用于开发和测试！**

对于生产环境，你应该：
1. 购买代码签名证书（如 DigiCert, Sectigo）
2. 或使用 Windows Store 进行分发（自动处理证书）

## 相关文件

- `scripts/generate-certificate.ps1` - 生成证书
- `scripts/install-certificate.ps1` - 安装证书
- `scripts/find-and-install-certificate.ps1` - 查找并安装已生成的证书
- `scripts/setup-msix-certificate.bat` - 一键设置脚本






