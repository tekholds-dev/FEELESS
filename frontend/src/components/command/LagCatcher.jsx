import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { errorText } from '../../lib/api';
import { liteMode, setLite } from '../../lib/perfWatch';
import { CodeHealth } from './CodeHealth';
import '../../styles/lagAdvice.css';
import { shaped } from '../../lib/shape';
import { Ic3 } from '../../lib/icon3d';
const PERF = shaped({ reports: 0, fixes: [], pages: [], routes: [] });

const AREA = { machine: '🖥', server: '⏳', storage: '💾', api: '🌐', page: '🎞' };
export function LagVitals({ v }) {
  if (!v?.length) return null;
  return <div className="lgv" data-testid="lag-vitals">{v.map((r, i) => <span key={r.k} className={`lgv-t t-${r.tone || 'na'}`} style={{ '--i': i }}><em>{r.k}</em>
    <b key={String(r.v)}>{r.v == null ? '—' : `${r.v}${r.unit}`}</b><i className="lgv-pulse" /></span>)}</div>;
}
export function LagAdvice({ a }) {
  if (!a) return null;
  if (!a.length) return <p className="lga-ok" data-testid="lag-advice">🟢 Nothing to fix — the loop, the machine and the browsers all read healthy.</p>;
  return <ol className="lga" data-testid="lag-advice">{a.map((x, i) => <li key={i} className={`t-${x.level}`} style={{ '--i': i }}>
    <i className="lga-ic">{AREA[x.area] || '•'}</i><div><b>{x.what}</b><small>{x.why}</small><p><Ic3 e="🛠" /> {x.fix}</p></div></li>)}</ol>;
}

// 🎮 One meter per page (owner 2026-11-15 "do the lag catcher proposal"): the bar is the page's average fps from real visitors on a 0–60
// scale, the tick is its worst report, the line is the 25 fps floor; the note says how often it fell under and had to step its effects down.
export const FLOOR = 25; const TOP = 60;
const pct = f => `${Math.max(0, Math.min(100, (f / TOP) * 100)).toFixed(1)}%`;
export function FpsMeters({ pages }) {
  const rows = (pages || []).filter(p => p.fps != null).sort((a, b) => a.fps - b.fps).slice(0, 12);
  if (!rows.length) return <p className="cc-empty">{pages?.length ? 'No fps samples yet (a browser reports every minute).' : 'No samples yet.'}</p>;
  return <ul className="fpm" data-testid="fps-meters" style={{ '--floor': pct(FLOOR) }}>{rows.map(p => {
    const tone = p.fps < FLOOR ? 'bad' : p.fps < 40 ? 'warn' : 'ok';
    return <li key={p.page} className={`fpm-row t-${tone}`}>
      <code title={p.page}>{p.page}</code>
      <span className="fpm-bar" role="meter" aria-valuemin={0} aria-valuemax={TOP} aria-valuenow={p.fps} aria-label={`${p.page} ${p.fps} fps`}>
        <i className="fpm-fill" style={{ width: pct(p.fps) }} />{p.fpsLow != null && <i className="fpm-low" style={{ left: pct(p.fpsLow) }} />}<i className="fpm-floor" /></span>
      <b>{p.fps}<small> fps</small></b>
      <small className="fpm-note">{p.underFloor ? `${p.underFloor}/${p.reports} under 25` : `${p.reports} report${p.reports === 1 ? '' : 's'}`}{p.stepped ? ` · stepped down ${p.stepped}×` : ''}{p.jankMsPerReport >= 400 ? ` · ${p.jankMsPerReport}ms jank` : ''}</small>
    </li>; })}</ul>;
}

