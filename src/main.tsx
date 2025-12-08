import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { AppRouter } from './AppRouter'
import Overlay from './Overlay'
import { isElectron } from './utils/isElectron'
import './index.css'

// 🚨 Define error boundary component
class ErrorBoundary extends React.Component<any, { hasError: boolean, error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("React crashed:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, background: 'red', color: 'white', height: '100vh', overflow: 'auto' }}>
          <h2>💥 Component Crashed</h2>
          <pre>{this.state.error?.toString()}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

// Get URL parameters
const params = new URLSearchParams(window.location.search);
const type = params.get('type');

const root = ReactDOM.createRoot(document.getElementById('root')!);

if (type === 'overlay') {
  // Overlay window mode
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <Overlay />
      </ErrorBoundary>
    </React.StrictMode>
  );
} else {
  // Main window mode
  // Electron uses HashRouter to avoid path issues under file:// protocol
  // Web uses BrowserRouter to support normal URL routing
  const Router = isElectron() ? HashRouter : BrowserRouter;
  
  root.render(
    <React.StrictMode>
      <Router>
        <ErrorBoundary>
          <AppRouter />
        </ErrorBoundary>
      </Router>
    </React.StrictMode>,
  );
}
