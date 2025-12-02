"""
Supabase 认证模块
提供用户登录、注册、token 验证等功能
"""
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from db_supabase import get_supabase

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


