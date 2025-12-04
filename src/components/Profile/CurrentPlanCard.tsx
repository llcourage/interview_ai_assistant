import React from 'react';
import './CurrentPlanCard.css';

interface CurrentPlanCardProps {
  plan: string | null;
  price: string;
}

const getPlanDescription = (plan: string | null): string => {
  switch (plan) {
    case 'normal':
      return 'Perfect for regular users who need reliable AI assistance. Uses GPT-4o-mini model with 500K tokens per month.';
    case 'high':
      return 'Premium plan with GPT-4o model (full version) and access to gpt-4o-mini. 500K tokens per month.';
    default:
      return 'Get started with our free plan. Upgrade anytime to unlock more features.';
  }
};

const getPlanFeatures = (plan: string | null): string[] => {
  switch (plan) {
    case 'normal':
      return [
        'GPT-4o-mini model',
        '500K tokens per month',
        'All core features',
        'Image analysis'
      ];
    case 'high':
      return [
        'GPT-4o model (full version)',
        'Access to gpt-4o-mini',
        '500K tokens per month',
        'Image analysis'
      ];
    default:
      return [
        'Basic AI responses',
        'Community support',
        'Core features'
      ];
  }
};

export const CurrentPlanCard: React.FC<CurrentPlanCardProps> = ({
  plan,
  price
}) => {
  const planDisplay = plan ? plan.charAt(0).toUpperCase() + plan.slice(1) : 'Free';
  const description = getPlanDescription(plan);
  const features = getPlanFeatures(plan);

  return (
    <section className="card plan-card">
      <div className="plan-card-header">
        <h2 className="card-title">Current Plan</h2>
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
    </section>
  );
};

