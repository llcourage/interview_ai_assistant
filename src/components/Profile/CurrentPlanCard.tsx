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
  const planDisplay = plan ? plan.charAt(0).toUpperCase() + plan.slice(1) : 'Free';
  const description = getPlanDescription(plan);
  const features = getPlanFeatures(plan);

  return (
    <section className="card plan-card">
      <div className="plan-card-header">
        <h2 className="section-title">Current Plan</h2>
        <div className="plan-badge">{planDisplay}</div>
      </div>

      <p className="plan-description">{description}</p>

      <div className="plan-price-section">
        <span className="plan-price">{price}</span>
        <span className="plan-price-unit">/month</span>
      </div>

      <hr className="plan-divider" />

      <ul className="plan-feature-list">
        {features.map((feature, index) => (
          <li key={index} className="plan-feature-item">
            ✓ {feature}
          </li>
        ))}
      </ul>

      <button className="plan-manage-button" onClick={onManagePlan}>
        Manage Subscription
      </button>
    </section>
  );
};

