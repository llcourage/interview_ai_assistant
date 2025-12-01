import React, { useState, useEffect } from 'react';
import './PlanSelector.css';

export type PlanType = 'starter' | 'normal' | 'high';

interface PlanSelectorProps {
  currentPlan: PlanType;
  onPlanChange: (plan: PlanType) => void;
  customApiKey?: string;
  onApiKeyChange?: (apiKey: string) => void;
}

export const PlanSelector: React.FC<PlanSelectorProps> = ({ 
  currentPlan, 
  onPlanChange,
  customApiKey = '',
  onApiKeyChange
}) => {
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState(customApiKey);

  useEffect(() => {
    setApiKeyInput(customApiKey);
  }, [customApiKey]);

  const plans = [
    {
      id: 'starter' as PlanType,
      name: 'Starter',
      icon: '🚀',
      price: 'Free',
      description: 'Use your own OpenAI API Key',
      features: [
        'Custom API Key',
        'Full GPT-4 access',
        'Pay as you go',
        'Your own usage limits'
      ],
      color: '#4A90E2'
    },
    {
      id: 'normal' as PlanType,
      name: 'Normal',
      icon: '⚡',
      price: 'Included',
      description: 'Powered by GPT-4o Mini',
      features: [
        'GPT-4o Mini included',
        'Vision support (screenshots)',
        'Fast & affordable',
        'No setup needed'
      ],
      color: '#50C878'
    },
    {
      id: 'high' as PlanType,
      name: 'High',
      icon: '👑',
      price: 'Premium',
      description: 'Powered by GPT-4o',
      features: [
        'GPT-4o included',
        'Best quality & vision',
        'Latest model',
        'Advanced reasoning'
      ],
      color: '#FFD700'
    }
  ];

  const handleSaveApiKey = () => {
    if (onApiKeyChange) {
      onApiKeyChange(apiKeyInput);
    }
    setShowApiKeyInput(false);
  };

  return (
    <div className="plan-selector-container">
      <h2 className="plan-title">Choose Your Plan</h2>
      <p className="plan-subtitle">Select the AI model that fits your needs</p>
      
      <div className="plans-grid">
        {plans.map(plan => (
          <div 
            key={plan.id}
            className={`plan-card ${currentPlan === plan.id ? 'active' : ''}`}
            onClick={() => {
              onPlanChange(plan.id);
              if (plan.id === 'starter') {
                setShowApiKeyInput(true);
              } else {
                setShowApiKeyInput(false);
              }
            }}
            style={{ 
              borderColor: currentPlan === plan.id ? plan.color : 'rgba(255, 255, 255, 0.1)'
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

      {/* API Key Input for Starter Plan */}
      {showApiKeyInput && currentPlan === 'starter' && (
        <div className="api-key-config">
          <h3>Configure Your API Key</h3>
          <p className="hint">Enter your OpenAI API Key to use the Starter Plan</p>
          
          <input
            type="text"
            value={apiKeyInput}
            onChange={(e) => setApiKeyInput(e.target.value)}
            placeholder="sk-..."
            className="api-key-input"
          />
          
          <div className="api-key-buttons">
            <button 
              className="btn-secondary"
              onClick={() => setShowApiKeyInput(false)}
            >
              Cancel
            </button>
            <button 
              className="btn-primary"
              onClick={handleSaveApiKey}
              disabled={!apiKeyInput.trim()}
            >
              Save API Key
            </button>
          </div>
        </div>
      )}

      {customApiKey && currentPlan === 'starter' && !showApiKeyInput && (
        <div className="current-api-key">
          <p>
            Current API Key: <code>{customApiKey.substring(0, 8)}...{customApiKey.substring(customApiKey.length - 4)}</code>
            <button 
              className="btn-edit"
              onClick={() => setShowApiKeyInput(true)}
            >
              Edit
            </button>
          </p>
        </div>
      )}
    </div>
  );
};

