import React from 'react';
import './UsageCard.css';

interface UsageCardProps {
  used: number;
  limit: number;
  onRefresh: () => void;
}

const calcPercent = (used: number, limit: number): number => {
  if (limit === -1 || limit === 0) return 0;
  return Math.min(Math.round((used / limit) * 100), 100);
};

export const UsageCard: React.FC<UsageCardProps> = ({
  used,
  limit,
  onRefresh
}) => {
  const percent = calcPercent(used, limit);
  const isUnlimited = limit === -1;

  return (
    <section className="card">
      <div className="card-header-row">
        <h2 className="section-title">Daily Usage</h2>
        <button className="small-button" onClick={onRefresh}>
          Refresh
        </button>
      </div>

      <div className="usage-body">
        <div className="usage-row">
          <span className="usage-text">
            {used} / {isUnlimited ? '∞' : limit} requests today
          </span>
          {!isUnlimited && <span className="usage-percent">{percent}%</span>}
        </div>

        {!isUnlimited && (
          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{ width: `${percent}%` }}
            />
          </div>
        )}

        <p className="helper-text">
          {isUnlimited
            ? 'You have unlimited daily requests.'
            : 'Usage resets every 24 hours. Upgrade to unlock more daily requests.'}
        </p>
      </div>
    </section>
  );
};
















