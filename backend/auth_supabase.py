"""
Supabase 认证模块
提供用户登录、注册、token 验证等功能
"""
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from backend.db_supabase import get_supabase

# HTTP Bearer token
security = HTTPBearer()


class UserRegister(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class User(BaseModel):
    id: str
    email: str
    created_at: Optional[str] = None


# ========== 认证函数 ==========

async def register_user(email: str, password: str) -> Token:
    """注册新用户"""
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="注册失败"
            )
        
        return Token(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"注册失败: {str(e)}"
        )


async def login_user(email: str, password: str) -> Token:
    """用户登录"""
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )
        
        return Token(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"登录失败: {str(e)}"
        )


async def verify_token(token: str) -> User:
    """验证 token 并返回用户信息
    
    使用 Supabase REST API 直接验证 token
    """
    try:
        import httpx
        
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase 配置未设置"
            )
        
        # 使用 Supabase REST API 验证 token
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": supabase_key
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Supabase auth 返回状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token 验证失败：无效的 token 或 token 已过期"
                )
            
            user_data = response.json()
            
            # 检查是否有用户数据
            if not user_data or not user_data.get("id"):
                print(f"❌ 用户数据为空: {user_data}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token 验证失败：用户不存在"
                )
            
            return User(
                id=user_data["id"],
                email=user_data.get("email", ""),
                created_at=user_data.get("created_at")
            )
            
    except httpx.HTTPError as e:
        print(f"❌ HTTP 请求错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 验证失败：无法连接到认证服务"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Token 验证错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 验证失败: {str(e)}"
        )


# ========== 依赖项：获取当前用户 ==========

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """获取当前登录用户（依赖项）"""
    token = credentials.credentials
    return await verify_token(token)


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    return current_user


async def get_google_oauth_url(redirect_to: str = None) -> str:
    """获取 Google OAuth 授权 URL"""
    try:
        # 对于 OAuth，我们需要使用 ANON_KEY 而不是 SERVICE_ROLE_KEY
        # 因为 OAuth 是用户认证流程，需要正常的 Supabase 认证
        import os
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        
        print(f"🔐 检查 Supabase 配置:")
        print(f"   SUPABASE_URL: {'已设置' if supabase_url else '未设置'} ({supabase_url[:50] if supabase_url else 'N/A'}...)")
        print(f"   SUPABASE_ANON_KEY: {'已设置' if supabase_anon_key else '未设置'} ({'***' + supabase_anon_key[-10:] if supabase_anon_key else 'N/A'})")
        
        if not supabase_url or not supabase_anon_key:
            error_msg = "Supabase 配置缺失: "
            if not supabase_url:
                error_msg += "SUPABASE_URL 未设置; "
            if not supabase_anon_key:
                error_msg += "SUPABASE_ANON_KEY 未设置; "
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg.strip()
            )
        
        # 创建使用 ANON_KEY 的 Supabase 客户端（用于 OAuth）
        supabase = create_client(supabase_url, supabase_anon_key)
        
        # 构建重定向 URL
        if not redirect_to:
            # 默认重定向到前端登录页面
            redirect_to = os.getenv("FRONTEND_URL", "https://www.desktopai.org")
        
        # 确保 redirect_to 是完整的 URL
        if not redirect_to.startswith("http"):
            redirect_to = f"https://{redirect_to}" if not redirect_to.startswith("localhost") else f"http://{redirect_to}"
        
        # 构建回调 URL
        # 注意：对于 Electron 和 Web，OAuth 回调都应该指向前端页面（/auth/callback）
        # 前端会使用 Supabase JS SDK 处理 PKCE，然后调用后端 API 设置 session cookie
        # 不要改为 /api/auth/callback，因为后端无法处理 PKCE（没有 code_verifier）
        if redirect_to.endswith("/auth/callback"):
            callback_url = redirect_to
        else:
            # 如果 redirect_to 不包含 /auth/callback，添加它
            callback_url = f"{redirect_to}/auth/callback" if not redirect_to.endswith("/") else f"{redirect_to}auth/callback"
        
        # 获取 Google OAuth URL
        # 注意：Supabase Python SDK 默认使用 PKCE
        # 由于回调会在前端处理（使用 Supabase JS SDK），PKCE 会被正确处理
        # 前端会从浏览器存储中获取 code_verifier
        print(f"🔐 准备调用 Supabase OAuth，provider: google, redirect_to: {callback_url}")
        try:
            response = supabase.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": callback_url
                }
            })
            print(f"🔐 Supabase OAuth 响应类型: {type(response)}")
            print(f"🔐 Supabase OAuth 响应内容: {response}")
            
            if not response:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="获取 Google OAuth URL 失败: Supabase 返回空响应"
                )
            
            # Supabase Python SDK 返回的可能是字典或对象
            url = None
            if isinstance(response, dict):
                url = response.get("url") or response.get("data", {}).get("url")
            elif hasattr(response, "url"):
                # 如果是对象，直接获取 url 属性
                url = response.url
            elif hasattr(response, "data"):
                # 如果有 data 属性，尝试从 data 中获取
                data = response.data
                if isinstance(data, dict):
                    url = data.get("url")
                elif hasattr(data, "url"):
                    url = data.url
            
            # 如果还是没有找到，尝试转换为字符串再解析（最后的手段）
            if not url:
                response_str = str(response)
                print(f"🔐 尝试从响应字符串中提取 URL: {response_str[:200]}")
                # 这里可以添加更多的解析逻辑，但通常不应该到达这里
            
            if not url:
                print(f"❌ Supabase OAuth 响应中没有找到 URL，响应内容: {response}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取 Google OAuth URL 失败: Supabase 返回的响应中没有 URL。响应类型: {type(response)}, 响应内容: {str(response)[:200]}"
                )
            
            print(f"✅ 成功获取 Google OAuth URL: {url[:100]}...")
            return url
        except Exception as oauth_error:
            import traceback
            oauth_trace = traceback.format_exc()
            print(f"❌ Supabase OAuth 调用异常: {oauth_error}")
            print(f"详细错误信息:\n{oauth_trace}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"调用 Supabase OAuth API 失败: {str(oauth_error)}"
            )
    except HTTPException:
        # 重新抛出 HTTPException
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ 获取 Google OAuth URL 失败: {e}")
        print(f"详细错误信息:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 Google OAuth URL 失败: {str(e)}"
        )

