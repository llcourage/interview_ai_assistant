"""
Unit tests for payment_stripe module, focusing on downgrade_subscription function
"""
import unittest
import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta, timezone

# Mock external modules before importing payment_stripe
sys.modules['supabase'] = Mock()
sys.modules['supabase'].create_client = Mock()
sys.modules['supabase'].Client = Mock()

# Mock dotenv module
sys.modules['dotenv'] = Mock()
sys.modules['dotenv'].load_dotenv = Mock()

# Mock postgrest module
postgrest_mod = types.ModuleType("postgrest")
postgrest_exceptions_mod = types.ModuleType("postgrest.exceptions")

class APIError(Exception):
    pass

postgrest_exceptions_mod.APIError = APIError
sys.modules["postgrest"] = postgrest_mod
sys.modules["postgrest.exceptions"] = postgrest_exceptions_mod

# Mock backend.utils.time module
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

# Mock pydantic module
class MockBaseModel:
    def __init__(self, **kwargs):
        if 'plan' in kwargs and isinstance(kwargs['plan'], str):
            try:
                from backend.db_models import PlanType
                kwargs['plan'] = PlanType(kwargs['plan'])
            except (ValueError, ImportError):
                pass
        
        if 'next_plan' in kwargs and isinstance(kwargs['next_plan'], str) and kwargs['next_plan']:
            try:
                from backend.db_models import PlanType
                kwargs['next_plan'] = PlanType(kwargs['next_plan'])
            except (ValueError, ImportError):
                pass
        
        for key, value in kwargs.items():
            setattr(self, key, value)

sys.modules['pydantic'] = Mock()
sys.modules['pydantic'].BaseModel = MockBaseModel

# Mock print function
import builtins
builtins.print = Mock()

# Mock stripe module
stripe_mod = types.ModuleType("stripe")
stripe_error_mod = types.ModuleType("stripe.error")

class StripeError(Exception):
    pass

stripe_error_mod.StripeError = StripeError
stripe_mod.error = stripe_error_mod
stripe_mod.api_key = "test_key"
stripe_mod.Subscription = Mock()
stripe_mod.Customer = Mock()
stripe_mod.checkout = Mock()
sys.modules["stripe"] = stripe_mod
sys.modules["stripe.error"] = stripe_error_mod

from backend.payment_stripe import downgrade_subscription, cancel_subscription, _is_downgrade, PLAN_HIERARCHY
from backend.db_models import PlanType, UserPlan
from backend.db_operations import get_user_plan, update_user_plan, _CLEAR_FIELD


class TestIsDowngrade(unittest.TestCase):
    """Test cases for _is_downgrade helper function"""
    
    def __is_downgrade_start_to_normal__test(self):
        """Test that START to NORMAL is not a downgrade (it's an upgrade)"""
        self.assertFalse(_is_downgrade(PlanType.START, PlanType.NORMAL))
    
    def __is_downgrade_normal_to_start__test(self):
        """Test that NORMAL to START is a downgrade"""
        self.assertTrue(_is_downgrade(PlanType.NORMAL, PlanType.START))
    
    def __is_downgrade_high_to_normal__test(self):
        """Test that HIGH to NORMAL is a downgrade"""
        self.assertTrue(_is_downgrade(PlanType.HIGH, PlanType.NORMAL))
    
    def __is_downgrade_premium_to_ultra__test(self):
        """Test that PREMIUM to ULTRA is a downgrade"""
        self.assertTrue(_is_downgrade(PlanType.PREMIUM, PlanType.ULTRA))
    
    def __is_downgrade_same_plan__test(self):
        """Test that same plan is not a downgrade"""
        self.assertFalse(_is_downgrade(PlanType.NORMAL, PlanType.NORMAL))
    
    def __is_downgrade_upgrade__test(self):
        """Test that upgrade is not a downgrade"""
        self.assertFalse(_is_downgrade(PlanType.NORMAL, PlanType.HIGH))
    
    def __is_downgrade_internal_to_premium__test(self):
        """Test that INTERNAL to PREMIUM is a downgrade"""
        self.assertTrue(_is_downgrade(PlanType.INTERNAL, PlanType.PREMIUM))
    
    def __is_downgrade_unknown_plan__test(self):
        """Test that unknown plan defaults to 0 (lowest tier)"""
        # This tests the .get(plan, 0) fallback
        unknown_plan = Mock()
        unknown_plan.value = "unknown"
        # Unknown plan should be treated as tier 0, so START to unknown is not downgrade
        self.assertFalse(_is_downgrade(PlanType.START, unknown_plan))


