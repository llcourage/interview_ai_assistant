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

  const handlePlanSelect = async (plan: 'start' | 'normal' | 'high') => {
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
            name="Start Plan"
            subtitle="Perfect for getting started"
            features={[
              "GPT-4o-mini Model",
              "100K Tokens Lifetime",
              "No Monthly Reset"
            ]}
            price="One-time"
            billing="Purchase"
            loading={loading === 'start'}
            onSelect={() => handlePlanSelect('start')}
          />

          <PlanCard
            name="Normal Plan"
            features={[
              "GPT-4o-mini Model",
              "500K Tokens per Month"
            ]}            
            price="$19.9"
            billing="/week"
            loading={loading === 'normal'}
            onSelect={() => handlePlanSelect('normal')}
          />

          <PlanCard
            name="High Plan"
            recommended
            features={[
              "GPT-4o Model (Full Version)",
              "Access to gpt-4o-mini",
              "500K Tokens per Month"
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

