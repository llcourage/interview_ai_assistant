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

from backend.payment_stripe import downgrade_subscription, cancel_subscription, _is_downgrade, PLAN_HIERARCHY, handle_checkout_completed, _extract_price_id_from_pending_update, handle_subscription_updated, handle_subscription_deleted, handle_subscription_pending_update_applied, get_subscription_info
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


class TestHandleCheckoutCompleted(unittest.IsolatedAsyncioTestCase):
    """Test cases for handle_checkout_completed function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "test_user_123"
        self.now = datetime.now(timezone.utc)
        self.future_time = self.now + timedelta(days=30)
        self.past_time = self.now - timedelta(days=1)
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_checkout_completed_rejects_downgrade(self, mock_update_user_plan, mock_get_user_plan):
        """Test that checkout downgrade is rejected"""
        # Setup: User has HIGH plan, trying to checkout NORMAL (downgrade)
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock checkout session with downgrade
        session = {
            "id": "cs_test_123",
            "metadata": {
                "user_id": self.user_id,
                "plan": "normal"  # Downgrade from HIGH
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        
        # Execute
        await handle_checkout_completed(session)
        
        # Assert: update_user_plan should NOT be called (rejected)
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_checkout_completed_rejects_start_plan(self, mock_update_user_plan, mock_get_user_plan):
        """Test that checkout START plan is rejected"""
        # Setup: User has HIGH plan, trying to checkout START
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock checkout session with START plan
        session = {
            "id": "cs_test_123",
            "metadata": {
                "user_id": self.user_id,
                "plan": "start"
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        
        # Execute
        await handle_checkout_completed(session)
        
        # Assert: update_user_plan should NOT be called (rejected)
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_checkout_completed_rejects_invalid_plan(self, mock_update_user_plan, mock_get_user_plan):
        """Test that invalid plan value in metadata is rejected"""
        # Setup: User has HIGH plan
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock checkout session with invalid plan
        session = {
            "id": "cs_test_123",
            "metadata": {
                "user_id": self.user_id,
                "plan": "invalid_plan"  # Invalid plan value
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        
        # Execute
        await handle_checkout_completed(session)
        
        # Assert: update_user_plan should NOT be called (rejected)
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def test_handle_checkout_completed_upgrade_no_pending_update(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test successful upgrade when no pending_update exists"""
        # Setup: User has NORMAL plan, upgrading to HIGH
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.NORMAL,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription (no pending_update)
        mock_subscription = Mock()
        mock_subscription.status = "active"
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.pending_update = None  # No pending_update
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock checkout session
        session = {
            "id": "cs_test_123",
            "metadata": {
                "user_id": self.user_id,
                "plan": "high"  # Upgrade from NORMAL
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        
        # Execute
        await handle_checkout_completed(session)
        
        # Assert: update_user_plan should be called with immediate upgrade
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.HIGH)
        self.assertEqual(call_kwargs['next_plan'], _CLEAR_FIELD)  # Should clear scheduled changes
        self.assertEqual(call_kwargs['plan_expires_at'], _CLEAR_FIELD)
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def test_handle_checkout_completed_upgrade_with_relevant_pending_update(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test upgrade when pending_update exists and is relevant (same price_id)"""
        # Setup: User has NORMAL plan, upgrading to HIGH
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.NORMAL,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock pending_update with same price_id (relevant)
        mock_pending_update = Mock()
        mock_pending_update.effective_at = int((self.now + timedelta(days=7)).timestamp())
        mock_pending_item = Mock()
        mock_pending_item.price = Mock()
        mock_pending_item.price.id = "price_yyy"  # HIGH plan price_id (assuming from STRIPE_PRICE_IDS)
        mock_pending_update.items = [mock_pending_item]
        
        # Mock Stripe subscription with relevant pending_update
        mock_subscription = Mock()
        mock_subscription.status = "active"
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.pending_update = mock_pending_update
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock checkout session
        session = {
            "id": "cs_test_123",
            "metadata": {
                "user_id": self.user_id,
                "plan": "high"  # Upgrade from NORMAL
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        
        # Mock STRIPE_PRICE_IDS to return HIGH price_id
        with patch('backend.payment_stripe.STRIPE_PRICE_IDS', {PlanType.HIGH: "price_yyy"}):
            # Execute
            await handle_checkout_completed(session)
        
        # Assert: update_user_plan should be called with scheduled upgrade (next_plan)
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertIsNone(call_kwargs.get('plan'))  # plan should not be updated immediately
        self.assertEqual(call_kwargs['next_plan'], PlanType.HIGH)  # Should schedule upgrade
        self.assertIsNotNone(call_kwargs.get('next_update_at'))  # Should have effective_at
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def test_handle_checkout_completed_upgrade_with_irrelevant_pending_update(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test upgrade when pending_update exists but is irrelevant (different price_id)"""
        # Setup: User has NORMAL plan, upgrading to HIGH
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.NORMAL,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock pending_update with different price_id (irrelevant)
        mock_pending_update = Mock()
        mock_pending_update.effective_at = int((self.now + timedelta(days=7)).timestamp())
        mock_pending_item = Mock()
        mock_pending_item.price = Mock()
        mock_pending_item.price.id = "price_xxx"  # Different price_id (not HIGH)
        mock_pending_update.items = [mock_pending_item]
        
        # Mock Stripe subscription with irrelevant pending_update
        mock_subscription = Mock()
        mock_subscription.status = "active"
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.pending_update = mock_pending_update
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock checkout session
        session = {
            "id": "cs_test_123",
            "metadata": {
                "user_id": self.user_id,
                "plan": "high"  # Upgrade from NORMAL
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        
        # Mock STRIPE_PRICE_IDS to return HIGH price_id
        with patch('backend.payment_stripe.STRIPE_PRICE_IDS', {PlanType.HIGH: "price_yyy"}):
            # Execute
            await handle_checkout_completed(session)
        
        # Assert: update_user_plan should be called with immediate upgrade (pending_update ignored)
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.HIGH)  # Should upgrade immediately
        self.assertEqual(call_kwargs['next_plan'], _CLEAR_FIELD)  # Should clear scheduled changes
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_checkout_completed_new_subscription(self, mock_update_user_plan, mock_get_user_plan):
        """Test new subscription (user has START plan, subscribing to HIGH)"""
        # Setup: User has START plan (new user)
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.START,
            stripe_subscription_id=None,  # No existing subscription
            subscription_status=None,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock checkout session (new subscription, no subscription_id yet)
        session = {
            "id": "cs_test_123",
            "metadata": {
                "user_id": self.user_id,
                "plan": "high"
            },
            "subscription": None,  # New subscription
            "customer": "cus_123"
        }
        
        # Execute
        await handle_checkout_completed(session)
        
        # Assert: update_user_plan should be called with immediate upgrade
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.HIGH)
        self.assertEqual(call_kwargs['next_plan'], _CLEAR_FIELD)
    
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    async def test_handle_checkout_completed_retrieve_failed(self, mock_stripe_retrieve, mock_update_user_plan, mock_get_user_plan):
        """Test behavior when Stripe subscription retrieve fails"""
        # Setup: User has NORMAL plan, upgrading to HIGH
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.NORMAL,
            stripe_subscription_id="sub_123",
            subscription_status="active",
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe retrieve to fail
        mock_stripe_retrieve.side_effect = Exception("Stripe API error")
        
        # Mock checkout session
        session = {
            "id": "cs_test_123",
            "metadata": {
                "user_id": self.user_id,
                "plan": "high"
            },
            "subscription": "sub_123",
            "customer": "cus_123"
        }
        
        # Execute
        await handle_checkout_completed(session)
        
        # Assert: update_user_plan should be called with immediate upgrade (checkout completed)
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.HIGH)
        # When Stripe retrieve fails, next_update_at should be set to a default value (30 days from now)
        self.assertIn('next_update_at', call_kwargs, 
            "next_update_at should be set to default value when Stripe retrieve fails")
        self.assertIsNotNone(call_kwargs['next_update_at'])


class TestExtractPriceIdFromPendingUpdate(unittest.TestCase):
    """Test cases for _extract_price_id_from_pending_update helper function"""
    
    def test_extract_price_id_from_dict_structure(self):
        """Test extracting price_id from dict structure"""
        # Mock pending_update with dict items structure
        mock_pending_update = Mock()
        mock_pending_update.items = {
            "data": [
                {
                    "price": {
                        "id": "price_test_123"
                    }
                }
            ]
        }
        
        result = _extract_price_id_from_pending_update(mock_pending_update)
        self.assertEqual(result, "price_test_123")
    
    def test_extract_price_id_from_list_structure(self):
        """Test extracting price_id from list structure"""
        # Mock pending_update with list items structure
        mock_pending_update = Mock()
        mock_item = Mock()
        mock_item.price = Mock()
        mock_item.price.id = "price_test_456"
        mock_pending_update.items = [mock_item]
        
        result = _extract_price_id_from_pending_update(mock_pending_update)
        self.assertEqual(result, "price_test_456")
    
    def test_extract_price_id_from_items_data_attribute(self):
        """Test extracting price_id from items.data attribute"""
        # Mock pending_update with items.data structure
        mock_pending_update = Mock()
        mock_item = Mock()
        mock_item.price = Mock()
        mock_item.price.id = "price_test_789"
        mock_items = Mock()
        mock_items.data = [mock_item]
        mock_pending_update.items = mock_items
        
        result = _extract_price_id_from_pending_update(mock_pending_update)
        self.assertEqual(result, "price_test_789")
    
    def test_extract_price_id_returns_none_when_not_found(self):
        """Test that None is returned when price_id cannot be extracted"""
        # Mock pending_update without items
        mock_pending_update = Mock()
        mock_pending_update.items = None
        
        result = _extract_price_id_from_pending_update(mock_pending_update)
        self.assertIsNone(result)
    
    def test_extract_price_id_handles_exception(self):
        """Test that exceptions are handled gracefully"""
        # Mock pending_update that raises exception
        mock_pending_update = Mock()
        mock_pending_update.items = Mock()
        mock_pending_update.items.__getattribute__ = Mock(side_effect=Exception("Test error"))
        
        result = _extract_price_id_from_pending_update(mock_pending_update)
        self.assertIsNone(result)


class TestHandleSubscriptionUpdated(unittest.IsolatedAsyncioTestCase):
    """Test cases for handle_subscription_updated function"""
    
    def setUp(self):
        self.user_id = "test_user_123"
        self.customer_id = "cus_test_123"
        self.subscription_id = "sub_test_123"
        self.now = datetime.now(timezone.utc)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_updated_missing_status(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that missing status is handled gracefully"""
        # Setup: Mock Supabase response
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription without status
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id
        }
        
        # Execute - should return early without error
        await handle_subscription_updated(subscription, event_created=1234567890, event_id="evt_test")
        
        # Assert: update_user_plan should not be called
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_updated_customer_as_dict(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that customer can be a dict or string"""
        # Setup: Mock Supabase response
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "stripe_event_ts": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription with customer as dict
        subscription = {
            "id": self.subscription_id,
            "customer": {"id": self.customer_id},
            "status": "active",
            "cancel_at_period_end": False,
            "current_period_end": int(self.now.timestamp()) + 86400
        }
        
        # Execute
        await handle_subscription_updated(subscription, event_created=1234567890, event_id="evt_test")
        
        # Assert: update_user_plan should be called
        mock_update_user_plan.assert_called_once()
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_updated_event_created_none(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that event_created=None skips critical fields"""
        # Setup: Mock Supabase response
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "stripe_event_ts": None,
            "next_plan": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False,
            "current_period_end": int(self.now.timestamp()) + 86400
        }
        
        # Execute with event_created=None
        await handle_subscription_updated(subscription, event_created=None, event_id="evt_test")
        
        # Assert: update_user_plan should be called but without stripe_subscription_id and next_update_at
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertNotIn('stripe_subscription_id', call_kwargs)
        self.assertNotIn('next_update_at', call_kwargs)
        self.assertNotIn('stripe_event_ts', call_kwargs)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_updated_past_due_expired_uses_clear_field(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that expired plan_expires_at uses _CLEAR_FIELD"""
        # Setup: Mock Supabase response with expired plan_expires_at
        expired_time = self.now - timedelta(days=1)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "stripe_event_ts": None,
            "next_plan": None,
            "plan_expires_at": expired_time.isoformat()
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription with past_due status
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "past_due",
            "cancel_at_period_end": False
        }
        
        # Execute
        await handle_subscription_updated(subscription, event_created=1234567890, event_id="evt_test")
        
        # Assert: update_user_plan should be called with _CLEAR_FIELD for plan_expires_at
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.START)
        self.assertEqual(call_kwargs['plan_expires_at'], _CLEAR_FIELD)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_updated_deduplication(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that old events are ignored based on stripe_event_ts"""
        # Setup: Mock Supabase response with newer event_ts
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "stripe_event_ts": 1234567900  # Newer than event_created
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False
        }
        
        # Execute with older event_created
        await handle_subscription_updated(subscription, event_created=1234567890, event_id="evt_test")
        
        # Assert: update_user_plan should not be called (event ignored)
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_updated_event_created_zero(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that event_created=0 is handled correctly (not treated as None)"""
        # Setup: Mock Supabase response
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "stripe_event_ts": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False
        }
        
        # Execute with event_created=0 (should not be treated as None)
        await handle_subscription_updated(subscription, event_created=0, event_id="evt_test")
        
        # Assert: update_user_plan should be called with event_created=0
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs.get('stripe_event_ts'), 0)


