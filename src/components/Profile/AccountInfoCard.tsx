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
      <h2 className="section-title">Account Information</h2>

      <div className="info-list">
        <InfoRow
          label="Email Address"
          value={email || 'N/A'}
          icon="📧"
        />
        <InfoRow
          label="Current Plan"
          value={planDisplay}
          pill="billed monthly"
          icon="📋"
        />
      </div>
    </section>
  );
};

interface InfoRowProps {
  label: string;
  value: string;
  icon: string;
  pill?: string;
}

const InfoRow: React.FC<InfoRowProps> = ({ label, value, icon, pill }) => {
  return (
    <div className="info-row">
      <div className="info-icon">{icon}</div>
      <div className="info-content">
        <div className="info-label">{label}</div>
        <div className="info-value-row">
          <span className="info-value">{value}</span>
          {pill && <span className="info-pill">{pill}</span>}
        </div>
      </div>
    </div>
  );
};

