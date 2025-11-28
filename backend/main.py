from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from vision import analyze_image

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="AI Interview Assistant API",
    description="AI 面试助手后端服务",
    version="1.0.0"
)

# 配置 CORS - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class VisionQueryRequest(BaseModel):
    image_base64: str | list[str]  # 支持单张或多张图片
    prompt: str = "" # 默认为空，使用 vision.py 中的新 Prompt

# 响应模型
class VisionQueryResponse(BaseModel):
    answer: str
    success: bool = True
    error: str = ""

@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "status": "running",
        "message": "AI Interview Assistant API is running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}

@app.post("/api/vision_query", response_model=VisionQueryResponse)
async def vision_query(request: VisionQueryRequest):
    """
    视觉分析接口
    
    接收 base64 编码的图片，调用 OpenAI Vision API 进行分析
    """
    try:
        # 验证 API 密钥
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            return VisionQueryResponse(
                answer="⚠️ 请配置 OpenAI API Key！\n\n请在 backend/.env 文件中设置 OPENAI_API_KEY",
                success=False,
                error="API Key not configured"
            )
        
        # 调用视觉分析函数
        answer = await analyze_image(
            image_base64=request.image_base64,
            prompt=request.prompt
        )
        
        return VisionQueryResponse(
            answer=answer,
            success=True
        )
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ 视觉分析失败: {error_message}")
        
        return VisionQueryResponse(
            answer=f"分析失败: {error_message}",
            success=False,
            error=error_message
        )

@app.post("/api/test")
async def test_endpoint(data: dict):
    """测试接口"""
    return {
        "message": "Test successful",
        "received": data
    }

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print("🔥 AI 面试助手后端服务")
    print("=" * 60)
    print(f"📡 服务地址: http://{host}:{port}")
    print(f"📚 API 文档: http://{host}:{port}/docs")
    print(f"🔧 健康检查: http://{host}:{port}/health")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


