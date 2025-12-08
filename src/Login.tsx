import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { register, login, loginWithGoogle, isAuthenticated } from './lib/auth';
import { isElectron } from './utils/isElectron';
import './Login.css';

interface LoginProps {
  onLoginSuccess?: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const [showPrivacy, setShowPrivacy] = useState(false);

  // Check if already authenticated, redirect to home
  useEffect(() => {
    const checkAuth = async () => {
      const authenticated = await isAuthenticated();
      if (authenticated) {
        console.log('🔒 Login: Already authenticated, redirecting to home');
        navigate('/', { replace: true });
      }
    };
    checkAuth();
  }, [navigate]);

  // Check URL parameters
  useEffect(() => {
    const mode = searchParams.get('mode');
    const plan = searchParams.get('plan');
    const redirect = searchParams.get('redirect');

    if (mode === 'signup') {
      setIsRegister(true);
      setAcceptedTerms(false);
      setAcceptedPrivacy(false);
      setShowTerms(false);
      setShowPrivacy(false);
    }

    // If plan and redirect exist, save to localStorage
    if (plan && redirect) {
      localStorage.setItem('pendingPlan', plan);
      localStorage.setItem('pendingRedirect', redirect);
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      if (isRegister) {
        // Check if user accepted both terms and privacy policy
        if (!acceptedTerms) {
          setError('Please read and accept the Terms of Use to create an account.');
          setLoading(false);
          return;
        }
        if (!acceptedPrivacy) {
          setError('Please read and accept the Privacy Policy to create an account.');
          setLoading(false);
          return;
        }
        // Register
        await register(email, password);
          setMessage('Registration successful! Signing in...');
          setTimeout(() => {
            handleLoginSuccess();
          }, 1000);
      } else {
        // Login
        const token = await login(email, password);
        console.log('✅ Login successful, token saved:', !!token);
          setMessage('Login successful!');
        
        // Trigger custom event to notify other components that authentication state has changed
        window.dispatchEvent(new CustomEvent('auth-state-changed', { detail: { authenticated: true } }));
        
          setTimeout(() => {
            handleLoginSuccess();
          }, 500);
      }
    } catch (err: any) {
      console.error('Auth error:', err);
      setError(err.message || 'Operation failed. Please check your email and password.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    // Check if there's a pending plan and redirect
    const pendingPlan = localStorage.getItem('pendingPlan');
    const pendingRedirect = localStorage.getItem('pendingRedirect');

    if (pendingPlan && pendingRedirect) {
      // Clear temporary data
      localStorage.removeItem('pendingPlan');
      localStorage.removeItem('pendingRedirect');
      // Navigate to checkout
      navigate(`${pendingRedirect}?plan=${pendingPlan}`);
    } else if (onLoginSuccess) {
      // Use the provided callback
      onLoginSuccess();
    } else {
      // In Electron client, redirect to /app; in web browser, redirect to /profile
      if (isElectron()) {
        navigate('/app');
      } else {
        navigate('/profile');
      }
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setLoading(true);
    try {
      // For Electron: set up event listener before calling loginWithGoogle
      // because token might be saved via IPC event (async)
      if (isElectron()) {
        let authStateChanged = false;
        const handleAuthStateChange = async () => {
          if (authStateChanged) return; // Only handle once
          authStateChanged = true;
          
          // Wait a bit for token to be fully saved
          await new Promise(resolve => setTimeout(resolve, 100));
          
          const authenticated = await isAuthenticated();
          if (authenticated) {
            console.log('✅ Login: Google login successful, navigating to home');
            navigate('/', { replace: true });
            setLoading(false);
            window.removeEventListener('auth-state-changed', handleAuthStateChange);
          } else {
            console.warn('⚠️ Login: Auth state changed but not authenticated');
            setLoading(false);
            window.removeEventListener('auth-state-changed', handleAuthStateChange);
          }
        };
        
        // Listen for auth state change event
        window.addEventListener('auth-state-changed', handleAuthStateChange);
        
        // Set timeout fallback (5 seconds)
        const timeout = setTimeout(() => {
          if (!authStateChanged) {
            console.warn('⚠️ Login: Timeout waiting for auth state change');
            window.removeEventListener('auth-state-changed', handleAuthStateChange);
            // Try to check auth status anyway
            isAuthenticated().then(authenticated => {
              if (authenticated) {
                navigate('/', { replace: true });
              }
              setLoading(false);
            });
          }
        }, 5000);
        
        // Call loginWithGoogle
        await loginWithGoogle();
        
        // If loginWithGoogle resolved immediately (promise path), check auth status
        // The event listener will handle IPC event path
        setTimeout(async () => {
          if (!authStateChanged) {
            const authenticated = await isAuthenticated();
            if (authenticated) {
              authStateChanged = true;
              clearTimeout(timeout);
              window.removeEventListener('auth-state-changed', handleAuthStateChange);
              console.log('✅ Login: Google login successful (promise path), navigating to home');
              navigate('/', { replace: true });
              setLoading(false);
            }
          }
        }, 500);
      } else {
        // Web: user will be redirected to Google OAuth page
        await loginWithGoogle();
        // The redirect will happen in auth.ts, so we don't need to do anything here
      }
    } catch (err: any) {
      console.error('Google login error:', err);
      setError(err.message || 'Failed to initiate Google login');
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>🔥 Desktop AI</h1>
        <h2>{isRegister ? 'Create Account' : 'Welcome Back'}</h2>
        
        {error && <div className="error-message">❌ {error}</div>}
        {message && <div className="success-message">✅ {message}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={loading}
              autoComplete="email"
            />
          </div>
          
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              required
              disabled={loading}
              minLength={6}
              autoComplete={isRegister ? "new-password" : "current-password"}
            />
          </div>
          
          {isRegister && (
            <div className="terms-section">
              <div className="terms-checkbox-container">
                <input
                  type="checkbox"
                  id="terms-checkbox"
                  checked={acceptedTerms}
                  onChange={(e) => setAcceptedTerms(e.target.checked)}
                  disabled={loading}
                />
                <label htmlFor="terms-checkbox" className="terms-label">
                  I have read and agree to the{' '}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      setShowTerms(!showTerms);
                    }}
                    className="terms-link"
                  >
                    Terms of Use
                  </button>
                </label>
              </div>
              <div className="terms-checkbox-container">
                <input
                  type="checkbox"
                  id="privacy-checkbox"
                  checked={acceptedPrivacy}
                  onChange={(e) => setAcceptedPrivacy(e.target.checked)}
                  disabled={loading}
                />
                <label htmlFor="privacy-checkbox" className="terms-label">
                  I have read and agree to the{' '}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      setShowPrivacy(!showPrivacy);
                    }}
                    className="terms-link"
                  >
                    Privacy Policy
                  </button>
                </label>
              </div>
              {showTerms && (
                <div className="terms-modal" onClick={(e) => {
                  if (e.target === e.currentTarget) {
                    setShowTerms(false);
                  }
                }}>
                  <div className="terms-modal-content" onClick={(e) => e.stopPropagation()}>
                    <div className="terms-modal-header">
                      <h3>Desktop AI – Terms of Use</h3>
                      <button
                        type="button"
                        onClick={() => setShowTerms(false)}
                        className="terms-close-btn"
                      >
                        ×
                      </button>
                    </div>
                    <div className="terms-modal-body">
                      <p><strong>Last updated: 2025-12-01</strong></p>
                      <p>By accessing or using Desktop AI ("the Service"), you agree to the following Terms of Use. If you do not agree with these terms, you must not use the Service.</p>

                      <h4>1. Description of the Service</h4>
                      <p>Desktop AI provides AI-powered assistance for tasks such as writing, analysis, brainstorming, and productivity support.</p>
                      <p>The Service generates responses using artificial intelligence models. All outputs are machine-generated and may be inaccurate, incomplete, misleading, or inappropriate in certain contexts.</p>
                      <p>Desktop AI is a tool for assistance only and does not replace human judgment.</p>

                      <h4>2. Disclaimer of Accuracy and Warranties</h4>
                      <p>Desktop AI is provided "as is" and "as available."</p>
                      <p>We make no guarantees regarding the accuracy, reliability, completeness, or correctness of any output.</p>
                      <p>AI-generated content may contain factual errors, outdated information, or unreasonable suggestions.</p>
                      <p>You acknowledge that you use all outputs at your own risk.</p>
                      <p>To the maximum extent permitted by law, Desktop AI disclaims all warranties, express or implied, including but not limited to fitness for a particular purpose and non-infringement.</p>

                      <h4>3. Anti-Cheating and Prohibited Use Policy (IMPORTANT)</h4>
                      <p>You must not use Desktop AI for any activity that violates rules, laws, contracts, or ethical standards, including but not limited to:</p>
                      <ul>
                        <li>Academic cheating (e.g., submitting AI-generated work as your own where prohibited)</li>
                        <li>Exam, interview, or assessment fraud</li>
                        <li>Circumventing employment policies or compliance requirements</li>
                        <li>Impersonation, plagiarism, or misrepresentation</li>
                        <li>Assisting or enabling dishonest, deceptive, or unethical behavior</li>
                      </ul>
                      <p>Desktop AI is intended to support learning and productivity, not to replace personal effort, qualifications, or integrity.</p>
                      <p>You are solely responsible for ensuring that your use of the Service complies with:</p>
                      <ul>
                        <li>School or academic institution policies</li>
                        <li>Employer rules and codes of conduct</li>
                        <li>Laws, regulations, and professional standards</li>
                      </ul>

                      <h4>4. User Responsibility</h4>
                      <p>You acknowledge and agree that:</p>
                      <ul>
                        <li>You are fully responsible for how you use the outputs of Desktop AI.</li>
                        <li>Any decisions, actions, or consequences resulting from the use of the Service are your sole responsibility.</li>
                        <li>Desktop AI does not know your personal context, rules, or constraints.</li>
                        <li>Do not input confidential, sensitive, proprietary, or personal data unless you clearly understand and accept the risks.</li>
                      </ul>

                      <h4>5. Limitation of Liability</h4>
                      <p>To the maximum extent permitted by law:</p>
                      <ul>
                        <li>Desktop AI and its creators shall not be liable for any direct, indirect, incidental, consequential, or special damages</li>
                        <li>This includes, but is not limited to, academic penalties, employment consequences, financial loss, legal issues, or reputational harm</li>
                        <li>Your sole remedy for dissatisfaction with the Service is to stop using it.</li>
                      </ul>

                      <h4>6. Data Usage and Logging</h4>
                      <p>To operate and improve the Service, Desktop AI may collect and store limited usage data and logs, including but not limited to:</p>
                      <ul>
                        <li>Feature usage</li>
                        <li>Error reports</li>
                        <li>Performance metrics</li>
                      </ul>
                      <p>We do not guarantee that AI inputs or outputs will be private or confidential.</p>

                      <h4>7. Changes to These Terms</h4>
                      <p>We may update these Terms of Use from time to time.</p>
                      <p>If material changes are made:</p>
                      <ul>
                        <li>You may be required to re-accept the updated Terms before continuing to use the Service</li>
                        <li>Continued use after updates constitutes acceptance of the new terms</li>
                      </ul>

                      <h4>8. Acceptance</h4>
                      <p>By logging in, accessing, or using Desktop AI, you acknowledge that:</p>
                      <ul>
                        <li>You have read and understood these Terms of Use</li>
                        <li>You agree to be bound by them</li>
                        <li>You accept full responsibility for your use of the Service</li>
                      </ul>
                    </div>
                    <div className="terms-modal-footer">
                      <button
                        type="button"
                        onClick={() => {
                          setAcceptedTerms(true);
                          setShowTerms(false);
                        }}
                        className="terms-accept-btn"
                      >
                        I Accept
                      </button>
                    </div>
                  </div>
                </div>
              )}
              {showPrivacy && (
                <div className="terms-modal" onClick={(e) => {
                  if (e.target === e.currentTarget) {
                    setShowPrivacy(false);
                  }
                }}>
                  <div className="terms-modal-content" onClick={(e) => e.stopPropagation()}>
                    <div className="terms-modal-header">
                      <h3>Desktop AI – Privacy Policy</h3>
                      <button
                        type="button"
                        onClick={() => setShowPrivacy(false)}
                        className="terms-close-btn"
                      >
                        ×
                      </button>
                    </div>
                    <div className="terms-modal-body">
                      <p><strong>Last updated: 2025-12-01</strong></p>
                      <p>Desktop AI ("we", "our", or "the Service") is committed to protecting your privacy. This Privacy Policy explains what data we collect, what we do not collect, and how data is used when you use Desktop AI.</p>

                      <h4>1. Our Privacy Principles</h4>
                      <p>Desktop AI is designed with a privacy-first architecture:</p>
                      <ul>
                        <li>We minimize data collection</li>
                        <li>We do not store user content</li>
                        <li>We collect only what is strictly necessary to operate billing and maintain service reliability</li>
                      </ul>

                      <h4>2. Information We Do Not Collect</h4>
                      <p>Desktop AI does not collect, store, or retain any of the following:</p>
                      <ul>
                        <li>Chat messages or conversation content</li>
                        <li>AI prompts or AI-generated responses</li>
                        <li>Voice recordings or audio input</li>
                        <li>Conversation history</li>
                        <li>Personal profile information or user-provided profile data</li>
                        <li>Files, documents, or screen content</li>
                      </ul>
                      <p>Any content you submit is processed transiently for generating a response and is not persisted by Desktop AI.</p>

                      <h4>3. Information We Do Collect</h4>
                      <p>We collect only minimal, non-content usage data, including:</p>
                      <ul>
                        <li>Usage counts (e.g., number of requests, interactions, or tokens consumed)</li>
                        <li>Feature usage metrics (used solely to enforce plan limits)</li>
                        <li>Subscription and billing-related identifiers</li>
                        <li>Basic operational logs (e.g., request success/failure, latency, error rates)</li>
                      </ul>
                      <p>We do not associate usage data with the actual content of your requests.</p>

                      <h4>4. How We Use Collected Data</h4>
                      <p>The limited data we collect is used only for the following purposes:</p>
                      <ul>
                        <li>Billing and subscription management</li>
                        <li>Enforcing usage limits based on your plan</li>
                        <li>Preventing abuse of the Service</li>
                        <li>Monitoring system performance and reliability</li>
                      </ul>
                      <p>Desktop AI does not:</p>
                      <ul>
                        <li>Sell user data</li>
                        <li>Share user data for advertising</li>
                        <li>Use your data to train AI models</li>
                      </ul>

                      <h4>5. Data Retention</h4>
                      <ul>
                        <li>Content data is not retained because it is not stored</li>
                        <li>Usage and billing data may be retained as long as necessary for:</li>
                        <ul>
                          <li>Subscription management</li>
                          <li>Accounting and legal obligations</li>
                          <li>Resolving billing disputes</li>
                        </ul>
                      </ul>

                      <h4>6. Data Security</h4>
                      <p>We use reasonable technical and organizational measures to protect usage and billing data.</p>
                      <p>However, no online service can guarantee absolute security. By using Desktop AI, you acknowledge and accept this risk.</p>

                      <h4>7. Third-Party Services</h4>
                      <p>Desktop AI may rely on third-party infrastructure providers (e.g., cloud hosting, payment processors) strictly to operate the Service.</p>
                      <p>These providers are only given access to the minimum data required to perform their function and are subject to their own privacy obligations.</p>

                      <h4>8. Your Responsibilities</h4>
                      <p>You are responsible for ensuring that your use of Desktop AI complies with:</p>
                      <ul>
                        <li>Applicable laws and regulations</li>
                        <li>Employer, academic, or organizational privacy rules</li>
                      </ul>
                      <p>Do not submit sensitive or confidential information unless you fully understand the risks.</p>

                      <h4>9. Changes to This Privacy Policy</h4>
                      <p>We may update this Privacy Policy from time to time.</p>
                      <p>If material changes are made, we may require you to review and re-accept the updated policy before continuing to use the Service.</p>

                      <h4>10. Contact</h4>
                      <p>If you have questions or concerns about this Privacy Policy, please discontinue use of the Service.</p>
                    </div>
                    <div className="terms-modal-footer">
                      <button
                        type="button"
                        onClick={() => {
                          setAcceptedPrivacy(true);
                          setShowPrivacy(false);
                        }}
                        className="terms-accept-btn"
                      >
                        I Accept
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? '⏳ Processing...' : (isRegister ? 'Sign Up' : 'Sign In')}
          </button>
        </form>

        <div className="oauth-divider">
          <span>or</span>
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={loading}
          className="google-login-btn"
        >
          <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>
        
        <p className="toggle-mode">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}
          <button 
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError('');
              setMessage('');
              setAcceptedTerms(false);
              setAcceptedPrivacy(false);
              setShowTerms(false);
              setShowPrivacy(false);
            }}
            className="toggle-btn"
            disabled={loading}
          >
            {isRegister ? 'Sign In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  );
};

