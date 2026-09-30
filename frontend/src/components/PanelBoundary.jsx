import React from 'react';

// One broken widget must never take the page down: it shows a small retry card instead, and the crash is
// reported to Command Center > Bugs with the component that threw. Wrap any self-contained panel in this.
export class PanelBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null, tries: 0 }; }

  static getDerivedStateFromError(error) { return { error }; }

  componentDidCatch(error, info) {
    try {
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
