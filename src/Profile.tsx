import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuthHeader, getCurrentUser } from './lib/auth';
import { API_BASE_URL } from './lib/api';
import { TopNav } from './components/Profile/TopNav';
import { ProfileHeader } from './components/Profile/ProfileHeader';
import { QuotaUsageCard } from './components/Profile/QuotaUsageCard';
import './components/Profile/ProfileBase.css';
import './Profile.css';

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
      const authHeader = getAuthHeader();
      
      if (!authHeader) {
        navigate('/login');
        return;
      }

      const user = await getCurrentUser();
      setUserEmail(user?.email || null);
      await loadPlanInfo();
    } catch (err) {
      console.error('Auth check error:', err);
      setError('加载用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const loadPlanInfo = async () => {
    try {
      setError(null);
      const authHeader = getAuthHeader();
      if (!authHeader) return;
      
      console.log('🔍 Loading plan info from:', `${API_BASE_URL}/api/plan`);
      const response = await fetch(`${API_BASE_URL}/api/plan`, {
        headers: {
          'Authorization': authHeader
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

  const handleManagePlan = () => {
    navigate('/plans');
  };

  if (loading) {
    return (
      <div className="page-bg">
        <TopNav />
        <div className="main-container">
          <div className="loading-spinner">⏳ Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-bg">
      <TopNav />

      <div className="main-container">
        <div className="profile-center-wrapper">
          <div className="profile-cards-container">
          <ProfileHeader
            email={userEmail}
            plan={planInfo?.plan || null}
            nextBillingDate={planInfo?.subscription_info?.current_period_end || null}
            onManagePlan={handleManagePlan}
          />
            <QuotaUsageCard
              monthlyTokenLimit={planInfo?.monthly_token_limit}
              monthlyTokensUsed={planInfo?.monthly_tokens_used}
              plan={planInfo?.plan}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
