import React from 'react';
import { Header } from './components/Header';
import './Landing.css';

export const Landing: React.FC = () => {
  return (
    <div className="landing-page">
      <Header />

      {/* Main Content - Only YouTube Video */}
      <main className="landing-main">
        <section className="hero-section">
          <h2 className="hero-title">Screenshot Instantly, AI Solves Interview Questions</h2>
          <p className="hero-subtitle">Watch this video and get started in 30 seconds</p>
          
          <div className="video-container">
            <iframe
              src="https://www.youtube.com/embed/VIDEO_ID"
              title="AI Interview Assistant Demo"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              className="youtube-embed"
            ></iframe>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="landing-footer">
        <p>© 2024 AI Interview Assistant. All rights reserved.</p>
      </footer>
    </div>
  );
};