class TestHandleSubscriptionDeleted(unittest.IsolatedAsyncioTestCase):
    """Test cases for handle_subscription_deleted function"""
    
    def setUp(self):
        self.user_id = "test_user_123"
        self.customer_id = "cus_test_123"
        self.now = datetime.now(timezone.utc)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_deleted_customer_as_dict(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that customer can be a dict or string"""
        # Setup: Mock Supabase response
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "plan_expires_at": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription with customer as dict
        subscription = {
            "id": "sub_test_123",
            "customer": {"id": self.customer_id}
        }
        
        # Execute
        await handle_subscription_deleted(subscription)
        
        # Assert: update_user_plan should be called with all fields cleared
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.START)
        self.assertEqual(call_kwargs['next_plan'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['next_update_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['plan_expires_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['cancel_at_period_end'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['stripe_subscription_id'], _CLEAR_FIELD)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_deleted_missing_customer_id(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that missing customer_id is handled gracefully"""
        # Setup: Mock Supabase response
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription without customer
        subscription = {
            "id": "sub_test_123"
        }
        
        # Execute - should return early without error
        await handle_subscription_deleted(subscription)
        
        # Assert: update_user_plan should not be called
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_deleted_plan_expires_at_string(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that plan_expires_at as string is parsed correctly"""
        # Setup: Mock Supabase response with plan_expires_at as string
        expired_time = self.now - timedelta(days=1)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "plan_expires_at": expired_time.isoformat()  # String format
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": "sub_test_123",
            "customer": self.customer_id
        }
        
        # Execute
        await handle_subscription_deleted(subscription)
        
        # Assert: update_user_plan should be called with all fields cleared
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.START)
        self.assertEqual(call_kwargs['next_plan'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['next_update_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['plan_expires_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['cancel_at_period_end'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['stripe_subscription_id'], _CLEAR_FIELD)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_deleted_plan_not_expired(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that plan is kept if not expired"""
        # Setup: Mock Supabase response with future plan_expires_at
        future_time = self.now + timedelta(days=1)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "plan_expires_at": future_time.isoformat()
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": "sub_test_123",
            "customer": self.customer_id
        }
        
        # Execute
        await handle_subscription_deleted(subscription)
        
        # Assert: update_user_plan should be called but only with subscription_status
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['subscription_status'], "canceled")
        self.assertNotIn('plan', call_kwargs)
        self.assertNotIn('plan_expires_at', call_kwargs)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_deleted_clears_all_schedule_fields(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that all schedule and cancel fields are cleared when subscription is deleted"""
        # Setup: Mock Supabase response with all schedule fields set
        expired_time = self.now - timedelta(days=1)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "next_plan": "ultra",  # Has next_plan (should be cleared, not applied)
            "next_update_at": (self.now + timedelta(days=1)).isoformat(),
            "plan_expires_at": expired_time.isoformat(),
            "cancel_at_period_end": True,
            "stripe_subscription_id": "sub_old_123"
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": "sub_test_123",
            "customer": self.customer_id
        }
        
        # Execute
        await handle_subscription_deleted(subscription)
        
        # Assert: All fields should be cleared, and plan should be START (not next_plan)
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.START)  # Should be START, not next_plan (ultra)
        self.assertEqual(call_kwargs['next_plan'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['next_update_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['plan_expires_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['cancel_at_period_end'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['stripe_subscription_id'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['subscription_status'], "canceled")
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_deleted_does_not_apply_next_plan(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that next_plan is cleared but not applied (even if it's an upgrade)"""
        # Setup: Mock Supabase response with next_plan set to upgrade
        expired_time = self.now - timedelta(days=1)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "normal",
            "next_plan": "high",  # Upgrade scheduled (should NOT be applied on deletion)
            "plan_expires_at": expired_time.isoformat()
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": "sub_test_123",
            "customer": self.customer_id
        }
        
        # Execute
        await handle_subscription_deleted(subscription)
        
        # Assert: Plan should be START (not high), and next_plan should be cleared
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.START)  # Should be START, not high
        self.assertEqual(call_kwargs['next_plan'], _CLEAR_FIELD)  # Should be cleared, not applied
        self.assertEqual(call_kwargs['next_update_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['plan_expires_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['cancel_at_period_end'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['stripe_subscription_id'], _CLEAR_FIELD)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_deleted_clears_next_update_at(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that next_update_at is cleared to avoid stale timestamps"""
        # Setup: Mock Supabase response with next_update_at set
        expired_time = self.now - timedelta(days=1)
        future_time = self.now + timedelta(days=30)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "next_update_at": future_time.isoformat(),  # Future timestamp (should be cleared)
            "plan_expires_at": expired_time.isoformat()
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": "sub_test_123",
            "customer": self.customer_id
        }
        
        # Execute
        await handle_subscription_deleted(subscription)
        
        # Assert: next_update_at should be cleared
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['next_update_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['plan'], PlanType.START)


class TestHandleSubscriptionPendingUpdateApplied(unittest.IsolatedAsyncioTestCase):
    """Test cases for handle_subscription_pending_update_applied function"""
    
    def setUp(self):
        self.user_id = "test_user_123"
        self.customer_id = "cus_test_123"
        self.subscription_id = "sub_test_123"
        self.now = datetime.now(timezone.utc)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_success(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test successful application of pending_update (upgrade)"""
        # Setup: Mock Supabase response with next_plan scheduled
        future_time = self.now + timedelta(days=1)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "normal",
            "next_plan": "high",
            "stripe_event_ts": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription with pending_update applied
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False,
            "current_period_end": int(future_time.timestamp())
        }
        
        # Execute
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=1234567890,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should be called with plan upgrade and cleared schedule
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['user_id'], self.user_id)
        self.assertEqual(call_kwargs['plan'], PlanType.HIGH)
        self.assertEqual(call_kwargs['next_plan'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['plan_expires_at'], _CLEAR_FIELD)
        self.assertEqual(call_kwargs['subscription_status'], "active")
        self.assertEqual(call_kwargs['stripe_subscription_id'], self.subscription_id)
        self.assertEqual(call_kwargs['stripe_event_ts'], 1234567890)
        self.assertIn('next_update_at', call_kwargs)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_no_next_plan(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that if no next_plan exists, only status is synced"""
        # Setup: Mock Supabase response without next_plan
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "next_plan": None,
            "stripe_event_ts": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False
        }
        
        # Execute
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=1234567890,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should be called but only with status fields
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['subscription_status'], "active")
        self.assertNotIn('plan', call_kwargs)
        self.assertNotIn('next_plan', call_kwargs)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_not_upgrade(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that downgrades are not applied (only status synced)"""
        # Setup: Mock Supabase response with next_plan that is a downgrade
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "next_plan": "normal",  # Downgrade, not upgrade
            "stripe_event_ts": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False
        }
        
        # Execute
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=1234567890,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should be called but only with status fields (not plan change)
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['subscription_status'], "active")
        self.assertNotIn('plan', call_kwargs)
        self.assertNotIn('next_plan', call_kwargs)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_customer_as_dict(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that customer can be a dict or string"""
        # Setup: Mock Supabase response
        future_time = self.now + timedelta(days=1)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "normal",
            "next_plan": "high",
            "stripe_event_ts": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription with customer as dict
        subscription = {
            "id": self.subscription_id,
            "customer": {"id": self.customer_id},
            "status": "active",
            "cancel_at_period_end": False,
            "current_period_end": int(future_time.timestamp())
        }
        
        # Execute
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=1234567890,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should be called
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.HIGH)
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_missing_customer_id(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that missing customer_id is handled gracefully"""
        # Setup: Mock Supabase response
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription without customer
        subscription = {
            "id": self.subscription_id
        }
        
        # Execute - should return early without error
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=1234567890,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should not be called
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_deduplication(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that old events are ignored based on stripe_event_ts"""
        # Setup: Mock Supabase response with newer event_ts
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "normal",
            "next_plan": "high",
            "stripe_event_ts": 1234567900  # Newer than event_created
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False
        }
        
        # Execute with older event_created
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=1234567890,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should not be called (event ignored)
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_user_not_found(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that missing user is handled gracefully"""
        # Setup: Mock Supabase response with no user
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False
        }
        
        # Execute - should return early without error
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=1234567890,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should not be called
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_invalid_next_plan(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that invalid next_plan is handled gracefully"""
        # Setup: Mock Supabase response with invalid next_plan
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "normal",
            "next_plan": "invalid_plan",  # Invalid plan value
            "stripe_event_ts": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False
        }
        
        # Execute - should return early without error
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=1234567890,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should not be called
        mock_update_user_plan.assert_not_called()
    
    @patch('backend.db_supabase.get_supabase_admin')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_handle_subscription_pending_update_applied_event_created_none(self, mock_update_user_plan, mock_get_supabase_admin):
        """Test that event_created=None still works (no dedup but still processes)"""
        # Setup: Mock Supabase response
        future_time = self.now + timedelta(days=1)
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "user_id": self.user_id,
            "plan": "normal",
            "next_plan": "high",
            "stripe_event_ts": None
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Subscription
        subscription = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "cancel_at_period_end": False,
            "current_period_end": int(future_time.timestamp())
        }
        
        # Execute with event_created=None
        await handle_subscription_pending_update_applied(
            subscription,
            event_created=None,
            event_id="evt_test_123"
        )
        
        # Assert: update_user_plan should be called but without stripe_event_ts
        mock_update_user_plan.assert_called_once()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(call_kwargs['plan'], PlanType.HIGH)
        self.assertNotIn('stripe_event_ts', call_kwargs)


class TestGetSubscriptionInfo(unittest.IsolatedAsyncioTestCase):
    """Test cases for get_subscription_info function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "test_user_123"
        self.subscription_id = "sub_123"
        self.now = datetime.now(timezone.utc)
        self.future_time = self.now + timedelta(days=30)
    
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    async def test_get_subscription_info_success_with_cancel_false(self, mock_get_user_plan, mock_stripe_retrieve):
        """Test successful retrieval with cancel_at_period_end=False from DB"""
        # Setup: User has subscription with cancel_at_period_end=False
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=False,  # From DB
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.id = self.subscription_id
        mock_subscription.status = "active"
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute
        result = await get_subscription_info(self.user_id)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result["subscription_id"], self.subscription_id)
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["cancel_at_period_end"], False)  # From DB, not Stripe
        self.assertIsNotNone(result["current_period_end"])
        self.assertAlmostEqual(result["current_period_end"].timestamp(), self.future_time.timestamp(), delta=1.0)
        
        # Verify Stripe was called
        mock_stripe_retrieve.assert_called_once_with(self.subscription_id)
    
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    async def test_get_subscription_info_success_with_cancel_true(self, mock_get_user_plan, mock_stripe_retrieve):
        """Test successful retrieval with cancel_at_period_end=True from DB"""
        # Setup: User has subscription with cancel_at_period_end=True
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=True,  # From DB
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription (cancel_at_period_end might be different, but we use DB)
        mock_subscription = Mock()
        mock_subscription.id = self.subscription_id
        mock_subscription.status = "active"
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.cancel_at_period_end = False  # Different from DB, but we ignore it
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute
        result = await get_subscription_info(self.user_id)
        
        # Assert: Should use DB value (True), not Stripe value (False)
        self.assertIsNotNone(result)
        self.assertEqual(result["cancel_at_period_end"], True)  # From DB
    
    @patch('backend.payment_stripe.get_user_plan')
    async def test_get_subscription_info_no_subscription_id(self, mock_get_user_plan):
        """Test that returns None when user has no subscription_id"""
        # Setup: User has no subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.START,
            stripe_subscription_id=None,  # No subscription
            subscription_status=None,
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Execute
        result = await get_subscription_info(self.user_id)
        
        # Assert
        self.assertIsNone(result)
    
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    async def test_get_subscription_info_missing_current_period_end(self, mock_get_user_plan, mock_stripe_retrieve):
        """Test that returns None when subscription has no current_period_end"""
        # Setup: User has subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription without current_period_end
        mock_subscription = Mock()
        mock_subscription.id = self.subscription_id
        mock_subscription.status = "active"
        mock_subscription.current_period_end = None  # Missing field
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute
        result = await get_subscription_info(self.user_id)
        
        # Assert: Should return None when critical field is missing
        self.assertIsNone(result)
    
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    async def test_get_subscription_info_stripe_api_error(self, mock_get_user_plan, mock_stripe_retrieve):
        """Test that handles Stripe API errors gracefully"""
        # Setup: User has subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe error
        from backend.payment_stripe import stripe
        mock_stripe_retrieve.side_effect = stripe.error.StripeError("API Error")
        
        # Execute
        result = await get_subscription_info(self.user_id)
        
        # Assert: Should return None on error
        self.assertIsNone(result)
    
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    async def test_get_subscription_info_cancel_at_period_end_none_becomes_false(self, mock_get_user_plan, mock_stripe_retrieve):
        """Test that cancel_at_period_end=None is converted to False using bool()"""
        # Setup: User has subscription with cancel_at_period_end=None (edge case)
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=None,  # Edge case: None value
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.id = self.subscription_id
        mock_subscription.status = "active"
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute
        result = await get_subscription_info(self.user_id)
        
        # Assert: bool(None) = False
        self.assertIsNotNone(result)
        self.assertEqual(result["cancel_at_period_end"], False)
    
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    async def test_get_subscription_info_uses_ensure_utc(self, mock_get_user_plan, mock_stripe_retrieve):
        """Test that current_period_end uses ensure_utc for consistency"""
        # Setup: User has subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription
        mock_subscription = Mock()
        mock_subscription.id = self.subscription_id
        mock_subscription.status = "active"
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute
        result = await get_subscription_info(self.user_id)
        
        # Assert: current_period_end should be UTC aware datetime
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["current_period_end"])
        self.assertIsNotNone(result["current_period_end"].tzinfo)  # Should have timezone
        self.assertEqual(result["current_period_end"].tzinfo, timezone.utc)


