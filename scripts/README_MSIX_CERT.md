# MSIX 证书快速设置

## 问题
MSIX 安装包报错：`publisher certificate could not be verified (0x800B010A)`

## 解决方案（3 种方法）

### 🚀 方法 1：一键设置（最简单）
```batch
# 以管理员身份运行
scripts\setup-msix-certificate.bat
```

### 📝 方法 2：分步执行
```powershell
# 步骤 1：生成证书（管理员权限）
scripts\generate-certificate.ps1

# 步骤 2：安装证书（管理员权限）
scripts\install-certificate.ps1
```

### 🔍 方法 3：使用已生成的证书
```powershell
# 如果 electron-builder 已经生成了 .cer 文件
scripts\find-and-install-certificate.ps1
```

## 重要提示

1. ⚠️ **必须使用管理员权限运行**
2. ✅ 证书会安装到 **Local Machine** 的 **Trusted Root CA**
3. 📁 证书文件保存在 `certificates/` 目录（已加入 .gitignore）

## 详细文档

查看完整文档：`docs/MSIX_CERTIFICATE_SETUP.md`







