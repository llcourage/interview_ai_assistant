# 用户认证使用指南 🔐

## ✅ 已完成的工作

### 1. 后端配置
- ✅ 安装 Supabase Python SDK
- ✅ 创建 `backend/db_supabase.py` - Supabase 客户端
- ✅ 创建 `backend/auth_supabase.py` - 认证服务
- ✅ 在 `backend/main.py` 中添加认证 API 路由：
  - `POST /api/register` - 用户注册
  - `POST /api/login` - 用户登录
  - `GET /api/me` - 获取当前用户信息
- ✅ 配置环境变量 `backend/.env`

### 2. 前端配置
- ✅ 安装 `@supabase/supabase-js`
- ✅ 创建 `src/lib/supabase.ts` - Supabase 客户端
- ✅ 创建 `src/Login.tsx` 和 `src/Login.css` - 登录/注册界面
- ✅ 在 `src/App.tsx` 中集成认证检查

### 3. 启动服务
- ✅ 前端运行在 http://localhost:5174
- ✅ 后端需要启动（运行 `python backend/start.py` 或 `.\start-backend.bat`）

---

## 🚀 下一步：在 Supabase Dashboard 启用 Email 认证

### 步骤 1：访问 Supabase Dashboard
1. 打开 https://supabase.com/dashboard/project/cjrblsalpfhugeatrhrr
2. 登录你的 Supabase 账户

### 步骤 2：启用 Email 认证
1. 在左侧菜单点击 **Authentication** → **Providers**
2. 找到 **Email** 选项
3. 确保 **Enable Email provider** 已打开
4. **重要设置**：
   - **Enable email confirmations**（启用邮箱验证）：
     - 🟢 **如果关闭**：用户注册后可以直接登录（推荐用于开发测试）
     - 🔴 **如果打开**：用户需要点击邮箱中的验证链接才能登录（推荐用于生产环境）
   - **Minimum password length**（最小密码长度）：建议设为 6-8

5. 点击 **Save** 保存设置

### 步骤 3（可选）：配置邮件模板
如果你启用了邮箱验证，可以自定义邮件模板：
1. 在左侧菜单点击 **Authentication** → **Email Templates**
2. 编辑 **Confirm signup** 模板
3. 自定义邮件内容和样式

---

## 🧪 测试登录功能

### 方法 1：直接在前端测试
1. 启动前端：`npm run dev`
2. 访问 http://localhost:5174
3. 你应该会看到登录界面
4. 点击"去注册"创建新账户：
   - 输入邮箱（如 `test@example.com`）
   - 输入密码（至少 6 个字符）
   - 点击"注册"
5. 如果**未启用邮箱验证**：
   - ✅ 注册成功后会自动登录，进入主界面
6. 如果**启用了邮箱验证**：
   - 📧 你会看到"注册成功！请检查邮箱验证链接"
   - 去邮箱点击验证链接
   - 返回登录页面登录

### 方法 2：使用 Python 测试后端 API
```bash
cd backend
python -c "
from auth_supabase import register_user, UserCredentials
import asyncio

async def test():
    result = await register_user(UserCredentials(
        email='test@example.com',
        password='password123'
    ))
    print(result)

asyncio.run(test())
"
```

---

## 📝 常见问题

### Q1: 前端显示"加载中..."不动
**A**: 检查浏览器控制台是否有 Supabase 连接错误：
- 打开浏览器开发工具（F12）
- 查看 Console 是否有错误
- 确认 `SUPABASE_URL` 和 `SUPABASE_ANON_KEY` 是否正确

### Q2: 注册后收不到验证邮件
**A**: 
1. 检查 Supabase Dashboard → Authentication → Providers → Email 是否启用
2. 检查垃圾邮件文件夹
3. 在开发阶段，建议关闭邮箱验证（"Enable email confirmations" 设为 Off）

### Q3: 登录后立即退出登录
**A**: 检查 Supabase Session 是否正确保存：
- 打开浏览器开发工具 → Application → Local Storage
- 查看是否有 `supabase.auth.token` 相关的键

### Q4: 后端测试连接失败
**A**: 
```bash
cd backend
python test_supabase.py
```
如果失败，检查：
1. `backend/.env` 文件是否存在
2. `SUPABASE_URL` 和 `SUPABASE_ANON_KEY` 是否正确
3. 尝试重新运行 `pip install -r requirements.txt`

---

## 🔧 配置文件位置

- **后端环境变量**: `backend/.env`
  ```env
  SUPABASE_URL=https://cjrblsalpfhugeatrhrr.supabase.co
  SUPABASE_ANON_KEY=your-anon-key-here
  ```

- **前端 Supabase 客户端**: `src/lib/supabase.ts`
  ```typescript
  const supabaseUrl = 'https://cjrblsalpfhugeatrhrr.supabase.co'
  const supabaseAnonKey = 'your-anon-key-here'
  ```

---

## 🎯 功能清单

- ✅ 用户注册
- ✅ 用户登录
- ✅ Session 管理（自动保持登录状态）
- ✅ 未登录时显示登录页面
- ✅ 已登录时显示主应用
- ✅ 优雅的加载状态
- ✅ 美观的登录界面（渐变背景 + 现代 UI）
- ✅ 错误提示和成功提示
- ⏳ 邮箱验证（可选，需在 Supabase Dashboard 启用）
- ⏳ 密码重置（可以在后续添加）
- ⏳ 用户 Profile 编辑（可以在后续添加）

---

## 📚 相关文档

- [Supabase 认证文档](https://supabase.com/docs/guides/auth)
- [Supabase Python 客户端](https://github.com/supabase-community/supabase-py)
- [Supabase JavaScript 客户端](https://github.com/supabase/supabase-js)

---

## 🚀 启动完整应用

1. **启动后端**（在项目根目录）：
   ```bash
   .\start-backend.bat
   ```
   或
   ```bash
   cd backend
   python start.py
   ```

2. **启动前端**（在项目根目录）：
   ```bash
   npm run dev
   ```

3. **访问应用**：
   - 主应用：http://localhost:5174
   - 后端 API：http://localhost:8000
   - API 文档：http://localhost:8000/docs

---

## 🎉 恭喜！

你的 AI Interview Assistant 现在已经有用户认证功能了！🔐

用户必须先注册/登录才能使用应用，所有会话数据都与用户账户关联。

下一步你可以：
- 将会话数据存储到 Supabase 数据库（而不是 localStorage）
- 添加密码重置功能
- 添加第三方登录（Google, GitHub 等）
- 添加用户 Profile 页面

