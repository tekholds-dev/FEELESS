import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useWallet } from '../../hooks/useWallet';
import { getChatSession } from '../../lib/chatSession';
import { familiaSwap, FamiliaTradeDock } from '../FamiliaTrade';
import { apiUrl } from '../../lib/api';
import '../../styles/catReal.css';

// 💵 REAL MODE (docs/DECISIONS.md #2 — option A, the owner's go 2026-10-23): your cat keeps hunting on its paper ledger and every buy it makes
// (and every exit of a coin you really bought through it) arrives here as a PROPOSAL — coin, size (never above your per-buy budget), its reason
// and its own paper record. ✍ Sign it opens the swap with the coins + amount set (you press Get quote; your wallet signs, normal swap fee);
// Skip lets it pass; after 15 min it expires (prices moved). FEELESS never holds your SOL or a key. The same proposal reaches your inbox.
const SOL = 'So11111111111111111111111111111111111111112';
const BUDGETS = [0.02, 0.05, 0.1, 0.25, 0.5];
const LIFE = 900;   // cat_real.PROPOSAL_SEC
const short = a => (a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '—');
const clock = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
const STATUS = { failed: ['FAILED', 'bad'], done: ['✓ SIGNED', 'ok'], skip: ['SKIPPED', 'off'], expired: ['EXPIRED', 'off'], replaced: ['REPLACED', 'off'], cancelled: ['CANCELLED', 'off'] };

// pure: the proposals as the panel shows them — pending first (newest first), each with its seconds left
export function realView(cat, now = Date.now() / 1000) {
  const list = (cat?.proposals || []).map(p => ({ ...p, status: p.status === 'pending' && now > p.until ? 'expired' : p.status, left: Math.max(0, Math.round(p.until - now)) }))
    .sort((a, b) => (a.status !== 'pending') - (b.status !== 'pending') || b.at - a.at);
  return { real: cat?.mode === 'real' && !!cat?.realWallet, wallet: cat?.realWallet || null, budget: Number(cat?.budgetSol) || 0, list: list.slice(0, 8),
    pending: list.filter(p => p.status === 'pending').length, held: Object.entries(cat?.realHeld || {}).map(([mint, h]) => ({ mint, ...h })) };
}
const recLine = r => (r && r.trades ? `its paper record: ${r.trades} trades · ${r.wonPct ?? '—'}% won · ${r.pnlSol >= 0 ? '+' : '−'}${Math.abs(r.pnlSol).toFixed(3)} SOL` : 'no closed paper trades yet — no record to lean on');

// 👛 THE WALLET CARD (owner 2026-10-29: "the real money button doesn't open my FeeCat wallet — show balance, vitals, copy so I can load it"):
// the wallet this cat trades through (its linked wallet, else the one connected) — address + ⧉ copy (load it from anywhere), its live SOL
// balance, and the cat's vitals. Option A: FEELESS holds no key — loading the cat = sending SOL to this wallet (your own).
export function useSolBalance(addr, every = 20000) {
  const [sol, setSol] = useState(null);
  useEffect(() => { if (!addr) { setSol(null); return undefined; } let on = true;
    const load = () => fetch(apiUrl(`/api/reputation/balance/${addr}/${SOL}`)).then(r => (r.ok ? r.json() : null)).then(d => { if (on && d && d.amount != null) setSol(Number(d.amount)); }).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, every); return () => { on = false; clearInterval(t); }; }, [addr, every]);
  return sol;
}
function WalletCard({ cat, addr, v }) {
  const w = v.wallet || addr; const sol = useSolBalance(w); const [copied, setCopied] = useState(false);
  const copy = () => { try { navigator.clipboard.writeText(w); setCopied(true); setTimeout(() => setCopied(false), 1400); } catch { /* blocked */ } };
  const trades = (cat?.wins || 0) + (cat?.losses || 0); const pnl = Number(cat?.realizedPnlSol) || 0;
  if (!w) return null;
  return <div className="cr-wallet" data-testid="cr-wallet">
    <div className="cr-wid"><i className={`cr-wdot ${v.real ? 'is-on' : ''}`} aria-hidden="true" /><span><em>{v.real ? 'TRADES THROUGH' : 'YOUR WALLET'}</em><b className="m-num">{short(w)}</b></span>
      <button type="button" className={`m-btn cr-copy ${copied ? 'is-ok' : ''}`} onClick={copy} data-testid="cr-copy" data-tip="Copy the address — send SOL here to load your cat (it is your own wallet; FEELESS never holds a key)">{copied ? '✓ copied' : '⧉ Copy'}</button></div>
    <div className="cr-strip is-vitals">
      <span style={{ '--i': 0 }} data-tip="Live SOL in this wallet (re-read every 20s)"><em>BALANCE</em><b className="m-num" key={sol}>{sol == null ? '…' : `${sol.toFixed(sol >= 10 ? 2 : 4)} SOL`}</b></span>
      <span style={{ '--i': 1 }} data-tip="Its paper record: trades closed and the share won"><em>RECORD</em><b className="m-num">{trades ? `${trades} · ${cat?.winRate ?? '—'}%` : '—'}</b></span>
      <span style={{ '--i': 2 }} className={pnl > 0 ? 'is-up' : pnl < 0 ? 'is-dn' : ''} data-tip="Its realized P&L (fees excluded)"><em>P&L</em><b className="m-num">{`${pnl >= 0 ? '+' : '−'}${Math.abs(pnl).toFixed(3)} SOL`}</b></span>
    </div>
  </div>;
}

