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
    START = "start"      # 入门计划 - 100k tokens 终身，不重置，gpt-4o-mini
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
    monthly_tokens_used: int = 0  # 本月已用 tokens
    quota_reset_date: datetime  # 配额重置日期
    created_at: datetime
    updated_at: datetime


# Plan quota definitions
PLAN_LIMITS = {
    PlanType.START: {
        "lifetime_token_limit": 100_000,  # 100k tokens lifetime, no reset
        "is_lifetime": True,  # 标识为终身配额，不进行月度重置
        "models": ["gpt-4o-mini"],  # Only mini model
        "features": ["basic_chat", "image_analysis"]
    },
    PlanType.NORMAL: {
        "monthly_token_limit": 500_000,  # 500k tokens per month
        "is_lifetime": False,
        "models": ["gpt-4o-mini"],  # Only mini model
        "features": ["basic_chat", "image_analysis", "speech_to_text", "priority_support"]
    },
    PlanType.HIGH: {
        "monthly_token_limit": 500_000,  # 500k tokens per month (same as Normal)
        "is_lifetime": False,
        "models": ["gpt-4o-mini", "gpt-4o"],  # Can access both mini and full gpt-4o
        "features": ["basic_chat", "image_analysis", "speech_to_text", "priority_support"]
    }
}


# Model 价格定义（输入/输出 per 1K tokens）
MODEL_PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "o1-mini": {"input": 0.003, "output": 0.012},
    "o1": {"input": 0.015, "output": 0.06},
}

