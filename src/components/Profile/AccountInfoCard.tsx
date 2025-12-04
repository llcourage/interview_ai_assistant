import React from 'react';
import './AccountInfoCard.css';

interface AccountInfoCardProps {
  email: string | null;
  plan: string | null;
}

export const AccountInfoCard: React.FC<AccountInfoCardProps> = ({
  email,
  plan
}) => {
  const planDisplay = plan ? plan.charAt(0).toUpperCase() + plan.slice(1) : 'Free';

  return (
    <section className="card">
      <h2 className="card-title">Account Information</h2>

      <div className="info-list">
        <div className="info-row">
          <div className="info-label">Email Address</div>
          <div className="info-value">{email || 'N/A'}</div>
        </div>
        <div className="info-row">
          <div className="info-label">Current Plan</div>
          <div className="info-value-row">
            <span className="info-value">{planDisplay}</span>
            <span className="info-tag">billed monthly</span>
          </div>
        </div>
      </div>
    </section>
  );
};

