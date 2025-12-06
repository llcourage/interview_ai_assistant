import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'
import './App.css'
import { isAuthenticated, getCurrentUser, logout, getAuthHeader } from './lib/auth'
import { Login } from './Login'
import { PlanSelector, PlanType } from './components/PlanSelector'
import { API_BASE_URL } from './lib/api'
import { ScenarioEditDialog } from './components/ScenarioEditDialog'
import { ScenarioSelector } from './components/ScenarioSelector'
import { SettingsDialog } from './components/SettingsDialog'
import { getCurrentSceneName, getSceneConfig } from './lib/sceneStorage'

// Session 类型定义
interface SessionData {
  id: string;
  timestamp: number;
  conversations: Array<{
    type: 'image' | 'text';
    screenshots?: string[];
    userInput?: string;
    response: string;
  }>;
}

// 扩展 window 类型以包含 aiShot
declare global {
  interface Window {
    aiShot?: {
      userLoggedIn: () => Promise<{ success: boolean }>;
      userLoggedOut: () => Promise<{ success: boolean }>;
      onScenarioSelected: (callback: (data: { sceneId: string; presetId: string; prompt: string }) => void) => void;
      onOpenScenarioEditor: (callback: (data: { mode: 'create' | 'edit'; scenario?: any }) => void) => void;
      notifyScenarioUpdated: () => void;
    };
  }
}

