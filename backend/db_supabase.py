"""
Supabase 客户端配置
提供 Supabase 认证和数据库服务
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ 警告: 未设置 Supabase 配置，请在 .env 文件中添加 SUPABASE_URL 和 SUPABASE_ANON_KEY")

# 创建 Supabase 客户端
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


def get_supabase() -> Client:
    """获取 Supabase 客户端实例"""
    if not supabase_client:
        raise Exception("Supabase 客户端未初始化，请检查环境变量配置")
    return supabase_client

