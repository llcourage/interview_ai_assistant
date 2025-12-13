import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import './Success.css';

export const Success: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const plan = searchParams.get('plan');

  useEffect(() => {
    // Auto redirect to home page after 3 seconds
    const timer = setTimeout(() => {
      navigate('/');
    }, 3000);

    return () => clearTimeout(timer);
  }, [navigate]);

  const getPlanDisplayName = (plan: string | null): string => {
    if (!plan) return 'Plan';
    const names: Record<string, string> = {
      'start': 'Start Plan',
      'normal': 'Weekly Normal Plan',
      'high': 'Monthly Normal Plan',
      'ultra': 'Monthly Ultra Plan',
      'premium': 'Monthly Premium Plan',
      'internal': 'Internal Plan'
    };
    return names[plan] || 'Plan';
  };

  const isStartPlan = plan === 'start';
  const planDisplayName = getPlanDisplayName(plan);

  return (
    <div className="success-page">
      <div className="success-container">
        <div className="success-icon">✅</div>
        <h1>{isStartPlan ? 'Plan Activated!' : 'Payment Successful!'}</h1>
        <p>You have successfully {isStartPlan ? 'activated' : 'subscribed to'} <strong>{planDisplayName}</strong></p>
        <p className="success-note">Redirecting to app...</p>
        <button onClick={() => navigate('/')} className="go-to-app-button">
          Back to Home
        </button>
      </div>
    </div>
  );
};

