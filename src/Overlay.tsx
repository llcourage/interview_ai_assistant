import React, { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/atom-one-dark.css';
import './Overlay.css';

// Session 类型定义
interface SessionData {
  id: string;
  timestamp: number;
  conversations: Array<{
    screenshots: string[];
    response: string;
  }>;
}

const Overlay = () => {
  // 当前 Session ID
  const [currentSessionId] = useState<string>(() => `session_${Date.now()}`);
  
  // Session 数据
  const [screenshots, setScreenshots] = useState<string[]>([]);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<Array<{screenshots: string[], response: string}>>([]);
  
  // UI 状态
  const [status, setStatus] = useState<string>('等待截图...');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isFocusMode, setIsFocusMode] = useState<boolean>(false);
  
  const contentRef = useRef<HTMLDivElement>(null);

  // 💾 保存当前 Session 到 localStorage
  const saveCurrentSession = () => {
    if (conversationHistory.length === 0) return; // 空会话不保存
    
    const sessions: SessionData[] = JSON.parse(localStorage.getItem('sessions') || '[]');
    
    // 查找是否已存在当前 Session
    const existingIndex = sessions.findIndex(s => s.id === currentSessionId);
    
    const sessionData: SessionData = {
      id: currentSessionId,
      timestamp: Date.now(),
      conversations: conversationHistory
    };
    
    if (existingIndex >= 0) {
      sessions[existingIndex] = sessionData;
    } else {
      sessions.push(sessionData);
    }
    
    localStorage.setItem('sessions', JSON.stringify(sessions));
    console.log('💾 Session 已保存:', currentSessionId);
  };

  // 🆕 创建新 Session
  const createNewSession = () => {
    console.log('🆕 创建新 Session');
    
    // 保存当前 Session（如果有对话）
    saveCurrentSession();
    
    // 重新加载页面以创建全新的 Session ID
    window.location.reload();
  };

  // 简化穿透控制：根据专注模式决定是否穿透
  useEffect(() => {
    console.log('🎯 穿透控制模式:', isFocusMode ? '专注模式（不穿透）' : '穿透模式');
    
    if (isFocusMode) {
      // 专注模式：完全不穿透，可以交互
      window.aiShot?.setIgnoreMouseEvents(false);
    } else {
      // 穿透模式：动态检测按钮
      const handleMouseMove = (e: MouseEvent) => {
        const elementUnderMouse = document.elementFromPoint(e.clientX, e.clientY);
        const isOnButton = elementUnderMouse?.tagName === 'BUTTON' || 
                           elementUnderMouse?.closest('button');

        if (isOnButton) {
          window.aiShot?.setIgnoreMouseEvents(false);
        } else {
          window.aiShot?.setIgnoreMouseEvents(true, { forward: true });
        }
      };

      window.addEventListener('mousemove', handleMouseMove);
      
      // 初始状态：穿透
      setTimeout(() => {
        window.aiShot?.setIgnoreMouseEvents(true, { forward: true });
      }, 100);
      
      return () => window.removeEventListener('mousemove', handleMouseMove);
    }
  }, [isFocusMode]);

  // 监听 IPC 事件
  useEffect(() => {
    console.log('Overlay 组件挂载完成，开始监听事件...');

    const handleScreenshotTaken = (imageBase64: string) => {
      console.log('收到截图，添加到列表');
      console.log('图片数据前50字符:', imageBase64.substring(0, 50));
      setScreenshots(prev => [...prev, imageBase64]); // 追加新截图
      setAiResponse(null);
      setStatus(`已捕获 ${screenshots.length + 1} 张截图，按 Ctrl+Enter 发送分析，Ctrl+D 清空`);
    };

    const handleSendScreenshotRequest = async () => {
      if (screenshots.length === 0) {
        setStatus('请先截图 (Ctrl+H)');
        return;
      }
      
      if (isLoading) return;
      
      console.log(`🚀 开始分析 ${screenshots.length} 张截图...`);
      setIsLoading(true);
      setStatus('正在分析图片...');

      try {
        // 移除所有截图的 data URL 前缀
        const base64DataList = screenshots.map(img => 
          img.replace(/^data:image\/\w+;base64,/, '')
        );
        
        // 如果只有一张图，发送字符串；多张图发送数组
        const imageData = base64DataList.length === 1 ? base64DataList[0] : base64DataList;
        
        const response = await fetch('http://127.0.0.1:8000/api/vision_query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ image_base64: imageData }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ 收到 AI 回复:', data);
        
        setAiResponse(data.answer);
        setStatus('');
        
        // 📝 添加到对话历史
        const newConversation = {
          screenshots: [...screenshots],
          response: data.answer
        };
        setConversationHistory(prev => {
          const updated = [...prev, newConversation];
          // 保存到 localStorage
          setTimeout(() => saveCurrentSession(), 100);
          return updated;
        });
        
        // 🚨 分析完成后自动清空截图
        setScreenshots([]);
        console.log('🗑️ 截图已自动清空');
        
      } catch (error) {
        console.error('❌ 分析失败:', error);
        setStatus(`分析失败: ${error}`);
        setAiResponse(`### 出错了\n\n请求后端失败。\n\n错误信息: ${error}`);
      } finally {
        setIsLoading(false);
      }
    };

    if (window.aiShot) {
      window.aiShot.removeListener('screenshot-taken');
      window.aiShot.removeListener('send-screenshot-request');
      window.aiShot.onScreenshotTaken(handleScreenshotTaken);
      window.aiShot.onSendScreenshotRequest(handleSendScreenshotRequest);

      return () => {
        if (window.aiShot && window.aiShot.removeListener) {
          window.aiShot.removeListener('screenshot-taken');
          window.aiShot.removeListener('send-screenshot-request');
        }
      };
    } else {
      console.error('window.aiShot 未定义！IPC 桥接失败。');
      setStatus('IPC 连接失败 (preload 未加载)');
    }
  }, [screenshots, isLoading, saveCurrentSession]);

  // 自动调整高度
  useEffect(() => {
    const updateHeight = () => {
      if (!contentRef.current) return;
      
      const contentHeight = contentRef.current.scrollHeight;
      const screenHeight = window.screen.height;
      const maxHeight = screenHeight * 0.5;
      
      let targetHeight = Math.min(contentHeight + 20, maxHeight);
      targetHeight = Math.max(targetHeight, 80);
      
      if (window.aiShot && window.aiShot.resizeOverlay) {
        window.aiShot.resizeOverlay(targetHeight);
      }
    };

    const t1 = setTimeout(updateHeight, 100);
    const t2 = setTimeout(updateHeight, 300);
    const t3 = setTimeout(updateHeight, 800);
    const t4 = setTimeout(updateHeight, 1500);

    return () => {
      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4);
    };
  }, [screenshots, aiResponse, status, isLoading]);

  // 监听键盘事件（Ctrl+Left/Right 移动窗口，Ctrl+D 删除截图）
  // Ctrl+Up/Down 由全局快捷键处理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;

      let handled = false;
      switch (e.key) {
        case 'ArrowLeft':
          // Ctrl+Left: 向左移动窗口
          window.aiShot?.moveOverlay?.('left', 20);
          handled = true;
          break;
        case 'ArrowRight':
          // Ctrl+Right: 向右移动窗口
          window.aiShot?.moveOverlay?.('right', 20);
          handled = true;
          break;
        case 'd':
        case 'D':
          // Ctrl+D: 删除所有截图
          console.log('🗑️ 清空所有截图');
          setScreenshots([]);
          setAiResponse(null);
          setStatus('截图已清空');
          handled = true;
          break;
        case 's':
        case 'S':
          // Ctrl+S: 切换专注模式
          setIsFocusMode(prev => {
            const newMode = !prev;
            console.log(newMode ? '🔒 专注模式：不透明+可选中' : '👻 穿透模式：透明+穿透');
            setStatus(newMode ? '专注模式已开启' : '穿透模式已开启');
            setTimeout(() => setStatus(''), 2000);
            return newMode;
          });
          handled = true;
          break;
        case 'n':
        case 'N':
          // Ctrl+N: 创建新 Session
          createNewSession();
          handled = true;
          break;
      }

      if (handled) {
        e.preventDefault();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [createNewSession]);

  return (
    <div 
      className="overlay" 
      tabIndex={0}
      style={{ 
        outline: 'none',
        minHeight: '80px', 
        display: 'flex', 
        flexDirection: 'column',
        width: '100%',
        // 🚨 根据专注模式调整透明度
        background: isFocusMode ? 'rgba(0, 0, 0, 0.85)' : 'rgba(0, 0, 0, 0.15)',
        color: '#ffffff',
        borderRadius: '0 0 12px 12px',
        position: 'relative',
        zIndex: 1,
        transition: 'background 0.3s ease'
      }}
    >
      <div ref={contentRef} style={{ width: '100%', display: 'flex', flexDirection: 'column', flex: 1 }}>
        {/* 快捷键栏 */}
        <div className="overlay-shortcuts-bar">
          <div className="shortcut-hint">
            <kbd>Ctrl+H</kbd> 截图
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+Enter</kbd> 分析
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+N</kbd> 新会话
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+B</kbd> 隐藏/显示
          </div>
        </div>

        {/* 内容区域 */}
        <div className="overlay-content-wrapper">
          <div className="overlay-content">
            {screenshots.length > 0 && (
              <div className="overlay-screenshots">
                <div className="screenshots-label">
                  截图 ({screenshots.length} 张) - <kbd>Ctrl+D</kbd> 清空
                </div>
                <div className="screenshots-grid">
                  {screenshots.map((img, index) => (
                    <div key={index} className="screenshot-item">
                      <img src={img} alt={`Screenshot ${index + 1}`} />
                      <div className="screenshot-number">{index + 1}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {status && (
              <div className="overlay-status">
                <p className="status-text">{status}</p>
              </div>
            )}

            {aiResponse && (
              <div className="overlay-response">
                <div className="response-label">AI 回答：</div>
                <div className="response-text markdown-content">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                  >
                    {aiResponse}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Overlay;
