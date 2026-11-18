import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { LineChart, Line, YAxis, ReferenceLine, ResponsiveContainer } from 'recharts';
import { apiUrl } from '../../lib/api';
import { Reels, RoomBid, TeamMark } from './GameRoom';
import { gameName } from '../../lib/pobGroups';
import '../../styles/gameRoom.css';
import '../../styles/liveBid.css';

// 📺 WATCH IT LIVE IN CHAT (owner 2026-11-15: "choose that live filing when brains are done to watch in chat … categories … live activity, new clips,
// bid %, pnl"). A PoB's real game pinned to the top of the desk chat: four views of one bid. Reads the same ESPN feed as the game window
// (/api/cats/tools/game) every 20 s while live, and its own Kalshi ticket (P&L never includes fees). Watching only: nothing here sends an order.
const POLL_MS = 20000;
const VIEWS = [['live', 'Live'], ['clips', 'Clips'], ['pct', 'Bid %'], ['pnl', 'P&L']];
const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`);
const usd = v => (v == null ? '—' : `${v < 0 ? '−' : ''}$${Math.abs(v).toFixed(2)}`);

// The ticket → the room's bid row: what is in, what it is worth now, P&L (worth − in; fees live on the receipt, never here). Pure.
export function bidRow(f) {
  const k = f?.kalshi; if (!k) return null;
  const filled = Number(k.filled ?? (k.status === 'filled' ? k.count : 0)) || 0; const cost = k.usd != null ? Number(k.usd) : filled * Number(k.price || 0);
  const now = k.outcome === 'won' ? filled : k.outcome === 'lost' ? 0 : k.livePx != null ? filled * Number(k.livePx) : null;
  return { ...k, n: f.n, placed: !!k.orderId, filled, cost, now, pnl: now == null || !filled ? null : Math.round((now - cost) * 100) / 100, hist: (k.pxHist || []).map(([t, v]) => [t, filled * v]) };
}

// Which of the two teams its bid backs, and that team's win chance through the game (ESPN's line is the HOME side's). Pure.
export function ourChance(d, f) {
  const want = String(f?.games?.[0]?.side || f?.kalshi?.title || '').toLowerCase();
  const ts = d?.teams || []; const i = ts.findIndex(t => t && [t.name, t.short, t.abbr].some(x => x && want.includes(String(x).toLowerCase())));
  if (i < 0) return { team: null, rows: [] };
  const home = ts[i].side === 'home';
  return { team: ts[i], rows: (d.wp || []).map((v, n) => ({ n, v: home ? v : 1 - v })) };
}

// 🧩 owner 2026-11-17 ("a parlay slip for the same game, so I can see in chat the 2 slips"): every PoB slip on this game rides one card.
export function LiveBidCard({ f, also = [], onClose }) {
  const g = f?.games?.[0]; const [d, setD] = useState(null); const [err, setErr] = useState(false); const [view, setView] = useState('live');
  const load = useCallback(() => (g ? fetch(apiUrl(`/api/cats/tools/game/${g.sport}/${g.id}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(j => { setD(j); setErr(false); }).catch(() => setErr(true)) : null), [g]);
  const live = (d?.state || g?.state) === 'in';
  useEffect(() => { load(); if (!g || (d && d.state === 'post')) return undefined; const t = setInterval(() => { if (!document.hidden) load(); }, POLL_MS); return () => clearInterval(t); }, [load, g, d?.state]);   // eslint-disable-line react-hooks/exhaustive-deps
  const b = useMemo(() => bidRow(f), [f]); const ch = useMemo(() => ourChance(d, f), [d, f]); const bids = useMemo(() => [f, ...also].map(bidRow).filter(Boolean), [f, also]);
  const plays = (d?.plays || []).filter(p => p.text != null).slice(-6).reverse(); const ta = d?.teams?.[0]; const tb = d?.teams?.[1];
  const minds = (f?.calls || []).map(c => ({ name: c.name || `Mind ${'AB'[c.mind] || ''}`, top: (c.picks || [])[0] }));
  const now = ch.rows.length ? ch.rows[ch.rows.length - 1].v : null;
  if (!g) return null;
  return <section className="lbc m-glass" data-testid="live-bid" aria-label={`Watching ${gameName(f)} live`}>
    <header className="lbc-h">
      <span className="lbc-t">{ta ? <TeamMark t={ta} size={26} /> : null}<b className="m-num" data-testid="live-bid-score">{d ? `${ta?.abbr || ''} ${ta?.score ?? 0} – ${tb?.score ?? 0} ${tb?.abbr || ''}` : gameName(f)}</b>{tb ? <TeamMark t={tb} size={26} /> : null}</span>
      <small className={live ? 'is-live' : ''}>{live ? '● LIVE · ' : ''}{d?.status || g.status || ''}</small>
      {bids.length > 1 ? <button type="button" className="lbc-n" onClick={() => setView('pnl')} data-tip="Every slip its PoBs put on this game" data-testid="live-bid-count">{bids.length} slips</button> : null}
      <button type="button" className="lbc-x" onClick={onClose} aria-label="Stop watching" data-tip="Stop watching (the PoB stays in its file)" data-testid="live-bid-close">✕</button>
    </header>
    <div className="m-seg lbc-views" role="group" aria-label="What to watch">{VIEWS.map(([k, l]) => <button key={k} type="button" className={view === k ? 'active' : ''} aria-pressed={view === k} onClick={() => setView(k)} data-testid={`live-bid-${k}`}>{l}{k === 'live' && live ? <i className="lbc-dot" aria-hidden="true" /> : k === 'clips' && d?.reels?.length ? <em className="m-num">{d.reels.length}</em> : null}</button>)}</div>
    <div className="lbc-pane" key={view}>
      {err && !d ? <p className="lbc-none" role="alert">ESPN did not answer for this game. It tries again in 20 s.</p> : !d ? <p className="lbc-none">Reading the game…</p>
        : view === 'live' ? (plays.length ? <ol className="lbc-feed" data-testid="live-bid-feed">{plays.map((p, i) => <li key={p.id} className={`${p.pts ? 'is-score' : ''}${i === 0 ? ' is-new' : ''}`} style={{ '--i': i }}><small className="m-num">{p.clock} · {p.perName || `P${p.per}`}</small><span>{p.text}</span>{p.a != null ? <b className="m-num">{p.a}–{p.b}</b> : null}</li>)}</ol> : <p className="lbc-none">No plays yet. They land here the moment it tips off.</p>)
        : view === 'clips' ? <Reels reels={d.reels} live={live} />
        : view === 'pct' ? <div className="lbc-pct" data-testid="live-bid-pctpane">
          <dl className="lbc-kv"><div><dt>{ch.team?.abbr || 'Its side'} win chance</dt><dd className="m-num">{pct(now)}</dd></div><div><dt>Kalshi now</dt><dd className="m-num">{b?.livePx != null ? pct(b.livePx) : b?.price != null ? pct(b.price) : '—'}</dd></div><div><dt>It paid</dt><dd className="m-num">{b?.placed ? pct(b.price) : '—'}</dd></div></dl>
          {ch.rows.length > 1 ? <div className="lbc-chart" aria-label={`${ch.team?.abbr || 'Its side'} win chance, from ${pct(ch.rows[0].v)} to ${pct(now)}`}><ResponsiveContainer width="100%" height={70}><LineChart data={ch.rows} margin={{ top: 4, right: 4, bottom: 2, left: 4 }}><YAxis hide domain={[0, 1]} /><ReferenceLine y={0.5} strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.3} />{b?.placed ? <ReferenceLine y={Number(b.price)} stroke="currentColor" strokeOpacity={0.55} /> : null}<Line type="monotone" dataKey="v" stroke="currentColor" strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></div> : <p className="lbc-none">The win-chance line starts at tip-off.</p>}
          <ul className="lbc-minds">{minds.map(m => <li key={m.name}><b>{m.name}</b>{m.top ? <><span>{m.top.pick}</span><em className="m-num">{m.top.confidence}%</em></> : <span>passed</span>}</li>)}</ul></div>
        : bids.length ? <div className="lbc-bids" data-testid="live-bid-bids">{bids.map(x => <RoomBid key={x.id || x.n} b={x} agent="" />)}</div> : <p className="lbc-none">No Kalshi bid on this PoB, so there is no P&amp;L. The game still plays out here.</p>}
    </div>
  </section>;
}
