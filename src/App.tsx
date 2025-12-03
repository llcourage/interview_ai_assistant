import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'
import './App.css'
import { supabase } from './lib/supabase'
import { Login } from './Login'
import { PlanSelector, PlanType } from './components/PlanSelector'
import { Settings } from './components/Settings'
import { API_BASE_URL } from './lib/api'

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
      getApiKey: () => Promise<string | null>;
      saveApiKey: (apiKey: string) => Promise<{ success: boolean; message: string }>;
      deleteApiKey: () => Promise<{ success: boolean; message: string }>;
      onOpenApiKeyDialog: (callback: (data: { action: string; apiKey: string | null }) => void) => void;
      onApiKeyDeleted: (callback: () => void) => void;
    };
  }
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionData | null>(null);
  // 🎨 主题状态：'dark' | 'light'
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') || 'dark';
  });
  // 🔑 API Key 对话框状态
  const [showApiKeyDialog, setShowApiKeyDialog] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [currentApiKey, setCurrentApiKey] = useState<string | null>(null);
  const [apiKeyStatus, setApiKeyStatus] = useState<{ type: 'success' | 'error' | null; message: string }>({ type: null, message: '' });
  // 📦 Plan 状态
  const [currentPlan, setCurrentPlan] = useState<PlanType>(() => {
    return (localStorage.getItem('currentPlan') as PlanType) || 'normal';
  });
  const [showPlanSelector, setShowPlanSelector] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // 📦 从后端 API 加载 Plan 信息（与网页端同步）
  useEffect(() => {
    const loadPlanFromAPI = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) return;

        const response = await fetch(`${API_BASE_URL}/api/plan`, {
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        });

        if (response.ok) {
          const planData = await response.json();
          if (planData.plan) {
            const newPlan = planData.plan as PlanType;
            setCurrentPlan(newPlan);
            localStorage.setItem('currentPlan', newPlan);
            // 触发自定义事件，通知其他窗口（如悬浮窗）更新 plan
            window.dispatchEvent(new CustomEvent('planChanged', { detail: newPlan }));
          }
        }
      } catch (error) {
        console.error('Failed to load plan from API:', error);
        // 如果 API 调用失败，保持使用 localStorage 中的值
      }
    };

    // 登录后立即加载 plan
    if (isAuthenticated) {
      loadPlanFromAPI();
    }

    // 监听 localStorage 的 storage 事件（跨窗口同步）
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'currentPlan' && e.newValue) {
        const newPlan = e.newValue as PlanType;
        setCurrentPlan(newPlan);
      }
    };

    // 监听自定义 planChanged 事件（同窗口同步）
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
  }, [isAuthenticated]);

  // 🔒 检查认证状态
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      console.log('Current session:', session);
      setIsAuthenticated(!!session);
      
      // 🔒 如果已登录，通知 Electron 创建悬浮窗
      if (session && window.aiShot?.userLoggedIn) {
        await window.aiShot.userLoggedIn();
      }
    };
    
    checkAuth();
    
    // 监听认证状态变化
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      console.log('Auth state changed:', _event, session);
      setIsAuthenticated(!!session);
      
      // 🔒 根据认证状态控制悬浮窗
      if (session && window.aiShot?.userLoggedIn) {
        await window.aiShot.userLoggedIn();
      } else if (!session && window.aiShot?.userLoggedOut) {
        await window.aiShot.userLoggedOut();
      }
    });
    
    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // 🎨 监听主题变化
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // 🔑 加载当前 API Key
  useEffect(() => {
    const loadApiKey = async () => {
      if (window.aiShot?.getApiKey) {
        const key = await window.aiShot.getApiKey();
        setCurrentApiKey(key);
      }
    };
    loadApiKey();
  }, []);

  // 🔑 监听打开 API Key 对话框事件
  useEffect(() => {
    if (window.aiShot?.onOpenApiKeyDialog) {
      window.aiShot.onOpenApiKeyDialog((data) => {
        const apiKey = data.apiKey || null;
        setCurrentApiKey(apiKey);
        setApiKeyInput(apiKey || '');
        setShowApiKeyDialog(true);
      });
    }
  }, []);

  // 🔑 监听 API Key 删除事件
  useEffect(() => {
    if (window.aiShot?.onApiKeyDeleted) {
      window.aiShot.onApiKeyDeleted(() => {
        setCurrentApiKey(null);
        setApiKeyInput('');
        setApiKeyStatus({ type: 'success', message: 'API Key deleted' });
        setTimeout(() => {
          setShowApiKeyDialog(false);
          setApiKeyStatus({ type: null, message: '' });
        }, 1500);
      });
    }
  }, []);

  // 🔑 Save API Key
  const handleSaveApiKey = async () => {
    if (!window.aiShot?.saveApiKey) {
      setApiKeyStatus({ type: 'error', message: 'IPC connection failed' });
      return;
    }

    const result = await window.aiShot.saveApiKey(apiKeyInput);
    if (result.success) {
      setCurrentApiKey(apiKeyInput);
      setApiKeyStatus({ type: 'success', message: result.message });
      setTimeout(() => {
        setShowApiKeyDialog(false);
        setApiKeyStatus({ type: null, message: '' });
      }, 1500);
    } else {
      setApiKeyStatus({ type: 'error', message: result.message });
    }
  };

  // 🔑 Delete API Key
  const handleDeleteApiKey = async () => {
    if (!window.aiShot?.deleteApiKey) {
      setApiKeyStatus({ type: 'error', message: 'IPC connection failed' });
      return;
    }

    if (!confirm('Are you sure you want to delete the API Key? You will need to set it again to use AI features.')) {
      return;
    }

    const result = await window.aiShot.deleteApiKey();
    if (result.success) {
      setCurrentApiKey(null);
      setApiKeyInput('');
      setApiKeyStatus({ type: 'success', message: result.message });
      setTimeout(() => {
        setShowApiKeyDialog(false);
        setApiKeyStatus({ type: null, message: '' });
      }, 1500);
    } else {
      setApiKeyStatus({ type: 'error', message: result.message });
    }
  };

  // 🎨 切换主题
  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  // 🚪 退出登录
  const handleLogout = async () => {
    console.log('Logging out...');
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('Logout error:', error);
    } else {
      console.log('Logout successful');
      setIsAuthenticated(false);
      
      // 🔒 通知 Electron 关闭悬浮窗
      if (window.aiShot?.userLoggedOut) {
        await window.aiShot.userLoggedOut();
      }
    }
  };

  // 从 localStorage 加载所有 Session
  useEffect(() => {
    const loadSessions = () => {
      const sessionsData = localStorage.getItem('sessions');
      if (sessionsData) {
        const parsed: SessionData[] = JSON.parse(sessionsData);
        // 按时间倒序排列（最新的在前）
        parsed.sort((a, b) => b.timestamp - a.timestamp);
        setSessions(parsed);
      }
    };

    loadSessions();
    
    // 每秒刷新一次，以便实时显示新的 Session
    const interval = setInterval(loadSessions, 1000);
    return () => clearInterval(interval);
  }, []);

  // 删除 Session
  const deleteSession = (sessionId: string) => {
    const updatedSessions = sessions.filter(s => s.id !== sessionId);
    setSessions(updatedSessions);
    localStorage.setItem('sessions', JSON.stringify(updatedSessions));
    if (selectedSession?.id === sessionId) {
      setSelectedSession(null);
    }
  };

  // 格式化时间
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
  if (isAuthenticated === null) {
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

  if (!isAuthenticated) {
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
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🔥 AI Interview Assistant</h1>
          <p className="subtitle">Session History</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button 
            className="theme-toggle" 
            onClick={() => setShowSettings(!showSettings)}
            title="Settings"
            style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
          >
            ⚙️ Settings
          </button>
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
      </header>

      {/* Settings Modal */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '1000px', width: '90%' }}>
            <button 
              onClick={() => setShowSettings(false)}
              style={{
                position: 'absolute',
                top: '1rem',
                right: '1rem',
                background: 'transparent',
                border: 'none',
                fontSize: '1.5rem',
                cursor: 'pointer',
                color: 'var(--text-secondary)'
              }}
            >
              ✕
            </button>
            <Settings />
          </div>
        </div>
      )}

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
                <p className="hint">Use the overlay window to start your first conversation!</p>
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

      {/* 🔑 API Key 管理对话框 */}
      {showApiKeyDialog && (
        <div className="api-key-dialog-overlay" onClick={() => setShowApiKeyDialog(false)}>
          <div className="api-key-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>API Key 管理</h3>
            
            {/* 当前状态显示 */}
            {currentApiKey ? (
              <div className="api-key-current">
                <div className="api-key-current-label">当前 API Key:</div>
                <div className="api-key-current-value">
                  {currentApiKey.substring(0, 8)}...{currentApiKey.substring(currentApiKey.length - 4)}
                </div>
              </div>
            ) : (
              <div className="api-key-current">
                <div className="api-key-current-label">当前状态:</div>
                <div className="api-key-current-value empty">未设置</div>
              </div>
            )}

            <p className="api-key-hint">
              {currentApiKey ? '编辑或删除你的 OpenAI API Key' : '请输入你的 OpenAI API Key。API Key 将保存在本地配置文件中。'}
            </p>
            
            <input
              type="password"
              className="api-key-input"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="sk-..."
              autoFocus
            />
            
            {apiKeyStatus.type && (
              <div className={`api-key-status ${apiKeyStatus.type}`}>
                {apiKeyStatus.message}
              </div>
            )}
            
            <div className="api-key-dialog-actions">
              <button 
                className="api-key-btn api-key-btn-cancel"
                onClick={() => {
                  setShowApiKeyDialog(false);
                  setApiKeyStatus({ type: null, message: '' });
                }}
              >
                取消
              </button>
              {currentApiKey && (
                <button 
                  className="api-key-btn api-key-btn-delete"
                  onClick={handleDeleteApiKey}
                >
                  删除
                </button>
              )}
              <button 
                className="api-key-btn api-key-btn-save"
                onClick={handleSaveApiKey}
                disabled={!apiKeyInput.trim()}
              >
                {currentApiKey ? '更新' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App

