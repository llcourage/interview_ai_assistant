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

  return (
    <div className="success-page">
      <div className="success-container">
        <div className="success-icon">✅</div>
        <h1>Payment Successful!</h1>
        <p>You have successfully subscribed to <strong>{plan === 'normal' ? 'Normal' : 'High'} Plan</strong></p>
        <p className="success-note">Redirecting to app...</p>
        <button onClick={() => navigate('/')} className="go-to-app-button">
          Back to Home
        </button>
      </div>
    </div>
  );
};

