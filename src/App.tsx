import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'
import './App.css'

// Session 类型定义
interface SessionData {
  id: string;
  timestamp: number;
  conversations: Array<{
    screenshots: string[];
    response: string;
  }>;
}

function App() {
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionData | null>(null);

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

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔥 AI 面试助手</h1>
        <p className="subtitle">会话历史记录</p>
      </header>

      <main className="app-main">
        <div className="sessions-layout">
          {/* 左侧：Session 列表 */}
          <section className="sessions-list">
            <h2>📚 会话列表 ({sessions.length})</h2>
            
            {sessions.length === 0 ? (
              <div className="empty-state">
                <p>还没有任何会话记录</p>
                <p className="hint">使用悬浮窗开始第一次对话吧！</p>
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
                        title="删除会话"
                      >
                        🗑️
                      </button>
                    </div>
                    <div className="session-preview">
                      <span className="conversation-count">
                        {session.conversations.length} 轮对话
                      </span>
                      <span className="screenshot-count">
                        {session.conversations.reduce((sum, c) => sum + c.screenshots.length, 0)} 张截图
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 右侧：Session 详情 */}
          <section className="session-detail">
            {selectedSession ? (
              <>
                <h2>📖 会话详情</h2>
                <div className="session-meta">
                  <p>时间：{formatTime(selectedSession.timestamp)}</p>
                  <p>对话轮数：{selectedSession.conversations.length}</p>
                </div>

                <div className="conversations">
                  {selectedSession.conversations.map((conv, index) => (
                    <div key={index} className="conversation-item">
                      <h3>🔹 第 {index + 1} 轮对话</h3>
                      
                      {/* 截图 */}
                      <div className="screenshots-grid-detail">
                        {conv.screenshots.map((screenshot, idx) => (
                          <div key={idx} className="screenshot-item-detail">
                            <img src={screenshot} alt={`Screenshot ${idx + 1}`} />
                          </div>
                        ))}
                      </div>

                      {/* AI 回复 */}
                      <div className="ai-response-detail">
                        <h4>🤖 AI 回复：</h4>
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
                <p>👈 选择一个会话查看详情</p>
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="app-footer">
        <p>💡 提示：使用 <kbd>Ctrl+N</kbd> 创建新会话</p>
      </footer>
    </div>
  )
}

export default App

