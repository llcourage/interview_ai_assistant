import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from '../lib/api';
import './Settings.css';

interface PlanInfo {
  plan: string;
  daily_requests: number;
  monthly_requests: number;
  daily_limit: number;
  monthly_limit: number;
  features: string[];
  subscription_info?: {
    subscription_id: string;
    status: string;
    current_period_end: string;
    cancel_at_period_end: boolean;
  };
}

interface ApiKeyInfo {
  has_key: boolean;
  masked_key: string | null;
}

export const Settings: React.FC = () => {
  const [planInfo, setPlanInfo] = useState<PlanInfo | null>(null);
  const [apiKeyInfo, setApiKeyInfo] = useState<ApiKeyInfo | null>(null);
  const [newApiKey, setNewApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  useEffect(() => {
    loadPlanInfo();
    loadApiKeyInfo();
  }, []);

  const getAuthToken = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token;
  };

  const loadPlanInfo = async () => {
    try {
      const token = await getAuthToken();
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/plan`, {
        headers: {
          'Authorization': `Bearer ${token}`
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

  const loadApiKeyInfo = async () => {
    try {
      const token = await getAuthToken();
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/apikey`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to load API key info');

      const data = await response.json();
      setApiKeyInfo(data);
    } catch (error) {
      console.error('Error loading API key info:', error);
    }
  };

  const handleSaveApiKey = async () => {
    if (!newApiKey.trim()) {
      setMessage({ type: 'error', text: 'Please enter API Key' });
      return;
    }

    if (!newApiKey.startsWith('sk-')) {
      setMessage({ type: 'error', text: 'OpenAI API Key should start with sk-' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const token = await getAuthToken();
      if (!token) throw new Error('Not logged in');

      const response = await fetch(`${API_BASE_URL}/api/apikey`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          api_key: newApiKey,
          provider: 'openai'
        })
      });

      if (!response.ok) throw new Error('Failed to save API key');

      setMessage({ type: 'success', text: 'API Key saved successfully' });
      setNewApiKey('');
      await loadApiKeyInfo();
    } catch (error) {
      console.error('Error saving API key:', error);
      setMessage({ type: 'error', text: 'Failed to save API Key' });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteApiKey = async () => {
    if (!confirm('Are you sure you want to delete the API Key? You will not be able to use AI features until you set it again.')) {
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const token = await getAuthToken();
      if (!token) throw new Error('Not logged in');

      const response = await fetch(`${API_BASE_URL}/api/apikey`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to delete API key');

      setMessage({ type: 'success', text: 'API Key deleted' });
      await loadApiKeyInfo();
    } catch (error) {
      console.error('Error deleting API key:', error);
      setMessage({ type: 'error', text: 'Failed to delete API Key' });
    } finally {
      setLoading(false);
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

            <div className="plan-usage">
              <div className="usage-item">
                <label>Daily Usage:</label>
                <div className="usage-bar">
                  <div 
                    className="usage-progress" 
                    style={{ 
                      width: planInfo.daily_limit === -1 ? '0%' : 
                        `${(planInfo.daily_requests / planInfo.daily_limit) * 100}%` 
                    }}
                  />
                </div>
                <span className="usage-text">
                  {planInfo.daily_requests} / {planInfo.daily_limit === -1 ? 'Unlimited' : planInfo.daily_limit}
                </span>
              </div>

              <div className="usage-item">
                <label>Monthly Usage:</label>
                <div className="usage-bar">
                  <div 
                    className="usage-progress" 
                    style={{ 
                      width: planInfo.monthly_limit === -1 ? '0%' : 
                        `${(planInfo.monthly_requests / planInfo.monthly_limit) * 100}%` 
                    }}
                  />
                </div>
                <span className="usage-text">
                  {planInfo.monthly_requests} / {planInfo.monthly_limit === -1 ? 'Unlimited' : planInfo.monthly_limit}
                </span>
              </div>
            </div>

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
                <li>Premium model</li>
                <li>Advanced features</li>
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