class TestDowngradeSubscription(unittest.IsolatedAsyncioTestCase):
    """Test cases for downgrade_subscription function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "test_user_123"
        self.now = datetime.now(timezone.utc)
        self.future_time = self.now + timedelta(days=30)
        self.past_time = self.now - timedelta(days=1)
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_success_from_stripe__test(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test successful downgrade when getting period_end from Stripe"""
        # Setup: User has HIGH plan, active subscription, no plan_expires_at
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "active"
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock update_user_plan to return updated plan
        updated_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,  # Current plan doesn't change immediately
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.NORMAL,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_update_user_plan.return_value = updated_plan
        
        # Execute
        result = await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        # Assert
        self.assertTrue(result)
        mock_get_user_plan.assert_called_once_with(self.user_id)
        mock_stripe_retrieve.assert_called_once_with("sub_123")
        mock_update_user_plan.assert_called_once()
        
        # Verify update_user_plan was called with correct parameters
        call_args = mock_update_user_plan.call_args
        self.assertEqual(call_args[1]['user_id'], self.user_id)
        self.assertEqual(call_args[1]['next_plan'], PlanType.NORMAL)
        # Compare timestamps (ignore microsecond precision differences)
        actual_expires_at = call_args[1]['plan_expires_at']
        self.assertIsNotNone(actual_expires_at)
        self.assertAlmostEqual(
            actual_expires_at.timestamp(),
            self.future_time.timestamp(),
            delta=1.0  # Allow 1 second difference
        )
        self.assertFalse(call_args[1]['cancel_at_period_end'])
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_success_use_db_plan_expires_at__test(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test successful downgrade using existing plan_expires_at from DB"""
        # Setup: User has HIGH plan, active subscription, with future plan_expires_at
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,  # Already has plan_expires_at
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock update_user_plan
        updated_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.NORMAL,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_update_user_plan.return_value = updated_plan
        
        # Execute
        result = await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        # Assert
        self.assertTrue(result)
        mock_get_user_plan.assert_called_once_with(self.user_id)
        # Should NOT call Stripe since plan_expires_at exists in DB
        mock_stripe_retrieve.assert_not_called()
        mock_update_user_plan.assert_called_once()
    
    @patch('backend.payment_stripe.get_user_plan')
    async def __downgrade_fails_not_a_downgrade__test(self, mock_get_user_plan):
        """Test that downgrade fails if target plan is not lower than current plan"""
        # Setup: User has NORMAL plan, trying to downgrade to HIGH (upgrade)
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.NORMAL,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Execute & Assert
        with self.assertRaises(ValueError) as context:
            await downgrade_subscription(self.user_id, PlanType.HIGH)
        
        self.assertIn("not lower than current plan", str(context.exception))
    
    @patch('backend.payment_stripe.get_user_plan')
    async def __downgrade_fails_no_subscription__test(self, mock_get_user_plan):
        """Test that downgrade fails if user has no subscription"""
        # Setup: User has no stripe_subscription_id
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=None,  # No subscription
            subscription_status=None,
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Execute & Assert
        with self.assertRaises(ValueError) as context:
            await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        self.assertIn("no active subscription", str(context.exception))
    
    @patch('backend.payment_stripe.get_user_plan')
    async def __downgrade_fails_invalid_status__test(self, mock_get_user_plan):
        """Test that downgrade fails if subscription status is not active or trialing"""
        # Setup: User has canceled subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="canceled",  # Invalid status
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Execute & Assert
        with self.assertRaises(ValueError) as context:
            await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        self.assertIn("subscription status", str(context.exception))
        self.assertIn("must be one of", str(context.exception))
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_fails_stripe_invalid_status__test(self, mock_stripe_retrieve, mock_get_user_plan):
        """Test that downgrade fails if Stripe subscription status is invalid"""
        # Setup: User has HIGH plan, active in DB
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription with invalid status
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "canceled"  # Invalid in Stripe
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute & Assert
        with self.assertRaises(ValueError) as context:
            await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        self.assertIn("Stripe subscription status", str(context.exception))
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_fails_stripe_no_period_end__test(self, mock_stripe_retrieve, mock_get_user_plan):
        """Test that downgrade fails if Stripe subscription has no current_period_end"""
        # Setup
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription without current_period_end
        mock_subscription = Mock()
        mock_subscription.current_period_end = None
        mock_subscription.status = "active"
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute & Assert
        with self.assertRaises(ValueError) as context:
            await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        self.assertIn("no current_period_end", str(context.exception))
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_fails_stripe_error__test(self, mock_stripe_retrieve, mock_get_user_plan):
        """Test that downgrade fails gracefully when Stripe API call fails"""
        # Setup
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe error
        from backend.payment_stripe import stripe
        mock_stripe_retrieve.side_effect = stripe.error.StripeError("API Error")
        
        # Execute & Assert
        with self.assertRaises(ValueError) as context:
            await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        self.assertIn("Failed to get subscription period end date", str(context.exception))
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_idempotent_same_plan_same_time__test(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test that downgrade is idempotent when same downgrade is already scheduled"""
        # Setup: User already has next_plan set to target_plan with same plan_expires_at
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.NORMAL,  # Already scheduled
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription (will be used to get period_end for comparison)
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "active"
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute
        result = await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        # Assert: Should return True without calling update_user_plan
        self.assertTrue(result)
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_idempotent_same_plan_later_time__test(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test that downgrade is idempotent when same downgrade is scheduled for later time"""
        # Setup: User already has next_plan set to target_plan with later plan_expires_at
        later_time = self.future_time + timedelta(days=1)
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=later_time,  # Later than what Stripe will return
            next_plan=PlanType.NORMAL,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription (returns earlier time)
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "active"
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute
        result = await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        # Assert: Should return True without calling update_user_plan (existing is later)
        self.assertTrue(result)
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_overrides_different_next_plan__test(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test that downgrade overrides existing different next_plan"""
        # Setup: User has different next_plan scheduled
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.PREMIUM,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.HIGH,  # Different from target
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "active"
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock update_user_plan
        updated_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.PREMIUM,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.NORMAL,  # Overridden
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_update_user_plan.return_value = updated_plan
        
        # Execute: Downgrade to NORMAL (overriding existing HIGH downgrade)
        result = await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        # Assert: Should succeed and override
        self.assertTrue(result)
        mock_update_user_plan.assert_called_once()
        call_args = mock_update_user_plan.call_args
        self.assertEqual(call_args[1]['next_plan'], PlanType.NORMAL)
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_ignores_past_plan_expires_at__test(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test that past plan_expires_at is ignored and Stripe is called instead"""
        # Setup: User has past plan_expires_at
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.past_time,  # Past time, should be ignored
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "active"
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock update_user_plan
        updated_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.NORMAL,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_update_user_plan.return_value = updated_plan
        
        # Execute
        result = await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        # Assert: Should call Stripe since past plan_expires_at is ignored
        self.assertTrue(result)
        mock_stripe_retrieve.assert_called_once()
        mock_update_user_plan.assert_called_once()
        call_args = mock_update_user_plan.call_args
        # Compare timestamps (ignore microsecond precision differences)
        actual_expires_at = call_args[1]['plan_expires_at']
        self.assertIsNotNone(actual_expires_at)
        self.assertAlmostEqual(
            actual_expires_at.timestamp(),
            self.future_time.timestamp(),
            delta=1.0  # Allow 1 second difference
        )
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def __downgrade_with_trialing_status__test(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test that downgrade works with trialing subscription status"""
        # Setup: User has trialing subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="trialing",  # Trialing status
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "trialing"
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock update_user_plan
        updated_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="trialing",
            plan_expires_at=self.future_time,
            next_plan=PlanType.NORMAL,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_update_user_plan.return_value = updated_plan
        
        # Execute
        result = await downgrade_subscription(self.user_id, PlanType.NORMAL)
        
        # Assert: Should succeed with trialing status
        self.assertTrue(result)
        mock_update_user_plan.assert_called_once()


class TestCancelSubscription(unittest.IsolatedAsyncioTestCase):
    """Test cases for cancel_subscription function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "test_user_cancel"
        self.now = datetime.now(timezone.utc)
        self.future_time = self.now + timedelta(days=30)
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.stripe.Subscription.modify')
    async def test_cancel_subscription_success(self, mock_stripe_modify, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test successful subscription cancellation"""
        # Setup: User has HIGH plan with active subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=None,
            next_plan=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock update_user_plan to return updated plan
        updated_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,  # Current plan doesn't change immediately
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.START,
            cancel_at_period_end=True,
            next_update_at=None,  # Should be cleared
            created_at=self.now,
            updated_at=self.now
        )
        mock_update_user_plan.return_value = updated_plan
        
        # Execute
        result = await cancel_subscription(self.user_id)
        
        # Assert: Should succeed
        self.assertTrue(result)
        
        # Verify get_user_plan was called
        mock_get_user_plan.assert_called_once_with(self.user_id)
        
        # Verify Stripe subscription was retrieved
        mock_stripe_retrieve.assert_called_once_with("sub_123")
        
        # Verify update_user_plan was called with correct parameters
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['user_id'], self.user_id)
        self.assertEqual(call_kwargs['next_plan'], PlanType.START)
        self.assertEqual(call_kwargs['cancel_at_period_end'], True)
        self.assertEqual(call_kwargs['next_update_at'], _CLEAR_FIELD)  # Should use _CLEAR_FIELD
        # Verify plan_expires_at is set (should be UTC aware)
        self.assertIsNotNone(call_kwargs['plan_expires_at'])
        
        # Verify Stripe modify was called
        mock_stripe_modify.assert_called_once_with("sub_123", cancel_at_period_end=True)
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def test_cancel_subscription_no_subscription_id(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test cancellation fails when user has no subscription"""
        # Setup: User has no subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.START,
            stripe_subscription_id=None,  # No subscription
            subscription_status=None,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Execute
        result = await cancel_subscription(self.user_id)
        
        # Assert: Should fail
        self.assertFalse(result)
        
        # Verify update_user_plan was NOT called
        mock_update_user_plan.assert_not_called()
        mock_stripe_retrieve.assert_not_called()
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def test_cancel_subscription_no_period_end(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test cancellation fails when subscription has no current_period_end"""
        # Setup: User has subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription without current_period_end
        mock_subscription = Mock()
        mock_subscription.current_period_end = None  # Missing period end
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute
        result = await cancel_subscription(self.user_id)
        
        # Assert: Should fail
        self.assertFalse(result)
        
        # Verify update_user_plan was NOT called
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.stripe.Subscription.modify')
    async def test_cancel_subscription_overrides_existing_downgrade(self, mock_stripe_modify, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test that cancel_subscription overrides any existing scheduled downgrade"""
        # Setup: User has HIGH plan with scheduled downgrade to NORMAL
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.NORMAL,  # Existing scheduled downgrade
            next_update_at=self.future_time,  # Existing scheduled change time
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock update_user_plan
        updated_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            plan_expires_at=self.future_time,
            next_plan=PlanType.START,  # Should override NORMAL
            cancel_at_period_end=True,  # Should be set
            next_update_at=None,  # Should be cleared
            created_at=self.now,
            updated_at=self.now
        )
        mock_update_user_plan.return_value = updated_plan
        
        # Execute
        result = await cancel_subscription(self.user_id)
        
        # Assert: Should succeed
        self.assertTrue(result)
        
        # Verify update_user_plan was called with _CLEAR_FIELD to clear next_update_at
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['next_plan'], PlanType.START)  # Should override NORMAL
        self.assertEqual(call_kwargs['cancel_at_period_end'], True)
        self.assertEqual(call_kwargs['next_update_at'], _CLEAR_FIELD)  # Should clear existing next_update_at


if __name__ == '__main__':
    unittest.main()

