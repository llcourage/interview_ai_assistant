"""
Supabase 客户端配置
提供 Supabase 认证和数据库服务

⚠️ 重要：后端使用 SERVICE_ROLE_KEY 以绕过 RLS (Row Level Security)
这样可以确保数据库操作（INSERT/UPDATE）不会被 RLS 策略阻止
"""
import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# 明确指定 .env 文件路径
backend_dir = Path(__file__).parent.resolve()
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)


# Supabase 配置
# 后端使用 SERVICE_ROLE_KEY 以绕过 RLS 限制
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# 优先使用 SERVICE_ROLE_KEY，如果没有则使用 ANON_KEY（但会导致 RLS 错误）
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY

# 调试：检查使用的是哪个 key
if SUPABASE_SERVICE_ROLE_KEY:
    # 检查 key 是否真的是 service_role（不是 anon）
    # service_role key 的 JWT payload 中 role 字段应该是 "service_role"
    import base64
    import json
    try:
        # JWT 格式：header.payload.signature
        parts = SUPABASE_SERVICE_ROLE_KEY.split('.')
        if len(parts) >= 2:
            # Decode payload (添加 padding 如果 needed)
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)  # Add padding
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            role = decoded.get('role', 'unknown')
            if role != 'service_role':
                print(f"⚠️ WARNING: SUPABASE_SERVICE_ROLE_KEY appears to have role='{role}', not 'service_role'!")
                print(f"   This will cause RLS policy violations. Please check your .env file.")
    except Exception:
        pass  # 如果解码失败，忽略（可能是格式问题）

# 创建 Supabase 客户端
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# 注意：模块级别的 print 已移除，避免 Windows 控制台编码问题
# 配置检查会在应用启动时通过日志系统处理


def get_supabase() -> Client:
    """获取 Supabase 客户端实例
    
    注意：此客户端使用 SERVICE_ROLE_KEY，可以绕过 RLS 限制
    仅用于后端服务器端操作，绝对不能暴露给前端
    """
    if not supabase_client:
        raise Exception("Supabase 客户端未初始化，请检查环境变量配置")
    return supabase_client


