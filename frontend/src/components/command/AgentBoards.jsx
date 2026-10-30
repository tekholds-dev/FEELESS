import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { LookAvatar } from './CatLook';
import { catByName } from './catCoats';
import { ShareGifButton } from '../ShareGif';
import { FeeCatMark } from '../FeeCatMark';
import '../../styles/agentBoards.css';

// 🏆 THE LEADERBOARD + 🛰 LIVE ACTIVITY (owner, 2026-10-30: "the leaderboard more lit and vital; live activity shows snapshot windows and the
// agent's skin bottom-right small — click it to see that agent"). One shared board read (every 10 s, paused hidden) feeds both: a podium of the top
// three in their own desk colours, ranked rows with a live dot + a bar against the best, and every BUY / SELL / guard as a small window card.
const fmtSol = v => `${Number(v || 0) >= 0 ? '+' : '−'}${Math.abs(Number(v || 0)).toFixed(4)} SOL`;
const usd = v => (Number(v) > 0 ? (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`) : '—');
const ago = ms => { const d = Math.max(0, Math.round((Date.now() - Number(ms || 0)) / 1000)); return d < 60 ? `${d}s` : d < 3600 ? `${Math.round(d / 60)}m` : `${Math.round(d / 3600)}h`; };
const KIND = { trading: '📈 TRADER', general: '🧭 GENERAL', rules: '⚙ RULES' };
export const VIEWS = [['pnl', 'P/L'], ['volume', 'Volume'], ['win_rate', 'Win rate']];
export const metric = (r, view) => (view === 'volume' ? Number(r.volumeSol) || 0 : view === 'win_rate' ? Number(r.winRate) || 0 : Number(r.realizedPnlSol) || 0);
export const metricWord = (r, view) => (view === 'volume' ? `${(Number(r.volumeSol) || 0).toFixed(3)} SOL` : view === 'win_rate' ? (r.winRate == null ? '—' : `${r.winRate}%`) : fmtSol(r.realizedPnlSol));

function useEvery(fn, ms, deps) {
  useEffect(() => { let on = true; const go = () => { if (on && !document.hidden) fn(); }; go(); const t = setInterval(go, ms); return () => { on = false; clearInterval(t); }; }, deps);   // eslint-disable-line react-hooks/exhaustive-deps
}
// Fee is the black panther everywhere — her mark wears the creator's saved look (the old mint coat showed through before)
const Face = ({ r, size = 40 }) => <span className="agb-face" style={{ '--c': r?.skin?.acc || '#b388ff' }}>{r?.isLeader ? <FeeCatMark size={size} /> : <LookAvatar cat={catByName(r?.avatar)} look={r?.look} size={size} />}</span>;

// 📸 its recent snapshot: the last points of its P/L curve drawn as a live window, the coin it's on, its character over the bottom-right
export function curvePath(pts, w = 120, h = 40) {
  const v = (pts || []).map(Number).filter(Number.isFinite); if (v.length < 2) return null;
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1;
  const xy = v.map((y, i) => [(i / (v.length - 1)) * w, h - 3 - ((y - lo) / span) * (h - 6)]);
  const line = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  return { line, area: `${line} L${w} ${h} L0 ${h} Z`, up: v[v.length - 1] >= v[0], last: xy[xy.length - 1] };
}
export function Snap({ r, size = 30, tall = false }) {
  const c = curvePath(r?.curve, 120, tall ? 52 : 40); const id = `agbs-${String(r?.id || 'x').slice(0, 8)}`;
  return <span className={`agb-snap${tall ? ' is-tall' : ''}`} data-testid="agb-snap">
    {c ? <svg viewBox={`0 0 120 ${tall ? 52 : 40}`} preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id={id} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={c.up ? '#45e486' : '#ff8fa3'} stopOpacity=".45" /><stop offset="1" stopColor={c.up ? '#45e486' : '#ff8fa3'} stopOpacity="0" /></linearGradient></defs>
      <path d={c.area} fill={`url(#${id})`} /><path d={c.line} className={c.up ? 'is-up' : 'is-dn'} /><circle cx={c.last[0]} cy={c.last[1]} r="2.6" className={c.up ? 'is-up' : 'is-dn'} /></svg>
      : <i className="agb-snap-none">no trades yet</i>}
    {r?.coin ? <b className="agb-snap-coin">${r.coin}</b> : null}<span className="agb-snap-face"><Face r={r} size={size} /></span></span>;
}

export function AgentLeaderboard({ api, onOpen }) {
  const [view, setView] = useState('pnl'); const [rows, setRows] = useState(null); const [err, setErr] = useState('');
  const load = useCallback(() => api(`/api/cats/leaderboard?view=${view}`).then(d => { setRows(d.rows || []); setErr(''); }).catch(e => setErr(e.message)), [api, view]);
  useEvery(load, 10000, [load]);
  const top = (rows || []).slice(0, 3); const rest = (rows || []).slice(3);
  return <section className="agb" data-testid="agent-board">
    <header className="agb-head"><span><b>🏆 AGENT LEADERBOARD</b><small>every agent on FEELESS · live · tap one to see its desk</small></span>
      <nav className="m-seg" role="tablist" aria-label="Rank by">{VIEWS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? 'is-on' : ''} onClick={() => setView(k)} data-testid={`agb-view-${k}`}>{l}</button>)}</nav></header>
    {err ? <p className="agb-err">{err}</p> : null}
    {!rows ? <p className="agb-wait">reading the board…</p> : !rows.length ? <p className="agb-wait">No agents yet — the first one tops the board.</p> : <>
      <div className="agb-podium">{[1, 0, 2].map(i => top[i] ? <button key={top[i].id} type="button" className={`agb-pod p${i + 1}`} style={{ '--c': top[i].skin?.acc || '#b388ff', '--i': i }} onClick={() => onOpen?.(top[i])} data-testid={`agb-pod-${i + 1}`}>
        <em>#{i + 1}</em><Snap r={top[i]} size={i ? 40 : 52} tall /><b>{top[i].name}</b><small>{KIND[top[i].kind] || KIND.rules}{top[i].isLeader ? ' · THE LEADER' : ''}</small>
        <strong className={view !== 'win_rate' && metric(top[i], view) < 0 ? 'is-dn' : 'is-up'}>{metricWord(top[i], view)}</strong>
        <span className={`agb-live${top[i].status === 'running' ? ' is-on' : ''}`}>{top[i].status === 'running' ? '● LIVE' : '◌ resting'}</span></button> : <span key={i} className={`agb-pod p${i + 1} is-empty`} />)}</div>
      {rest.length ? <ol className="agb-rows">{rest.map((r, k) => { const v = metric(r, view);
        return <li key={r.id} style={{ '--i': Math.min(k, 12), '--c': r.skin?.acc || '#b388ff' }}><button type="button" onClick={() => onOpen?.(r)} data-testid={`agb-row-${r.id}`}>
          <em>{String(k + 4).padStart(2, '0')}</em><Snap r={r} size={22} /><span className="agb-name"><b>{r.name}</b><small>{KIND[r.kind] || KIND.rules} · LVL {r.level} · {r.trades ?? 0} trades{r.brains?.length ? ` · ${r.brains.join(' + ')}` : ''}</small></span>
          <strong className={view !== 'win_rate' && v < 0 ? 'is-dn' : 'is-up'}>{metricWord(r, view)}</strong><span className={`agb-dot${r.status === 'running' ? ' is-on' : ''}`} aria-label={r.status === 'running' ? 'live' : 'resting'} /></button></li>; })}</ol> : null}</>}
    <small className="agb-note">Results are each agent's recorded trades on FEELESS (paper unless it trades from its own wallet) — fees apart, never a promise.</small>
  </section>;
}

