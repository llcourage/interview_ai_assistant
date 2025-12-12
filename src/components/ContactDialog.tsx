import React from 'react';
import './ContactDialog.css';

interface ContactDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

const ContactDialog: React.FC<ContactDialogProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const contactEmail = 'support@desktopai.org'; // 可以改为实际的联系邮箱

  const handleCopyEmail = () => {
    navigator.clipboard.writeText(contactEmail).then(() => {
      // Show brief success feedback
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
      setTimeout(() => {
        successMsg.remove();
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy email:', err);
    });
  };

  return (
    <div className="contact-dialog-overlay" onClick={onClose}>
      <div className="contact-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="contact-dialog-header">
          <h2>Contact Us</h2>
          <button className="contact-dialog-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="contact-dialog-content">
          <p className="contact-description">
            If you encounter any inappropriate AI-generated content or have other concerns, please contact us:
          </p>
          <div className="contact-email-section">
            <label>Email:</label>
            <div className="contact-email-container">
              <a 
                href={`mailto:${contactEmail}`}
                className="contact-email-link"
              >
                {contactEmail}
              </a>
              <button 
                className="contact-copy-button"
                onClick={handleCopyEmail}
                title="Copy email to clipboard"
              >
                📋
              </button>
            </div>
          </div>
          <div className="contact-note">
            <p>We will review your report and respond as soon as possible.</p>
          </div>
        </div>
        <div className="contact-dialog-footer">
          <button className="contact-dialog-ok" onClick={onClose}>
            OK
          </button>
        </div>
      </div>
    </div>
  );
};

export default ContactDialog;