class TestHandleSubscriptionUpdatedStartPlanBug(unittest.IsolatedAsyncioTestCase):
    """
    Test to reproduce bug: START plan users with active subscriptions should have 
    their subscriptions canceled when subscription.updated event is received.
    
    Bug scenario:
    - User has START plan (free, shouldn't have subscription)
    - But still has active subscription in Stripe (bug state)
    - When subscription.updated webhook arrives, subscription should be canceled
    - Current bug: Subscription status is synced, user continues to be charged
    """
    
    def setUp(self):
        self.user_id = "test_user_start_plan"
        self.customer_id = "cus_test_start"
        self.subscription_id = "sub_test_start"
    
    @patch('backend.payment_stripe.stripe.Subscription.delete')
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.db_supabase.get_supabase_admin')
    async def test_subscription_updated_should_cancel_for_start_plan_user(self, mock_get_supabase_admin, mock_update_user_plan, mock_stripe_delete):
        """
        Test that subscription.updated event cancels subscription when user has START plan.
        This test reproduces the bug where START plan users are incorrectly charged.
        """
        # Mock Supabase response: user has START plan but still has subscription
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "user_id": self.user_id,
            "plan": "start",  # START plan (free, shouldn't have subscription)
            "stripe_customer_id": self.customer_id,
            "stripe_subscription_id": self.subscription_id,  # But subscription still exists (bug)
            "subscription_status": "active",  # Active subscription (shouldn't exist for START plan)
            "stripe_event_ts": None,
            "next_plan": None,
            "plan_expires_at": None,
            "next_update_at": None,
            "cancel_at_period_end": False,
        }]
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Mock Stripe subscription delete
        mock_stripe_delete.return_value = None
        
        # Create subscription.updated event
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        subscription_event = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "current_period_end": int(future_date.timestamp()),
            "cancel_at_period_end": False,
        }
        
        event_created = int(datetime.now(timezone.utc).timestamp())
        event_id = "evt_test_start_plan"
        
        # Execute: Handle subscription.updated event
        await handle_subscription_updated(
            subscription=subscription_event,
            event_created=event_created,
            event_id=event_id
        )
        
        # Assert: Stripe subscription should be canceled
        # This assertion will FAIL with current code (reproducing the bug)
        mock_stripe_delete.assert_called_once_with(self.subscription_id), \
            "BUG REPRODUCED: stripe.Subscription.delete was NOT called. START plan user subscription should be canceled!"
        
        # Assert: Database should be updated to clear subscription fields
        mock_update_user_plan.assert_called()
        call_kwargs = mock_update_user_plan.call_args[1]
        self.assertEqual(
            call_kwargs.get('stripe_subscription_id'), _CLEAR_FIELD,
            "stripe_subscription_id should be cleared for START plan user"
        )
        self.assertEqual(
            call_kwargs.get('subscription_status'), 'canceled',
            "subscription_status should be 'canceled' for START plan user"
        )


