import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { supabase } from './lib/supabase';
import './Checkout.css';

export const Checkout: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const plan = searchParams.get('plan') as 'normal' | 'high' | null;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!plan) {
      navigate('/');
      return;
    }

    // Check if user is logged in
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        // Not logged in, redirect to login page
        navigate(`/login?plan=${plan}&redirect=/checkout?plan=${plan}`);
        return;
      }

      // Logged in, create Stripe Checkout
      handleCheckout(session.access_token);
    };

    checkAuth();
  }, [plan, navigate]);

  const handleCheckout = async (token: string) => {
    if (!plan) {
      navigate('/');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || window.location.origin;
      
      const response = await fetch(`${API_BASE_URL}/api/plan/checkout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          plan: plan,
          success_url: `${window.location.origin}/success?plan=${plan}`,
          cancel_url: `${window.location.origin}/?canceled=true`
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create checkout session');
      }

      const data = await response.json();
      
      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url;
      
    } catch (err) {
      console.error('Checkout error:', err);
      setError('Failed to create checkout session. Please try again later.');
      setLoading(false);
    }
  };

  if (!plan) {
    return null;
  }

  return (
    <div className="checkout-page">
      <div className="checkout-container">
        {loading ? (
          <div className="checkout-loading">
            <div className="spinner"></div>
            <p>Redirecting to checkout...</p>
          </div>
        ) : error ? (
          <div className="checkout-error">
            <h2>❌ Error</h2>
            <p>{error}</p>
            <button onClick={() => navigate('/')} className="back-button">
              Back to Home
            </button>
          </div>
        ) : (
          <div className="checkout-loading">
            <div className="spinner"></div>
            <p>Preparing checkout...</p>
          </div>
        )}
      </div>
    </div>
  );
};

