"""
Unit tests for db_operations module
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
from backend.db_operations import get_user_plan, create_user_plan, update_user_plan
from backend.db_models import UserPlan, PlanType


class TestGetUserPlan:
    """Test cases for get_user_plan function"""
    
    @pytest.mark.asyncio
    async def test_get_user_plan_existing_record(self):
        """Test getting user plan when record exists"""
        user_id = "test_user_123"
        now = datetime.now()
        
        # Mock Supabase response with existing plan
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": "cus_123",
            "stripe_subscription_id": "sub_123",
            "subscription_status": "active",
            "plan_expires_at": None,
            "next_update_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }]
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin:
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.user_id == user_id
            assert result.plan == PlanType.NORMAL
            assert result.stripe_customer_id == "cus_123"
            assert result.stripe_subscription_id == "sub_123"
            assert result.subscription_status == "active"
    
    @pytest.mark.asyncio
    async def test_get_user_plan_no_record(self):
        """Test getting user plan when no record exists - should create default plan"""
        user_id = "test_user_456"
        
        # Mock Supabase response with no data
        mock_response = MagicMock()
        mock_response.data = []
        
        # Mock create_user_plan to return a default plan
        mock_default_plan = UserPlan(
            user_id=user_id,
            plan=PlanType.START,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.create_user_plan', new_callable=AsyncMock) as mock_create:
            
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            mock_create.return_value = mock_default_plan
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.user_id == user_id
            assert result.plan == PlanType.START
            mock_create.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_plan_expired_plan(self):
        """Test getting user plan when plan has expired - should downgrade to START"""
        user_id = "test_user_789"
        now = datetime.now()
        expired_time = now - timedelta(days=1)  # Plan expired 1 day ago
        
        # Mock Supabase response with expired plan
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": "cus_456",
            "stripe_subscription_id": "sub_456",
            "subscription_status": "canceled",
            "plan_expires_at": expired_time.isoformat(),
            "next_update_at": None,
            "created_at": (now - timedelta(days=30)).isoformat(),
            "updated_at": (now - timedelta(days=1)).isoformat()
        }]
        
        # Mock update_user_plan to handle downgrade
        mock_updated_plan = UserPlan(
            user_id=user_id,
            plan=PlanType.START,
            plan_expires_at=None,
            created_at=now - timedelta(days=30),
            updated_at=now
        )
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.update_user_plan', new_callable=AsyncMock) as mock_update:
            
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            mock_update.return_value = mock_updated_plan
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.plan == PlanType.START
            # Verify update_user_plan was called to downgrade
            mock_update.assert_called_once_with(
                user_id=user_id,
                plan=PlanType.START,
                plan_expires_at=None
            )
    
    @pytest.mark.asyncio
    async def test_get_user_plan_not_expired(self):
        """Test getting user plan when plan hasn't expired - should keep current plan"""
        user_id = "test_user_101"
        now = datetime.now()
        future_time = now + timedelta(days=7)  # Plan expires in 7 days
        
        # Mock Supabase response with non-expired plan
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "high",
            "stripe_customer_id": "cus_789",
            "stripe_subscription_id": "sub_789",
            "subscription_status": "active",
            "plan_expires_at": future_time.isoformat(),
            "next_update_at": future_time.isoformat(),
            "created_at": (now - timedelta(days=30)).isoformat(),
            "updated_at": now.isoformat()
        }]
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.update_user_plan', new_callable=AsyncMock) as mock_update:
            
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.plan == PlanType.HIGH
            # Verify update_user_plan was NOT called (plan not expired)
            mock_update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_user_plan_response_none(self):
        """Test getting user plan when response is None - should create default plan"""
        user_id = "test_user_202"
        
        # Mock Supabase response returning None
        mock_response = None
        
        # Mock create_user_plan to return a default plan
        mock_default_plan = UserPlan(
            user_id=user_id,
            plan=PlanType.START,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.create_user_plan', new_callable=AsyncMock) as mock_create:
            
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            mock_create.return_value = mock_default_plan
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.user_id == user_id
            assert result.plan == PlanType.START
            mock_create.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_plan_starter_plan_normalization(self):
        """Test getting user plan with 'starter' plan value - should normalize to 'start'"""
        user_id = "test_user_303"
        now = datetime.now()
        
        # Mock Supabase response with 'starter' plan (old data format)
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "starter",  # Old format
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "subscription_status": None,
            "plan_expires_at": None,
            "next_update_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }]
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin:
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.plan == PlanType.START  # Should be normalized to START
    
    @pytest.mark.asyncio
    async def test_get_user_plan_exception_handling(self):
        """Test getting user plan when exception occurs - should try to create default plan"""
        user_id = "test_user_404"
        
        # Mock create_user_plan to return a default plan
        mock_default_plan = UserPlan(
            user_id=user_id,
            plan=PlanType.START,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.create_user_plan', new_callable=AsyncMock) as mock_create:
            
            # Make get_supabase_admin raise an exception
            mock_get_admin.side_effect = Exception("Database connection failed")
            mock_create.return_value = mock_default_plan
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.user_id == user_id
            assert result.plan == PlanType.START
            mock_create.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_plan_exception_create_fails(self):
        """Test getting user plan when both query and create fail - should raise exception"""
        user_id = "test_user_505"
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.create_user_plan', new_callable=AsyncMock) as mock_create:
            
            # Make get_supabase_admin raise an exception
            mock_get_admin.side_effect = Exception("Database connection failed")
            # Make create_user_plan also fail
            mock_create.side_effect = Exception("Failed to create plan")
            
            with pytest.raises(Exception) as exc_info:
                await get_user_plan(user_id)
            
            assert "Failed to get or create user plan" in str(exc_info.value)
            mock_create.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_plan_expired_plan_with_timezone(self):
        """Test getting user plan with expired plan that has timezone info"""
        user_id = "test_user_606"
        now = datetime.now()
        expired_time = now - timedelta(days=1)
        
        # Mock Supabase response with expired plan (ISO format with Z)
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "ultra",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "subscription_status": "canceled",
            "plan_expires_at": expired_time.isoformat() + "Z",  # With timezone
            "next_update_at": None,
            "created_at": (now - timedelta(days=30)).isoformat(),
            "updated_at": (now - timedelta(days=1)).isoformat()
        }]
        
        # Mock update_user_plan to handle downgrade
        mock_updated_plan = UserPlan(
            user_id=user_id,
            plan=PlanType.START,
            plan_expires_at=None,
            created_at=now - timedelta(days=30),
            updated_at=now
        )
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.update_user_plan', new_callable=AsyncMock) as mock_update:
            
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            mock_update.return_value = mock_updated_plan
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.plan == PlanType.START
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_plan_start_plan_no_expiration_check(self):
        """Test getting START plan - should not check expiration (START plans don't expire)"""
        user_id = "test_user_707"
        now = datetime.now()
        
        # Mock Supabase response with START plan
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "start",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "subscription_status": None,
            "plan_expires_at": None,
            "next_update_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }]
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.update_user_plan', new_callable=AsyncMock) as mock_update:
            
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.plan == PlanType.START
            # START plans don't expire, so update_user_plan should not be called
            mock_update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_user_plan_missing_weekly_monthly_fields(self):
        """Test getting user plan with missing weekly_tokens_used and monthly_tokens_used fields"""
        user_id = "test_user_808"
        now = datetime.now()
        
        # Mock Supabase response without weekly/monthly fields (old data format)
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "subscription_status": None,
            "plan_expires_at": None,
            "next_update_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
            # Note: no weekly_tokens_used or monthly_tokens_used fields
        }]
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin:
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            
            mock_get_admin.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = mock_response
            
            result = await get_user_plan(user_id)
            
            assert isinstance(result, UserPlan)
            assert result.user_id == user_id
            assert result.plan == PlanType.NORMAL