class TestDowngradeToStartBug(unittest.IsolatedAsyncioTestCase):
    """
    Bug 1: downgrade_subscription to START plan should cancel Stripe subscription.
    
    Current bug: downgrade_subscription only updates database, doesn't cancel Stripe subscription.
    Result: User is still charged by Stripe even though they're on START (free) plan.
    """
    
    def setUp(self):
        self.user_id = "test_user_downgrade_start"
        self.subscription_id = "sub_test_downgrade"
        self.now = datetime.now(timezone.utc)
        self.future_time = self.now + timedelta(days=30)
    
    @patch('backend.payment_stripe.stripe.Subscription.modify')
    @patch('backend.payment_stripe.stripe.Subscription.delete')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_downgrade_to_start_should_cancel_stripe_subscription(
        self, mock_update_user_plan, mock_get_user_plan, mock_stripe_retrieve, 
        mock_stripe_delete, mock_stripe_modify
    ):
        """
        Bug 1: Downgrading to START should cancel Stripe subscription.
        This test will FAIL with current code.
        """
        # Setup: User has HIGH plan with active subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription retrieve
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "active"
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute: Downgrade to START
        result = await downgrade_subscription(self.user_id, PlanType.START)
        
        # Assert: Should succeed
        self.assertTrue(result)
        
        # Assert: Stripe subscription should be canceled (delete or modify with cancel_at_period_end)
        # This will FAIL with current code - Bug 1 reproduced
        stripe_canceled = mock_stripe_delete.called or (
            mock_stripe_modify.called and 
            mock_stripe_modify.call_args[1].get('cancel_at_period_end') == True
        )
        self.assertTrue(
            stripe_canceled,
            "BUG 1 REPRODUCED: Stripe subscription was NOT canceled when downgrading to START. "
            "User will continue to be charged!"
        )


