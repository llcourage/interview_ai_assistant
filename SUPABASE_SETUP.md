# Supabase 集成指南

## 概述
使用 Supabase 为 AI Interview Assistant 添加用户认证和数据存储功能。

## 第一步：创建 Supabase 项目

1. 访问 [https://supabase.com](https://supabase.com)
2. 点击 "Start your project" 或 "New Project"
3. 创建一个新项目（例如：`ai-interview-assistant`）
4. 记录以下信息：
   - **Project URL**（例如：`https://xxxxx.supabase.co`）
   - **Anon/Public Key**（在 Settings > API 中找到）

## 第二步：配置后端

### 1. 安装依赖

```bash
cd backend
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `backend/.env` 文件中添加：

```env
# Supabase 配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# OpenAI 配置（保持原有的）
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 修改 main.py 添加认证路由

在 `backend/main.py` 的开头添加导入：

```python
from supabase_auth import (
    UserRegister, UserLogin, Token, User,
    register_user, login_user, get_current_active_user
)
```

然后在路由部分添加（在 `@app.get("/")` 之前）：

```python
# ========== 认证相关 API ==========

@app.post("/api/register", response_model=Token, tags=["认证"])
async def register(user_data: UserRegister):
    """用户注册"""
    return await register_user(user_data.email, user_data.password)


@app.post("/api/login", response_model=Token, tags=["认证"])
async def login(user_data: UserLogin):
    """用户登录"""
    return await login_user(user_data.email, user_data.password)


@app.get("/api/me", response_model=User, tags=["认证"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


# ========== AI 功能 API（需要登录） ==========
```

### 4. 保护现有 API（可选）

如果需要用户登录才能使用 AI 功能，在相应的路由添加认证依赖：

```python
@app.post("/api/vision_query", response_model=VisionQueryResponse)
async def vision_query(
    request: VisionQueryRequest,
    current_user: User = Depends(get_current_active_user)  # 添加这一行
):
    # 原有代码...
    pass
```

## 第三步：配置前端

### 1. 安装 Supabase 客户端

```bash
npm install @supabase/supabase-js
```

### 2. 创建 Supabase 配置

创建 `src/lib/supabase.ts`：

```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://your-project.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'your-anon-key'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### 3. 配置环境变量

创建 `.env` 文件（在项目根目录）：

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

### 4. 创建登录组件

创建 `src/Login.tsx`：

```typescript
import React, { useState } from 'react';
import { supabase } from './lib/supabase';
import './Login.css';

interface LoginProps {
  onLoginSuccess: (token: string) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        // 注册
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        });
        
        if (error) throw error;
        
        if (data.session) {
          onLoginSuccess(data.session.access_token);
        } else {
          setError('请检查邮箱验证链接完成注册');
        }
      } else {
        // 登录
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        
        if (error) throw error;
        
        if (data.session) {
          onLoginSuccess(data.session.access_token);
        }
      }
    } catch (err: any) {
      setError(err.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>🔥 AI Interview Assistant</h1>
        <h2>{isRegister ? '注册' : '登录'}</h2>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={loading}
            />
          </div>
          
          <div className="form-group">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 6 个字符"
              required
              disabled={loading}
              minLength={6}
            />
          </div>
          
          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? '处理中...' : (isRegister ? '注册' : '登录')}
          </button>
        </form>
        
        <p className="toggle-mode">
          {isRegister ? '已有账号？' : '还没有账号？'}
          <button 
            type="button"
            onClick={() => setIsRegister(!isRegister)}
            className="toggle-btn"
          >
            {isRegister ? '去登录' : '去注册'}
          </button>
        </p>
      </div>
    </div>
  );
};
```

### 5. 创建登录样式

创建 `src/Login.css`：

```css
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  background: white;
  padding: 2.5rem;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  min-width: 400px;
  max-width: 450px;
}

.login-box h1 {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 1.8rem;
  text-align: center;
}

