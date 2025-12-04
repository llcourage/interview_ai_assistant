import React from 'react';
import './ProfileHeader.css';

interface ProfileHeaderProps {
  email: string | null;
  plan: string | null;
  nextBillingDate?: string | null;
  onManagePlan: () => void;
}

const getInitialsFromEmail = (email: string | null): string => {
  if (!email) return 'U';
  return email.charAt(0).toUpperCase();
};

const formatDate = (dateString: string): string => {
  if (!dateString) return '';
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return dateString;
  }
};

export const ProfileHeader: React.FC<ProfileHeaderProps> = ({
  email,
  plan,
  nextBillingDate,
  onManagePlan
}) => {
  const initials = getInitialsFromEmail(email);
  const planDisplay = plan ? plan.charAt(0).toUpperCase() + plan.slice(1) : 'Free';

  return (
    <section className="summary-bar">
      <div className="summary-bar-left">
        <div className="avatar">
          {initials}
        </div>
        <div className="summary-bar-content">
          <h1 className="summary-title">Account Settings</h1>
          <p className="summary-email">{email || 'N/A'}</p>
          <div className="summary-meta">
            <span className="summary-status">Active · {planDisplay}</span>
            {nextBillingDate && (
              <span className="summary-billing">Next billing: {formatDate(nextBillingDate)}</span>
            )}
          </div>
        </div>
      </div>
      <div className="summary-bar-right">
        <button className="summary-manage-button" onClick={onManagePlan}>
          Manage Subscription
        </button>
      </div>
    </section>
  );
};

