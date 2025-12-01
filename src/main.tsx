import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AppRouter } from './AppRouter'
import Overlay from './Overlay'
import './index.css'

// 🚨 定义错误边界组件
class ErrorBoundary extends React.Component<any, { hasError: boolean, error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("React 崩溃:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, background: 'red', color: 'white', height: '100vh', overflow: 'auto' }}>
          <h2>💥 组件崩溃了</h2>
          <pre>{this.state.error?.toString()}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

// 获取 URL 参数
const params = new URLSearchParams(window.location.search);
const type = params.get('type');

const root = ReactDOM.createRoot(document.getElementById('root')!);

if (type === 'overlay') {
  // 悬浮窗模式
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <Overlay />
      </ErrorBoundary>
    </React.StrictMode>
  );
} else {
  // 主窗口模式 - 使用 BrowserRouter 支持网页版
  root.render(
    <React.StrictMode>
      <BrowserRouter>
        <ErrorBoundary>
          <AppRouter />
        </ErrorBoundary>
      </BrowserRouter>
    </React.StrictMode>,
  );
}
