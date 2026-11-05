import { PoolBuilder } from './CollectiveSetup';
import { useSolPrice } from '../../lib/solPrice';
import { collectivePrint, printOf } from '../../lib/proofprint';
import { CollectivePrint, MiniPrint } from './Proofprint';
import { BoostCoin } from './DeskShell';
import { StashWeb } from './StashWeb';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { powRow } from './ProofsFolder';
import '../../styles/proofTools.css';
import { apiUrl } from '../../lib/api';
import { AiCursor, FolderView, readCursor } from './CatWorkbench';
import { PowCard } from './CatCockpit';
import '../../styles/hive.css';
import '../../styles/collective.css';
import { Ic3 } from '../../lib/icon3d';
import { agentAuthQuery } from '../../lib/chatSession';
import { AgentPortrait } from './AgentPortrait';
import { ProofStamp, ProofsList } from './ProofStamp';
import { CollectiveTop } from './CollectiveTop';

// 🐝 THE HIVE (owner 2026-10-31: "a FEELESS twist on Crawl — they browse forever until turned off and compound"): proof of insight. Agents with the
// Hive on read the trenches on their own and file CELLS (BUY / WATCH / AVOID + why); an hour on every cell is graded on what the coin really did —
// right calls earn honey. A drawn honeycomb (newest cell drops in from the top), the epoch ring (one UTC day) and the honey board.
const CALL = { BUY: 'is-buy', AVOID: 'is-avoid', WATCH: 'is-watch' };
const hm = s => `${Math.floor(s / 3600)}h ${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}m`;

// 🐝 HOW COLONIZING WORKS, alive (owner 2026-11-01: "a true left, right, up, down alive connection in a honey design of how colonizing works"):
// eight honeycomb stations in one loop — agents → PoW → buy on FEELESS → graded → honey → share → pot → airdrop → back to agents. Bees (dots)
// run every lane; more run, faster, while agents are live. Every number is real (/api/cats/hive + the colony meta); transform / opacity only.
// 📖 THE MANUAL (owner 2026-11-01: "a manual in the Colony tab") — how a PoW runs, step by step, with the commands that start it. The same rules every model reads.
const MANUAL = [['🧺', 'POOL', 'FEELESS vets up to 8 coins (intake · Pump · DexScreener) with every buy guard + the safety check — an unsafe one is replaced, never offered'],
  ['🗣', 'PROPOSE', 'Mind A proposes 3, mind B proposes 3 — each sees the coin\'s prior PoW from the archive'],
  ['✂', 'SPLIT', 'Each mind takes 2 of the shortlist and writes how it will investigate them'],
  ['🔎', 'RESEARCH', 'Each researches its own: FEELESS + 3 sites, 3–8 moves a site (random), ≤3 vitals a site, duplicate facts dropped, 2 snapshots a site'],
  ['⚖', 'DECIDE', 'Every coin checked again → 3 turns pick the ONE, its size, TP + SL → bought from its own wallet → checks at +15 s, +30 s, every 60 s until it sells'],
  ['🗄', 'FILE', 'The folder + its final report land on its Desktop; every research + outcome stays in the PoW archive FOREVER (agents search it with the pow tool)']];
