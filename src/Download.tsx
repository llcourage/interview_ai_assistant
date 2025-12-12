import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from './components/Header';
import { DOWNLOAD_CONFIG } from './constants/download';
import './Download.css';

export const Download: React.FC = () => {
  const navigate = useNavigate();

  const handleDirectDownload = () => {
    // Open Microsoft Store link
    window.open(DOWNLOAD_CONFIG.windows.url, '_blank');
  };

  return (
    <div className="download-page">
      <Header />
      
      <main className="download-main">
        <div className="download-container">
          <h1 className="download-title">Download Desktop AI</h1>
          <p className="download-subtitle">Choose your preferred download method</p>
          
          <div className="download-options">
            <div className="download-option-card" onClick={handleDirectDownload}>
              <div className="download-option-icon">
                <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </div>
              <h3 className="download-option-title">Free Download (Windows)</h3>
              <p className="download-option-description">
                Download the installer directly. Quick and easy setup.
              </p>
              <div className="download-option-badge">Direct Download</div>
            </div>

            <div className="download-option-card coming-soon-card">
              <div className="download-option-icon">
                <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="download-option-title">Free Download (Mac)</h3>
              <p className="download-option-description">
                macOS version is coming soon. Stay tuned for updates!
              </p>
              <div className="download-option-badge coming-soon-badge">Coming Soon</div>
            </div>
          </div>

          <button 
            className="download-back-btn"
            onClick={() => navigate('/')}
          >
            ← Back to Home
          </button>
        </div>
      </main>
    </div>
  );
};

