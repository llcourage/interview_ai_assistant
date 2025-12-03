"""
数据库模型定义
支持用户Plan、API Keys、Usage统计
"""
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class PlanType(str, Enum):
    """用户订阅计划类型"""
    NORMAL = "normal"    # 付费计划 $19.9/week
    HIGH = "high"        # 付费计划 $29.9/week


class UserPlan(BaseModel):
    """用户订阅计划"""
    user_id: str
    plan: PlanType = PlanType.NORMAL
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: Optional[str] = None  # active, canceled, past_due
    plan_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# 已移除 UserApiKey - 所有用户使用服务器的 API Key


class UsageLog(BaseModel):
    """API 调用记录"""
    user_id: str
    plan: PlanType
    api_endpoint: str  # /api/chat, /api/vision_query, etc
    model_used: str  # gpt-4o, gpt-4o-mini, etc
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0  # 成本（美元）
    success: bool = True
    error_message: Optional[str] = None
    created_at: datetime


class UsageQuota(BaseModel):
    """用户配额管理"""
    user_id: str
    plan: PlanType
    daily_requests: int = 0  # 今日已用请求数
    monthly_requests: int = 0  # 本月已用请求数
    monthly_tokens_used: int = 0  # 本月已用 tokens
    daily_limit: int = 100  # 每日限制
    monthly_limit: int = 3000  # 每月限制
    last_request_at: Optional[datetime] = None
    quota_reset_date: datetime  # 配额重置日期
    created_at: datetime
    updated_at: datetime


# Plan 配额定义
PLAN_LIMITS = {
    PlanType.NORMAL: {
        "daily_limit": 200,  # 每日200次
        "monthly_limit": 5000,  # 每月5000次
        "monthly_token_limit": 500_000,  # 每月500k tokens
        "models": ["gpt-4o-mini"],  # 只能用mini
        "features": ["basic_chat", "image_analysis", "speech_to_text", "priority_support"]
    },
    PlanType.HIGH: {
        "daily_limit": -1,  # 无限制
        "monthly_limit": -1,  # 无限制
        "monthly_token_limit": 500_000,  # 每月500k tokens
        "models": ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"],  # 全模型
        "features": ["basic_chat", "image_analysis", "speech_to_text", "priority_support", "pdf_export", "advanced_analytics"]
    }
}


# Model 价格定义（输入/输出 per 1K tokens）
MODEL_PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "o1-mini": {"input": 0.003, "output": 0.012},
    "o1": {"input": 0.015, "output": 0.06},
}

