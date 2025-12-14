"""
Unit tests for get_user_plan function in db_operations module
"""
import unittest
import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta, timezone

# Mock external modules before importing db_operations
# This prevents ModuleNotFoundError when db_operations imports db_supabase
sys.modules['supabase'] = Mock()
sys.modules['supabase'].create_client = Mock()
sys.modules['supabase'].Client = Mock()

# Mock dotenv module
sys.modules['dotenv'] = Mock()
sys.modules['dotenv'].load_dotenv = Mock()

# Mock postgrest module (used in db_operations for exception handling)
# Use types.ModuleType to create real modules, not Mock objects
postgrest_mod = types.ModuleType("postgrest")
postgrest_exceptions_mod = types.ModuleType("postgrest.exceptions")

class APIError(Exception):
    pass

postgrest_exceptions_mod.APIError = APIError

sys.modules["postgrest"] = postgrest_mod
sys.modules["postgrest.exceptions"] = postgrest_exceptions_mod

# Mock backend.utils.time module (used in db_operations for UTC time handling)
# Only mock backend.utils.time, don't touch backend package itself
time_mod = types.ModuleType("backend.utils.time")

def mock_ensure_utc(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    else:
        return dt.astimezone(timezone.utc)

time_mod.utcnow = lambda: datetime.now(timezone.utc)
time_mod.ensure_utc = mock_ensure_utc

sys.modules["backend.utils.time"] = time_mod

# Mock pydantic module (used in db_models)
# Create a simple BaseModel mock class that handles PlanType conversion
class MockBaseModel:
    def __init__(self, **kwargs):
        # Convert plan string to PlanType enum if it exists
        # This handles the case where database returns plan as string (e.g., 'normal', 'start')
        if 'plan' in kwargs and isinstance(kwargs['plan'], str):
            try:
                # Import PlanType here to avoid circular imports
                # At this point, db_models should already be imported
                from backend.db_models import PlanType
                kwargs['plan'] = PlanType(kwargs['plan'])
            except (ValueError, ImportError):
                # If string doesn't match any PlanType or import fails, keep as is
                pass
        
        # Set all attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

sys.modules['pydantic'] = Mock()
sys.modules['pydantic'].BaseModel = MockBaseModel

# Mock print function to avoid Unicode encoding errors on Windows
# This prevents UnicodeEncodeError when db_operations tries to print emoji characters
import builtins
builtins.print = Mock()  # Mock print to do nothing, avoiding encoding issues

from backend.db_operations import get_user_plan, update_user_plan
from backend.db_models import UserPlan, PlanType


class TestGetUserPlan(unittest.IsolatedAsyncioTestCase):
    """Test cases for get_user_plan function"""
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.user_id, user_id)
            self.assertEqual(result.plan, PlanType.NORMAL)
            self.assertEqual(result.stripe_customer_id, "cus_123")
            self.assertEqual(result.stripe_subscription_id, "sub_123")
            self.assertEqual(result.subscription_status, "active")
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.user_id, user_id)
            self.assertEqual(result.plan, PlanType.START)
            mock_create.assert_called_once_with(user_id)
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.plan, PlanType.START)
            # Verify update_user_plan was called to downgrade
            mock_update.assert_called_once_with(
                user_id=user_id,
                plan=PlanType.START,
                plan_expires_at=None
            )
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.plan, PlanType.HIGH)
            # Verify update_user_plan was NOT called (plan not expired)
            mock_update.assert_not_called()
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.user_id, user_id)
            self.assertEqual(result.plan, PlanType.START)
            mock_create.assert_called_once_with(user_id)
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.plan, PlanType.START)  # Should be normalized to START
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.user_id, user_id)
            self.assertEqual(result.plan, PlanType.START)
            mock_create.assert_called_once_with(user_id)
    
    async def test_get_user_plan_exception_create_fails(self):
        """Test getting user plan when both query and create fail - should raise exception"""
        user_id = "test_user_505"
        
        with patch('backend.db_operations.get_supabase_admin') as mock_get_admin, \
             patch('backend.db_operations.create_user_plan', new_callable=AsyncMock) as mock_create:
            
            # Make get_supabase_admin raise an exception
            mock_get_admin.side_effect = Exception("Database connection failed")
            # Make create_user_plan also fail
            mock_create.side_effect = Exception("Failed to create plan")
            
            with self.assertRaises(Exception) as context:
                await get_user_plan(user_id)
            
            self.assertIn("Failed to get or create user plan", str(context.exception))
            mock_create.assert_called_once_with(user_id)
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.plan, PlanType.START)
            mock_update.assert_called_once()
    
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.plan, PlanType.START)
            # START plans don't expire, so update_user_plan should not be called
            mock_update.assert_not_called()
    
    async def test_get_user_plan_all_plan_types(self):
        """Test getting user plan for all plan types"""
        user_id = "test_user_plan_types"
        now = datetime.now()
        plan_types = [PlanType.START, PlanType.NORMAL, PlanType.HIGH, PlanType.ULTRA, PlanType.PREMIUM, PlanType.INTERNAL]
        
        for plan_type in plan_types:
            mock_response = MagicMock()
            mock_response.data = [{
                "user_id": f"{user_id}_{plan_type.value}",
                "plan": plan_type.value,
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
                
                result = await get_user_plan(f"{user_id}_{plan_type.value}")
                
                self.assertIsInstance(result, UserPlan)
                self.assertEqual(result.plan, plan_type)
    
    async def test_get_user_plan_expired_at_exactly_now(self):
        """Test getting user plan when plan_expires_at is exactly now - should downgrade"""
        user_id = "test_user_now"
        now = datetime.now()
        
        # Mock Supabase response with plan expiring exactly now
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "subscription_status": "canceled",
            "plan_expires_at": now.isoformat(),  # Expires exactly now
            "next_update_at": None,
            "created_at": (now - timedelta(days=30)).isoformat(),
            "updated_at": now.isoformat()
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.plan, PlanType.START)
            mock_update.assert_called_once()
    
    async def test_get_user_plan_with_new_fields(self):
        """Test getting user plan with new fields: stripe_event_ts, next_plan, updated_at"""
        user_id = "test_user_new_fields"
        now = datetime.now(timezone.utc)
        stripe_event_ts = int(now.timestamp())  # Unix timestamp
        
        # Mock Supabase response with new fields
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "high",
            "stripe_customer_id": "cus_123",
            "stripe_subscription_id": "sub_123",
            "subscription_status": "active",
            "plan_expires_at": None,
            "next_update_at": None,
            "next_plan": "normal",
            "cancel_at_period_end": False,
            "stripe_event_ts": stripe_event_ts,
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.user_id, user_id)
            self.assertEqual(result.plan, PlanType.HIGH)
            self.assertEqual(result.next_plan, PlanType.NORMAL)
            self.assertEqual(result.cancel_at_period_end, False)
            self.assertEqual(result.stripe_event_ts, stripe_event_ts)
            self.assertIsNotNone(result.updated_at)
    
    async def test_get_user_plan_with_null_new_fields(self):
        """Test getting user plan with null new fields"""
        user_id = "test_user_null_fields"
        now = datetime.now(timezone.utc)
        
        # Mock Supabase response with null new fields
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "normal",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "subscription_status": None,
            "plan_expires_at": None,
            "next_update_at": None,
            "next_plan": None,
            "cancel_at_period_end": None,
            "stripe_event_ts": None,
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.user_id, user_id)
            self.assertIsNone(result.next_plan)
            self.assertIsNone(result.stripe_event_ts)
            self.assertIsNotNone(result.updated_at)
    
    async def test_update_user_plan_with_stripe_event_ts(self):
        """Test updating user plan with stripe_event_ts field"""
        user_id = "test_user_stripe_ts"
        now = datetime.now(timezone.utc)
        stripe_event_ts = int(now.timestamp())
        
        # Mock existing plan
        mock_existing_response = MagicMock()
        mock_existing_response.data = {
            "plan": "normal"
        }
        
        # Mock upsert response
        mock_upsert_response = MagicMock()
        mock_upsert_response.data = [{
            "user_id": user_id,
            "plan": "normal",
            "stripe_event_ts": stripe_event_ts,
            "updated_at": now.isoformat(),
            "created_at": now.isoformat()
        }]
        
        with patch('backend.db_operations.get_supabase') as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            mock_maybe_single = MagicMock()
            mock_upsert = MagicMock()
            
            mock_get_supabase.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            
            # Mock the select chain for checking existing plan
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.maybe_single.return_value = mock_maybe_single
            mock_maybe_single.execute.return_value = mock_existing_response
            
            # Mock the upsert chain
            mock_table.upsert.return_value = mock_upsert
            mock_upsert.execute.return_value = mock_upsert_response
            
            result = await update_user_plan(
                user_id=user_id,
                stripe_event_ts=stripe_event_ts
            )
            
            self.assertIsInstance(result, UserPlan)
            # Verify upsert was called with stripe_event_ts
            self.assertTrue(mock_table.upsert.called)
            upsert_call_args = mock_table.upsert.call_args[0][0]
            self.assertIn("stripe_event_ts", upsert_call_args)
            self.assertEqual(upsert_call_args["stripe_event_ts"], stripe_event_ts)
            self.assertIn("updated_at", upsert_call_args)
    
    async def test_update_user_plan_with_next_plan(self):
        """Test updating user plan with next_plan field"""
        user_id = "test_user_next_plan"
        now = datetime.now(timezone.utc)
        
        # Mock existing plan
        mock_existing_response = MagicMock()
        mock_existing_response.data = {
            "plan": "high"
        }
        
        # Mock upsert response
        mock_upsert_response = MagicMock()
        mock_upsert_response.data = [{
            "user_id": user_id,
            "plan": "high",
            "next_plan": "normal",
            "updated_at": now.isoformat(),
            "created_at": now.isoformat()
        }]
        
        with patch('backend.db_operations.get_supabase') as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            mock_maybe_single = MagicMock()
            mock_upsert = MagicMock()
            
            mock_get_supabase.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            
            # Mock the select chain for checking existing plan
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.maybe_single.return_value = mock_maybe_single
            mock_maybe_single.execute.return_value = mock_existing_response
            
            # Mock the upsert chain
            mock_table.upsert.return_value = mock_upsert
            mock_upsert.execute.return_value = mock_upsert_response
            
            result = await update_user_plan(
                user_id=user_id,
                next_plan=PlanType.NORMAL
            )
            
            self.assertIsInstance(result, UserPlan)
            # Verify upsert was called with next_plan
            self.assertTrue(mock_table.upsert.called)
            upsert_call_args = mock_table.upsert.call_args[0][0]
            self.assertIn("next_plan", upsert_call_args)
            self.assertEqual(upsert_call_args["next_plan"], "normal")
            self.assertIn("updated_at", upsert_call_args)
    
    async def test_update_user_plan_with_cancel_at_period_end(self):
        """Test updating user plan with cancel_at_period_end field"""
        user_id = "test_user_cancel"
        now = datetime.now(timezone.utc)
        
        # Mock existing plan
        mock_existing_response = MagicMock()
        mock_existing_response.data = {
            "plan": "high"
        }
        
        # Mock upsert response
        mock_upsert_response = MagicMock()
        mock_upsert_response.data = [{
            "user_id": user_id,
            "plan": "high",
            "cancel_at_period_end": True,
            "updated_at": now.isoformat(),
            "created_at": now.isoformat()
        }]
        
        with patch('backend.db_operations.get_supabase') as mock_get_supabase:
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            mock_maybe_single = MagicMock()
            mock_upsert = MagicMock()
            
            mock_get_supabase.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            
            # Mock the select chain for checking existing plan
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.maybe_single.return_value = mock_maybe_single
            mock_maybe_single.execute.return_value = mock_existing_response
            
            # Mock the upsert chain
            mock_table.upsert.return_value = mock_upsert
            mock_upsert.execute.return_value = mock_upsert_response
            
            result = await update_user_plan(
                user_id=user_id,
                cancel_at_period_end=True
            )
            
            self.assertIsInstance(result, UserPlan)
            # Verify upsert was called with cancel_at_period_end
            self.assertTrue(mock_table.upsert.called)
            upsert_call_args = mock_table.upsert.call_args[0][0]
            self.assertIn("cancel_at_period_end", upsert_call_args)
            self.assertEqual(upsert_call_args["cancel_at_period_end"], True)
            self.assertIn("updated_at", upsert_call_args)
    
    async def test_update_user_plan_updated_at_auto_update(self):
        """Test that updated_at is automatically updated when calling update_user_plan"""
        user_id = "test_user_updated_at"
        now = datetime.now(timezone.utc)
        
        # Mock existing plan
        mock_existing_response = MagicMock()
        mock_existing_response.data = {
            "plan": "normal"
        }
        
        # Mock upsert response
        mock_upsert_response = MagicMock()
        mock_upsert_response.data = [{
            "user_id": user_id,
            "plan": "normal",
            "updated_at": now.isoformat(),
            "created_at": (now - timedelta(days=1)).isoformat()
        }]
        
        with patch('backend.db_operations.get_supabase') as mock_get_supabase, \
             patch('backend.db_operations.utcnow') as mock_utcnow:
            
            mock_utcnow.return_value = now
            
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()
            mock_maybe_single = MagicMock()
            mock_upsert = MagicMock()
            
            mock_get_supabase.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            
            # Mock the select chain for checking existing plan
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.maybe_single.return_value = mock_maybe_single
            mock_maybe_single.execute.return_value = mock_existing_response
            
            # Mock the upsert chain
            mock_table.upsert.return_value = mock_upsert
            mock_upsert.execute.return_value = mock_upsert_response
            
            result = await update_user_plan(
                user_id=user_id,
                subscription_status="active"
            )
            
            self.assertIsInstance(result, UserPlan)
            # Verify upsert was called with updated_at
            self.assertTrue(mock_table.upsert.called)
            upsert_call_args = mock_table.upsert.call_args[0][0]
            self.assertIn("updated_at", upsert_call_args)
            self.assertEqual(upsert_call_args["updated_at"], now.isoformat())
    
    async def test_get_user_plan_with_downgrade_scenario(self):
        """Test getting user plan with downgrade scenario: plan=high, next_plan=normal"""
        user_id = "test_user_downgrade"
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(days=30)
        
        # Mock Supabase response with downgrade scenario
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "high",
            "stripe_customer_id": "cus_123",
            "stripe_subscription_id": "sub_123",
            "subscription_status": "active",
            "plan_expires_at": future_time.isoformat(),
            "next_update_at": future_time.isoformat(),
            "next_plan": "normal",
            "cancel_at_period_end": False,
            "stripe_event_ts": int(now.timestamp()),
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.plan, PlanType.HIGH)
            self.assertEqual(result.next_plan, PlanType.NORMAL)
            self.assertEqual(result.cancel_at_period_end, False)
            self.assertIsNotNone(result.stripe_event_ts)
    
    async def test_get_user_plan_with_cancel_scenario(self):
        """Test getting user plan with cancel scenario: plan=high, next_plan=start, cancel_at_period_end=True"""
        user_id = "test_user_cancel"
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(days=30)
        
        # Mock Supabase response with cancel scenario
        mock_response = MagicMock()
        mock_response.data = [{
            "user_id": user_id,
            "plan": "high",
            "stripe_customer_id": "cus_123",
            "stripe_subscription_id": "sub_123",
            "subscription_status": "canceled",
            "plan_expires_at": future_time.isoformat(),
            "next_update_at": future_time.isoformat(),
            "next_plan": "start",
            "cancel_at_period_end": True,
            "stripe_event_ts": int(now.timestamp()),
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
            
            self.assertIsInstance(result, UserPlan)
            self.assertEqual(result.plan, PlanType.HIGH)
            self.assertEqual(result.next_plan, PlanType.START)
            self.assertEqual(result.cancel_at_period_end, True)
            self.assertIsNotNone(result.stripe_event_ts)


if __name__ == '__main__':
    unittest.main()