// HQ › Lag catcher: what real visitors feel (slow routes, janky pages, fps) + the fix for each.
export function LagCatcher({ call }) {
  const [hours, setHours] = useState(1);
  const [d, setD] = useState(null);
  const [mine, setMine] = useState(liteMode());
  const load = useCallback(() => call(`/admin/perf?hours=${hours}`).then(x => setD(PERF(x))).catch(e => toast.error(errorText(e))), [call, hours]);
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);
  const force = async on => { try { const r = await call('/admin/perf/config', { method: 'PUT', body: JSON.stringify({ forceLite: on }) }); setD(x => ({ ...x, forceLite: r.forceLite })); toast.success(on ? 'Lite effects on for everyone.' : 'Full effects restored.'); } catch (e) { toast.error(errorText(e)); } };
  const tone = !d ? '' : d.score >= 85 ? 'ok' : d.score >= 60 ? 'warn' : 'bad';
  return <section className="cc-panel lag-catcher" data-testid="lag-catcher">
    <div className="lag-hero"><div className={`lag-score t-${tone}`}><b>{d ? d.score : '…'}</b><small>SPEED SCORE</small></div>
      <div className="lag-hero-copy"><small>LAG CATCHER</small><h3>What visitors actually feel</h3><p>{d ? `${d.reports} browser reports in the last ${hours}h. Devices that lag switch to lite effects on their own.` : 'Collecting…'}</p></div>
      <div className="bdg-seg">{[[1, '1H'], [6, '6H'], [24, '24H']].map(([h, l]) => <button key={h} type="button" className={hours === h ? 'active' : ''} onClick={() => setHours(h)}>{l}</button>)}</div></div>
    <LagVitals v={d?.vitals} />
    <div className="cc-block lga-wrap"><h4>🩺 What to fix, worst first</h4><LagAdvice a={d?.advice} /></div>
    <div className="lag-fixers">
      <label className="lag-toggle"><input type="checkbox" checked={!!d?.forceLite} onChange={e => force(e.target.checked)} /><span><b>Lite effects site-wide</b><small>Pauses backdrops, glows and orbits for every visitor.</small></span></label>
      <label className="lag-toggle"><input type="checkbox" checked={!!mine} onChange={e => { const m = e.target.checked ? 'manual' : ''; setLite(m); setMine(m); }} /><span><b>Lite on this device</b><small>{String(mine).startsWith('auto') ? 'Auto-enabled: this device was lagging (switches back off once it runs smooth).' : 'Just for you.'}</small></span></label>
    </div>
    <div className="lag-grid">
      <div className="cc-block"><h4>Fix list</h4>{!d?.fixes?.length ? <p className="cc-empty">Nothing lagging. 🟢</p> : d.fixes.map((f, i) => <div key={i} className={`lag-fix t-${f.level}`}><b>{f.what}</b><span>{f.fix}</span></div>)}</div>
      <div className="cc-block"><h4>Slowest API routes</h4>{!d?.routes?.length ? <p className="cc-empty">No samples yet.</p> : d.routes.slice(0, 10).map(r => <div key={r.route} className="lag-row"><code>{r.route}</code><small>{r.calls}×</small><b className={r.p95 >= 2500 ? 'bad' : r.p95 >= 1200 ? 'warn' : ''}>{r.p50} / {r.p95}ms</b></div>)}</div>
      <div className="cc-block"><h4>Pages vs the 25 fps floor</h4><FpsMeters pages={d?.pages} /></div>
      {/* 🧱 E12: the page watcher's findings from real visitors — a page that scrolls sideways, an element spilling out, a control under another layer */}
      <div className="cc-block" data-testid="lag-layout"><h4>Layout watch</h4>{(() => { const bad = (d?.pages || []).filter(p => p.sideways || p.spills?.length || p.covered?.length);
        return !bad.length ? <p className="cc-empty">{d?.pages?.length ? 'No page spills, overlaps or scrolls sideways. 🟢' : 'No samples yet.'}</p>
          : bad.slice(0, 8).map(p => <div key={p.page} className={`lag-fix t-${p.sideways ? 'bad' : 'warn'}`} data-testid="lag-layout-row"><b>{p.page}</b>
            <span>{[p.sideways ? `scrolls sideways ${p.sideways}px` : null, p.spills?.length ? `spills: ${p.spills.join(', ')}` : null, p.covered?.length ? `covered: ${p.covered.join(', ')}` : null].filter(Boolean).join(' · ')}</span></div>); })()}</div>
    </div>
    <CodeHealth call={call} />
  </section>;
}
