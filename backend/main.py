# ========== 必须在所有导入之前加载环境变量 ==========
from pathlib import Path
from dotenv import load_dotenv

# 明确指定 .env 文件路径，确保无论从哪里启动都能找到
backend_dir = Path(__file__).parent.resolve()
env_path = backend_dir / ".env"
# 使用 override=True 确保覆盖已存在的环境变量
load_dotenv(dotenv_path=str(env_path), override=True)

# ========== 现在可以导入其他模块 ==========
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import json
import platform
from typing import Optional, Union
from datetime import datetime
import stripe  # 导入 stripe 用于错误处理

# 导入现有模块
from vision import analyze_image
from speech import transcribe_audio
from openai import AsyncOpenAI

# 导入认证模块
from auth_supabase import (
    User, UserRegister, UserLogin, Token,
    register_user, login_user, get_current_active_user
)

# 导入新的数据库模块
from db_models import PlanType, PLAN_LIMITS, MODEL_PRICING
from db_operations import (
    get_user_plan, get_user_quota, increment_user_quota, check_rate_limit, log_usage
)
from payment_stripe import (
    create_checkout_session, handle_checkout_completed,
    handle_subscription_updated, handle_subscription_deleted,
    cancel_subscription, get_subscription_info
)

# ========== FastAPI App ==========

