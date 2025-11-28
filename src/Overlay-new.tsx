import React, { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/atom-one-dark.css';
import './Overlay.css';

const Overlay = () => {
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('等待截图...');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // 监听 IPC 事件
  useEffect(() => {
    console.log('Overlay 组件挂载完成，开始监听事件...');

    const handleScreenshotTaken = (imageBase64: string) => {
      console.log('收到截图');
      setScreenshot(imageBase64);
      setAiResponse(null);
      setStatus('截图已捕获，按 Ctrl+Enter 发送分析');
    };

    const handleSendScreenshotRequest = async () => {
      if (!screenshot) {
        setStatus('请先截图 (Ctrl+H)');
        return;
      }
      
      if (isLoading) return;
      
      console.log('🚀 开始请求后端分析...');
      setIsLoading(true);
      setStatus('正在分析图片...');

      try {
        const base64Data = screenshot.replace(/^data:image\/\w+;base64,/, '');
        
        const response = await fetch('http://127.0.0.1:8000/api/vision_query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ image_base64: base64Data }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ 收到 AI 回复:', data);
        
        setAiResponse(data.answer);
        setStatus('');
        
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
  }, [screenshot, isLoading]);

  // 自动调整高度
  useEffect(() => {
    const updateHeight = () => {
      if (!contentRef.current) return;
      
      const contentHeight = contentRef.current.scrollHeight;
      const screenHeight = window.screen.height;
      const maxHeight = screenHeight * 0.5;
      
      let targetHeight = Math.min(contentHeight + 20, maxHeight);
      targetHeight = Math.max(targetHeight, 80);
      
      console.log(`📏 高度调整: 内容=${contentHeight}, 目标=${targetHeight}`);
      
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
  }, [screenshot, aiResponse, status, isLoading]);

  // 监听键盘事件
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;

      let handled = false;
      switch (e.key) {
        case 'ArrowUp':
          window.aiShot?.moveOverlay?.('up', 20);
          handled = true;
          break;
        case 'ArrowDown':
          window.aiShot?.moveOverlay?.('down', 20);
          handled = true;
          break;
        case 'ArrowLeft':
          window.aiShot?.moveOverlay?.('left', 20);
          handled = true;
          break;
        case 'ArrowRight':
          window.aiShot?.moveOverlay?.('right', 20);
          handled = true;
          break;
      }

      if (handled) {
        e.preventDefault();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleOpenMainWindow = () => {
    console.log('🔔🔔🔔 设置按钮被点击了！');
    
    if (window.aiShot?.openMainWindow) {
      console.log('✅ 准备调用 openMainWindow API');
      window.aiShot.openMainWindow();
      console.log('✅ openMainWindow 已调用');
    } else {
      console.error('❌ openMainWindow API 不可用');
      console.log('window.aiShot:', window.aiShot);
      alert('API 不可用，请检查控制台');
    }
  };

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
        background: 'transparent', 
        color: '#ffffff',
        borderRadius: '0 0 12px 12px'
      }}
    >
      {/* 🚨 设置按钮 - 独立，固定定位，最高 z-index */}
      <button
        onClick={(e) => {
          console.log('🔔🔔🔔 按钮点击事件触发！');
          e.stopPropagation();
          handleOpenMainWindow();
        }}
        onMouseOver={() => console.log('🎯 鼠标悬停')}
        style={{
          position: 'fixed',
          top: '10px',
          right: '10px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          border: '3px solid white',
          background: 'red', // 🚨 红色便于调试
          color: 'white',
          fontSize: '2rem',
          cursor: 'pointer',
          zIndex: 9999999,
          boxShadow: '0 4px 16px rgba(0,0,0,0.8)',
          
          // 🚨 关键
          pointerEvents: 'auto',
        }}
        title="打开主程序"
      >
        ⚙
      </button>

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
            <kbd>Ctrl+B</kbd> 隐藏/显示
          </div>
        </div>

        {/* 内容区域 */}
        <div className="overlay-content-wrapper">
          <div className="overlay-content">
            {screenshot && (
              <div className="overlay-screenshot">
                <img src={screenshot} alt="Screenshot" />
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

