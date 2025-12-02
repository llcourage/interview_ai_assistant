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
      const response = await fetch(`${API_BASE_URL}/api/plan`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load plan info');
      }

      const data = await response.json();
      setPlanInfo(data);
    } catch (err) {
      console.error('Error loading plan info:', err);
      setError('加载Plan信息失败');
    }
  };

  const getPlanDisplayName = (plan: string) => {
    const planMap: { [key: string]: string } = {
      'starter': 'Starter (Free)',
      'normal': 'Normal Plan',
      'high': 'High Plan'
    };
    return planMap[plan] || plan;
  };

  const getPlanPrice = (plan: string) => {
    const priceMap: { [key: string]: string } = {
      'starter': 'Free',
      'normal': '$19.99/month',
      'high': '$49.99/month'
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

  if (error) {
    return (
      <div className="profile-page">
        <Header />
        <div className="profile-container">
          <div className="error-message">❌ {error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <Header />
      <div className="profile-container">
        <div className="profile-header">
          <h1>👤 User Profile</h1>
          <p className="profile-subtitle">Your account information and subscription details</p>
        </div>

        <div className="profile-content">
          {/* Account Information */}
          <div className="profile-section">
            <h2 className="section-title">Account Information</h2>
            <div className="info-card">
              <div className="info-row">
                <span className="info-label">Email:</span>
                <span className="info-value">{userEmail || 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Current Plan */}
          {planInfo && (
            <div className="profile-section">
              <h2 className="section-title">Current Plan</h2>
              <div className="plan-info-card">
                <div className="plan-header">
                  <div className="plan-name-badge">
                    <span className="plan-name">{getPlanDisplayName(planInfo.plan)}</span>
                    <span className="plan-price">{getPlanPrice(planInfo.plan)}</span>
                  </div>
                  <button
                    className="upgrade-btn"
                    onClick={() => navigate('/plans')}
                  >
                    {planInfo.plan === 'high' ? 'Manage Plan' : 'Upgrade Plan'}
                  </button>
                </div>

                {/* Usage Statistics */}
                <div className="usage-stats">
                  <div className="stat-item">
                    <div className="stat-label">Daily Requests</div>
                    <div className="stat-value">
                      {planInfo.daily_requests} / {planInfo.daily_limit === -1 ? '∞' : planInfo.daily_limit}
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
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Monthly Requests</div>
                    <div className="stat-value">
                      {planInfo.monthly_requests} / {planInfo.monthly_limit === -1 ? '∞' : planInfo.monthly_limit}
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
                  </div>
                </div>

                {/* Features */}
                <div className="plan-features">
                  <h3 className="features-title">Plan Features</h3>
                  <ul className="features-list">
                    {planInfo.features.map((feature, index) => (
                      <li key={index}>✅ {feature}</li>
                    ))}
                  </ul>
                </div>

                {/* Subscription Info */}
                {planInfo.subscription_info && (
                  <div className="subscription-info">
                    <h3 className="subscription-title">Subscription Details</h3>
                    <div className="subscription-details">
                      <div className="subscription-row">
                        <span className="subscription-label">Status:</span>
                        <span className={`subscription-status ${planInfo.subscription_info.status}`}>
                          {planInfo.subscription_info.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="subscription-row">
                        <span className="subscription-label">Subscription ID:</span>
                        <span className="subscription-value">{planInfo.subscription_info.subscription_id}</span>
                      </div>
                      <div className="subscription-row">
                        <span className="subscription-label">Current Period End:</span>
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
          )}

          {/* Actions */}
          <div className="profile-actions">
            <button
              className="action-btn primary"
              onClick={() => navigate('/plans')}
            >
              {planInfo?.plan === 'high' ? 'Manage Subscription' : 'Upgrade Plan'}
            </button>
            <button
              className="action-btn secondary"
              onClick={() => navigate('/app')}
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

