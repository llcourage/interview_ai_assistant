import React from 'react';
import './CurrentPlanCard.css';

interface CurrentPlanCardProps {
  plan: string | null;
  price: string;
  onManagePlan: () => void;
}

const getPlanDescription = (plan: string | null): string => {
  switch (plan) {
    case 'normal':
      return 'Perfect for regular users who need reliable AI assistance for interviews and career development.';
    case 'high':
      return 'Premium plan with unlimited requests, priority support, and advanced AI models for the best experience.';
    default:
      return 'Get started with our free plan. Upgrade anytime to unlock more features.';
  }
};

const getPlanFeatures = (plan: string | null): string[] => {
  switch (plan) {
    case 'normal':
      return [
        'High-quality AI responses',
        '200 daily requests',
        'Standard support',
        'All core features'
      ];
    case 'high':
      return [
        'Premium AI models',
        'Unlimited requests',
        'Priority support',
        'Advanced features',
        'Early access to new features'
      ];
    default:
      return [
        'Basic AI responses',
        'Limited daily requests',
        'Community support'
      ];
  }
};

export const CurrentPlanCard: React.FC<CurrentPlanCardProps> = ({
  plan,
  price,
  onManagePlan
}) => {
  const planDisplay = plan ? plan.toUpperCase() : 'FREE';
  const description = getPlanDescription(plan);
  const features = getPlanFeatures(plan);

  return (
    <section className="card plan-card">
      <h2 className="section-title">Current Plan</h2>

      <div className="plan-main">
        <div className="plan-left">
          <div className="plan-badge">{planDisplay}</div>
          <p className="plan-description">{description}</p>
        </div>

        <div className="plan-right">
          <div className="plan-price">{price}</div>
          <div className="plan-price-sub">Billed monthly</div>
        </div>
      </div>

      <div className="plan-footer">
        <div className="plan-feature-list">
          {features.map((feature, index) => (
            <div key={index} className="plan-feature-item">
              <span className="plan-feature-icon">✓</span>
              <span className="plan-feature-text">{feature}</span>
            </div>
          ))}
        </div>
        <button className="primary-button" onClick={onManagePlan}>
          Manage subscription
        </button>
      </div>
    </section>
  );
};

