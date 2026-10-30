import { CatWorkbench } from './CatWorkbench';
import { AgentLive, HeadCloud, asModel, catMinds, catCoins } from './AgentLive';
import { MindVitals, TradeChat, AgentLog, catLogItems, useCatEvents, useDeskSkin, DeskBackdrop, SkinPicker } from './CatCockpit';
import { signWord } from './LaunchCat';
import React, { useEffect, useMemo, useState } from 'react';
import { useWallet } from '../../hooks/useWallet';
import { getChatSession } from '../../lib/chatSession';
import { ArrowLeft, Copy } from 'lucide-react';
import NumInput from '../NumInput';
import { LookAvatar } from './CatLook';
import { FeeCatMark } from '../FeeCatMark';
import { catByName } from './catCoats';
import { openWarRoom } from '../WarRoomHost';
import '../../styles/catDesk.css';

// 🤖 ONE AGENT'S DESK (owner, 2026-10-23: "redo the agent detail page … in the same violet meta" — it was the old green paper page: a form
// sidebar, a thin sparkline, a disclosure paragraph). Now: the cat on its own violet stage (it purrs while it hunts, pounces while it holds,
// sleeps when stopped), live vitals as meters (balance vs start, realized, a win ring, slots, TODAY'S LOSS against its daily cap), the P/L curve
// drawn big, each open position as a lit row with a diverging move bar (tap = its war room), what it learned, its brains, and its limits as
// meters you drag. The desk itself never signs or moves SOL; `Real` (CatReal.jsx) turns its buys into proposals YOUR wallet signs.
// `Activity`, `BrainPanel`, `EngineLine`, `Real` come from the agents page.
const sol = v => `${(Number(v) || 0) >= 0 ? '+' : '−'}${Math.abs(Number(v) || 0).toFixed(4)}`;
const short = v => (v ? `${v.slice(0, 5)}…${v.slice(-4)}` : '—');
const RC = 2 * Math.PI * 24;
export const MAX_SLOTS = 5;   // feecat_service.RULES.maxPositions

// pure: the desk's numbers from a cat (one place, so every tile agrees)
export function deskVitals(cat, today = new Date().toISOString().slice(0, 10)) {
  const c = cat || {}; const r = c.risk || {};
  const start = Number(c.startingBalanceSol) || Number(c.pnlHistory?.[0]?.balance) || 10; const bal = Number(c.balanceSol) || 0;
  const closed = (c.wins || 0) + (c.losses || 0); const lossToday = Number((c.dailyLoss || {})[today]) || 0; const cap = Number(r.maxDailyLossSol) || 0;
  return { start, bal, real: Number(c.realizedPnlSol) || 0, total: Number(c.totalPnlSol ?? c.realizedPnlSol) || 0, closed, wr: c.winRate ?? null,
    open: (c.positions || []).length, slots: MAX_SLOTS, lossToday, cap, capUsed: cap > 0 ? Math.min(1, lossToday / cap) : 0,
    mood: c.revoked ? 'sleep' : c.status !== 'running' ? 'sleep' : (c.positions || []).length ? 'pounce' : (Number(c.realizedPnlSol) || 0) > 0 ? 'celebrate' : 'purr' };
}
// pure: the P/L curve as an SVG path (area + line) on a 0..100 × 0..40 box, with the zero line
export function curveOf(points) {
  const v = (points || []).map(p => Number(p?.value) || 0); const xs = v.length > 1 ? v : [0, ...v, ...(v.length ? [] : [0])];
  const lo = Math.min(0, ...xs); const hi = Math.max(0, ...xs); const span = hi - lo || 1;
  const P = xs.map((y, i) => [(i / (xs.length - 1)) * 100, 38 - ((y - lo) / span) * 34]);
  const line = P.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(2)} ${y.toFixed(2)}`).join(' ');
  const zero = 38 - ((0 - lo) / span) * 34;
  return { line, area: `${line} L100 ${zero.toFixed(2)} L0 ${zero.toFixed(2)} Z`, zero, last: xs[xs.length - 1], up: xs[xs.length - 1] >= 0 };
}

function Tile({ k, label, value, sub, fill, tone, tip, children }) {
  return <div className={`kd-tile ${tone || ''}`} style={{ '--i': k }} data-tip={tip}><em>{label}</em><b className="m-num" key={String(value)}>{value}</b>
    {fill != null ? <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, fill))})` }} /></u> : null}{sub ? <small>{sub}</small> : null}{children}</div>;
}