.login-box h2 {
  margin: 0 0 2rem 0;
  color: #666;
  font-size: 1.3rem;
  text-align: center;
  font-weight: 400;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 0.875rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 500;
  font-size: 0.95rem;
}

.form-group input {
  width: 100%;
  padding: 0.875rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.form-group input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.submit-btn {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-mode {
  margin-top: 1.5rem;
  text-align: center;
  color: #666;
  font-size: 0.95rem;
}

.toggle-btn {
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  margin-left: 0.5rem;
  font-weight: 600;
  text-decoration: none;
  font-size: 0.95rem;
}

.toggle-btn:hover {
  text-decoration: underline;
}
```

### 6. 修改 App.tsx

修改 `src/App.tsx` 添加认证检查：

```typescript
import { useState, useEffect } from 'react'
import { supabase } from './lib/supabase'
import { Login } from './Login'
// ... 其他导入

function App() {
  const [session, setSession] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 检查当前 session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    // 监听认证状态变化
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    setSession(null)
  }

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        加载中...
      </div>
    )
  }

  if (!session) {
    return <Login onLoginSuccess={(token) => {
      // Session 会通过 onAuthStateChange 自动更新
    }} />
  }

  // 原有的 App 界面
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🔥 AI 面试助手</h1>
          <p className="subtitle">会话历史记录</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
            {session.user.email}
          </span>
          <button 
            onClick={handleLogout}
            style={{
              padding: '0.5rem 1rem',
              background: 'var(--accent-color)',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            登出
          </button>
        </div>
      </header>
      
      {/* 原有内容 */}
    </div>
  )
}

export default App
```

### 7. 在 API 请求中添加 token

修改所有 API 请求，添加认证头：

```typescript
const token = (await supabase.auth.getSession()).data.session?.access_token

const response = await fetch('http://localhost:8000/api/vision_query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`  // 添加认证头
  },
  body: JSON.stringify(data)
});
```

## 第四步：Supabase 控制台配置

### 1. 配置认证设置

在 Supabase 控制台：
1. 进入 **Authentication** > **Providers**
2. 启用 **Email** 提供商
3. 可选：关闭 "Confirm email" 以便快速测试（生产环境建议开启）

### 2. 设置邮件模板（可选）

在 **Authentication** > **Email Templates** 中自定义：
- 确认邮件
- 重置密码邮件
- 邀请邮件

## 第五步：测试

1. 启动后端：
   ```bash
   cd backend
   python start.py
   ```

2. 启动前端：
   ```bash
   npm run dev
   ```

3. 访问应用，测试注册和登录功能

## 可选功能

### 1. 添加社交登录

Supabase 支持多种社交登录：

```typescript
// Google 登录
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google'
})

// GitHub 登录
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'github'
})
```

### 2. 保存用户会话数据到 Supabase

创建表来存储用户的会话记录：

```sql
-- 在 Supabase SQL 编辑器中运行
create table sessions (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users not null,
  session_data jsonb not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 启用 Row Level Security
alter table sessions enable row level security;

-- 创建策略：用户只能访问自己的数据
create policy "Users can only access their own sessions"
  on sessions for all
  using (auth.uid() = user_id);
```

### 3. 密码重置

```typescript
// 发送重置密码邮件
const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
  redirectTo: 'http://localhost:5173/reset-password',
})

// 更新密码
const { data, error } = await supabase.auth.updateUser({
  password: newPassword
})
```

## 优势

使用 Supabase 的优势：
- ✅ 无需管理用户数据库
- ✅ 内置认证系统（支持邮箱、社交登录等）
- ✅ 自动处理 token 刷新
- ✅ 实时数据同步
- ✅ 免费套餐（50,000 月活用户）
- ✅ 可扩展到生产环境

## 故障排除

1. **连接失败**：检查 `.env` 中的 Supabase URL 和 Key 是否正确
2. **注册失败**：检查 Supabase 控制台的认证设置
3. **Token 无效**：确保前后端使用相同的 Supabase 项目

