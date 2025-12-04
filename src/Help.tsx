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
          <h3>Welcome to AI Interview Assistant</h3>
          <p>Learn how to use AI Interview Assistant to solve interview questions quickly and efficiently.</p>
          <h4>Quick Start Guide:</h4>
          <ol>
            <li>Sign up for an account or log in</li>
            <li>Choose a plan that fits your needs</li>
            <li>Take a screenshot of your interview question</li>
            <li>Get instant AI-powered solutions</li>
          </ol>
        </div>
      )
    },
    'plans-pricing': {
      title: 'Plans & Pricing',
      content: (
        <div>
          <h3>Choose the Right Plan for You</h3>
          <p>Understand the differences between our plans and choose the one that fits your needs.</p>
          <h4>Available Plans:</h4>
          <ul>
            <li><strong>Normal Plan:</strong> $19.9/week - GPT-4o-mini model, 500K tokens per month</li>
            <li><strong>High Plan:</strong> $29.9/week - GPT-4o model (full version), access to gpt-4o-mini, 500K tokens per month</li>
          </ul>
          <p>The only difference between the plans is the AI model used. Both plans have the same token limits and features.</p>
        </div>
      )
    },
    'faq': {
      title: 'Frequently Asked Questions',
      content: (
        <div>
          <h3>Common Questions</h3>
          <div className="faq-item">
            <h4>How does AI Interview Assistant work?</h4>
            <p>Simply take a screenshot of your interview question, and our AI will analyze it and provide detailed solutions.</p>
          </div>
          <div className="faq-item">
            <h4>What payment methods do you accept?</h4>
            <p>We accept all major credit cards and process payments securely through Stripe.</p>
          </div>
          <div className="faq-item">
            <h4>Can I cancel my subscription anytime?</h4>
            <p>Yes, you can cancel your subscription at any time. Your access will continue until the end of your billing period.</p>
          </div>
          <div className="faq-item">
            <h4>Is there a free trial?</h4>
            <p>Currently, we don't offer a free trial, but we have a flexible cancellation policy.</p>
          </div>
        </div>
      )
    },
    'contact': {
      title: 'Contact Us',
      content: (
        <div>
          <h3>Get in Touch</h3>
          <p>Have a question or need help? We're here to assist you.</p>
          <div className="contact-info">
            <div className="contact-item">
              <h4>Email Support</h4>
              <p>support@aiinterviewassistant.com</p>
            </div>
            <div className="contact-item">
              <h4>Response Time</h4>
              <p>We typically respond within 24 hours</p>
            </div>
            <div className="contact-item">
              <h4>Business Hours</h4>
              <p>Monday - Friday: 9:00 AM - 6:00 PM (EST)</p>
            </div>
          </div>
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

