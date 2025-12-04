import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { getAuthHeader, getToken } from './lib/auth';
import { API_BASE_URL } from './lib/api';
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
      const authHeader = getAuthHeader();
      
      if (!authHeader) {
        // Not logged in, redirect to login page
        navigate(`/login?plan=${plan}&redirect=/checkout?plan=${plan}`);
        return;
      }

      // Logged in, create Stripe Checkout
      const token = getToken();
      if (token) {
        handleCheckout(token.access_token);
      }
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
      // 调试信息
      console.log('🔍 Checkout Debug Info:');
      console.log('  - API_BASE_URL:', API_BASE_URL);
      console.log('  - Request URL:', `${API_BASE_URL}/api/plan/checkout`);
      console.log('  - Plan:', plan);
      console.log('  - Token present:', !!token);
      
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

      console.log('📡 Response status:', response.status, response.statusText);
      console.log('📡 Response headers:', Object.fromEntries(response.headers.entries()));
      
      if (!response.ok) {
        // 尝试获取详细错误信息
        let errorMessage = 'Failed to create checkout session';
        let errorData = null;
        try {
          const text = await response.text();
          console.error('📡 Response body (text):', text);
          try {
            errorData = JSON.parse(text);
            errorMessage = errorData.detail || errorData.message || errorMessage;
            console.error('Checkout API error (JSON):', errorData);
          } catch (e) {
            errorMessage = text || `Server error: ${response.status} ${response.statusText}`;
            console.error('Checkout API error (non-JSON):', response.status, response.statusText, text);
          }
        } catch (e) {
          console.error('Failed to read response:', e);
          errorMessage = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url;
      
    } catch (err) {
      console.error('Checkout error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to create checkout session. Please try again later.';
      setError(errorMessage);
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

