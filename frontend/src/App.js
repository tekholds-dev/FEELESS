import React, { lazy, Suspense } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { WalletProvider } from './hooks/useWallet';
import { WorkspaceProvider } from './hooks/useWorkspace';
import { Toaster } from './components/ui/sonner';
import './styles/terminal.css';
import './styles/command.css';
import './styles/trade.css';
import './styles/heartbeat.css';
const Landing = lazy(() => import('./pages/Landing'));
const Terminal = lazy(() => import('./pages/Terminal'));

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    const isChunkError = /ChunkLoadError|Loading chunk|dynamically imported module/i.test(this.state.error?.message || '');
    return <main className="app-fatal" role="alert">
      <span className="eyebrow">{isChunkError ? 'SESSION UPDATE REQUIRED' : 'FEELESS RECOVERY MODE'}</span>
      <h1>{isChunkError ? 'This screen needs a fresh bundle.' : 'This screen could not load.'}</h1>
      <p>{isChunkError ? 'The preview updated while this tab was open. Reload once to use the current interface.' : 'The app caught the error before it could leave you with a blank screen.'}</p>
      <button type="button" className="btn-primary" onClick={() => window.location.reload()}>Reload FEELESS</button>
    </main>;
  }
}

function AppShell() {
  return (
    <div className="App">
      <WalletProvider><WorkspaceProvider><BrowserRouter>
        <Suspense fallback={<div className="app-loading" data-testid="app-loading"><span className="loader" />Opening FEELESS…</div>}><Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/terminal/*" element={<Terminal />} />
          <Route path="/whitepaper" element={<Navigate to="/terminal/whitepaper" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes></Suspense>
      </BrowserRouter><Toaster theme="dark" position="bottom-right" /></WorkspaceProvider></WalletProvider>
    </div>
  );
}

function App() {
  return <AppErrorBoundary><AppShell /></AppErrorBoundary>;
}

export default App;
