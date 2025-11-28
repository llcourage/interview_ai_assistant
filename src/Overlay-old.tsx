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
  const [isMinimized, setIsMinimized] = useState<boolean>(false);
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // 监听 IPC 事件
  useEffect(() => {
    console.log('Overlay 组件挂载完成，开始监听事件...');

    // 1. 监听截图完成
    const handleScreenshotTaken = (imageBase64: string) => {
      console.log('收到截图');
      setScreenshot(imageBase64);
      setAiResponse(null);
      setStatus('截图已捕获，按 Ctrl+Enter 发送分析');
    };

    // 2. 监听开始分析 (Ctrl+Enter)
    // 🚨 修复：之前这里函数名写错了，导致崩溃
    const handleSendScreenshotRequest = async () => {
      // 注意：这里我们依赖最新的 state 可能会有问题 (闭包陷阱)
      // 但因为 useEffect 依赖了 [screenshot]，所以每次截图更新都会重新绑定，是安全的
      
      if (!screenshot) {
        setStatus('请先截图 (Ctrl+H)');
        return;
      }
      
      if (isLoading) return;
      
      console.log('🚀 开始请求后端分析...');
      setIsLoading(true);
      setStatus('正在分析图片...');

      try {
        // 去掉 base64 头部
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
        setStatus(''); // 清空状态文字
        
      } catch (error) {
        console.error('❌ 分析失败:', error);
        setStatus(`分析失败: ${error}`);
        setAiResponse(`### 出错了\n\n请求后端失败。\n\n错误信息: ${error}`);
      } finally {
        setIsLoading(false);
      }
    };

    // 注册监听器 (使用正确的 API 名称)
    if (window.aiShot) {
      // 使用 preload.js 里定义的正确名字
      // 注意：preload.js 的实现是 callback 形式，不需要 removeListener 返回值
      // 但为了防止重复绑定，我们需要清理逻辑
      
      // 由于 preload.js 里的 onScreenshotTaken 实现是 ipcRenderer.on
      // 每次调用都会增加一个 listener。我们需要一种方式来移除。
      // 现在的 preload.js 没有返回 remove 函数，这是一个小缺陷。
      // 但因为我们有 removeListener API，可以用它。
      
      // 先移除旧的，防止重复
      window.aiShot.removeListener('screenshot-taken');
      window.aiShot.removeListener('send-screenshot-request');

      // 绑定新的
      window.aiShot.onScreenshotTaken(handleScreenshotTaken);
      
      // 🚨 关键修复：使用正确的 API 名字 onSendScreenshotRequest
      window.aiShot.onSendScreenshotRequest(handleSendScreenshotRequest);

      return () => {
        // 清理函数
        if (window.aiShot && window.aiShot.removeListener) {
          window.aiShot.removeListener('screenshot-taken');
          window.aiShot.removeListener('send-screenshot-request');
        }
      };
    } else {
      console.error('window.aiShot 未定义！IPC 桥接失败。');
      setStatus('IPC 连接失败 (preload 未加载)');
    }
  }, [screenshot, isLoading]); // 依赖项

  // 自动调整高度
  useEffect(() => {
    const updateHeight = () => {
      if (!contentRef.current) return;
      
      const contentHeight = contentRef.current.scrollHeight;
      const screenHeight = window.screen.height;
      const maxHeight = screenHeight * 0.5; // 最大高度为屏幕的 50%
      
      // 加上 padding，并限制最大高度
      // 注意：如果内容超过 50%，我们希望它是 scrollable 的，但窗口高度只到 50%
      let targetHeight = Math.min(contentHeight + 20, maxHeight);
      
      // 确保至少有快捷键栏的高度
      targetHeight = Math.max(targetHeight, 80);
      
      console.log(`📏 高度调整: 内容=${contentHeight}, 屏幕=${screenHeight}, 目标=${targetHeight}`);
      
      if (window.aiShot && window.aiShot.resizeOverlay) {
        window.aiShot.resizeOverlay(targetHeight);
      }
    };

    // 多次尝试，确保渲染完成 (特别是图片和 Markdown 加载后)
    const t1 = setTimeout(updateHeight, 100);
    const t2 = setTimeout(updateHeight, 300);
    const t3 = setTimeout(updateHeight, 800);
    const t4 = setTimeout(updateHeight, 1500); // 最后一次兜底

    return () => {
      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4);
    };
  }, [screenshot, aiResponse, status, isLoading]);

  // 监听键盘事件 (本地快捷键)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      console.log('按键触发:', e.key, 'Ctrl:', e.ctrlKey, 'Alt:', e.altKey);
      
      // 只有当按住 Ctrl 时才生效 (防止误触)
      if (!e.ctrlKey) return; // 必须按 Ctrl

      let handled = false;
      switch (e.key) {
        case 'ArrowUp':
          console.log('尝试向上移动');
          window.aiShot?.moveOverlay?.('up', 20);
          handled = true;
          break;
        case 'ArrowDown':
          console.log('尝试向下移动');
          window.aiShot?.moveOverlay?.('down', 20);
          handled = true;
          break;
        case 'ArrowLeft':
          console.log('尝试向左移动');
          window.aiShot?.moveOverlay?.('left', 20);
          handled = true;
          break;
        case 'ArrowRight':
          console.log('尝试向右移动');
          window.aiShot?.moveOverlay?.('right', 20);
          handled = true;
          break;
      }

      if (handled) {
        e.preventDefault(); // 防止滚动页面
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 点击时获取焦点
  const handleFocus = () => {
    window.focus();
  };

  // 控制鼠标穿透：鼠标进入按钮区域时，禁用穿透
  const handleMouseEnterButton = () => {
    console.log('🎯 鼠标进入按钮，禁用穿透');
    if (window.aiShot?.setIgnoreMouseEvents) {
      window.aiShot.setIgnoreMouseEvents(false);
      console.log('✅ 穿透已禁用');
    } else {
      console.error('❌ setIgnoreMouseEvents API 不可用');
    }
  };

  // 鼠标离开按钮区域时，启用穿透
  const handleMouseLeaveButton = () => {
    console.log('👋 鼠标离开按钮，启用穿透');
    if (window.aiShot?.setIgnoreMouseEvents) {
      window.aiShot.setIgnoreMouseEvents(true);
      console.log('✅ 穿透已启用');
    } else {
      console.error('❌ setIgnoreMouseEvents API 不可用');
    }
  };

  // 打开主窗口
  const handleOpenMainWindow = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('🔔🔔🔔 设置按钮被点击了！！！');
    console.log('事件类型:', e.type);
    console.log('鼠标位置:', e.clientX, e.clientY);
    
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
      className={`overlay ${isMinimized ? 'minimized' : ''}`} 
      ref={overlayRef}
      tabIndex={0} // 允许获取焦点
      onClick={handleFocus}
      onMouseEnter={handleFocus} // 鼠标移入自动获取焦点
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
      <div ref={contentRef} style={{ width: '100%', display: 'flex', flexDirection: 'column', flex: 1 }}>
        {/* 顶部按钮栏 */}
        <div 
          style={{ position: 'relative', width: '100%' }}
          onMouseEnter={handleMouseEnterButton}
          onMouseLeave={handleMouseLeaveButton}
        >
          {/* 按钮悬停区域（扩大触发范围） */}
          <div
            style={{
              position: 'absolute',
              top: '0',
              right: '0',
              width: '80px',
              height: '80px',
              zIndex: 9998
            }}
            onMouseEnter={handleMouseEnterButton}
          />
          
          {/* 设置按钮（右上角，唯一按钮） */}
          <button
            className="settings-button"
            onMouseEnter={(e) => {
              console.log('🎯 按钮本身的 onMouseEnter 触发');
              handleMouseEnterButton();
            }}
            onMouseLeave={(e) => {
              console.log('👋 按钮本身的 onMouseLeave 触发');
              handleMouseLeaveButton();
            }}
            onMouseDown={(e) => {
              console.log('🖱 按钮 onMouseDown 触发');
            }}
            onClick={handleOpenMainWindow}
            style={{
              position: 'absolute',
              top: '10px',
              right: '10px',
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              border: '2px solid rgba(255,255,255,0.3)',
              background: 'rgba(102, 126, 234, 0.8)',
              color: '#fff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.2rem',
              fontWeight: 'bold',
              zIndex: 9999,
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
            }}
            onMouseOver={(e) => {
              console.log('鼠标悬停在按钮上');
              e.currentTarget.style.background = 'rgba(102, 126, 234, 1)';
              e.currentTarget.style.transform = 'scale(1.1)';
            }}
            onMouseOut={(e) => {
              console.log('鼠标离开按钮');
              e.currentTarget.style.background = 'rgba(102, 126, 234, 0.8)';
              e.currentTarget.style.transform = 'scale(1)';
            }}
            title="打开主程序"
          >
            ⚙
          </button>
        </div>

        {/* 快捷键栏 */}
        <div 
          className="overlay-shortcuts-bar" 
          style={{ 
            display: 'flex', 
            minHeight: '60px',
            background: 'rgba(102, 126, 234, 0.2)',
            padding: '0.8rem 1rem',
            gap: '1rem',
            justifyContent: 'center',
            alignItems: 'center',
            flexShrink: 0
          }}
        >
          <div className="shortcut-hint">
            <kbd>Ctrl+H</kbd> 截图
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+Enter</kbd> {isLoading ? '⏳ 分析中...' : '分析'}
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+B</kbd> 显/隐
          </div>
          <div className="shortcut-hint" style={{ opacity: 0.8, fontSize: '0.8rem' }}>
            <kbd>Ctrl+↕↔</kbd> 移动
          </div>
        </div>

        {/* 内容区域 */}
        <div 
          className="overlay-content-wrapper"
          style={{
            flex: 1,
            overflowY: 'auto', // 允许内容滚动
            padding: (screenshot || aiResponse) ? '1rem' : '0',
            // 当有内容时，显示半透明背景，增加可读性
            background: (screenshot || aiResponse) ? 'rgba(0,0,0,0.6)' : 'transparent'
          }}
        >
          {/* 截图预览 */}
          {screenshot && (
            <div className="screenshot-preview" style={{ marginBottom: '1rem', textAlign: 'center' }}>
              <img src={screenshot} alt="Screenshot" style={{ maxHeight: '200px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)' }} />
            </div>
          )}

          {/* 状态显示 */}
          {status && !aiResponse && (
            <div style={{ textAlign: 'center', color: '#aaa', padding: '10px' }}>
              {status}
            </div>
          )}

          {/* AI 回复 (Markdown) */}
          {aiResponse && (
            <div className="markdown-content" style={{ background: '#1e1e2e', padding: '15px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]} 
                rehypePlugins={[rehypeHighlight]}
              >
                {aiResponse}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Overlay;
