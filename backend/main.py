# ========== 必须在所有导入之前加载环境变量 ==========
from pathlib import Path
from dotenv import load_dotenv
import os

# 只在开发环境（本地）加载 .env 文件
# 在生产环境（Vercel）中，应该从系统环境变量读取
is_production = os.getenv("VERCEL") or os.getenv("ENVIRONMENT") == "production"
if not is_production:
    # 明确指定 .env 文件路径，确保无论从哪里启动都能找到
    backend_dir = Path(__file__).parent.resolve()
    env_path = backend_dir / ".env"
    # 不使用 override，优先使用系统环境变量（Vercel 环境变量）
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path), override=False)

# ========== 现在可以导入其他模块 ==========
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import os
import sys
import json
import platform
from typing import Optional, Union
from datetime import datetime
import stripe  # 导入 stripe 用于错误处理

# 导入现有模块 - 使用绝对导入（backend 作为包）
from backend.vision import analyze_image
from openai import AsyncOpenAI

# 导入认证模块
from backend.auth_supabase import (
    User, UserRegister, UserLogin, Token,
    register_user, login_user, get_current_active_user, verify_token
)

# 导入新的数据库模块
from backend.db_models import PlanType, PLAN_LIMITS, MODEL_PRICING
from backend.db_operations import (
    get_user_plan, get_user_quota, increment_user_quota, check_rate_limit, log_usage
)
from backend.payment_stripe import (
    create_checkout_session, handle_checkout_completed,
    handle_subscription_updated, handle_subscription_deleted,
    cancel_subscription, get_subscription_info
)

# ========== FastAPI App ==========

app = FastAPI(
    title="Desktop AI API",
    description="Desktop AI 后端服务 - Your AI assistant for daily usage, interviews, and productivity",
    version="2.0.0"
)

# 添加启动时的日志
@app.on_event("startup")
async def startup_event():
    import os
    is_vercel = os.getenv("VERCEL")
    is_desktop = getattr(sys, 'frozen', False)  # 检测是否为打包后的桌面版
    
    print("=" * 60)
    print("🚀 FastAPI 应用启动")
    if is_vercel:
        print(f"   环境: Vercel (云端)")
        print(f"   ✅ 所有 API Key 在云端")
    elif is_desktop:
        print(f"   环境: Desktop (桌面版)")
        print(f"   ⚠️  桌面版模式：不包含任何配置和 API Key")
        print(f"   ✅ 所有 API 请求将转发到 Vercel（包括认证、数据库、AI、支付）")
        vercel_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        print(f"   云端 API: {vercel_url}")
        print(f"   ✅ 桌面版不直接连接 Supabase 或任何外部服务")
    else:
        print(f"   环境: Local (本地开发)")
        print(f"   OPENAI_API_KEY 已配置: {bool(os.getenv('OPENAI_API_KEY'))}")
    print("=" * 60)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 静态文件服务（桌面版）==========
# 仅在桌面版模式下提供静态文件服务

def find_ui_directory():
    """查找 UI 目录"""
    import sys
    possible_dirs = []
    
    # 如果是打包后的 exe，UI 可能在多个位置
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent.resolve()
        # 1. exe 同目录的 ui/ 文件夹
        possible_dirs.append(exe_dir / "ui")
        # 2. 父目录的 ui/ 文件夹（用于 release_root 结构）
        parent_dir = exe_dir.parent.resolve()
        possible_dirs.append(parent_dir / "ui")
    else:
        # 开发环境
        backend_dir = Path(__file__).parent.resolve()
        project_root = backend_dir.parent.resolve()
        possible_dirs.append(project_root / "dist")
        possible_dirs.append(project_root / "ui")
    
    for dir_path in possible_dirs:
        if dir_path.exists() and (dir_path / "index.html").exists():
            return dir_path
    return None

# 查找并设置 UI 目录
ui_directory = find_ui_directory()
if ui_directory:
    print(f"📁 检测到 UI 目录: {ui_directory}")
    
    # 挂载静态资源目录
    assets_dir = ui_directory / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        print(f"✅ 已挂载静态资源: /assets")
