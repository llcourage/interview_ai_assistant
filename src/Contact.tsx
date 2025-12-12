import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from './components/Header';
import ContactDialog from './components/ContactDialog';
import './Contact.css';

export const Contact: React.FC = () => {
  const navigate = useNavigate();
  const [showContactDialog, setShowContactDialog] = useState(false);

  return (
    <div className="contact-page">
      <Header />
      <main className="contact-main">
        <div className="contact-container">
          <h1>Contact Us</h1>
          
          <div className="contact-info-card">
            <h2>📧 如有问题，请联系我们</h2>
            <p className="contact-intro">
              If you encounter any inappropriate AI-generated content or have other concerns, 
              please don't hesitate to reach out to us.
            </p>
            
            <div className="contact-email-display">
              <span className="contact-email-label">Email:</span>
              <div className="contact-email-value">
                <a href="mailto:support@desktopai.org" className="contact-email-link">
                  support@desktopai.org
                </a>
                <button 
                  className="contact-copy-btn"
                  onClick={() => {
                    navigator.clipboard.writeText('support@desktopai.org').then(() => {
                      const successMsg = document.createElement('div');
                      successMsg.textContent = '✓ Email copied to clipboard';
                      successMsg.style.cssText = `
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        background: rgba(76, 175, 80, 0.9);
                        color: white;
                        padding: 12px 20px;
                        border-radius: 6px;
                        z-index: 10000;
                        font-size: 14px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                      `;
                      document.body.appendChild(successMsg);
                      setTimeout(() => successMsg.remove(), 2000);
                    }).catch(() => {
                      alert('Failed to copy email');
                    });
                  }}
                  title="Copy email"
                >
                  📋 Copy
                </button>
              </div>
            </div>
            
            <p className="contact-note-text">
              We typically respond within 24-48 hours. For urgent matters regarding inappropriate content, 
              please include "URGENT" in the subject line.
            </p>
          </div>

          <div className="contact-actions">
            <button 
              className="contact-action-btn primary"
              onClick={() => window.location.href = 'mailto:support@desktopai.org'}
            >
              📧 Open Email Client
            </button>
          </div>

          <div className="contact-report-section">
            <h3>🚩 Report Inappropriate Content</h3>
            <p>
              If you encounter AI-generated content that is inappropriate, harmful, or violates our guidelines, 
              please report it using the report button (🚩) that appears when you hover over AI responses in the main app.
            </p>
            <button 
              className="contact-action-btn"
              onClick={() => navigate('/app')}
            >
              Go to Main App
            </button>
          </div>
        </div>
      </main>
      
      <ContactDialog 
        isOpen={showContactDialog} 
        onClose={() => setShowContactDialog(false)} 
      />
    </div>
  );
};

