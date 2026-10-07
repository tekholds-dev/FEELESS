import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { openCoin } from './CoinDrawer';
import '../styles/trenchOpen.css';

const big = v => { const n = Number(v) || 0; return n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(0)}K` : `$${n.toFixed(0)}`; };
const sg = v => (v == null ? '—' : Math.abs(v) >= 1000 ? `${(v / 100 + 1).toFixed(1)}x` : `${v >= 0 ? '+' : ''}${Number(v).toFixed(0)}%`);
const ICON = { leader: '🔥', mover: '🚀', fresh: '🆕' };

// 🚪 OPEN GATES + 📣 CALLOUTS (GET /fuses/trench/open, one fetch a minute): every launch coin the feed sees, front-runners first,
// nothing filtered — each chip says safe ✅ / what it has not passed ⚠ / never scanned ❔ — and the callouts of the last hours
// (volume leader · mover · fresh launch) with what each did since. To look at; the engine never buys from this list.
export function TrenchOpen({ max = 10 }) {
  const [d, setD] = useState(null); const [all, setAll] = useState(false);
  useEffect(() => { let alive = true; const load = first => (first || !document.hidden) && fetch(apiUrl('/api/reputation/fuses/trench/open')).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(true); const t = setInterval(() => load(false), 60000); return () => { alive = false; clearInterval(t); }; }, []);
  if (!d || !(d.rows || []).length) return null;
  const rows = all ? d.rows : d.rows.slice(0, max);
  const open = r => openCoin({ mint: r.mint, pairAddress: r.pairAddress, symbol: r.symbol });
  return <div className="top" data-testid="trench-open">
    <div className="top-head"><span className="m-label">🚪 OPEN GATES · {d.rows.length} FRONT-RUNNERS OF {d.seen} LAUNCH COINS</span>
      <small className="m-dim">Nothing filtered: busiest right now first. ✅ passed the safety scan · ⚠ did not · ❔ never scanned. Yours to pick by hand; the engine never buys from here.</small></div>
    <ol className="top-rows">{rows.map(r => <li key={r.mint}><button type="button" className={`top-coin ${r.safe === true ? 'is-safe' : r.safe === false ? 'is-bad' : 'is-unk'}`} onClick={() => open(r)} data-testid={`open-${r.symbol}`}
      data-tip={`#${r.rank} $${r.symbol} · front-runner score ${r.front} · ${big(r.vol1h)} traded this hour · ${r.txns1h} trades${r.buyShare != null ? ` · ${r.buyShare}% buys` : ''} · cap ${big(r.mcap)}${r.ageH != null ? ` · ${r.ageH < 1 ? `${Math.round(r.ageH * 60)}m` : `${r.ageH.toFixed(0)}h`} old` : ''}. ${r.safe === true ? 'Passed every safety check.' : `Not passed: ${(r.fails || []).join(' · ')}`}`}>
      <i>{r.rank}</i><b>${r.symbol}</b>{r.call && <u aria-label="called out now">{ICON[r.call]}</u>}<em className="m-num">{big(r.vol1h)}/h</em>
      <span className={Number(r.chg5m) >= 0 ? 'm-pos' : 'm-neg'}>{sg(r.chg5m)} 5m</span><s>{r.safe === true ? '✅' : r.safe === false ? '⚠' : '❔'}</s></button></li>)}</ol>
    {d.rows.length > max && <button type="button" className="top-more" onClick={() => setAll(a => !a)} aria-expanded={all} data-testid="open-more">{all ? 'Show fewer' : `Show all ${d.rows.length}`}</button>}
    <div className="top-head"><span className="m-label">📣 CALLOUTS · EVERY {Math.round((d.everySec || 210) / 60 * 10) / 10} MIN</span>
      <span className="top-kinds">{(d.kinds || []).map(k => <span key={k.key} className="top-kind" data-testid={`call-kind-${k.key}`} data-tip={`${k.name}: ${k.rule}. Each coin is noted once when first called and settled 1 hour later (a coin with no price then counts as −100%).${k.proof?.n ? ` ${k.proof.n} settled · typical ${sg(k.proof.medPct)} · ${k.proof.wonPct}% up.` : ' Nothing settled yet.'} A record, never a promise.`}>
        {k.icon} {k.name}{k.proof?.n >= 5 ? <b className={k.proof.medPct > 0 ? 'm-pos' : 'm-neg'}> {sg(k.proof.medPct)} · {k.proof.wonPct}% up</b> : <b className="m-dim"> {k.proof?.n || 0}/5</b>}</span>)}</span></div>
    {(d.feed || []).length ? <ul className="top-feed" data-testid="call-feed">{d.feed.slice(0, 8).map(c => <li key={`${c.kind}-${c.mint}-${c.at}`}><button type="button" onClick={() => open(c)}>
      <i>{ICON[c.kind]}</i><b>${c.symbol || `${String(c.mint).slice(0, 4)}…`}</b><small>{c.mins < 60 ? `${c.mins}m ago` : `${Math.round(c.mins / 60)}h ago`}</small>
      <em className={`m-num ${Number(c.pct) >= 0 ? 'm-pos' : 'm-neg'}`}>{sg(c.pct)}</em><u>{c.live ? 'since the call' : 'after 1h'}</u></button></li>)}</ul>
      : <small className="m-dim">First callouts land within {Math.round((d.everySec || 210) / 60)} minutes.</small>}
  </div>;
}
