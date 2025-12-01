from fastapi import FastAPI, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import json
import platform
from pathlib import Path
from dotenv import load_dotenv
from vision import analyze_image
from speech import transcribe_audio
from openai import AsyncOpenAI
from datetime import timedelta
from auth_supabase import (
    User, UserRegister, UserLogin, Token,
    register_user, login_user, get_current_active_user
)

# 加载环境变量
load_dotenv()
load_dotenv('.env.plans')  # 加载 Plan API Keys

# 🔑 获取 Electron 配置文件路径
def get_electron_config_path():
    """获取 Electron 配置文件路径"""
    system = platform.system()
    app_name = "AI Interview Assistant"  # 需要与 Electron app 名称匹配
    
    if system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / app_name / "config.json"
    elif system == "Darwin":  # macOS
        home = Path.home()
        return home / "Library" / "Application Support" / app_name / "config.json"
    else:  # Linux
        home = Path.home()
        return home / ".config" / app_name.lower().replace(" ", "-") / "config.json"
    
    return None

# 🔑 从配置文件读取 API Key
def get_api_key_from_config():
    """从 Electron 配置文件读取 API Key"""
    config_path = get_electron_config_path()
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_key = config.get('apiKey')
                if api_key:
                    print(f"✅ 从配置文件读取 API Key: {config_path}")
                    return api_key
        except Exception as e:
            print(f"⚠️ 读取配置文件失败: {e}")
    return None

# 🔑 获取 API Key（优先从配置文件，其次从环境变量）
def get_api_key(plan_type: str = "starter"):
    """
    获取 API Key，优先级：配置文件 > 环境变量
    plan_type: "starter" | "normal" | "high"
    """
    # Starter Plan: 从配置文件读取用户自定义的 API Key
    if plan_type == "starter":
        api_key = get_api_key_from_config()
        if api_key:
            return api_key, None
        return None, None
    
    # Normal Plan: GPT-4o Mini (使用 OpenAI API)
    elif plan_type == "normal":
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if api_key and api_key != "your_openai_api_key_here":
            return api_key, base_url
        return None, None
    
    # High Plan: ChatGPT (OpenAI)
    elif plan_type == "high":
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if api_key and api_key != "your_openai_api_key_here":
            return api_key, base_url
        return None, None
    
    return None, None

# 🔑 动态获取 API Key 的函数（支持 plan 类型）
def get_current_api_key(plan_type: str = "starter"):
    """每次调用时重新读取 API Key（支持动态更新）
    
    Args:
        plan_type: "starter" | "normal" | "high"
            - starter: 用户自定义 API Key（从配置文件读取）
            - normal: DeepSeek API
            - high: ChatGPT API
    """
    api_key, base_url = get_api_key(plan_type)
    return api_key, base_url

# ⚠️ 不再使用全局客户端，而是在每个请求中动态创建

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
    plan: str = "starter"  # "starter" | "normal" | "high"

class TextChatRequest(BaseModel):
    user_input: str  # 用户输入
    context: str = ""  # 对话上下文（可选）
    plan: str = "starter"  # "starter" | "normal" | "high"

# 响应模型
class VisionQueryResponse(BaseModel):
    answer: str
    success: bool = True
    error: str = ""

class TextChatResponse(BaseModel):
    answer: str
    success: bool = True
    error: str = ""

class SpeechToTextResponse(BaseModel):
    text: str
    language: str = ""
    duration: float = 0.0
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

# ========== AI 功能 API ==========

