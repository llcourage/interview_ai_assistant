import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from './lib/supabase';
import { API_BASE_URL } from './lib/api';
import { Header } from './components/Header';
import './Profile.css';

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

export const Profile: React.FC = () => {
  const navigate = useNavigate();
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [planInfo, setPlanInfo] = useState<PlanInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkAuthAndLoadData();
  }, []);

  const checkAuthAndLoadData = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        navigate('/login');
        return;
      }

      setUserEmail(session.user.email || null);
      await loadPlanInfo(session.access_token);
    } catch (err) {
      console.error('Auth check error:', err);
      setError('加载用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const loadPlanInfo = async (token: string) => {
    try {
      setError(null);
      console.log('🔍 Loading plan info from:', `${API_BASE_URL}/api/plan`);
      const response = await fetch(`${API_BASE_URL}/api/plan`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Failed to load plan info:', response.status, errorText);
        const errorMsg = `Failed to load plan info (${response.status}): ${errorText || 'Unknown error'}`;
        setError(errorMsg);
        setPlanInfo(null);
        return;
      }

      const data = await response.json();
      
      // Validate required fields
      if (!data.plan) {
        throw new Error('Invalid plan data: missing plan field');
      }
      
      setPlanInfo(data);
      setError(null);
      
      // 同步 plan 到 localStorage，并通知其他窗口（如 Electron 客户端）
      const plan = data.plan as 'normal' | 'high';
      localStorage.setItem('currentPlan', plan);
      window.dispatchEvent(new CustomEvent('planChanged', { detail: plan }));
    } catch (err: any) {
      console.error('❌ Error loading plan info:', err);
      const errorMsg = err?.message || '加载Plan信息失败，请检查网络连接和服务器状态';
      setError(errorMsg);
      setPlanInfo(null);
    }
  };

  const getPlanDisplayName = (plan: string) => {
    const planMap: { [key: string]: string } = {
      'normal': 'Normal',
      'high': 'High'
    };
    return planMap[plan] || plan;
  };

  const getPlanPrice = (plan: string) => {
    const priceMap: { [key: string]: string } = {
      'normal': '$19.99',
      'high': '$49.99'
    };
    return priceMap[plan] || 'N/A';
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="profile-page">
        <Header />
        <div className="profile-container">
          <div className="loading-spinner">⏳ Loading...</div>
        </div>
      </div>
    );
  }

  // Don't block the entire page if only planInfo fails to load
  // The error will be shown in the plan card section

  return (
    <div className="profile-page">
      <Header />
      <div className="profile-container">
        {/* Profile Header with Avatar */}
        <div className="profile-header">
          <div className="avatar-container">
            <div className="avatar">
              {userEmail?.charAt(0).toUpperCase() || 'U'}
            </div>
          </div>
          <div className="profile-header-info">
            <h1>Account Settings</h1>
            <p className="profile-email">{userEmail}</p>
          </div>
        </div>

        <div className="profile-content">
          {/* Account Information Card */}
          <div className="profile-card">
            <div className="card-header">
              <h2 className="card-title">Account Information</h2>
            </div>
            <div className="card-body">
              <div className="info-item">
                <div className="info-icon">📧</div>
                <div className="info-content">
                  <div className="info-label">Email Address</div>
                  <div className="info-value">{userEmail || 'N/A'}</div>
                </div>
              </div>
              {planInfo && (
                <>
                  <div className="info-item">
                    <div className="info-icon">📋</div>
                    <div className="info-content">
                      <div className="info-label">Current Plan</div>
                      <div className="info-value">{getPlanDisplayName(planInfo.plan)}</div>
                    </div>
                  </div>
                  <div className="info-item">
                    <div className="info-icon">📊</div>
                    <div className="info-content">
                      <div className="info-label">Daily Usage</div>
                      <div className="info-value">
                        {planInfo.daily_requests} / {planInfo.daily_limit === -1 ? '∞' : planInfo.daily_limit} requests today
                      </div>
                      {planInfo.daily_limit !== -1 && (
                        <div className="stat-progress" style={{ marginTop: '0.75rem' }}>
                          <div
                            className="stat-progress-bar"
                            style={{
                              width: `${Math.min((planInfo.daily_requests / planInfo.daily_limit) * 100, 100)}%`
                            }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
              {!planInfo && !loading && error && (
                <div className="info-item">
                  <div className="info-icon">⚠️</div>
                  <div className="info-content">
                    <div className="info-label">Plan Status</div>
                    <div className="info-value" style={{ color: '#ffc107' }}>Failed to load plan information</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Current Plan Card */}
          {planInfo ? (
            <div className="profile-card plan-card">
              <div className="card-header">
                <div>
                  <h2 className="card-title">Current Plan</h2>
                  <p className="card-subtitle">Manage your subscription and usage</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="refresh-btn"
                    onClick={async () => {
                      const { data: { session } } = await supabase.auth.getSession();
                      if (session) {
                        setLoading(true);
                        await loadPlanInfo(session.access_token);
                        setLoading(false);
                      }
                    }}
                    title="Refresh plan information"
                  >
                    🔄 Refresh
                  </button>
                  <button
                    className="upgrade-btn"
                    onClick={() => navigate('/plans')}
                  >
                    {planInfo.plan === 'high' ? 'Manage' : 'Upgrade'}
                  </button>
                </div>
              </div>

              <div className="card-body">
                {/* Plan Badge */}
                <div className="plan-badge-section">
                  <div className="plan-badge">
                    <span className="plan-name">{getPlanDisplayName(planInfo.plan)}</span>
                    <span className="plan-price">{getPlanPrice(planInfo.plan)}<span className="price-unit">/month</span></span>
                  </div>
                </div>

                {/* Usage Statistics */}
                <div className="usage-section">
                  <h3 className="section-subtitle">Usage Statistics</h3>
                  <div className="usage-stats">
                    <div className="stat-card">
                      <div className="stat-header">
                        <span className="stat-label">Daily Requests</span>
                        <span className="stat-value">
                          {planInfo.daily_requests} / {planInfo.daily_limit === -1 ? '∞' : planInfo.daily_limit}
                        </span>
                      </div>
                      <div className="stat-progress">
                        <div
                          className="stat-progress-bar"
                          style={{
                            width: planInfo.daily_limit === -1
                              ? '100%'
                              : `${Math.min((planInfo.daily_requests / planInfo.daily_limit) * 100, 100)}%`
                          }}
                        />
                      </div>
                      <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.5)' }}>
                        {planInfo.daily_limit === -1 
                          ? 'Unlimited requests' 
                          : `${planInfo.daily_limit - planInfo.daily_requests} requests remaining today`
                        }
                      </div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-header">
                        <span className="stat-label">Monthly Requests</span>
                        <span className="stat-value">
                          {planInfo.monthly_requests} / {planInfo.monthly_limit === -1 ? '∞' : planInfo.monthly_limit}
                        </span>
                      </div>
                      <div className="stat-progress">
                        <div
                          className="stat-progress-bar"
                          style={{
                            width: planInfo.monthly_limit === -1
                              ? '100%'
                              : `${Math.min((planInfo.monthly_requests / planInfo.monthly_limit) * 100, 100)}%`
                          }}
                        />
                      </div>
                      <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.5)' }}>
                        {planInfo.monthly_limit === -1 
                          ? 'Unlimited requests' 
                          : `${planInfo.monthly_limit - planInfo.monthly_requests} requests remaining this month`
                        }
                      </div>
                    </div>
                  </div>
                </div>

                {/* Features */}
                <div className="features-section">
                  <h3 className="section-subtitle">Plan Features</h3>
                  <div className="features-grid">
                    {planInfo.features.map((feature, index) => (
                      <div key={index} className="feature-item">
                        <span className="feature-icon">✓</span>
                        <span className="feature-text">{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Subscription Info */}
                {planInfo.subscription_info && (
                  <div className="subscription-section">
                    <h3 className="section-subtitle">Subscription Details</h3>
                    <div className="subscription-details">
                      <div className="subscription-item">
                        <span className="subscription-label">Status</span>
                        <span className={`subscription-badge ${planInfo.subscription_info.status}`}>
                          {planInfo.subscription_info.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="subscription-item">
                        <span className="subscription-label">Subscription ID</span>
                        <span className="subscription-value">{planInfo.subscription_info.subscription_id}</span>
                      </div>
                      <div className="subscription-item">
                        <span className="subscription-label">Renews On</span>
                        <span className="subscription-value">
                          {formatDate(planInfo.subscription_info.current_period_end)}
                        </span>
                      </div>
                      {planInfo.subscription_info.cancel_at_period_end && (
                        <div className="subscription-warning">
                          ⚠️ Subscription will cancel at period end
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : !loading && (
            <div className="profile-card">
              <div className="card-header">
                <h2 className="card-title">Current Plan</h2>
              </div>
              <div className="card-body">
                <div style={{ textAlign: 'center', padding: '2rem' }}>
                  <p style={{ color: 'rgba(255, 255, 255, 0.6)', marginBottom: '1rem' }}>
                    {error || 'Unable to load plan information'}
                  </p>
                  <button
                    className="refresh-btn"
                    onClick={async () => {
                      const { data: { session } } = await supabase.auth.getSession();
                      if (session) {
                        setLoading(true);
                        setError(null);
                        await loadPlanInfo(session.access_token);
                        setLoading(false);
                      }
                    }}
                  >
                    🔄 Retry Loading Plan
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="profile-actions">
            <button
              className="action-btn primary"
              onClick={() => navigate('/plans')}
            >
              {planInfo?.plan === 'high' ? 'Manage Subscription' : planInfo?.plan === 'normal' ? 'Manage Plan' : 'Upgrade Plan'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
