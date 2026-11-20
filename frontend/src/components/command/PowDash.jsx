import React, { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, ReferenceLine, ResponsiveContainer, Tooltip, YAxis } from 'recharts';
import { apiUrl } from '../../lib/api';
import { boxRef } from '../../lib/boxRef';
import { TestTag } from './TrueRecord';
import '../../styles/powDash.css';

// ⛏ THE PoW DESK DASHBOARD (Slice 25 · the desk bar, RULINGS 2026-11-20: "each proof type will have a user in it for hours"). The PoW folder opens
// on its coin work, its own look (a gold seam on the dark: the shaft it digs coins out of), never a copy of PoB / PoC: what is open now (the live
// folder, a held coin, a proposal waiting for him), P&L without fees (§1: pool in → pool out, fees on the receipt) with its curve, the coins it
// watches with live prices (our /api/market proxy = DexScreener + our indexes, never GeckoTerminal), the minds' last calls, and its guards (age /
// pool / already-ran) with every coin they stopped. Every number is read from its PoW folders or the live price read; nothing is made up here.
const POLL_MS = 30000;
const TAB_KEY = 'feeless.powDashTab';
const TABS = [['open', 'Open'], ['watch', 'Watching'], ['calls', 'Calls'], ['guards', 'Guards'], ['filed', 'All filed'], ['tools', 'Tools']];
// The buy door's guards (backend/cat_orders.py POOL_MIN_USD / AGE_MIN_MIN / RAN_MAX_H1). Here they only colour a watched coin's live pips: the
// server's own check is the one that stops a buy.
export const GUARD = { pool: 5000, ageMin: 15, ranH1: 300 };
const box = boxRef([640, 900]);
const ENGINE = /^(engine|watcher|the watcher|feeless|plan)$/i;
const NOTE = /researched|^research:/i;   // a mind's research note, not a call
/** A mind's line → the word it called (the talk text the engine files: "picks $X", "final plan: …", "check 2: HOLD …", "on $X: …"). */
export const callWord = t => { const s = String(t || ''); const w = s.match(/\b(SELL|HOLD|BUY)\b/); return w ? w[1] : /^(picks?|takes|proposes|final plan)/i.test(s) ? 'PICK' : /^answers/i.test(s) ? 'ANSWER' : /^on \$/i.test(s) ? 'READ' : 'SAYS'; };
const readTab = () => { try { return localStorage.getItem(TAB_KEY) || 'open'; } catch { return 'open'; } };
const sol = v => (v == null ? '—' : `${v >= 0 ? '+' : '−'}${Math.abs(v) >= 0.01 ? Math.abs(v).toFixed(4) : Math.abs(v).toFixed(6)}`);
const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(Math.abs(v) >= 10 ? 0 : 1)}%`);
const usd = v => (v == null ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(v >= 1e5 ? 0 : 1)}K` : v >= 1 ? `$${v.toFixed(2)}` : `$${v.toFixed(v < 0.01 ? 4 : 3)}`);
const px = v => { const n = Number(v); if (!n) return '—'; if (n >= 1) return `$${n.toFixed(n >= 100 ? 0 : 2)}`; const z = Math.floor(-Math.log10(n)); return `$${n.toFixed(Math.min(12, z + 3))}`; };
const ago = s => { const m = Math.max(0, (Date.now() / 1000 - Number(s || 0)) / 60); return m < 1 ? 'now' : m < 60 ? `${Math.round(m)}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
const nOf = f => f.n ?? String(f.name || '').match(/#(\d+)/)?.[1] ?? '?';
// §1: a PoW settled since the pool legs were kept carries pnlBasis 'pool' (fees apart). Older ones only have their cash fills: said, never hidden.
export const basisOf = f => (f.pnlBasis ? (String(f.pnlBasis).startsWith('pool') ? 'pool' : 'cash') : f.poolSpentSol ? 'pool' : 'cash');

/** Which guard a dropped coin's risk line is (the server writes these words: cat_orders.buy_guards, the holder read, the repeat check). */
export function guardOf(risk) {
  const r = String(risk || '');
  if (/min old|🐣/.test(r)) return 'age';
  if (/pool \$|💧/.test(r)) return 'pool';
  if (/already ran|🚀/.test(r)) return 'ran';
  if (/fingerprint/.test(r)) return 'repeat';
  if (/no holder intel/.test(r)) return 'unread';
  return 'holders';
}
export const GUARD_NAME = { age: ['AGE', `Under ${GUARD.ageMin} min old`], pool: ['POOL', `Pool under $${GUARD.pool.toLocaleString()}`], ran: ['RAN', `Up over ${GUARD.ranH1}% in 1 h`], holders: ['HOLDERS', 'Snipers, bundles, a crew or a few wallets holding it'], repeat: ['REPEAT', 'Same fingerprint as a PoW that lost'], unread: ['UNREAD', 'No holder read yet: it never buys blind'] };

/** Pure: every number on the PoW dashboard, from its folders (newest first) and the live folder. */
export function powNumbers(folders, live = null) {
  const rows = [...(live ? [{ ...live, live: true }] : []), ...(folders || []).filter(Boolean)];
  const trades = rows.filter(f => !f.live && f.pnlPct != null && !f.propose).sort((a, b) => (a.soldAt || a.at || 0) - (b.soldAt || b.at || 0));
  let run = 0; const curve = trades.map(f => { run += Number(f.pnlSol) || 0; return { n: nOf(f), sym: f.sym, v: Number(run.toFixed(9)), d: Number(f.pnlSol) || 0 }; });
  const won = trades.filter(f => Number(f.pnlPct) > 0).length;
  const open = rows.filter(f => f.live || (f.boughtAt && !f.soldAt && f.status !== 'closed') || (f.propose && !f.manual));
  const cash = trades.filter(f => basisOf(f) === 'cash').length;
  const calls = rows.flatMap(f => (f.talk || []).filter(t => t?.by && !ENGINE.test(String(t.by).trim()) && t.text && !NOTE.test(t.text)).map(t => ({ ...t, f }))).sort((a, b) => (b.at || 0) - (a.at || 0)).slice(0, 24);
  const stops = rows.flatMap(f => (f.dropped || []).map(x => ({ ...x, g: guardOf(x.risk), f }))).sort((a, b) => (b.f.at || 0) - (a.f.at || 0));
  const byGuard = stops.reduce((a, x) => ({ ...a, [x.g]: (a[x.g] || 0) + 1 }), {});
  const head = rows[0] || null; const dropped = new Set((head?.dropped || []).map(x => x.mint));
  const seen = new Set(); const watch = [...rows.filter(x => x.live || (x.propose && !x.manual)), ...(head ? [head] : [])].flatMap(f => (f.coins || []).filter(c => c?.mint && !dropped.has(c.mint) && !(f.hidden || []).includes(c.mint)).map(c => ({ ...c, f, pick: f.pick?.mint === c.mint })))
    .filter(c => (seen.has(c.mint) ? false : seen.add(c.mint))).slice(0, 12);
  return { rows, trades, curve, pnl: run, won, winPct: trades.length ? Math.round(100 * won / trades.length) : null, open, cash, calls, stops, byGuard,
    cost: rows.reduce((a, f) => a + (Number(f.cost) || 0), 0), watch, best: trades.reduce((a, f) => (!a || f.pnlPct > a.pnlPct ? f : a), null) };
}

/** Pure: a live DexScreener pair (from /api/market) → the three buy-door pips for a watched coin. */
export function livePips(p, nowMs = Date.now()) {
  if (!p) return null; const liq = Number(p.liquidity?.usd) || 0; const born = Number(p.pairCreatedAt) || 0; const h1 = Number(p.priceChange?.h1);
  return { pool: liq >= GUARD.pool, age: !born || (nowMs - born) / 60000 >= GUARD.ageMin, ran: !(h1 > GUARD.ranH1), liq, ageMin: born ? (nowMs - born) / 60000 : null, h1: Number.isFinite(h1) ? h1 : null };
}

function Curve({ data }) {
  if (data.length < 2) return <span className="pwd-curve is-empty" aria-hidden="true" />;
  const up = data[data.length - 1].v >= 0;
  return <span className={`pwd-curve ${up ? 'is-up' : 'is-dn'}`} data-testid="pwd-curve"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 3, right: 0, bottom: 0, left: 0 }}>
    <defs><linearGradient id="pwdFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="currentColor" stopOpacity={0.45} /><stop offset="100%" stopColor="currentColor" stopOpacity={0} /></linearGradient></defs>
    <YAxis hide domain={['dataMin', 'dataMax']} /><ReferenceLine y={0} stroke="currentColor" strokeOpacity={0.3} strokeDasharray="2 3" />
    <Tooltip cursor={false} contentStyle={{ display: 'none' }} wrapperStyle={{ display: 'none' }} />
    <Area type="monotone" dataKey="v" stroke="currentColor" strokeWidth={1.6} fill="url(#pwdFill)" isAnimationActive={false} /></AreaChart></ResponsiveContainer></span>;
}

function Pips({ on, tip }) { return <span className="pwd-pips" data-tip={tip}>{['age', 'pool', 'ran'].map(k => <i key={k} className={on == null ? '' : on[k] ? 'is-ok' : 'is-bad'} aria-label={`${k} ${on == null ? 'not read' : on[k] ? 'passes' : 'stops it'}`} />)}</span>; }

function Hero({ n, onTab }) {
  const g = n.byGuard; const hard = (g.age || 0) + (g.pool || 0) + (g.ran || 0);
  return <div className="pwd-hero" data-testid="pwd-hero">
    <div className={`pwd-kpi is-pnl ${n.pnl >= 0 ? 'is-up' : 'is-dn'}`} style={{ '--i': 0 }} data-tip={`P&L without fees (§1): the money that came back from the pool minus what reached it, summed over ${n.trades.length} closed trades.${n.cash ? ` ${n.cash} settled before the pool legs were kept: only their cash fills exist, fees in, said on each row.` : ''}`}>
      <small>P&L · NO FEES</small><b className="m-num" data-testid="pwd-pnl">{sol(n.pnl)}<small> SOL</small></b><Curve data={n.curve} /><em>{n.trades.length} trades{n.cash ? ` · ${n.cash} cash-basis` : ''}</em></div>
    <div className="pwd-kpi" style={{ '--i': 1 }} data-tip="Closed PoW trades that made money (fees never count)">
      <small>WON</small><b className="m-num" data-testid="pwd-win">{n.winPct == null ? '—' : `${n.winPct}%`}</b><span className="pwd-bar" aria-hidden="true"><u style={{ transform: `scaleX(${(n.winPct || 0) / 100})` }} /></span><em>{n.won}/{n.trades.length}{n.best ? ` · best $${n.best.sym} ${pct(n.best.pnlPct)}` : ''}</em></div>
    <button type="button" className="pwd-kpi is-go" style={{ '--i': 2 }} onClick={() => onTab('open')} data-tip="The live folder, a coin it holds, or a proposal waiting for you" data-testid="pwd-kpi-open">
      <small>OPEN NOW</small><b className="m-num" data-testid="pwd-open-n">{n.open.length}</b><em>{n.open.length ? n.open.map(f => (f.live ? `● ${f.phase || 'live'}` : f.propose ? 'proposal' : 'holding')).slice(0, 2).join(' · ') : 'nothing open'}</em></button>
    <button type="button" className="pwd-kpi is-go" style={{ '--i': 3 }} onClick={() => onTab('guards')} data-tip="Coins its guards kept it out of: age, pool and already-ran are the hard three; holders, repeats and unread coins count too" data-testid="pwd-kpi-guards">
      <small>GUARDS STOPPED</small><b className="m-num" data-testid="pwd-stops">{n.stops.length}</b>
      <span className="pwd-gmini" aria-hidden="true">{['age', 'pool', 'ran'].map(k => <i key={k}><u style={{ transform: `scaleY(${Math.max(0.08, (g[k] || 0) / Math.max(1, hard))})` }} /></i>)}</span><em>age {g.age || 0} · pool {g.pool || 0} · ran {g.ran || 0}</em></button>
  </div>;
}

function Open({ n, onOpen, onCommand }) {
  if (!n.open.length) return <><p className="pwd-none">Nothing open. Its last trade is filed; a new PoW starts from its chat.</p>{onCommand ? <button type="button" className="m-btn m-go pwd-file" onClick={() => onCommand('file a PoW')} data-tip="Puts “file a PoW” in its chat box. You press send" data-testid="pwd-file">⛏ File a PoW</button> : null}</>;
  return <ol className="pwd-rows" data-testid="pwd-open">{n.open.map((f, i) => { const p = f.pick || {}; const state = f.live ? `● ${String(f.phase || 'live').toUpperCase()}` : f.propose ? 'PROPOSAL' : 'HOLDING';
    return <li key={f.id} className="pwd-row" style={{ '--i': i }}><button type="button" className="pwd-open-b" onClick={() => onOpen(f.id)} data-tip={f.propose ? 'Open it: the proposal, its evidence, and the claim door if you trade it yourself' : 'Open its folder: coins, evidence, the trade'} data-testid={`pwd-open-${f.id}`}>
      <span className={`pwd-state ${f.live ? 'is-live' : f.propose ? 'is-prop' : 'is-hold'}`}>{state}</span>
      <span className="pwd-t"><b>{f.sym || p.sym ? `$${f.sym || p.sym}` : f.name}</b><small>PoW #{nOf(f)} · {f.why ? String(f.why).slice(0, 90) : `${(f.coins || []).length} coins in the folder`}</small></span>
      <span className="pwd-n"><b className="m-num">{f.sol ? `${f.sol}` : '—'}</b><small>SOL size</small></span>
      <span className="pwd-n"><b className="m-num">{f.tp != null ? `+${f.tp}/−${f.sl}` : '—'}</b><small>TP / SL %</small></span>
      <TestTag f={f} /></button></li>; })}</ol>;
}

function Watching({ n, live, err }) {
  if (!n.watch.length) return <p className="pwd-none">No coins in its folder right now. Its next PoW fills this.</p>;
  return <><p className="pwd-src"><i className={live ? 'is-on' : ''} aria-hidden="true" />{live ? 'Live from DexScreener through FEELESS · every 30 s' : err ? 'The live read failed: the folder’s own read shows. It tries again in 30 s.' : 'Reading live prices…'}</p>
    <ol className="pwd-rows is-tape" data-testid="pwd-watch">{n.watch.map((c, i) => { const p = live?.[c.mint]; const pip = livePips(p); const ch = p ? Number(p.priceChange?.h1) : null;
      return <li key={c.mint} className={`pwd-row pwd-coin${c.pick ? ' is-pick' : ''}`} style={{ '--i': i }} data-testid={`pwd-coin-${c.mint}`}>
        <span className="pwd-sym"><b>${c.sym}</b><small>{c.pick ? '★ its pick' : c.src === 'intake' ? 'FEELESS' : c.src === 'pump' ? 'Pump' : c.src === 'dex' ? 'DEX' : c.src || ''}</small></span>
        <span className="pwd-n"><b className="m-num" data-testid={`pwd-px-${c.mint}`}>{p ? px(p.priceUsd) : '—'}</b><small>price</small></span>
        <span className="pwd-n"><b className={`m-num ${ch == null ? '' : ch >= 0 ? 'is-up' : 'is-dn'}`}>{p ? pct(ch) : '—'}</b><small>1 h</small></span>
        <span className="pwd-n"><b className="m-num">{usd(pip ? pip.liq : c.liq)}</b><small>pool</small></span>
        <span className="pwd-n"><b className="m-num">{usd(p ? Number(p.marketCap || p.fdv) : c.mc)}</b><small>cap</small></span>
        <Pips on={pip} tip={pip ? `Age ${pip.ageMin == null ? '?' : `${Math.round(pip.ageMin)} min`} · pool ${usd(pip.liq)} · 1 h ${pct(pip.h1)} — against its guards (≥ ${GUARD.ageMin} min, ≥ $${GUARD.pool.toLocaleString()}, ≤ +${GUARD.ranH1}%)` : 'Not read live yet'} />
      </li>; })}</ol></>;
}

function Calls({ n, onOpen }) {
  if (!n.calls.length) return <p className="pwd-none">No mind has called a coin yet. Each PoW's minds pick one and say why: it lands here.</p>;
  return <ol className="pwd-rows is-dense" data-testid="pwd-calls">{n.calls.map((t, i) => { const w = callWord(t.text); const pick = w === 'PICK'; const m = String(t.text).match(/\$([A-Za-z0-9._-]+)/);
    return <li key={`${t.f.id}${t.at}${i}`} className="pwd-row" style={{ '--i': Math.min(i, 14) }}><button type="button" className="pwd-open-b is-call" onClick={() => onOpen(t.f.id)} data-tip={t.text} data-testid={`pwd-call-${i}`}>
      <span className="pwd-who"><em className={`pwd-word is-${w.toLowerCase()}`}>{w}</em><span className="pwd-mind">{String(t.by).split('/').pop()}</span></span>
      <span className="pwd-t"><b>{t.text}</b><small>PoW #{nOf(t.f)}{m ? ` · $${m[1]}` : ''} · {ago(t.at)} ago{t.f.pnlPct != null && pick ? ` · it went ${pct(t.f.pnlPct)}` : ''}</small></span></button></li>; })}</ol>;
}

function Guards({ n, onOpen }) {
  const ks = ['age', 'pool', 'ran', 'holders', 'repeat', 'unread']; const max = Math.max(1, ...ks.map(k => n.byGuard[k] || 0));
  return <><ol className="pwd-gbars" data-testid="pwd-gbars">{ks.map((k, i) => <li key={k} className={['age', 'pool', 'ran'].includes(k) ? 'is-hard' : ''} style={{ '--i': i }} data-tip={GUARD_NAME[k][1]}>
    <small>{GUARD_NAME[k][0]}</small><span className="pwd-bar" aria-hidden="true"><u style={{ transform: `scaleX(${(n.byGuard[k] || 0) / max})` }} /></span><b className="m-num">{n.byGuard[k] || 0}</b></li>)}</ol>
    {n.stops.length ? <ol className="pwd-rows is-dense" data-testid="pwd-stops-list">{n.stops.slice(0, 40).map((x, i) => <li key={`${x.f.id}${x.mint}`} className="pwd-row" style={{ '--i': Math.min(i, 14) }}><button type="button" className="pwd-open-b is-stop" onClick={() => onOpen(x.f.id)} data-tip={x.risk} data-testid={`pwd-stop-${i}`}>
      <span className={`pwd-g is-${x.g}`}>{GUARD_NAME[x.g][0]}</span><span className="pwd-t"><b>${x.sym} · {String(x.risk).replace(/^[^\w$]+/u, '')}</b><small>PoW #{nOf(x.f)} · {ago(x.f.at)} ago</small></span></button></li>)}</ol>
      : <p className="pwd-none">No coin stopped yet.</p>}</>;
}

function Filed({ n, older, onOpen, onOlder }) {
  return <ol className="pwd-rows is-dense" data-testid="pwd-filed">{n.rows.map((f, i) => { const g = f.pnlPct == null ? null : f.pnlPct > 0 ? 'is-up' : 'is-dn';
    return <li key={f.id} className="pwd-row" style={{ '--i': Math.min(i, 14) }}><button type="button" className="pwd-open-b" onClick={() => onOpen(f.id)} data-tip={`${f.name}${f.why ? ` — ${f.why}` : ''}`} data-testid={`dsk-x-${f.id}`}>
      <em className="m-num pwd-num">#{nOf(f)}</em><span className="pwd-t"><b>{f.kept ? '📌 ' : ''}{f.sym ? `$${f.sym}` : f.live ? 'Live now' : 'No coin bought'}</b><small>{f.live ? `● ${f.phase}` : f.propose ? 'Proposal' : f.pnlPct != null ? `${basisOf(f) === 'pool' ? 'pool basis' : 'cash fills, fees in'}` : f.status || 'filed'} · {ago(f.at)} ago</small></span>
      <span className="pwd-n"><b className={`m-num ${g || ''}`}>{f.pnlPct != null ? pct(f.pnlPct) : '—'}</b><small>{f.pnlSol != null ? `${sol(f.pnlSol)} SOL` : 'P&L'}</small></span>
      <span className="pwd-n"><b className="m-num">{f.cost != null ? usd(Number(f.cost)) : '—'}</b><small>minds</small></span><TestTag f={f} /></button></li>; })}
    {older ? <li className="pwd-row"><button type="button" className="pwd-open-b" onClick={onOlder} data-tip="The single-coin proofs filed before PoW folders" data-testid="dsk-x-old"><em className="m-num pwd-num">🗃</em><span className="pwd-t"><b>Older proofs</b><small>{older} filed before PoW folders</small></span></button></li> : null}</ol>;
}

export function PowDash({ folders, live = null, older = 0, onOpen, onOlder, onCommand, tools = null }) {
  const [tab, setTab] = useState(readTab); const [prices, setPrices] = useState(null); const [err, setErr] = useState(false);
  const n = useMemo(() => powNumbers(folders, live), [folders, live]);
  const mints = n.watch.map(c => c.mint).join(',');
  useEffect(() => { if (!mints) return undefined; let on = true; let first = true;
    const go = () => { if (document.hidden && !first) return; first = false;
      fetch(apiUrl(`/api/market/tokens/solana/${mints}`)).then(r => (r.ok ? r.json() : Promise.reject())).then(list => { if (!on) return; const best = {};
        (Array.isArray(list) ? list : list?.pairs || []).forEach(p => { const m = p?.baseToken?.address; if (m && (!best[m] || (Number(p.liquidity?.usd) || 0) > (Number(best[m].liquidity?.usd) || 0))) best[m] = p; });
        setPrices(best); setErr(false); }).catch(() => on && setErr(true)); };
    go(); const t = setInterval(go, POLL_MS); return () => { on = false; clearInterval(t); }; }, [mints]);
  const go = k => { setTab(k); try { localStorage.setItem(TAB_KEY, k); } catch { /* private window */ } };
  const counts = { open: n.open.length, watch: n.watch.length, calls: n.calls.length, guards: n.stops.length, filed: n.rows.length };
  return <section ref={box} className="pwd" data-testid="pwd">
    <Hero n={n} onTab={go} />
    <div className="m-seg pwd-tabs" role="tablist" aria-label="PoW dashboard">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={e => { go(k); e.currentTarget.scrollIntoView?.({ block: 'nearest', inline: 'nearest' }); }} data-testid={`pwd-tab-${k}`}>
      {k === 'open' && n.open.some(f => f.live) ? <i className="pwd-lamp" aria-hidden="true" /> : null}{l}{counts[k] ? <em className="m-num"> {counts[k]}</em> : null}</button>)}</div>
    <div key={tab} className="pwd-pane" role="tabpanel">
      {tab === 'open' ? <Open n={n} onOpen={onOpen} onCommand={onCommand} /> : tab === 'watch' ? <Watching n={n} live={prices} err={err} /> : tab === 'calls' ? <Calls n={n} onOpen={onOpen} />
        : tab === 'guards' ? <Guards n={n} onOpen={onOpen} /> : tab === 'filed' ? <Filed n={n} older={older} onOpen={onOpen} onOlder={onOlder} /> : <div className="pwd-tools">{tools}</div>}
    </div>
  </section>;
}
