# ⚙️ Vercel 配置说明

## 📁 Root Directory（根目录）

### 设置

**Root Directory**: `.` (点号，表示根目录)  
**或者留空**（默认就是根目录）

### 为什么？

项目结构：
```
项目根目录/
├── vercel.json          ← Vercel 配置文件（必须在根目录）
├── package.json         ← 前端构建配置
├── vite.config.ts       ← Vite 配置
├── api/                 ← Vercel Serverless Functions
│   ├── index.py
│   └── requirements.txt
├── src/                 ← 前端源代码
│   ├── App.tsx
│   └── ...
└── dist/                ← 构建输出（自动生成）
```

所有关键文件都在根目录，所以 Root Directory 必须是根目录。

---

## 🔧 Vercel 项目设置

### 在 Vercel Dashboard 中配置

1. **Project Settings** → **General**
2. **Root Directory**: 留空或输入 `.`
3. **Framework Preset**: 选择 **Other** 或 **Vite**
4. **Build Command**: `npm run build`
5. **Output Directory**: `dist`
6. **Install Command**: `npm install`

---

## 📋 完整配置清单

### General Settings

- **Root Directory**: `.` (或留空)
- **Framework Preset**: `Other` 或 `Vite`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### Environment Variables

```bash
OPENAI_API_KEY=sk-proj-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_NORMAL=price_...
STRIPE_PRICE_HIGH=price_...
```

### Functions Settings

- **Function Region**: 选择离用户最近的区域
- **Max Duration**: 
  - Hobby: 10秒（默认）
  - Pro: 60秒（推荐）

---

## ✅ 验证配置

部署后检查：

1. **前端是否正常**: `https://your-app.vercel.app`
2. **API 是否正常**: `https://your-app.vercel.app/api/health`
3. **API 文档**: `https://your-app.vercel.app/api/docs`

---

## 🎯 总结

**Root Directory = `.` (根目录)**

所有文件都在根目录下，不需要设置子目录。

