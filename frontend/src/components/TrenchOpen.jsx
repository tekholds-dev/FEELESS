import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { openCoin } from './CoinDrawer';
import '../styles/trenchOpen.css';
import { TrenchVital } from './CoinVital';
import { TrenchQuick, warmCoin } from './TrenchQuick';
import { SocialIcons } from './QuickPulse';
import { PumpCallouts } from './QuickPulse';
import { BsBar } from './BsBar';
import { leanOf, rushScore } from '../lib/lean';

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

// ⚡ SPLIT view (owner, 2026-10-08: "one vertical section showing newest, the other showing bond run, send it, near bond… with real vital data,
// plus a layout switch back to the OG way"). Left = 🆕 newest first. Right = THE READS, by lane: 🔥 Hot (the good calls, best call first) ·
// 🎢 Curve · 🧲 Dips · 👀 Watch · ☠ Avoid. Every card opens the ⚡ quick look (chart + every vital + pick), never the side drawer.
export const LAYOUTS = [['split', '⚡ Split'], ['list', '≡ List']];
const LKEY = 'feeless.openLayout';
const loadLayout = () => { try { return localStorage.getItem(LKEY) === 'list' ? 'list' : 'split'; } catch { return 'split'; } };
const word = r => r.tv?.call?.[1]; const tone = r => r.tv?.call?.[2];
const m0 = r => Number(r.tv?.meters?.[0]?.[1]) || 0;
// 🔥 Hot = what the ⚡ Rush board would take (clean scan or unscanned, no busted / wash / blow-off read, rug < 50, not a +15% candle),
// best rush first — it used to lead with BOND RUN / EARLY RUSH / BREAKOUT, calls whose own records read −84 / −64 / −45% an hour.
// ☠ Avoid = a bad tone OR a busted call; nothing rushes from there.
const rush = r => rushScore(r);
export const LANES = [
  ['hot', '🔥 Hot', r => rush(r) != null && tone(r) !== 'bad' && tone(r) !== 'warn', (a, b) => rush(b) - rush(a)],
  ['curve', '🎢 Curve', r => r.tv?.kind === 'curve' || r.curvePct != null, (a, b) => (Number(b.curvePct) || 0) - (Number(a.curvePct) || 0)],
  ['dip', '🧲 Dips', r => r.tv?.kind === 'dip' && rush(r) != null, (a, b) => m0(b) - m0(a)],
  ['watch', '👀 Watch', r => tone(r) === 'warn' && rush(r) != null, (a, b) => m0(b) - m0(a)],
  ['avoid', '☠ Avoid', r => tone(r) === 'bad' || (rush(r) == null && r.safe !== false && !!word(r)), (a, b) => m0(b) - m0(a)]];
export const laneRows = (rows, key) => { const l = LANES.find(x => x[0] === key) || LANES[0]; return (rows || []).filter(l[2]).slice().sort(l[3]); };

function Lean({ r }) {
  const v = leanOf(r); const dir = v > 0.15 ? 'up' : v < -0.15 ? 'down' : 'flat';
  return <svg className={`tsp-lean is-${dir}`} viewBox="0 0 40 12" data-tip={`Lean ${v >= 0 ? '+' : ''}${v} — 5-min move, the hour, buyers, pace, heat vs rug. A read, not a forecast.`} data-testid={`tlean-${r.symbol}`}><line x1="2" y1="6" x2="36" y2={6 - v * 5} /><circle cx="36" cy={6 - v * 5} r="1.6" /></svg>;
}

