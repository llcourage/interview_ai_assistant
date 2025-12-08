import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuthHeader, getToken } from './lib/auth';
import { API_BASE_URL } from './lib/api';
import { Header } from './components/Header';
import { PlanCard } from './components/PlanCard';
import './Plans.css';

export const Plans: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<string | null>(null);

  const handlePlanSelect = async (plan: 'start' | 'normal' | 'high' | 'ultra') => {
    setLoading(plan);
    
    try {
      // Check if user is logged in
      const authHeader = getAuthHeader();
      
      if (!authHeader) {
        // Not logged in, redirect to login page with plan parameter
        navigate(`/login?plan=${plan}&redirect=/checkout`);
        return;
      }

      // Logged in, create Stripe Checkout Session
      const token = getToken();
      if (!token) {
        navigate(`/login?plan=${plan}&redirect=/checkout`);
        return;
      }
      
      const response = await fetch(`${API_BASE_URL}/api/plan/checkout`, {
        method: 'POST',
        headers: {
          'Authorization': getAuthHeader() || '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          plan: plan,
          success_url: `${window.location.origin}/success?plan=${plan}`,
          cancel_url: `${window.location.origin}/?canceled=true`
        })
      });

      if (!response.ok) {
        // Try to get detailed error information
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
        {/* Focus gradient glow - make title and card area the visual center */}
        <div className="plans-glow"></div>
        
        <h1 className="plans-title">Choose Your Plan</h1>
        <p className="plans-subtitle">Select the perfect plan for your needs</p>
        
        <div className="plans-grid">
          <PlanCard
            name="Start Plan"
            features={[
              "Great Model",
              "100K Tokens Lifetime",
              "No Weekly Reset"
            ]}
            price="Free"
            billing=""
            loading={loading === 'start'}
            onSelect={() => handlePlanSelect('start')}
          />

          <PlanCard
            name="Normal Plan"
            features={[
              "Great Model",
              "1M Tokens per week"
            ]}            
            price="$19.9"
            billing="/week"
            loading={loading === 'normal'}
            onSelect={() => handlePlanSelect('normal')}
          />

          <PlanCard
            name="High Plan"
            features={[
              "Exceptional Model",
              "1M Tokens per week"
            ]}
            price="$39.9"
            billing="/week"
            loading={loading === 'high'}
            onSelect={() => handlePlanSelect('high')}
          />

          <PlanCard
            name="Ultra Plan"
            recommended
            features={[
              "State of the Art Model",
              "1M Tokens per week",
              "Priority Support"
            ]}
            price="$69.9"
            billing="/week"
            loading={loading === 'ultra'}
            onSelect={() => handlePlanSelect('ultra')}
          />
        </div>
      </div>
    </div>
  );
};

