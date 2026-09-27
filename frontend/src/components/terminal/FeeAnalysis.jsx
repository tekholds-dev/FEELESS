import React, { useEffect, useState } from 'react';
import { FeeCatMark } from '../FeeCatMark';

const VERDICT = {
  strong_buy: ['Strong buy', 'good'], buy: ['Buy', 'good'], watch: ['Watch', 'mid'], avoid: ['Avoid', 'bad'], rug_risk: ['Rug risk', 'bad'],
};

// Ask Fee: a written read on this coin from her Claude-powered brain. Only runs when you press the
// button (each analysis costs real money), and the server caches it for 10 minutes per coin.
export function FeeAnalysis({ pair }) {
  const [state, setState] = useState({ status: 'idle' });
  const key = `${pair?.chainId}:${pair?.pairAddress}`;
  useEffect(() => { setState({ status: 'idle' }); }, [key]);
  if (!pair?.pairAddress) return null;
  const ask = async () => {
    setState({ status: 'loading' });
    try {
      const r = await fetch('/api/cats/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ chain: pair.chainId, pairAddress: pair.pairAddress }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Fee could not read this coin.');
      setState({ status: 'done', d });
    } catch (e) { setState({ status: 'error', error: e.message }); }
  };
  const a = state.d?.analysis;
  const [label, tone] = VERDICT[a?.verdict] || ['—', 'mid'];
  return <section className="fee-analysis" data-testid="fee-analysis">
    <header><FeeCatMark size={30} variant={tone === 'good' ? 'mint' : tone === 'bad' ? 'rose' : 'gold'} animate={state.status === 'loading'} /><div><b>Ask Fee</b><small>A written read from real on-chain data</small></div>
      <button type="button" className="btn-primary" onClick={ask} disabled={state.status === 'loading'}>{state.status === 'loading' ? 'Fee is reading…' : state.status === 'done' ? 'Re-read' : 'Analyze'}</button></header>
    {state.status === 'error' && <p className="fa-error">{state.error}</p>}
    {a && <div className="fa-body">
      <div className="fa-verdict"><span className={`fa-pill ${tone}`}>{label}</span><span>{a.confidence}% confident</span>{state.d.cached && <em>cached</em>}</div>
      <h4>{a.headline}</h4>
      <p>{a.thesis}</p>
      {a.risks?.length > 0 && <ul>{a.risks.map(r => <li key={r}>{r}</li>)}</ul>}
      <p className="fa-plan"><b>Plan:</b> {a.plan}</p>
      <small className="fa-note">Analysis, not financial advice · FEELESS never trades for you.</small>
    </div>}
  </section>;
}