else:
    print("ℹ️  未检测到 UI 目录，仅提供 API 服务")

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
    monthly_token_limit: Optional[int] = None
    monthly_tokens_used: Optional[int] = None
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


# ========== Helper Functions ==========

async def get_api_client_for_user(user_id: str, plan: PlanType) -> tuple[AsyncOpenAI, str]:
    """根据用户Plan获取对应的OpenAI客户端和模型
    
    Note: 此函数仅在非桌面版（Vercel/本地开发）环境下调用
    桌面版的所有请求都会直接转发到 Vercel API，不会调用此函数
    
    Returns:
        (AsyncOpenAI, model_name)
    """
    # 所有Plan都使用服务器的 API Key
    server_api_key = os.getenv("OPENAI_API_KEY")
    if not server_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not configured. Please configure it in Vercel Dashboard -> Settings -> Environment Variables"
        )
    
    client = AsyncOpenAI(
        api_key=server_api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    
    # Select model based on plan
    # Normal Plan: uses gpt-4o-mini
    # High Plan: uses gpt-4o (full version) by default, can also access gpt-4o-mini
    if plan == PlanType.NORMAL:
        model = "gpt-4o-mini"  # Normal Plan uses mini
    elif plan == PlanType.HIGH:
        model = "gpt-4o"  # High Plan uses full version by default
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported plan type: {plan}")
    
    return client, model


# ========== API Endpoints ==========

@app.get("/")
async def root():
    """根路径 - 健康检查或返回 UI"""
    # 尝试查找 UI 目录
    ui_dir = None
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent.resolve()
        ui_dir = exe_dir / "ui"
    else:
        backend_dir = Path(__file__).parent.resolve()
        project_root = backend_dir.parent.resolve()
        ui_dir = project_root / "ui"
    
    if ui_dir and (ui_dir / "index.html").exists():
        return FileResponse(str(ui_dir / "index.html"))
    else:
        # 否则返回 API 信息
        return {
            "status": "running",
            "message": "Desktop AI API v2.0",
            "version": "2.0.0"
        }


@app.get("/health")
@app.get("/api/health")  # 同时支持 /health 和 /api/health
async def health_check():
    """健康检查接口 - 包含环境变量状态"""
    is_vercel = os.getenv("VERCEL")
    env_status = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
        "STRIPE_SECRET_KEY": bool(os.getenv("STRIPE_SECRET_KEY")),
        "STRIPE_WEBHOOK_SECRET": bool(os.getenv("STRIPE_WEBHOOK_SECRET"))
    }
    
    all_configured = all(env_status.values())
    
    return {
        "status": "healthy" if all_configured else "warning",
        "environment": "Vercel" if is_vercel else "Local",
        "message": "All environment variables configured" if all_configured else "Some environment variables are missing",
        "environment_variables": env_status,
        "ready": all_configured
    }


# ========== 认证相关 API ==========

@app.post("/api/register", response_model=Token, tags=["认证"])
async def register(user_data: UserRegister, http_request: Request):
    """用户注册"""
    # 如果是桌面版，转发到 Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/register",
                    json={"email": user_data.email, "password": user_data.password},
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"无法连接到云端 API: {str(e)}")
    
    # 非桌面版：正常处理
    return await register_user(user_data.email, user_data.password)


@app.post("/api/login", response_model=Token, tags=["认证"])
async def login(user_data: UserLogin, http_request: Request):
    """用户登录"""
    # 如果是桌面版，转发到 Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/login",
                    json={"email": user_data.email, "password": user_data.password},
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"无法连接到云端 API: {str(e)}")
    
    # 非桌面版：正常处理
    return await login_user(user_data.email, user_data.password)


@app.get("/api/auth/google/url", tags=["认证"])
async def get_google_oauth_url_endpoint(redirect_to: Optional[str] = None, http_request: Request = None):
    """获取 Google OAuth 授权 URL"""
    from backend.auth_supabase import get_google_oauth_url
    
    # 如果是桌面版，转发到 Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                params = {}
                if redirect_to:
                    params["redirect_to"] = redirect_to
                response = await http_client.get(
                    f"{vercel_api_url}/api/auth/google/url",
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"无法连接到云端 API: {str(e)}")
    
    # 非桌面版：正常处理
    # 如果没有提供 redirect_to，使用请求来源
    if not redirect_to and http_request:
        origin = http_request.headers.get("Origin") or http_request.headers.get("Referer", "").rsplit("/", 1)[0]
        redirect_to = origin if origin else None
    
    url = await get_google_oauth_url(redirect_to)
    return {"url": url}


