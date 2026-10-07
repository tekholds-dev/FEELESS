import React, { Suspense, lazy, useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { openCoin } from './CoinDrawer';
import '../styles/fuseRoom.css';

const EcosystemChat = lazy(() => import('./EcosystemChat'));
const KEY = 'feeless.fuseRoom';
export const FUSE_ROOMS = [['big', '🔥', 'Big moves', 'Only the biggest things that happened: large wins and losses on real cards, callouts that ran or died'],
  ['chat', '💬', 'Lounge', 'The Fuse chat — everyone on any Fuse page'], ['radar', '🎯', 'Radar', 'What to look at right now: entry setups and the front-runners of the launch feed']];
const read = () => { try { const v = JSON.parse(window.localStorage.getItem(KEY) || '{}'); return { open: !!v.open, room: FUSE_ROOMS.some(r => r[0] === v.room) ? v.room : 'big' }; } catch { return { open: false, room: 'big' }; } };
const sg = v => (v == null ? '' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(0)}%`);
const ago = at => { const m = Math.max(0, Math.round((Date.now() / 1000 - at) / 60)); return m < 60 ? `${m}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
const CALL = { leader: '🔥', mover: '🚀', fresh: '🆕' };

// 🔥 BIG MOVES = the biggest activity, never all of it: a real card's sale that won or lost ≥ 10% (or any swap ≥ $5), and a
// callout that ran ≥ +25% or died ≤ −25%. Newest first, ≤ `n`.
export function bigMoves(swaps, calls, n = 10) {
  const out = [];
  (swaps || []).forEach(s => { const p = Number(s.pct); const big = (s.side === 'sell' && Number.isFinite(p) && Math.abs(p) >= 10) || Number(s.usd) >= 5; if (!big) return;
    out.push({ key: `s-${s.sig || s.at}`, at: s.at, ic: s.side === 'buy' ? '🟢' : p >= 0 ? '💰' : '🛑', sym: s.symbol, mint: s.mint, pair: s.pair, pct: Number.isFinite(p) ? p : null,
      text: `${s.label || 'A card'} ${s.side === 'buy' ? 'bought' : 'sold'} $${Number(s.usd).toFixed(2)}`, why: s.why || '' }); });
  (calls || []).forEach(c => { const p = Number(c.pct); if (!Number.isFinite(p) || Math.abs(p) < 25) return;
    out.push({ key: `c-${c.kind}-${c.mint}-${c.at}`, at: c.at, ic: CALL[c.kind] || '📣', sym: c.symbol, mint: c.mint, pair: c.pairAddress, pct: p, text: `callout ${c.live ? 'so far' : 'after 1h'}`, why: '' }); });
  return out.sort((a, b) => b.at - a.at).slice(0, n);
}

// ⚛ THE FUSE ROOM: a small glass panel on the side of EVERY Fuse page. A slim tab when closed; three rooms when open.
export function FuseRoom() {
  const [st, setSt] = useState(read); const [d, setD] = useState(null);
  useEffect(() => { try { window.localStorage.setItem(KEY, JSON.stringify(st)); } catch { /* private window */ } }, [st]);
  const live = st.open && st.room !== 'chat';
  useEffect(() => { if (!live) return undefined; let alive = true;
    const get = u => fetch(apiUrl(u)).then(r => r.json()).catch(() => null);
    const load = first => (first || !document.hidden) && Promise.all([get('/api/reputation/fuses/proof'), get('/api/reputation/fuses/trench/open'), get('/api/reputation/fuses/forecast')]).then(([proof, open, fc]) => alive && setD({ proof, open, fc }));
    load(true); const t = setInterval(() => load(false), 45000); return () => { alive = false; clearInterval(t); }; }, [live]);
  const coin = (mint, pair, sym) => mint && openCoin({ mint, pairAddress: pair, symbol: sym });
  if (!st.open) return <button type="button" className="frm-tab" onClick={() => setSt(s => ({ ...s, open: true }))} data-testid="fuse-room-tab" aria-label="Open the Fuse room" data-tip="The Fuse room: big moves · lounge chat · radar">
    <i className="frm-logo" aria-hidden><b>⚛</b></i><span>FUSE ROOM</span></button>;
  const big = bigMoves(d?.proof?.feed, d?.open?.feed);
  return <aside className="frm" data-testid="fuse-room" aria-label="Fuse room">
    <header className="frm-head"><i className="frm-logo" aria-hidden><b>⚛</b></i><strong>FUSE ROOM</strong>
      <button type="button" className="frm-x" onClick={() => setSt(s => ({ ...s, open: false }))} data-testid="fuse-room-hide" aria-label="Hide the Fuse room" data-tip="Hide to the side">›</button></header>
    <nav className="frm-tabs" role="tablist">{FUSE_ROOMS.map(([k, ic, name, tip]) => <button key={k} type="button" role="tab" aria-selected={st.room === k} className={st.room === k ? 'active' : ''} onClick={() => setSt(s => ({ ...s, room: k }))} data-tip={tip} data-testid={`fuse-room-${k}`}>{ic} {name}</button>)}</nav>
    <div className="frm-body">
      {st.room === 'big' && (!d ? <p className="frm-wait">Loading…</p> : big.length ? <ul className="frm-list" data-testid="fuse-room-big-list">{big.map(x => <li key={x.key}><button type="button" onClick={() => coin(x.mint, x.pair, x.sym)} data-tip={x.why || undefined}>
        <i>{x.ic}</i><b>${x.sym || '…'}</b>{x.pct != null && <em className={x.pct >= 0 ? 'm-pos' : 'm-neg'}>{sg(x.pct)}</em>}<span>{x.text}</span><small>{ago(x.at)}</small></button></li>)}</ul>
        : <p className="frm-wait">Nothing big in the last hours. Small swaps are left out on purpose.</p>)}
      {st.room === 'chat' && <Suspense fallback={<p className="frm-wait">Opening the lounge…</p>}><div className="frm-chat"><EcosystemChat compact room="fuse-lab" ecosystem={{ id: 'fuse-lab', name: 'Fuse lounge' }} /></div></Suspense>}
      {st.room === 'radar' && (!d ? <p className="frm-wait">Loading…</p> : <div data-testid="fuse-room-radar-pane">
        <span className="m-label">🎯 ENTRIES NOW</span>
        {(d.fc?.entries || []).length ? <ul className="frm-list">{d.fc.entries.slice(0, 5).map(e => <li key={e.mint}><button type="button" onClick={() => coin(e.mint, e.pairAddress, e.symbol)} data-tip={e.why}>
          <i>{e.ico}</i><b>${e.symbol}</b><em className={Number(e.chg5m) >= 0 ? 'm-pos' : 'm-neg'}>{sg(e.chg5m)} 5m</em><span>{e.name} · {sg(e.chg1h)} 1h</span></button></li>)}</ul> : <p className="frm-wait">No safe coin shows an entry setup right now.</p>}
        <span className="m-label">🚪 FRONT-RUNNERS</span>
        <ul className="frm-list">{(d.open?.rows || []).slice(0, 6).map(r => <li key={r.mint}><button type="button" onClick={() => coin(r.mint, r.pairAddress, r.symbol)} data-tip={r.safe === true ? 'Passed every safety check' : `Not passed: ${(r.fails || []).join(' · ')}`}>
          <i>{r.safe === true ? '✅' : r.safe === false ? '⚠' : '❔'}</i><b>${r.symbol}</b><em className={Number(r.chg5m) >= 0 ? 'm-pos' : 'm-neg'}>{sg(r.chg5m)} 5m</em><span>#{r.rank} · ${Math.round((r.vol1h || 0) / 1000)}K/h</span></button></li>)}</ul>
        <small className="frm-note">A read of the live feed · never a promise</small></div>)}
    </div>
  </aside>;
}
