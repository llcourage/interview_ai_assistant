import React from 'react';
import './ProfileHeader.css';

interface ProfileHeaderProps {
  email: string | null;
  plan: string | null;
  nextBillingDate?: string | null;
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
      month: 'long',
      day: 'numeric'
    });
  } catch {
    return dateString;
  }
};

export const ProfileHeader: React.FC<ProfileHeaderProps> = ({
  email,
  plan,
  nextBillingDate
}) => {
  const initials = getInitialsFromEmail(email);
  const planDisplay = plan ? plan.charAt(0).toUpperCase() + plan.slice(1) : 'Free';

  return (
    <section className="card card-lg profile-header">
      <div className="avatar avatar-lg">
        {initials}
      </div>

      <div className="profile-header-text">
        <h1 className="page-title">Account Settings</h1>
        <p className="subtitle">{email || 'N/A'}</p>

        <div className="profile-header-meta">
          <span className="chip">
            Active · {planDisplay}
          </span>
          {nextBillingDate && (
            <span className="meta-text">
              Next billing: {formatDate(nextBillingDate)}
            </span>
          )}
        </div>
      </div>
    </section>
  );
};