@app.get("/api/auth/callback", tags=["认证"])
async def oauth_callback(code: str, state: Optional[str] = None, http_request: Request = None):
    """处理 OAuth 回调"""
    from backend.db_supabase import get_supabase
    
    # 如果是桌面版，转发到 Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        async with httpx.AsyncClient() as http_client:
            try:
                params = {"code": code}
                if state:
                    params["state"] = state
                response = await http_client.get(
                    f"{vercel_api_url}/api/auth/callback",
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"无法连接到云端 API: {str(e)}")
    
    # 非桌面版：正常处理
    try:
        supabase = get_supabase()
        # 使用 code 交换 session - 使用与 login_user 相同的方式
        response = supabase.auth.exchange_code_for_session(code)
        
        # 调试日志
        print(f"🔍 OAuth 回调响应类型: {type(response)}")
        
        if not response.user:
            print(f"❌ OAuth 回调失败：response.user 为空")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth 回调失败：无法获取用户信息"
            )
        
        if not response.session:
            print(f"❌ OAuth 回调失败：response.session 为空")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth 回调失败：无法获取会话信息"
            )
        
        # 返回 token 信息 - 使用与 login_user 相同的方式
        token = Token(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email
            }
        )
        
        return token
    except HTTPException:
        raise
    except AttributeError as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ OAuth 回调属性错误: {e}")
        print(f"错误堆栈:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth 回调处理失败：响应格式不正确 - {str(e)}"
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ OAuth 回调处理错误: {e}")
        print(f"错误类型: {type(e)}")
        print(f"错误堆栈:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth 回调处理失败: {str(e)}"
        )


@app.get("/api/me", response_model=User, tags=["认证"])
async def read_users_me(http_request: Request):
    """获取当前用户信息"""
    # 如果是桌面版，转发到 Vercel（不验证 token，让 Vercel 验证）
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="缺少认证 token")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.get(
                    f"{vercel_api_url}/api/me",
                    headers={"Authorization": auth_header},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"无法连接到云端 API: {str(e)}")
    
    # 非桌面版：正常处理（需要验证 token）
    # 从请求头获取 token
    auth_header = http_request.headers.get("Authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 token")
    
    token = auth_header.replace("Bearer ", "")
    current_user = await verify_token(token)
    return current_user


# ========== 用户Plan相关 API ==========

@app.get("/api/plan", response_model=PlanResponse, tags=["Plan管理"])
async def get_plan(http_request: Request):
    """获取用户当前Plan信息"""
    # 如果是桌面版，转发到 Vercel（不验证 token，让 Vercel 验证）
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="缺少认证 token")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.get(
                    f"{vercel_api_url}/api/plan",
                    headers={"Authorization": auth_header},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"无法连接到云端 API: {str(e)}")
    
    # 非桌面版：正常处理（需要验证 token）
    auth_header = http_request.headers.get("Authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 token")
    
    token = auth_header.replace("Bearer ", "")
    current_user = await verify_token(token)
    user_plan = await get_user_plan(current_user.id)
    quota = await get_user_quota(current_user.id)
    
    limits = PLAN_LIMITS[user_plan.plan]
    
    # 获取订阅信息
    # Get subscription info for all plans (both NORMAL and HIGH have subscriptions)
    subscription_info = await get_subscription_info(current_user.id)
    
    monthly_token_limit = limits.get("monthly_token_limit")
    monthly_tokens_used = getattr(quota, 'monthly_tokens_used', 0)
    
    return PlanResponse(
        plan=user_plan.plan.value,
        daily_requests=quota.daily_requests,
        monthly_requests=quota.monthly_requests,
        daily_limit=limits["daily_limit"],
        monthly_limit=limits["monthly_limit"],
        monthly_token_limit=monthly_token_limit,
        monthly_tokens_used=monthly_tokens_used,
        features=limits["features"],
        subscription_info=subscription_info
    )


