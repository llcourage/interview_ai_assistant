import React, { useEffect, useState, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/atom-one-dark.css';
import './Overlay.css';

// 🚨 配置：最大保存对话轮数（防止 localStorage 过大）
const MAX_CONVERSATIONS_TO_SAVE = 50;

// Session 类型定义
interface SessionData {
  id: string;
  timestamp: number;
  conversations: Array<{
    type: 'image' | 'text';  // 区分图片分析和文字对话
    screenshots?: string[];   // 图片分析时有截图
    userInput?: string;       // 文字对话时有用户输入
    response: string;
  }>;
}

const Overlay = () => {
  // 当前 Session ID
  const [currentSessionId] = useState<string>(() => `session_${Date.now()}`);
  
  // 📦 Plan 状态
  const [currentPlan, setCurrentPlan] = useState<'starter' | 'normal' | 'high'>(() => {
    return (localStorage.getItem('currentPlan') as 'starter' | 'normal' | 'high') || 'starter';
  });
  
  // 📦 监听 localStorage 中 plan 的变化（与主窗口同步）
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'currentPlan' && e.newValue) {
        setCurrentPlan(e.newValue as 'starter' | 'normal' | 'high');
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // 也监听同窗口内的变化（通过自定义事件）
    const handlePlanChange = (e: CustomEvent) => {
      const newPlan = e.detail as 'starter' | 'normal' | 'high';
      setCurrentPlan(newPlan);
    };
    
    window.addEventListener('planChanged', handlePlanChange as EventListener);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('planChanged', handlePlanChange as EventListener);
    };
  }, []);
  
  // Session 数据
  const [screenshots, setScreenshots] = useState<string[]>([]);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<Array<{
    type: 'image' | 'text';
    screenshots?: string[];
    userInput?: string;
    response: string;
  }>>([]);
  
  // UI 状态
  const [status, setStatus] = useState<string>('Waiting for screenshot...');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isFocusMode, setIsFocusMode] = useState<boolean>(false);
  const [userInput, setUserInput] = useState<string>(''); // 用户输入
  
  // 🎤 录音状态
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingTime, setRecordingTime] = useState<number>(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  const contentRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const conversationEndRef = useRef<HTMLDivElement>(null); // 🚨 新增：对话底部标记

  // 💾 保存当前 Session 到 localStorage
  const saveCurrentSession = useCallback(() => {
    if (conversationHistory.length === 0) return; // 空会话不保存
    
    const sessions: SessionData[] = JSON.parse(localStorage.getItem('sessions') || '[]');
    
    // 查找是否已存在当前 Session
    const existingIndex = sessions.findIndex(s => s.id === currentSessionId);
    
    // 🚨 截断对话历史，只保存最近 N 轮
    const truncatedConversations = conversationHistory.length > MAX_CONVERSATIONS_TO_SAVE
      ? conversationHistory.slice(-MAX_CONVERSATIONS_TO_SAVE)
      : conversationHistory;
    
    const sessionData: SessionData = {
      id: currentSessionId,
      timestamp: Date.now(),
      conversations: truncatedConversations
    };
    
    if (existingIndex >= 0) {
      sessions[existingIndex] = sessionData;
    } else {
      sessions.push(sessionData);
    }
    
    localStorage.setItem('sessions', JSON.stringify(sessions));
    console.log('💾 Session 已保存:', currentSessionId, '对话数量:', truncatedConversations.length);
    if (conversationHistory.length > MAX_CONVERSATIONS_TO_SAVE) {
      console.log(`📊 对话已截断: ${conversationHistory.length} -> ${MAX_CONVERSATIONS_TO_SAVE} 轮`);
    }
  }, [conversationHistory, currentSessionId]);

  // 🆕 创建新 Session
  const createNewSession = () => {
    console.log('🆕 创建新 Session');
    
    // 保存当前 Session（如果有对话）
    saveCurrentSession();
    
    // 重新加载页面以创建全新的 Session ID
    window.location.reload();
  };

  // 🎤 开始录音
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      setStatus('Recording...');
      
      // 开始计时
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
      console.log('🎤 开始录音');
    } catch (error) {
      console.error('❌ 录音失败:', error);
      setStatus('Recording failed, please check microphone permissions');
    }
  }, []);

  // 🎤 停止录音
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      
      setStatus('Recording stopped');
      console.log('🎤 停止录音');
    }
  }, [isRecording]);

  // 🎤 发送录音
  const sendRecording = useCallback(async () => {
    if (audioChunksRef.current.length === 0) {
      setStatus('No recording data');
      return;
    }
    
    if (isLoading) return;
    
    setIsLoading(true);
    setStatus('Transcribing audio...');
    
    try {
      // 合并音频片段
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      
      // 发送到后端进行语音转文字
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', 'zh'); // 中文
      
      const response = await fetch('http://127.0.0.1:8000/api/speech_to_text', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('✅ 语音转文字完成:', data);
      
      if (data.success && data.text) {
        // 将转写的文字作为用户输入
        setUserInput(data.text);
        setStatus('Thinking...');
        
        // 直接发送给 ChatGPT
        const context = conversationHistory.map(conv => {
          if (conv.type === 'image') {
            return `[图片分析]\n${conv.response}`;
          } else {
            return `用户: ${conv.userInput}\nAI: ${conv.response}`;
          }
        }).join('\n\n');
        
        const chatResponse = await fetch('http://127.0.0.1:8000/api/text_chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_input: data.text,
            context: context,
            plan: currentPlan
          }),
        });
        
        if (!chatResponse.ok) {
          throw new Error(`HTTP error! status: ${chatResponse.status}`);
        }
        
        const chatData = await chatResponse.json();
        console.log('✅ 收到 AI 回复:', chatData);
        
        setAiResponse(chatData.answer);
        setIsLoading(false);
        setStatus('Response complete');
        setTimeout(() => setStatus(''), 2000);
        
        // 添加到对话历史
        const newConversation = {
          type: 'text' as const,
          userInput: data.text,
          response: chatData.answer
        };
        setConversationHistory(prev => {
          const updated = [...prev, newConversation];
          setTimeout(() => saveCurrentSession(), 100);
          setTimeout(() => {
            conversationEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
          }, 150);
          return updated;
        });
      } else {
        throw new Error(data.error || '语音转文字失败');
      }
      
      // 清空录音数据
      audioChunksRef.current = [];
      setRecordingTime(0);
      
    } catch (error) {
      console.error('❌ 发送录音失败:', error);
      setStatus(`Send failed: ${error}`);
      setIsLoading(false);
    }
  }, [isLoading, conversationHistory, saveCurrentSession]);

  // 💬 使用指定文本发送对话（用于录音转文字后）
  const handleSendTextInputWithText = useCallback(async (text: string) => {
    if (!text.trim()) return;
    
    if (isLoading) return;
    
    setIsLoading(true);
    setStatus('Thinking...');
    
    try {
      // 构建上下文
      const context = conversationHistory.map(conv => {
        if (conv.type === 'image') {
          return `[图片分析]\n${conv.response}`;
        } else {
          return `用户: ${conv.userInput}\nAI: ${conv.response}`;
        }
      }).join('\n\n');
      
      const response = await fetch('http://127.0.0.1:8000/api/text_chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_input: text,
          context: context,
          plan: currentPlan
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('✅ 收到 AI 回复:', data);
      
      setAiResponse(data.answer);
      setIsLoading(false);
      setStatus('Response complete');
      setTimeout(() => setStatus(''), 2000);
      
      // 添加到对话历史
      const newConversation = {
        type: 'text' as const,
        userInput: text,
        response: data.answer
      };
      setConversationHistory(prev => {
        const updated = [...prev, newConversation];
        setTimeout(() => saveCurrentSession(), 100);
        setTimeout(() => {
          conversationEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 150);
        return updated;
      });
      
    } catch (error) {
      console.error('❌ 对话失败:', error);
      setIsLoading(false);
      setStatus(`Conversation failed: ${error}`);
      setAiResponse(`### 出错了\n\n请求后端失败。\n\n错误信息: ${error}`);
    }
  }, [isLoading, conversationHistory, saveCurrentSession]);

  // 💬 处理文字对话请求
  const handleSendTextInput = useCallback(async () => {
    if (!userInput.trim()) {
      setStatus('Please enter content');
      return;
    }
    
    if (isLoading) return;
    
    console.log(`💬 发送文字对话: ${userInput.substring(0, 50)}...`);
    setIsLoading(true);
    setStatus('Thinking...');
    
    const currentInput = userInput;
    setUserInput(''); // 清空输入框

    try {
      // 🚨 构建完整上下文：包含图片分析和文字对话
      const context = conversationHistory
        .map(conv => {
          if (conv.type === 'image') {
            return `[用户发送了 ${conv.screenshots?.length || 0} 张截图]\nAI: ${conv.response}`;
          } else {
            return `User: ${conv.userInput}\nAI: ${conv.response}`;
          }
        })
        .join('\n\n');
      
      const response = await fetch('http://127.0.0.1:8000/api/text_chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          user_input: currentInput,
          context: context,  // 传递完整上下文
          plan: currentPlan
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ 收到 AI 回复:', data);
      
      setAiResponse(data.answer);
      setIsLoading(false);
      setStatus('Response complete');
      setTimeout(() => setStatus(''), 2000); // 2秒后清空状态
      
      // 📝 添加到对话历史（文字类型）
      const newConversation = {
        type: 'text' as const,
        userInput: currentInput,
        response: data.answer
      };
      setConversationHistory(prev => {
        const updated = [...prev, newConversation];
        // 保存到 localStorage
        setTimeout(() => saveCurrentSession(), 100);
        // 🚨 滚动到底部
        setTimeout(() => {
          conversationEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 150);
        return updated;
      });
      
    } catch (error) {
      console.error('❌ 对话失败:', error);
      setIsLoading(false);
      setStatus(`Conversation failed: ${error}`);
      setAiResponse(`### 出错了\n\n请求后端失败。\n\n错误信息: ${error}`);
      setUserInput(currentInput); // 恢复输入
    }
  }, [userInput, isLoading, conversationHistory, saveCurrentSession]);

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

  // 🎯 监听专注模式和内容变化，自动调整窗口高度
  useEffect(() => {
    const adjustWindowHeight = () => {
      if (!scrollContainerRef.current) {
        return;
      }
      
      const headerHeight = 60; // 快捷键栏
      const footerHeight = isFocusMode ? 120 : 0; // 输入框
      
      // 🚨 新策略：根据"状态"决定高度，而不是测量 DOM
      let contentHeight = 0;
      
      if (aiResponse) {
        // 有 AI 回复：根据模式给不同的默认高度
        const screenHeight = window.screen.height;
        if (isFocusMode) {
          // 专注模式：默认 70% 屏幕高度
          contentHeight = Math.floor(screenHeight * 0.7) - 60 - 120; // 减去 header 和 footer
        } else {
          // 穿透模式：默认 50% 屏幕高度
          contentHeight = Math.floor(screenHeight * 0.5) - 60; // 减去 header
        }
      } else if (isLoading) {
        // 正在加载：给足够空间显示截图 + 状态
        // 如果有截图，按截图数量估算；否则给最小值
        if (screenshots.length > 0) {
          const screenshotRowHeight = 180; // 增加到 180px 每行
          const rows = Math.ceil(screenshots.length / 3);
          contentHeight = rows * screenshotRowHeight + 100; // 截图 + 状态栏
        } else {
          contentHeight = 150; // 只有状态文字时
        }
      } else if (screenshots.length > 0) {
        // 只有截图：根据截图数量估算
        const screenshotRowHeight = 180; // 增加到 180px 每行
        const rows = Math.ceil(screenshots.length / 3); // 假设每行 3 张
        contentHeight = rows * screenshotRowHeight + 80; // 截图 + 提示文字
      } else {
        // 空状态：最小高度
        contentHeight = 40;
      }
      
      let totalDesiredHeight = headerHeight + contentHeight + footerHeight;
      
      console.log(`🎯 调整高度 (专注模式=${isFocusMode}):`);
      console.log(`   - 内容估算: ${contentHeight}px (AI回复=${!!aiResponse}, 加载=${isLoading}, 截图=${screenshots.length})`);
      console.log(`   - 总需高度: ${totalDesiredHeight}px`);
      
      let targetHeight: number;
      
      if (isFocusMode) {
        // 🎯 专注模式：最大 70% 屏幕高度，最小 400
        const screenHeight = window.screen.height;
        const maxHeightFocus = Math.floor(screenHeight * 0.7);
        targetHeight = Math.min(totalDesiredHeight, maxHeightFocus);
        targetHeight = Math.max(targetHeight, 400);
      } else {
        // 🎯 穿透模式：最大 50% 屏幕高度，最小 250
        const screenHeight = window.screen.height;
        const maxHeightNormal = Math.floor(screenHeight * 0.5);
        targetHeight = Math.min(totalDesiredHeight, maxHeightNormal);
        targetHeight = Math.max(targetHeight, 250);
      }
      
      console.log(`   - 最终请求窗口高度: ${targetHeight}px`);
      
      const resizeFn = window.aiShot.resizeOverlay || (window.aiShot as any).adjustHeight;
      
      if (resizeFn) {
        resizeFn(targetHeight);
      }
    };
    
    // 延迟执行，确保 DOM 已更新
    const t1 = setTimeout(adjustWindowHeight, 50);
    const t2 = setTimeout(adjustWindowHeight, 200);
    const t3 = setTimeout(adjustWindowHeight, 500);
    
    return () => {
      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
    };
  }, [isFocusMode, aiResponse, screenshots.length, status, isLoading]);

  // 🎯 监听 IPC 滚动事件 (Ctrl+Up/Down)
  useEffect(() => {
    if (window.aiShot && window.aiShot.onScrollContent) {
      const handleScroll = (direction: 'up' | 'down') => {
        console.log(`🖱️ 收到滚动指令: ${direction}`);
        if (scrollContainerRef.current) {
          const step = 100;
          const currentScroll = scrollContainerRef.current.scrollTop;
          const maxScroll = scrollContainerRef.current.scrollHeight - scrollContainerRef.current.clientHeight;
          
          console.log(`   当前状态: scrollTop=${currentScroll}, maxScroll=${maxScroll}, clientHeight=${scrollContainerRef.current.clientHeight}, scrollHeight=${scrollContainerRef.current.scrollHeight}`);
          
          const newScroll = direction === 'up' ? currentScroll - step : currentScroll + step;
          
          scrollContainerRef.current.scrollTo({
            top: newScroll,
            behavior: 'auto'
          });
          console.log(`   执行滚动: ${currentScroll} -> ${newScroll}`);
        } else {
          console.warn('⚠️ scrollContainerRef.current 不存在');
        }
      };

      window.aiShot.onScrollContent(handleScroll);
    }
  }, []);

  // 监听 IPC 事件
  useEffect(() => {
    console.log('Overlay 组件挂载完成，开始监听事件...');

    const handleScreenshotTaken = (imageBase64: string) => {
      console.log('收到截图，添加到列表');
      console.log('图片数据前50字符:', imageBase64.substring(0, 50));
      setScreenshots(prev => [...prev, imageBase64]); // 追加新截图
      setAiResponse(null);
      setStatus(`Captured ${screenshots.length + 1} screenshot(s), press Ctrl+Enter to analyze, Ctrl+D to clear`);
    };

    // 📸 处理图片分析请求
    const handleSendScreenshotRequest = async () => {
      if (screenshots.length === 0) {
        setStatus('Please take a screenshot first (Ctrl+H)');
        return;
      }
      
      if (isLoading) return;
      
      console.log(`🚀 开始分析 ${screenshots.length} 张截图...`);
      setIsLoading(true);
      setStatus('Analyzing images...');

      try {
        // 移除所有截图的 data URL 前缀
        const base64DataList = screenshots.map(img => 
          img.replace(/^data:image\/\w+;base64,/, '')
        );
        
        console.log(`📷 截图数据长度: ${base64DataList.map(d => d.length).join(', ')}`);
        console.log(`📷 第一张截图前50字符: ${base64DataList[0].substring(0, 50)}`);
        
        // 如果只有一张图，发送字符串；多张图发送数组
        const imageData = base64DataList.length === 1 ? base64DataList[0] : base64DataList;
        
        const response = await fetch('http://127.0.0.1:8000/api/vision_query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            image_base64: imageData,
            plan: currentPlan
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ 收到 AI 回复:', data);
        
        setAiResponse(data.answer);
        setIsLoading(false);
        setStatus('Analysis complete');
        setTimeout(() => setStatus(''), 2000); // 2秒后清空状态
        
        // 📝 添加到对话历史（图片类型）
        const newConversation = {
          type: 'image' as const,
          screenshots: [...screenshots],
          response: data.answer
        };
        setConversationHistory(prev => {
          const updated = [...prev, newConversation];
          // 保存到 localStorage
          setTimeout(() => saveCurrentSession(), 100);
          // 🚨 滚动到底部
          setTimeout(() => {
            conversationEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
          }, 150);
          return updated;
        });
        
        // 🚨 分析完成后自动清空截图
        setScreenshots([]);
        console.log('🗑️ 截图已自动清空');
        
      } catch (error) {
        console.error('❌ 分析失败:', error);
        setIsLoading(false);
        setStatus(`Analysis failed: ${error}`);
        setAiResponse(`### 出错了\n\n请求后端失败。\n\n错误信息: ${error}`);
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
      setStatus('IPC connection failed (preload not loaded)');
    }
  }, [screenshots, isLoading, saveCurrentSession]);


  // 监听键盘事件（Ctrl+Left/Right 移动窗口，Ctrl+D 删除截图）
  // Ctrl+Up/Down 由全局快捷键处理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;

      let handled = false;
      
      switch (e.key.toLowerCase()) {
        case 'arrowleft':
          // Ctrl+Left: 向左移动窗口
          window.aiShot?.moveOverlay?.('left', 20);
          handled = true;
          break;
        case 'arrowright':
          // Ctrl+Right: 向右移动窗口
          window.aiShot?.moveOverlay?.('right', 20);
          handled = true;
          break;
        case 'd':
          // Ctrl+D: 删除所有截图
          console.log('🗑️ 清空所有截图');
          setScreenshots([]);
          setAiResponse(null);
          setStatus('Screenshots cleared');
          handled = true;
          break;
        case 't':
          // 🎤 Ctrl+T: 开始/停止录音
          if (isRecording) {
            stopRecording();
            // 停止后自动发送
            setTimeout(() => {
              sendRecording();
            }, 500);
          } else {
            startRecording();
          }
          handled = true;
          break;
        case 'enter':
          // 🎤 Ctrl+Enter: 如果正在录音，则停止并发送；否则让全局快捷键处理（发送截图）
          if (isRecording) {
            stopRecording();
            setTimeout(() => {
              sendRecording();
            }, 500);
            handled = true;
          }
          // 如果不处理，让全局快捷键处理（发送截图）
          break;
        case 's':
        case 'S':
          // Ctrl+S: 切换专注模式
          setIsFocusMode(prev => {
            const newMode = !prev;
            console.log(newMode ? '🔒 专注模式：不透明+可选中' : '👻 穿透模式：透明+穿透');
            // 🚨 如果正在加载（分析图片/对话），不覆盖状态，只在控制台提示
            if (!isLoading) {
              setStatus(newMode ? 'Focus mode enabled' : 'Transparent mode enabled');
              setTimeout(() => setStatus(''), 2000);
            }
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
  }, [createNewSession, isRecording, isLoading, status, startRecording, stopRecording, sendRecording]);

  return (
    <div 
      className={`overlay ${isFocusMode ? 'focus-mode-active' : ''}`}
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
      <div ref={contentRef} style={{ 
        width: '100%', 
        display: 'flex', 
        flexDirection: 'column', 
        flex: 1,
        overflow: 'hidden' /* 🚨 关键：防止中间层被撑开 */
      }}>
        {/* Shortcut Bar */}
        <div className="overlay-shortcuts-bar">
          <div className="shortcut-hint">
            <kbd>Ctrl+H</kbd> Screenshot
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+Enter</kbd> {isRecording ? 'Send Recording' : 'Analyze'}
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+T</kbd> {isRecording ? 'Stop Recording' : 'Start Recording'}
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+S</kbd> {isFocusMode ? 'Transparent Mode' : 'Focus Mode'}
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+N</kbd> New Session
          </div>
          <div className="shortcut-hint">
            <kbd>Ctrl+B</kbd> Hide/Show
          </div>
        </div>

        {/* 内容区域 */}
        <div ref={scrollContainerRef} className="overlay-content-wrapper">
          <div className="overlay-content">
            {screenshots.length > 0 && (
              <div className="overlay-screenshots">
                <div className="screenshots-label">
                  Screenshot ({screenshots.length}) - <kbd>Ctrl+D</kbd> Clear
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
                <p className="status-text">
                  {status}
                  {isRecording && (
                    <span className="recording-indicator">
                      {' '}🎤 {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, '0')}
                    </span>
                  )}
                </p>
              </div>
            )}

            {/* 显示对话历史 */}
            {conversationHistory.length > 0 && (
              <div 
                className={`conversation-history ${isFocusMode ? 'focus-mode' : 'penetrate-mode'}`}
                style={{ 
                  overflowY: isFocusMode ? 'auto' : 'visible', /* 🚨 穿透模式下不显示滚动条 */
                  paddingRight: isFocusMode ? '0.5rem' : '0' /* 🚨 穿透模式下不留滚动条空间 */
                }}
              >
                {isFocusMode ? (
                  // 🎯 专注模式：显示完整历史
                  <>
                    {conversationHistory.map((conv, index) => (
                      <div key={index} className="conversation-item">
                        {conv.type === 'image' && conv.screenshots && (
                          <div className="conv-screenshots">
                            <div className="screenshots-label">
                              📸 Sent {conv.screenshots.length} screenshot(s)
                            </div>
                          </div>
                        )}
                        {conv.type === 'text' && conv.userInput && (
                          <div className="user-message">
                            <div className="message-label">👤 你：</div>
                            <div className="message-text">{conv.userInput}</div>
                          </div>
                        )}
                        <div className="overlay-response" style={{
                          maxHeight: '60vh', /* 专注模式下限制高度 */
                          overflowY: 'auto' /* 专注模式下可滚动 */
                        }}>
                          <div className="response-label">🤖 AI：</div>
                          <div className="response-text markdown-content">
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
                    {/* 🚨 底部标记，用于自动滚动 */}
                    <div ref={conversationEndRef} style={{ height: '1px' }}></div>
                  </>
                ) : (
                  // 🎯 穿透模式：只显示最新一条
                  (() => {
                    const latestConv = conversationHistory[conversationHistory.length - 1];
                    return (
                      <div className="conversation-item">
                        {latestConv.type === 'image' && latestConv.screenshots && (
                          <div className="conv-screenshots">
                            <div className="screenshots-label">
                              📸 发送了 {latestConv.screenshots.length} 张截图
                            </div>
                          </div>
                        )}
                        {latestConv.type === 'text' && latestConv.userInput && (
                          <div className="user-message">
                            <div className="message-label">👤 你：</div>
                            <div className="message-text">{latestConv.userInput}</div>
                          </div>
                        )}
                        <div className="overlay-response" style={{
                          maxHeight: '60vh', /* 限制高度 */
                          overflowY: 'auto' /* 显示滚动条，可用 Ctrl+Up/Down */
                        }}>
                          <div className="response-label">🤖 AI：</div>
                          <div className="response-text markdown-content">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeHighlight]}
                            >
                              {latestConv.response}
                            </ReactMarkdown>
                          </div>
                        </div>
                      </div>
                    );
                  })()
                )}
              </div>
            )}

            {/* 当前正在加载但还没有历史记录时，显示单独的 AI 回复 */}
            {aiResponse && conversationHistory.length === 0 && (
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

          {/* 调试信息 */}
          {isFocusMode && (
            <div style={{ 
              padding: '0.5rem', 
              background: 'rgba(255, 0, 0, 0.3)',
              color: 'white',
              fontSize: '0.8rem',
              margin: '0 1rem 1rem 1rem'
            }}>
              🐛 专注模式已激活 - 输入框应该在上方固定显示
            </div>
          )}
        </div>

        {/* 输入框：仅在专注模式下显示，放在 content-wrapper 外部，固定在底部 */}
        {isFocusMode && (
          <div className="chat-input-container" style={{ 
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            borderTop: '1px solid rgba(255, 255, 255, 0.2)',
            padding: '1rem',
            flexShrink: 0 // 防止被挤压
          }}>
            <textarea
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendTextInput();
                }
              }}
              placeholder="Enter your question or continue conversation... (Enter to send, Shift+Enter for new line)"
              className="chat-input"
              disabled={isLoading}
              style={{
                minHeight: '60px',
                fontSize: '1rem'
              }}
            />
            <button
              onClick={handleSendTextInput}
              disabled={isLoading || !userInput.trim()}
              className="send-button"
              style={{
                minWidth: '60px',
                minHeight: '60px'
              }}
            >
              {isLoading ? '⏳' : '📤'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Overlay;
