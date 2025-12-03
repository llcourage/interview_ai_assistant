import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from './lib/supabase';
import { API_BASE_URL } from './lib/api';
import { TopNav } from './components/Profile/TopNav';
import { ProfileHeader } from './components/Profile/ProfileHeader';
import { AccountInfoCard } from './components/Profile/AccountInfoCard';
import { UsageCard } from './components/Profile/UsageCard';
import { CurrentPlanCard } from './components/Profile/CurrentPlanCard';
import './components/Profile/ProfileBase.css';
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

  const getPlanPrice = (plan: string | null): string => {
    if (!plan) return '$0';
    const priceMap: { [key: string]: string } = {
      'normal': '$19.99',
      'high': '$49.99'
    };
    return priceMap[plan] || '$0';
  };

  const handleRefresh = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (session) {
      setLoading(true);
      await loadPlanInfo(session.access_token);
      setLoading(false);
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
        {/* 1. 顶部 Profile 头部卡片 */}
        <ProfileHeader
          email={userEmail}
          plan={planInfo?.plan || null}
          nextBillingDate={planInfo?.subscription_info?.current_period_end || null}
        />

        {/* 2. 内容区：左右两列 */}
        <div className="two-column-layout">
          {/* 左侧 */}
          <div className="column">
            <AccountInfoCard 
              email={userEmail} 
              plan={planInfo?.plan || null} 
            />
            <UsageCard
              used={planInfo?.daily_requests || 0}
              limit={planInfo?.daily_limit || 0}
              onRefresh={handleRefresh}
            />
          </div>

          {/* 右侧 */}
          <div className="column">
            <CurrentPlanCard
              plan={planInfo?.plan || null}
              price={getPlanPrice(planInfo?.plan || null)}
              onManagePlan={handleManagePlan}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
