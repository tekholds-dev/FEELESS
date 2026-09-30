import React, { lazy, Suspense, useEffect } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useLocation as _useLoc } from 'react-router-dom';
import { WalletProvider } from './hooks/useWallet';
import { WorkspaceProvider } from './hooks/useWorkspace';
import { WatchlistAlerts } from './components/command/AdvancedWatchlist';
import { Toaster } from './components/ui/sonner';
import './styles/terminal.css';
import './styles/command.css';
import './styles/tab-variants.css';
import './styles/trade.css';
import './styles/heartbeat.css';
import { LegalConsent } from './components/LegalConsent';
import { captureInvite } from './lib/chatSession';
captureInvite();
import { installOverflowTitles, installImageFallback, installChartDisposalGuard } from './components/Hint';
installOverflowTitles();
if (process.env.NODE_ENV !== 'test') import('./lib/perfWatch').then(m => m.startPerfWatch()).catch(() => {});
installImageFallback();
installChartDisposalGuard();
import AmbientBackground from './components/AmbientBackground';
import { useHolderTheme } from './components/HolderTheme';
import { MobileTabBar } from './components/MobileTabBar';
import { FeeCatWidget } from './components/FeeCatWidget';
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

  componentDidCatch(error, info) {
    // Keep the real cause visible (console + recovery screen) instead of a generic message.
    console.error('FEELESS crash:', error, info?.componentStack);
    try { sessionStorage.setItem('feeless:last-crash', JSON.stringify({ at: Date.now(), path: window.location.pathname, message: String(error?.message || error), stack: String(info?.componentStack || '').slice(0, 1500) })); } catch { /* ignore */ }
    this.setState({ stack: info?.componentStack || '' });
    // Auto crash report → Command Center > Bugs, with the real error and the component that threw.
    try {
      const firstComp = (String(info?.componentStack || '').match(/at (\w+)/) || [])[1] || '?';
      fetch('/api/reputation/bugs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'bug', page: `${window.location.pathname}${window.location.search}`.slice(0, 300),
          text: `[auto crash] ${String(error?.message || error).slice(0, 400)} · in <${firstComp}> · ${String(info?.componentStack || '').replace(/\s+/g, ' ').slice(0, 1200)}` }) }).catch(() => {});
    } catch { /* never crash the crash screen */ }
  }

  render() {
    if (!this.state.error) return this.props.children;
    const isChunkError = /ChunkLoadError|Loading chunk|dynamically imported module/i.test(this.state.error?.message || '');
    return <main className="app-fatal" role="alert">
      <span className="eyebrow">{isChunkError ? 'SESSION UPDATE REQUIRED' : 'FEELESS RECOVERY MODE'}</span>
      <h1>{isChunkError ? 'This screen needs a fresh bundle.' : 'This screen could not load.'}</h1>
      <p>{isChunkError ? 'The preview updated while this tab was open. Reload once to use the current interface.' : 'The app caught the error before it could leave you with a blank screen.'}</p>
      <button type="button" className="btn-primary" onClick={() => window.location.reload()}>Reload FEELESS</button>
      {!isChunkError && <details className="app-fatal-detail"><summary>What went wrong</summary><code>{String(this.state.error?.message || this.state.error)}</code>{this.state.stack && <pre>{String(this.state.stack).trim().split('\n').slice(0, 6).join('\n')}</pre>}</details>}
    </main>;
  }
}

function AppShell() {
  return (
    <div className="App">
      <AmbientBackground />
      <div className="app-content">
        <WalletProvider><WorkspaceProvider><BrowserRouter><WatchlistAlerts />
          <Suspense fallback={<div className="app-loading" data-testid="app-loading"><span className="loader" />Opening FEELESS…</div>}><Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/terminal/*" element={<Terminal />} />
            <Route path="/whitepaper" element={<Navigate to="/terminal/whitepaper" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes></Suspense>
          <HolderThemeMount /><PageViews /><MobileTabBar /><FeeCatWidget />
        </BrowserRouter><Toaster theme="dark" position="bottom-right" /><LegalConsent /></WorkspaceProvider></WalletProvider>
      </div>
    </div>
  );
}

function App() {
  return <AppErrorBoundary><AppShell /></AppErrorBoundary>;
}

export default App;

function HolderThemeMount() { useHolderTheme(); return null; }

// One fire-and-forget beacon per route change: powers the command center's Traffic tab.
function PageViews() {
  const loc = _useLoc();
  // Pages rewrite their own query string while loading, so count one view per page (and per coin),
  // settled for 1.5s — not one per URL tick.
  const pair = new URLSearchParams(loc.search).get('pair') || (loc.search.match(/coin=([^&]+)/) || [])[1] || '';
  useEffect(() => {
    const t = setTimeout(() => {
      try {
        const body = JSON.stringify({ path: loc.pathname + (pair ? `?pair=${pair}` : ''), ref: document.referrer || '' });
        if (!(navigator.sendBeacon && navigator.sendBeacon('/api/reputation/pv', new Blob([body], { type: 'application/json' })))) fetch('/api/reputation/pv', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true }).catch(() => {});
      } catch { /* analytics never breaks the app */ }
    }, 1500);
    return () => clearTimeout(t);
  }, [loc.pathname, pair]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}
