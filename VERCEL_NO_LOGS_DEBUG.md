# 🔍 Vercel 没有日志 - 调试指南

## 问题分析

如果 **Vercel 函数日志为空**，可能的原因：

1. ❌ **请求根本没有到达 Vercel 函数**
2. ❌ **API 路由配置有问题**
3. ❌ **函数没有被正确部署**
4. ❌ **请求被前端拦截或失败**

## 🔍 立即检查步骤

### 步骤 1：检查浏览器网络请求（最重要）

1. 打开你的网站（例如：`https://www.desktopai.org`）
2. 按 **F12** 打开开发者工具
3. 进入 **Network** 标签
4. **清空所有请求**（点击 🚫 图标）
5. 点击购买按钮
6. 查找 `/api/plan/checkout` 请求

#### 检查点 A：请求是否发送？

**如果没有看到 `/api/plan/checkout` 请求**：
- ❌ 请求根本没有发送
- 可能原因：前端代码错误、JavaScript 错误
- **解决方法**：查看 **Console** 标签中的错误信息

**如果看到了请求**，继续检查：

#### 检查点 B：请求 URL 是什么？

查看请求的 **Request URL**：
- ✅ 正确：`https://www.desktopai.org/api/plan/checkout`
- ❌ 错误：`http://127.0.0.1:8000/api/plan/checkout`（本地地址）
- ❌ 错误：`https://www.desktopai.org/api/plan/checkout` 但返回 404

#### 检查点 C：请求状态码是什么？

查看 **Status** 列：
- `200` - 成功（但可能返回错误 JSON）
- `404` - 路由未找到（API 路由配置问题）
- `500` - 服务器错误（函数执行失败）
- `CORS error` - 跨域问题
- `Failed` 或 `(failed)` - 网络错误

#### 检查点 D：查看响应内容

点击请求，查看 **Response** 标签：
- 如果看到 JSON 错误信息，说明请求到达了后端
- 如果看到 HTML（404 页面），说明路由配置有问题
- 如果看到 `CORS` 错误，说明跨域配置有问题

### 步骤 2：测试 API 端点是否工作

我已经创建了一个测试端点 `/api/test_api`，用于验证 API 是否正常工作。

**测试方法**：

1. 在浏览器中访问：
   ```
   https://www.desktopai.org/api/test_api
   ```
   或者
   ```
   https://你的域名/api/test_api
   ```

2. **如果看到**：
   ```json
   {
     "status": "ok",
     "message": "API test endpoint is working!",
     "path": "/api/test_api",
     "method": "GET"
   }
   ```
   ✅ **API 路由工作正常**

3. **如果看到 404**：
   ❌ **API 路由配置有问题**

### 步骤 3：检查 Vercel 部署

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 选择你的项目
3. 进入 **Deployments** 标签
4. 确认最新部署：
   - ✅ **Status**: Ready
   - ✅ **Functions**: 显示函数数量（应该有 3 个：`/api/index`, `/api/stripe_webhook`, `/api/test_api`）

5. 如果部署失败或函数数量不对：
   - 检查 `vercel.json` 配置
   - 检查构建日志

### 步骤 4：检查浏览器控制台

1. 打开浏览器开发者工具（F12）
2. 进入 **Console** 标签
3. 点击购买按钮
4. 查看：
   - ✅ 现在会显示详细的调试信息（我已经添加了）
   - 查找以 `🔍` 开头的日志
   - 查找错误信息（红色）

**现在会显示**：
```
🔍 Checkout Debug Info:
  - API_BASE_URL: https://www.desktopai.org
  - Request URL: https://www.desktopai.org/api/plan/checkout
  - Plan: normal
  - Token present: true
📡 Response status: 404 NOT_FOUND
```

## 🎯 常见问题和解决方案

### 问题 1：请求返回 404

**症状**：Network 标签中看到 `404 NOT_FOUND`

**可能原因**：
1. API 路由配置错误
2. 函数没有被正确部署

**解决方法**：
1. 检查 `vercel.json` 中的 `rewrites` 配置
2. 确认 `api/index.py` 文件存在
3. 重新部署应用

### 问题 2：请求根本没有发送

**症状**：Network 标签中没有 `/api/plan/checkout` 请求

**可能原因**：
1. 前端代码错误
2. JavaScript 异常
3. 用户未登录（请求被拦截）

**解决方法**：
1. 查看 **Console** 标签中的错误
2. 确认用户已登录
3. 检查前端代码逻辑

### 问题 3：CORS 错误

**症状**：Console 中看到 `CORS policy` 错误

**解决方法**：
- 后端已配置 CORS，但可能需要检查 `allow_origins` 设置

### 问题 4：请求发送但函数日志为空

**症状**：Network 中看到请求，但 Vercel 函数日志为空

**可能原因**：
1. 请求被 Vercel 路由拦截
2. 函数没有被正确触发

**解决方法**：
1. 检查 `vercel.json` 配置
2. 确认函数文件路径正确
3. 查看 Vercel 部署日志

## 📋 诊断清单

请按顺序检查：

- [ ] **浏览器 Network 标签** - 请求是否发送？
- [ ] **请求 URL** - 是否正确？
- [ ] **请求状态码** - 是什么？
- [ ] **响应内容** - 是什么？
- [ ] **浏览器 Console** - 有什么错误？
- [ ] **测试端点** - `/api/test_api` 是否工作？
- [ ] **Vercel 部署状态** - 是否成功？
- [ ] **Vercel 函数列表** - 函数是否存在？

## 🆘 下一步

请告诉我：

1. **浏览器 Network 标签中**：
   - 是否看到 `/api/plan/checkout` 请求？
   - 请求的 URL 是什么？
   - 状态码是什么？
   - 响应内容是什么？

2. **浏览器 Console 标签中**：
   - 是否看到 `🔍 Checkout Debug Info` 日志？
   - 有什么错误信息？

3. **测试端点**：
   - 访问 `https://你的域名/api/test_api` 是否工作？

有了这些信息，我可以帮你进一步诊断问题！

