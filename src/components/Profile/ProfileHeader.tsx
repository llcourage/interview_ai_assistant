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
  nextBillingDate
}) => {
  const initials = getInitialsFromEmail(email);
  const planDisplay = plan ? plan.charAt(0).toUpperCase() + plan.slice(1) : 'Free';

  return (
    <section className="profile-header">
      <div className="avatar">
        {initials}
      </div>

      <h1 className="profile-header-title">Account Settings</h1>
      <p className="profile-header-email">{email || 'N/A'}</p>

      <div className="profile-header-badge">
        Active · {planDisplay}
      </div>

      {nextBillingDate && (
        <p className="profile-header-billing">
          Next billing: {formatDate(nextBillingDate)}
        </p>
      )}
    </section>
  );
};