class TestSubscriptionUpdatedExpiredNextPlanBug(unittest.IsolatedAsyncioTestCase):
    """
    Bug 3: subscription.updated should apply next_plan when next_update_at has passed.
    
    Current bug: subscription.updated only syncs status, doesn't check if next_plan should be applied.
    Result: If user is offline for a long time, downgrade is never applied.
    """
    
    def setUp(self):
        self.user_id = "test_user_expired_next_plan"
        self.customer_id = "cus_test_expired"
        self.subscription_id = "sub_test_expired"
        self.now = datetime.now(timezone.utc)
    
    @patch('backend.payment_stripe.update_user_plan')
    @patch('backend.db_supabase.get_supabase_admin')
    async def test_subscription_updated_should_apply_expired_next_plan(
        self, mock_get_supabase_admin, mock_update_user_plan
    ):
        """
        Bug 3: When subscription.updated arrives and next_update_at has passed, apply next_plan.
        This test will FAIL with current code.
        """
        # Setup: User has HIGH plan with expired next_plan=NORMAL
        past_time = self.now - timedelta(days=5)  # 5 days ago
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "user_id": self.user_id,
            "plan": "high",
            "stripe_customer_id": self.customer_id,
            "stripe_subscription_id": self.subscription_id,
            "subscription_status": "active",
            "stripe_event_ts": None,
            "next_plan": "normal",  # Scheduled downgrade
            "next_update_at": past_time.isoformat(),  # Already expired!
            "plan_expires_at": past_time.isoformat(),
            "cancel_at_period_end": False,
        }]
        mock_get_supabase_admin.return_value = mock_supabase
        
        # Create subscription.updated event
        future_date = self.now + timedelta(days=30)
        subscription_event = {
            "id": self.subscription_id,
            "customer": self.customer_id,
            "status": "active",
            "current_period_end": int(future_date.timestamp()),
            "cancel_at_period_end": False,
        }
        
        event_created = int(self.now.timestamp())
        event_id = "evt_test_expired"
        
        # Execute
        await handle_subscription_updated(
            subscription=subscription_event,
            event_created=event_created,
            event_id=event_id
        )
        
        # Assert: next_plan should be applied (plan changed to NORMAL)
        mock_update_user_plan.assert_called()
        call_kwargs = mock_update_user_plan.call_args[1]
        
        # This will FAIL with current code - Bug 3 reproduced
        self.assertEqual(
            call_kwargs.get('plan'), PlanType.NORMAL,
            "BUG 3 REPRODUCED: next_plan was NOT applied even though next_update_at has passed. "
            "User is still on HIGH plan instead of scheduled NORMAL plan!"
        )
        # Also check next_plan is cleared
        self.assertEqual(
            call_kwargs.get('next_plan'), _CLEAR_FIELD,
            "BUG 3 REPRODUCED: next_plan was NOT cleared after applying"
        )


