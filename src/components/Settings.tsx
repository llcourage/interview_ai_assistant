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
      setMessage({ type: 'error', text: '加载Plan信息失败' });
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
      setMessage({ type: 'error', text: '请输入API Key' });
      return;
    }

    if (!newApiKey.startsWith('sk-')) {
      setMessage({ type: 'error', text: 'OpenAI API Key 应该以 sk- 开头' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const token = await getAuthToken();
      if (!token) throw new Error('未登录');

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

      setMessage({ type: 'success', text: 'API Key 已保存成功' });
      setNewApiKey('');
      await loadApiKeyInfo();
    } catch (error) {
      console.error('Error saving API key:', error);
      setMessage({ type: 'error', text: '保存API Key失败' });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteApiKey = async () => {
    if (!confirm('确定要删除API Key吗？删除后您将无法使用AI功能，直到重新设置。')) {
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const token = await getAuthToken();
      if (!token) throw new Error('未登录');

      const response = await fetch(`${API_BASE_URL}/api/apikey`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to delete API key');

      setMessage({ type: 'success', text: 'API Key 已删除' });
      await loadApiKeyInfo();
    } catch (error) {
      console.error('Error deleting API key:', error);
      setMessage({ type: 'error', text: '删除API Key失败' });
    } finally {
      setLoading(false);
    }
  };

  const handleUpgradePlan = async (plan: 'normal' | 'high') => {
    setLoading(true);
    setMessage(null);

    try {
      const token = await getAuthToken();
      if (!token) throw new Error('未登录');

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
      setMessage({ type: 'error', text: '创建支付会话失败' });
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm('确定要取消订阅吗？订阅将在当前周期结束时取消，之后自动降级为Starter Plan。')) {
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const token = await getAuthToken();
      if (!token) throw new Error('未登录');

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
      setMessage({ type: 'error', text: '取消订阅失败' });
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
      'normal': '$19.99/月',
      'high': '$49.99/月'
    };
    return prices[plan] || '未知';
  };

  return (
    <div className="settings-container">
      <h1>⚙️ 设置</h1>

      {message && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      {/* Plan 信息 */}
      <section className="settings-section">
        <h2>📦 订阅计划</h2>
        
        {planInfo ? (
          <div className="plan-info-card">
            <div className="plan-header">
              <div>
                <h3>{getPlanDisplayName(planInfo.plan)}</h3>
                <p className="plan-price">{getPlanPrice(planInfo.plan)}</p>
              </div>
              <span className="plan-badge">当前计划</span>
            </div>

            <div className="plan-usage">
              <div className="usage-item">
                <label>今日使用:</label>
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
                  {planInfo.daily_requests} / {planInfo.daily_limit === -1 ? '无限' : planInfo.daily_limit}
                </span>
              </div>

              <div className="usage-item">
                <label>本月使用:</label>
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
                  {planInfo.monthly_requests} / {planInfo.monthly_limit === -1 ? '无限' : planInfo.monthly_limit}
                </span>
              </div>
            </div>

            <div className="plan-features">
              <h4>功能特性:</h4>
              <ul>
                {planInfo.features.map((feature, index) => (
                  <li key={index}>✓ {feature}</li>
                ))}
              </ul>
            </div>

            {planInfo.subscription_info && (
              <div className="subscription-info">
                <p>订阅状态: {planInfo.subscription_info.status}</p>
                <p>下次续费: {new Date(planInfo.subscription_info.current_period_end).toLocaleDateString()}</p>
                {planInfo.subscription_info.cancel_at_period_end && (
                  <p className="warning">⚠️ 订阅将在当前周期结束时取消</p>
                )}
              </div>
            )}
          </div>
        ) : (
          <p>加载中...</p>
        )}

        {/* 升级/降级按钮 */}
        {planInfo && planInfo.plan === 'normal' && (
          <div className="upgrade-options">
            <div className="plan-option featured">
              <div className="badge">升级</div>
              <h3>High Plan</h3>
              <p className="price">$49.99/月</p>
              <ul>
                <li>无限请求</li>
                <li>GPT-4o 完整版模型</li>
                <li>支持所有高级模型</li>
                <li>PDF 导出</li>
                <li>高级分析</li>
                <li>优先支持</li>
              </ul>
              <button 
                className="upgrade-button"
                onClick={() => handleUpgradePlan('high')}
                disabled={loading}
              >
                升级到 High
              </button>
            </div>
          </div>
        )}

        {planInfo && planInfo.plan === 'high' && (
          <div className="plan-actions">
            <p className="plan-message">🎉 您正在使用最高级别的 High Plan！</p>
          </div>
        )}

        {planInfo && (
          <button 
            className="cancel-button"
            onClick={handleCancelSubscription}
            disabled={loading}
          >
            取消订阅
          </button>
        )}
      </section>

      {/* API Key 管理已移除 - 所有用户使用服务器 API Key */}
    </div>
  );
};

