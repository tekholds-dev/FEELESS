import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { errorText } from '../../lib/api';
import { liteMode, setLite } from '../../lib/perfWatch';

// Command Center › Lag catcher: what real visitors feel (slow routes, janky pages, fps) + the fix for each.
export function LagCatcher({ call }) {
  const [hours, setHours] = useState(1);
  const [d, setD] = useState(null);
  const [mine, setMine] = useState(liteMode());
  const load = useCallback(() => call(`/admin/perf?hours=${hours}`).then(setD).catch(e => toast.error(errorText(e))), [call, hours]);
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);
  const force = async on => { try { const r = await call('/admin/perf/config', { method: 'PUT', body: JSON.stringify({ forceLite: on }) }); setD(x => ({ ...x, forceLite: r.forceLite })); toast.success(on ? 'Lite effects on for everyone.' : 'Full effects restored.'); } catch (e) { toast.error(errorText(e)); } };
  const tone = !d ? '' : d.score >= 85 ? 'ok' : d.score >= 60 ? 'warn' : 'bad';
  return <section className="cc-panel lag-catcher" data-testid="lag-catcher">
    <div className="lag-hero"><div className={`lag-score t-${tone}`}><b>{d ? d.score : '…'}</b><small>SPEED SCORE</small></div>
      <div className="lag-hero-copy"><small>LAG CATCHER</small><h3>What visitors actually feel</h3><p>{d ? `${d.reports} browser reports in the last ${hours}h. Devices that lag switch to lite effects on their own.` : 'Collecting…'}</p></div>
      <div className="bdg-seg">{[[1, '1H'], [6, '6H'], [24, '24H']].map(([h, l]) => <button key={h} type="button" className={hours === h ? 'active' : ''} onClick={() => setHours(h)}>{l}</button>)}</div></div>
    <div className="lag-fixers">
      <label className="lag-toggle"><input type="checkbox" checked={!!d?.forceLite} onChange={e => force(e.target.checked)} /><span><b>Lite effects site-wide</b><small>Pauses backdrops, glows and orbits for every visitor.</small></span></label>
      <label className="lag-toggle"><input type="checkbox" checked={!!mine} onChange={e => { const m = e.target.checked ? 'manual' : ''; setLite(m); setMine(m); }} /><span><b>Lite on this device</b><small>{mine === 'auto' ? 'Auto-enabled: this device was lagging.' : 'Just for you.'}</small></span></label>
    </div>
    <div className="lag-grid">
      <div className="cc-block"><h4>Fix list</h4>{!d?.fixes?.length ? <p className="cc-empty">Nothing lagging. 🟢</p> : d.fixes.map((f, i) => <div key={i} className={`lag-fix t-${f.level}`}><b>{f.what}</b><span>{f.fix}</span></div>)}</div>
      <div className="cc-block"><h4>Slowest API routes</h4>{!d?.routes?.length ? <p className="cc-empty">No samples yet.</p> : d.routes.slice(0, 10).map(r => <div key={r.route} className="lag-row"><code>{r.route}</code><small>{r.calls}×</small><b className={r.p95 >= 2500 ? 'bad' : r.p95 >= 1200 ? 'warn' : ''}>{r.p50} / {r.p95}ms</b></div>)}</div>
      <div className="cc-block"><h4>Pages</h4>{!d?.pages?.length ? <p className="cc-empty">No samples yet.</p> : d.pages.slice(0, 10).map(p => <div key={p.page} className="lag-row"><code>{p.page}</code><small>{p.fps != null ? `${p.fps} fps` : '—'}</small><b className={p.jankMsPerReport >= 400 ? 'warn' : ''}>{p.jankMsPerReport}ms jank</b></div>)}</div>
    </div>
  </section>;
}
