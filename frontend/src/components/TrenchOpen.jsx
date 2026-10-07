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

const pct = v => (v == null ? '—' : `${Number(v).toFixed(0)}%`);
// what the holder scan found, in a few words (safe coins) — or what it failed / that it was never scanned
const whyLine = r => (r.safe === true ? [r.top10 != null && `top-10 hold ${pct(r.top10)}`, r.dev != null && `dev ${pct(r.dev)}`, r.insiders != null && `insiders ${pct(r.insiders)}`, r.bundled != null && `${r.bundled} bundled`].filter(Boolean).join(' · ') || 'passed every safety check'
  : r.safe === false ? `did not pass: ${(r.fails || []).join(' · ')}` : 'holders not scanned yet — unknown, not safe');
const FILTERS = [['all', 'All', () => true], ['safe', '✅ Safe', r => r.safe === true], ['unk', '❔ Unscanned', r => r.safe == null], ['bad', '⚠ Failed', r => r.safe === false]];
const SORTS = [['front', '🔥 Busiest', r => -(r.front || 0)], ['new', '🆕 Newest', r => (r.ageH == null ? 1e9 : r.ageH)], ['m5', '🚀 5 min', r => -(Number(r.chg5m) || -1e9)], ['h1', '📈 1 hour', r => -(Number(r.chg1h) || -1e9)]];
const mv = v => `top-n ${v == null ? '' : Number(v) >= 0 ? 'm-pos' : 'm-neg'}`;

// 🚪 OPEN GATES + 📣 CALLOUTS (GET /fuses/trench/open, one fetch a minute). ONE table, one coin a row, everything needed to
// choose on the row itself: logo · coin · age + cap · pool · traded this hour · 5 min · 1 hour · buyers · safety in a word, and
// under it WHY (what the holder scan found / failed). Filter by safety, sort by busiest / newest / what is moving. One button
// per row: "Pick" where a pick is being made (`onPick`, the swap picker), else "View".
export function TrenchOpen({ max = 10, onPick, busy }) {
  const [d, setD] = useState(null); const [all, setAll] = useState(false); const [f, setF] = useState('all'); const [sort, setSort] = useState('front');
  useEffect(() => { let alive = true; const load = first => (first || !document.hidden) && fetch(apiUrl('/api/reputation/fuses/trench/open')).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(true); const t = setInterval(() => load(false), 60000); return () => { alive = false; clearInterval(t); }; }, []);
  if (!d || !(d.rows || []).length) return null;
  const keyOf = SORTS.find(x => x[0] === sort)[2];
  const list = d.rows.filter(FILTERS.find(x => x[0] === f)[2]).slice().sort((a, b) => keyOf(a) - keyOf(b));
  const rows = all ? list : list.slice(0, max);
  const open = r => openCoin({ mint: r.mint, pairAddress: r.pairAddress, symbol: r.symbol });
  return <div className="top" data-testid="trench-open">
    <div className="top-head"><span className="m-label">🚪 OPEN GATES · EVERY LAUNCH COIN</span>
      <small className="m-dim">{d.rows.length} of {d.seen} coins in the feed. Nothing is hidden — read the safety word and the line under each coin before you pick. The engine never buys from this list.</small></div>
    <div className="top-bar"><div className="m-seg top-seg" role="group" aria-label="Safety filter">{FILTERS.map(([k, label, fn]) => <button key={k} type="button" className={f === k ? 'active' : ''} aria-pressed={f === k} onClick={() => setF(k)} data-testid={`open-f-${k}`}>{label}<i>{d.rows.filter(fn).length}</i></button>)}</div>
      <div className="m-seg top-seg" role="group" aria-label="Sort">{SORTS.map(([k, label]) => <button key={k} type="button" className={sort === k ? 'active' : ''} aria-pressed={sort === k} onClick={() => setSort(k)} data-testid={`open-s-${k}`}>{label}</button>)}</div></div>
    <div className={`top-table ${all ? 'is-all' : ''}`} role="table" aria-label="Open gates">
      <div className="top-tr top-th" role="row"><span>#</span><span /><span>Coin</span><span>Pool</span><span>Traded / h</span><span>5 min</span><span>1 hour</span><span>Buyers</span><span>Safety</span><span /></div>
      {rows.map((r, i) => { const sf = SAFE(r); return <div key={r.mint} className={`top-tr ${sf[2]}`} role="row" data-testid={`open-${r.symbol}`}>
        <span className="top-rank">{sort === 'front' && f === 'all' ? r.rank : i + 1}</span>
        <span className="top-av" aria-hidden="true">{String(r.symbol || '?').slice(0, 1)}{r.logo && <img src={r.logo} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} />}</span>
        <span className="top-coin"><button type="button" className="top-sym" onClick={() => open(r)} data-tip={`Open $${r.symbol}: chart, holders, flow · ${r.txns1h} trades this hour${r.curve ? ' · still on its launch curve' : ''}`}>${r.symbol}{r.call && <i aria-label={`called out: ${KIND[r.call]}`}>{ICON[r.call]}</i>}</button>
          <small>{age(r.ageH)} old · {big(r.mcap)} cap{r.curve ? ' · curve' : ''}</small></span>
        <span className="top-n">{r.liq ? big(r.liq) : '—'}</span><span className="top-n">{big(r.vol1h)}</span>
        <span className={mv(r.chg5m)}>{sg(r.chg5m)}</span><span className={mv(r.chg1h)}>{sg(r.chg1h)}</span>
        <span className={`top-n ${r.buyShare == null ? '' : r.buyShare >= 55 ? 'm-pos' : r.buyShare < 45 ? 'm-neg' : ''}`}>{r.buyShare == null ? '—' : `${Math.round(r.buyShare)}%`}</span>
        <span className="top-safe" data-tip={sf[3]}>{sf[0]} {sf[1]}</span>
        {onPick ? <button type="button" className="m-btn primary top-act" disabled={!!busy} onClick={() => onPick(r)} data-testid={`open-pick-${r.symbol}`}>Pick</button>
          : <button type="button" className="m-btn top-act" onClick={() => open(r)} data-testid={`open-view-${r.symbol}`}>View</button>}
        <small className="top-why">{whyLine(r)}</small></div>; })}
      {!rows.length && <small className="m-dim top-none">No coin in this filter right now.</small>}
    </div>
    {list.length > max && <button type="button" className="top-more" onClick={() => setAll(a => !a)} aria-expanded={all} data-testid="open-more">{all ? 'Show fewer' : `Show all ${list.length}`}</button>}
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
