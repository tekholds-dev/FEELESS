import React from 'react';
import { dexUrl } from '../../lib/dexscreener';
export class ChartBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <div className="empty-focus" data-testid="chart-render-error"><p>Chart rendering is temporarily unavailable.</p><a className="btn-outline" data-testid="chart-render-fallback" href={dexUrl(this.props.pair)} target="_blank" rel="noreferrer">Open on DexScreener ↗</a><button className="btn-outline" data-testid="chart-render-retry" onClick={() => this.setState({ failed: false })}>Retry chart</button></div>;
    return this.props.children;
  }
}