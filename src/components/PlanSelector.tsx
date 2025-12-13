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
      name: 'Weekly Normal Plan',
      icon: '⚡',
      price: '$9.9/week',
      description: 'Great Model, 1M tokens per week',
      features: [
        'Great Model',
        '1M tokens per week',
        '~2-3 sessions',
        'Vision support (screenshots)'
      ],
      color: '#50C878'
    },
    {
      id: 'high' as PlanType,
      name: 'Monthly Normal Plan',
      icon: '👑',
      price: '$19.9/month',
      description: 'Great Model, 1M tokens per month',
      features: [
        'Great Model',
        '1M tokens per month',
        '~2-3 sessions',
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