function App() {
  const [authStatus, setAuthStatus] = useState<boolean | null>(null);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionData | null>(null);
  // 🎨 主题状态：'dark' | 'light'
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') || 'dark';
  });
  // 📦 Plan 状态
  const [currentPlan, setCurrentPlan] = useState<PlanType>(() => {
    return (localStorage.getItem('currentPlan') as PlanType) || 'normal';
  });
  const [showPlanSelector, setShowPlanSelector] = useState(false);
  const [showScenarioEditor, setShowScenarioEditor] = useState(false);
  const [scenarioEditorMode, setScenarioEditorMode] = useState<'create' | 'edit'>('create');
  const [editingScenario, setEditingScenario] = useState<any>(null);
  const [currentSceneName, setCurrentSceneName] = useState<string>(getCurrentSceneName());
  const [showScenarioSelector, setShowScenarioSelector] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // 📦 Load Plan info from backend API (sync with web)
  useEffect(() => {
    const loadPlanFromAPI = async () => {
      try {
        const authHeader = getAuthHeader();
        if (!authHeader) return;

        const response = await fetch(`${API_BASE_URL}/api/plan`, {
          headers: {
            'Authorization': authHeader
          }
        });

        if (response.ok) {
          const planData = await response.json();
          if (planData.plan) {
            const newPlan = planData.plan as PlanType;
            setCurrentPlan(newPlan);
            localStorage.setItem('currentPlan', newPlan);
            // Trigger custom event to notify other windows (e.g., overlay) to update plan
            window.dispatchEvent(new CustomEvent('planChanged', { detail: newPlan }));
          }
        }
      } catch (error) {
        console.error('Failed to load plan from API:', error);
        // If API call fails, keep using value from localStorage
      }
    };

    // Load plan immediately after login
    if (authStatus) {
      loadPlanFromAPI();
    }
  }, [authStatus]);

  // 📦 Listen to Plan changes (cross-window and same-window sync)
  useEffect(() => {
    // Listen to localStorage storage events (cross-window sync)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'currentPlan' && e.newValue) {
        const newPlan = e.newValue as PlanType;
        setCurrentPlan(newPlan);
      }
    };

    // Listen to custom planChanged events (same-window sync)
    const handlePlanChange = (e: CustomEvent) => {
      const newPlan = e.detail as PlanType;
      setCurrentPlan(newPlan);
      localStorage.setItem('currentPlan', newPlan);
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('planChanged', handlePlanChange as EventListener);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('planChanged', handlePlanChange as EventListener);
    };
  }, []);

  // 🔒 Check authentication status
  useEffect(() => {
    let isMounted = true;
    let lastAuthStatus: boolean | null = null;
    
      const checkAuth = async () => {
        const authenticated = await isAuthenticated();
        
        if (!isMounted) return;
        
        // Only notify Electron when status changes to avoid duplicate calls
        if (lastAuthStatus !== authenticated) {
          console.log('🔒 Auth status changed:', lastAuthStatus, '->', authenticated);
          lastAuthStatus = authenticated;
          setAuthStatus(authenticated);
        
        // 🔒 If logged in, notify Electron to create overlay window
          if (authenticated && window.aiShot?.userLoggedIn) {
            await window.aiShot.userLoggedIn();
          } else if (!authenticated && window.aiShot?.userLoggedOut) {
            await window.aiShot.userLoggedOut();
          }
        }
      };
    
    checkAuth();
    
    // Listen to authentication state change events (triggered on login/logout)
    const handleAuthStateChange = () => {
      checkAuth();
    };
    window.addEventListener('auth-state-changed', handleAuthStateChange);
    
    // Periodically check authentication status (every 30 seconds to reduce log spam)
    const interval = setInterval(checkAuth, 30000);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
      window.removeEventListener('auth-state-changed', handleAuthStateChange);
    };
  }, []);

  // 🎨 Listen to theme changes
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // 🎨 Toggle theme
  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  // 🎯 Listen to scenario selection events (from menu)
  useEffect(() => {
    if (window.aiShot?.onScenarioSelected) {
      const handleScenarioSelected = (data: { sceneId: string; presetId: string; prompt: string }) => {
        console.log('Scenario selected from menu:', data);
        // Update scene configuration
        const { setCurrentScene } = require('./lib/sceneStorage');
        setCurrentScene(data.sceneId, data.presetId);
        // Update current scene name display
        setCurrentSceneName(getCurrentSceneName());
        // Trigger custom event to notify other components
        window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
      };
      
      window.aiShot.onScenarioSelected(handleScenarioSelected);
      
      return () => {
        // Cleanup if needed
      };
    }
  }, []);

  // 🎯 Listen to scene configuration changes (update scene name display)
  useEffect(() => {
    const handleSceneConfigChange = () => {
      setCurrentSceneName(getCurrentSceneName());
    };
    
    window.addEventListener('sceneConfigChanged', handleSceneConfigChange);
    window.addEventListener('storage', handleSceneConfigChange);
    
    return () => {
      window.removeEventListener('sceneConfigChanged', handleSceneConfigChange);
      window.removeEventListener('storage', handleSceneConfigChange);
    };
  }, []);

  // 🎯 Listen to open scenario editor events (from menu)
  useEffect(() => {
    if (window.aiShot?.onOpenScenarioEditor) {
      const handleOpenScenarioEditor = (data: { mode: 'create' | 'edit'; scenario?: any }) => {
        console.log('Open scenario editor from menu:', data);
        setScenarioEditorMode(data.mode);
        setEditingScenario(data.scenario || null);
        setShowScenarioEditor(true);
      };
      
      window.aiShot.onOpenScenarioEditor(handleOpenScenarioEditor);
      
      return () => {
        // Cleanup if needed
      };
    }
  }, []);

  // 🚪 Logout
  const handleLogout = async () => {
    console.log('Logging out...');
    try {
      await logout();
      console.log('Logout successful');
      setAuthStatus(false);
      
      // 🔒 Notify Electron to close overlay window
      if (window.aiShot?.userLoggedOut) {
        await window.aiShot.userLoggedOut();
      }
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  // Load all Sessions from localStorage
  useEffect(() => {
    const loadSessions = () => {
      try {
        const sessionsData = localStorage.getItem('sessions');
        
        if (sessionsData) {
          const parsed: SessionData[] = JSON.parse(sessionsData);
          
          // Filter out empty sessions (no conversation records)
          const validSessions = parsed.filter(s => 
            s.conversations && s.conversations.length > 0
          );
          
          // Sort by timestamp descending (newest first)
          validSessions.sort((a, b) => b.timestamp - a.timestamp);
          setSessions(validSessions);
        } else {
          setSessions([]);
        }
      } catch (error) {
        console.error('❌ Failed to load Session List:', error);
        setSessions([]);
      }
    };

    // Initial load
    loadSessions();
    
    // Listen to localStorage storage events (cross-window sync)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'sessions') {
        loadSessions();
      }
    };
    window.addEventListener('storage', handleStorageChange);
    
    // Listen to custom events (same-window sync)
    const handleSessionsUpdate = () => {
      loadSessions();
    };
    window.addEventListener('sessionsUpdated', handleSessionsUpdate as EventListener);
    
    // Refresh every 3 seconds to show new sessions in real-time (as fallback)
    const interval = setInterval(loadSessions, 3000);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('sessionsUpdated', handleSessionsUpdate as EventListener);
    };
  }, []);

  // Delete Session
  const deleteSession = (sessionId: string) => {
    const updatedSessions = sessions.filter(s => s.id !== sessionId);
    setSessions(updatedSessions);
    localStorage.setItem('sessions', JSON.stringify(updatedSessions));
    if (selectedSession?.id === sessionId) {
      setSelectedSession(null);
    }
  };

  // Format timestamp
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 🔒 Authentication check - show loading or login page
  if (authStatus === null) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh', 
        fontSize: '1.2rem',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        color: '#333'
      }}>
        <p>⏳ Loading...</p>
      </div>
    );
  }

  if (!authStatus) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh', 
        fontSize: '1.2rem',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        color: '#333'
      }}>
        <div style={{ textAlign: 'center' }}>
          <p>⏳ Loading...</p>
          <p style={{ fontSize: '0.9rem', marginTop: '1rem' }}>
            <a href="/" style={{ color: '#667eea', textDecoration: 'none' }}>Back to Home</a>
          </p>
        </div>
      </div>
    );
  }

  // 🔐 Already logged in, show main app interface
  // Show scenario selector page if requested
  if (showScenarioSelector) {
    return (
      <ScenarioSelector
        onBack={() => setShowScenarioSelector(false)}
        onScenarioSelected={() => {
          setCurrentSceneName(getCurrentSceneName());
        }}
      />
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🔥 Desktop AI</h1>
          <p className="subtitle">Your AI assistant for daily usage, interviews, and productivity</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <button 
              className="theme-toggle" 
              onClick={() => setShowPlanSelector(!showPlanSelector)}
              title="Select Plan"
              style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
            >
              📦 {currentPlan === 'normal' ? 'Normal' : 'High'} Plan
            </button>
            <button 
              className="theme-toggle" 
              onClick={() => setShowScenarioSelector(true)}
              title={`Current Application Scenario: ${currentSceneName}. Click to change.`}
              style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
            >
              🎯 Application Scenario: {currentSceneName}
            </button>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <button 
              className="theme-toggle" 
              onClick={() => setShowSettings(true)}
              title="Settings"
              style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
            >
              ⚙️ Settings
            </button>
            <button 
              className="theme-toggle" 
              onClick={handleLogout}
              title="Logout"
              style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
            >
              🚪 Logout
            </button>
            <button 
              className="theme-toggle" 
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>



      {/* Plan Selector Modal */}
      {showPlanSelector && (
        <div className="modal-overlay" onClick={() => setShowPlanSelector(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <PlanSelector
              currentPlan={currentPlan}
              onPlanChange={(plan) => {
                // Plan switching is disabled in client - users must upgrade through web interface
                console.log('Plan switching is not allowed in client. Please upgrade through web interface.');
              }}
            />
          </div>
        </div>
      )}

      <main className="app-main">
        <div className="sessions-layout">
          {/* Left: Session List */}
          <section className="sessions-list">
            <h2>📚 Session List ({sessions.length})</h2>
            
            {sessions.length === 0 ? (
              <div className="empty-state">
                <p>No session records yet</p>
              </div>
            ) : (
              <div className="session-items">
                {sessions.map(session => (
                  <div
                    key={session.id}
                    className={`session-item ${selectedSession?.id === session.id ? 'active' : ''}`}
                    onClick={() => setSelectedSession(session)}
                  >
                    <div className="session-header">
                      <span className="session-time">
                        {formatTime(session.timestamp)}
                      </span>
                      <button
                        className="delete-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSession(session.id);
                        }}
                        title="Delete session"
                      >
                        🗑️
                      </button>
                    </div>
                    <div className="session-preview">
                      <span className="conversation-count">
                        {session.conversations.length} conversations
                      </span>
                      <span className="screenshot-count">
                        {session.conversations.filter(c => c.type === 'image').length} images
                      </span>
                      <span className="screenshot-count">
                        {session.conversations.filter(c => c.type === 'text').length} messages
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Right: Session Detail */}
          <section className="session-detail">
            {selectedSession ? (
              <>
                <h2>📖 Session Details</h2>
                <div className="session-meta">
                  <p>Time: {formatTime(selectedSession.timestamp)}</p>
                  <p>Conversations: {selectedSession.conversations.length}</p>
                </div>

                <div className="conversations">
                  {selectedSession.conversations.map((conv, index) => (
                    <div key={index} className="conversation-item">
                      <h3>
                        {conv.type === 'image' ? '🖼️' : '💬'} Round {index + 1}
                      </h3>
                      
                      {/* Image Analysis */}
                      {conv.type === 'image' && conv.screenshots && (
                        <div className="screenshots-grid-detail">
                          {conv.screenshots.map((screenshot, idx) => (
                            <div key={idx} className="screenshot-item-detail">
                              <img src={screenshot} alt={`Screenshot ${idx + 1}`} />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* User Text Input */}
                      {conv.type === 'text' && conv.userInput && (
                        <div className="user-input-display">
                          <h4>👤 User:</h4>
                          <p>{conv.userInput}</p>
                        </div>
                      )}

                      {/* AI Response */}
                      <div className="ai-response-detail">
                        <h4>🤖 AI Response:</h4>
                        <div className="markdown-content">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeHighlight]}
                          >
                            {conv.response}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="empty-detail">
                <p>👈 Select a session to view details</p>
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="app-footer">
        <p>💡 Tip: Use <kbd>Ctrl+N</kbd> to create a new session</p>
      </footer>

      {/* Scenario Editor Dialog */}
      {showScenarioEditor && (
        <ScenarioEditDialog
          mode={scenarioEditorMode}
          scenario={editingScenario}
          onClose={() => {
            setShowScenarioEditor(false);
            setEditingScenario(null);
          }}
          onSave={() => {
            setShowScenarioEditor(false);
            setEditingScenario(null);
            // Notify Electron to update menu
            if (window.aiShot?.notifyScenarioUpdated) {
              window.aiShot.notifyScenarioUpdated();
            }
            // Trigger scene configuration update event
            window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
          }}
        />
      )}

      {/* Settings Dialog */}
      {showSettings && (
        <SettingsDialog
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}

export default App

