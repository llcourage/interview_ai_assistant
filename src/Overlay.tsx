import React, { useEffect, useState, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/atom-one-dark.css';
import './Overlay.css';
import { getAuthHeader } from './lib/auth';
import { API_BASE_URL } from './lib/api';
import { getCurrentPrompt } from './lib/sceneStorage';

// 🚨 Configuration: Maximum number of conversations to save (prevent localStorage from being too large)
const MAX_CONVERSATIONS_TO_SAVE = 50;

// Session type definition
interface SessionData {
  id: string;
  timestamp: number;
  conversations: Array<{
    type: 'image' | 'text';  // Distinguish between image analysis and text conversation
    screenshots?: string[];   // Screenshots when analyzing images
    userInput?: string;       // User input when having text conversation
    response: string;
  }>;
}

const Overlay = () => {
  // Current Session ID
  const [currentSessionId] = useState<string>(() => `session_${Date.now()}`);
  
  // Helper function to get authentication token
  const getAuthToken = useCallback(async () => {
    const authHeader = getAuthHeader();
    // Extract token from "Bearer token" format
    return authHeader ? authHeader.replace('Bearer ', '') : null;
  }, []);
  
  // 📦 Plan state
  const [currentPlan, setCurrentPlan] = useState<'normal' | 'high'>(() => {
    return (localStorage.getItem('currentPlan') as 'normal' | 'high') || 'normal';
  });
  
  // 📦 Listen to plan changes in localStorage (sync with main window)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'currentPlan' && e.newValue) {
        setCurrentPlan(e.newValue as 'normal' | 'high');
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // Also listen to changes in the same window (via custom events)
    const handlePlanChange = (e: CustomEvent) => {
      const newPlan = e.detail as 'normal' | 'high';
      setCurrentPlan(newPlan);
    };
    
    window.addEventListener('planChanged', handlePlanChange as EventListener);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('planChanged', handlePlanChange as EventListener);
    };
  }, []);
  
  // Session data
  const [screenshots, setScreenshots] = useState<string[]>([]);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<Array<{
    type: 'image' | 'text';
    screenshots?: string[];
    userInput?: string;
    response: string;
  }>>([]);
  
  // UI state
  const [status, setStatus] = useState<string>('Waiting for screenshot...');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isFocusMode, setIsFocusMode] = useState<boolean>(false);
  const [userInput, setUserInput] = useState<string>(''); // User input
  
  // 🎤 Recording state
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingTime, setRecordingTime] = useState<number>(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  const contentRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const conversationEndRef = useRef<HTMLDivElement>(null); // 🚨 New: Conversation bottom marker

  // 💾 Save current Session to localStorage
  const saveCurrentSession = useCallback(() => {
    if (conversationHistory.length === 0) return; // Don't save empty sessions
    
    const sessions: SessionData[] = JSON.parse(localStorage.getItem('sessions') || '[]');
    
    // Find if current Session already exists
    const existingIndex = sessions.findIndex(s => s.id === currentSessionId);
    
    // 🚨 Truncate conversation history, only save recent N rounds
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
    console.log('💾 Session saved:', currentSessionId, 'conversations:', truncatedConversations.length);
    if (conversationHistory.length > MAX_CONVERSATIONS_TO_SAVE) {
      console.log(`📊 Conversation truncated: ${conversationHistory.length} -> ${MAX_CONVERSATIONS_TO_SAVE} rounds`);
    }
    // Trigger custom event to notify main window Session List update
    window.dispatchEvent(new CustomEvent('sessionsUpdated'));
  }, [conversationHistory, currentSessionId]);

  // 🆕 Create new Session
  const createNewSession = () => {
    console.log('🆕 Creating new Session');
    
    // Save current Session (if has conversations)
    saveCurrentSession();
    
    // Reload page to create a brand new Session ID
    window.location.reload();
  };

  // 🎤 Start recording
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
      
      // Start timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
      console.log('🎤 Starting recording');
    } catch (error) {
      console.error('❌ Recording failed:', error);
      setStatus('Recording failed, please check microphone permissions');
    }
  }, []);

  // 🎤 Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      
      setStatus('Recording stopped');
      console.log('🎤 Stopping recording');
    }
  }, [isRecording]);

  // 🎤 Send recording (using local Whisper)
  const sendRecording = useCallback(async () => {
    if (audioChunksRef.current.length === 0) {
      setStatus('No recording data');
      return;
    }
    
    if (isLoading) return;
    
    setIsLoading(true);
    setStatus('Transcribing audio locally...');
    
    try {
      // Get authentication token
      const token = await getAuthToken();
      if (!token) {
        throw new Error('Not logged in, please login first');
      }
      
      // Merge audio chunks
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      
      // 🎤 Use local Whisper to convert speech to text (not sent to cloud)
      let transcribedText: string;
      
      if (!window.aiShot?.speechToTextLocal) {
        throw new Error('Speech-to-text feature is only available in desktop version. Please use Electron desktop app.');
      }
      
      // Convert Blob to ArrayBuffer, then to base64
      const arrayBuffer = await audioBlob.arrayBuffer();
      // In browser environment, use btoa instead of Buffer
      const uint8Array = new Uint8Array(arrayBuffer);
      const base64Audio = btoa(String.fromCharCode(...uint8Array));
      
      console.log('🎤 Calling local Whisper to convert speech to text...');
      const result = await window.aiShot.speechToTextLocal(base64Audio, 'zh');
      
      if (result.success && result.text) {
        transcribedText = result.text;
        console.log('✅ Local speech-to-text completed:', transcribedText);
      } else {
        throw new Error(result.error || 'Local speech-to-text failed');
      }
      
      // Use transcribed text as user input
      setUserInput(transcribedText);
      setStatus('Thinking...');
      
      // Send text to cloud ChatGPT API
      const context = conversationHistory.map(conv => {
        if (conv.type === 'image') {
          return `[Image Analysis]\n${conv.response}`;
        } else {
          return `User: ${conv.userInput}\nAI: ${conv.response}`;
        }
      }).join('\n\n');
      
      // 🔗 Use cloud API (Vercel)
      const chatResponse = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_input: transcribedText,
          context: context
        }),
      });
      
      if (!chatResponse.ok) {
        throw new Error(`HTTP error! status: ${chatResponse.status}`);
      }
      
      const chatData = await chatResponse.json();
      console.log('✅ Received AI response:', chatData);
      
      setAiResponse(chatData.answer);
      setIsLoading(false);
      setStatus('Response complete');
      setTimeout(() => setStatus(''), 2000);
      
      // Add to conversation history
      const newConversation = {
        type: 'text' as const,
        userInput: transcribedText,
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
      
      // Clear recording data
      audioChunksRef.current = [];
      setRecordingTime(0);
      
    } catch (error) {
      console.error('❌ Failed to send recording:', error);
      setStatus(`Send failed: ${error}`);
      setIsLoading(false);
    }
  }, [isLoading, conversationHistory, saveCurrentSession, getAuthToken]);

  // 💬 Send conversation with specified text (used after speech-to-text)
  const handleSendTextInputWithText = useCallback(async (text: string) => {
    if (!text.trim()) return;
    
    if (isLoading) return;
    
    setIsLoading(true);
    setStatus('Thinking...');
    
    try {
      // Get authentication token
      const token = await getAuthToken();
      if (!token) {
        throw new Error('Not logged in, please login first');
      }
      
      // Build context
      const context = conversationHistory.map(conv => {
        if (conv.type === 'image') {
          return `[Image Analysis]\n${conv.response}`;
        } else {
          return `User: ${conv.userInput}\nAI: ${conv.response}`;
        }
      }).join('\n\n');
      
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_input: text,
          context: context
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('✅ Received AI response:', data);
      
      setAiResponse(data.answer);
      setIsLoading(false);
      setStatus('Response complete');
      setTimeout(() => setStatus(''), 2000);
      
      // Add to conversation history
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
      
      } catch (error: any) {
        console.error('❌ Conversation failed:', error);
        console.error('   - Error type:', error?.constructor?.name);
        console.error('   - Error message:', error?.message);
        console.error('   - API_BASE_URL:', API_BASE_URL);
        console.error('   - Request URL:', `${API_BASE_URL}/api/chat`);
        
        setIsLoading(false);
        const errorMsg = error?.message || String(error);
        let userFriendlyError = `### Error\n\nFailed to request backend.\n\n`;
        
        if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
          userFriendlyError += `**Network Error**: Unable to connect to server.\n\n`;
          userFriendlyError += `Please check:\n`;
          userFriendlyError += `1. Network connection is normal\n`;
          userFriendlyError += `2. API server is running (${API_BASE_URL})\n`;
          userFriendlyError += `3. Browser console for more error information\n`;
        } else {
          userFriendlyError += `Error message: ${errorMsg}`;
        }
        
        setStatus(`Error: ${errorMsg}`);
        setAiResponse(userFriendlyError);
      }
  }, [isLoading, conversationHistory, saveCurrentSession, getAuthToken]);

  // 💬 Handle text conversation request
  const handleSendTextInput = useCallback(async () => {
    if (!userInput.trim()) {
      setStatus('Please enter content');
      return;
    }
    
    if (isLoading) return;
    
    console.log(`💬 Sending text conversation: ${userInput.substring(0, 50)}...`);
    setIsLoading(true);
    setStatus('Thinking...');
    
    const currentInput = userInput;
    setUserInput(''); // Clear input field

    try {
      // Get authentication token
      const token = await getAuthToken();
      if (!token) {
        throw new Error('Not logged in, please login first');
      }
      
      // 🚨 For text conversation, don't use prompt template (which is for image analysis)
      // Just use user input directly and pass context for conversation continuity
      // 🚨 Build complete context: includes image analysis and text conversation
      const context = conversationHistory
        .map(conv => {
          if (conv.type === 'image') {
            return `[User sent ${conv.screenshots?.length || 0} screenshot(s)]\nAI: ${conv.response}`;
          } else {
            return `User: ${conv.userInput}\nAI: ${conv.response}`;
          }
        })
        .join('\n\n');
      
      const requestUrl = `${API_BASE_URL}/api/chat`;
      console.log('📡 Sending API request:', {
        url: requestUrl,
        method: 'POST',
        hasToken: !!token,
        inputLength: currentInput.length,
        API_BASE_URL: API_BASE_URL,
        contextLength: context.length
      });
      
      let response: Response;
      try {
        response = await fetch(requestUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ 
            user_input: currentInput,  // Use user input directly (no prompt template for text conversation)
            context: context  // Pass complete context for conversation continuity
          }),
        });
      } catch (fetchError: any) {
        console.error('❌ Fetch request failed:', {
          error: fetchError,
          errorType: fetchError?.constructor?.name,
          errorMessage: fetchError?.message,
          errorStack: fetchError?.stack,
          url: requestUrl,
          API_BASE_URL: API_BASE_URL
        });
        throw fetchError;
      }

      console.log('📡 API response status:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API error response:', {
          status: response.status,
          statusText: response.statusText,
          body: errorText
        });
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log('✅ Received AI response:', data);
      
      setAiResponse(data.answer);
      setIsLoading(false);
      setStatus('Response complete');
      setTimeout(() => setStatus(''), 2000); // Clear status after 2 seconds
      
      // 📝 Add to conversation history (text type)
      const newConversation = {
        type: 'text' as const,
        userInput: currentInput,
        response: data.answer
      };
      setConversationHistory(prev => {
        const updated = [...prev, newConversation];
        // Save to localStorage
        setTimeout(() => saveCurrentSession(), 100);
        // 🚨 Scroll to bottom
        setTimeout(() => {
          conversationEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 150);
        return updated;
      });
      
    } catch (error: any) {
      console.error('❌ Conversation failed:', error);
      console.error('   - Error type:', error?.constructor?.name);
      console.error('   - Error message:', error?.message);
      console.error('   - API_BASE_URL:', API_BASE_URL);
      console.error('   - Request URL:', `${API_BASE_URL}/api/chat`);
      
      setIsLoading(false);
      const errorMsg = error?.message || String(error);
      let userFriendlyError = `### Error\n\nFailed to request backend.\n\n`;
      
      if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
        userFriendlyError += `**Network Error**: Unable to connect to server.\n\n`;
        userFriendlyError += `Please check:\n`;
        userFriendlyError += `1. Network connection is normal\n`;
        userFriendlyError += `2. API server is running (${API_BASE_URL})\n`;
        userFriendlyError += `3. Browser console for more error information\n`;
      } else {
        userFriendlyError += `Error message: ${errorMsg}`;
      }
      
      setStatus(`Error: ${errorMsg}`);
      setAiResponse(userFriendlyError);
      setUserInput(currentInput); // Restore input
    }
  }, [userInput, isLoading, conversationHistory, saveCurrentSession, getAuthToken]);

  // Simplify click-through control: decide based on focus mode
  useEffect(() => {
    console.log('🎯 Click-through control mode:', isFocusMode ? 'Focus mode (no click-through)' : 'Click-through mode');
    
    if (isFocusMode) {
      // Focus mode: completely no click-through, can interact
      window.aiShot?.setIgnoreMouseEvents(false);
    } else {
      // Click-through mode: completely click-through, no interaction allowed
      // All clicks will pass through the window
      window.aiShot?.setIgnoreMouseEvents(true, { forward: true });
    }
  }, [isFocusMode]);

  // 🎯 Listen to focus mode and content changes, automatically adjust window height
  useEffect(() => {
    const adjustWindowHeight = () => {
      if (!scrollContainerRef.current) {
        return;
      }
      
      const headerHeight = 60; // Shortcut bar
      const footerHeight = isFocusMode ? 120 : 0; // Input box
      
      // 🚨 New strategy: decide height based on "state", not measuring DOM
      let contentHeight = 0;
      
      if (aiResponse) {
        // Has AI response: give different default height based on mode
        const screenHeight = window.screen.height;
        if (isFocusMode) {
          // Focus mode: default 70% screen height
          contentHeight = Math.floor(screenHeight * 0.7) - 60 - 120; // Subtract header and footer
        } else {
          // Transparent mode: default 50% screen height
          contentHeight = Math.floor(screenHeight * 0.5) - 60; // Subtract header
        }
      } else if (isLoading) {
        // Loading: give enough space to display screenshots + status
        // If there are screenshots, estimate by screenshot count; otherwise give minimum
        if (screenshots.length > 0) {
          const screenshotRowHeight = 180; // Increased to 180px per row
          const rows = Math.ceil(screenshots.length / 3);
          contentHeight = rows * screenshotRowHeight + 100; // Screenshots + status bar
        } else {
          contentHeight = 150; // Only status text
        }
      } else if (screenshots.length > 0) {
        // Only screenshots: estimate based on screenshot count
        const screenshotRowHeight = 180; // Increased to 180px per row
        const rows = Math.ceil(screenshots.length / 3); // Assume 3 per row
        contentHeight = rows * screenshotRowHeight + 80; // Screenshots + hint text
      } else {
        // Empty state: minimum height
        contentHeight = 40;
      }
      
      let totalDesiredHeight = headerHeight + contentHeight + footerHeight;
      
      console.log(`🎯 Adjusting height (Focus mode=${isFocusMode}):`);
      console.log(`   - Content estimate: ${contentHeight}px (AI response=${!!aiResponse}, Loading=${isLoading}, Screenshots=${screenshots.length})`);
      console.log(`   - Total required height: ${totalDesiredHeight}px`);
      
      let targetHeight: number;
      
      if (isFocusMode) {
        // 🎯 Focus mode: max 70% screen height, min 400
        const screenHeight = window.screen.height;
        const maxHeightFocus = Math.floor(screenHeight * 0.7);
        targetHeight = Math.min(totalDesiredHeight, maxHeightFocus);
        targetHeight = Math.max(targetHeight, 400);
      } else {
        // 🎯 Click-through mode: max 50% screen height, min 250
        const screenHeight = window.screen.height;
        const maxHeightNormal = Math.floor(screenHeight * 0.5);
        targetHeight = Math.min(totalDesiredHeight, maxHeightNormal);
        targetHeight = Math.max(targetHeight, 250);
      }
      
      console.log(`   - Final requested window height: ${targetHeight}px`);
      
      const resizeFn = window.aiShot.resizeOverlay || (window.aiShot as any).adjustHeight;
      
      if (resizeFn) {
        resizeFn(targetHeight);
      }
    };
    
    // Delay execution to ensure DOM is updated
    const t1 = setTimeout(adjustWindowHeight, 50);
    const t2 = setTimeout(adjustWindowHeight, 200);
    const t3 = setTimeout(adjustWindowHeight, 500);
    
    return () => {
      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
    };
  }, [isFocusMode, aiResponse, screenshots.length, status, isLoading]);

  // 🎯 Listen to IPC scroll events (Ctrl+Up/Down)
  useEffect(() => {
    if (window.aiShot && window.aiShot.onScrollContent) {
      const handleScroll = (direction: 'up' | 'down') => {
        console.log(`🖱️ Received scroll command: ${direction}`);
        if (scrollContainerRef.current) {
          const step = 100;
          const currentScroll = scrollContainerRef.current.scrollTop;
          const maxScroll = scrollContainerRef.current.scrollHeight - scrollContainerRef.current.clientHeight;
          
          console.log(`   Current state: scrollTop=${currentScroll}, maxScroll=${maxScroll}, clientHeight=${scrollContainerRef.current.clientHeight}, scrollHeight=${scrollContainerRef.current.scrollHeight}`);
          
          const newScroll = direction === 'up' ? currentScroll - step : currentScroll + step;
          
          scrollContainerRef.current.scrollTo({
            top: newScroll,
            behavior: 'auto'
          });
          console.log(`   Executing scroll: ${currentScroll} -> ${newScroll}`);
        } else {
          console.warn('⚠️ scrollContainerRef.current does not exist');
        }
      };

      window.aiShot.onScrollContent(handleScroll);
    }
  }, []);

  // Listen to IPC events
  useEffect(() => {
    console.log('Overlay component mounted, starting to listen to events...');

    const handleScreenshotTaken = (imageBase64: string) => {
      console.log('Received screenshot, adding to list');
      console.log('Image data first 50 characters:', imageBase64.substring(0, 50));
      setScreenshots(prev => [...prev, imageBase64]); // Append new screenshot
      setAiResponse(null);
      setStatus(`Captured ${screenshots.length + 1} screenshot(s), press Ctrl+Enter to analyze, Ctrl+D to clear`);
    };

    // 📸 Handle image analysis request
    const handleSendScreenshotRequest = async () => {
      if (screenshots.length === 0) {
        setStatus('Please take a screenshot first (Ctrl+H)');
        return;
      }
      
      if (isLoading) return;
      
      console.log(`🚀 Starting to analyze ${screenshots.length} screenshots...`);
      setIsLoading(true);
      setStatus('Analyzing images...');

      try {
        // Get authentication token
        const token = await getAuthToken();
        if (!token) {
          throw new Error('Not logged in, please login first');
        }
        
        // Remove data URL prefix from all screenshots
        const base64DataList = screenshots.map(img => 
          img.replace(/^data:image\/\w+;base64,/, '')
        );
        
        console.log(`📷 Screenshot data length: ${base64DataList.map(d => d.length).join(', ')}`);
        console.log(`📷 First screenshot first 50 chars: ${base64DataList[0].substring(0, 50)}`);
        
        // If only one image, send string; if multiple images, send array
        const imageData = base64DataList.length === 1 ? base64DataList[0] : base64DataList;
        
        // 🚨 Get current Prompt template (for image analysis)
        const promptTemplate = getCurrentPrompt();
        
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ 
            image_base64: imageData,
            prompt: promptTemplate || undefined  // If there's a Prompt template, pass it to backend
          }),
        });

        console.log('📡 API response status:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      });

        if (!response.ok) {
          const errorText = await response.text();
          console.error('❌ API error response:', {
            status: response.status,
            statusText: response.statusText,
            body: errorText
          });
          throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        console.log('✅ Received AI response:', data);
        
        setAiResponse(data.answer);
        setIsLoading(false);
        setStatus('Analysis complete');
        setTimeout(() => setStatus(''), 2000); // Clear status after 2 seconds
        
        // 📝 Add to conversation history (image type)
        const newConversation = {
          type: 'image' as const,
          screenshots: [...screenshots],
          response: data.answer
        };
        setConversationHistory(prev => {
          const updated = [...prev, newConversation];
          // Save to localStorage
          setTimeout(() => saveCurrentSession(), 100);
          // 🚨 Scroll to bottom
          setTimeout(() => {
            conversationEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
          }, 150);
          return updated;
        });
        
        // 🚨 Automatically clear screenshots after analysis completes
        setScreenshots([]);
        console.log('🗑️ Screenshots automatically cleared');
        
      } catch (error) {
        console.error('❌ Analysis failed:', error);
        setIsLoading(false);
        setStatus(`Analysis failed: ${error}`);
        setAiResponse(`### Error\n\nFailed to request backend.\n\nError message: ${error}`);
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
      console.error('window.aiShot is undefined! IPC bridge failed.');
      setStatus('IPC connection failed (preload not loaded)');
    }
  }, [screenshots, isLoading, saveCurrentSession]);

  // 🎯 Listen to scene selection events (from menu)
  useEffect(() => {
    if (window.aiShot?.onScenarioSelected) {
      const handleScenarioSelected = (data: { sceneId: string; presetId: string; prompt: string }) => {
        console.log('Scenario selected from menu in Overlay:', data);
        // Update scene configuration
        const { setCurrentScene } = require('./lib/sceneStorage');
        setCurrentScene(data.sceneId, data.presetId);
        // Trigger custom event to notify other components
        window.dispatchEvent(new CustomEvent('sceneConfigChanged'));
      };
      
      window.aiShot.onScenarioSelected(handleScenarioSelected);
      
      return () => {
        // Cleanup if needed
      };
    }
  }, []);


  // Listen to keyboard events (Ctrl+Left/Right to move window, Ctrl+D to delete screenshots)
  // Ctrl+Up/Down handled by global shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;

      let handled = false;
      
      switch (e.key.toLowerCase()) {
        case 'arrowleft':
          // Ctrl+Left: Move window left
          window.aiShot?.moveOverlay?.('left', 20);
          handled = true;
          break;
        case 'arrowright':
          // Ctrl+Right: Move window right
          window.aiShot?.moveOverlay?.('right', 20);
          handled = true;
          break;
        case 'd':
          // Ctrl+D: Delete all screenshots
          console.log('🗑️ Clearing all screenshots');
          setScreenshots([]);
          setAiResponse(null);
          setStatus('Screenshots cleared');
          handled = true;
          break;
        case 't':
          // 🎤 Ctrl+T: Start/stop recording
          if (isRecording) {
            stopRecording();
            // Automatically send after stopping
            setTimeout(() => {
              sendRecording();
            }, 500);
          } else {
            startRecording();
          }
          handled = true;
          break;
        case 'enter':
          // 🎤 Ctrl+Enter: If recording, stop and send; otherwise let global shortcut handle (send screenshots)
          if (isRecording) {
            stopRecording();
            setTimeout(() => {
              sendRecording();
            }, 500);
            handled = true;
          }
          // If not handled, let global shortcut handle (send screenshots)
          break;
        case 's':
        case 'S':
          // Ctrl+S: Toggle focus mode
          setIsFocusMode(prev => {
            const newMode = !prev;
            console.log(newMode ? '🔒 Focus mode: Opaque + selectable' : '👻 Click-through mode: Transparent + click-through');
            // 🚨 If loading (analyzing image/conversation), don't override status, only log to console
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
          // Ctrl+N: Create new Session
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
        // 🚨 Adjust transparency based on focus mode
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
        overflow: 'hidden' /* 🚨 Key: Prevent middle layer from being stretched */
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

        {/* Content area */}
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

            {/* Display conversation history */}
            {conversationHistory.length > 0 && (
              <div 
                className={`conversation-history ${isFocusMode ? 'focus-mode' : 'penetrate-mode'}`}
                style={{ 
                  overflowY: isFocusMode ? 'visible' : 'visible', /* 🚨 Focus mode: use global scrollbar, not individual scroll */
                  paddingRight: isFocusMode ? '0' : '0' /* 🚨 Focus mode: no padding needed, global scrollbar handles it */
                }}
              >
                {isFocusMode ? (
                  // 🎯 Focus mode: display complete history
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
                            <div className="message-label">👤 You:</div>
                            <div className="message-text">{conv.userInput}</div>
                          </div>
                        )}
                        <div className="overlay-response" style={{
                          maxHeight: 'none', /* No height limit in focus mode, use global scroll */
                          overflowY: 'visible' /* Use global scrollbar, not individual scroll */
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
                    {/* 🚨 Bottom marker for auto-scroll */}
                    <div ref={conversationEndRef} style={{ height: '1px' }}></div>
                  </>
                ) : (
                  // 🎯 Click-through mode: only show latest one
                  (() => {
                    const latestConv = conversationHistory[conversationHistory.length - 1];
                    return (
                      <div className="conversation-item">
                        {latestConv.type === 'image' && latestConv.screenshots && (
                          <div className="conv-screenshots">
                            <div className="screenshots-label">
                              📸 Sent {latestConv.screenshots.length} screenshots
                            </div>
                          </div>
                        )}
                        {latestConv.type === 'text' && latestConv.userInput && (
                          <div className="user-message">
                            <div className="message-label">👤 You:</div>
                            <div className="message-text">{latestConv.userInput}</div>
                          </div>
                        )}
                        <div className="overlay-response" style={{
                          maxHeight: '60vh', /* Limit height */
                          overflowY: 'auto' /* Show scrollbar, can use Ctrl+Up/Down */
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

            {/* When currently loading but no history yet, show separate AI response */}
            {aiResponse && conversationHistory.length === 0 && (
              <div className="overlay-response">
                <div className="response-label">AI Answer:</div>
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

          {/* Debug information */}
          {isFocusMode && (
            <div style={{ 
              padding: '0.5rem', 
              background: 'rgba(255, 0, 0, 0.3)',
              color: 'white',
              fontSize: '0.8rem',
              margin: '0 1rem 1rem 1rem'
            }}>
              🐛 Focus mode activated - Input box should be fixed at top
            </div>
          )}
        </div>

        {/* Input box: Only shown in focus mode, placed outside content-wrapper, fixed at bottom */}
        {isFocusMode && (
          <div className="chat-input-container" style={{ 
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            borderTop: '1px solid rgba(255, 255, 255, 0.2)',
            padding: '1rem',
            flexShrink: 0 // Prevent being squeezed
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