class TestDowngradeToPaidPlanBug(unittest.IsolatedAsyncioTestCase):
    """
    Bug 4: downgrade_subscription to a paid plan should modify Stripe subscription price.
    
    Current bug: downgrade_subscription only updates database, doesn't modify Stripe price.
    Result: User is charged at old (higher) price instead of new (lower) price.
    """
    
    def setUp(self):
        self.user_id = "test_user_downgrade_paid"
        self.subscription_id = "sub_test_downgrade_paid"
        self.now = datetime.now(timezone.utc)
        self.future_time = self.now + timedelta(days=30)
    
    @patch('backend.payment_stripe.STRIPE_PRICE_IDS', {
        PlanType.NORMAL: "price_normal_real",
        PlanType.HIGH: "price_high_real",
        PlanType.ULTRA: "price_ultra_real",
        PlanType.PREMIUM: "price_premium_real"
    })
    @patch('backend.payment_stripe.stripe.Subscription.modify')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_downgrade_to_paid_plan_should_modify_stripe_subscription(
        self, mock_update_user_plan, mock_get_user_plan, mock_stripe_retrieve, mock_stripe_modify
    ):
        """
        Bug 4: Downgrading from ULTRA to HIGH should modify Stripe subscription.
        """
        # Setup: User has ULTRA plan
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.ULTRA,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription retrieve with items structure
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_subscription.status = "active"
        mock_subscription.get = Mock(side_effect=lambda key: {
            "items": {"data": [{"id": "si_test_item"}]}
        }.get(key))
        mock_subscription.__getitem__ = Mock(side_effect=lambda key: {
            "items": {"data": [{"id": "si_test_item"}]}
        }[key])
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Execute: Downgrade to HIGH
        result = await downgrade_subscription(self.user_id, PlanType.HIGH)
        
        # Assert: Should succeed
        self.assertTrue(result)
        
        # Assert: Stripe subscription should be modified with new price
        self.assertTrue(
            mock_stripe_modify.called,
            "BUG 4 FIX VERIFICATION: Stripe subscription should be modified when downgrading to paid plan"
        )