app = FastAPI(
    title="AI Interview Assistant API",
    description="AI 面试助手后端服务 - 支持多Plan订阅、限流、使用统计",
    version="2.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Request/Response Models ==========

class ChatRequest(BaseModel):
    """统一的 Chat 请求模型"""
    user_input: Optional[str] = None  # 文字输入
    image_base64: Optional[Union[str, list[str]]] = None  # 图片输入（单张或多张）
    context: Optional[str] = None  # 对话上下文
    prompt: Optional[str] = None  # 自定义提示词（用于图片分析）


class ChatResponse(BaseModel):
    """统一的 Chat 响应模型"""
    answer: str
    success: bool = True
    error: Optional[str] = None
    usage: Optional[dict] = None  # Token使用情况


class PlanResponse(BaseModel):
    """用户Plan信息"""
    plan: str
    daily_requests: int
    monthly_requests: int
    daily_limit: int
    monthly_limit: int
    features: list[str]
    subscription_info: Optional[dict] = None


class ApiKeyRequest(BaseModel):
    """API Key 请求"""
    api_key: str
    provider: str = "openai"


class CheckoutRequest(BaseModel):
    """创建支付会话请求"""
    plan: str
    success_url: str
    cancel_url: str


class SpeechToTextResponse(BaseModel):
    text: str
    language: str = ""
    duration: float = 0.0
    success: bool = True
    error: str = ""


# ========== Helper Functions ==========

async def get_api_client_for_user(user_id: str, plan: PlanType) -> tuple[AsyncOpenAI, str]:
    """根据用户Plan获取对应的OpenAI客户端和模型
    
    Returns:
        (AsyncOpenAI, model_name)
    """
    # 所有Plan都使用服务器的 API Key
    server_api_key = os.getenv("OPENAI_API_KEY")
    if not server_api_key:
        raise HTTPException(
            status_code=500,
            detail="服务器API Key未配置"
        )
    
    client = AsyncOpenAI(
        api_key=server_api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    
    # 根据Plan选择模型
    if plan == PlanType.NORMAL:
        model = "gpt-4o-mini"  # Normal使用mini
    elif plan == PlanType.HIGH:
        model = "gpt-4o"  # High使用完整版
    else:
        raise HTTPException(status_code=400, detail=f"不支持的Plan类型: {plan}")
    
    return client, model


# ========== API Endpoints ==========

@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "status": "running",
        "message": "AI Interview Assistant API v2.0",
        "version": "2.0.0"
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


# ========== 用户Plan相关 API ==========

@app.get("/api/plan", response_model=PlanResponse, tags=["Plan管理"])
async def get_plan(current_user: User = Depends(get_current_active_user)):
    """获取用户当前Plan信息"""
    user_plan = await get_user_plan(current_user.id)
    quota = await get_user_quota(current_user.id)
    
    limits = PLAN_LIMITS[user_plan.plan]
    
    # 获取订阅信息
    subscription_info = None
    if user_plan.plan != PlanType.STARTER:
        subscription_info = await get_subscription_info(current_user.id)
    
    return PlanResponse(
        plan=user_plan.plan.value,
        daily_requests=quota.daily_requests,
        monthly_requests=quota.monthly_requests,
        daily_limit=limits["daily_limit"],
        monthly_limit=limits["monthly_limit"],
        features=limits["features"],
        subscription_info=subscription_info
    )


@app.post("/api/plan/checkout", tags=["Plan管理"])
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user)
):
    """创建Stripe支付会话"""
    try:
        plan = PlanType(request.plan)
        
        checkout_data = await create_checkout_session(
            user_id=current_user.id,
            plan=plan,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            user_email=current_user.email  # 传递用户邮箱
        )
        
        return checkout_data
    except ValueError as e:
        # 配置错误，返回 400
        print(f"❌ Checkout 配置错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except AttributeError as e:
        # AttributeError 通常是 None.data 错误
        error_msg = f"数据访问错误: {str(e)}"
        print(f"❌ Checkout AttributeError: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)
    except stripe.error.StripeError as e:
        # Stripe API 错误
        error_msg = f"Stripe API 错误: {e.user_message if hasattr(e, 'user_message') else str(e)}"
        print(f"❌ Stripe API 错误: {e}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        # 其他错误
        error_msg = f"创建支付会话失败: {str(e)}"
        print(f"❌ Checkout 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/api/plan/cancel", tags=["Plan管理"])
async def cancel_plan(current_user: User = Depends(get_current_active_user)):
    """取消当前订阅"""
    success = await cancel_subscription(current_user.id)
    
    if success:
        return {"message": "订阅将在当前周期结束时取消"}
    else:
        raise HTTPException(status_code=400, detail="取消订阅失败")


# ========== API Key 管理已移除 ==========
# 所有用户都使用服务器的 API Key


# ========== 统一的 Chat API（核心接口）==========

@app.post("/api/chat", response_model=ChatResponse, tags=["AI功能"])
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    """统一的Chat接口 - 支持文字对话和图片分析
    
    - 如果有 image_base64：进行图片分析
    - 如果只有 user_input：进行文字对话
    - 自动根据用户Plan选择对应的API Key和模型
    - 自动进行限流检查
    - 自动记录使用统计
    """
    try:
        # 1. 检查限流
        allowed, error_msg = await check_rate_limit(current_user.id)
        if not allowed:
            raise HTTPException(status_code=429, detail=error_msg)
        
        # 2. 获取用户Plan
        user_plan = await get_user_plan(current_user.id)
        
        # 3. 获取对应的API客户端和模型
        client, model = await get_api_client_for_user(current_user.id, user_plan.plan)
        
        # 4. 处理请求
        if request.image_base64:
            # 图片分析
            print(f"🖼️ 用户 {current_user.id} ({user_plan.plan.value}) 请求图片分析")
            
            answer = await analyze_image(
                image_base64=request.image_base64,
                prompt=request.prompt,
                client=client,
                model=model
            )
            
            # 估算token使用（图片分析难以精确计算，这里用估算值）
            image_count = 1 if isinstance(request.image_base64, str) else len(request.image_base64)
            estimated_input_tokens = 1000 * image_count  # 每张图约1000 tokens
            estimated_output_tokens = len(answer) // 4  # 粗略估算
            
        elif request.user_input:
            # 文字对话
            print(f"💬 用户 {current_user.id} ({user_plan.plan.value}) 请求文字对话")
            
            messages = []
            
            # 添加系统提示
            messages.append({
                "role": "system",
                "content": """你是一个专业的技术面试助手。你的任务是：
1. 回答技术问题，提供清晰的解释和代码示例
2. 帮助用户理解面试题的解题思路
3. 提供最佳实践和优化建议
4. 保持简洁、专业的回答风格

请用中文回答，代码默认使用 Python。"""
            })
            
            # 添加上下文（如果有）
            if request.context:
                messages.append({
                    "role": "system",
                    "content": f"以下是之前的对话历史：\n\n{request.context}"
                })
            
            # 添加用户输入
            messages.append({
                "role": "user",
                "content": request.user_input
            })
            
            # 调用LLM
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            # 获取真实的token使用
            estimated_input_tokens = response.usage.prompt_tokens
            estimated_output_tokens = response.usage.completion_tokens
            
        else:
            raise HTTPException(
                status_code=400,
                detail="请提供 user_input（文字）或 image_base64（图片）"
            )
        
        # 5. 增加配额计数
        await increment_user_quota(current_user.id)
        
        # 6. 记录使用日志
        await log_usage(
            user_id=current_user.id,
            plan=user_plan.plan,
            api_endpoint="/api/chat",
            model_used=model,
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
            success=True
        )
        
        return ChatResponse(
            answer=answer,
            success=True,
            usage={
                "input_tokens": estimated_input_tokens,
                "output_tokens": estimated_output_tokens,
                "total_tokens": estimated_input_tokens + estimated_output_tokens,
                "model": model
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        print(f"❌ Chat API 失败: {error_message}")
        
        # 记录失败日志
        try:
            user_plan = await get_user_plan(current_user.id)
            await log_usage(
                user_id=current_user.id,
                plan=user_plan.plan,
                api_endpoint="/api/chat",
                model_used="unknown",
                success=False,
                error_message=error_message
            )
        except:
            pass
        
        return ChatResponse(
            answer=f"处理失败: {error_message}",
            success=False,
            error=error_message
        )


# ========== 语音转文字 API ==========

@app.post("/api/speech_to_text", response_model=SpeechToTextResponse, tags=["AI功能"])
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = "zh",
    current_user: User = Depends(get_current_active_user)
):
    """语音转文字接口 - 使用本地Whisper模型（不计入配额）"""
    try:
        # 读取音频数据
        audio_data = await audio.read()
        
        if len(audio_data) == 0:
            return SpeechToTextResponse(
                text="",
                success=False,
                error="音频文件为空"
            )
        
        print(f"🎤 用户 {current_user.id} 语音转文字: {audio.filename}, 大小: {len(audio_data)} 字节")
        
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


# ========== Stripe Webhook ==========

@app.get("/api/webhooks/stripe", tags=["Webhooks"])
async def stripe_webhook_get():
    """Webhook 端点健康检查（用于测试）"""
    # 检查必要的环境变量
    env_status = {
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
        "STRIPE_WEBHOOK_SECRET": bool(os.getenv("STRIPE_WEBHOOK_SECRET"))
    }
    
    all_configured = all(env_status.values())
    
    return {
        "status": "ok" if all_configured else "warning",
        "message": "Stripe Webhook endpoint is active. Use POST method for actual webhook events." if all_configured else "Endpoint is active but some environment variables are missing.",
        "endpoint": "/api/webhooks/stripe",
        "methods": ["POST", "GET"],
        "environment_variables": env_status,
        "ready": all_configured
    }

@app.post("/api/webhooks/stripe", tags=["Webhooks"])
async def stripe_webhook(request: Request):
    """Stripe Webhook Handler with signature verification and database updates"""
    
    body = await request.body()
    event_type = "unknown"
    event_id = "unknown"
    
    try:
        # Step 1: Get signature (body already retrieved above)
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            error_msg = "Missing stripe-signature header"
            print(f"ERROR: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Step 2: Get webhook secret from environment
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        if not webhook_secret:
            error_msg = "STRIPE_WEBHOOK_SECRET not configured"
            print(f"ERROR: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Step 3: Verify Stripe signature
        try:
            event = stripe.Webhook.construct_event(
                body, sig_header, webhook_secret
            )
        except ValueError as e:
            error_msg = f"Invalid payload: {str(e)}"
            print(f"ERROR: Webhook signature verification failed - {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        except stripe.error.SignatureVerificationError as e:
            error_msg = f"Invalid signature: {str(e)}"
            print(f"ERROR: Webhook signature verification failed - {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Step 4: Extract event info
        event_type = event.get("type", "unknown")
        event_id = event.get("id", "unknown")
        
        print(f"Received webhook event: {event_type} [id: {event_id}]")
        
        # Step 5: Handle different event types
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            await handle_checkout_completed(session)
            print(f"Successfully processed {event_type} [id: {event_id}]")
            
        elif event_type == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await handle_subscription_updated(subscription)
            print(f"Successfully processed {event_type} [id: {event_id}]")
            
        elif event_type == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await handle_subscription_deleted(subscription)
            print(f"Successfully processed {event_type} [id: {event_id}]")
            
        else:
            # Log unhandled events but return success (Stripe expects 200 for all received events)
            print(f"Unhandled event type: {event_type} [id: {event_id}] - returning success")
        
        # Step 6: Return success response
        return {
            "status": "success",
            "event_type": event_type,
            "event_id": event_id
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        # Catch all other exceptions and return 500 with details
        error_msg = f"Error processing webhook event {event_type} [id: {event_id}]: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


# ========== 保持向后兼容的API（逐步废弃）==========

@app.post("/api/vision_query", tags=["已废弃 - 请使用 /api/chat"])
async def vision_query_legacy(
    request: dict,
    current_user: User = Depends(get_current_active_user)
):
    """旧的图片分析接口（向后兼容）"""
    chat_request = ChatRequest(
        image_base64=request.get("image_base64"),
        prompt=request.get("prompt", "")
    )
    return await chat(chat_request, current_user)


@app.post("/api/text_chat", tags=["已废弃 - 请使用 /api/chat"])
async def text_chat_legacy(
    request: dict,
    current_user: User = Depends(get_current_active_user)
):
    """旧的文字对话接口（向后兼容）"""
    chat_request = ChatRequest(
        user_input=request.get("user_input"),
        context=request.get("context", "")
    )
    return await chat(chat_request, current_user)


# ========== 启动服务 ==========

if __name__ == "__main__":
    # 如果是直接运行（不是通过 uvicorn backend.main:app），需要处理导入路径
    import sys
    from pathlib import Path
    
    # 获取 backend 目录的绝对路径并添加到 sys.path
    backend_dir = Path(__file__).parent.resolve()
    project_root = backend_dir.parent.resolve()
    
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print("AI Interview Assistant Backend Service v2.0")
    print("=" * 60)
    print(f"Service URL: http://{host}:{port}")
    print(f"API Docs: http://{host}:{port}/docs")
    print(f"Health Check: http://{host}:{port}/health")
    print("=" * 60)
    print("Features:")
    print("  - Unified /api/chat endpoint")
    print("  - Plan subscription management")
    print("  - Usage statistics and rate limiting")
    print("  - Stripe payment integration")
    print("=" * 60)
    print("Tip: Use 'uvicorn backend.main:app --port 8000' from project root")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",  # 直接运行时，backend 已经在 sys.path 中
        host=host,
        port=port,
        reload=False,  # 直接运行时暂时禁用 reload，避免路径问题
        log_level="info"
    )