// 🗑 delete for good (owner 2026-10-30: "user keeps the agent forever + an option to perma delete"): retired first, its name typed; the server also
// refuses while its own wallet still holds money
function DeleteForGood({ cat, busy, onAct }) {
  const [t, setT] = useState('');
  return <form className="kd-del" onSubmit={e => { e.preventDefault(); if (t.trim().toLowerCase() === String(cat.name).toLowerCase()) onAct('delete', { text: t.trim() }); }}>
    <input className="m-input" value={t} onChange={e => setT(e.target.value)} placeholder={`type ${cat.name} to delete it`} aria-label="Type the agent's name to delete it" data-testid="kd-del-name" />
    <button type="submit" className="m-btn kd-danger" disabled={busy || t.trim().toLowerCase() !== String(cat.name).toLowerCase()} data-testid="kd-delete" data-tip="Gone for good — withdraw its wallet first">🗑 Delete for good</button></form>;
}
// 🔁 its models can be switched 24 h after you got it (the sealed brief, credit, memory and cloud carry over)
export const MODEL_LOCK_H = 24;
export function lockLeft(createdAt, now = Date.now() / 1000) { return Math.max(0, MODEL_LOCK_H * 3600 - (now - Number(createdAt || 0))); }
function ModelSwitch({ cat, busy, onAct }) {
  const left = lockLeft(cat.createdAt); const [list, setList] = useState(null); const [memory, setMemory] = useState('keep'); const [pick, setPick] = useState(() => [...(cat.brainsCfg.brains || [])]);
  useEffect(() => { if (left > 0 || list) return; fetch('/api/cats/models').then(r => (r.ok ? r.json() : null)).then(d => setList((d?.models || []).filter(m => m.tools).sort((a, b) => (b.intel ?? -1) - (a.intel ?? -1)).slice(0, 40))).catch(() => setList([])); }, [left, list]);
  return <section className="kd-card kd-models" data-testid="kd-models"><header><b>🔁 ITS MODELS</b><small>{left > 0 ? `switchable in ${(left / 3600).toFixed(1)} h` : 'switch any time — its brief, memory + cloud stay'}</small></header>
    {left > 0 ? <i className="kd-lock" aria-hidden="true"><u style={{ transform: `scaleX(${1 - left / (MODEL_LOCK_H * 3600)})` }} /></i>
      : <div className="kd-mpick">{[0, 1].map(i => <select key={i} className="m-input" value={pick[i] || ''} aria-label={`Model ${'AB'[i]}`} onChange={e => setPick(p => { const n = [...p]; n[i] = e.target.value; return n.filter(Boolean); })} data-testid={`kd-model-${i}`}>
        {i ? <option value="">no second model</option> : null}{(list || []).map(m => <option key={m.id} value={m.id}>{m.name} · ♟ {m.intel ?? '—'}</option>)}</select>)}
        <button type="button" className="m-btn m-go" disabled={busy || !pick.length || pick.join() === (cat.brainsCfg.brains || []).join()} onClick={() => onAct('models', { brains: pick, memory })} data-testid="kd-model-save">Switch</button>
        <div className="m-seg kd-mem" role="radiogroup" aria-label="Its memory with the new models">{[['keep', '☁ keep its memory'], ['fresh', '🧹 start fresh']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={memory === k} className={memory === k ? 'is-on' : ''} onClick={() => setMemory(k)} data-testid={`kd-mem-${k}`}>{l}</button>)}</div></div>}
  </section>;
}

