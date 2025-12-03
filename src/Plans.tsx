import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from './lib/supabase';
import { Header } from './components/Header';
import { PlanCard } from './components/PlanCard';
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
        {/* 焦点渐变光 - 让标题和卡片区域成为视觉中心 */}
        <div className="plans-glow"></div>
        
        <h1 className="plans-title">Choose Your Plan</h1>
        <p className="plans-subtitle">Select the perfect plan for your needs</p>
        
        <div className="plans-grid">
          <PlanCard
            name="Normal Plan"
            features={[
              "Great Model",
              "500K Tokens per Week"
            ]}            
            price="$19.9"
            billing="/week"
            loading={loading === 'normal'}
            onSelect={() => handlePlanSelect('normal')}
          />

          <PlanCard
            name="High Plan"
            features={[
              "Premium Model",
              "Advanced Features"
            ]}
            price="$29.9"
            billing="/week"
            loading={loading === 'high'}
            onSelect={() => handlePlanSelect('high')}
          />
        </div>
      </div>
    </div>
  );
};

