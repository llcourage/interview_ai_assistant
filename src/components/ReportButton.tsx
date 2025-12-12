import React, { useState } from 'react';
import { isElectron } from '../utils/isElectron';
import './ReportButton.css';

interface ReportButtonProps {
  content: string;
  context?: string;
  className?: string;
}

const ReportButton: React.FC<ReportButtonProps> = ({ content, context, className = '' }) => {
  const [isReporting, setIsReporting] = useState(false);
  const [showDialog, setShowDialog] = useState(false);

  const handleReport = async () => {
    if (!window.aiShot?.reportInappropriateContent) {
      console.error('Report feature not available');
      return;
    }

    setIsReporting(true);
    try {
      const result = await window.aiShot.reportInappropriateContent({
        content: content.substring(0, 1000), // Limit content length
        context: context?.substring(0, 500),
        reason: 'User reported inappropriate content'
      });

      if (result.success) {
        setShowDialog(false);
        // Show brief success feedback
        const successMsg = document.createElement('div');
        successMsg.textContent = '✓ Report submitted';
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
      } else {
        alert('Failed to submit report. Please try again.');
      }
    } catch (error) {
      console.error('Report error:', error);
      alert('Failed to submit report. Please try again.');
    } finally {
      setIsReporting(false);
    }
  };

  // Only render in Electron
  if (!isElectron() || !window.aiShot?.reportInappropriateContent) {
    return null;
  }

  return (
    <>
      <button
        className={`report-button ${className}`}
        data-electron="true"
        onClick={(e) => {
          e.stopPropagation();
          setShowDialog(true);
        }}
        title="Report inappropriate content"
        aria-label="Report inappropriate content"
      >
        🚩
      </button>
      
      {showDialog && (
        <div className="report-dialog-overlay" onClick={() => setShowDialog(false)}>
          <div className="report-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Report Inappropriate Content</h3>
            <p>Are you sure you want to report this AI-generated content as inappropriate?</p>
            <div className="report-dialog-actions">
              <button
                className="report-dialog-cancel"
                onClick={() => setShowDialog(false)}
                disabled={isReporting}
              >
                Cancel
              </button>
              <button
                className="report-dialog-submit"
                onClick={handleReport}
                disabled={isReporting}
              >
                {isReporting ? 'Submitting...' : 'Submit Report'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ReportButton;

