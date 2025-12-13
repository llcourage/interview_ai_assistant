import React, { useState } from 'react';
import { Header } from './components/Header';
import './Help.css';

type HelpSection = 'getting-started' | 'plans-pricing' | 'faq' | 'contact';

export const Help: React.FC = () => {
  const [activeSection, setActiveSection] = useState<HelpSection>('getting-started');

  const helpContent = {
    'getting-started': {
      title: 'Getting Started',
      content: (
        <div>
          <h3>Welcome to Interview Assistant</h3>
          <p>Your AI-powered assistant for interviews, coding problems, and productivity. Learn how to use Interview Assistant to help with your interviews, technical questions, and more.</p>
          
          <h4>Quick Start Guide:</h4>
          <ol>
            <li><strong>Sign up for an account</strong> - Create a free account or log in to get started</li>
            <li><strong>Choose your plan</strong> - Select the plan that fits your needs (Start Plan is free!)</li>
            <li><strong>Take a screenshot or ask a question</strong> - Capture your interview question or type your query</li>
            <li><strong>Get instant AI-powered solutions</strong> - Receive detailed explanations and solutions</li>
          </ol>

          <h4>Key Features:</h4>
          <ul>
            <li><strong>Image Analysis:</strong> Take screenshots of coding problems, interview questions, or any visual content</li>
            <li><strong>Text Chat:</strong> Ask questions directly and get AI-powered responses</li>
            <li><strong>Multiple AI Models:</strong> Access to state-of-the-art AI models based on your plan</li>
            <li><strong>Token-Based Usage:</strong> Fair usage system with monthly or lifetime token allocation</li>
          </ul>
        </div>
      )
    },
    'plans-pricing': {
      title: 'Plans & Pricing',
      content: (
        <div>
          <h3>Choose the Right Plan for You</h3>
          <p>We offer flexible plans to suit different needs, from beginners to power users.</p>
          
          <div className="plan-pricing-list">
            <div className="plan-pricing-item">
              <h4>Start Plan</h4>
              <p className="plan-price">Free</p>
            </div>

            <div className="plan-pricing-item">
              <h4>Weekly Normal Plan</h4>
              <p className="plan-price">$9.9/week</p>
            </div>

            <div className="plan-pricing-item">
              <h4>Monthly Normal Plan</h4>
              <p className="plan-price">$19.9/month</p>
            </div>

            <div className="plan-pricing-item">
              <h4>Monthly Ultra Plan</h4>
              <p className="plan-price">$39.9/month</p>
            </div>

            <div className="plan-pricing-item">
              <h4>Monthly Premium Plan</h4>
              <p className="plan-price">$69.9/month</p>
            </div>
          </div>

          <p>Visit our <a href="/plans" style={{ color: 'var(--color-primary)', textDecoration: 'none' }}>Plans page</a> to see detailed features and choose the plan that fits your needs.</p>
        </div>
      )
    },
    'faq': {
      title: 'Frequently Asked Questions',
      content: (
        <div>
          <h3>Common Questions</h3>
          
          <div className="faq-item">
            <h4>How does Interview Assistant work?</h4>
            <p>Interview Assistant uses advanced AI models to help you with interviews, coding problems, and technical questions. Simply take a screenshot of your question or type it directly, and our AI will provide detailed explanations and solutions.</p>
          </div>

          <div className="faq-item">
            <h4>What are tokens and how do they work?</h4>
            <p>Tokens are units used to measure AI usage. Each request (both input and output) consumes tokens. Paid plans include 1M tokens per month, which reset every month. The Start Plan includes 100K lifetime tokens with no reset.</p>
          </div>

          <div className="faq-item">
            <h4>Can I change my plan later?</h4>
            <p>Yes! You can upgrade or downgrade your plan at any time. When you upgrade from the Start Plan, your quota will reset. Upgrades/downgrades between paid plans are prorated through Stripe.</p>
          </div>

          <div className="faq-item">
            <h4>What payment methods do you accept?</h4>
            <p>We accept all major credit cards and process payments securely through Stripe. Payments are billed monthly for all paid plans.</p>
          </div>

          <div className="faq-item">
            <h4>Can I cancel my subscription anytime?</h4>
            <p>Yes, you can cancel your subscription at any time. Your access will continue until the end of your current billing period. After cancellation, you can still use the free Start Plan.</p>
          </div>

          <div className="faq-item">
            <h4>What's the difference between the AI models?</h4>
            <p>The models differ in their capabilities and response quality. GPT-4o-mini (Start/Normal) is great for general use, GPT-5-mini (High) offers better quality, and GPT-4o (Ultra) provides the most advanced reasoning and accuracy.</p>
          </div>

          <div className="faq-item">
            <h4>Is there a free plan?</h4>
            <p>Yes! The Start Plan is completely free and includes 100K lifetime tokens. Perfect for trying out the service without any commitment.</p>
          </div>

          <div className="faq-item">
            <h4>How do monthly token resets work?</h4>
            <p>For paid plans, your token quota resets every month on a natural monthly cycle. The Start Plan has a lifetime token allocation that never resets. You can check your token usage in your profile settings.</p>
          </div>
        </div>
      )
    },
    'contact': {
      title: 'Contact Us',
      content: (
        <div>
          <h3>Get in Touch</h3>
          <p>Have a question or need help? We're here to assist you with any questions about Interview Assistant.</p>
          
          <div className="contact-info">
            <div className="contact-item">
              <h4>Email Support</h4>
              <p><a href="mailto:supports@desktopai.org" style={{ color: 'var(--color-primary)', textDecoration: 'none' }}>supports@desktopai.org</a></p>
              <p className="contact-description">Send us an email and we'll get back to you as soon as possible.</p>
            </div>
            
            <div className="contact-item">
              <h4>Response Time</h4>
              <p>We typically respond within 24 hours</p>
              <p className="contact-description">For Monthly Ultra Plan users, priority support ensures faster response times.</p>
            </div>
            
            <div className="contact-item">
              <h4>Business Hours</h4>
              <p>Monday - Friday: 9:00 AM - 6:00 PM (EST)</p>
              <p className="contact-description">We monitor emails during business hours and aim to respond promptly.</p>
            </div>
          </div>

          <h4>Need Help?</h4>
          <p>Before contacting support, check out our FAQ section above - it covers most common questions about plans, features, and usage.</p>
        </div>
      )
    }
  };

  return (
    <div className="help-page">
      <Header />
      <div className="help-container">
        <div className="help-sidebar">
          <h2 className="sidebar-title">Help & Support</h2>
          <nav className="help-nav">
            <button
              className={`help-nav-item ${activeSection === 'getting-started' ? 'active' : ''}`}
              onClick={() => setActiveSection('getting-started')}
            >
              Getting Started
            </button>
            <button
              className={`help-nav-item ${activeSection === 'plans-pricing' ? 'active' : ''}`}
              onClick={() => setActiveSection('plans-pricing')}
            >
              Plans & Pricing
            </button>
            <button
              className={`help-nav-item ${activeSection === 'faq' ? 'active' : ''}`}
              onClick={() => setActiveSection('faq')}
            >
              FAQ
            </button>
            <button
              className={`help-nav-item ${activeSection === 'contact' ? 'active' : ''}`}
              onClick={() => setActiveSection('contact')}
            >
              Contact
            </button>
          </nav>
        </div>
        <div className="help-content">
          <div className="help-content-inner">
            <h1 className="help-content-title">{helpContent[activeSection].title}</h1>
            <div className="help-content-body">
              {helpContent[activeSection].content}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

