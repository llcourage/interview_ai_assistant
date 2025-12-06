import React, { useState, useEffect } from 'react';
import { getAuthHeader } from '../lib/auth';
import { API_BASE_URL } from '../lib/api';
import './QuotaCard.css';

interface PlanInfo {
  monthly_token_limit?: number;
  monthly_tokens_used?: number;
}

export const QuotaCard: React.FC = () => {
  const [planInfo, setPlanInfo] = useState<PlanInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPlanInfo();
    // 每30秒刷新一次配额信息
    const interval = setInterval(loadPlanInfo, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadPlanInfo = async () => {
    try {
      const authHeader = getAuthHeader();
      if (!authHeader) {
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_BASE_URL}/api/plan`, {
        headers: {
          'Authorization': authHeader
        }
      });

      if (!response.ok) {
        setLoading(false);
        return;
      }

      const data = await response.json();
      setPlanInfo({
        monthly_token_limit: data.monthly_token_limit,
        monthly_tokens_used: data.monthly_tokens_used
      });
    } catch (error) {
      console.error('Error loading quota:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !planInfo || !planInfo.monthly_token_limit || planInfo.monthly_token_limit <= 0) {
    return null;
  }

  const usagePercentage = ((planInfo.monthly_tokens_used || 0) / planInfo.monthly_token_limit) * 100;
  const remaining = Math.max(0, planInfo.monthly_token_limit - (planInfo.monthly_tokens_used || 0));
  const isWarning = usagePercentage >= 80;
  const isDanger = usagePercentage >= 90;

  return (
    <div className={`quota-card ${isWarning ? 'quota-card-warning' : ''}`}>
      <div className="quota-card-header">
        <span className="quota-icon">📊</span>
        <span className="quota-title">月度配额</span>
        <span className="quota-percentage">{usagePercentage.toFixed(1)}%</span>
      </div>
      <div className="quota-bar-container">
        <div className={`quota-bar ${isWarning ? 'quota-bar-warning' : ''}`}>
          <div 
            className={`quota-progress ${isDanger ? 'quota-progress-danger' : isWarning ? 'quota-progress-warning' : ''}`}
            style={{ width: `${Math.min(usagePercentage, 100)}%` }}
          />
        </div>
      </div>
      <div className="quota-details">
        <span className="quota-remaining">
          剩余: <strong>{remaining.toLocaleString()}</strong> / {planInfo.monthly_token_limit.toLocaleString()} tokens
        </span>
      </div>
      {isWarning && (
        <div className="quota-warning-text">
          ⚠️ 配额使用率已超过 80%
        </div>
      )}
    </div>
  );
};

