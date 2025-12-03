# AI 面试助手 - 后端服务

FastAPI 后端服务，提供视觉分析 API。

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填入你的 OpenAI API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### 3. 启动服务

```bash
python start.py
```

或者直接运行：

```bash
python main.py
```

或者使用 uvicorn：

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## API 接口

### 健康检查

```
GET /health
```

### 视觉分析

```
POST /api/vision_query
```

请求体：

```json
{
  "image_base64": "base64_encoded_image_string",
  "prompt": "请分析这张图片（可选）"
}
```

响应：

```json
{
  "answer": "AI 分析结果",
  "success": true,
  "error": ""
}
```

## API 文档

启动服务后，访问以下地址查看自动生成的 API 文档：

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## 支持的模型

- gpt-4o (推荐)
- gpt-4-turbo
- gpt-4-vision-preview

## 故障排除

### 1. API Key 错误

确保 `.env` 文件中的 `OPENAI_API_KEY` 已正确配置。

### 2. 模块未找到

确保已安装所有依赖：

```bash
pip install -r requirements.txt
```

### 3. 端口被占用

修改 `.env` 文件中的 `PORT` 配置，或在命令行指定：

```bash
PORT=8001 python start.py
```

## 开发

### 添加新的 API 端点

在 `main.py` 中添加新的路由函数。

### 修改视觉分析逻辑

编辑 `vision.py` 文件。















