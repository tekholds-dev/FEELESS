import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { readChatSession } from '../lib/chatSession';
import { unfuseOrders, rebalanceOrders, SOL_MINT } from '../lib/fuseGo';
import { FuseLab } from './FuseLab';
import { FuseSide } from './FuseSide';
import { FuseGo } from './FuseGo';
import { LiveFuseCard } from './FuseCard';
import { useRunners, Countdown, ProofRing, CoinRow, LANES } from './RunnersPanel';
import '../styles/runners.css';
import '../styles/fusePage.css';

// Fuse 🧬 — the whole Fuse product in one tab: Lab (build + featured) · Runners (pick ≤3 fresh coins) · Arena (proof)
// · My cards (live cards + every action). Runner picks and "Load" carry across tabs. Every money action is a normal
// wallet-signed FuseGo approval; the server re-checks every signature before anything counts.
export const FUSE_TABS = [['lab', '🧪 Lab'], ['runners', '🏃 Runners'], ['arena', '🏟 Arena'], ['cards', '🃏 My cards']];
const m$ = v => `${v < 0 ? '−' : ''}$${Math.abs(v || 0) >= 1e3 ? `${(Math.abs(v) / 1e3).toFixed(1)}K` : Math.abs(v || 0).toFixed(2)}`;
const pc = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;
const MAX_RUNNERS = 3;
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Request failed'); return x; });
const readTab = () => { const t = new URLSearchParams(window.location.search).get('tab'); return FUSE_TABS.some(([k]) => k === t) ? t : 'lab'; };

