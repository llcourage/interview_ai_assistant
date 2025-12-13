import React, { useState, useEffect } from 'react';
import './PlanSelector.css';

export type PlanType = 'normal' | 'high';

interface PlanSelectorProps {
  currentPlan: PlanType;
  onPlanChange: (plan: PlanType) => void;
}

export const PlanSelector: React.FC<PlanSelectorProps> = ({ 
  currentPlan, 
  onPlanChange
}) => {
  const plans = [
    {
      id: 'normal' as PlanType,
      name: 'Normal Plan',
      icon: '⚡',
      price: '$19.9/month',
      description: 'GPT-4o-mini model, 1M tokens per month',
      features: [
        'GPT-4o-mini model',
        '1M tokens per month',
        'Vision support (screenshots)',
        'Fast & affordable'
      ],
      color: '#50C878'
    },
    {
      id: 'high' as PlanType,
      name: 'High Plan',
      icon: '👑',
      price: '$29.9/month',
      description: 'GPT-4o model (full version), 1M tokens per month',
      features: [
        'GPT-4o model (full version)',
        'Access to gpt-4o-mini',
        '1M tokens per month',
        'Vision support (screenshots)'
      ],
      color: '#FFD700'
    }
  ];

  return (
    <div className="plan-selector-container">
      <h2 className="plan-title">Current Plan</h2>
      <p className="plan-subtitle">Your subscription plan information</p>
      
      <div className="plans-grid">
        {plans
          .filter(plan => plan.id === currentPlan) // Only show current plan
          .map(plan => (
          <div 
            key={plan.id}
            className={`plan-card ${currentPlan === plan.id ? 'active' : ''}`}
            style={{ 
              borderColor: plan.color
            }}
          >
            <div className="plan-header">
              <span className="plan-icon">{plan.icon}</span>
              <h3 className="plan-name">{plan.name}</h3>
            </div>
            
            <div className="plan-price">{plan.price}</div>
            <p className="plan-description">{plan.description}</p>
            
            <ul className="plan-features">
              {plan.features.map((feature, idx) => (
                <li key={idx}>
                  <span className="check-icon">✓</span>
                  {feature}
                </li>
              ))}
            </ul>
            
            {currentPlan === plan.id && (
              <div className="plan-badge" style={{ background: plan.color }}>
                Current Plan
              </div>
            )}
          </div>
          ))}
      </div>
    </div>
  );
};