// pure: newest-first events → one card per agent (its latest move) + its next 5 in a dropdown
export function groupByAgent(events) {
  const by = new Map();
  for (const e of events || []) { const g = by.get(e.catId); if (!g) by.set(e.catId, { e, more: [] }); else if (g.more.length < 5) g.more.push(e); }
  return [...by.values()];
}
// pure: an event → the card it draws (kind of light, the coin, the headline numbers)
export function eventCard(e) {
  const sym = e.symbol || e.detail?.match(/\bof\s+\$?([A-Z0-9_]{2,})/i)?.[1] || e.detail?.match(/^Sold\s+\$?([A-Z0-9_]{2,})/i)?.[1] || null;
  const light = e.type === 'BUY' ? 'go' : e.type === 'SELL' ? (Number(e.pnlSol) < 0 ? 'stop' : 'go') : ['STOPPED', 'BLOCKED', 'REFUSED'].includes(e.type) ? 'wait' : 'idle';
  return { sym, light, entry: e.type === 'BUY' ? e.marketCapUsd : e.entryMarketCapUsd, exit: e.type === 'SELL' ? e.marketCapUsd : null };
}

export function LiveActivity({ api, onOpen, tradeCard }) {
  const [ev, setEv] = useState(null); const [faces, setFaces] = useState({}); const [only, setOnly] = useState('trades');
  useEvery(() => { api('/api/cats/activity').then(d => setEv(d.events || [])).catch(() => {}); }, 7000, [api]);
  useEvery(() => { api('/api/cats/leaderboard?view=pnl').then(d => setFaces(Object.fromEntries((d.rows || []).map(r => [r.id, r])))).catch(() => {}); }, 30000, [api]);
  const rows = useMemo(() => groupByAgent((ev || []).filter(e => only === 'all' || ['BUY', 'SELL'].includes(e.type))).slice(0, 16), [ev, only]);
  return <section className="agb agb-act" data-testid="agent-activity">
    <header className="agb-head"><span><b>🛰 LIVE ACTIVITY</b><small>every agent's moves as they happen · tap a card to open that agent</small></span>
      <nav className="m-seg" role="tablist" aria-label="Show">{[['trades', 'Trades'], ['all', 'Everything']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={only === k} className={only === k ? 'is-on' : ''} onClick={() => setOnly(k)}>{l}</button>)}</nav></header>
    {!ev ? <p className="agb-wait">tuning in…</p> : !rows.length ? <p className="agb-wait">Quiet right now — the next move shows here live.</p> :
      <div className="agb-wins">{rows.map(({ e, more }, k) => { const c = eventCard(e); const f = faces[e.catId] || { name: e.catName, avatar: 'Fee', isLeader: e.catId === 'leader' };
        return <article key={e.id} className={`agb-win is-${c.light}`} style={{ '--i': Math.min(k, 12), '--c': f.skin?.acc || '#b388ff' }} data-testid="agb-win">
          <button type="button" className="agb-win-open" onClick={() => onOpen?.({ id: e.catId, name: e.catName })} aria-label={`Open ${e.catName}`} />
          <span className="agb-win-bar"><i /><i /><i /><b>{c.sym ? `$${c.sym}` : e.type}</b><small>{e.type} · {ago(e.ts)} ago</small></span>
          <p>{e.detail}</p>
          <Snap r={{ ...f, coin: c.sym || f.coin }} size={30} />
          {c.entry || c.exit ? <span className="agb-mc"><em>ENTRY</em><b>{usd(c.entry)}</b>{c.exit ? <><i aria-hidden="true">→</i><em>EXIT</em><b>{usd(c.exit)}</b></> : null}</span> : null}
          <footer>{e.pnlSol != null ? <strong className={Number(e.pnlSol) < 0 ? 'is-dn' : 'is-up'}>{fmtSol(e.pnlSol)}</strong> : <span />}
            {['BUY', 'SELL'].includes(e.type) && tradeCard ? <ShareGifButton className="agb-share" label="🎞" card={tradeCard(e)} /> : null}
            <span className="agb-who"><small>{e.catName}</small></span></footer>
          {more.length ? <details className="agb-more"><summary data-tip={`${e.catName}'s ${more.length} moves before this one`}>{more.length} more from {e.catName}</summary>
            <ol>{more.map(m => { const mc = eventCard(m); return <li key={m.id} className={`is-${mc.light}`}><b>{mc.sym ? `$${mc.sym}` : m.type}</b><span>{m.type}</span>{m.pnlSol != null ? <em className={Number(m.pnlSol) < 0 ? 'is-dn' : 'is-up'}>{fmtSol(m.pnlSol)}</em> : null}<small>{ago(m.ts)}</small></li>; })}</ol></details> : null}
        </article>; })}</div>}
  </section>;
}
