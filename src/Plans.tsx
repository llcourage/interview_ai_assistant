import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getAuthHeader, getToken, isAuthenticated } from './lib/auth';
import { API_BASE_URL } from './lib/api';
import { Header } from './components/Header';
import { PlanCard } from './components/PlanCard';
import './Plans.css';

interface PlanInfo {
  plan: string;
}

export const Plans: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState<string | null>(null);
  const [currentPlan, setCurrentPlan] = useState<string | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(true);
  const [canceling, setCanceling] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 每次路由变化时都重新查询数据库
  useEffect(() => {
    loadCurrentPlan();
  }, [location.pathname]);

  // 监听认证状态变化，登录后自动重新查询
  useEffect(() => {
    const handleAuthStateChange = async () => {
      // 等待更长时间确保token已保存并同步到服务器
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 重试机制：最多重试3次，每次间隔500ms
      let retries = 0;
      const maxRetries = 3;
      
      const tryLoadPlan = async () => {
        const authenticated = await isAuthenticated();
        if (authenticated) {
          console.log(`🔒 Plans: Auth state changed, reloading plan from database (attempt ${retries + 1}/${maxRetries})`);
          await loadCurrentPlan();
          
          // 如果加载失败且还有重试次数，继续重试
          if (retries < maxRetries - 1) {
            retries++;
            await new Promise(resolve => setTimeout(resolve, 500));
            return tryLoadPlan();
          }
        } else if (retries < maxRetries - 1) {
          // 如果还没认证，等待后重试
          retries++;
          await new Promise(resolve => setTimeout(resolve, 500));
          return tryLoadPlan();
        }
      };
      
      await tryLoadPlan();
    };

    window.addEventListener('auth-state-changed', handleAuthStateChange);
    return () => {
      window.removeEventListener('auth-state-changed', handleAuthStateChange);
    };
  }, []);

  const loadCurrentPlan = async () => {
    try {
      setLoadingPlan(true);
      setCurrentPlan(null); // 先清空，避免显示旧数据
      
      // 确保用户已认证
      const authenticated = await isAuthenticated();
      if (!authenticated) {
        setLoadingPlan(false);
        return;
      }

      const authHeader = getAuthHeader();
      if (!authHeader) {
        setLoadingPlan(false);
        return;
      }

      // 添加时间戳参数，确保每次请求都是新的，不读取缓存
      const timestamp = Date.now();
      const response = await fetch(`${API_BASE_URL}/api/plan?t=${timestamp}`, {
        method: 'GET',
        headers: {
          'Authorization': authHeader,
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        },
        cache: 'no-store' // 确保不缓存
      });

      if (response.ok) {
        const data: PlanInfo = await response.json();
        console.log('📦 Plans: Loaded plan from database:', data.plan);
        setCurrentPlan(data.plan);
      } else {
        console.error('❌ Plans: Failed to load plan, status:', response.status);
        setCurrentPlan(null);
      }
    } catch (error) {
      console.error('❌ Plans: Failed to load current plan:', error);
      setCurrentPlan(null);
    } finally {
      setLoadingPlan(false);
    }
  };

  const getPlanDisplayName = (plan: string | null): string => {
    if (!plan) return '';
    const names: Record<string, string> = {
      'start': 'Start Plan',
      'normal': 'Weekly Normal Plan',
      'high': 'Monthly Normal Plan',
      'ultra': 'Monthly Ultra Plan',
      'premium': 'Monthly Premium Plan',
      'internal': 'Internal Plan'
    };
    return names[plan] || plan;
  };

  const handleCancelSubscription = async () => {
    // Show confirmation dialog
    const confirmed = window.confirm(
      'Are you sure you want to cancel your subscription?\n\n' +
      'Your subscription will be canceled at the end of the current billing period. ' +
      'You will continue to have access until then, and can still use the free Start Plan afterwards.'
    );
    
    if (!confirmed) {
      return;
    }

    setCanceling(true);
    setMessage(null);

    try {
      const token = getToken();
      if (!token) throw new Error('Not logged in');

      const response = await fetch(`${API_BASE_URL}/api/plan/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to cancel subscription');

      const data = await response.json();
      setMessage({ type: 'success', text: data.message || 'Subscription will be canceled at the end of current period' });
      
      // Reload plan info to reflect the change
      await loadCurrentPlan();
    } catch (error) {
      console.error('Error canceling subscription:', error);
      setMessage({ type: 'error', text: 'Failed to cancel subscription. Please try again.' });
    } finally {
      setCanceling(false);
    }
  };

  const handlePlanSelect = async (plan: 'start' | 'normal' | 'high' | 'ultra' | 'premium') => {
    setLoading(plan);
    
    try {
      // Check if user is logged in
      const authHeader = getAuthHeader();
      
      if (!authHeader) {
        // Not logged in, redirect to login page with plan parameter
        navigate(`/login?plan=${plan}&redirect=/checkout`);
        return;
      }

      // Logged in, create Stripe Checkout Session
      const token = getToken();
      if (!token) {
        navigate(`/login?plan=${plan}&redirect=/checkout`);
        return;
      }
      
      const response = await fetch(`${API_BASE_URL}/api/plan/checkout`, {
        method: 'POST',
        headers: {
          'Authorization': getAuthHeader() || '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          plan: plan,
          success_url: `${window.location.origin}/success?plan=${plan}`,
          cancel_url: `${window.location.origin}/?canceled=true`
        })
      });

      if (!response.ok) {
        // Try to get detailed error information
        let errorMessage = 'Failed to create checkout session';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
          console.error('Checkout API error:', errorData);
        } catch (e) {
          console.error('Checkout API error (non-JSON):', response.status, response.statusText);
          errorMessage = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url;
      
    } catch (error) {
      console.error('Error creating checkout:', error);
      // If failed, redirect to checkout page
      navigate(`/checkout?plan=${plan}`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="plans-page">
      <Header />
      <div className="plans-container">
        {/* Focus gradient glow - make title and card area the visual center */}
        <div className="plans-glow"></div>
        
        <h1 className="plans-title">Choose Your Plan</h1>
        <p className="plans-subtitle">Select the perfect plan for your needs</p>
        
        {message && (
          <div className={`plans-message plans-message-${message.type}`}>
            {message.text}
          </div>
        )}
        
        {!loadingPlan && currentPlan && (
          <div className="current-plan-badge">
            <span className="current-plan-label">Current Plan:</span>
            <span className="current-plan-name">{getPlanDisplayName(currentPlan)}</span>
            {currentPlan !== 'start' && (
              <button
                className="cancel-plan-button"
                onClick={handleCancelSubscription}
                disabled={canceling}
                title="Cancel your subscription"
              >
                {canceling ? 'Canceling...' : 'Cancel your plan'}
              </button>
            )}
          </div>
        )}
        
        <div className="plans-grid">
          <PlanCard
            name="Start Plan"
            features={[
              "Great Model",
              "100K Tokens Lifetime",
              "No Monthly Reset"
            ]}
            price="Free"
            billing=""
            loading={loading === 'start'}
            onSelect={() => handlePlanSelect('start')}
          />

          <PlanCard
            name="Weekly Normal Plan"
            features={[
              "Great Model",
              "1M Tokens per week",
              "~2-3 sessions"
            ]}            
            price="$9.9"
            billing="/week"
            loading={loading === 'normal'}
            onSelect={() => handlePlanSelect('normal')}
          />

          <PlanCard
            name="Monthly Normal Plan"
            features={[
              "Great Model",
              "1M Tokens per month",
              "~2-3 sessions"
            ]}
            price="$19.9"
            billing="/month"
            loading={loading === 'high'}
            onSelect={() => handlePlanSelect('high')}
          />

          <PlanCard
            name="Monthly Ultra Plan"
            features={[
              "Great Model",
              "5M Tokens per month",
              "~10-15 sessions"
            ]}
            price="$39.9"
            billing="/month"
            loading={loading === 'ultra'}
            onSelect={() => handlePlanSelect('ultra')}
          />

          <PlanCard
            name="Monthly Premium Plan"
            recommended
            features={[
              "Great Model",
              "20M Tokens per month",
              "~20-30 sessions",
              "Priority Support"
            ]}
            price="$69.9"
            billing="/month"
            loading={loading === 'premium'}
            onSelect={() => handlePlanSelect('premium')}
          />
        </div>
      </div>
    </div>
  );
};

