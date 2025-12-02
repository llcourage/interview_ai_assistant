"""
Supabase 客户端配置
提供 Supabase 认证和数据库服务

⚠️ 重要：后端使用 SERVICE_ROLE_KEY 以绕过 RLS (Row Level Security)
这样可以确保数据库操作（INSERT/UPDATE）不会被 RLS 策略阻止
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase 配置
# 后端使用 SERVICE_ROLE_KEY 以绕过 RLS 限制
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ 警告: 未设置 Supabase 配置")
    print("   请在环境变量中添加:")
    print("   - SUPABASE_URL")
    print("   - SUPABASE_SERVICE_ROLE_KEY (推荐，用于后端数据库操作)")
    print("   或 SUPABASE_ANON_KEY (如果 SERVICE_ROLE_KEY 不可用)")

# 创建 Supabase 客户端
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# 检查是否使用了 SERVICE_ROLE_KEY
if os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
    print("✅ 使用 SUPABASE_SERVICE_ROLE_KEY (可以绕过 RLS)")
else:
    print("⚠️ 使用 SUPABASE_ANON_KEY (可能受 RLS 限制，建议使用 SERVICE_ROLE_KEY)")


def get_supabase() -> Client:
    """获取 Supabase 客户端实例
    
    注意：此客户端使用 SERVICE_ROLE_KEY，可以绕过 RLS 限制
    仅用于后端服务器端操作，绝对不能暴露给前端
    """
    if not supabase_client:
        raise Exception("Supabase 客户端未初始化，请检查环境变量配置")
    return supabase_client