@app.post("/api/vision_query", response_model=VisionQueryResponse)
async def vision_query(request: VisionQueryRequest):
    """
    视觉分析接口
    
    接收 base64 编码的图片，调用 OpenAI Vision API 进行分析
    """
    try:
        # 🔑 根据 plan 类型获取对应的 API Key 和 Base URL
        plan_type = request.plan or "starter"
        api_key, base_url = get_current_api_key(plan_type)
        
        if not api_key:
            plan_name = {"starter": "Starter", "normal": "Normal", "high": "High"}.get(plan_type, "Starter")
            error_msg = f"⚠️ {plan_name} Plan API Key not configured!"
            if plan_type == "starter":
                error_msg += "\n\nPlease configure your OpenAI API Key in settings."
            return VisionQueryResponse(
                answer=error_msg,
                success=False,
                error="API Key not configured"
            )
        
        # 🔑 使用对应的 API Key 和 Base URL 创建客户端
        dynamic_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1"
        )
        
        # 🤖 根据 plan 类型选择模型
        model_map = {
            "starter": os.getenv("OPENAI_MODEL", "gpt-4o"),  # Starter: 用户自己的 OpenAI 模型
            "normal": "gpt-4o-mini",  # Normal: GPT-4o Mini（便宜且支持 Vision）
            "high": "gpt-4o"  # High: GPT-4o（最强性能）
        }
        model = model_map.get(plan_type, "gpt-4o")
        
        print(f"🎯 Plan: {plan_type}, Model: {model}, Base URL: {base_url}")
        
        # 调用视觉分析函数（需要传入客户端和模型）
        answer = await analyze_image(
            image_base64=request.image_base64,
            prompt=request.prompt,
            client=dynamic_client,
            model=model
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

@app.post("/api/text_chat", response_model=TextChatResponse)
async def text_chat(request: TextChatRequest):
    """
    文字对话接口
    
    接收用户输入和上下文，调用 OpenAI GPT 进行对话
    """
    try:
        # 🔑 根据 plan 类型获取对应的 API Key 和 Base URL
        plan_type = request.plan or "starter"
        api_key, base_url = get_current_api_key(plan_type)
        
        if not api_key:
            plan_name = {"starter": "Starter", "normal": "Normal", "high": "High"}.get(plan_type, "Starter")
            error_msg = f"⚠️ {plan_name} Plan API Key not configured!"
            if plan_type == "starter":
                error_msg += "\n\nPlease configure your OpenAI API Key in settings."
            return TextChatResponse(
                answer=error_msg,
                success=False,
                error="API Key not configured"
            )
        
        # 🔑 使用对应的 API Key 和 Base URL 创建客户端
        dynamic_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1"
        )
        
        # 构建消息
        messages = []
        
        # 添加系统提示（针对面试助手场景）
        messages.append({
            "role": "system",
            "content": """你是一个专业的技术面试助手。你的任务是：
1. 回答技术问题，提供清晰的解释和代码示例
2. 帮助用户理解面试题的解题思路
3. 提供最佳实践和优化建议
4. 保持简洁、专业的回答风格

请用中文回答，代码默认使用 Python。"""
        })
        
        # 🚨 如果有上下文，截断到最近 10 轮对话
        if request.context:
            # 按双换行符分割对话
            context_parts = request.context.strip().split('\n\n')
            
            # 🚨 只保留最近 10 轮对话（每轮包含 User 和 AI）
            max_conversations = 10
            if len(context_parts) > max_conversations:
                truncated_context = '\n\n'.join(context_parts[-max_conversations:])
                print(f"📊 上下文截断: {len(context_parts)} 轮 -> {max_conversations} 轮")
            else:
                truncated_context = request.context
            
            messages.append({
                "role": "system",
                "content": f"以下是之前的对话历史（最近 {min(len(context_parts), max_conversations)} 轮）：\n\n{truncated_context}"
            })
        
        # 添加用户当前输入
        messages.append({
            "role": "user",
            "content": request.user_input
        })
        
        # 🤖 根据 plan 类型选择模型
        model_map = {
            "starter": os.getenv("OPENAI_MODEL", "gpt-4o"),  # Starter: 用户自己的 OpenAI 模型
            "normal": "gpt-4o-mini",  # Normal: GPT-4o Mini（便宜且支持对话）
            "high": "gpt-4o"  # High: GPT-4o（最强性能）
        }
        model = model_map.get(plan_type, "gpt-4o")
        
        print(f"🎯 Plan: {plan_type}, Model: {model}, Base URL: {base_url}")
        print(f"📝 用户输入: {request.user_input[:100]}...")
        
        response = await dynamic_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2000,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        print(f"✅ 对话完成，回复长度: {len(answer)} 字符")
        
        return TextChatResponse(
            answer=answer,
            success=True
        )
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ 对话失败: {error_message}")
        
        return TextChatResponse(
            answer=f"对话失败: {error_message}",
            success=False,
            error=error_message
        )

@app.post("/api/speech_to_text", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = "zh"
):
    """
    语音转文字接口
    
    接收音频文件，使用本地 Whisper 模型转换为文字
    """
    try:
        # 读取音频数据
        audio_data = await audio.read()
        
        if len(audio_data) == 0:
            return SpeechToTextResponse(
                text="",
                success=False,
                error="音频文件为空"
            )
        
        print(f"🎤 收到音频文件: {audio.filename}, 大小: {len(audio_data)} 字节")
        
        # 调用语音转文字
        result = await transcribe_audio(audio_data, language=language)
        
        return SpeechToTextResponse(
            text=result["text"],
            language=result.get("language", ""),
            duration=result.get("duration", 0.0),
            success=True
        )
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ 语音转文字失败: {error_message}")
        
        return SpeechToTextResponse(
            text="",
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


