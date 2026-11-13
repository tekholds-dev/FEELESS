import { KitPick } from './KitPick';
import { useSolPrice } from '../../lib/solPrice';
import { ChatSettings } from '../chat/ChatKit';
import { boostX, dayEarn, GRADE_BASE, limitIn, seatOf, tinyUsd, usePoolRates } from './KeepDeal';
import { usePoolRules } from './SplitFlow';
import React, { Suspense, createContext, lazy, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { useWallet } from '../../hooks/useWallet';
import { Ic3 } from '../../lib/icon3d';
import { FolderArt } from '../../lib/folderArt';
import { fitBox, identityOf, inkOf, ridge, segment, kindIdentity, kindOfFolder } from '../../lib/proofprint';
import '../../styles/proofKit.css';
import '../../styles/kitGallery.css';

// 🧰 THREE TOOLS IN EVERY PROOF FOLDER (owner 2026-11-05). Each one reads the agent's own filed proofs, so a number here is always something that really happened. Too few proofs says so; nothing is ever filled in.
const pct = v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}%`;
const avg = a => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
const count = (list, key) => { const m = {}; list.forEach(x => { const k = key(x); if (k) m[k] = (m[k] || 0) + 1; }); return Object.entries(m).sort((a, b) => b[1] - a[1]); };
const bars = (rows, unit = '') => { const top = Math.max(1, ...rows.map(r => r[1])); return rows.slice(0, 5).map(([l, n]) => ({ l, v: `${n}${unit}`, part: n / top })); };

const Coin3DLazy = lazy(() => import('./Coin3D'));
const SEND_CHIPS = [1, 5, 25, 100];
// 💎 Every proof can go to the Collective with real dollars, $1 or more. Its own wallet signs one transfer, read back from the chain, and the five checks grade it. One small button, so it never crowds a chat: the card opens in a popover, and its second tap sends.
// ⚖ How this proof scores, part by part: each read from its own record by code, each with its weight. What is not known yet earns nothing.
export function WeightBars({ v, testid = 'proof-weights' }) {
  if (!v?.parts) return null;
  return <section className="pwb" data-testid={testid}><header><small>ON ITS RECORD</small><b className={`pwb-rank is-${v.rank}`} data-tip="S, A, B, C, D. S takes deep work, a near full record and every part known" data-testid={`${testid}-rank`}>{v.rank}</b><em className="m-num" data-testid={`${testid}-score`}>{Math.round(v.score)}<small>/{Math.round(v.top)}</small></em></header>
    {v.held ? <p className="pwb-held" data-tip="Simple work, a failed proof or one with no result yet cannot rank high, however well the rest went" data-testid={`${testid}-held`}>{v.held}</p> : null}
    <ul>{v.parts.map(p => <li key={p.key} className={p.value == null ? 'is-unknown' : ''} data-tip={`Worth ${+p.weight.toFixed(1)} of 100`} data-testid={`${testid}-${p.key}`}><span>{p.label}</span><i aria-hidden="true"><u style={{ transform: `scaleX(${p.value || 0})`, '--pwb-w': p.value == null ? 0 : p.value }} /></i><small className="m-num">{+p.weight.toFixed(1)}</small><em>{p.note}</em></li>)}</ul></section>;
}
const perpTitle = f => { const c = (Array.isArray(f?.calls) ? f.calls : []).find(x => x?.market); return c ? `${c.market} ${c.side || ''}`.trim() : ''; };
export const proofTitle = f => f?.name || f?.topic || f?.title || f?.game || f?.sym || perpTitle(f) || `Proof${f?.n ? ` #${f.n}` : ''}`;
const SentCard = ({ sent, f }) => <section className="psub is-sent" data-testid="proof-submit-sent"><span className="psub-said"><b>SENT TO THE COLLECTIVE</b>{sent.usd ? <em className="m-num">${sent.usd}</em> : <em className="m-num">{Number(sent.sol).toFixed(4)} SOL</em>}</span>{(sent.review || f?.review)?.seats ? <ul className="psub-seats" aria-label="The five checks">{(sent.review || f.review).seats.map(x => <li key={x.k} className={x.ok ? 'is-ok' : 'is-no'} data-tip={x.why}>{x.name}</li>)}</ul> : null}{sent.link ? <a className="m-btn" href={sent.link} target="_blank" rel="noopener noreferrer">Tx ↗</a> : null}</section>;
// 🪙 The send itself: the amount, what it can earn, and a second tap to confirm. The proof's popover and the Boost folder both use it.
// 🧮 Before anything is sent (owner 2026-11-07: "users should see the score, how much boost it could get, and why, before they just send"). The grade
// on its own record now, each part and why, how far the three seats can still move it, and what this amount does at this grade against flawless.
const GRADES = new Map();
export const gradeMath = (rules, score, usdIn, pot, rate) => { const x = boostX(score); const seat = seatOf(rules, x, usdIn); const limit = usdIn * x; const day = dayEarn(seat, pot, rate); return { x, seat, limit, day, takes: limitIn(limit, day) }; };
export function GradePreview({ cat, work, f, usdIn }) {
  const [v, setV] = useState(() => GRADES.get(`${cat?.id}:${f?.id}`) ?? null); const rules = usePoolRules(); const rates = usePoolRates();
  useEffect(() => { if (!work || !cat?.id || !f?.id || v) return undefined; let on = true; Promise.resolve().then(() => work(cat.id, { op: 'pool' })).then(j => { const g = j?.weights?.[f.id] || { none: true }; GRADES.set(`${cat.id}:${f.id}`, g); if (on) setV(g); }).catch(() => on && setV({ none: true })); return () => { on = false; }; }, [cat?.id, f?.id, work, v]);
  if (!v) return <p className="gpv-wait" data-testid="grade-wait">Reading its grade…</p>;
  if (v.none || !v.parts) return <p className="gpv-wait" data-testid="grade-none">This kind is graded after it is sent.</p>;
  const top = v.top || rules?.score?.top || GRADE_BASE; const pot = rules?.score?.potUsd ?? 0; const rate = rates?.hotPct ?? 20; const lift = Math.round(0.08 * top);
  const now = gradeMath(rules, v.score, usdIn, pot, rate); const best = gradeMath(rules, top, usdIn, pot, rate); const big = gradeMath(rules, v.score, usdIn, 10000, rate);
  const weak = [...v.parts].filter(p => p.value != null).sort((a, b) => a.value * a.weight - b.value * b.weight).slice(0, 2);
  return <section className="gpv" data-testid="grade-preview">
    <header><span className={`gpv-rank is-${v.rank || 'D'}`} data-tip="S 92%+ · A 78% · B 60% · C 40% · D below">{v.rank || '–'}</span><span><small>ITS GRADE ON ITS RECORD NOW</small><b className="m-num">{Math.round(v.score)}<em> / {top}</em></b><i className="gpv-bar" aria-hidden="true"><u style={{ transform: `scaleX(${Math.min(1, v.score / top)})` }} /></i></span></header>
    <ul className="gpv-parts">{v.parts.map((p, i) => <li key={p.key} style={{ '--i': i }} data-tip={`Weighs ${Math.round(p.weight * 100)} of its grade`}><span>{p.label}</span><i aria-hidden="true"><u style={{ transform: `scaleX(${p.value ?? 0})` }} /></i><b className="m-num">{p.value == null ? '–' : `${Math.round(p.value * 100)}%`}</b><small>{p.note}</small></li>)}</ul>
    {v.held ? <p className="gpv-note is-warn" data-testid="grade-held">Held at {Math.round(v.score)}: {String(v.held)}.</p> : null}
    <p className="gpv-note">After you send, three seats grade it. They can lift it at most {lift} above this, or lower it. {weak.length ? `To grade higher next time: ${weak.map(p => p.label.toLowerCase()).join(' and ')}.` : ''}</p>
    <table className="gpv-math" data-testid="grade-math"><thead><tr><th>${usdIn || 0} sent</th><th>At this grade</th><th>If flawless ({top})</th></tr></thead><tbody>
      <tr><td>Boost</td><td className="m-num">{now.x.toFixed(2)}x</td><td className="m-num">{best.x.toFixed(2)}x</td></tr>
      <tr><td>Most it can earn</td><td className="m-num">{tinyUsd(now.limit)}</td><td className="m-num">{tinyUsd(best.limit)}</td></tr>
      <tr><td>A day, pot today ${Math.round(pot).toLocaleString()}</td><td className="m-num">{tinyUsd(now.day)}</td><td className="m-num">{tinyUsd(best.day)}</td></tr>
      <tr><td>Reaches its limit, pot today</td><td className="m-num">{now.takes}</td><td className="m-num">{best.takes}</td></tr>
      <tr><td>Reaches its limit, at a $10K pot</td><td className="m-num">{big.takes}</td><td className="m-num">{gradeMath(rules, top, usdIn, 10000, rate).takes}</td></tr></tbody></table>
    <p className="gpv-note">{v.score < 100 ? 'Under 100 it is 1x: the most it can earn is what it sends. ' : ''}Pools earn {rate}% a year today and can lose money. Only real pool profit pays.</p>
  </section>;
}
export function ProofSendForm({ cat, work, f, kind, coin = true, onSent = null, rules = null, onUsd = null }) {
  const px = useSolPrice(); const [usd, setUsd] = useState(5); const [sure, setSure] = useState(false); const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [done, setDone] = useState(null);
  const n = Number(usd) || 0; const low = boostX(0) * n; const top = boostX(GRADE_BASE) * n; const seat = seatOf(rules, boostX(GRADE_BASE), n); const least = cat?.ownerStaff ? 0 : 1;   // the owner's own agents may send any amount, to test
  const blocked = kind === 'PoW' && !(Number(f?.pnlPct) >= 50) ? 'A PoW goes only if it won +50% or more' : '';
  const go = async () => { if (!sure) { setSure(true); return; } setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'pot_send', job: f.id, cap: Number((n / px).toFixed(6)) }); const sent = { ...j.sent, link: `https://solscan.io/tx/${j.sent.sig}`, review: j.review, usd: n }; setDone(sent); onSent?.(sent); } catch (e) { setErr(e.message || 'Not sent. Nothing moved.'); } setBusy(false); setSure(false); };
  if (done) return <SentCard sent={done} f={f} />;
  return <section className="psub">{coin ? <span className="psub-coin" aria-hidden="true"><Suspense fallback={null}><Coin3DLazy energy={sure ? 1 : 0.6} size={64} /></Suspense></span> : null}
    <span className="psub-body"><b>SEND THIS PROOF TO THE COLLECTIVE</b><span className="m-seg" role="group" aria-label="Dollars to send">{SEND_CHIPS.map(v => <button key={v} type="button" className={usd === v ? 'active' : ''} aria-pressed={usd === v} onClick={() => { setUsd(v); onUsd?.(v); setSure(false); }} data-testid={`proof-usd-${v}`}>${v}</button>)}</span><input className="m-input m-num" type="number" min={least || 0} step="any" value={usd} onChange={e => { const v = e.target.value === '' ? '' : Number(e.target.value); setUsd(v); onUsd?.(v); setSure(false); }} aria-label="Dollars to send" data-testid="proof-usd" /></span>
    {f?.id && work ? null : <span className="psub-meter" data-tip="Its score decides. A flawless proof scores 300 today, which is 3x. It earns only from real pool profit. It can also earn nothing, and a stake can lose money" data-testid="proof-meter"><small>MOST IT CAN EARN</small><i aria-hidden="true"><u /></i><em className="m-num">${low.toFixed(2)} to ${top.toFixed(2)}</em><small className="m-num">Seat about {seat.toFixed(2)}% if flawless</small></span>}
    <button type="button" className={`m-btn m-go${sure ? ' is-sure' : ''}`} disabled={busy || !px || n <= 0 || n < least || !!blocked} onClick={go} data-tip={blocked || "Its own wallet signs one transfer. It can't be undone, and a stake can lose money"} data-testid="proof-send">{busy ? 'Sending…' : sure ? `Yes, send $${n}` : blocked ? 'Not a +50% win' : n < least ? '$1 minimum' : `Send $${n}`}</button>
    {err ? <small className="kd-err" role="alert" data-testid="proof-send-err">⚠ {err}</small> : null}{f?.id ? <GradePreview cat={cat} work={work} f={f} usdIn={n} /> : null}</section>;
}
// 💸 COL-16: the owner sends this proof WITH his own funds to be graded; on AUTO its agent adds its % from its own wallet. Amounts first, his wallet signs the quote.
const b64 = u8 => btoa(String.fromCharCode(...u8));
export const FundReceipt = ({ r }) => <li className="pfund-rc" data-testid="fund-receipt"><b className="m-num">{Number(r.totalSol).toFixed(4)} SOL</b><span>You {Number(r.userSol).toFixed(4)}{r.agentSig ? ` · its ${r.pct}% ${Number(r.agentSol).toFixed(4)}` : r.agentMissed ? ' · its share did not go' : ''}</span>{r.userSig ? <a href={`https://solscan.io/tx/${r.userSig}`} target="_blank" rel="noopener noreferrer">Yours ↗</a> : null}{r.agentSig ? <a href={`https://solscan.io/tx/${r.agentSig}`} target="_blank" rel="noopener noreferrer">Its ↗</a> : null}</li>;
export function ProofFundForm({ cat, work, f, signer = null }) {
  const w = useWallet() || {}; const provider = signer || w.provider;
  const [sol, setSol] = useState(0.01); const [cfg, setCfg] = useState(cat?.fundGrade || { auto: false, pct: 10 }); const [q, setQ] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [rcs, setRcs] = useState(f?.funds || []);
  const run = async (what, fn) => { setBusy(what); setErr(''); try { await fn(); } catch (e) { setErr(e.message || 'Nothing moved.'); } setBusy(''); };
  const setAuto = patch => run('cfg', async () => { const j = await work(cat.id, { op: 'fund_cfg', tools: patch }); setCfg(j.fundGrade); setQ(null); });
  const quote = () => run('quote', async () => { const j = await work(cat.id, { op: 'fund_quote', job: f.id, cap: Number(sol) }); setQ({ ...j.quote, tx: j.tx }); });
  const send = () => run('send', async () => {
    if (!provider?.signTransaction) throw new Error('Connect the wallet that owns this agent. Nothing moved.');
    const { Transaction } = await import('@solana/web3.js');
    const signed = await provider.signTransaction(Transaction.from(Uint8Array.from(atob(q.tx), c => c.charCodeAt(0))));
    const j = await work(cat.id, { op: 'fund_send', job: f.id, text: q.id, sig: b64(signed.serialize()) }); setRcs(r => [...r, j.receipt]); setQ(null);
  });
  const n = Number(sol) || 0; const share = cfg.auto ? Math.round(n * cfg.pct * 1e4) / 1e6 : 0;
  return <section className="psub pfund" data-testid="proof-fund">
    <span className="psub-body"><b>SEND IT WITH YOUR FUNDS TO BE GRADED</b>
      <input className="m-input m-num" type="number" min="0.001" step="any" value={sol} onChange={e => { setSol(e.target.value === '' ? '' : Number(e.target.value)); setQ(null); }} aria-label="SOL you send" data-testid="fund-sol" /><small>SOL from your wallet</small></span>
    <span className="pfund-auto"><button type="button" className={`m-btn${cfg.auto ? ' is-on' : ''}`} aria-pressed={!!cfg.auto} disabled={!!busy} onClick={() => setAuto({ auto: !cfg.auto })} data-testid="fund-auto" data-tip="On AUTO its agent adds its % from its own wallet, with the same proof">AUTO {cfg.auto ? 'on' : 'off'}</button>
      {cfg.auto ? <label>its share <input className="m-input m-num" type="number" min="1" max="100" step="1" defaultValue={cfg.pct} onBlur={e => Number(e.target.value) !== cfg.pct && setAuto({ pct: Number(e.target.value) })} aria-label="Its share in percent" data-testid="fund-pct" />%</label> : null}</span>
    <ul className="pfund-math" data-testid="fund-math"><li><span>You send</span><b className="m-num">{(q ? q.userSol : n).toFixed(4)} SOL</b></li><li><span>{cfg.auto ? `Its wallet adds ${cfg.pct}%` : 'Its wallet adds'}</span><b className="m-num">{cfg.auto ? `${(q ? q.agentSol : share).toFixed(4)} SOL` : 'nothing (AUTO off)'}</b></li><li className="is-total"><span>To the Collective pot</span><b className="m-num">{(q ? q.totalSol : n + share).toFixed(4)} SOL</b></li></ul>
    {q ? <button type="button" className="m-btn m-go is-sure" disabled={!!busy} onClick={send} data-testid="fund-send" data-tip="Your wallet signs ONE transfer to the pot. It can't be undone, and a stake can lose money">{busy === 'send' ? 'Signing…' : `Sign and send ${q.totalSol.toFixed(4)} SOL`}</button>
      : <button type="button" className="m-btn m-go" disabled={!!busy || n < 0.001} onClick={quote} data-testid="fund-quote">{busy === 'quote' ? 'Quoting…' : 'Quote it'}</button>}
    {err ? <small className="kd-err" role="alert" data-testid="fund-err">⚠ {err}</small> : null}
    {rcs.length ? <ul className="pfund-rcs" aria-label="Sent with funds">{rcs.map(r => <FundReceipt key={r.quote} r={r} />)}</ul> : null}
  </section>;
}
export function ProofSubmit({ cat, work, f, kind }) {
  const [open, setOpen] = useState(false);
  if (!f?.id || f.live) return null;
  if (f.sent) return <SentCard sent={f.sent} f={f} />;
  return <span className="psub-open" data-testid="proof-submit"><ChatSettings open={open} onOpen={setOpen} label="Send this proof to the Collective" tip={cat?.ownerStaff ? 'Send this proof to the Collective. Any amount, to test' : 'Send this proof to the Collective with $1 or more'} testid="proof-open" panelTestid="proof-panel" placement="bottom start" icon={<Ic3 e="🪙" size="22px" />}>{open ? <><ProofSendForm cat={cat} work={work} f={f} kind={kind} /><ProofFundForm cat={cat} work={work} f={f} /></> : null}</ChatSettings><small>Send to the Collective</small></span>;
}
// 📖 The listed sites really opened before the minds answered, and the ones that walled us.
export function SitesRead({ rows }) {
  return rows?.length ? <span className="kit-used" data-testid="sites-read">{rows.map(r => <em key={r.host} className={r.ok ? 'is-on' : ''} data-tip={r.ok ? `Read ${r.host} before answering` : `${r.host} blocked a plain read, so it moved on`}>{r.ok ? '✓' : '✕'} {r.name}</em>)}</span> : null;
}

