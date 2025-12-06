import React from 'react';
import './QuotaUsageCard.css';

interface QuotaUsageCardProps {
  monthlyTokenLimit?: number;
  monthlyTokensUsed?: number;
  plan?: string; // 'start', 'normal', 'high'
}

export const QuotaUsageCard: React.FC<QuotaUsageCardProps> = ({
  monthlyTokenLimit,
  monthlyTokensUsed,
  plan
}) => {
  if (!monthlyTokenLimit || monthlyTokenLimit <= 0) {
    return null;
  }

  const used = monthlyTokensUsed || 0;
  const remaining = Math.max(0, monthlyTokenLimit - used);
  const usagePercentage = (used / monthlyTokenLimit) * 100;
  const isWarning = usagePercentage >= 80;
  const isDanger = usagePercentage >= 90;
  const isLifetime = plan === 'start';

  return (
    <div className="quota-card card">
      <h2 className="card-title">
        {isLifetime ? 'Lifetime Token Quota Usage' : 'Monthly Token Quota Usage'}
      </h2>
      
      <div className="quota-usage-content">
        <div className="quota-header">
          <span className="quota-percentage">
            {usagePercentage.toFixed(1)}%
          </span>
        </div>

        <div className="quota-bar-container">
          <div className={`quota-bar ${isWarning ? 'quota-bar-warning' : ''}`}>
            <div 
              className={`quota-progress ${isDanger ? 'quota-progress-danger' : isWarning ? 'quota-progress-warning' : ''}`}
              style={{ 
                width: `${Math.min(usagePercentage, 100)}%` 
              }}
            />
          </div>
        </div>

        <div className="quota-details">
          <div className="quota-detail-item">
            <span className="quota-label">Used:</span>
            <span className="quota-value">{used.toLocaleString()} tokens</span>
          </div>
          <div className="quota-detail-item">
            <span className="quota-label">Remaining:</span>
            <span className="quota-value">{remaining.toLocaleString()} tokens</span>
          </div>
          <div className="quota-detail-item">
            <span className="quota-label">Total:</span>
            <span className="quota-value">{monthlyTokenLimit.toLocaleString()} tokens</span>
          </div>
        </div>

        {isWarning && (
          <div className="quota-warning-banner">
            ⚠️ Your quota usage has exceeded 80%. Remaining quota is limited.
            {!isLifetime && ' Quota will reset monthly.'}
          </div>
        )}
      </div>
    </div>
  );
};

