# AI Interview Assistant - Backend Service

FastAPI backend service providing vision analysis API.

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your OpenAI API Key:

```bash
cp .env.example .env
```

Edit `.env` file:

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### 3. Start Service

```bash
python start.py
```

Or run directly:

```bash
python main.py
```

Or use uvicorn:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## API Endpoints

### Health Check

```
GET /health
```

### Vision Analysis

```
POST /api/vision_query
```

Request body:

```json
{
  "image_base64": "base64_encoded_image_string",
  "prompt": "Please analyze this image (optional)"
}
```

Response:

```json
{
  "answer": "AI analysis result",
  "success": true,
  "error": ""
}
```

## API Documentation

After starting the service, visit the following addresses to view auto-generated API documentation:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Supported Models

- gpt-4o (recommended)
- gpt-4-turbo
- gpt-4-vision-preview

## Troubleshooting

### 1. API Key Error

Ensure `OPENAI_API_KEY` in `.env` file is correctly configured.

### 2. Module Not Found

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### 3. Port Already in Use

Modify `PORT` configuration in `.env` file, or specify in command line:

```bash
PORT=8001 python start.py
```

## Development

### Add New API Endpoints

Add new route functions in `main.py`.

### Modify Vision Analysis Logic

Edit `vision.py` file.


















