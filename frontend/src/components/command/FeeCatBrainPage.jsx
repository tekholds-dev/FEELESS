import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { useLeaderProfile, useLeaderScan, feeHeadline } from '../../lib/feeLeader';
import '../../styles/feecatBrain.css';

// 🧠 HER BRAIN (FeeCat redo, 2026-10-23 — the tab was one chip row): how Fee decides, as live visuals from her own engine. HOW SHE PICKS = the
// entry gate as meters (her auto-strength's tightened values shown "now vs default"), HOW SHE SELLS = her exit ladder drawn on a % axis,
// WHAT SHE LEARNED = her playbook (setups that pay vs lose, by her own closed trades) + the lessons log, MEMORY VETOES = coins her memory blocked
// on the last scan, NINE LIVES = discipline. Reads: /api/cats/leader/profile + /api/cats/leader (shared 15 s) + /api/cats/brain (once a minute).
const k$ = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(v % 1e6 ? 1 : 0)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}K` : `$${v}`);
const sgn = v => `${v > 0 ? '+' : ''}${v}%`;

// pure: the entry gate as tiles [key, label, shown value, fill 0..1, tip, moved {now, def}]
export function gateTiles(rules, entry = {}) {
  const r = rules || {}; const now = k => (entry[k] && entry[k].now !== entry[k].default ? entry[k] : null);
  const v = k => (now(k) ? now(k).now : r[k]);
  const lg = (x, lo, hi) => Math.max(0.04, Math.min(1, (Math.log10(Math.max(1, x)) - lo) / (hi - lo)));
  return [
    ['minLiquidity', 'POOL ≥', k$(v('minLiquidity') || 0), lg(v('minLiquidity') || 0, 3, 6), 'The least liquidity a coin needs — thin pools rug and slip', now('minLiquidity')],
    ['minVolume24h', 'VOLUME 24H ≥', k$(r.minVolume24h || 0), lg(r.minVolume24h || 0, 3, 7), 'A coin nobody trades is a coin nobody buys from you', null],
    ['mc', 'MARKET CAP', `${k$(r.minMarketCap || 0)} – ${k$(r.maxMarketCap || 0)}`, lg(r.maxMarketCap || 1, 4, 8), 'Her hunting band — under it is a coin flip, over it the 10× is gone', null],
    ['h1', '1H MOVE', `${sgn(r.h1Min ?? 0)} … ${sgn(r.h1Max ?? 0)}`, Math.min(1, (r.h1Max || 0) / 100), 'Moving, but not already vertical', null],
    ['minBuySellRatio', 'BUYS ≥', `${r.minBuySellRatio ?? '—'}× sells`, Math.min(1, (r.minBuySellRatio || 0) / 3), 'Buyers have to be in control on the 5 m', null],
    ['maxM5Chase', 'NO CHASE', `5m ≤ ${sgn(v('maxM5Chase') ?? 0)}`, Math.min(1, (v('maxM5Chase') || 0) / 20), 'She never buys a candle that already ran', now('maxM5Chase')],
    ['maxTop10Pct', 'TOP-10 ≤', `${v('maxTop10Pct') ?? '—'}%`, Math.min(1, (v('maxTop10Pct') || 0) / 60), 'The ten biggest wallets may hold at most this much', now('maxTop10Pct')],
    ['maxSnipers', 'SNIPERS ≤', `${v('maxSnipers') ?? '—'}`, Math.min(1, (v('maxSnipers') || 0) / 15), 'Sniped launches get dumped on the first green candle', now('maxSnipers')],
    ['maxBundled', 'BUNDLED ≤', `${r.maxBundled ?? '—'}`, Math.min(1, (r.maxBundled || 0) / 15), 'Bundled supply = one seller pretending to be many', null],
  ];
}
// pure: her exit ladder — markers on a % axis (lo … hi), each [pct, label, kind]
export function exitLadder(r) {
  const x = r || {}; const m = [[x.hardStop, 'HARD STOP', 'stop'], [0, 'ENTRY', 'entry']];
  if (x.protectAt) m.push([x.protectAt, 'PROTECT', 'guard']);
  if (x.takeProfit1) m.push([x.takeProfit1, `TAKE ${Math.round((x.takeProfit1Sell || 0.4) * 100)}%`, 'take']);
  if (x.takeProfit2) m.push([x.takeProfit2, `TAKE ${Math.round((x.takeProfit2Sell || 0.4) * 100)}%`, 'take']);
  if (x.add1At && x.add1Fraction) m.push([x.add1At, 'ADD', 'add']);
  const pts = m.filter(([p]) => Number.isFinite(Number(p)));
  const lo = Math.min(-30, ...pts.map(p => p[0])) - 5; const hi = Math.max(80, ...pts.map(p => p[0])) + 10;
  return { lo, hi, marks: pts.sort((a, b) => a[0] - b[0]).map(([p, l, k]) => ({ p, l, k, at: (p - lo) / (hi - lo) })) };
}

function useBrain() {
  const [b, setB] = useState(null);
  useEffect(() => { let on = true; const go = () => fetch(apiUrl('/api/cats/brain')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setB(x)).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); return () => { on = false; clearInterval(t); }; }, []);
  return b;
}

// 🧭 HOW FEE THINKS (owner 2026-10-31: "put her brain inside Lore and redo it into a cooler understanding of it all"): her whole loop as ONE drawn
// pipeline, each station with its live number — a coin travels left → right; the station that stops most coins glows
export function thinkStations(sc, p, hive) {
  const scan = sc?.scan || {}; const b = sc?.cat?.brainsCfg || {}; const h = feeHeadline(p); const L = p?.learning || {};
  const dec = b.decisions || []; const today = (hive?.cells || []).length;
  return [
    ['scan', '🔎', 'SCAN', `${scan.scanned ?? 0}`, 'coins read on the trench board', 'Every round she reads the live trench board — FEELESS data, no outside guesses.'],
    ['gate', '🧭', 'GATES', `${scan.passed ?? 0}`, 'passed all nine', 'Pool, volume, cap band, 1 h move, buyers vs sellers, no chase, top-10, snipers, bundles — one fail and the coin is out.'],
    ['brains', '🧠', 'TWO BRAINS', `${(b.brains || []).length || '—'}`, dec.length ? `${dec.length} calls · last ${dec.at(-1)?.word || '—'} $${dec.at(-1)?.sym || ''}` : 'no call yet', 'Two AI models read the case one after the other; she buys only when they agree (the head cloud).'],
    ['hive', '🐝', 'THE HIVE', `${today}`, 'graded calls she can read', 'Other agents file calls on the same coins; an hour later each is graded on the real move. Her brains read those grades first.'],
    ['buy', '🎯', 'BUY + LADDER', `${h.open}`, 'open now', 'A small first bite, then the exit ladder: hard stop, protect, take profits in pieces, a trail behind a runner.'],
    ['lives', '❤', 'NINE LIVES', `${h.lives}/${h.maxLives}`, h.nap ? 'napping — no new trades' : (h.why || 'normal size'), 'A loss blows a life out, a win in 24 h lights one. At zero she naps: discipline only ever makes her trade less.'],
    ['learn', '📚', 'LEARN', `${L.memory ?? 0}`, `trades remembered · ${L.missed ?? 0} runners sold early`, 'Every exit is checked an hour on: runners she sold early loosen her trail, bad setups get vetoed next time.'],
  ];
}
export function ThinkFlow() {
  const p = useLeaderProfile(); const sc = useLeaderScan(); const [hive, setHive] = useState(null); const [open, setOpen] = useState('gate');
  useEffect(() => { let on = true; fetch(apiUrl('/api/cats/hive')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setHive(x)).catch(() => {}); return () => { on = false; }; }, []);
  const st = thinkStations(sc, p, hive); const cur = st.find(x => x[0] === open) || st[0];
  return <section className="fbr-flow" data-testid="fee-think">
    <header><b>🧭 HOW FEE THINKS</b><small>one coin's trip through her brain · live numbers · tap a station</small></header>
    <ol className="fbr-pipe" role="tablist" aria-label="Her decision loop">{st.map(([k, ic, name, big, small], i) => <li key={k} style={{ '--i': i }}>
      <button type="button" role="tab" aria-selected={open === k} className={open === k ? 'is-on' : ''} onClick={() => setOpen(k)} data-testid={`think-${k}`} data-tip={small}>
        <i aria-hidden="true">{ic}</i><em>{name}</em><b className="m-num" key={big}>{big}</b><small>{small}</small></button></li>)}
      <span className="fbr-coin" aria-hidden="true" /></ol>
    <p className="fbr-why" role="tabpanel" key={cur[0]}><b>{cur[1]} {cur[2]}</b> {cur[5]}</p>
  </section>;
}

export function FeeCatBrainPage() {
  const p = useLeaderProfile(); const sc = useLeaderScan(); const b = useBrain(); const h = feeHeadline(p);
  const rules = { ...(p?.rules || {}), ...(sc?.rules || {}) }; const L = p?.learning || {}; const pb = L.playbook || {};
  const tiles = gateTiles(rules, b?.entry || {}); const lad = exitLadder(rules);
  const setups = [...(pb.best || []).map(x => ({ ...x, good: true })), ...(pb.worst || []).map(x => ({ ...x, good: false }))];
  const maxRet = Math.max(10, ...setups.map(x => Math.abs(x.avgRet || 0)));
  const vetoes = sc?.scan?.brainRejects || [];
  const MODE = { warming: 'WARMING UP', tuned: 'TUNED', strict: 'STRICT', loose: 'LOOSE' };
  if (!p && !sc) return <p className="fbr-wait" data-testid="fee-brain-wait">🧠 reading her brain…</p>;
  return <section className="fbr" data-testid="fee-brain">
    <article className="fbr-card fbr-gate">
      <header><b>🧭 HOW SHE PICKS</b><small>every coin must pass all {tiles.length} · {b?.mode ? `auto-strength ${MODE[b.mode] || b.mode.toUpperCase()}` : 'her own engine'}</small></header>
      <ul>{tiles.map(([k, label, val, fill, tip, moved], i) => <li key={k} className={moved ? 'is-moved' : ''} style={{ '--i': i }} data-tip={moved ? `${tip}. Her auto-strength moved it: default ${moved.default} → now ${moved.now}` : tip} data-testid={`gate-${k}`}>
        <em>{label}</em><b className="m-num">{val}</b><u aria-hidden="true"><s style={{ transform: `scaleX(${fill})` }} /></u>{moved ? <small>tightened · was {k === 'minLiquidity' ? k$(moved.default) : moved.default}</small> : null}</li>)}</ul>
    </article>
    <article className="fbr-card fbr-exit">
      <header><b>🎯 HOW SHE SELLS</b><small>the ladder from her entry · max hold {rules.maxHoldHours ?? '—'} h · trail {rules.runnerTrail ?? '—'}% behind a runner</small></header>
      <div className="fbr-ladder" data-testid="exit-ladder">
        <i className="fbr-axis" aria-hidden="true"><s className="dn" style={{ transform: `scaleX(${lad.marks.find(m => m.k === 'entry')?.at ?? 0.3})` }} /></i>
        {lad.marks.map((m, i) => <span key={`${m.l}${m.p}`} className={`fbr-mk k-${m.k}`} style={{ left: `${(m.at * 100).toFixed(1)}%`, '--i': i }} data-tip={`${m.l} at ${sgn(m.p)} from her average entry`}>
          <i /><b className="m-num">{sgn(m.p)}</b><small>{m.l}</small></span>)}
        <span className="fbr-runner" aria-hidden="true" />
      </div>
      <p className="fbr-line">Below <b className="m-neg">{sgn(rules.hardStop ?? -25)}</b> the thesis is dead — out, no hoping. Above <b className="m-pos">{sgn(rules.takeProfit1 ?? 30)}</b> she sells in pieces and lets the rest run on a {rules.runnerTrail ?? 20}% trail that never drops under break-even.</p>
    </article>
    <article className="fbr-card fbr-learn">
      <header><b>📚 WHAT SHE LEARNED</b><small>{L.memory ?? 0} trades remembered · {L.good ?? 0} good exits · {L.missed ?? 0} runners sold early</small></header>
      {setups.length ? <ul className="fbr-setups">{setups.map((x, i) => <li key={`${x.setup}${x.good}`} className={x.good ? 'up' : 'dn'} style={{ '--i': i }} data-tip={`${x.n} trades with ${x.setup.replace('=', ' ')} · ${x.wins} won · average ${x.avgRet}%`}>
        <span>{x.setup.replace('=', ' · ')}</span><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.04, Math.abs(x.avgRet || 0) / maxRet)})` }} /></i>
        <b className="m-num">{x.avgRet >= 0 ? '+' : ''}{x.avgRet}%</b><small>{x.winRate}% won · {x.n}</small></li>)}</ul>
        : <p className="fbr-empty">Her playbook fills in as she closes trades — each setup needs a few before it counts.</p>}
      <div className="fbr-params">{Object.entries(L.params || {}).map(([k, v]) => <span key={k} data-tip={v !== L.defaults?.[k] ? `She moved it from ${L.defaults?.[k]}% after watching her exits` : 'At its default — her exits have not asked for a change'}>
        <em>{k === 'runnerTrail' ? 'RUNNER TRAIL' : k === 'takeProfit1' ? 'FIRST TAKE' : k.toUpperCase()}</em><b className="m-num">{v}%</b><small>{v !== L.defaults?.[k] ? `default ${L.defaults?.[k]}%` : 'default'}</small></span>)}</div>
      {(L.log || []).length ? <ol className="fbr-log">{L.log.slice(0, 5).map((x, i) => <li key={i} className={x.missed ? 'dn' : 'up'}>{x.note}</li>)}</ol> : null}
    </article>
    <article className="fbr-card fbr-lives">
      <header><b>❤ NINE LIVES</b><small>{h.why || 'normal size'}</small></header>
      <div className="fbr-lanterns" aria-label={`${h.lives} of ${h.maxLives} lives`}>{Array.from({ length: h.maxLives }, (_, i) => <i key={i} className={i < h.lives ? 'on' : ''} style={{ '--i': i }}><s /></i>)}</div>
      <div className="fbr-kv"><span><em>SIZE</em><b className="m-num">×{h.size ?? 1}</b></span><span><em>STREAK</em><b className="m-num">{p?.discipline?.streak ?? 0}</b></span>
        <span><em>EXPECTANCY</em><b className="m-num">{(p?.discipline?.expectancySol ?? 0).toFixed(4)}</b></span></div>
      <p className="fbr-line">A loss blows a lantern out, a win inside 24 h lights one. At zero she naps — her discipline can only ever make her trade <b>less</b>.</p>
    </article>
    {vetoes.length ? <article className="fbr-card fbr-veto"><header><b>🚫 HER MEMORY SAID NO</b><small>coins her own record blocked on the last scan</small></header>
      <ul>{vetoes.slice(0, 6).map((x, i) => <li key={`${x.symbol}${i}`} style={{ '--i': i }}><b>${x.symbol}</b><span>{x.why}</span></li>)}</ul></article> : null}
  </section>;
}
