import React, { useCallback, useEffect, useState } from 'react';

// Live health of every chart/data provider, the chart fallback order, and which .env key swaps each one.
export function LatencyPanel({ call }) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { setBusy(true); call('/admin/latency').then(setD).catch(() => setD({ providers: [] })).finally(() => setBusy(false)); }, [call]);
  useEffect(() => { load(); }, [load]);
  const tone = p => (!p.ok ? 'bad' : p.ms > 1500 ? 'warn' : 'good');
  return <section className="cc-panel latency-panel">
    <div className="cc-block"><h4>Charts & latency <button type="button" className="btn-outline" disabled={busy} onClick={load}>{busy ? 'Checking…' : 'Re-check'}</button></h4>
      <div className="lat-grid">{(d?.providers || []).map(p => <div key={p.name} className={`lat-row ${tone(p)}`}>
        <i /><b>{p.name}</b><span>{p.role}</span><em>{p.ok ? `${p.ms} ms` : 'down'}</em><small>{p.note || (p.env !== '—' ? `swap via ${p.env}` : 'built-in')}</small>
      </div>)}</div>
      {d?.chartOrder && <p className="cc-empty">Chart fallback order: {d.chartOrder.join(' → ')}. If one is down or slow, charts automatically use the next. To replace a provider, change its key in <code>backend/.env</code> and restart the backend.</p>}
    </div>
  </section>;
}