// 🛸 its live view (owner 2026-10-30): the demo's layout on its real data — a trading cat: two live bubbles + two real coin charts + its decisions;
// a general cat: the same bubbles over its two cloud browsers (CatWorkbench)
// 🐱 a rule-engine cat (Fee herself, a paper rule trader) has no model minds — it still gets its two live windows: what it holds, then what it just sold,
// its own BUY / SELL calls riding over them, and its log (owner 2026-10-30: "clicking FeeCat from the leaderboard still doesn't show the 2 screens")
function RuleWindows({ cat }) {
  const coins = useMemo(() => catCoins(cat), [cat]); const ev = useCatEvents(cat.id);
  const feed = ev.filter(e => ['BUY', 'SELL'].includes(e.type)).slice(0, 3).reverse().map(e => `🐱 ${e.detail}`.slice(0, 120));
  return <><AgentLive title={`LIVE · ${cat.name}'s view`} coins={coins} feed={feed.length ? feed : [cat.status === 'running' ? '🔎 hunting — it buys only what passes every rule' : '⏸ stopped']} />
    <AgentLog items={catLogItems(cat, ev)} /></>;
}
// (owner 2026-10-30) two live windows on top, then the cockpit: [brain A vitals | skinny bubble chat (+ the head cloud) | brain B vitals], then 📁 its log.
// A general cat's cockpit lives inside CatWorkbench (its windows are its cloud browsers).
function LiveMinds({ cat, onAct, busy, canEdit = true }) {
  const x = useMemo(() => catMinds(cat), [cat]); const coins = useMemo(() => catCoins(cat), [cat]);
  const gen = cat.brainsCfg?.kind === 'general'; const on = cat.status === 'running'; const ev = useCatEvents(gen ? null : cat.id);
  const log = useMemo(() => catLogItems(cat, ev), [cat, ev]);
  if (gen) return <CatWorkbench cat={cat} readOnly={!canEdit} />;
  return <>
    <AgentLive title={`LIVE · ${cat.name}'s two brains`} coins={coins} feed={x.feed.length ? x.feed : [on ? '🔎 hunting — it buys only what passes every rule' : '⏸ stopped — start it to hunt']} />
    <div className="ck-cockpit" data-testid="kd-cockpit">
      <MindVitals cat={cat} model={x.brains[0]} i={0} live={on} />
      <div className="ck-center"><HeadCloud items={x.cloud} /><TradeChat cat={cat} busy={busy} onSend={canEdit ? async t => { await onAct('chime', { text: t }); return true; } : null} /></div>
      <MindVitals cat={cat} model={x.brains[1]} i={1} live={on} />
    </div>
    <AgentLog items={log} />
  </>;
}