function ReadCard({ r, onOpen, showAge, onPick, busy }) {
  const sf = SAFE(r);
  return <div role="button" tabIndex={0} className={`tsp-card ${sf[2]} ${r.tv?.call ? `call-${r.tv.call[2]}` : ''}`} onClick={() => onOpen(r)} onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onOpen(r))}
    onMouseEnter={() => warmCoin(r)} onFocus={() => warmCoin(r)} data-testid={`rc-${r.symbol}`} data-tip={`Quick look: chart, every vital, pick · ${whyLine(r)}`}>
    <span className="tsp-av" aria-hidden="true">{String(r.symbol || '?').slice(0, 1)}{r.logo && <img src={r.logo} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} />}</span>
    <span className="tsp-id"><b><SocialIcons r={r} />${r.symbol}{r.call && <i>{ICON[r.call]}</i>}{r.pc?.callers ? <i data-tip={`${r.pc.callers} Pump callers right now`}>📣{r.pc.callers}</i> : null}{r.fd?.n ? <i data-tip={`${r.fd.n} new Pump coins are paired with it — their buys route through its pool`}>🧲{r.fd.n}</i> : null}</b>
      <small>{showAge ? <em className="tsp-age">{age(r.ageH)}</em> : `${age(r.ageH)} ·`} {big(r.mcap)} · {big(r.vol1h)}/h</small></span>
    <span className="tsp-mv"><span className={mv(r.chg5m)}>{sg(r.chg5m)}</span><small>5m</small><span className={mv(r.chg1h)}>{sg(r.chg1h)}</span><small>1h</small></span>
    <span className={`tsp-safe ${sf[2]}`} data-tip={sf[3]}>{sf[0]}</span>
    {r.curvePct != null && <span className="tsp-bond" data-tip={`${Math.round(r.curvePct)}% along its launch curve`}><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, r.curvePct / 100))})` }} /><small>🔔 {Math.round(r.curvePct)}%</small></span>}
    {r.tv && <span className="tsp-tv"><TrenchVital r={r} mini /></span>}
    <span className="tsp-foot">{r.vital && <span className={`tsp-grade cvl-${r.vital.tone}`} data-tip={`Vital ${r.vital.score}/100 — ${r.vital.word}`}>🫀 {r.vital.grade}</span>}
      {(r.tv?.tags || []).slice(0, 2).map(([ic, t, tn]) => <span key={t} className={`tsp-tag ${tn}`}>{ic} {t}</span>)}
      {r.buyShare != null && <span className="tsp-tag">{Math.round(r.buyShare)}% buys</span>}</span>
    <span className="tsp-flow" onClick={e => e.stopPropagation()} role="presentation">{r.mint && <BsBar mint={r.mint} compact />}<Lean r={r} />
      {onPick && rush(r) != null && <button type="button" className="m-btn m-go tsp-go" disabled={busy} onClick={e => { e.stopPropagation(); onPick(r); }} data-testid={`rush-pick-${r.symbol}`}>⚡ Rush</button>}</span>
  </div>;
}

// 🚪 OPEN GATES + 📣 CALLOUTS (GET /fuses/trench/open, one fetch a minute). ONE table, one coin a row, everything needed to
// choose on the row itself: logo · coin · age + cap · pool · traded this hour · 5 min · 1 hour · buyers · safety in a word, and
// under it WHY (what the holder scan found / failed). Filter by safety, sort by busiest / newest / what is moving. One button
// per row: "Pick" where a pick is being made (`onPick`, the swap picker), else "View".
// 🔗 socials first (owner: "filter for socials first"): a real link beats set-at-launch beats none; order kept inside each
const socN = r => ['site', 'x', 'tg'].reduce((n, k) => n + (typeof r[k] === 'string' ? 2 : r[k] ? 1 : 0), 0);
export const socFirst = rows => rows.map((r, i) => [r, i]).sort((a, b) => (socN(b[0]) > 0) - (socN(a[0]) > 0) || (socN(b[0]) >= 2) - (socN(a[0]) >= 2) || a[1] - b[1]).map(x => x[0]);
const SOC_KEY = 'feeless.openSoc';
export function TrenchOpen({ max = 10, onPick, busy }) {
  const [d, setD] = useState(null); const [all, setAll] = useState(false); const [f, setF] = useState('all'); const [sort, setSort] = useState('front');
  const [layout, setLayoutS] = useState(loadLayout); const [lane, setLane] = useState('hot'); const [llane, setLlane] = useState('all');   /* the list view's own read filter */ const [look, setLook] = useState(null);
  const [clean, setClean] = useState(true);   /* 🧹 the newest column hides failed scans + rug / busted / wash reads unless asked */
  const [soc, setSocS] = useState(() => { try { return localStorage.getItem(SOC_KEY) === '1'; } catch { return false; } });
  const setSoc = v => { setSocS(v); try { localStorage.setItem(SOC_KEY, v ? '1' : '0'); } catch { /* private window */ } };
  const sf = a => (soc ? socFirst(a) : a);
  const setLayout = v => { setLayoutS(v); try { localStorage.setItem(LKEY, v); } catch { /* private window */ } };
  useEffect(() => { let alive = true; const load = first => (first || !document.hidden) && fetch(apiUrl('/api/reputation/fuses/trench/open')).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(true); const t = setInterval(() => load(false), 20000); return () => { alive = false; clearInterval(t); }; }, []);
  if (!d || !(d.rows || []).length) return null;
  const keyOf = SORTS.find(x => x[0] === sort)[2];
  const laneFn = (LANES.find(x => x[0] === llane) || [])[2];
  const list = d.rows.filter(FILTERS.find(x => x[0] === f)[2]).filter(r => !laneFn || laneFn(r)).slice().sort((a, b) => keyOf(a) - keyOf(b));
  const listS = sf(list);
  const rows = all ? listS : listS.slice(0, max);
  const byMint = new Map(d.rows.map(r => [r.mint, r]));
  const open = (r, from) => { const full = byMint.get(r.mint); if (full) setLook({ row: full, list: from || list }); else openCoin({ mint: r.mint, pairAddress: r.pairAddress, symbol: r.symbol }); };
  const newAll = d.rows.filter(FILTERS.find(x => x[0] === f)[2]);
  const newest = sf(newAll.filter(r => !clean || rush(r) != null).slice().sort((a, b) => (a.ageH ?? 1e9) - (b.ageH ?? 1e9)));
  const hidden = newAll.length - newest.length;
  const lanes = LANES.map(l => [l[0], l[1], laneRows(d.rows.filter(FILTERS.find(x => x[0] === f)[2]), l[0])]);
  const laneList = sf((lanes.find(x => x[0] === lane) || lanes[0])[2]);
  const cap = all ? 200 : Math.max(12, max);
  return <div className="top" data-testid="trench-open">
    <PumpCallouts onOpen={c => open(c)} />
    <div className="top-head"><span className="m-label">🚪 OPEN GATES · EVERY LAUNCH COIN</span>
      <small className="m-dim">{d.rows.length} of {d.seen} coins in the feed. Nothing is hidden — read the safety word and the line under each coin before you pick. The engine never buys from this list.</small></div>
    <div className="top-bar"><div className="m-seg top-seg" role="group" aria-label="Layout">{LAYOUTS.map(([k, label]) => <button key={k} type="button" className={layout === k ? 'active' : ''} aria-pressed={layout === k} onClick={() => setLayout(k)} data-testid={`open-l-${k}`}>{label}</button>)}</div>
      <div className="m-seg top-seg" role="group" aria-label="Safety filter">{FILTERS.map(([k, label, fn]) => <button key={k} type="button" className={f === k ? 'active' : ''} aria-pressed={f === k} onClick={() => setF(k)} data-testid={`open-f-${k}`}>{label}<i>{d.rows.filter(fn).length}</i></button>)}</div>
      <button type="button" className={`top-soc-btn ${soc ? 'on' : ''}`} aria-pressed={soc} onClick={() => setSoc(!soc)} data-tip="Coins with a website / X / Telegram link first" data-testid="open-soc">🔗 Socials first<i>{d.rows.filter(r => socN(r) > 0).length}</i></button>
      {layout === 'list' && <div className="m-seg top-seg" role="group" aria-label="Sort">{SORTS.map(([k, label]) => <button key={k} type="button" className={sort === k ? 'active' : ''} aria-pressed={sort === k} onClick={() => setSort(k)} data-testid={`open-s-${k}`}>{label}</button>)}</div>}</div>
    {layout === 'split' && <div className="tsp" data-testid="open-split">
      <div className="tsp-col" data-testid="split-new"><div className="tsp-head"><span className="m-label">🆕 NEWEST</span><small className="m-dim">{newest.length} coins · youngest first</small>
          <button type="button" className={`top-soc-btn ${clean ? 'on' : ''}`} aria-pressed={clean} onClick={() => setClean(c => !c)} data-tip="Hide failed scans and rug / busted / wash reads" data-testid="split-clean">🧹 Clean{hidden > 0 ? <i>{hidden} hidden</i> : null}</button></div>
        <div className="tsp-list">{newest.slice(0, cap).map(r => <ReadCard key={r.mint} r={r} showAge onOpen={x => open(x, newest)} onPick={onPick} busy={busy} />)}
          {!newest.length && <small className="m-dim top-none">No coin in this filter right now.</small>}</div></div>
      <div className="tsp-col" data-testid="split-reads"><div className="tsp-head"><span className="m-label">🔥 THE READS</span>
        <div className="m-seg top-seg tsp-lanes" role="group" aria-label="Read lane">{lanes.map(([k, label, rs]) => <button key={k} type="button" className={lane === k ? 'active' : ''} aria-pressed={lane === k} onClick={() => setLane(k)} data-testid={`lane-${k}`}>{label}<i>{rs.length}</i></button>)}</div></div>
        <div className="tsp-list">{laneList.slice(0, cap).map((r, i) => <React.Fragment key={r.mint}>{lane === 'hot' && word(r) !== word(laneList[i - 1] || {}) && <small className="tsp-sub">{r.tv.call[0]} {word(r)} · {laneList.filter(x => word(x) === word(r)).length}</small>}
          <ReadCard r={r} onOpen={x => open(x, laneList)} onPick={onPick} busy={busy} /></React.Fragment>)}
          {!laneList.length && <small className="m-dim top-none">Nothing reads {(LANES.find(x => x[0] === lane) || LANES[0])[1]} right now — try another lane.</small>}</div></div>
    </div>}
    {layout === 'split' && (newest.length > cap || laneList.length > cap) && <button type="button" className="top-more" onClick={() => setAll(a => !a)} aria-expanded={all} data-testid="split-more">{all ? 'Show fewer' : 'Show every coin'}</button>}
    {layout === 'list' && <>
    <div className="m-seg top-seg top-lanes" role="group" aria-label="Read" data-testid="list-lanes"><button type="button" className={llane === 'all' ? 'active' : ''} aria-pressed={llane === 'all'} onClick={() => setLlane('all')} data-testid="llane-all">All reads<i>{d.rows.filter(FILTERS.find(x => x[0] === f)[2]).length}</i></button>
      {lanes.map(([k, label, rs]) => <button key={k} type="button" className={llane === k ? 'active' : ''} aria-pressed={llane === k} onClick={() => setLlane(llane === k ? 'all' : k)} data-testid={`llane-${k}`}>{label}<i>{rs.length}</i></button>)}</div>
    <div className={`top-table ${all ? 'is-all' : ''}`} role="table" aria-label="Open gates">
      <div className="top-tr top-th" role="row"><span>#</span><span /><span>Coin</span><span>Pool</span><span>Traded / h</span><span>5 min</span><span>1 hour</span><span>Buyers</span><span>Safety</span><span /></div>
      {rows.map((r, i) => { const sf = SAFE(r); return <div key={r.mint} className={`top-tr ${sf[2]} ${r.tv?.call ? `call-${r.tv.call[2]}` : ''}`} role="row" data-testid={`open-${r.symbol}`} onMouseEnter={() => warmCoin(r)}>
        <span className="top-rank">{sort === 'front' && f === 'all' ? r.rank : i + 1}</span>
        <span className="top-av" aria-hidden="true">{String(r.symbol || '?').slice(0, 1)}{r.logo && <img src={r.logo} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} />}</span>
        <span className="top-coin"><span className="top-soc"><SocialIcons r={r} /></span><button type="button" className="top-sym" onClick={() => open(r)} data-tip={`Open $${r.symbol}: chart, holders, flow · ${r.txns1h} trades this hour${r.curve ? ' · still on its launch curve' : ''}`}>${r.symbol}{r.call && <i aria-label={`called out: ${KIND[r.call]}`}>{ICON[r.call]}</i>}</button>
          <small>{age(r.ageH)} old · {big(r.mcap)} cap{r.curve ? ' · curve' : ''}</small></span>
        <span className="top-n">{r.liq ? big(r.liq) : '—'}</span><span className="top-n">{big(r.vol1h)}</span>
        <span className={mv(r.chg5m)}>{sg(r.chg5m)}</span><span className={mv(r.chg1h)}>{sg(r.chg1h)}</span>
        <span className={`top-n ${r.buyShare == null ? '' : r.buyShare >= 55 ? 'm-pos' : r.buyShare < 45 ? 'm-neg' : ''}`}>{r.buyShare == null ? '—' : `${Math.round(r.buyShare)}%`}</span>
        <span className="top-safe" data-tip={sf[3]}>{sf[0]} {sf[1]}</span>
        {onPick ? <button type="button" className="m-btn primary top-act" disabled={!!busy} onClick={() => onPick(r)} data-testid={`open-pick-${r.symbol}`}>Pick</button>
          : <button type="button" className="m-btn top-act" onClick={() => open(r)} data-testid={`open-view-${r.symbol}`}>View</button>}
        <small className="top-why">{whyLine(r)}</small>{r.tv && <span className="top-tv"><TrenchVital r={r} mini /></span>}</div>; })}
      {!rows.length && <small className="m-dim top-none">No coin in this filter right now.</small>}
    </div>
    {list.length > max && <button type="button" className="top-more" onClick={() => setAll(a => !a)} aria-expanded={all} data-testid="open-more">{all ? 'Show fewer' : `Show all ${list.length}`}</button>}</>}
    <div className="top-head"><span className="m-label">📡 FEELESS CALLS · CHECKED EVERY {Math.round((d.everySec || 210) / 60 * 10) / 10} MIN</span>
      <small className="m-dim">A coin is called once when it first leads a list; we then track what it did. Record so far:</small>
      <span className="top-kinds">{(d.kinds || []).map(k => <span key={k.key} className="top-kind" data-testid={`call-kind-${k.key}`} data-tip={`${k.name}: ${k.rule}. Settled 1 hour after the call (no price then = −100%). A record, never a promise.`}>
        {k.icon} {k.name}: {k.proof?.n >= 5 ? <b className={k.proof.medPct > 0 ? 'm-pos' : 'm-neg'}>typical {sg(k.proof.medPct)} after 1h · {k.proof.wonPct}% up</b> : <b className="m-dim">{k.proof?.n || 0} of 5 settled — too early</b>}</span>)}
        {Object.entries(d.earliness || {}).filter(([, v]) => v.n >= 5).map(([label, v]) => <span key={label} className="top-kind" data-testid={`early-${label}`} data-tip="Does being early pay? Coins grouped by how old they were when first called out; settled 1 hour later. A record, never a promise.">
          ⏱ seen at {label}: <b className={v.medPct > 0 ? 'm-pos' : 'm-neg'}>typical {sg(v.medPct)} · {v.big} ran +50% · {v.dead} died</b></span>)}</span></div>
    {(d.feed || []).length ? <ul className="top-feed" data-testid="call-feed">{d.feed.slice(0, 8).map(c => <li key={`${c.kind}-${c.mint}-${c.at}`}><button type="button" onClick={() => open(c)}>
      <i>{ICON[c.kind]}</i><b>${c.symbol || `${String(c.mint).slice(0, 4)}…`}</b><span>{KIND[c.kind]} · called {c.mins < 60 ? `${c.mins}m` : `${Math.round(c.mins / 60)}h`} ago</span>
      <em className={`m-num ${Number(c.pct) >= 0 ? 'm-pos' : 'm-neg'}`}>{sg(c.pct)}</em><u>{c.live ? 'since the call' : 'after 1h'}</u></button></li>)}</ul>
      : <small className="m-dim">First callouts land within {Math.round((d.everySec || 210) / 60)} minutes.</small>}
    {look && <TrenchQuick row={look.row} list={look.list} onPick={onPick} busy={busy} onClose={() => setLook(null)} />}
  </div>;
}
