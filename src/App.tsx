import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'
import './App.css'

// 声明全局类型
declare global {
  interface Window {
    aiShot: {
      onScreenshotTaken: (callback: (base64Image: string) => void) => void;
      onSendScreenshotRequest: (callback: (base64Image: string) => void) => void;
      onScreenshotError: (callback: (errorMessage: string) => void) => void;
      captureScreen: () => Promise<string>;
      minimizeOverlay: () => void;
      showOverlay: () => void;
    };
  }
}

function App() {
  const [status, setStatus] = useState<string>('就绪');
  const [lastScreenshot, setLastScreenshot] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false); // 防止重复提交

  useEffect(() => {
    if (window.aiShot) {
      // 监听截图事件
      window.aiShot.onScreenshotTaken((base64Image: string) => {
        setLastScreenshot(base64Image);
        setStatus('截图已捕获');
        setAiResponse('');
        setIsLoading(false);
      });

      // 监听发送截图请求
      window.aiShot.onSendScreenshotRequest((base64Image: string) => {
        // 防止重复提交
        if (isLoading) {
          console.log('正在处理中，忽略重复请求');
          return;
        }
        setStatus('正在分析截图...');
        setIsLoading(true);
        sendToBackend(base64Image);
      });

      // 监听错误
      window.aiShot.onScreenshotError((errorMessage: string) => {
        setStatus(`错误: ${errorMessage}`);
        setIsLoading(false);
      });
    }
  }, [isLoading]);

  const sendToBackend = async (base64Image: string) => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/vision_query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_base64: base64Image,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setAiResponse(data.answer);
      setStatus('分析完成');
    } catch (error) {
      console.error('发送到后端失败:', error);
      setStatus(`错误: ${error instanceof Error ? error.message : '未知错误'}`);
      setAiResponse('无法连接到后端服务，请确保 FastAPI 服务正在运行 (http://127.0.0.1:8000)');
    } finally {
      setIsLoading(false); // 无论成功失败都重置状态
    }
  };

  const handleManualCapture = async () => {
    if (window.aiShot) {
      const base64 = await window.aiShot.captureScreen();
      if (base64) {
        setLastScreenshot(base64);
        setStatus('截图已捕获');
      }
    }
  };

  const handleManualSend = () => {
    if (isLoading) {
      console.log('正在处理中，请稍候');
      return;
    }
    if (lastScreenshot) {
      setStatus('正在分析截图...');
      setIsLoading(true);
      sendToBackend(lastScreenshot);
    } else {
      setStatus('没有截图可发送，请先截图');
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔥 AI 面试助手</h1>
        <p className="subtitle">Windows 桌面版</p>
      </header>

      <main className="app-main">
        <section className="shortcuts-section">
          <h2>⌨️ 全局快捷键</h2>
          <div className="shortcuts">
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>H</kbd>
              <span>截屏（全屏）</span>
            </div>
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>Enter</kbd>
              <span>发送截图到 AI 分析</span>
            </div>
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>B</kbd>
              <span>显示/隐藏悬浮窗</span>
            </div>
          </div>
        </section>

        <section className="status-section">
          <h2>📊 当前状态</h2>
          <div className={`status-indicator ${status.includes('错误') ? 'error' : 'active'}`}>
            {status}
          </div>
        </section>

        <section className="manual-controls">
          <h2>🎮 手动控制</h2>
          <div className="button-group">
            <button onClick={handleManualCapture} className="btn btn-primary">
              📸 手动截图
            </button>
            <button 
              onClick={handleManualSend} 
              className="btn btn-secondary"
              disabled={!lastScreenshot || isLoading}
            >
              {isLoading ? '⏳ 分析中...' : '🚀 发送分析'}
            </button>
          </div>
        </section>

        {lastScreenshot && (
          <section className="preview-section">
            <h2>🖼️ 最新截图</h2>
            <div className="screenshot-preview">
              <img src={`data:image/png;base64,${lastScreenshot}`} alt="Screenshot" />
            </div>
          </section>
        )}

        {aiResponse && (
          <section className="response-section">
            <h2>🤖 AI 分析结果</h2>
            <div className="ai-response markdown-content">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {aiResponse}
              </ReactMarkdown>
            </div>
          </section>
        )}

        <section className="info-section">
          <h2>ℹ️ 使用说明</h2>
          <ol>
            <li>确保后端服务已启动（FastAPI 在 http://127.0.0.1:8000）</li>
            <li>按 <kbd>Ctrl+H</kbd> 进行全屏截图</li>
            <li>截图会显示在悬浮窗中</li>
            <li>按 <kbd>Ctrl+Enter</kbd> 将截图发送给 AI 分析</li>
            <li>查看悬浮窗或主窗口中的 AI 回复</li>
          </ol>
        </section>
      </main>

      <footer className="app-footer">
        <p>💡 悬浮窗永远置顶，方便随时查看</p>
      </footer>
    </div>
  )
}

export default App

