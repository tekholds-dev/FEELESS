import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { duoState } from '../../lib/duo';
import '../../styles/updatesLog.css';

// 📜 SETTINGS › UPDATES (owner 2026-10-27: "a log of updates for site, backend or mobile — users see active fixes and what came from
// requests" + "new Duo screens, closed and open, every orientation, in the settings log"). The shipped changes come from git
// (/api/reputation/updates: NEW = a requested feature, FIX = an active fix; SITE · BACKEND · MOBILE); the DUO lens shows what FEELESS does on
// each phone shape — closed / open × portrait / landscape — and lights the one this screen is right now.
const LENSES = [['all', 'ALL'], ['site', 'SITE'], ['backend', 'BACKEND'], ['mobile', 'MOBILE'], ['duo', '📱 DUO SCREENS']];
export const DUO_SCREENS = [
  ['closed-port', 'CLOSED · PORTRAIT', 'a phone held upright', ['The coin\'s chart sits right under its name (stats + passport swipe below it)', 'Chart buttons = ONE swipe row of real tap targets', 'Inputs never zoom the page (16 px)', 'Perps provider rail swipes sideways']],
  ['closed-land', 'CLOSED · LANDSCAPE', 'a phone turned sideways', ['The coin\'s chart comes first, full height, beside the ticket / chat', 'The header shrinks to one thin bar', 'Perps vitals strip folds away · ⇄ swaps the sides']],
  ['open-port', 'OPEN · PORTRAIT', 'iPhone Duo open upright · 626 × 890', ['Trenches coin = a full-screen app: coin bar + live vitals, the chart, then the dock (TRADE · CHAT · CALLS · COINS · TAPE)', 'A pump-style BUY / SELL bar pinned to the bottom', '‹ › or a swipe on the coin bar = the next coin · ⇅ puts the dock on top']],
  ['open-land', 'OPEN · LANDSCAPE', 'iPhone Duo open wide · 890 × 626', ['Chart on one half, the dock on the other — the split sits on the crease', 'The rail: ← back · your recent coins · ⇄ swap the halves · home', 'Every tab is its own split app: Trenches · Pump radar (LAUNCHES dock) · HQ Agents (desk dock, seats on the rail) · Familia (city | your family, rooms lock to a half) · Perps (chart | ticket) · FEEd locks to a half', 'One slim top bar on every page (was four)']],
];
// pure: which Duo screen this device is now
export function screenNow(w = typeof window !== 'undefined' ? window : null) {
  if (!w) return null;
  const s = duoState(w); const land = (w.innerWidth || 0) > (w.innerHeight || 0);
  if (s.land) return 'closed-land';                              // a phone sideways (short screen) — before the wide-touch check
  if (s.duo) return land ? 'open-land' : 'open-port';
  const coarse = (() => { try { return !!w.matchMedia?.('(pointer: coarse)').matches; } catch { return false; } })();
  return coarse ? 'closed-port' : null;
}
const PART = { site: 'SITE', backend: 'BACKEND', mobile: 'MOBILE' };

export function UpdatesLog() {
  const [d, setD] = useState(null); const [lens, setLens] = useState('all'); const [now] = useState(() => screenNow());
  useEffect(() => { let on = true; fetch(apiUrl('/api/reputation/updates')).then(r => (r.ok ? r.json() : null)).then(x => on && setD(x || { rows: [], counts: {} })).catch(() => on && setD({ rows: [], counts: {} }));
    return () => { on = false; }; }, []);
  const c = d?.counts || {}; const rows = (d?.rows || []).filter(r => lens === 'all' || r.parts.includes(lens));
  const tot = Math.max(1, (c.new || 0) + (c.fix || 0));
  return <section className="m-card upl" data-testid="updates-log">
    <header className="upl-h"><span className="m-label">📜 UPDATES · WHAT SHIPPED</span>
      <span className="upl-split" data-tip="Of the last shipped changes: new features people asked for vs fixes"><i style={{ transform: `scaleX(${(c.new || 0) / tot})` }} />
        <b className="m-num">{c.new ?? '—'} NEW</b><b className="m-num is-fix">{c.fix ?? '—'} FIXES</b></span></header>
    <nav className="m-seg upl-lens" role="tablist" aria-label="Which updates">{LENSES.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''}
      onClick={() => setLens(k)} data-tip={k === 'duo' ? 'What FEELESS does on each phone shape: closed / open, portrait / landscape' : `Updates that touched ${k === 'all' ? 'anything' : PART[k].toLowerCase()}`} data-testid={`upl-${k}`}>
      {l}{c[k] != null ? <em className="m-num">{c[k]}</em> : null}</button>)}</nav>
    {lens === 'duo' ? <div className="upl-duo" data-testid="upl-duo">{DUO_SCREENS.map(([k, name, sub, feats], i) => <article key={k} className={`upl-scr s-${k} ${now === k ? 'is-now' : ''}`} style={{ '--i': i }}>
      <i className="upl-dev" aria-hidden="true"><s /><s /></i>
      <span><b>{name}</b><small>{sub}{now === k ? ' · THIS SCREEN NOW' : ''}</small></span>
      <ul>{feats.map(f => <li key={f}>{f}</li>)}</ul></article>)}</div>
      : <ol className="upl-list">{!d ? <li className="m-dim">Reading the log…</li> : null}
        {d && !rows.length ? <li className="m-dim">Nothing in this lens yet.</li> : null}
        {rows.slice(0, 40).map((r, i) => <li key={r.sha} className={`is-${r.type}`} style={{ '--i': Math.min(i, 10) }}>
          <span className="upl-meta"><em className={`upl-tag is-${r.type}`}>{r.type === 'fix' ? 'FIX' : 'NEW'}</em><small className="m-num">{r.at}</small>
            {r.parts.map(p => <u key={p} className={`upl-part p-${p}`}>{PART[p]}</u>)}</span>
          <ul>{r.items.map((t, j) => <li key={j}>{t}</li>)}</ul></li>)}</ol>}
  </section>;
}