// 👛 ITS OWN WALLET (owner 2026-10-29, DECISIONS #2 → agent wallets): one Crossmint smart wallet per cat, made once. Fund it and a TRADING cat
// rides (no signing per trade); a GENERAL cat has a switch — ASK ME (every AI move waits for your OK) or DO ITS THING. Crossmint holds the
// key; FEELESS keeps only the address. Live SOL / USDC from GET /api/cats/{id}/agent-wallet (20s).
export function useAgentWallet(id, has, every = 20000) {
  const [d, setD] = useState(null);
  useEffect(() => { if (!id || !has) { setD(null); return undefined; } let on = true;
    const load = () => fetch(apiUrl(`/api/cats/${id}/agent-wallet`)).then(r => (r.ok ? r.json() : null)).then(x => { if (on && x) setD(x); }).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, every); return () => { on = false; clearInterval(t); }; }, [id, has, every]);
  return d;
}
// pure: today's spend from its own wallet vs its daily cap (agent_trade.day_cap: 4 × its per-buy budget, at most 2 SOL)
export function agentDay(cat, now = Date.now() / 1000) {
  const cap = Math.min(2, 4 * Math.min(0.5, Number(cat?.budgetSol) || 0.05));
  const spent = (cat?.agentTx || []).filter(t => t.side === 'buy' && t.status !== 'failed' && now - (Number(t.at) || 0) < 86400).reduce((a, t) => a + (Number(t.sol) || 0), 0);
  const live = (cat?.agentTx || []).find(t => ['sending', 'pending', 'awaiting-approval'].includes(t.status));
  return { cap: Math.round(cap * 1e4) / 1e4, spent: Math.round(spent * 1e6) / 1e6, live: live || null };
}
// 💵 FUND IT (cat_fund.py): any amount → GET A RECEIPT (the server prices it live and builds ONE transaction: the one-time FEELESS fee out of a
// first funding of $10+, the rest into its wallet) → SIGN & FUND (your wallet signs that exact transaction; the server sends only it, confirms
// it on-chain). A receipt lives 90s — prices move. No auto-quote: you ask for the receipt.
const FUND_AMTS = [1, 5, 10, 25, 50, 100];
// pure: the warning BEFORE a receipt (owner 2026-10-29: "if it isn't enough to start, let them know it only covers the fee")
export function fundWarn(usd, rules, first) {
  const u = Number(usd) || 0; const r = rules || {}; const fee = first ? Number(r.feeUsd) || 0 : 0; const min = first ? Number(r.minUsd) || 10 : Number(r.topupMinUsd) || 1;
  if (u <= 0) return null;
  if (first && fee > 0 && u <= fee) return `$${u} only covers the $${fee} one-time fee — its wallet would get nothing to trade. A first funding starts at $${min}.`;
  if (u < min) return `${first ? 'A first funding' : 'A top-up'} starts at $${min}${first && fee ? ` ($${fee} to FEELESS once, the rest into its wallet)` : ''}.`;
  return null;
}
const sol4 = l => (Number(l) / 1e9).toFixed(4);
const SAVED_KEY = id => `feeless.recoverySaved.${id}`;
export const readSaved = id => { try { return localStorage.getItem(SAVED_KEY(id)) === '1'; } catch { return false; } };
// 🔐 SAFE-KEEPING before the first funding (owner 2026-10-30: "show the WALLET and strongly advise saving the recovery code + a check box").
// The truth, said plainly: its wallet's keys sit with Crossmint and FEELESS's server runs it inside your caps — there is NO separate code for it;
// what gets you back in is YOUR wallet, so the phrase to save is your own wallet's. The first funding stays locked until you tick the box.
export function SafeKeeping({ cat, addr, saved, onSaved }) {
  const w = cat?.agentWallet?.address; const [copied, setCopied] = useState(false);
  const copy = async () => { try { await navigator.clipboard.writeText(w); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* blocked */ } };
  return <div className={`cr-safe${saved ? ' is-saved' : ''}`} data-testid="cr-safe">
    <span className="cr-safe-h"><i aria-hidden="true">🔐</i><b>ITS WALLET</b><small>made for {cat?.name || 'your agent'} · Solana</small></span>
    <span className="cr-safe-addr"><code data-testid="cr-safe-addr">{w || '—'}</code>
      <button type="button" className="m-btn" onClick={copy} disabled={!w} data-tip="Copy its address">{copied ? '✓ copied' : 'Copy'}</button>
      {w ? <a className="m-btn" href={`https://solscan.io/account/${w}`} target="_blank" rel="noopener noreferrer" data-tip="See it on Solscan">Solscan ↗</a> : null}</span>
    <p className="cr-safe-why">It is tied to <b>your wallet {addr ? `${addr.slice(0, 4)}…${addr.slice(-4)}` : ''}</b>: money only ever comes back to it, and only when you sign. There is no separate code for this agent wallet — <b>your wallet's recovery phrase is the only way back in</b>.</p>
    <p className="cr-safe-warn" role="note">⚠ Save your wallet's recovery phrase OFFLINE now (Phantom › Settings › Security › Show recovery phrase — write it on paper). Lose it AND this device and nobody — not FEELESS, not Crossmint — can get your funds back. Never type it into any site or chat.</p>
    <label className="cr-safe-ok"><input type="checkbox" checked={saved} onChange={e => onSaved(e.target.checked)} data-testid="cr-safe-check" />
      <i aria-hidden="true" /><span>I confirm I saved my recovery phrase safely, offline</span></label>
  </div>;
}
export function FundCat({ cat, addr, session, sign, onDone, onConfirm }) {
  const first = !(cat?.agentFunded || []).length;
  const [saved, setSavedState] = useState(() => readSaved(cat?.id));
  const setSaved = v => { setSavedState(v); try { localStorage.setItem(SAVED_KEY(cat?.id), v ? '1' : '0'); } catch { /* private window */ } if (v) onConfirm?.(); };
  const [rules, setRules] = useState(null);
  useEffect(() => { let on = true; fetch(apiUrl(`/api/reputation/cats/fund-rules?address=${encodeURIComponent(addr || '')}`)).then(r => (r.ok ? r.json() : null)).then(j => { if (on && j) setRules(j); }).catch(() => {}); return () => { on = false; }; }, [addr]);
  const [usd, setUsd] = useState(first ? 10 : 5); const [rcpt, setRcpt] = useState(null); const [stage, setStage] = useState('pick'); const [err, setErr] = useState(''); const [sig, setSig] = useState(null);
  const [left, setLeft] = useState(0);
  useEffect(() => { if (!rcpt) return undefined; const t = setInterval(() => setLeft(l => Math.max(0, l - 1)), 1000); return () => clearInterval(t); }, [rcpt]);
  const min = first ? Number(rules?.minUsd) || 10 : Number(rules?.topupMinUsd) || 1; const fee = first ? Number(rules?.feeUsd ?? 2) : 0;
  const warn = fundWarn(usd, rules || { feeUsd: 2, minUsd: 10, topupMinUsd: 1 }, first);
  const post = async (path, body) => { const r = await fetch(apiUrl(`/api/reputation/cats/${cat.id}/${path}`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); return j; };
  const quote = async () => { setErr(''); setStage('quoting');
    try { const s0 = await session(); const j = await post('fund', { address: addr, session: s0, usd: Number(usd) }); setRcpt({ ...j, session: s0 }); setLeft(Math.round(j.expiresIn || 90)); setStage('ready'); }
    catch (e) { setErr(e.message); setStage('pick'); } };
  const go = async () => { if (!rcpt || left <= 0) return; setErr(''); setStage('signing');
    try { const signed = await sign(rcpt.transaction); setStage('sending'); const j = await post('fund/send', { address: addr, session: rcpt.session, signed }); setSig(j.signature); setStage(j.state === 'confirmed' ? 'done' : 'landing'); setRcpt(null); onDone?.(); }
    catch (e) { setErr(e.message || 'Your wallet did not sign.'); setStage('ready'); } };
  const p = rcpt?.plan;
  return <div className="cr-fund" data-testid="cr-fund">
    {first ? <SafeKeeping cat={cat} addr={addr} saved={saved} onSaved={setSaved} /> : null}
    <p className={`cr-fund-rule ${rules?.staff ? 'is-staff' : ''}`} data-testid="cr-fund-rule">{rules?.staff ? `👑 creator wallet — no FEELESS fee, from $${min}` : first
      ? `Starts at $${min}: $${fee} to FEELESS once, $${Math.max(0, min - fee)}+ into its wallet. Top-ups after that: no fee.` : `Top-up from $${min} — no fee, all of it into its wallet.`}</p>
    <div className="cr-fund-pick"><em>{first ? 'FUND IT · FIRST' : 'TOP IT UP'}</em>
      <div className="m-seg" role="radiogroup" aria-label="How much">{FUND_AMTS.filter(a => a >= min).map(a => <button key={a} type="button" role="radio" aria-checked={Number(usd) === a} className={Number(usd) === a ? 'active' : ''} onClick={() => { setUsd(a); setRcpt(null); setStage('pick'); }} data-testid={`cr-fund-${a}`}>${a}</button>)}</div>
      <label className="cr-fund-in">$<input className="m-input" type="number" min={min} step="any" value={usd} onChange={e => { setUsd(e.target.value); setRcpt(null); setStage('pick'); }} aria-label="Dollars to fund it with" data-testid="cr-fund-usd" /></label></div>
    {warn ? <p className="cr-fund-warn" role="status" data-testid="cr-fund-warn">⚠ {warn}</p> : null}
    {p ? <ol className="cr-rcpt" data-testid="cr-receipt">
      <li style={{ '--i': 0 }}><small>YOU PAY</small><b className="m-num">${p.usd.toFixed(2)}</b><i>{sol4(p.totalLamports)} SOL</i></li>
      <li style={{ '--i': 1 }} className={p.feeUsd ? 'is-fee' : 'is-free'} data-tip={p.feeUsd ? 'One time, out of its first funding — never on a top-up' : 'Top-ups carry no FEELESS fee'}><small>FEELESS · ONE-TIME</small><b className="m-num">{p.feeUsd ? `$${p.feeUsd.toFixed(2)}` : '$0'}</b><i>{sol4(p.feeLamports)} SOL</i></li>
      <li style={{ '--i': 2 }} className="is-cat"><small>INTO ITS WALLET</small><b className="m-num">${p.catUsd.toFixed(2)}</b><i>{sol4(p.catLamports)} SOL</i></li>
      <li style={{ '--i': 3 }}><small>PRICE · NETWORK</small><b className="m-num">${p.solUsd}</b><i>/SOL · ~0.000005 SOL fee</i></li>
    </ol> : null}
    <div className="cr-fund-go">
      {stage === 'ready' || stage === 'signing' || stage === 'sending' ? <>
        <button type="button" className="m-btn m-go" disabled={stage !== 'ready' || left <= 0} onClick={go} data-testid="cr-fund-sign" data-tip="Your wallet signs this exact transaction; FEELESS sends only it">{stage === 'signing' ? 'Sign in your wallet…' : stage === 'sending' ? 'Sending…' : '✍ Sign & fund'}</button>
        <span className={`cr-fund-clock ${left < 20 ? 'is-low' : ''}`} data-tip="A receipt lives 90s — prices move"><u><s style={{ transform: `scaleX(${left / 90})` }} /></u><em className="m-num">{left}s</em></span></>
        : <button type="button" className="m-btn m-go" disabled={stage === 'quoting' || !addr || Number(usd) < min || (first && !saved)} onClick={quote} data-testid="cr-fund-quote">{stage === 'quoting' ? 'Pricing…' : '🧾 Get receipt'}</button>}
      {sig ? <a className="cr-fund-sig" href={`https://solscan.io/tx/${sig}`} target="_blank" rel="noreferrer" data-testid="cr-fund-done">{stage === 'done' ? '✓ funded' : '⏳ landing'} · {sig.slice(0, 8)}… ↗</a> : null}
    </div>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
  </div>;
}

// 👛 N16: Fee (the leader) takes a wallet the creator ALREADY has — Crossmint's own wallet = she trades from it; any other = watch-only
function AssignWallet({ cat, busy, send }) {
  const [a, setA] = useState(''); const ok = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(a.trim());
  return <div className="cr-assign" data-testid="cr-assign"><em>{cat?.agentWallet ? 'SWAP IN ANOTHER WALLET' : 'OR ASSIGN ONE YOU ALREADY HAVE'}</em>
    <input className="m-input" value={a} onChange={e => setA(e.target.value)} placeholder="Solana address — a Crossmint wallet of your project trades; any other is watch-only" aria-label="Wallet address for Fee" data-testid="cr-assign-in" />
    <button type="button" className="m-btn" disabled={busy || !ok} onClick={() => send('agent_assign', { text: a.trim() })} data-testid="cr-assign-go"
      data-tip="FEELESS signs only through Crossmint: a wallet Crossmint holds for this project → Fee trades from it. Any other wallet → shown watch-only (FEELESS never holds a private key)">👛 Assign</button></div>;
}

export function AgentWalletCard({ cat, busy, send, addr, session, sign }) {
  const w = cat?.agentWallet; const kind = cat?.brainsCfg?.kind; const d = useAgentWallet(cat?.id, !!w); const [copied, setCopied] = useState(false);
  const bal = d?.balance || {}; const mode = w?.mode || 'approve';
  const copy = () => { try { navigator.clipboard.writeText(w.address); setCopied(true); setTimeout(() => setCopied(false), 1400); } catch { /* blocked */ } };
  return <div className={`cr-agent ${w ? 'is-made' : ''} m-${mode}`} data-testid="cr-agent">
    <svg className="cr-vault" viewBox="0 0 48 48" aria-hidden="true"><rect x="5" y="9" width="38" height="30" rx="6" /><circle cx="24" cy="24" r="8" /><path className="cr-vdial" d="M24 16 V20 M24 28 V32 M16 24 H20 M28 24 H32" /><path d="M11 39 V43 M37 39 V43" /></svg>
    {!w ? <div className="cr-ag-off"><b>👛 ITS OWN WALLET</b><small>Fund it once — {kind === 'trading' ? 'it rides: trades without asking you to sign' : 'it works from it; you choose ask-first or let it go'}. Crossmint holds the key, FEELESS keeps only the address.</small>
      <button type="button" className="m-btn m-go cr-ag-go" disabled={busy || !addr || cat?.revoked} onClick={() => send('agent_wallet')} data-testid="cr-agent-make"
        data-tip={addr ? 'One signature (no transaction) proves you own this cat — then Crossmint makes its wallet' : 'Connect your wallet first'}>👛 Give it its own wallet</button>
      {cat?.isLeader || cat?.id === 'leader' ? <AssignWallet cat={cat} busy={busy} send={send} /> : null}</div>
      : <div className="cr-ag-on">
        {w.provider === 'circle' ? <p className="cr-ag-watch is-circle" role="status" data-testid="cr-agent-circle">🟦 YOUR CIRCLE WALLET — Circle signs each trade she makes, inside her caps (one at a time, per-buy + daily limits).</p> : null}
        {w.provider === 'watch' ? <p className="cr-ag-watch" role="status" data-testid="cr-agent-watch">👁 WATCH-ONLY — Crossmint doesn't hold this wallet's key, so she shows it but never trades from it. Assign a Crossmint wallet of your project to let her trade.</p> : null}
        <div className="cr-wid"><span><em>{w.provider === 'watch' ? '👁 WATCHED WALLET' : kind === 'trading' ? '🏇 RIDES · ITS WALLET' : w.assigned ? '👛 YOUR WALLET · SHE TRADES FROM IT' : 'ITS WALLET'}</em><b className="m-num">{short(w.address)}</b></span>
          <button type="button" className={`m-btn cr-copy ${copied ? 'is-ok' : ''}`} onClick={copy} data-testid="cr-agent-copy" data-tip="Copy its address — send SOL / USDC here to fund it">{copied ? '✓ copied' : '⧉ Copy'}</button></div>
        <div className="cr-strip is-vitals">
          <span style={{ '--i': 0 }} data-tip="Live SOL in its wallet (Crossmint, every 20s)"><em>SOL</em><b className="m-num" key={bal.sol}>{bal.sol == null ? '…' : bal.sol.toFixed(4)}</b></span>
          <span style={{ '--i': 1 }} data-tip="Live USDC in its wallet"><em>USDC</em><b className="m-num" key={bal.usdc}>{bal.usdc == null ? '…' : bal.usdc.toFixed(2)}</b></span>
          <span style={{ '--i': 2 }} className={bal.sol > 0 || bal.usdc > 0 ? 'is-up' : ''} data-tip="Funded = it has money to work with"><em>STATE</em><b className="m-num">{bal.error ? 'NO READ' : bal.sol > 0 || bal.usdc > 0 ? 'FUNDED' : 'EMPTY'}</b></span>
        </div>
        {kind === 'trading' ? null : <div className="m-seg cr-ag-mode" role="radiogroup" aria-label="How it moves">
          {[['approve', '✋ ASK ME', 'Every AI move waits for your OK'], ['auto', '🚀 DO ITS THING', 'AI moves go ahead on their own, inside its limits']].map(([k, l, tip]) =>
            <button key={k} type="button" role="radio" aria-checked={mode === k} className={mode === k ? 'active' : ''} disabled={busy} onClick={() => mode !== k && send('agent_mode', { mode: k })} data-tip={tip} data-testid={`cr-agent-${k}`}>{l}</button>)}</div>}
        {session && sign && w.provider !== 'watch' ? <FundCat cat={cat} addr={addr} session={session} sign={sign} onConfirm={() => send?.('confirm_recovery')} /> : null}
        {cat?.isLeader || cat?.id === 'leader' ? <AssignWallet cat={cat} busy={busy} send={send} /> : null}
        {(() => { const dd = agentDay(cat); return <div className="cr-ag-day" data-testid="cr-agent-day" data-tip={`Its own wallet trades go through the same FEELESS engine: one at a time, a buy ≤ its ${Math.min(0.5, Number(cat?.budgetSol) || 0.05)} SOL budget, ≤ ${dd.cap} SOL a day, 0.01 SOL always kept for gas; it sells only what it bought`}>
          <em>TODAY</em><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, dd.spent / (dd.cap || 1))})` }} /></u><b className="m-num">{dd.spent} / {dd.cap} SOL</b>
          {dd.live ? <i className="cr-ag-live">🏇 {dd.live.side.toUpperCase()} ${dd.live.symbol} settling…</i> : null}</div>; })()}
      </div>}
  </div>;
}

// the drawn flow: the cat reads → proposes → your wallet signs (a beam charges along it)
const Flow = () => <div className="cr-flow" aria-hidden="true"><i className="cr-beam" />
  {[['READS', <><circle cx="12" cy="12" r="4" /><path d="M2 12 C6 5 18 5 22 12 C18 19 6 19 2 12 Z" /></>], ['PROPOSES', <><rect x="4" y="3" width="16" height="18" rx="3" /><path d="M8 9 H16 M8 13 H14 M8 17 H12" /></>],
    ['YOU SIGN', <><circle cx="8" cy="12" r="4.5" /><path d="M12.5 12 H22 M18 12 V16 M21 12 V15" /></>]].map(([l, d], i) =>
    <span key={l} style={{ '--i': i }}><svg viewBox="0 0 24 24">{d}</svg><em>{l}</em></span>)}</div>;

export function CatReal({ cat, busy = false, onAct, devAddress = '' }) {
  const { wallet, connect, signMessage, provider } = useWallet() || {};
  const signTx = async b64 => {   // 💵 the funding transaction FEELESS built → your wallet signs it (never sends it) → base64 back for /fund/send
    if (!provider?.signTransaction) throw new Error('Connect a Solana wallet that can sign.');
    const { VersionedTransaction } = await import('@solana/web3.js');
    const tx = VersionedTransaction.deserialize(Uint8Array.from(atob(b64), c => c.charCodeAt(0)));
    const out = await provider.signTransaction(tx); return btoa(String.fromCharCode(...out.serialize()));
  };
  const addr = devAddress || wallet?.address || '';
  const [budget, setBudget] = useState(0.05); const [err, setErr] = useState(''); const [signing, setSigning] = useState(null);
  const [now, setNow] = useState(() => Date.now() / 1000);
  const v = useMemo(() => realView(cat, now), [cat, now]);
  useEffect(() => { if (!v.pending) return undefined; const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, [v.pending]);
  const send = useRef(null);
  send.current = async (action, extra = {}) => {
    setErr('');
    try { const session = devAddress ? 'dev' : await getChatSession(addr, signMessage, { own: true }); await onAct(action, { address: addr, session, ...extra }); }
    catch (e) { setErr(e.message || 'Your wallet did not sign.'); }
  };
  useEffect(() => {   // the swap you opened from a proposal confirmed on-chain → that proposal is done (its signature on the record)
    const on = e => { const d = e.detail || {}; if (!signing || d.mint !== signing.mint || d.side !== signing.side) return; setSigning(null); send.current('proposal', { proposal: signing.id, result: 'done', sig: d.signature }); };
    window.addEventListener('feeless:trade-confirmed', on); return () => window.removeEventListener('feeless:trade-confirmed', on);
  }, [signing]);
  const sign = p => {
    const title = `🐱 ${String(cat.name || 'YOUR CAT').toUpperCase()} PROPOSES`; const where = 'your cat proposed it';
    if (p.side === 'buy') familiaSwap({ from: SOL, to: p.mint, amount: p.sol, title, where, sub: `BUY $${p.symbol} with ${p.sol} SOL — press Get quote; your wallet signs` });
    else familiaSwap({ from: p.mint, to: SOL, pct: p.fraction, title, where, sub: `SELL ${Math.round(p.fraction * 100)}% of your $${p.symbol} — press Get quote; your wallet signs` });
    setSigning(p);
  };
  const wrong = v.real && addr && v.wallet !== addr;
  return <section className={`kd-card cr ${v.real ? 'is-real' : ''}`} data-testid="cat-real">
    <header><b>💵 REAL MODE</b><small>{cat.agentWallet ? (cat.agentWallet.mode === 'auto' ? 'it trades from its own wallet — no signing per trade' : 'it asks you · its own wallet sends what you approve')
      : 'give it its own wallet below — you sign once to fund it, then it trades on its own'}</small></header>
    <AgentWalletCard cat={cat} busy={busy} addr={addr} send={(a, x) => send.current(a, x)}
      session={() => (devAddress ? Promise.resolve('dev') : getChatSession(addr, signMessage, { own: true }))} sign={signTx} />
    <WalletCard cat={cat} addr={addr} v={v} />
    {!v.real ? <div className="cr-off">
      <Flow />
      <div className="cr-budget"><em>MOST A BUY</em><div className="m-seg" role="group" aria-label="The most it may propose for one buy">
        {BUDGETS.map(b => <button key={b} type="button" aria-pressed={budget === b} className={budget === b ? 'active' : ''} onClick={() => setBudget(b)} data-tip={`It never proposes a buy above ${b} SOL`} data-testid={`cr-b-${b}`}>{b} SOL</button>)}</div></div>
      <p className="cr-rec" data-tip="Every proposal carries this record — no cat has a proven edge on unseen coins yet">{recLine({ trades: (cat.wins || 0) + (cat.losses || 0), wonPct: cat.winRate, pnlSol: Number(cat.realizedPnlSol) || 0 })}</p>
      {addr ? <button type="button" className="m-btn m-go cr-go" disabled={busy || cat.revoked} onClick={() => send.current('real', { budgetSol: budget })} data-testid="cr-go"
        data-tip="One signature (no transaction) proves this wallet is yours — then each trade it proposes waits for your wallet">🔑 Sign in · go real</button>
        : <button type="button" className="m-btn m-go cr-go" onClick={() => connect?.('solana')} data-testid="cr-connect" data-tip="Connect the Solana wallet your cat will propose trades to">Connect wallet</button>}
    </div> : <>
      <div className="cr-strip">
        <span style={{ '--i': 0 }} data-tip="The most it proposes for one buy"><em>A BUY ≤</em><b className="m-num">{v.budget} SOL</b></span>
        <span style={{ '--i': 1 }} className={v.pending ? 'is-hot' : ''} data-tip="Proposals waiting for your wallet"><em>WAITING</em><b className="m-num" key={v.pending}>{v.pending}</b>{v.pending ? <i className="cr-ping" aria-hidden="true" /> : null}</span>
        <span style={{ '--i': 2 }} data-tip={v.held.length ? v.held.map(h => `$${h.symbol}`).join(' · ') : 'Coins you bought through its proposals'}><em>REAL COINS</em><b className="m-num">{v.held.length}</b></span>
        <button type="button" className="m-btn cr-paper" disabled={busy} onClick={() => send.current('paper')} data-testid="cr-paper" data-tip="Back to paper — waiting proposals are cancelled">⏸ Paper</button>
      </div>
      {wrong ? <p className="m-note" role="alert">This cat proposes to {short(v.wallet)} — connect that wallet to sign its trades.</p> : null}
      {v.list.length ? <ul className="cr-list">{v.list.map((p, i) => { const st = STATUS[p.status];
        return <li key={p.id} className={`cr-p is-${p.side} st-${p.status}`} style={{ '--i': i }} data-testid={`cr-p-${p.id}`}>
          <span className="cr-side">{p.side === 'buy' ? 'BUY' : 'SELL'}</span>
          <span className="cr-what"><b>${p.symbol}</b><small title={p.why}>{p.why || 'its rules passed'}</small><small className="cr-r">{recLine(p.record)}</small></span>
          <b className="cr-size m-num">{p.side === 'buy' ? `${p.sol} SOL` : `${Math.round(p.fraction * 100)}%`}</b>
          {p.status === 'pending' && cat.agentWallet ? <span className="cr-acts is-agent">
            {p.agentTx ? <em className="cr-ag-st">🏇 sending from its wallet…</em>
              : cat.agentWallet.mode === 'auto' || p.approved ? <em className="cr-ag-st" title={p.agentWhy || ''}>{p.agentWhy ? `⏸ ${p.agentWhy}` : '🏇 its wallet sends it next pass'}</em>
              : <><button type="button" className="m-btn m-go" disabled={busy} onClick={() => send.current('agent_approve', { proposal: p.id })} data-testid={`cr-approve-${p.id}`} data-tip="Your OK — its own wallet sends it (no transaction for you to sign)">✅ Approve</button>
                <button type="button" className="m-btn" disabled={busy} onClick={() => send.current('proposal', { proposal: p.id, result: 'skip' })} data-testid={`cr-skip-${p.id}`} data-tip="Let this one pass">Skip</button></>}</span>
            : p.status === 'pending' ? <span className="cr-acts">
            <span className="cr-clock" data-tip="It expires when this runs out — prices move"><u><s key={p.id} style={{ '--f': Math.min(1, p.left / LIFE), animationDuration: `${p.left}s` }} /></u><em className="m-num">{clock(p.left)}</em></span>
            <button type="button" className="m-btn m-go" disabled={busy || wrong} onClick={() => sign(p)} data-testid={`cr-sign-${p.id}`} data-tip="Opens the swap with the coins and amount set — press Get quote, your wallet signs">✍ Sign it</button>
            <button type="button" className="m-btn" disabled={busy} onClick={() => send.current('proposal', { proposal: p.id, result: 'skip' })} data-testid={`cr-skip-${p.id}`} data-tip="Let this one pass">Skip</button></span>
            : <span className={`cr-st is-${st?.[1] || 'off'}`}>{p.status === 'done' && p.sig ? <a href={`https://solscan.io/tx/${p.sig}`} target="_blank" rel="noreferrer" data-tip="Its transaction on Solscan">{st[0]} ↗</a> : st?.[0] || p.status}</span>}
        </li>; })}</ul>
        : <p className="kd-empty">No proposals yet — it hunts the live board; the moment it would buy, it asks your wallet here and in your inbox.</p>}
    </>}
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    <FamiliaTradeDock />
  </section>;
}
