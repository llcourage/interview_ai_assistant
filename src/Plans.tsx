import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from './lib/supabase';
import { Header } from './components/Header';
import './Plans.css';

export const Plans: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<string | null>(null);

  const handlePlanSelect = async (plan: 'normal' | 'high') => {
    setLoading(plan);
    
    try {
      // Check if user is logged in
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        // Not logged in, redirect to login page with plan parameter
        navigate(`/login?plan=${plan}&redirect=/checkout`);
        return;
      }

      // Logged in, create Stripe Checkout Session
      const token = session.access_token;
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
        // 尝试获取详细错误信息
        let errorMessage = 'Failed to create checkout session';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
          console.error('Checkout API error:', errorData);
        } catch (e) {
          console.error('Checkout API error (non-JSON):', response.status, response.statusText);
          errorMessage = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url;
      
    } catch (error) {
      console.error('Error creating checkout:', error);
      // If failed, redirect to checkout page
      navigate(`/checkout?plan=${plan}`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="plans-page">
      <Header />
      <div className="plans-container">
        <h1 className="plans-title">Choose Your Plan</h1>
        <p className="plans-subtitle">Select the perfect plan for your needs</p>
        
        <div className="plans-cards">
          {/* Normal Plan */}
          <div className="plan-card featured">
            <div className="plan-badge">Recommended</div>
            <h3 className="plan-name">Normal</h3>
            <p className="plan-description">We provide GPT-4o mini</p>
            <div className="plan-price">$19.99<span className="price-unit">/month</span></div>
            <button
              className="plan-button"
              onClick={() => handlePlanSelect('normal')}
              disabled={loading === 'normal'}
            >
              {loading === 'normal' ? 'Processing...' : 'Get Started'}
            </button>
          </div>

          {/* High Plan */}
          <div className="plan-card">
            <h3 className="plan-name">High</h3>
            <p className="plan-description">We provide GPT-4o</p>
            <div className="plan-price">$49.99<span className="price-unit">/month</span></div>
            <button
              className="plan-button"
              onClick={() => handlePlanSelect('high')}
              disabled={loading === 'high'}
            >
              {loading === 'high' ? 'Processing...' : 'Get Started'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

