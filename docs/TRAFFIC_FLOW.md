# 流量路径总结 (Traffic Flow Summary)

## 📊 总体架构

**核心原则：所有流量都走 Vercel，不直接连接 Supabase（除了一个例外）**

---

## 🔐 登录流程的流量路径

### 1. **邮箱/密码登录** ✅ 完全走 Vercel

```
前端 (Web/Electron)
  ↓
POST https://www.desktopai.org/api/login
  ↓
Vercel API (backend/main.py)
  ↓
Supabase (后端连接，使用 SERVICE_ROLE_KEY)
  ↓
返回 token 给前端
```

**代码位置：**
- 前端：`src/lib/auth.ts` → `login()` → `fetch(${API_BASE_URL}/api/login)`
- 后端：`backend/main.py` → `/api/login` → `backend/auth_supabase.py` → `login_user()`

---

### 2. **Google OAuth 登录** ⚠️ 有一个直接连接 Supabase 的地方

#### Web 环境流程：

```
步骤 1: 获取 OAuth URL
前端
  ↓
GET https://www.desktopai.org/api/auth/google/url?redirect_to=https://www.desktopai.org/auth/callback
  ↓
Vercel API (backend/main.py)
  ↓
backend/auth_supabase.py → get_google_oauth_url()
  ↓
Supabase Python SDK (后端连接，使用 ANON_KEY)
  ↓
返回 OAuth URL 给前端

步骤 2: 用户授权
前端跳转到 Google OAuth 页面
  ↓
Google 授权后重定向到: https://www.desktopai.org/auth/callback?code=xxx

步骤 3: 交换 code 获取 token ⚠️ 直接连接 Supabase
前端 (src/lib/auth.ts → handleOAuthCallback())
  ↓
supabase.auth.exchangeCodeForSession(code)  ← 直接连接 Supabase！
  ↓
https://cjrblsalpfhugeatrhrr.supabase.co/auth/v1/token
  ↓
返回 session/token 给前端
```

**⚠️ 这是唯一直接连接 Supabase 的地方！**

**原因：** PKCE 流程需要 `code_verifier`，它保存在浏览器本地存储中，只有前端能访问。

**代码位置：**
- 前端：`src/lib/auth.ts` → `handleOAuthCallback()` → `supabase.auth.exchangeCodeForSession()`
- Supabase 客户端：`src/lib/supabase.ts` → `createClient(supabaseUrl, supabaseAnonKey)`

#### Electron 环境流程：

```
步骤 1: 获取 OAuth URL
Electron (electron/main.js)
  ↓
GET https://www.desktopai.org/api/auth/google/url?redirect_to=https://www.desktopai.org/auth/callback
  ↓
Vercel API (backend/main.py)
  ↓
backend/auth_supabase.py → get_google_oauth_url()
  ↓
Supabase Python SDK (后端连接，使用 ANON_KEY)
  ↓
返回 OAuth URL 给 Electron

步骤 2: 用户授权
Electron 打开 OAuth 窗口，加载 Google OAuth 页面
  ↓
Google 授权后重定向到: https://www.desktopai.org/auth/callback?code=xxx
  ↓
Electron 捕获回调 URL，提取 code

步骤 3: 交换 code 获取 token ⚠️ 直接连接 Supabase
Electron 将 code 传递给前端
  ↓
前端 (src/lib/auth.ts → handleOAuthCallback())
  ↓
supabase.auth.exchangeCodeForSession(code)  ← 直接连接 Supabase！
  ↓
https://cjrblsalpfhugeatrhrr.supabase.co/auth/v1/token
  ↓
返回 session/token 给前端
```

---

## 📡 其他 API 流量路径

### 所有其他 API 调用 ✅ 完全走 Vercel

```
前端 (Web/Electron)
  ↓
GET/POST https://www.desktopai.org/api/*
  ↓
Vercel API (backend/main.py)
  ↓
Supabase (后端连接，使用 SERVICE_ROLE_KEY)
  ↓
返回数据给前端
```

**包括：**
- `/api/register` - 用户注册
- `/api/me` - 获取当前用户信息
- `/api/plan` - 获取用户 Plan 信息
- `/api/plan/checkout` - 创建支付会话
- `/api/chat` - AI 聊天
- `/api/vision_query` - 图片分析
- 等等...

**代码位置：**
- 前端：所有 `fetch(${API_BASE_URL}/api/...)` 调用
- 后端：`backend/main.py` 中的各个路由

---

## 🔍 直接连接 Supabase 的地方总结

### ✅ 只有 1 个地方直接连接 Supabase：

1. **OAuth 回调处理** (`src/lib/auth.ts` → `handleOAuthCallback()`)
   - 使用：`supabase.auth.exchangeCodeForSession(code)`
   - 连接：`https://cjrblsalpfhugeatrhrr.supabase.co/auth/v1/token`
   - 原因：PKCE 流程需要从浏览器存储获取 `code_verifier`
   - 环境：Web 和 Electron 都会使用

### ❌ 不直接连接 Supabase 的地方：

- ✅ 所有后端 API 调用都通过 Vercel
- ✅ 所有数据库操作都通过 Vercel 后端
- ✅ 所有认证验证都通过 Vercel 后端
- ✅ Electron 的所有 API 调用都走 Vercel

---

## 📝 代码位置总结

### 前端直接连接 Supabase：
- `src/lib/supabase.ts` - Supabase 客户端配置（仅用于 OAuth）
- `src/lib/auth.ts` - `handleOAuthCallback()` 函数

### 前端通过 Vercel API：
- `src/lib/auth.ts` - `login()`, `register()`, `getCurrentUser()`, `getGoogleOAuthUrl()`
- `src/lib/api.ts` - `API_BASE_URL` 配置（指向 Vercel）
- 所有其他 API 调用

### Electron 通过 Vercel API：
- `electron/main.js` - `oauth-google` IPC handler（获取 OAuth URL）
- Electron 中所有其他操作都通过前端代码，前端代码走 Vercel

### 后端连接 Supabase：
- `backend/auth_supabase.py` - 所有认证相关操作
- `backend/db_operations.py` - 所有数据库操作
- `backend/main.py` - API 路由（通过上述模块连接 Supabase）

---

## 🎯 总结

**登录时的流量：**

1. **邮箱/密码登录**：✅ 100% 走 Vercel
   - 前端 → Vercel → Supabase（后端）→ 返回 token

2. **Google OAuth 登录**：⚠️ 99% 走 Vercel，1% 直接连接 Supabase
   - 获取 OAuth URL：前端 → Vercel → Supabase（后端）
   - 交换 code 获取 token：前端 → **直接连接 Supabase**（因为 PKCE）

**其他所有流量：** ✅ 100% 走 Vercel

---

## ⚙️ 环境变量要求

### 前端需要：
- `VITE_SUPABASE_URL` - 仅用于 OAuth 回调（可选，有默认值）
- `VITE_SUPABASE_ANON_KEY` - 仅用于 OAuth 回调（必需）

### 后端需要（Vercel 环境变量）：
- `SUPABASE_URL` - 所有后端操作
- `SUPABASE_ANON_KEY` - OAuth URL 生成
- `SUPABASE_SERVICE_ROLE_KEY` - 数据库操作

