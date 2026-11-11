import React from 'react';

// 🧹 SITE-1: what a crash reporter must NOT file. The support queue held 51 crash reports and every live one was dev-server noise:
// half-applied hot reloads (`.hot-update.js`, React Refresh's `_s is not a function`, webpack's `reading 'call'`), a build error shown
// mid-edit, a stale chunk, or a /dev/* fixture page (no router). Production crashes are always filed.
const HMR = /\.hot-update\.js|_s is not a function|reading 'call'|Module build failed|Cannot find module '|Loading (CSS )?chunk [\w-]+ failed/;
export function isCrashNoise(error, stack = '', path = (typeof window !== 'undefined' ? window.location.pathname : '')) {
  if (String(path).startsWith('/dev/')) return true;
  return process.env.NODE_ENV === 'development' && HMR.test(`${error?.message || error} ${error?.stack || ''} ${stack}`);
}

// One broken widget must never take the page down: it shows a small retry card instead, and the crash is
// reported to HQ > Bugs with the component that threw. Wrap any self-contained panel in this.
export class PanelBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null, tries: 0 }; }

  static getDerivedStateFromError(error) { return { error }; }

  componentDidCatch(error, info) {
    try {
      if (isCrashNoise(error, info?.componentStack)) return;   // dev hot-reload / fixture page, not a bug
      const comp = (String(info?.componentStack || '').match(/at (\w+)/) || [])[1] || '?';
      fetch('/api/reputation/bugs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'bug', page: `${window.location.pathname}${window.location.search}`.slice(0, 300),
          text: `[panel crash] ${this.props.name || comp}: ${String(error?.message || error).slice(0, 300)} · in <${comp}>` }) }).catch(() => {});
    } catch { /* reporting must never throw */ }
  }

  componentDidUpdate(prev) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });  // new page/coin → try again
  }

  render() {
    if (!this.state.error) return this.props.children;
    return <div className="panel-crash" role="status" data-testid="panel-crash">
      <b>{this.props.name || 'This panel'} hit a snag.</b>
      <span>The rest of FEELESS is fine. Reported automatically.</span>
      <button type="button" onClick={() => this.setState(s => ({ error: null, tries: s.tries + 1 }))}>Retry</button>
    </div>;
  }
}