@app.post("/api/plan/checkout", tags=["Plan管理"])
async def create_checkout(
    request: CheckoutRequest,
    http_request: Request
):
    """创建Stripe支付会话"""
    # 如果是桌面版，转发到 Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        
        if not auth_header:
            raise HTTPException(status_code=401, detail="缺少认证 token")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/plan/checkout",
                    json={
                        "plan": request.plan,
                        "success_url": request.success_url,
                        "cancel_url": request.cancel_url
                    },
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"无法连接到云端 API: {str(e)}")
    
    # 非桌面版：正常处理
    try:
        # 验证 token 并获取用户信息
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="缺少认证 token")
        
        token = auth_header.replace("Bearer ", "")
        current_user = await verify_token(token)
        
        # 创建支付会话
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
async def cancel_plan(http_request: Request):
    """取消当前订阅"""
    # 如果是桌面版，转发到 Vercel
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        
        if not auth_header:
            raise HTTPException(status_code=401, detail="缺少认证 token")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/plan/cancel",
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"无法连接到云端 API: {str(e)}")
    
    # 非桌面版：正常处理（需要验证 token）
    auth_header = http_request.headers.get("Authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证 token")
    
    token = auth_header.replace("Bearer ", "")
    current_user = await verify_token(token)
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
    http_request: Request
):
    """统一的Chat接口 - 支持文字对话和图片分析
    
    - 如果有 image_base64：进行图片分析
    - 如果只有 user_input：进行文字对话
    - 自动根据用户Plan选择对应的API Key和模型
    - 自动进行限流检查
    - 自动记录使用统计
    """
    # 如果是桌面版，直接转发到 Vercel（不验证 token，让 Vercel 验证）
    is_desktop = getattr(sys, 'frozen', False)
    if is_desktop:
        import httpx
        vercel_api_url = os.getenv("VERCEL_API_URL", "https://www.desktopai.org")
        auth_header = http_request.headers.get("Authorization", "")
        
        if not auth_header:
            raise HTTPException(status_code=401, detail="缺少认证 token，无法转发请求到云端")
        
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.post(
                    f"{vercel_api_url}/api/chat",
                    json={
                        "user_input": request.user_input,
                        "image_base64": request.image_base64,
                        "context": request.context,
                        "prompt": request.prompt
                    },
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"无法连接到云端 API: {str(e)}"
                )
    
    # 非桌面版：正常处理（需要验证 token）
    try:
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="缺少认证 token")
        
        token = auth_header.replace("Bearer ", "")
        current_user = await verify_token(token)
        
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
            
            answer, token_usage = await analyze_image(
                image_base64=request.image_base64,
                prompt=request.prompt,
                client=client,
                model=model
            )
            
            # 使用真实的 token 使用量
            estimated_input_tokens = token_usage["input_tokens"]
            estimated_output_tokens = token_usage["output_tokens"]
            
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
        
        # 5. 计算总 token 使用量
        total_tokens = estimated_input_tokens + estimated_output_tokens
        
        # 6. 增加配额计数（包括 token 使用量）
        await increment_user_quota(current_user.id, tokens_used=total_tokens)
        
        # 7. 记录使用日志
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
                "total_tokens": total_tokens,
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


# ========== SPA 路由支持（必须在最后定义，作为 catch-all）==========
# 只有在检测到 UI 目录时才添加 SPA 路由
if ui_directory:
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """提供 SPA 路由支持"""
        # 排除 API 和文档路径
        if (full_path.startswith("api/") or 
            full_path in ["docs", "redoc", "openapi.json"]):
            raise HTTPException(status_code=404, detail="Not found")
        
        # 返回 index.html
        index_path = ui_directory / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="UI not found")


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
    print("Desktop AI Backend Service v2.0")
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
        app,  # 直接传递 app 对象，而不是字符串（PyInstaller 打包后无法使用字符串导入）
        host=host,
        port=port,
        reload=False,  # 直接运行时暂时禁用 reload，避免路径问题
        log_level="info"
    )