export function useFuseLimits(addr) {
  const [lim, setLim] = useState(null);
  useEffect(() => { if (!addr) { setLim(null); return undefined; } let alive = true;
    const load = () => fetch(apiUrl(`/api/reputation/fuses/limits/${addr}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setLim(x)).catch(() => {});
    load(); window.addEventListener('feeless:fuse-pnl', load); return () => { alive = false; window.removeEventListener('feeless:fuse-pnl', load); }; }, [addr]);
  return lim;
}

export function FusePage() {
  const [tab, setTab] = useState(readTab);
  const [runnerPicks, setRunnerPicks] = useState([]);
  const [incoming, setIncoming] = useState(null);
  const { wallet } = useWallet() || {};
  const addr = wallet?.chain === 'solana' ? wallet.address : null;
  const limits = useFuseLimits(addr);
  const go = t => { setTab(t); const u = new URL(window.location.href); u.searchParams.set('tab', t); window.history.replaceState(null, '', u); };
  return <section className="fuse-page" data-testid="fuse-page">
    <header className="fp-head"><h1 className="fp-title">Fuse <span>🧬</span></h1><p className="m-dim">Fuse pools + fresh runners into one card. You sign every move; we show every fee.</p>
      <div className="m-seg fp-tabs" role="tablist" aria-label="Fuse">{FUSE_TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} data-testid={`fuse-tab-${k}`} onClick={() => go(k)}>{l}{k === 'runners' && runnerPicks.length ? ` · ${runnerPicks.length}` : ''}</button>)}</div></header>
    <div className="fp-body" key={tab}>
      {tab === 'lab' && <div className="fz-split-view fp-lab"><FuseLab runnerPicks={runnerPicks} onRunnerPicks={setRunnerPicks} incoming={incoming} limits={limits} />
        <aside className="fp-right"><FeaturedFuses onLoad={f => setIncoming({ legs: f.legs, sol: 0, n: Date.now() })} /><FuseSide /></aside></div>}
      {tab === 'runners' && <RunnerPicker picks={runnerPicks} onPicks={setRunnerPicks} onDone={() => go('lab')} />}
      {tab === 'arena' && <ArenaBoard onPicks={list => { setRunnerPicks(list); go('lab'); }} />}
      {tab === 'cards' && <MyCards addr={addr} />}
    </div>
  </section>;
}

// ---- Lab › Featured (Cmd Ctr marks Fuses "Featured in Fuse Lab") ----------------------------------------------------
export function FeaturedFuses({ onLoad }) {
  const [list, setList] = useState(null);
  useEffect(() => { let alive = true; fetch(apiUrl('/api/reputation/fuses')).then(r => (r.ok ? r.json() : null)).then(d => alive && setList((d?.fuses || []).filter(f => f.featured))).catch(() => alive && setList([])); return () => { alive = false; }; }, []);
  if (!list?.length) return null;
  return <section className="m-card fp-featured" data-testid="fuse-featured"><span className="m-label">⭐ FEATURED FUSES</span>
    {list.map(f => <div key={f.id} className="fp-feat"><span className="fz-emoji">{f.emoji}</span><div><b>{f.name}</b><small>{f.legs.map(l => l.symbol).join(' · ')} · grade {f.score?.grade} · index {Number(f.index || 100).toFixed(1)}</small></div>
      <button type="button" className="m-btn" onClick={() => onLoad(f)} data-testid={`feat-load-${f.id}`}>Load</button></div>)}</section>;
}

// ---- Runners (users): live discovery — gated runners every source likes, pick ≤3 ----------------------------------------
export function togglePick(picks, r, max = MAX_RUNNERS) {
  if (picks.some(p => p.mint === r.mint)) return picks.filter(p => p.mint !== r.mint);
  return picks.length >= max ? picks : [...picks, r];
}
const SRC_ICON = { arena: '🏟', lit: '🔥', pump: '🚀', snipers: '🎯', creator: '📣' };
export const filterBySource = (rows, src) => (src === 'all' ? rows : rows.filter(r => r.sources.some(s => s.kind === src)));

export function RunnerPicker({ picks, onPicks, onDone }) {
  const [d, setD] = useState(null); const [src, setSrc] = useState('all');
  useEffect(() => { let alive = true; const load = () => !document.hidden && fetch(apiUrl('/api/reputation/runners/discover')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 20000); return () => { alive = false; clearInterval(t); }; }, []);
  if (!d) return <div className="fp-disc is-loading" data-testid="runner-picker"><div className="fp-scan" /><span className="m-dim">Scanning launchpads, the arena, the radar and the callers…</span></div>;
  const rows = filterBySource(d.runners || [], src);
  return <section className="fp-disc" data-testid="runner-picker">
    <header className="fp-disc-head m-card m-live"><div><span className="m-label">🏃 RUNNER DISCOVERY · LIVE</span><h2>Good runners, found for you.</h2>
      <p className="m-dim">Every coin here passed every gate right now ({d.gates.slice(0, 3).join(' · ')}…). The more sources that like it, the higher it sits.</p></div>
      <div className="rn-clock"><small>NEXT ROUND</small><Countdown at={d.nextRoundAt} /></div></header>
    <div className="m-seg fp-src" role="tablist" aria-label="Source">{[['all', '✨ All', (d.runners || []).length], ...Object.entries(d.sources).map(([k, l]) => [k, l, d.counts[k] || 0])].map(([k, l, n]) =>
      <button key={k} type="button" role="tab" aria-selected={src === k} className={src === k ? 'active' : ''} onClick={() => setSrc(k)} data-testid={`src-${k}`}>{l} <em>{n}</em></button>)}</div>
    {(d.swaps || []).length > 0 && <div className="fp-swaps" aria-label="Auto-swaps">{d.swaps.slice().reverse().map(s => <span key={s.at} className="fp-swap">🔁 ${s.out.symbol} → ${s.in.symbol} <small>{s.why[0]}</small></span>)}</div>}
    {!rows.length && <p className="m-dim fp-none">Nothing from this source passes every gate right now — that's the gates working. Next scan in seconds.</p>}
    <div className="fp-rgrid">{rows.map((r, i) => { const on = picks.some(p => p.mint === r.mint); const full = !on && picks.length >= MAX_RUNNERS; const hot = r.sources.length >= 2;
      return <article key={r.mint} className={`fp-runner ${on ? 'is-on' : ''} ${hot ? 'is-hot' : ''}`} style={{ '--i': Math.min(i, 14) }} data-testid={`runner-${r.mint}`}>
        {hot && <span className="fp-hotband">{r.sources.length} sources</span>}
        <div className="fp-rtop"><span className="fp-ava">{r.logo ? <img src={r.logo} alt="" loading="lazy" /> : '🏃'}</span><div><b>${r.symbol}</b><small>{r.lane || 'runner'} lane · score {Math.round(r.score || 0)}</small></div>
          <span className={`m-num fp-move ${(r.chg1h || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{pc(r.chg1h)}</span></div>
        <i className="fp-score"><i style={{ transform: `scaleX(${Math.min(1, (r.score || 0) / 100)})` }} /></i>
        <div className="fp-srcs">{r.sources.map(s => <span key={s.kind} className={`fp-chip src-${s.kind}`} data-tip={s.detail}>{SRC_ICON[s.kind]} {s.label.replace(/^\S+\s/, '')}</span>)}</div>
        <div className="m-row fp-rstats"><span>MC {m$(r.mcap)}</span><span>{Math.round(r.buyShare || 0)}% buys</span><span>{m$(r.vol1h)} 1h vol</span></div>
        <button type="button" className={`m-btn wide ${on ? 'primary' : ''}`} disabled={full} onClick={() => onPicks(togglePick(picks, r))} data-testid={`runner-add-${r.mint}`}>{on ? '✓ On your card' : full ? 'Card full (3)' : '+ Add to card'}</button>
      </article>; })}</div>
    {picks.length > 0 && <div className="fp-dock" data-testid="fp-dock"><span>{picks.map(p => `$${p.symbol}`).join(' · ')}</span><button type="button" className="m-btn primary m-go" onClick={onDone} data-testid="runners-to-lab">Build card with {picks.length} →</button></div>}
  </section>;
}

// ---- Arena: the runners' live show — proof ring, countdown, the round card that lights up, lit cards, swaps, strategies ----
export function ArenaBoard({ onPicks }) {
  const d = useRunners();
  const [a, setA] = useState(null);
  useEffect(() => { let alive = true; fetch(apiUrl('/api/reputation/fuses/arena')).then(r => (r.ok ? r.json() : null)).then(x => alive && setA(x)).catch(() => {}); return () => { alive = false; }; }, []);
  if (!d) return <div className="fp-disc is-loading" data-testid="fuse-arena"><div className="fp-scan" /><span className="m-dim">Loading the arena…</span></div>;
  const picks = d.round?.picks || []; const lit = d.proof?.lights;
  const use = list => onPicks?.(list.slice(0, MAX_RUNNERS).map(p => ({ ...p })));
  return <section className="fp-arena" data-testid="fuse-arena">
    <header className="rn-hero"><div className="rn-title"><span className="m-label">🏟 RUNNERS ARENA · LIVE</span><h3>Every round, played on paper.</h3>
      <p>A round deals the best gated runners every 15 min. When the last 24h of rounds win, the round card <b>lights up</b> and joins the lit-cards list. A runner that starts failing a gate is auto-swapped for the next best.</p></div>
      <ProofRing p={d.proof} need={d.lightMinRounds} /><div className="rn-clock"><small>NEXT ROUND</small><Countdown at={d.nextRoundAt} /></div></header>
    <div className={`fp-roundcard m-card ${lit ? 'is-lit' : ''}`} data-testid="round-card">
      <div className="m-row"><span className="m-label">{lit ? '🔥 THIS ROUND · LIT' : '⏳ THIS ROUND · PROVING'}</span><small className="m-dim">{picks.length} runners · equal weight · lane exits</small>
        {picks.length > 0 && <button type="button" className="m-btn primary m-go" onClick={() => use(picks)} data-testid="arena-use-round">Use in my card →</button>}</div>
      <div className="rn-lanes">{LANES.map(([k, ic, name]) => { const rows = picks.filter(p => p.lane === k); return <div key={k} className={`rn-lane lane-${k}`}><header><b>{ic} {name}</b><em>{d.exits[k]}</em></header>
        {rows.length ? rows.map(r => <CoinRow key={r.mint} r={r} live />) : <p className="m-dim rn-empty">—</p>}</div>; })}</div>
      {(d.round?.swaps || []).length > 0 && <div className="fp-swaps">{d.round.swaps.slice(-3).reverse().map(s => <span key={s.at} className="fp-swap">🔁 auto-swapped ${s.out.symbol} → ${s.in.symbol} <small>{s.why[0]}</small></span>)}</div>}
    </div>
    <div className="m-card"><span className="m-label">🔥 LIT CARDS · TRACKED 72H</span>
      {!(d.litCards || []).length ? <p className="m-dim">No round has lit yet. The first lit round lands here with its live paper result.</p>
        : <div className="fp-litlist">{d.litCards.map((c, i) => <div key={c.id} className="fp-lit" style={{ '--i': i }}><span className="fp-litglow" aria-hidden="true" />
          <div className="fp-litcoins">{c.picks.slice(0, 5).map(p => <span key={p.mint} className="fp-ava sm" title={p.symbol}>{p.logo ? <img src={p.logo} alt="" loading="lazy" /> : '🏃'}</span>)}</div>
          <div><b>{c.picks.map(p => `$${p.symbol}`).join(' · ')}</b><small className="m-dim">lit {new Date(c.at * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })} · proof {pc(c.proof?.avgPct)} / {c.proof?.winRate}% won</small></div>
          <b className={`m-num ${c.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pc(c.pct)}</b><button type="button" className="m-btn" onClick={() => use(c.picks)}>Use</button></div>)}</div>}</div>
    {a && <div className="m-card"><span className="m-label">STRATEGIES · $5 PAPER FOR 24H</span><p className="m-dim">{a.outlook?.note || (a.outlook?.style ? `${a.outlook.style}: ${pc(a.outlook.avgPct)} avg over ${a.outlook.runs} runs, ${a.outlook.winRate}% won.` : 'Not enough settled runs yet.')}</p>
      <table className="vd-table"><thead><tr><th>Strategy</th><th>Runs</th><th>Avg</th><th>Won</th><th /></tr></thead><tbody>
      {(a.board || []).map(b => <tr key={b.style}><td><b>{b.style}</b>{a.bestStyle === b.style ? ' 👑' : ''}</td><td>{b.runs}</td><td className={(b.avgPct || 0) >= 0 ? 'm-pos' : 'm-neg'}>{pc(b.avgPct || 0)}</td><td>{Math.round(b.winRate ?? 0)}%</td><td>{b.runs >= a.minSettled && b.avgPct > 0 ? <span className="m-chip ok">proven</span> : <span className="m-chip">needs {a.minSettled}+</span>}</td></tr>)}</tbody></table></div>}
    <small className="m-dim">Paper replays on prices seen after each round — never a promise. Fresh coins can go to zero in minutes; gates and exits cut that, they don't prevent it.</small>
  </section>;
}

// ---- My cards: live cards + every action ------------------------------------------------------------------------------
const balancesOf = async (addr, legs) => Object.fromEntries(await Promise.all(legs.filter(l => l.mint && l.soldUsd == null).map(l => fetch(apiUrl(`/api/reputation/balance/${addr}/${l.mint}`)).then(x => (x.ok ? x.json() : null)).catch(() => null).then(b => [l.mint, b]))));
const solPrice = () => fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL_MINT}`).then(r => r.json()).then(d => Number(d?.[SOL_MINT]?.usdPrice) || 0).catch(() => 0);
export const collectSplit = (pct, legs) => (legs || []).filter(l => l.soldUsd == null).map(l => ({ ...l, pct }));

export function MyCards({ addr }) {
  const [d, setD] = useState(null);
  const [act, setAct] = useState(null);   // {id, kind, ...} — one open action at a time
  const load = useCallback(() => addr && fetch(apiUrl(`/api/reputation/fuses/pnl/${addr}`)).then(r => (r.ok ? r.json() : null)).then(setD).catch(() => {}), [addr]);
  useEffect(() => { load(); const t = setInterval(() => !document.hidden && load(), 30000); window.addEventListener('feeless:fuse-pnl', load);
    return () => { clearInterval(t); window.removeEventListener('feeless:fuse-pnl', load); }; }, [load]);
  const ses = () => { const s = addr && readChatSession(addr); if (!s) toast.error('Open chat once to sign in your wallet first.'); return s; };
  const refresh = () => setTimeout(() => window.dispatchEvent(new Event('feeless:fuse-pnl')), 1200);
  const open = useCallback(async (r, kind, extra = {}) => {
    if (act?.id === r.id && act.kind === kind && !extra.pct) { setAct(null); return; }
    if (kind === 'withdraw' || kind === 'take') {
      const bal = await balancesOf(addr, r.legs); const pct = extra.pct || (kind === 'withdraw' ? 100 : 50);
      setAct({ id: r.id, kind, pct, legs: (extra.legs || r.legs.filter(l => l.soldUsd == null).map(l => l.pairAddress)), bal });
    } else if (kind === 'rebalance' || kind === 'switch') {
      const [bal, solUsd] = await Promise.all([balancesOf(addr, r.legs), solPrice()]);
      setAct({ id: r.id, kind, bal, solUsd });
    } else setAct({ id: r.id, kind, ...extra });
  }, [act, addr]);
  // Alert links: ?collect=<id>&pct= (💸 auto-collect), ?rebalance=<id>, ?unfuse=<id>
  useEffect(() => { if (!d?.rows || act) return; const q = new URLSearchParams(window.location.search); const find = id => id && d.rows.find(x => x.id === id && !x.closed);
    const c = find(q.get('collect')); if (c) { open(c, 'take', { pct: Number(q.get('pct')) || 33 }); return; }
    const rb = find(q.get('rebalance')); if (rb) { open(rb, 'rebalance'); return; }
    const u = find(q.get('unfuse')); if (u) open(u, 'withdraw'); }, [d]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!addr) return <div className="m-card fp-empty"><b>Connect your Solana wallet to see your Fuse cards.</b></div>;
  if (!d) return <div className="m-card"><span className="loader" /> Loading your cards…</div>;
  const openRows = (d.rows || []).filter(r => !r.closed);
  return <section className="fp-cards" data-testid="my-cards">
    <div className="m-row fp-book"><span className="m-label">YOUR FUSE CARDS</span><b className={`m-num ${d.pnlUsd >= 0 ? 'm-pos' : 'm-neg'}`}>{m$(d.pnlUsd)} <small>{pc(d.pnlPct)}</small></b><small className="m-dim">{m$(d.valueUsd)} now · {openRows.length} open</small></div>
    {!openRows.length && <div className="m-card fp-empty"><b>No open cards.</b><small className="m-dim">Build one in the Lab — 3 pools + up to 3 runners.</small></div>}
    <div className="fp-cgrid">{openRows.map(r => <div key={r.id} className="fp-cell"><LiveFuseCard r={r} />
      <div className="fp-acts" role="toolbar" aria-label={`${r.name} actions`}>
        <button type="button" className="m-btn" data-tip="Sell part of chosen legs back to SOL (25 / 50 / 100%)" onClick={() => open(r, 'take')} data-testid={`act-take-${r.id}`}>💰 Take profit</button>
        <button type="button" className={`m-btn ${r.autoYield ? 'is-armed' : ''}`} data-tip="Auto-collect: alert + pre-filled Collect profit when the card is up +X% (sells only the gain). You approve once." onClick={() => open(r, 'yield', { at: r.autoYield?.at || 50 })} data-testid={`act-yield-${r.id}`}>💸 {r.autoYield ? `Auto +${Math.round(r.autoYield.at)}%` : 'Auto-collect'}</button>
        <button type="button" className={`m-btn ${r.drift >= 5 ? 'is-warn' : ''}`} data-tip={`Back to the weights you bought (drift ${Math.round(r.drift || 0)} pts) — one approval`} onClick={() => open(r, 'rebalance')} data-testid={`act-rebalance-${r.id}`}>⚖ Rebalance</button>
        <button type="button" className="m-btn" data-tip="Sell one leg and buy a new pool or runner in one approval" onClick={() => open(r, 'switch')} data-testid={`act-switch-${r.id}`}>⇄ Switch</button>
        <button type="button" className={`m-btn ${r.guard && !r.guard.firedAt ? 'is-armed' : ''}`} data-tip="Take-profit / stop-loss / trailing on the whole card" onClick={() => open(r, 'limits', { tp: r.guard?.tp || 50, sl: r.guard?.sl || 20, trail: r.guard?.trail || '' })} data-testid={`act-limits-${r.id}`}>🎯 Limits</button>
        <button type="button" className="m-btn danger" data-tip="Sell every leg back to SOL — one approval" onClick={() => open(r, 'withdraw')} data-testid={`act-withdraw-${r.id}`}>↩ Withdraw</button>
      </div>
      {act?.id === r.id && <ActionPanel r={r} act={act} setAct={setAct} addr={addr} ses={ses} refresh={refresh} />}
    </div>)}</div>
  </section>;
}

function ActionPanel({ r, act, setAct, addr, ses, refresh }) {
  const close = () => setAct(null);
  const live = r.legs.filter(l => l.soldUsd == null);
  if (act.kind === 'take' || act.kind === 'withdraw') {
    const chosen = r.legs.filter(l => act.legs.includes(l.pairAddress));
    const orders = unfuseOrders(chosen, act.bal, addr, 150, act.pct);
    return <div className="m-card fp-panel" data-testid="act-panel-take">
      {act.kind === 'take' && <><div className="m-seg">{[25, 33, 50, 100].map(p => <button key={p} type="button" className={act.pct === p ? 'active' : ''} onClick={() => setAct({ ...act, pct: p })}>{p}%</button>)}
        {![25, 33, 50, 100].includes(act.pct) && <button type="button" className="active" title="Gain only — your base stays in the card">{act.pct}% · gain only</button>}</div>
        <div className="m-row">{live.map(l => <label key={l.pairAddress} className="m-toggle"><input type="checkbox" checked={act.legs.includes(l.pairAddress)} onChange={e => setAct({ ...act, legs: e.target.checked ? [...act.legs, l.pairAddress] : act.legs.filter(x => x !== l.pairAddress) })} />{l.symbol} <small>{m$(l.heldUsd ?? l.valueUsd)}</small></label>)}</div></>}
      <FuseGo side="sell" orders={orders} position={r.id} onClose={() => { close(); refresh(); }} />
    </div>;
  }
  if (act.kind === 'yield') {
    const save = async off => { const s = ses(); if (!s) return; try { await post('/api/reputation/fuses/auto-yield', { address: addr, session: s, id: r.id, at: Number(act.at) || 50, off }); toast.success(off ? 'Auto-collect off' : `Auto-collect armed at +${act.at}%`); close(); refresh(); } catch (e) { toast.error(e.message); } };
    const gain = Number(act.at) || 50; const sell = (gain / (100 + gain)) * 100;
    return <div className="m-card fp-panel" data-testid="act-panel-yield"><b>💸 Auto-collect profit</b>
      <label className="m-field"><span>Collect when the card is up</span><span className="m-row">+<input className="m-input m-num" inputMode="decimal" value={act.at} onChange={e => setAct({ ...act, at: e.target.value.replace(/[^0-9.]/g, '') })} />%</span></label>
      <p className="m-note">At +{gain}% we alert you (inbox + phone) with <b>Collect profit</b> pre-filled: it sells {sell.toFixed(1)}% of each leg — just the gain — and your base stays in the card. After you collect it re-arms from the new value. <b>FEELESS never signs for you</b>: you approve once, fees only on that sell.</p>
      <div className="fg-acts"><button type="button" className="m-btn primary m-go" onClick={() => save(false)} data-testid="yield-save">Arm auto-collect</button>{r.autoYield && <button type="button" className="m-btn" onClick={() => save(true)}>Turn off</button>}<button type="button" className="m-btn" onClick={close}>Cancel</button></div></div>;
  }
  if (act.kind === 'limits') {
    const save = async off => { const s = ses(); if (!s) return; try { await post('/api/reputation/fuses/guard', { address: addr, session: s, id: r.id, off, tp: Number(act.tp) || 0, sl: Number(act.sl) || 0, trail: Number(act.trail) || 0 }); toast.success(off ? 'Limits off' : 'Limits armed'); close(); refresh(); } catch (e) { toast.error(e.message); } };
    const f = (k, label, sign) => <label className="m-field"><span>{label}</span><span className="m-row">{sign}<input className="m-input m-num" inputMode="decimal" placeholder="off" value={act[k]} onChange={e => setAct({ ...act, [k]: e.target.value.replace(/[^0-9.]/g, '') })} />%</span></label>;
    return <div className="m-card fp-panel" data-testid="act-panel-limits"><b>🎯 Card limits</b><div className="m-row">{f('tp', 'Take profit', '+')}{f('sl', 'Stop loss', '−')}{f('trail', 'Trailing', '')}</div>
      <p className="m-note">Free to set. We check every minute and alert you with a one-tap exit; fees only if you exit.</p>
      <div className="fg-acts"><button type="button" className="m-btn primary m-go" onClick={() => save(false)}>Arm limits</button>{r.guard && <button type="button" className="m-btn" onClick={() => save(true)}>Turn off</button>}<button type="button" className="m-btn" onClick={close}>Cancel</button></div></div>;
  }
  const px = Object.fromEntries(r.legs.map(l => [l.pairAddress, Number(l.priceNow) || 0]));
  const record = (landed, s) => {   // sells close those legs; buys merge into the card
    const sells = landed.filter(l => l.side === 'sell').map(l => l.signature); const buys = landed.filter(l => l.side === 'buy');
    [5000, 20000].forEach(ms => setTimeout(() => {
      if (sells.length) post('/api/reputation/fuses/position/close', { address: addr, session: s, id: r.id, signatures: sells }).catch(() => {});
      if (buys.length) post('/api/reputation/fuses/position/switch', { address: addr, session: s, id: r.id, legs: buys.map(b => ({ pairAddress: b.pairAddress, symbol: b.symbol, role: b.role, signature: b.signature })) }).catch(() => {});
      refresh(); }, ms));
  };
  if (act.kind === 'rebalance') {
    const orders = rebalanceOrders(r, act.bal, px, act.solUsd, addr, 5);
    const auto = async on => { const s = ses(); if (!s) return; try { await post('/api/reputation/fuses/guard', on ? { address: addr, session: s, id: r.id, rebalance: 10 } : { address: addr, session: s, id: r.id, off: true }); toast.success(on ? 'Auto-rebalance on (alerts at 10 pts drift)' : 'Auto-rebalance off'); refresh(); } catch (e) { toast.error(e.message); } };
    return <div className="m-card fp-panel" data-testid="act-panel-rebalance"><div className="m-row"><b>⚖ Rebalance</b><label className="m-toggle"><input type="checkbox" checked={Boolean(r.autoRebalance)} onChange={e => auto(e.target.checked)} data-testid="auto-rebalance" />Auto-rebalance alerts</label></div>
      {!orders.length ? <p className="m-dim">Every leg is within 5 points of its weight — nothing to do.</p>
        : <><ul className="fp-moves">{orders.map(o => <li key={o.leg.pairAddress}>{o.target.symbol}: {o.why}</li>)}</ul><FuseGo side="sell" orders={orders} onLanded={record} onClose={close} /></>}</div>;
  }
  // switch: sell one leg, buy a new coin (by mint) with roughly what it returns
  const leg = r.legs.find(l => l.pairAddress === act.from);
  const sellO = leg ? unfuseOrders([leg], act.bal, addr, 150, 100)[0] : null;
  const solOut = leg && act.solUsd ? ((Number(leg.heldUsd) || 0) / act.solUsd) * 0.97 : 0;
  const buyO = act.toMint && solOut >= 0.001 ? { leg: { pairAddress: act.toPair || act.toMint, symbol: act.toSymbol, role: act.toRole || 'pool' }, target: { mint: act.toMint, symbol: act.toSymbol },
    request: { input_mint: SOL_MINT, output_mint: act.toMint, amount: solOut.toFixed(9).replace(/\.?0+$/, ''), slippage_bps: 150, wallet: addr } } : null;
  return <div className="m-card fp-panel" data-testid="act-panel-switch"><b>⇄ Switch a leg</b>
    <label className="m-field"><span>Sell</span><select className="m-input" value={act.from || ''} onChange={e => setAct({ ...act, from: e.target.value })}><option value="">Pick a leg…</option>{live.map(l => <option key={l.pairAddress} value={l.pairAddress}>{l.symbol} · {m$(l.heldUsd)}</option>)}</select></label>
    <label className="m-field"><span>Buy instead (token address)</span><input className="m-input" placeholder="Paste the new coin's mint" value={act.toMint || ''} onChange={e => setAct({ ...act, toMint: e.target.value.trim(), toSymbol: act.toSymbol || 'NEW' })} /></label>
    <input className="m-input" placeholder="Symbol (shown on your card)" value={act.toSymbol || ''} onChange={e => setAct({ ...act, toSymbol: e.target.value.slice(0, 12) })} />
    {sellO && buyO ? <FuseGo side="sell" orders={[sellO, buyO]} onLanded={record} onClose={close} /> : <small className="m-dim">Pick the leg to sell and the coin to buy — both happen in one approval (≈{solOut.toFixed(3)} SOL moves across).</small>}</div>;
}

// ---- Profile › Fuse receipts ----------------------------------------------------------------------------------------
export function FuseReceipts({ address }) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; if (address) fetch(apiUrl(`/api/reputation/fuses/receipts/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setD(x)).catch(() => {}); return () => { alive = false; }; }, [address]);
  if (!d?.receipts?.length) return null;
  return <section className="wp-card fp-receipts" data-testid="fuse-receipts"><h3>Fuse receipts</h3><ol>{d.receipts.map(r => <li key={r.id}>
    <b>{r.name}</b><small className="m-dim">{r.legs.map(l => l.symbol).join(' · ')} · {new Date((r.at || 0) * 1000).toLocaleDateString()} → {r.closedAt ? new Date(r.closedAt * 1000).toLocaleDateString() : 'open'}</small>
    <span className={r.pnlUsd >= 0 ? 'm-pos' : 'm-neg'}>{m$(r.pnlUsd)} ({pc(r.pnlPct)})</span><small className="m-dim">in {m$(r.costUsd)} · out {m$(r.realizedUsd || r.valueUsd)}</small></li>)}</ol></section>;
}
