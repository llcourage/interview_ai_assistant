"""
Database model definitions
Supports user Plan, API Keys, Usage statistics
"""
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class PlanType(str, Enum):
    """User subscription plan types"""
    START = "start"      # Starter plan - 100k tokens lifetime, no reset, gpt-4o-mini
    NORMAL = "normal"    # Weekly plan $9.99/week - 1M tokens/week, gpt-4o-mini
    HIGH = "high"        # Monthly plan $19.99/month - 1M tokens/month, gpt-4o-mini
    ULTRA = "ultra"      # Pro plan $39.99/month - 5M tokens/month, gpt-4o-mini
    INTERNAL = "internal"  # Internal plan - unlimited tokens, gpt-4o (not for sale, manually added in Supabase)


class UserPlan(BaseModel):
    """User subscription plan"""
    user_id: str
    plan: PlanType = PlanType.NORMAL
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: Optional[str] = None  # active, canceled, past_due
    plan_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# UserApiKey removed - all users use server API Key


class UsageLog(BaseModel):
    """API call log"""
    user_id: str
    plan: PlanType
    api_endpoint: str  # /api/chat, /api/vision_query, etc
    model_used: str  # gpt-4o, gpt-4o-mini, etc
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0  # Cost (USD)
    success: bool = True
    error_message: Optional[str] = None
    created_at: datetime


class UsageQuota(BaseModel):
    """User quota management"""
    user_id: str
    plan: PlanType
    weekly_tokens_used: int = 0  # Tokens used this week
    monthly_tokens_used: int = 0  # Tokens used this month
    quota_reset_date: datetime  # Quota reset date
    created_at: datetime
    updated_at: datetime


# Plan quota definitions
PLAN_LIMITS = {
    PlanType.START: {
        "lifetime_token_limit": 100_000,  # 100k tokens lifetime, no reset
        "is_lifetime": True,  # Marked as lifetime quota, no monthly reset
        "models": ["gpt-4o-mini"],  # Only mini model
        "features": ["basic_chat", "image_analysis"]
    },
    PlanType.NORMAL: {
        "weekly_token_limit": 1_000_000,  # 1M tokens per week
        "is_lifetime": False,  # Weekly quota, resets weekly
        "models": ["gpt-4o-mini"],  # All paid plans use gpt-4o-mini
        "features": ["basic_chat", "image_analysis"]
    },
    PlanType.HIGH: {
        "monthly_token_limit": 1_000_000,  # 1M tokens per month
        "is_lifetime": False,  # Monthly quota, resets monthly
        "models": ["gpt-4o-mini"],  # All paid plans use gpt-4o-mini
        "features": ["basic_chat", "image_analysis"]
    },
    PlanType.ULTRA: {
        "monthly_token_limit": 5_000_000,  # 5M tokens per month
        "is_lifetime": False,  # Monthly quota, resets monthly
        "models": ["gpt-4o-mini"],  # All paid plans use gpt-4o-mini
        "features": ["basic_chat", "image_analysis"]
    },
    PlanType.INTERNAL: {
        "monthly_token_limit": None,  # Unlimited tokens
        "is_lifetime": False,  # Monthly quota (but unlimited)
        "is_unlimited": True,  # Mark as unlimited
        "models": ["gpt-4o"],  # Only Internal Plan uses gpt-4o
        "features": ["basic_chat", "image_analysis", "priority_support", "advanced_reasoning"]
    }
}


# Model pricing definitions (input/output per 1K tokens)
MODEL_PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "o1-mini": {"input": 0.003, "output": 0.012},
    "o1": {"input": 0.015, "output": 0.06},
}

