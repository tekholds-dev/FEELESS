import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { openCoin } from './CoinDrawer';
import '../styles/trenchOpen.css';

const big = v => { const n = Number(v) || 0; return n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(0)}K` : `$${n.toFixed(0)}`; };
const sg = v => (v == null ? '—' : Math.abs(v) >= 1000 ? `${(v / 100 + 1).toFixed(1)}x` : `${v >= 0 ? '+' : ''}${Number(v).toFixed(0)}%`);
const ICON = { leader: '🔥', mover: '🚀', fresh: '🆕' };

const age = h => (h == null ? '—' : h < 1 ? `${Math.max(1, Math.round(h * 60))}m` : h < 48 ? `${Math.round(h)}h` : `${Math.round(h / 24)}d`);
const SAFE = r => (r.safe === true ? ['✅', 'safe', 'is-safe', 'Passed every safety check (holders, snipers, dev, creator).'] : r.safe === false ? ['⚠', 'failed', 'is-bad', `Did not pass: ${(r.fails || []).join(' · ')}`] : ['❔', 'unscanned', 'is-unk', 'Holders not scanned yet — unknown, not safe.']);
const KIND = { leader: 'volume leader', mover: 'mover', fresh: 'fresh launch' };

// 🚪 OPEN GATES + 📣 CALLOUTS (GET /fuses/trench/open, one fetch a minute). ONE plain table: every launch coin the feed sees,
// busiest first, nothing filtered — coin · age · traded this hour · last 5 min · safety in a WORD — and one button per row:
// "Pick" where a pick is being made (`onPick`, the swap picker), else "View". Under it the callouts as sentences.
export function TrenchOpen({ max = 10, onPick, busy }) {
  const [d, setD] = useState(null); const [all, setAll] = useState(false);
  useEffect(() => { let alive = true; const load = first => (first || !document.hidden) && fetch(apiUrl('/api/reputation/fuses/trench/open')).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(true); const t = setInterval(() => load(false), 60000); return () => { alive = false; clearInterval(t); }; }, []);
  if (!d || !(d.rows || []).length) return null;
  const rows = all ? d.rows : d.rows.slice(0, max);
  const open = r => openCoin({ mint: r.mint, pairAddress: r.pairAddress, symbol: r.symbol });
  return <div className="top" data-testid="trench-open">
    <div className="top-head"><span className="m-label">🚪 OPEN GATES · EVERY LAUNCH COIN, BUSIEST FIRST</span>
      <small className="m-dim">{d.rows.length} of {d.seen} coins in the feed. Nothing is hidden — read the SAFETY column before you pick. The engine never buys from this list.</small></div>
    <div className="top-table" role="table" aria-label="Open gates">
      <div className="top-tr top-th" role="row"><span>#</span><span>Coin</span><span>Age</span><span>Traded / h</span><span>5 min</span><span>Safety</span><span /></div>
      {rows.map(r => { const sf = SAFE(r); return <div key={r.mint} className={`top-tr ${sf[2]}`} role="row" data-testid={`open-${r.symbol}`}>
        <span className="top-rank">{r.rank}</span>
        <button type="button" className="top-sym" onClick={() => open(r)} data-tip={`Open $${r.symbol}: chart, holders, flow${r.buyShare != null ? ` · ${r.buyShare}% buys` : ''} · cap ${big(r.mcap)} · ${r.txns1h} trades this hour`}>${r.symbol}{r.call && <i aria-label={`called out: ${KIND[r.call]}`}>{ICON[r.call]}</i>}</button>
        <span>{age(r.ageH)}</span><span className="m-num">{big(r.vol1h)}</span><span className={`m-num ${Number(r.chg5m) >= 0 ? 'm-pos' : 'm-neg'}`}>{sg(r.chg5m)}</span>
        <span className="top-safe" data-tip={sf[3]}>{sf[0]} {sf[1]}</span>
        {onPick ? <button type="button" className="m-btn primary top-act" disabled={!!busy} onClick={() => onPick(r)} data-testid={`open-pick-${r.symbol}`}>Pick</button>
          : <button type="button" className="m-btn top-act" onClick={() => open(r)} data-testid={`open-view-${r.symbol}`}>View</button>}</div>; })}
    </div>
    {d.rows.length > max && <button type="button" className="top-more" onClick={() => setAll(a => !a)} aria-expanded={all} data-testid="open-more">{all ? 'Show fewer' : `Show all ${d.rows.length}`}</button>}
    <div className="top-head"><span className="m-label">📣 CALLOUTS · CHECKED EVERY {Math.round((d.everySec || 210) / 60 * 10) / 10} MIN</span>
      <small className="m-dim">A coin is called once when it first leads a list; we then track what it did. Record so far:</small>
      <span className="top-kinds">{(d.kinds || []).map(k => <span key={k.key} className="top-kind" data-testid={`call-kind-${k.key}`} data-tip={`${k.name}: ${k.rule}. Settled 1 hour after the call (no price then = −100%). A record, never a promise.`}>
        {k.icon} {k.name}: {k.proof?.n >= 5 ? <b className={k.proof.medPct > 0 ? 'm-pos' : 'm-neg'}>typical {sg(k.proof.medPct)} after 1h · {k.proof.wonPct}% up</b> : <b className="m-dim">{k.proof?.n || 0} of 5 settled — too early</b>}</span>)}</span></div>
    {(d.feed || []).length ? <ul className="top-feed" data-testid="call-feed">{d.feed.slice(0, 8).map(c => <li key={`${c.kind}-${c.mint}-${c.at}`}><button type="button" onClick={() => open(c)}>
      <i>{ICON[c.kind]}</i><b>${c.symbol || `${String(c.mint).slice(0, 4)}…`}</b><span>{KIND[c.kind]} · called {c.mins < 60 ? `${c.mins}m` : `${Math.round(c.mins / 60)}h`} ago</span>
      <em className={`m-num ${Number(c.pct) >= 0 ? 'm-pos' : 'm-neg'}`}>{sg(c.pct)}</em><u>{c.live ? 'since the call' : 'after 1h'}</u></button></li>)}</ul>
      : <small className="m-dim">First callouts land within {Math.round((d.everySec || 210) / 60)} minutes.</small>}
  </div>;
}
