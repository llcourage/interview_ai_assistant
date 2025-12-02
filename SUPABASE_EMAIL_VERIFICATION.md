# 📧 Supabase 邮箱验证配置指南

## ❌ 问题描述

如果邮箱验证链接指向 `http://localhost:3000` 或显示 `otp_expired` 错误，说明 Supabase 的 URL 配置不正确。

## 🔧 解决方案

### 1. 配置 Supabase Site URL

1. 访问 [Supabase Dashboard](https://app.supabase.com/)
2. 选择你的项目
3. 进入 **Authentication** → **URL Configuration**
4. 配置以下设置：

#### Site URL（必需）
```
https://www.desktopai.org
```
或者如果是本地开发：
```
http://localhost:5173
```

#### Redirect URLs（必需）
添加以下 URL 到允许的重定向列表：

```
https://www.desktopai.org/**
https://www.desktopai.org/login
https://www.desktopai.org/profile
http://localhost:5173/**
http://localhost:5173/login
http://localhost:5173/profile
```

> ⚠️ **注意**：`**` 表示匹配所有子路径

### 2. 邮箱验证设置

在 **Authentication** → **Email Templates** 中，确保：

1. **Confirm signup** 模板中的链接使用正确的 URL
2. 模板中的 `{{ .ConfirmationURL }}` 会自动使用配置的 Site URL

### 3. 验证配置

配置完成后：
1. 等待 1-2 分钟让配置生效
2. 重新注册一个新账户
3. 检查邮箱中的验证链接，应该指向你的生产域名（`https://www.desktopai.org`）

## 🔍 常见问题

### Q: 链接仍然指向 localhost:3000？

**A:** 检查以下几点：
1. 确认 Site URL 已保存（点击 Save）
2. 清除浏览器缓存
3. 等待几分钟让配置生效
4. 重新发送验证邮件

### Q: 链接显示 "otp_expired"？

**A:** 邮箱验证链接通常有有效期（默认 24 小时）：
1. 如果链接已过期，需要重新注册或请求新的验证邮件
2. 可以在 Supabase Dashboard → **Authentication** → **Settings** 中调整 OTP 过期时间

### Q: 如何禁用邮箱验证？

**A:** 在 Supabase Dashboard：
1. 进入 **Authentication** → **Providers** → **Email**
2. 取消勾选 **"Confirm email"**
3. 这样注册后会自动登录，不需要验证邮箱

## 📝 代码中的配置

当前代码在 `src/lib/supabase.ts` 中配置了 Supabase 客户端。如果需要自定义 redirect URL，可以在注册时指定：

```typescript
const { data, error } = await supabase.auth.signUp({
  email,
  password,
  options: {
    emailRedirectTo: 'https://www.desktopai.org/login'
  }
});
```

## ✅ 验证步骤

1. ✅ Site URL 设置为生产域名
2. ✅ Redirect URLs 包含所有需要的路径
3. ✅ 等待配置生效（1-2 分钟）
4. ✅ 重新注册测试
5. ✅ 检查邮箱中的验证链接

