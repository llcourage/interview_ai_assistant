import React, { useState, useEffect } from 'react';
import { getAuthHeader, getCurrentUser } from '../lib/auth';
import { API_BASE_URL } from '../lib/api';
import './Settings.css';

const getAuthToken = async () => {
  const user = await getCurrentUser();
  if (!user) return null;
  const authHeader = getAuthHeader();
  return authHeader ? authHeader.replace('Bearer ', '') : null;
};

interface PlanInfo {
  plan: string;
  monthly_token_limit?: number;
  monthly_tokens_used?: number;
  features: string[];
  subscription_info?: {
    subscription_id: string;
    status: string;
    current_period_end: string;
    cancel_at_period_end: boolean;
  };
}

export const Settings: React.FC = () => {
  const [planInfo, setPlanInfo] = useState<PlanInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  useEffect(() => {
    loadPlanInfo();
  }, []);

  const loadPlanInfo = async () => {
    try {
      const authHeader = getAuthHeader();
      if (!authHeader) return;

      const response = await fetch(`${API_BASE_URL}/api/plan`, {
        headers: {
          'Authorization': authHeader
        }
      });

      if (!response.ok) throw new Error('Failed to load plan info');

      const data = await response.json();
      setPlanInfo(data);
    } catch (error) {
      console.error('Error loading plan info:', error);
      setMessage({ type: 'error', text: 'Failed to load plan information' });
    }
  };

  const handleUpgradePlan = async (plan: 'normal' | 'high') => {
    setLoading(true);
    setMessage(null);

    try {
      const token = await getAuthToken();
      if (!token) throw new Error('Not logged in');

      const successUrl = `${window.location.origin}/settings?payment=success`;
      const cancelUrl = `${window.location.origin}/settings?payment=cancel`;

      const response = await fetch(`${API_BASE_URL}/api/plan/checkout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          plan,
          success_url: successUrl,
          cancel_url: cancelUrl
        })
      });

      if (!response.ok) throw new Error('Failed to create checkout session');

      const data = await response.json();
      
      // 跳转到Stripe支付页面
      window.location.href = data.checkout_url;
    } catch (error) {
      console.error('Error creating checkout:', error);
      setMessage({ type: 'error', text: 'Failed to create payment session' });
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel the subscription? The subscription will be canceled at the end of the current period.')) {
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const token = await getAuthToken();
      if (!token) throw new Error('Not logged in');

      const response = await fetch(`${API_BASE_URL}/api/plan/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to cancel subscription');

      const data = await response.json();
      setMessage({ type: 'success', text: data.message });
      await loadPlanInfo();
    } catch (error) {
      console.error('Error canceling subscription:', error);
      setMessage({ type: 'error', text: 'Failed to cancel subscription' });
    } finally {
      setLoading(false);
    }
  };

  const getPlanDisplayName = (plan: string) => {
    const names: Record<string, string> = {
      'normal': 'Normal Plan',
      'high': 'High Plan'
    };
    return names[plan] || plan;
  };

  const getPlanPrice = (plan: string) => {
    const prices: Record<string, string> = {
      'normal': '$19.9/week',
      'high': '$29.9/week'
    };
    return prices[plan] || 'N/A';
  };

  return (
    <div className="settings-container">
      <h1>⚙️ Settings</h1>

      {message && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      {/* Plan 信息 */}
      <section className="settings-section">
        <h2>📦 Subscription Plan</h2>
        
        {planInfo ? (
          <div className="plan-info-card">
            <div className="plan-header">
              <div>
                <h3>{getPlanDisplayName(planInfo.plan)}</h3>
                <p className="plan-price">{getPlanPrice(planInfo.plan)}</p>
              </div>
              <span className="plan-badge">Current Plan</span>
            </div>

            {planInfo.monthly_token_limit !== undefined && planInfo.monthly_token_limit > 0 && (
            <div className="plan-usage">
              <div className="usage-item">
                  <div className="usage-header">
                    <label>Monthly Token Quota Usage</label>
                    <span className="usage-percentage">
                      {(((planInfo.monthly_tokens_used || 0) / planInfo.monthly_token_limit) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="usage-bar-container">
                  <div 
                      className={`usage-bar ${((planInfo.monthly_tokens_used || 0) / planInfo.monthly_token_limit) >= 0.8 ? 'usage-bar-warning' : ''}`}
                    >
                      <div 
                        className={`usage-progress ${((planInfo.monthly_tokens_used || 0) / planInfo.monthly_token_limit) >= 0.9 ? 'usage-progress-danger' : ((planInfo.monthly_tokens_used || 0) / planInfo.monthly_token_limit) >= 0.8 ? 'usage-progress-warning' : ''}`}
                    style={{ 
                          width: `${Math.min(((planInfo.monthly_tokens_used || 0) / planInfo.monthly_token_limit) * 100, 100)}%` 
                    }}
                  />
                </div>
                  </div>
                  <div className="usage-details">
                <span className="usage-text">
                      <strong>Used:</strong> {(planInfo.monthly_tokens_used || 0).toLocaleString()} tokens
                    </span>
                    <span className="usage-remaining">
                      <strong>Remaining:</strong> {Math.max(0, planInfo.monthly_token_limit - (planInfo.monthly_tokens_used || 0)).toLocaleString()} tokens
                    </span>
                    <span className="usage-total">
                      <strong>Total:</strong> {planInfo.monthly_token_limit.toLocaleString()} tokens
                </span>
              </div>
                  {((planInfo.monthly_tokens_used || 0) / planInfo.monthly_token_limit) >= 0.8 && (
                    <div className="usage-warning-banner">
                      ⚠️ Your quota usage has exceeded 80%. Remaining quota is limited. Quota will reset monthly.
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="plan-features">
              <h4>Features:</h4>
              <ul>
                {planInfo.features.map((feature, index) => (
                  <li key={index}>✓ {feature}</li>
                ))}
              </ul>
            </div>

            {planInfo.subscription_info && (
              <div className="subscription-info">
                <p>Subscription Status: {planInfo.subscription_info.status}</p>
                <p>Next Renewal: {new Date(planInfo.subscription_info.current_period_end).toLocaleDateString()}</p>
                {planInfo.subscription_info.cancel_at_period_end && (
                  <p className="warning">⚠️ Subscription will be canceled at the end of the current period</p>
                )}
              </div>
            )}
          </div>
        ) : (
          <p>Loading...</p>
        )}

        {/* Upgrade/Downgrade buttons */}
        {planInfo && planInfo.plan === 'normal' && (
          <div className="upgrade-options">
            <div className="plan-option featured">
              <div className="badge">Upgrade</div>
              <h3>High Plan</h3>
              <p className="price">$29.9/week</p>
              <ul>
                <li>GPT-4o model (full version)</li>
                <li>Access to gpt-4o-mini</li>
                <li>500K tokens per month</li>
              </ul>
              <button 
                className="upgrade-button"
                onClick={() => handleUpgradePlan('high')}
                disabled={loading}
              >
                Upgrade to High
              </button>
            </div>
          </div>
        )}

        {planInfo && planInfo.plan === 'high' && (
          <div className="plan-actions">
            <p className="plan-message">🎉 You are using the highest level High Plan!</p>
          </div>
        )}

        {planInfo && (
          <button 
            className="cancel-button"
            onClick={handleCancelSubscription}
            disabled={loading}
          >
            Cancel Subscription
          </button>
        )}
      </section>

      {/* API Key management removed - All users use server API Key */}
    </div>
  );
};

