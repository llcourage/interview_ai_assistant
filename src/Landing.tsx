import React from 'react';
import { Header } from './components/Header';
import { DOWNLOAD_CONFIG } from './constants/download';
import './Landing.css';

export const Landing: React.FC = () => {
  return (
    <div className="landing-page">
      <Header />

      {/* Main Content - Only YouTube Video */}
      <main className="landing-main">
        <section className="hero-section">
          <h2 className="hero-title">Your AI Assistant for Daily Usage, Interviews, and Productivity</h2>
          <p className="hero-subtitle">Help with daily tasks, interviews, and more - Watch this video and get started in 30 seconds</p>
          
          <div className="video-container">
            <iframe
              src="https://www.youtube.com/embed/61psddHcFsA"
              title="Desktop AI Demo"
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
        <p>© 2024 Desktop AI. All rights reserved.</p>
      </footer>
    </div>
  );
};

