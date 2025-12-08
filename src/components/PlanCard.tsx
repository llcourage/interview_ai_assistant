import React from 'react';
import './PlanCard.css';

interface PlanCardProps {
  name: string;
  subtitle?: string;
  features?: string | string[];
  price: string;
  billing: string;
  recommended?: boolean;
  loading?: boolean;
  onSelect: () => void;
}

export const PlanCard: React.FC<PlanCardProps> = ({
  name,
  subtitle,
  features,
  price,
  billing,
  recommended = false,
  loading = false,
  onSelect
}) => {
  return (
    <article className="plan-card">
      {/* Recommended label - moved to top right */}
      {recommended && (
        <span className="plan-tag">RECOMMENDED</span>
      )}
      
      {/* Top: Title */}
      <header className="plan-card-header">
        <h3 className="plan-name">{name}</h3>
        {subtitle && (
          <p className="plan-subtitle">{subtitle}</p>
        )}
      </header>

      {/* Middle: Feature description */}
      {features && (
        <div className="plan-features">
          <p className="plan-features-text">
            {Array.isArray(features) ? (
              features.map((line, index) => (
                <React.Fragment key={index}>
                  {line}
                  {index < features.length - 1 && <br />}
                </React.Fragment>
              ))
            ) : (
              features.split('\n').map((line, index, arr) => (
                <React.Fragment key={index}>
                  {line}
                  {index < arr.length - 1 && <br />}
                </React.Fragment>
              ))
            )}
          </p>
        </div>
      )}

      {/* Price area */}
      <div className="plan-price-row">
        <span className="plan-price">{price}</span>
        <span className="plan-billing">{billing}</span>
      </div>

      {/* Bottom button */}
      <footer className="plan-footer">
        <button 
          className="plan-button"
          onClick={onSelect}
          disabled={loading}
        >
          {loading ? 'Processing...' : 'Get Started'}
        </button>
      </footer>
    </article>
  );
};