export function CatDesk({ cat, busy = false, error = '', onBack, onAct, Activity = null, Brains = null, Engine = null, Real = null, canEdit = true }) {   // canEdit: its owner (visitors from the leaderboard see the view, never the controls)
  const isReal = cat.mode === 'real' && !!cat.realWallet;
  const v = useMemo(() => deskVitals(cat), [cat]); const cv = useMemo(() => curveOf(cat?.pnlHistory), [cat?.pnlHistory]);
  const r = cat.risk || {};
  const [lim, setLim] = useState(() => ({ maxPositionSol: r.maxPositionSol, maxDailyLossSol: r.maxDailyLossSol, allowlist: (r.allowlist || []).join(', '), blocklist: (r.blocklist || []).join(', ') }));
  const [amt, setAmt] = useState(''); const [copied, setCopied] = useState(false);
  const learn = cat.learn?.params || {}; const lessons = (cat.learn?.log || []).slice(-3).reverse();
  const xpNext = 100 * (cat.level || 1); const xpFill = Math.min(1, (Number(cat.xp) || 0) / xpNext);
  const state = cat.revoked ? ['REVOKED', 'off'] : cat.status === 'running' ? [v.open ? `HOLDING ${v.open}` : 'HUNTING', 'on'] : ['STOPPED', 'off'];
  const copy = async () => { try { await navigator.clipboard.writeText(cat.wallet); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* blocked */ } };
  const { wallet, signMessage } = useWallet() || {};
  const saveSkin = async sk => { if (!canEdit) return; const look = { bg: sk.bg, acc: sk.acc };   // Fee's look is the creator's signed change; any other agent's, its owner's
    try { if (cat.isLeader) { const address = wallet?.address; if (!address) return; onAct('skin', { look, address, session: await getChatSession(address, signMessage, { own: true }) }); } else onAct('skin', { look }); } catch { /* declined */ } };
  const [skin, setSkin] = useDeskSkin(cat.skin, saveSkin);
  return <section className={`kd has-skin${skin.bg !== 'night' ? ' is-glass' : ''}`} style={{ '--kd-acc': skin.acc }} data-testid="cat-desk"><DeskBackdrop bg={skin.bg} />
    <button type="button" className="kd-back" onClick={onBack} data-testid="kd-back" data-tip="Back to your agents"><ArrowLeft size={14} /> My agents</button>
    <header className="kd-hero">
      <div className="kd-stage" aria-hidden="true"><i className="kd-spot" /><i className="kd-floor" />{cat.isLeader ? <FeeCatMark full size={170} gesture={v.mood} /> : <LookAvatar cat={catByName(cat.avatar)} look={cat.look} full size={170} large gesture={v.mood} />}</div>
      <div className="kd-id">
        <span className={`kd-state is-${state[1]}`} data-testid="kd-state"><i />{state[0]}</span>
        <h1>{cat.name}<small>@{cat.handle}</small></h1>
        <p className="kd-line">{cat.brainsCfg ? `🧠 ${cat.brainsCfg.brains.map(x => x.split('/').pop()).join(' + ')} · ${cat.brainsCfg.brainMode}` : `⚙ ${cat.strategyLabel || 'Rule trader'} · the Leader's engine`}</p>
        <div className="kd-xp" data-tip={`Level ${cat.level || 1} · ${cat.xp || 0} / ${xpNext} XP — closed trades earn XP`}><b>LVL {cat.level || 1}</b><u><s style={{ transform: `scaleX(${Math.max(0.02, xpFill)})` }} /></u><small>{cat.xp || 0} XP</small></div>
        <button type="button" className="kd-wallet" onClick={copy} data-tip="Its paper wallet id — no keys, no real SOL" data-testid="kd-wallet"><span>PAPER WALLET</span><b>{short(cat.wallet)}</b><Copy size={12} />{copied ? <em>copied</em> : null}</button>
        {Engine}
      </div>
      <div className="kd-acts m-seg" role="group" aria-label="Run the agent">
        {canEdit ? <>{cat.status === 'running' ? <button type="button" className="kd-stop" disabled={busy} onClick={() => onAct('stop')} data-testid="kd-stop" data-tip="Stops new trades now (open paper trades stay)">⏹ Stop</button>
          : <button type="button" className="kd-go" disabled={busy || cat.revoked} onClick={() => onAct('start')} data-testid="kd-start" data-tip="Starts it scanning the live board again">▶ Start</button>}
</> : <span className="kd-visitor" data-tip="You're viewing someone's agent — only its owner runs it">👀 VIEWING</span>}
        {canEdit ? <SkinPicker skin={skin} set={setSkin} /> : null}
        {canEdit ? <button type="button" disabled={busy || cat.revoked} onClick={() => onAct('run')} data-testid="kd-run" data-tip="Run one scan-and-decide cycle right now">⟳ One cycle</button> : null}
      </div>
    </header>
    {error ? <p className="kd-err" role="alert">⚠ {error}</p> : null}
    <div className="kd-tiles">
      <Tile k={0} label="BALANCE" value={`${v.bal.toFixed(3)} SOL`} fill={v.bal / (v.start * 1.5)} sub={`started ${v.start} SOL`} tip="Its paper balance against what it started with" />
      <Tile k={1} label="REALIZED" value={`${sol(v.real)} SOL`} tone={v.real > 0 ? 'up' : v.real < 0 ? 'dn' : ''} sub="price moves · fees apart" tip="Closed trades only — P&L never includes fees" />
      <div className="kd-tile kd-ring" style={{ '--i': 2 }} data-tip={`${cat.wins || 0} won · ${cat.losses || 0} lost`}><svg viewBox="0 0 56 56" aria-hidden="true"><circle className="t" cx="28" cy="28" r="24" />
        <circle className="a" cx="28" cy="28" r="24" strokeDasharray={`${(((v.wr || 0) / 100) * RC).toFixed(1)} ${RC.toFixed(1)}`} /></svg><span><em>WIN RATE</em><b className="m-num">{v.wr == null ? '—' : `${v.wr}%`}</b><small>{v.closed} closed</small></span></div>
      <Tile k={3} label="SLOTS" value={`${v.open}/${v.slots}`} tip="Open paper positions out of the most it may hold"><span className="kd-slots">{Array.from({ length: v.slots }, (_, i) => <i key={i} className={i < v.open ? 'on' : ''} />)}</span></Tile>
      <Tile k={4} label="TODAY'S LOSS" value={`${v.lossToday.toFixed(3)} / ${v.cap || '—'} SOL`} fill={v.capUsed} tone={v.capUsed >= 1 ? 'dn' : v.capUsed > 0.6 ? 'warn' : ''}
        sub={v.capUsed >= 1 ? 'cap hit — no new buys today' : 'its daily loss cap'} tip="Losses closed today against the cap you set — at the cap it stops buying until tomorrow" />
    </div>
    {cat.brainsCfg ? <LiveMinds cat={cat} onAct={onAct} busy={busy} canEdit={canEdit} /> : <RuleWindows cat={cat} />}
    <div className="kd-grid">
      <div className="kd-main">
        {Real}
        <section className="kd-card kd-curve" data-testid="kd-curve"><header><b>📈 P/L CURVE</b><small>{(cat.pnlHistory || []).length} cycles · realized + open</small></header>
          <svg viewBox="0 0 100 40" preserveAspectRatio="none" className={cv.up ? 'up' : 'dn'} aria-label="Profit and loss over its cycles"><defs><linearGradient id="kdArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="currentColor" stopOpacity=".35" /><stop offset="1" stopColor="currentColor" stopOpacity="0" /></linearGradient></defs>
            <line x1="0" x2="100" y1={cv.zero} y2={cv.zero} className="z" /><path d={cv.area} fill="url(#kdArea)" /><path d={cv.line} className="l" /></svg>
          <footer><span>START</span><b className={`m-num ${v.total >= 0 ? 'm-pos' : 'm-neg'}`}>{sol(v.total)} SOL</b><span>NOW</span></footer></section>
        <section className="kd-card"><header><b>🎯 WHAT IT HOLDS</b><small>{v.open ? 'tap a coin for its war room' : 'nothing open'}</small></header>
          {v.open ? <ul className="kd-pos">{cat.positions.map((p, i) => { const ch = Number(p.currentChange) || 0; const held = p.openedAt ? Math.max(1, Math.round((Date.now() / 1000 - p.openedAt) / 60)) : null;
            return <li key={p.pairAddress || p.mint || i} style={{ '--i': i }}><button type="button" onClick={() => p.pairAddress && openWarRoom({ chainId: 'solana', pairAddress: p.pairAddress, baseToken: { address: p.mint, symbol: p.symbol } })}
              data-testid={`kd-pos-${i}`} data-tip={p.reason || 'Open its war room'}><b>${p.symbol}</b><small>{held ? `${held}m held · ` : ''}{Number(p.costSol || p.notionalSol || 0).toFixed(3)} SOL in</small>
              <span className={`kd-move ${ch >= 0 ? 'up' : 'dn'}`}><i><u style={{ transform: `scaleX(${Math.min(1, Math.abs(ch) / 50)})` }} /></i><em className="m-num">{ch >= 0 ? '+' : ''}{ch.toFixed(1)}%</em></span></button></li>; })}</ul>
            : <p className="kd-empty">{cat.status === 'running' ? 'Hunting — it buys only what passes every rule.' : 'Stopped — start it to hunt again.'}</p>}</section>
        {Brains}
        {Object.keys(learn).length || lessons.length ? <section className="kd-card"><header><b>📚 WHAT IT LEARNED</b><small>from its own exits</small></header>
          <div className="kd-learn">{Object.entries(learn).map(([k, x]) => <span key={k}><em>{k === 'runnerTrail' ? 'RUNNER TRAIL' : k === 'takeProfit1' ? 'FIRST TAKE' : k.toUpperCase()}</em><b className="m-num">{x}%</b></span>)}</div>
          {lessons.length ? <ol className="kd-lessons">{lessons.map((x, i) => <li key={i}>{x.note}</li>)}</ol> : null}</section> : null}
        {Activity}
      </div>
      {canEdit ? <aside className="kd-side">
        <section className="kd-card kd-limits"><header><b>🎚 ITS LIMITS</b><small>it can only ever trade less than these</small></header>
          <form onSubmit={e => { e.preventDefault(); onAct('controls', lim); }}>
            {[['maxPositionSol', 'MAX A TRADE', 0.01, 2, 0.01], ['maxDailyLossSol', 'DAILY LOSS CAP', 0.01, 5, 0.01]].map(([k, l, lo, hi, st]) => <label key={k} className="kd-lim">
              <span><em>{l}</em><b className="m-num">{Number(lim[k] || 0).toFixed(2)} SOL</b></span>
              <input type="range" min={lo} max={hi} step={st} value={lim[k] || lo} onChange={e => setLim(x => ({ ...x, [k]: e.target.value }))} data-testid={`kd-${k}`} aria-label={l} />
              <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, (Number(lim[k]) || 0) / Math.max(0.01, v.bal || v.start))})` }} /></u><small>{Math.round(((Number(lim[k]) || 0) / Math.max(0.01, v.bal || v.start)) * 100)}% of its balance</small></label>)}
            <label className="kd-list"><em>ONLY THESE COINS</em><input className="m-input" value={lim.allowlist} onChange={e => setLim(x => ({ ...x, allowlist: e.target.value }))} placeholder="any coin when empty" /></label>
            <label className="kd-list"><em>NEVER THESE</em><input className="m-input" value={lim.blocklist} onChange={e => setLim(x => ({ ...x, blocklist: e.target.value }))} placeholder="none blocked" /></label>
            <button type="submit" className="m-btn m-go" disabled={busy} data-testid="kd-save">Save limits</button></form></section>
        <section className="kd-card kd-wd"><header><b>⏏ WITHDRAW</b><small>paper ledger only</small></header>
          <div><NumInput className="m-input" type="number" min="0.0001" step="0.0001" value={amt} onChange={e => setAmt(e.target.value)} placeholder={v.bal.toFixed(4)} aria-label="Amount to withdraw" />
            <button type="button" className="m-btn" disabled={busy} onClick={() => onAct('withdraw', { amount: amt || v.bal })} data-testid="kd-withdraw">Withdraw</button></div></section>
        <section className="kd-card kd-revoke"><header><b>🔒 RETIRE IT</b><small>stops it for good · frees a slot</small></header>
          <button type="button" className="m-btn kd-danger" disabled={busy || cat.revoked} onClick={() => window.confirm(`Retire ${cat.name} for good? It never trades again.`) && onAct('revoke')} data-testid="kd-revoke">{cat.revoked ? 'Retired' : 'Retire agent'}</button>
          {cat.revoked ? <DeleteForGood cat={cat} busy={busy} onAct={onAct} /> : <small className="kd-keep">♾ yours forever until you retire + delete it</small>}</section>
        {cat.brainsCfg ? <ModelSwitch cat={cat} busy={busy} onAct={onAct} /> : null}
        <p className={`kd-paper${isReal ? ' is-real' : ''}`} data-tip={isReal ? `Its own ledger stays paper (its record); every real move: ${signWord(cat)}` : 'Every entry and exit uses the real live price at that moment; balances are simulated and no key lives in the browser'}>
          {isReal ? (cat.agentWallet ? `💵 REAL · its own wallet · ${cat.agentWallet.mode === 'auto' ? 'auto' : 'you OK each move'}` : '💵 REAL · it proposes · your wallet signs') : '🧪 PAPER · live prices · no real SOL'}</p>
      </aside> : null}
    </div>
  </section>;
}