export function powTools(folders = []) {
  const done = folders.filter(f => f.pnlPct != null);
  const mins = f => (f.soldAt && f.boughtAt ? (f.soldAt - f.boughtAt) / 60 : null);
  const hold = [['Under 5 min', 0, 5], ['5 to 15 min', 5, 15], ['15 to 30 min', 15, 30], ['30 min or more', 30, 1e9]].map(([l, lo, hi]) => { const rows = done.filter(f => mins(f) != null && mins(f) >= lo && mins(f) < hi); const a = avg(rows.map(f => f.pnlPct)); return rows.length ? { l: `${l} · ${rows.length}`, v: pct(a), part: Math.min(1, Math.abs(a) / 30), tone: a >= 0 ? 'up' : 'dn' } : null; }).filter(Boolean);
  const kind = f => { const w = String(f.why || '').toLowerCase(); return w.startsWith('stop') ? 'Its stop' : w.startsWith('take') || w.includes('tp') ? 'Its take profit' : w.includes('watcher') ? 'The watcher' : w.startsWith('trail') ? 'Its trail' : 'Other'; };
  const groups = {}; done.forEach(f => { (groups[kind(f)] = groups[kind(f)] || []).push(f.pnlPct); });
  const exits = Object.entries(groups).sort((a, b) => b[1].length - a[1].length).map(([l, r]) => { const a = avg(r); return { l: `${l} · ${r.length}`, v: pct(a), part: Math.min(1, Math.abs(a) / 30), tone: a >= 0 ? 'up' : 'dn' }; });
  const duel = [0, 1].map(i => { const r = done.filter(f => Number(f.rMind) === i); const w = r.filter(f => f.pnlPct > 0).length; return { l: `Mind ${'AB'[i]} · ${r.length} picked`, v: r.length ? `${Math.round((100 * w) / r.length)}% won` : 'None yet', part: r.length ? w / r.length : 0, tone: 'up' }; });
  return [{ ic: '⏳', t: 'What pays', say: 'Its real result by how long it held', rows: hold, need: 'Shows after its first closed trade', ask: 'What hold time has paid best in your PoW folders, and why?' },
    { ic: '🚪', t: 'How it gets out', say: 'What closed each trade, and how that went', rows: exits, need: 'Shows after its first closed trade', ask: 'Look at how your PoW trades closed. Which exit costs you most?' },
    { ic: '🥊', t: 'Mind against mind', say: 'Whose pick it bought, and who won more', rows: duel.some(d => d.part || d.v !== 'None yet') ? duel : [], need: 'Shows once a mind has picked a trade', ask: 'Which of your two minds picks better coins? Show the numbers.' }];
}
export function popTools(folders = []) {
  const calls = folders.flatMap(f => f.calls || []); const traded = folders.filter(f => !f.noTrade).length;
  const sides = ['long', 'short'].map(s => ({ l: s === 'long' ? 'Long' : 'Short', v: `${calls.filter(c => c.side === s).length}`, part: calls.length ? calls.filter(c => c.side === s).length / calls.length : 0, tone: s === 'long' ? 'up' : 'dn' }));
  const lev = calls.length ? avg(calls.map(c => Number(c.lev) || 0)) : 0; const sl = calls.length ? avg(calls.map(c => Number(c.sl) || 0)) : 0;
  const sources = folders.flatMap(f => Object.values(f.sources || {}).flat()).filter(s => s && s.ok);
  const dev = sources.length ? avg(sources.map(s => Math.abs(Number(s.devBps) || 0))) : 0;
  return [{ ic: '📉', t: 'Its market calls', say: `${folders.length} rounds, ${traded} went on to a paper trade`, rows: calls.length ? [...sides, ...bars(count(calls, c => c.market))] : [], need: 'Shows after its first PoP', ask: 'file a perp' },
    { ic: '🎚', t: 'Its risk', say: 'What it asks for on an average call', rows: calls.length ? [{ l: 'Leverage', v: `${lev.toFixed(1)}x`, part: Math.min(1, lev / 10), tone: lev > 5 ? 'dn' : 'up' }, { l: 'Stop distance', v: `${sl.toFixed(1)}%`, part: Math.min(1, sl / 5) }, { l: 'A stop at this leverage costs', v: `${(lev * sl).toFixed(1)}%`, part: Math.min(1, (lev * sl) / 25), tone: 'dn' }] : [], need: 'Shows after its first PoP', ask: 'Is your leverage too high for your stops? Show the numbers.' },
    { ic: '🌐', t: 'Its price sources', say: 'How close each live source was', rows: sources.length ? [{ l: 'Live sources read', v: `${sources.length}`, part: 1, tone: 'up' }, { l: 'Average gap from the mid price', v: `${dev.toFixed(1)} bps`, part: Math.min(1, dev / 25), tone: dev > 10 ? 'dn' : 'up' }, ...bars(count(sources, s => s.site)).slice(0, 3)] : [], need: 'Shows after its first PoP with live sources', ask: 'Which of your price sources disagree the most, and what does that mean?' }];
}
export function pobTools(folders = []) {
  const calls = folders.flatMap(f => f.calls || []); const picks = calls.flatMap(c => c.picks || []);
  const byMind = [0, 1].map(i => { const r = calls.filter(c => c.mind === i).flatMap(c => c.picks || []); const a = avg(r.map(p => Number(p.confidence) || 0)); return { l: `Mind ${'AB'[i]} · ${r.length} picks`, v: r.length ? `${Math.round(a)}% sure` : 'None yet', part: a / 100, tone: 'up' }; });
  const agreed = folders.flatMap(f => f.agreed || []).length;
  const rate = picks.length ? (2 * agreed) / picks.length : 0;
  return [{ ic: '🎯', t: 'How sure it is', say: 'Average confidence, mind by mind', rows: picks.length ? byMind : [], need: 'Shows after its first PoB', ask: 'file a pob best picks tonight' },
    { ic: '🤝', t: 'Where both agree', say: 'Picks both minds made without seeing each other', rows: picks.length ? [{ l: 'Both picked the same', v: `${agreed}`, part: Math.min(1, rate), tone: 'up' }, { l: 'All picks made', v: `${picks.length}`, part: 1 }] : [], need: 'Shows after its first PoB', ask: 'Which picks did both your minds agree on, and how did they do?' },
    { ic: '🌐', t: 'Sites it trusts', say: 'Where its bids read from', rows: bars(count(folders.flatMap(f => f.sites || []), s => s), ' reads'), need: 'Shows after its first PoB', ask: 'Which sites gave you the most useful facts for your bids?' }];
}
export function pocTools(folders = []) {
  const shots = folders.flatMap(f => f.shots || []); const posted = folders.filter(f => f.result?.link); const earned = posted.reduce((a, f) => a + (Number(f.result?.earnedUsd) || 0), 0); const marked = folders.filter(f => f.graded); const worked = marked.filter(f => f.graded === 'right').length;
  const angles = folders.flatMap(f => (f.calls || []).map(c => c.name || `Mind ${'AB'[c.mind]}`));
  return [{ ic: '🔥', t: 'Where its trends come from', say: 'The pages it read before pitching', rows: bars(count(shots, s => s.site), ' reads'), need: 'Shows after its first PoC', ask: 'file a poc' },
    { ic: '💰', t: 'What posts earn', say: 'From what you reported on each post', rows: folders.length ? [{ l: 'Filed', v: `${folders.length}`, part: 1 }, { l: 'Posted', v: `${posted.length}`, part: posted.length / folders.length, tone: 'up' }, { l: 'Earned per post', v: posted.length ? `$${(earned / posted.length).toFixed(2)}` : '$0.00', part: posted.length ? Math.min(1, earned / posted.length / 50) : 0, tone: 'up' }] : [], need: 'Shows after its first PoC', ask: 'Which of your PoC ideas should I post first, and why?' },
    { ic: '✅', t: 'What worked', say: 'From the marks you gave', rows: marked.length ? [{ l: 'Worked', v: `${worked} of ${marked.length}`, part: worked / marked.length, tone: 'up' }, ...bars(count(angles, a => a)).slice(0, 2)] : [], need: 'Mark an idea and this fills in', ask: 'What do the ideas I marked as working have in common?' }];
}
export function posTools(folders = []) {
  const marked = folders.filter(f => f.graded); const worked = marked.filter(f => f.graded === 'right').length; const weeks = count(folders, f => (f.at ? new Date(f.at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''));
  return [{ ic: '🧪', t: 'Does it work', say: 'Pages you tried and marked', rows: folders.length ? [{ l: 'Filed pages', v: `${folders.length}`, part: 1 }, { l: 'You said it works', v: `${worked} of ${marked.length}`, part: marked.length ? worked / marked.length : 0, tone: 'up' }] : [], need: 'Shows after its first page', ask: 'Which of your pages should I try first?' },
    { ic: '🥊', t: 'Who builds better', say: 'Which mind finished each page', rows: bars(count(folders, f => f.by)), need: 'Shows after its first page', ask: 'Which of your minds builds better pages? Show why.' },
    { ic: '📅', t: 'Its pace', say: 'Pages filed by day', rows: bars(weeks), need: 'Shows after its first page', ask: 'Build me a page. Suggest the idea first.' }];
}
const MAKE = { pow: powTools, pop: popTools, pob: pobTools, poc: pocTools, pos: posTools, poe: (x => poeTools(x)) };
export function poeTools(folders = []) {
  // 📊 PoEco rebuilt (owner 2026-11-13): market calls first — right/wrong from reality — with the old book vitals only when books exist.
  const calls = folders.filter(f => f.kind === 'market'); const won = calls.filter(f => f.graded === 'right').length; const lost = calls.filter(f => f.graded === 'wrong').length; const openN = calls.length - won - lost; const graded = won + lost;
  const market = [{ ic: '📊', t: 'Its record', say: 'Graded by reality alone', rows: calls.length ? [{ l: 'Right', v: `${won}`, part: graded ? won / graded : 0, tone: 'up' }, { l: 'Wrong', v: `${lost}`, part: graded ? lost / graded : 0, tone: 'dn' }, { l: 'Waiting on the horn', v: `${openN}`, part: calls.length ? openN / calls.length : 0 }] : [], need: 'Shows after its first market call', ask: 'How are my market calls doing?' },
    { ic: '⏱', t: 'Open calls', say: 'Sealed, waiting to be graded', rows: calls.filter(f => !f.graded).slice(0, 5).map(f => ({ l: `#${f.n} ${(f.baseline?.pick?.pair || '').split('/')[0]}`, v: f.due * 1000 > Date.now() ? `${Math.max(1, Math.round((f.due * 1000 - Date.now()) / 3.6e6))}h` : 'due', part: Math.max(0.05, Math.min(1, 1 - (f.due * 1000 - Date.now()) / 8.64e7)) })), need: 'Every open call shows here with its clock', ask: 'Which of my market calls grade next?' }];
  const done = folders.filter(f => f.income != null);
  if (!done.length) return market; const net = done.reduce((n, f) => n + Number(f.net || 0), 0); const income = done.reduce((n, f) => n + Number(f.income || 0), 0); const costs = done.reduce((n, f) => n + Number(f.costs || 0), 0); const m = {}; done.forEach(f => (f.cats || []).forEach(c => { m[c.cat] = (m[c.cat] || 0) + c.usd; })); const top = Object.entries(m).sort((a, b) => b[1] - a[1]); const most = Math.max(1, top[0]?.[1] || 0); const money = v => `$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v).toFixed(0)}`;
  return [...market, { ic: '📒', t: 'All its books', say: `${done.length} filed`, rows: done.length ? [{ l: 'Income', v: money(income), part: 1, tone: 'up' }, { l: 'Costs', v: money(costs), part: income ? Math.min(1, costs / income) : 1, tone: 'dn' }, { l: 'Net', v: `${net < 0 ? '−' : ''}${money(net)}`, part: income ? Math.min(1, Math.abs(net) / income) : 0, tone: net >= 0 ? 'up' : 'dn' }] : [], need: 'Shows after its first books', ask: 'How is my business doing across my PoEco books?' },
    { ic: '🧾', t: 'Where it goes', say: 'Biggest costs, all books', rows: top.slice(0, 5).map(([l, v]) => ({ l, v: money(v), part: v / most })), need: 'Shows after its first books', ask: 'Which of my costs should I cut first?' },
    { ic: '✅', t: 'Your marks', say: 'Books you checked', rows: done.length ? [{ l: 'Correct', v: `${done.filter(f => f.graded === 'right').length}`, part: done.filter(f => f.graded === 'right').length / done.length, tone: 'up' }, { l: 'Off', v: `${done.filter(f => f.graded === 'wrong').length}`, part: done.filter(f => f.graded === 'wrong').length / done.length, tone: 'dn' }] : [], need: 'Mark a filed book to draw its line', ask: 'What should I check in my books before I send a proof?' }];
}
// One line per read until you open it, side by side, so the rail never turns into a wall.
export function ProofKit({ kind, folders, onCommand }) {
  const tools = MAKE[kind](folders || []); const [open, setOpen] = useState(-1);
  return <section className="pkt" aria-label="Its tools" data-testid={`pkt-${kind}`}>{tools.map((t, i) => { const on = open === i; const lead = t.rows[0]; return <article key={t.t} className={`pkt-card${on ? ' is-open' : ''}`} style={{ '--i': i }} data-testid={`pkt-${kind}-${i}`}><button type="button" className="pkt-head" aria-expanded={on} onClick={() => setOpen(on ? -1 : i)} data-tip={t.say} data-testid={`pkt-${kind}-open-${i}`}><Ic3 e={t.ic} size="20px" /><span><b>{t.t}</b><small>{lead ? lead.l : t.need}</small></span>{lead ? <em className={`m-num${lead.tone ? ` is-${lead.tone}` : ''}`}>{lead.v}</em> : null}</button>{lead ? <i className="pkt-lead" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, lead.part || 0)})` }} /></i> : null}
    {on ? <div className="pkt-more">{t.rows.length ? <ul>{t.rows.map(r => <li key={r.l} className={r.tone ? `is-${r.tone}` : ''}><span>{r.l}</span><b className="m-num">{r.v}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, r.part || 0)})` }} /></i></li>)}</ul> : <p className="pkt-none">{t.need}</p>}{onCommand ? <button type="button" className="m-btn" onClick={() => onCommand(t.ask)} data-tip="Puts this in its chat box. You press send" data-testid={`pkt-${kind}-ask-${i}`}>Ask it</button> : null}</div> : null}</article>; })}</section>;
}
const KIND_FULL = { pow: 'PROOF OF WORK', pop: 'PROOF OF PERPS', pob: 'PROOF OF BIDS', poc: 'PROOF OF CONTENT', pos: 'PROOF OF CODE', poe: 'PROOF OF ECONOMY' };
const KIND_NAME = { pow: 'PoW', pop: 'PoP', pob: 'PoB', poc: 'PoC', pos: 'PoStatic', poe: 'PoEco' };
const FingerprintLazy = lazy(() => import('./Proofprint').then(m => ({ default: m.ProofFingerprint })));
// 🖊 One folder's own ridge, coloured by its real result: green strong, gold medium, red weak, grey for no result yet.
export const PrintSeed = createContext('agent');
export const PrintLines = createContext({});
const FACE_RINGS = [3, 7, 11, 15];
export function folderFace(seed, kind, fid) { const id = kindIdentity(seed, kind || kindOfFolder(fid), fid); return { id, rings: FACE_RINGS.map(j => ridge(id, j, 40)) }; }
export function FolderRidge({ fid, score = null, size = 26, kind = null }) {
  const seed = useContext(PrintSeed); const line = useContext(PrintLines)[fid]; const face = useMemo(() => folderFace(seed, kind, fid), [seed, kind, fid]); const { id } = face;
  if (line) return <svg className="prg is-line" viewBox={fitBox(line.i * 2 + 4, id)} width={size} height={size} aria-hidden="true" data-ring={line.i}><path d={ridge(id, line.i * 2 + 2, 40)} fill="none" strokeWidth="5" stroke={`${id.ink}66`} /><path d={segment(id, line.i, line.a, line.b)} fill="none" strokeWidth="14" strokeLinecap="round" stroke={inkOf(line.score)} /></svg>;
  return <svg className="prg" viewBox={fitBox(18, id)} width={size} height={size} aria-hidden="true" data-kind={id.kind}>{face.rings.map((d, i) => <path key={i} d={d} fill="none" strokeWidth={i === face.rings.length - 1 ? 12 : 7} stroke={i === face.rings.length - 1 ? (score == null ? id.ink : inkOf(score)) : `${id.ink}88`} />)}</svg>;
}
// 🧾 What something cost, faint until you want it. Click for the receipt. Only real recorded costs: no cost recorded shows nothing.
export const shortCost = v => { const n = Number(v) || 0; if (!n) return '$0'; if (n >= 1) return `$${n.toFixed(2)}`; const t = n.toFixed(n < 0.001 ? 5 : n < 0.01 ? 4 : 3).replace(/0+$/, ''); return `$${t.slice(1)}`; };
export function CostTicket({ usd, rows = null, title = 'Receipt' }) {
  const [open, setOpen] = useState(false); const box = useRef(null);
  useEffect(() => { if (!open) return undefined; const off = e => { if (!box.current?.contains(e.target)) setOpen(false); }; const esc = e => { if (e.key === 'Escape') { e.stopPropagation(); setOpen(false); } }; document.addEventListener('pointerdown', off); window.addEventListener('keydown', esc, true); return () => { document.removeEventListener('pointerdown', off); window.removeEventListener('keydown', esc, true); }; }, [open]);
  if (usd == null) return null;
  return <span className={`cost-t${open ? ' is-open' : ''}`} ref={box}><button type="button" className="cost-t-b m-num" aria-expanded={open} onClick={e => { e.stopPropagation(); setOpen(x => !x); }} data-tip="What this cost. Click for the receipt" data-testid="cost-ticket">{shortCost(usd)}</button>{open ? <span className="cost-t-pop" role="dialog" aria-label={title} onClick={e => e.stopPropagation()}><b>{title.toUpperCase()}</b>{(rows || []).map(([k, v]) => <span key={k} className="cost-t-r"><small>{k}</small><em className="m-num">{v}</em></span>)}<span className="cost-t-r is-total"><small>TOTAL</small><em className="m-num">${(Number(usd) || 0).toFixed(5).replace(/0+$/, '').replace(/\.$/, '.00')}</em></span></span> : null}</span>;
}
// 📁 One proof folder's face, in every proof: the folder, and its own print hovering on its corner.
export function ProofTile({ kind = 'dir', tone = '', ic, label, sub, onOpen, tip, i = 0, testid, print = null, cost = null }) {
  return <button type="button" className={`dsk-ico dsk-xt${tone ? ` is-${tone}` : ''}`} style={{ '--i': i }} onClick={onOpen} data-tip={tip} data-testid={testid}>
    <i className={kind === 'dir' ? 'dsk-ico-art' : 'dsk-file'} aria-hidden="true"><FolderArt ic={ic} file={kind !== 'dir'} lit={tone === 'live'} /></i>
    {print ? <span className="dsk-xt-print"><FolderRidge fid={print[0]} score={print[1]} kind={print[2]} /></span> : null}<span>{label}</span>{sub ? <small className="m-num">{sub}</small> : null}{cost != null ? <small className="dsk-xt-cost m-num">{shortCost(cost)}</small> : null}</button>;
}
// 🪜 Its steps, per proof. The last one says what it needs before it can run the whole loop on its own; until then it proposes.
const STEPS = {
  pow: { steps: ['Reads 4 coins', 'Both minds propose', 'They agree on 1', 'Buys it', 'Holds and watches', 'Sells', 'Files it'], loop: 'Runs the whole loop with its own wallet.', needs: 'Proposes until its wallet is funded.' },
  pop: { steps: ['Reads live prices', 'Both call blind', 'They argue once', 'Proposes to you', 'Paper trade', 'Stops or takes', 'Graded'], loop: 'On paper, on true prices. Nothing real opens.', needs: 'On paper, on true prices. Nothing real opens.' },
  pob: { steps: ['Reads the games', 'Both pick blind', 'Builds the legs', 'Proposes to you', 'Waits for the game', 'Live scores in chat', 'Graded at the final'], loop: 'Picks are filed on paper.', needs: 'Proposes until its Polymarket address is on file.' },
  poc: { steps: ['Reads what is trending', 'Both pitch blind', 'You pick one', 'You post it', 'You report the result', 'Marked'], loop: 'It never posts on its own.', needs: 'Proposes. You post it and report what it earned.' },
  poe: { steps: ['Reads the live pools', 'States its rule', 'Calls it blind', 'Sealed with a hash', 'Reality grades it'], loop: 'Graded by the real numbers alone.', needs: 'Graded by the real numbers alone.' },
  pos: { steps: ['You ask', 'It researches', 'It suggests', 'You approve', 'It builds', 'Second mind reviews', 'You say if it works'], loop: 'Filed once you say it works.', needs: 'Proposes. Publishing needs a host you sign in to.' },
};
const stepNow = (kind, d) => { if (kind === 'pow') { const p = d?.powFolder?.phase; return !p ? -1 : /scan|read|intake/.test(p) ? 0 : /propose|split/.test(p) ? 1 : /choose/.test(p) ? 2 : /buy/.test(p) ? 3 : /hold|watch|run/.test(p) ? 4 : /sell/.test(p) ? 5 : 4; } if (kind === 'pop') return d?.popRead ? 0 : d?.popCard ? 3 : d?.popFolder ? 4 : -1; if (kind === 'pob') { const open = (d?.pobFolders || []).find(f => f.games?.length && !f.graded); const live = open?.games?.some(g => g.state === 'in'); return d?.pobRead ? 0 : live ? 5 : open ? 4 : -1; } return -1; };
function SiteFile({ kind, cat, work, onBrowse }) {
  const [rows, setRows] = useState(null); const [q, setQ] = useState(''); const [add, setAdd] = useState(''); const [said, setSaid] = useState('');
  useEffect(() => { let on = true; fetch(apiUrl(`/api/cats/tools/sources/${kind}`)).then(r => (r.ok ? r.json() : null)).then(j => on && setRows(j?.rows || [])).catch(() => on && setRows([])); return () => { on = false; }; }, [kind]);
  const plug = async e => { e.preventDefault(); if (!add.trim() || !work) return; setSaid(''); try { await work(cat.id, { op: 'refs_add', text: add.trim() }); setSaid(`It reads ${add.trim()} first now.`); setAdd(''); } catch (er) { setSaid(er.message); } };
  const shown = (rows || []).filter(r => !q.trim() || `${r.name} ${r.what} ${r.group}`.toLowerCase().includes(q.trim().toLowerCase())); const groups = [...new Set(shown.map(r => r.group))];
  return <div className="psf" data-testid={`psf-${kind}`}><div className="psf-top"><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder={`Search ${rows?.length || ''} places`} aria-label="Search its sites" data-testid={`psf-q-${kind}`} />{work ? <form onSubmit={plug}><input className="m-input" value={add} onChange={e => setAdd(e.target.value)} placeholder="Plug in your own site" aria-label="Plug in your own site" data-testid={`psf-add-${kind}`} /><button type="submit" className="m-btn m-go" disabled={!add.trim()} data-tip="It reads your sites before this list" data-testid={`psf-plug-${kind}`}>Plug in</button></form> : null}</div>{said ? <small className="psf-said" role="status">{said}</small> : null}
    <p className="psf-note">It looks here before it makes anything, then makes its own version. Once the Stash has 5 graded proofs from a site, real results move it up or down.</p>
    {!rows ? <small>Reading…</small> : groups.map(g => <section key={g}><h5>{g}</h5><ul className="phd-src">{shown.filter(r => r.group === g).map(r => <li key={r.host}><a href={`https://${r.host}`} target="_blank" rel="noopener noreferrer"><b>{r.name}</b><small>{r.what}</small></a>{r.trust != null ? <em className={`m-num ${r.trust >= 50 ? 'is-up' : 'is-dn'}`} data-tip={`${r.won} won, ${r.lost} lost, from the Stash`}>{r.trust}%</em> : r.reads ? <em className="m-num" data-tip="Times it was read, too few graded to trust yet">{r.reads}×</em> : null}{onBrowse ? <button type="button" className="m-btn" onClick={() => onBrowse(r.host.split('/')[0])} data-tip="Opens it in its Browser" data-testid={`phd-open-${r.host}`}>Open</button> : null}</li>)}</ul></section>)}</div>;
}
const KIT_KIND = { pow: 'pow', pop: 'pop', bids: 'pob', poc: 'poc', postatic: 'pos' };
export function ProofHead({ kind, folders, d, cat, pool, work, onBrowse }) {
  const [open, setOpen] = useState(false); const s = STEPS[kind]; const now = stepNow(kind, d); const canLoop = kind === 'pow' && !!(d?.wallet?.address || d?.agentWallet?.address || cat?.agentWallet?.address);
  const costOf = rows => (rows || []).reduce((sum, f) => sum + Number(f.cost ?? f.costUsd ?? 0), 0); const spent = costOf(folders); const known = (folders || []).some(f => f.cost != null || f.costUsd != null); const allKinds = [['PoW', d?.powFolders], ['PoP', d?.popFolders], ['PoB', d?.pobFolders], ['PoC', d?.pocFolders], ['PoStatic', d?.psFolders], ['Jobs', d?.jobs]]; const everything = allKinds.reduce((sum, [, r]) => sum + costOf(r), 0);
  return <section className={`phd m-live is-${kind}`} data-testid={`phd-${kind}`}><div className="phd-top"><span className="phd-print"><Suspense fallback={null}><FingerprintLazy kind={kind} cat={cat} d={d} pool={pool} size={44} /></Suspense></span><span className="phd-t"><em>{KIND_FULL[kind]}</em><b>{KIND_NAME[kind]}</b><small>{(folders || []).length} filed · {canLoop ? s.loop : s.needs}</small>{known ? <small className="phd-cost m-num" data-testid={`phd-cost-${kind}`}>{shortCost(spent)} on these. <CostTicket usd={everything} title="All its model calls" rows={allKinds.map(([k, r]) => [k, shortCost(costOf(r))])} /> on every proof and job</small> : null}</span><button type="button" className="m-btn" aria-expanded={open} onClick={() => setOpen(x => !x)} data-tip="The best places to read for this proof, and your own" data-testid={`phd-src-${kind}`}>Its sites</button></div>
    <ol className="phd-steps">{s.steps.map((t, i) => <li key={t} className={i === now ? 'is-now' : i < now ? 'is-done' : ''}><i className="m-num">{i + 1}</i>{t}</li>)}</ol>
    {work && cat?.id ? <KitPick cat={cat} work={work} kind={KIT_KIND[kind] || 'all'} /> : null}{open ? <SiteFile kind={kind} cat={cat} work={work} onBrowse={onBrowse} /> : null}</section>;
}