class TestCancelSubscriptionOrderBug(unittest.IsolatedAsyncioTestCase):
    """
    Bug 5: cancel_subscription writes DB before Stripe, causing inconsistency if Stripe fails.
    
    Current bug: DB is updated first, then Stripe is called.
    Result: If Stripe call fails, DB shows canceled but Stripe subscription is still active.
    """
    
    def setUp(self):
        self.user_id = "test_user_cancel_order"
        self.subscription_id = "sub_test_cancel_order"
        self.now = datetime.now(timezone.utc)
        self.future_time = self.now + timedelta(days=30)
    
    @patch('backend.payment_stripe.stripe.Subscription.modify')
    @patch('backend.payment_stripe.stripe.Subscription.retrieve')
    @patch('backend.payment_stripe.get_user_plan')
    @patch('backend.payment_stripe.update_user_plan')
    async def test_cancel_subscription_stripe_failure_should_not_update_db(
        self, mock_update_user_plan, mock_get_user_plan, mock_stripe_retrieve, mock_stripe_modify
    ):
        """
        Bug 5: If Stripe call fails, DB should not be updated.
        This test will FAIL with current code.
        """
        # Setup: User has active subscription
        user_plan = UserPlan(
            user_id=self.user_id,
            plan=PlanType.HIGH,
            stripe_subscription_id=self.subscription_id,
            subscription_status="active",
            cancel_at_period_end=False,
            created_at=self.now,
            updated_at=self.now
        )
        mock_get_user_plan.return_value = user_plan
        
        # Mock Stripe subscription retrieve
        mock_subscription = Mock()
        mock_subscription.current_period_end = int(self.future_time.timestamp())
        mock_stripe_retrieve.return_value = mock_subscription
        
        # Mock Stripe modify to FAIL
        mock_stripe_modify.side_effect = StripeError("Stripe API error")
        
        # Execute: Cancel subscription (should fail)
        result = await cancel_subscription(self.user_id)
        
        # Assert: Should return False (failure)
        self.assertFalse(result, "cancel_subscription should return False when Stripe fails")
        
        # Assert: DB should NOT be updated with cancel_at_period_end=True
        # This will FAIL with current code - Bug 5 reproduced
        # Current code updates DB first, so update_user_plan is called even though Stripe fails
        if mock_update_user_plan.called:
            call_kwargs = mock_update_user_plan.call_args[1]
            self.assertNotEqual(
                call_kwargs.get('cancel_at_period_end'), True,
                "BUG 5 REPRODUCED: DB was updated with cancel_at_period_end=True even though Stripe call failed. "
                "DB and Stripe are now inconsistent!"
            )


if __name__ == '__main__':
    unittest.main()