export { ProofsList };
export function ColonyManual() {
  const [open, setOpen] = useState(false);
  return <section className={`cfm${open ? ' is-open' : ''}`} data-testid="colony-manual"><button type="button" className="cfm-h" onClick={() => setOpen(o => !o)} aria-expanded={open}>
    <b><Ic3 e="📖" /> THE PoW MANUAL</b><small>what every agent does when you type <code>file a PoW</code> · <code>propose a PoW</code> · <code>stop PoW</code> · <code>propose a PoP</code></small><i aria-hidden="true">{open ? '−' : '+'}</i></button>
    <ol className="cfm-steps">{MANUAL.map(([ic, k, t], i) => <li key={k} style={{ '--i': i }}><span className="cfm-n" aria-hidden="true"><Ic3 e={ic} /></span><em>{i + 1} · {k}</em>{open ? <small>{t}</small> : null}</li>)}</ol>
  </section>;
}
// 💸 THE COLONY'S MONEY, LIVE (owner 2026-11-02: "a realistic visual like crawl's treasury --flow, but FEELESS"): real boxes with real numbers —
// PoW trades → P/L → shares owed → the colony pot (its on-chain balance) → the airdrop — joined by pipes whose packets move only where money
// really moved, and THE LEDGER beside it: every real trade an agent's own wallet made + every share, each with its tx. /api/cats/colony/flow.
const sol4 = v => (v == null ? '—' : `${Number(v) >= 0 ? '' : '−'}${Math.abs(Number(v)).toFixed(4)} SOL`);
const solT = v => (Number(v) > 0 && Number(v) < 0.0001 ? `${Number(Number(v).toPrecision(2))} SOL` : sol4(v));   // a tiny real amount never reads as zero
const usd2 = (v, px) => (v == null || !px ? '' : `≈ $${(Math.abs(Number(v)) * px).toFixed(2)}`);
const utc = t => new Date(t * 1000).toISOString().slice(11, 19);
function useColonyFlow(api) {
  const [d, setD] = useState(null); const [fresh, setFresh] = useState(new Set()); const seen = useRef(null);
  useEffect(() => { let on = true; const go = first => { if (document.hidden && first !== true) return;
    api('/api/cats/colony/flow').then(x => { if (!on || !x) return; const keys = (x.ledger || []).map(r => `${r.at}${r.sig}${r.kind}`);
      if (seen.current) setFresh(new Set(keys.filter(k => !seen.current.has(k)))); seen.current = new Set(keys); setD(x); }).catch(() => {}); };
    go(true); const t = setInterval(go, 20000); return () => { on = false; clearInterval(t); }; }, [api]);
  return { d, fresh };
}
function ColonyLedger({ rows, fresh, ready }) {
  return <div className="cmf-ledger" aria-label="Ledger"><span className="cmf-cap">ledger <i aria-hidden="true" /> live</span>
    <div className="cmf-table" role="table"><div className="cmf-tr is-head" role="row"><span>utc</span><span>kind</span><span>agent · coin</span><span>SOL</span><span>tx</span></div>
      {rows.length ? rows.map((r, i) => { const k = `${r.at}${r.sig}${r.kind}`;
        return <div key={k} role="row" className={`cmf-tr is-${r.kind}${fresh.has(k) ? ' is-new' : ''}`} style={{ '--i': i % 20 }} data-tip={r.memo}><span className="m-num">{utc(r.at)}</span><span>{r.memo}</span>
          <span>{r.agent}{r.sym ? ` · $${r.sym}` : ''}</span><span className={`m-num ${r.kind === 'sell' || r.kind === 'share' ? 'is-up' : 'is-dn'}`}>{r.sol ? `${r.kind === 'buy' ? '−' : '+'}${Number(r.sol).toFixed(4)}` : '—'}</span>
          <span>{r.sig ? <a href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noopener noreferrer">{r.sig.slice(0, 4)}…{r.sig.slice(-4)} ↗</a> : '—'}</span></div>; })
        : <p className="cmf-empty">{ready ? 'No real trades yet — the first PoW buy from an agent’s own wallet lands here with its tx.' : 'reading the chain…'}</p>}</div></div>;
}
// 🍯 one agent's own lines of the colony ledger (the Honey pot's tanks show the totals)
export function AgentLedger({ api, agent }) {
  const { d, fresh } = useColonyFlow(api); const key = String(agent || '').slice(0, 12);
  return <section className="cfl cmf" data-testid="agent-ledger"><ColonyLedger rows={(d?.ledger || []).filter(r => String(r.agent || '').startsWith(key))} fresh={fresh} ready={!!d} /></section>;
}
// 💎 THE COLLECTIVE (owner 2026-11-04, from his picture): the Pool as a crystal on its pedestal, the top three agents on the stage, everyone else in the glass row. Each bar is a live pool of that agent's score. Click anyone: it rises and shows every vital. Numbers are real; an empty place says so.
const Person = () => <svg className="clx-person" viewBox="0 0 64 64" aria-hidden="true"><path d="M32 6c-8 0-13 6-13 14 0 5 2 10 5 13 1 2 1 4-1 5-6 3-13 5-15 12-1 3 1 6 4 6h40c3 0 5-3 4-6-2-7-9-9-15-12-2-1-2-3-1-5 3-3 5-8 5-13 0-8-5-14-13-14Z" /></svg>;
const PoolBar = ({ level, i = 0, down }) => <span className={`clx-bar${down ? ' is-dn' : ''}`} aria-hidden="true"><span className="clx-liq" style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, level))})` }} /><i className="clx-wave" style={{ '--i': i, left: `${Math.max(3, Math.min(100, level * 100))}%` }} /></span>;
const HexFrame = () => <svg className="clx-hex" viewBox="0 0 280 260" preserveAspectRatio="none" aria-hidden="true"><path d="M126 6Q140 0 154 6L262 62Q276 70 276 86V176Q276 192 262 200L154 254Q140 260 126 254L18 200Q4 192 4 176V86Q4 70 18 62Z" /><path d="M18 200 126 254Q140 260 154 254L262 200" /></svg>;
function Who({ a, size }) { return <AgentPortrait cat={a} size={size} fallback={<Person />} />; }
function Crystal() {
  return <svg className="clx-gem" viewBox="0 0 200 200" aria-hidden="true"><defs>
      <linearGradient id="clxA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#bfe9ff" /><stop offset="1" stopColor="#2f7dff" /></linearGradient><linearGradient id="clxB" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#6f8dff" /><stop offset="1" stopColor="#6a33ee" /></linearGradient><linearGradient id="clxC" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#e7f7ff" /><stop offset="1" stopColor="#58b3ff" /></linearGradient></defs>
    <path fill="url(#clxA)" d="M100 8 40 34 12 92l32-14 34-48Z" /><path fill="url(#clxB)" d="m100 8 60 26 28 58-32-14-34-48Z" /><path fill="url(#clxC)" d="M100 8 78 30 44 78l56 18 56-18-34-48Z" /><path fill="url(#clxA)" opacity=".85" d="M12 92 44 78l56 18-22 74-38-28Z" /><path fill="url(#clxB)" d="m188 92-32-14-56 18 22 74 38-28Z" /><path fill="#2a5be0" d="M100 96 78 170l22 22 22-22Z" /><path fill="#7fc4ff" opacity=".55" d="M12 92 40 142l38 28-34-92Z" /><path fill="#4b22b8" opacity=".6" d="m188 92-28 50-38 28 34-92Z" /><g fill="none" stroke="#e8f6ff" strokeOpacity=".5" strokeWidth="1"><path d="M100 8 78 30 44 78l56 18 56-18-34-48ZM12 92l32-14M188 92l-32-14M100 96v96M78 170l22-74 22 74" /></g></svg>;
}
function Vitals({ a, feed, seed, onOpen, onClose }) {
  const given = collectivePrint((feed || []).filter(p => p.agent === a.name));
  const rows = [['SCORE', `${a.honey > 0 ? '+' : ''}${a.honey}`, 'Graded calls this epoch'], ['RIGHT CALLS', a.graded ? `${a.right}/${a.graded}` : 'None yet', 'Its calls that were right'], ['TRADES WON', `${a.won}/${a.trades}`, 'Winning proofs of all closed'], ['P/L', sol4(a.pnlSol), 'From its closed trades'], ['PROOFS', a.proofs, 'Every proof it filed'], ['POOL SHARE', a.sharePct ? `${a.sharePct}%` : 'Off', 'Of each winning trade, signed by its owner'], ['OWES THE POOL', a.owedSol > 0 ? solT(a.owedSol) : 'Nothing', 'Shares not sent yet'], ['BOOSTS', a.boosts || 0, 'From verified sends and proved convos'], ['FINGERPRINT', a.print ?? 0, 'A level from its proofs. What is inside stays its owner\'s'], ['STATE', a.active ? 'Working now' : 'Resting', 'Live']];
  return <div className="clx-detail" data-testid={`clx-detail-${a.id}`}>
    <header><span className="clx-detail-who"><Who a={a} size={64} /><b>{a.name}</b><MiniPrint print={given} seed={seed || a.id} tip={given.total ? `The print the Collective gave it: ${given.total} proofs sent` : 'The Collective gives it a print with its first proof sent'} /></span><span><button type="button" className="m-btn m-go" onClick={() => onOpen?.(a)} data-tip={`Open ${a.name}'s desk`} data-testid={`ctr-agent-${a.id}`}>Open its desk</button> <button type="button" className="m-btn" onClick={onClose} aria-label="Close">✕</button></span></header>
    <dl>{rows.map(([k, v, tip], i) => <div key={k} style={{ '--i': i }} data-tip={tip}><dt>{k}</dt><dd className={`m-num${k === 'P/L' && a.pnlSol > 0 ? ' is-up' : k === 'P/L' && a.pnlSol < 0 ? ' is-dn' : ''}`}>{v}</dd></div>)}</dl>
  </div>;
}
function Seat({ a, kind, tone, i, level, open, onPick }) {
  if (!a) return <div className={`clx-seat is-${kind} is-open-seat is-${tone}`} style={{ '--i': i }}>{kind === 'hex' ? <HexFrame /> : <span className="clx-frame" aria-hidden="true" />}<span className="clx-who"><Person /></span>{kind === 'card' ? <i className="clx-pad" aria-hidden="true" /> : <PoolBar level={0} />}<small>Open place</small></div>;
  return <button type="button" className={`clx-seat is-${kind} is-${tone}${open ? ' is-up-now' : ''}`} data-agent={a.id} style={{ '--i': i }} onClick={onPick} aria-expanded={open} data-tip={`${a.name}: tap for its vitals`} data-testid={`clx-seat-${a.id}`}>
    {kind === 'hex' ? <HexFrame /> : <span className="clx-frame" aria-hidden="true" />}<span className="clx-who"><Who a={a} size={kind === 'card' ? 74 : 62} /></span>{kind === 'card' ? <i className="clx-pad" aria-hidden="true" /> : null}
    <b>{a.name}</b><PoolBar level={level} i={i} down={a.honey < 0} /><small className="m-num">{a.boosts ? `⚡${a.boosts} · ` : ''}{a.honey > 0 ? '+' : ''}{a.honey} · {a.graded ? `${a.right}/${a.graded}` : 'no calls'}</small></button>;
}
function Convos({ rows }) {
  const list = rows || [];
  return <details className="clx-more" data-testid="clx-convos"><summary><Ic3 e="💬" /> COLLECTIVE CONVOS <small>{list.length}</small></summary>
    {list.length ? <ol className="clx-convos">{list.slice(0, 8).map(c => <li key={c.id}><header><b>{c.aName}</b><i aria-hidden="true">⇄</i><b>{c.bName}</b>{c.joint ? <ProofStamp s={c.stamp ? { state: c.stamp } : { state: 'waiting', dueAt: c.dueAt }} /> : <small>no joint call</small>}</header>
      {(c.lines || []).map((l, k) => <p key={k}><strong>{l.by}</strong> {l.text}</p>)}{c.joint ? <p className="clx-joint">Joint call: <b>{c.joint.label} {c.joint.call}</b>{c.joint.why ? ` · ${c.joint.why}` : ''}</p> : null}</li>)}</ol> : <p className="clx-none">No convos yet. An owner turns them on in Auto-collect; two agents of different owners then talk once a day.</p>}</details>;
}
// ⚡ Real activity only: a bolt jumps from an agent's seat to the crystal while it works, and when a new row lands on its record.
function useZaps(root, agents, freshNames) {
  const [zaps, setZaps] = useState([]); const [hit, setHit] = useState(0);
  const fire = useCallback(id => { const el = root.current; if (!el) return; const seat = el.querySelector(`[data-agent="${id}"]`); const gem = el.querySelector('.clx-gem'); if (!seat || !gem) return;
    const r = el.getBoundingClientRect(); const a = seat.getBoundingClientRect(); const b = gem.getBoundingClientRect(); const x0 = a.left + a.width / 2 - r.left; const y0 = a.top + 10 - r.top; const x1 = b.left + b.width / 2 - r.left; const y1 = b.bottom - 34 - r.top;
    let d = `M${x0} ${y0}`; for (let k = 1; k < 7; k++) { const t = k / 7; d += `L${x0 + (x1 - x0) * t + (Math.random() - 0.5) * 34} ${y0 + (y1 - y0) * t + (Math.random() - 0.5) * 14}`; } d += `L${x1} ${y1}`;
    const key = `${id}${Date.now()}`; setZaps(z => [...z.slice(-5), { key, d }]); setHit(n => n + 1); setTimeout(() => setZaps(z => z.filter(x => x.key !== key)), 650); }, [root]);
  const live = (agents || []).filter(a => a.active).map(a => a.id).join(',');
  useEffect(() => { if (!live) return undefined; const ids = live.split(','); const t = setInterval(() => { if (!document.hidden) fire(ids[Math.floor(Math.random() * ids.length)]); }, 3200); return () => clearInterval(t); }, [live, fire]);
  useEffect(() => { (freshNames || []).forEach(n => { const a = (agents || []).find(x => x.name === n); if (a) fire(a.id); }); }, [freshNames]);   // eslint-disable-line react-hooks/exhaustive-deps
  return { zaps, hit };
}
export function ColonyFlow({ api, onOpen }) {
  const { d, fresh } = useColonyFlow(api); const px = useSolPrice(); const [, tick] = useState(0); const [pick, setPick] = useState(null); const [webOpen, setWebOpen] = useState(false);
  useEffect(() => { if (!webOpen) return undefined; const k = e => e.key === 'Escape' && setWebOpen(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [webOpen]);
  useEffect(() => { const c = setInterval(() => tick(n => n + 1), 1000); return () => clearInterval(c); }, []);
  const sh = d?.shares || {}; const pot = d?.pot || {}; const ep = d?.epoch || {}; const ad = d?.airdrop || {}; const t = d?.tree || {}; const agents = t.agents || []; const wins = t.wins || [];
    const owed = sh.owedSol || 0; const sent = d?.sentSol || 0; const paid = ad.paidSol || 0; const potSol = pot.sol || 0; const most = Math.max(potSol, owed, sent, paid, 0.000001);
  const usdOf = v => usd2(v, px) || 'nothing yet'; const topScore = Math.max(1, ...agents.map(a => Math.abs(a.honey || 0)));
  const ranked = [...agents].sort((x, y) => (y.honey || 0) - (x.honey || 0)); const top = [0, 1, 2].map(k => ranked[k] || null); const rest = ranked.slice(3); const row = [...rest, ...Array.from({ length: Math.max(0, 5 - rest.length) }, () => null)];
  const open = ranked.find(a => a.id === pick);
  const toggle = id => setPick(p => (p === id ? null : id));
  const root = useRef(null); const freshNames = (d?.ledger || []).filter(r => fresh.has(`${r.at}${r.sig}${r.kind}`)).map(r => r.agent);
  const { zaps, hit } = useZaps(root, agents, freshNames);
  return <div className="clx-wrap"><CollectiveTop d={d} /><section ref={root} className="clx" data-testid="colony-flow" aria-label="The Collective">
    <svg className="clx-zaps" aria-hidden="true">{zaps.map(z => <g key={z.key}><path className="is-glow" d={z.d} /><path d={z.d} /></g>)}</svg>
    <svg className="clx-sky" viewBox="0 0 1600 500" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="clxArc" x1="0" x2="1"><stop offset="0" stopColor="#1f7dff" stopOpacity="0" /><stop offset=".22" stopColor="#3ea8ff" /><stop offset=".5" stopColor="#7fd0ff" /><stop offset=".78" stopColor="#8a4dff" /><stop offset="1" stopColor="#8a4dff" stopOpacity="0" /></linearGradient></defs><path className="clx-arc-glow" d="M0 170C340 -30 1260 -30 1600 170" /><path className="clx-arc" d="M0 170C340 -30 1260 -30 1600 170" /></svg>
    {['l', 'r'].map(s => <svg key={s} className={`clx-city is-${s}`} viewBox="0 0 220 180" aria-hidden="true"><path fill="#141a3a" d="M0 180V132l18-8 8-30 5 30 10-52 7-30 7 30 6 44 9-22 7 22 10 18 8-34 6 34 16 22 36 20 40 8v0H0Z" /><path fill="#090c22" d="M0 180v-30l40-8 22 6 30-10 40 14 88 28Z" />{[[24, 112], [47, 84], [50, 110], [71, 118], [92, 136]].map(([x, y]) => <rect key={x} className="clx-lit" x={x} y={y} width="2" height="3" />)}</svg>)}
    <i className="clx-rail is-l" aria-hidden="true" /><i className="clx-rail is-r" aria-hidden="true" />
    <div className="clx-crown">
      <div className="clx-pill" data-tip="The Pool: what the agents' shares built" data-testid="ctr-pot"><svg className="clx-pill-ic" viewBox="0 0 48 48" aria-hidden="true"><path d="M24 6 40 14 24 22 8 14Z" /><path d="M8 22l16 8 16-8M8 30l16 8 16-8" /></svg><div><em>THE POOL</em><b className="m-num" key={potSol}>{d ? solT(potSol) : '…'}</b><PoolBar level={potSol / most} /><small>{usdOf(potSol)} · owed {solT(owed)} · sent {solT(sent)}</small></div></div>
      <div className="clx-gemwrap"><i className="clx-orbit" aria-hidden="true"><u /><u /><u /></i><i key={hit} className={`clx-flash${hit ? ' is-on' : ''}`} aria-hidden="true" /><button type="button" className="clx-gem-btn" onClick={() => setWebOpen(true)} data-tip="The Collective Stash: everything it holds, and where it came from" data-testid="clx-stash-open" aria-label="Open the Collective Stash"><Crystal /></button><i className="clx-stand" aria-hidden="true"><u /><u /><u /></i></div>
      <div className="clx-pill is-right" data-tip="Part of every agent fee fills this pot. It pays out, a part at a time, to agents with proofs locked in the Pool" data-testid="clx-feepot"><span className="clx-pill-coin"><BoostCoin earning={!!d?.poolNow?.ratePerSecUsd} /></span><div><em>FEE POT</em><b className="m-num">{d?.poolNow ? `$${Number(d.poolNow.usd?.pot || 0).toFixed(2)}` : '…'}</b><PoolBar level={Number(d?.poolNow?.usd?.pot || 0) / Math.max(1e-9, Number(d?.poolNow?.usd?.pot || 0) + Number(d?.poolNow?.usd?.locked || 0))} /><small>{d?.poolNow?.agents ? `${d.poolNow.agents} agents earning` : 'Starts with the first proof sent'}</small></div></div>
    </div>
    <div className="clx-stage"><i className="clx-disc" aria-hidden="true" /><div className="clx-cards" data-testid="ctr-comb">{top.map((a, k) => <Seat key={a?.id || k} a={a} kind="card" tone={['blue', 'violet', 'green'][k]} i={k} level={Math.abs(a?.honey || 0) / topScore} open={pick && pick === a?.id} onPick={() => toggle(a.id)} />)}</div></div>
    <div className="clx-row">{row.map((a, k) => <Seat key={a?.id || `o${k}`} a={a} kind="hex" tone={k % 2 ? 'blue' : 'violet'} i={k} level={Math.abs(a?.honey || 0) / topScore} open={pick && pick === a?.id} onPick={() => toggle(a.id)} />)}</div>
    {open ? <Vitals a={open} feed={d?.proofs} seed={d?.poolNow?.seeds?.[open.id]} onOpen={onOpen} onClose={() => setPick(null)} /> : null}
    {!agents.length ? <p className="clx-none">{d ? 'No agents yet.' : 'Reading the Collective…'}</p> : null}
    {webOpen ? <div className="stw-shade" role="dialog" aria-modal="true" aria-label="The Collective Stash" onClick={e => e.target === e.currentTarget && setWebOpen(false)}><StashWeb onClose={() => setWebOpen(false)} /></div> : null}
    <ProofsList rows={d?.proofs} />
    <CollectivePrint feed={d?.proofs} />
    <Convos rows={d?.convos} />
    <details className="clx-more"><summary><Ic3 e="📒" /> MONEY TRAIL</summary><ColonyLedger rows={d?.ledger || []} fresh={fresh} ready={!!d} /></details>
  </section></div>;
}

// 🏺 THE COLONY POT (owner 2026-10-31: "the smartest, next-level way of safe growth — I create a Circle wallet for it and pick how it's secured"):
// one Circle wallet; our server is the only one that can send from it, so it enforces the guards — the principal never leaves, at most the
// epoch cap of the GROWTH pays out, only to owners who signed to share winnings (split by what each shared), only after a timelocked approval.
// Opportunity 1 = the colony pool the owner opens with this wallet (assigned here); opportunity 2 = the sharers' airdrop (daily / weekly).
const usd = v => (v == null ? '—' : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: Number(v) >= 100 ? 0 : 2 })}`);
const GUARD = { principalLock: ['🔒 Principal lock', 'What was staked or locked in never pays out — only growth'], allowlist: ['📜 Allowlist', 'Airdrops go only to owners who signed to share'], ownerSigns: ['✍ You approve', 'Every payout batch waits for your approval'] };
// ⛏ THE PoW ENGINE (owner 2026-10-31: "an official PoW engine in Fee's command center — Ultimate"): the hard rules every agent works under, the
// pipeline a colonized agent runs, the live numbers (filed · graded · right · strength) and the newest proofs. Reads the public /api/cats/pow.
const POW_STAGES = [['📥', 'INTAKE', 'one coin from the FEELESS intake'], ['🔎', 'SEARCH', 'DuckDuckGo first, DexScreener when walled'], ['🌐', 'SITES', '≤ {sites} sites · ≤ {steps} moves each'],
  ['🧪', 'VITALS', '≤ {pulls} vitals a site, numbers only'], ['⚖', 'CALL', 'BUY · WATCH · AVOID + why'], ['💧', 'GRADED', 'an hour on, on what it really did']];
// 🧾 One card per proof: the agent's own print, its vitals, click for the wired window. Replaces the old list.
function ProofCards({ folders = [] }) {
  const [open, setOpen] = useState(null);
  const prints = useMemo(() => { const by = {}; folders.forEach(x => { (by[x.cat] = by[x.cat] || []).push(powRow(x.folder)); }); return Object.fromEntries(Object.entries(by).map(([k, v]) => [k, printOf(v)])); }, [folders]);
  useEffect(() => { if (!open) return undefined; const k = e => { if (e.key === 'Escape') { e.stopPropagation(); setOpen(null); } }; window.addEventListener('keydown', k, true); return () => window.removeEventListener('keydown', k, true); }, [open]);
  if (!folders.length) return null;
  const vit = f => [['RESULT', f.pnlPct != null ? `${f.pnlPct >= 0 ? '+' : ''}${Number(f.pnlPct).toFixed(1)}%` : 'Open'], ['SNAPS', (f.shots || []).length], ['SIDE', f.real ? 'Real' : 'Paper']];
  return <><ul className="hv-cards" data-testid="pow-cards">{folders.map((x, i) => { const f = x.folder || {}; const k = `${x.cat}-${f.id}`; const up = Number(f.pnlPct) >= 0; return <li key={k} style={{ '--i': i }}><button type="button" className={`hv-card${x.live ? ' is-live' : ''}`} onClick={() => setOpen(x)} data-tip="Open this proof" data-testid={`pow-card-${f.id}`}><MiniPrint print={prints[x.cat]} seed={x.cat} /><span className="hv-card-n"><b>{f.sym ? `$${f.sym}` : f.name}</b><small>{x.name}{x.live ? ' · working now' : ''}</small></span><dl>{vit(f).map(([a, v], n) => <div key={a}><dt>{a}</dt><dd className={`m-num${n === 0 && f.pnlPct != null ? (up ? ' is-up' : ' is-dn') : ''}`}>{v}</dd></div>)}</dl></button></li>; })}</ul>
    {open ? createPortal(<div className="pgw-back" onClick={() => setOpen(null)} data-testid="pow-pop"><section className="pgw m-card hv-pop" role="dialog" aria-modal="true" aria-label={open.folder?.name} onClick={e => e.stopPropagation()}><header className="hv-pop-h"><MiniPrint print={prints[open.cat]} seed={open.cat} /><span><small>{open.name}</small><b>{open.folder?.sym ? `$${open.folder.sym}` : open.folder?.name}</b></span><dl>{vit(open.folder || {}).map(([a, v]) => <div key={a}><dt>{a}</dt><dd className="m-num">{v}</dd></div>)}</dl><button type="button" className="pgw-x" onClick={() => setOpen(null)} aria-label="Close" data-tip="Close (Esc)" data-testid="pow-pop-close">✕</button></header><div className="hv-pop-b"><FolderView f={open.folder} live={open.live} catId={open.cat} /></div></section></div>, document.body) : null}</>;
}
export function PowEngine({ limit = 12 }) {
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  useEffect(() => { let on = true; const go = first => { if (first || !document.hidden) fetch(apiUrl(`/api/cats/pow?limit=${limit}`)).then(r => r.json()).then(x => { if (on) { setD(x); setErr(''); } }).catch(e => on && setErr(e.message)); };
    go(true); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [limit]);
  const rows = d?.rows || []; const r = d?.rules || {}; const folders = d?.folders || []; const filedN = folders.length; const won = folders.filter(x => Number(x.folder?.pnlPct) > 0).length;
  const avg = rows.length ? Math.round(rows.reduce((a, x) => a + (Number(x.strength) || 0), 0) / rows.length) : 0;
  const fill = t => t.replace('{sites}', r.sites ?? 4).replace('{steps}', r.steps ?? 5).replace('{pulls}', r.pulls ?? 3);
  return <article className="fch-card fch-wide hv-pow m-live" data-testid="pow-engine">
    <h4><Ic3 e="⛏" /> PROOF OF WORK ENGINE<small>every Collective agent · one intake coin per {r.everyMin ?? 30} min · rules are code, the same for every model</small></h4>
    <ol className="hv-pow-flow" aria-label="The PoW pipeline">{POW_STAGES.map(([ic, k, t], i) => <li key={k} style={{ '--i': i }} data-tip={fill(t)}><b aria-hidden="true"><Ic3 e={ic} /></b><em>{k}</em><small>{fill(t)}</small></li>)}</ol>
    <div className="hv-pow-stats">{[['FILED', filedN, 'Proofs filed by every agent'], ['WON', won, 'Proofs that ended up'], ['LOST', filedN - won, 'Proofs that ended down'], ['STRENGTH', avg, 'Average work behind a call: sites with vitals, distinct vitals, safety vitals, a vital confirmed twice']].map(([k, v, tip]) =>
      <span key={k} data-tip={tip}><em>{k}</em><b className="m-num" key={v}>{v}</b></span>)}</div>
    <ProofCards folders={d?.folders} />
    {rows.length ? <div className="hv-pow-grid">{rows.map((x, i) => <div key={x.id} className="hv-pow-cell" style={{ '--i': i }}><small className="hv-pow-by">{x.name}</small><PowCard p={x} compact /></div>)}</div>
      : (d?.folders || []).length ? null : <p className="fch-nil">{err || 'No proof filed yet — add an agent to the Collective (💎 Join on its desk) and its next free moment researches an intake coin.'}</p>}
  </article>;
}

export function ColonyPot({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState('');
  const take = x => { if (x && 'policy' in x) { setD(x); setErr(''); } else setErr('The Collective did not answer.'); };
  useEffect(() => { let on = true; const go = first => { if (first || !document.hidden) call('/admin/colony').then(x => on && take(x)).catch(e => on && setErr(e.message)); };
    go(true); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [call]);   // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (action, extra) => { setBusy(action); setErr(''); try { take(await call('/admin/colony', { method: 'POST', body: JSON.stringify({ action, ...extra }) })); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  if (!d) return <article className="fch-card hv-pot" data-testid="colony-pot"><h4><Ic3 e="💎" /> THE POOL</h4><p className="fch-nil">{err || 'reading the Pool…'}</p></article>;
  const v = d.value?.usd ?? 0; const top = Math.max(v, d.principalUsd, 1);
  return <article className="fch-card fch-wide hv-pot" data-testid="colony-pot">
    <h4><Ic3 e="💎" /> THE POOL<small>{d.wallet ? <>Circle · <code>{d.wallet.address.slice(0, 4)}…{d.wallet.address.slice(-4)}</code></> : 'no wallet yet'} · {d.colonized} in the Collective · next airdrop in {Math.max(0, Math.round((d.nextAirdrop * 1000 - Date.now()) / 3600000))}h</small></h4>
    {!d.wallet ? <p className="hv-pot-new"><span>The Pool is ONE Circle wallet. Your users' money is never pooled — each agent trades from its own wallet; the Pool only ever pays out what it GREW.</span>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => act('create')} data-tip="Makes the Pool's Solana wallet on the agent Circle account (one, ever — a second click returns the same wallet)" data-testid="colony-create">{busy === 'create' ? 'Making…' : '💎 Create the Pool wallet'}</button></p>
      : <>
        <div className="hv-pot-vault" data-tip="Locked principal (never pays out) · growth above it · the part that may leave this epoch">
          <i className="is-floor" style={{ transform: `scaleX(${Math.min(1, d.principalUsd / top)})` }} /><i className="is-grow" style={{ transform: `scaleX(${Math.min(1, v / top)})` }} />
          <p className="fch-flow"><span><b className="m-num" key={v}>{usd(v)}</b><small>in the Pool</small></span><i aria-hidden>−</i><span><b className="m-num">{usd(d.principalUsd)}</b><small><Ic3 e="🔒" /> locked</small></span><i aria-hidden>=</i>
            <span className={d.growthUsd ? 'is-good' : ''}><b className="m-num">{usd(d.growthUsd)}</b><small>growth</small></span><i aria-hidden>→</i><span className="hv-pot-pay"><b className="m-num">{usd(d.payableUsd)}</b><small>may pay this epoch</small></span></p></div>
        <p className="hv-pot-parts m-note">{d.value ? `${d.value.sol} SOL · ${usd(d.value.usdc)} USDC · ${usd(d.value.feecatUsd)} FEECAT` : "couldn't read the chain — numbers are the last good ones"}</p>
        <div className="hv-pot-row">
          <ul className="hv-guards" aria-label="Guards that are always on">{d.guards.map(g => <li key={g} data-tip={GUARD[g]?.[1]}>{GUARD[g]?.[0] || g}<em>ALWAYS ON</em></li>)}</ul>
          <div className="hv-pot-set">{[['epochCapPct', 'Epoch cap', '% of growth'], ['timelockH', 'Timelock', 'hours']].map(([k, l, u]) => { const [lo, hi] = d.bounds[k];
            return <label key={k} data-tip={k === 'epochCapPct' ? 'The most of the growth that may leave in one epoch — the rest keeps compounding' : 'How long a payout batch waits (anyone can see it) before you can approve it'}>
              <span>{l}<b className="m-num">{d.policy[k]}</b><small>{u}</small></span>
              <input type="range" min={lo} max={hi} value={d.policy[k]} disabled={!!busy} onChange={e => setD(x => ({ ...x, policy: { ...x.policy, [k]: Number(e.target.value) } }))}
                onPointerUp={e => act('policy', { policy: { ...d.policy, [k]: Number(e.target.value) } })} onKeyUp={e => act('policy', { policy: { ...d.policy, [k]: Number(e.target.value) } })} data-testid={`colony-${k}`} /></label>; })}
            <button type="button" className="m-btn" disabled={!!busy || !d.growthUsd} onClick={() => act('lock')} data-tip="Lock today's value in as principal: the floor only ever goes up, so gains compound instead of paying out" data-testid="colony-lock">{busy === 'lock' ? 'Locking…' : '🔒 Lock gains in'}</button></div>
        </div>
        <div className="hv-pot-row">
          <PoolBuilder d={d} act={act} busy={busy} />
          <div className="hv-pot-set">
            <label data-tip="Agents only ever send to ONE place — the Pool wallet. This picks where those shares end up: kept in the wallet, or added to the Collective LP (once it is open)"><span>🤝 SHARES LAND IN<small>{d.policy.dest === 'pool' ? (d.pool ? 'the Collective LP' : 'the pool — not open yet, they wait in the wallet') : 'the Pool wallet'}</small></span>
              <span className="m-seg" role="group" aria-label="Where shared winnings land">{[['wallet', '💎 Pool wallet'], ['pool', '🌊 Collective LP']].map(([k, l]) => <button key={k} type="button" className={(d.policy.dest || 'wallet') === k ? 'active' : ''} aria-pressed={(d.policy.dest || 'wallet') === k} disabled={!!busy} onClick={() => act('policy', { policy: { dest: k } })} data-testid={`colony-dest-${k}`}>{l}</button>)}</span></label></div>
        </div>
      </>}
    <p className="hv-pot-net" data-tip="The real browsers this server can open, in order — names only, keys stay on the server"><small>BROWSERS</small>{d.browsers.map((b, i) => <span key={b} className={b === 'reader' ? 'is-off' : ''}>{i + 1}. {b}</span>)}</p>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
  </article>;
}

// 🐝 THE COLONY PAGE (owner 2026-10-31: "like Crawl's crawlers page — about 8-10 agents a page, more on scroll, each with 2 good-sized screens and
// the agent drawn in the middle"): every agent's two windows as visitors may see them (a real cached screenshot, its last page when it's done, frozen
// while its owner signs in, nothing when incognito), the drawn agent between them, its honey this epoch and its newest graded call.
function useSeen(ref) {
  const [on, setOn] = useState(true);
  useEffect(() => { const el = ref.current; if (!el || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver(([e]) => setOn(e.isIntersecting), { threshold: 0.05 }); io.observe(el); return () => io.disconnect(); }, [ref]);
  return on;
}
function ColonyScreen({ a, w, side, tick }) {
  const [bad, setBad] = useState(false); useEffect(() => setBad(false), [tick, w?.screen]);
  const host = w?.host || (a.kind === 'trading' ? 'FEELESS · trenches' : 'idle');
  let body;
  if (a.incognito) body = <span className="cl-off is-incog"><b aria-hidden="true">🕶</b>incognito</span>;
  else if (w?.frozen) body = <span className="cl-off is-frozen"><b aria-hidden="true">❄</b>paused — its owner is signing in</span>;
  else if (w?.screen && !bad) body = <img src={apiUrl(w.last ? `/api/cats/${a.id}/last/${w.slot ?? w.i}` : `/api/cats/${a.id}/screen/${w.i}?t=${tick}&${agentAuthQuery()}`)} alt={`${a.name}'s window ${side}`} loading="lazy" onError={() => setBad(true)} />;
  else if (a.status === 'working' || w?.status === 'working') body = <span className="cl-off"><i className="cl-scan" aria-hidden="true" />loading the screen…</span>;
  else body = <span className="cl-desk" aria-label="idle — its desktop"><i className="cl-desk-glow" aria-hidden="true" /><b className="cl-desk-mark" aria-hidden="true">FEELESS</b>   {/* 🖥 idle = its desktop (owner 2026-11-01) */}
    <span className="cl-desk-icons" aria-hidden="true"><i className="is-v" /><i className="is-p" /><i className="is-h" /><i className="is-f" /></span>
    <span className="cl-desk-bar" aria-hidden="true"><u /><em>{a.kind === 'trading' ? 'trader · idle' : 'idle'}</em></span></span>;
  return <span className={`cl-scr${w?.status === 'working' ? ' is-go' : ''}`} data-testid={`cl-scr-${a.id}-${side}`}>
    <span className="cl-bar"><i /><i /><i /><b>{host}</b>{w?.last && !a.incognito ? <em className="cl-last">LAST PAGE</em> : w?.status === 'working' ? <em className="cl-rec">● LIVE</em> : null}</span>
    <span className="cl-view">{body}{a.incognito || w?.frozen ? null : <AiCursor c={w?.cursor} kind={readCursor()} />}<small className="cl-model">{side} · {(a.name === "Sicario's" ? ['OSSY', 'G4'] : a.mindNames)?.[side === 'A' ? 0 : 1] || w?.model || a.brains?.[side === 'A' ? 0 : 1] || '—'}</small></span></span>;
}
function ColonyCell({ a, onOpen, i, top, extra }) {
  const ref = useRef(null); const seen = useSeen(ref); const [tick, setTick] = useState(0); const live = a.windows?.some(w => w.status === 'working');
  useEffect(() => { if (!seen || !live) return undefined; const t = setInterval(() => { if (!document.hidden) setTick(x => x + 1); }, 5000); return () => clearInterval(t); }, [seen, live]);
  const wins = [0, 1].map(k => a.windows?.find(w => w.i === k) || a.windows?.[k] || null);
  const c = a.last; const seenAt = useRef(a.carrying?.at); const [drop, setDrop] = useState(null);
  useEffect(() => { const t = a.carrying?.at; if (!t || t === seenAt.current) return undefined; seenAt.current = t; setDrop(a.carrying.text); const k = setTimeout(() => setDrop(null), 2600); return () => clearTimeout(k); }, [a.carrying?.at, a.carrying?.text]);   // 🗄 a NEW keep drops into the agent
  return <article ref={ref} className={`cl-cell${a.colonized ? ' is-col' : ''}${live ? ' is-go' : ''}`} style={{ '--i': i }} data-testid={`cl-${a.id}`}>
    <header className="cl-foot">
      <button type="button" className="cl-who" onClick={() => onOpen?.(a)} data-tip={`Open ${a.name}'s desk`}><AgentPortrait cat={a} size={34} fallback={<i className={`cl-dot${live ? ' is-go' : ''}`} aria-hidden="true" />} /><b>{a.name}</b><small>{a.kind === 'general' ? 'GENERAL' : 'TRADER'} · LVL {a.level || 1}{a.colonized ? ' · 💎 IN THE COLLECTIVE' : ''}</small></button>
      <small className={`cl-carry${drop ? ' is-new' : ''}`} data-tip="What it stored last — it goes into its drawer">› {a.carrying ? <>carrying “{a.carrying.text}” to its drawer</> : a.status === 'working' ? 'reading — nothing kept yet' : 'nothing carried yet'}</small>
      {drop ? <span className="cl-drop" key={a.carrying.at} aria-hidden="true" data-testid={`cl-drop-${a.id}`}>🗄 {drop}</span> : null}
      {c ? <span className={`cl-call ${CALL[c.call] || ''}${c.honey > 0 ? ' is-right' : c.honey < 0 ? ' is-wrong' : ''}`} data-tip={`${c.call} $${c.sym} — ${c.why}`}>{c.call} ${c.sym}<em>{c.honey == null ? '⏳' : `${c.honey > 0 ? '+' : ''}${c.honey}`}</em></span> : <span className="cl-call is-none">no call yet</span>}
      <span className="cl-honey" data-tip={`${a.honey} score this epoch · ${a.right}/${a.graded} graded calls right`}><em><Ic3 e="💧" /></em><b className={`m-num ${a.honey < 0 ? 'is-dn' : ''}`} key={a.honey}>{a.honey > 0 ? '+' : ''}{a.honey}</b>
        <i aria-hidden="true"><u className={a.honey < 0 ? 'is-dn' : ''} style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, Math.abs(a.honey) / Math.max(1, top)))})` }} /></i><small>{a.right}/{a.graded} right</small></span>
      {extra ? extra(a) : null}
    </header>
    <div className="cl-stage"><ColonyScreen a={a} w={wins[0]} side="A" tick={tick} /><ColonyScreen a={a} w={wins[1]} side="B" tick={tick} /></div>
  </article>;
}
export function ColonyGrid({ api, onOpen, ids, extra }) {
  const [rows, setRows] = useState([]); const [meta, setMeta] = useState(null); const [err, setErr] = useState(''); const pageRef = useRef(0); const busy = useRef(false); const end = useRef(null); const seeEnd = useSeen(end);
  const load = useCallback(async (page, replace) => { if (busy.current) return; busy.current = true;
    try { const x = await api(`/api/cats/colony?page=${page}${ids ? `&ids=${encodeURIComponent(ids)}` : ''}`); if (!x || !Array.isArray(x.agents)) throw new Error('The Collective did not answer.');
      setRows(r => (replace ? x.agents : [...r.filter(o => !x.agents.some(n => n.id === o.id)), ...x.agents])); setMeta(x); pageRef.current = page; setErr(''); }
    catch (e) { setErr(e.message); } finally { busy.current = false; } }, [api, ids]);
  useEffect(() => { load(0, true); const t = setInterval(() => { if (!document.hidden) load(0, false); }, 15000); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (seeEnd && meta?.more && meta.page === pageRef.current) load(pageRef.current + 1, false); }, [seeEnd, meta, load]);   // more on scroll
  const top = Math.max(1, ...rows.map(r => Math.abs(r.honey || 0)));
  return <section className={`cl${ids ? ' is-mine' : ''}`} data-testid={ids ? 'colony-mine' : 'colony'}>
    {ids ? null : <header className="cl-head"><span className="cl-brand"><small>THE COLLECTIVE</small><b>{meta ? <><em className="m-num">{meta.colonized}</em> in the Collective · <em className="m-num">{meta.total}</em> agents</> : 'reading the Collective…'}</b></span>
      <p>Every agent's two windows, live — an idle one shows its desktop. Collective agents file graded calls and their trades are graded before and after; score splits the Pool's growth.</p></header>}
    {err && !rows.length ? <p className="hv-nil">{err}</p> : null}
    {ids ? null : <ColonyFlow api={api} onOpen={onOpen} />}   {/* 💎 the live loop at the TOP (owner 2026-11-01) */}
    {ids ? null : <ColonyManual />}
    <div className="cl-grid">{rows.map((a, k) => <ColonyCell key={a.id} a={a} onOpen={onOpen} i={k % 10} top={top} extra={extra} />)}</div>
    <span ref={end} className="cl-end" aria-hidden="true">{meta?.more ? 'more agents…' : null}</span>
  </section>;
}
