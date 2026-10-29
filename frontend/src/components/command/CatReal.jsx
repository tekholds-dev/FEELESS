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
export function AgentWalletCard({ cat, busy, send, addr }) {
  const w = cat?.agentWallet; const kind = cat?.brainsCfg?.kind; const d = useAgentWallet(cat?.id, !!w); const [copied, setCopied] = useState(false);
  const bal = d?.balance || {}; const mode = w?.mode || 'approve';
  const copy = () => { try { navigator.clipboard.writeText(w.address); setCopied(true); setTimeout(() => setCopied(false), 1400); } catch { /* blocked */ } };
  return <div className={`cr-agent ${w ? 'is-made' : ''} m-${mode}`} data-testid="cr-agent">
    <svg className="cr-vault" viewBox="0 0 48 48" aria-hidden="true"><rect x="5" y="9" width="38" height="30" rx="6" /><circle cx="24" cy="24" r="8" /><path className="cr-vdial" d="M24 16 V20 M24 28 V32 M16 24 H20 M28 24 H32" /><path d="M11 39 V43 M37 39 V43" /></svg>
    {!w ? <div className="cr-ag-off"><b>👛 ITS OWN WALLET</b><small>Fund it once — {kind === 'trading' ? 'it rides: trades without asking you to sign' : 'it works from it; you choose ask-first or let it go'}. Crossmint holds the key, FEELESS keeps only the address.</small>
      <button type="button" className="m-btn m-go cr-ag-go" disabled={busy || !addr || cat?.revoked} onClick={() => send('agent_wallet')} data-testid="cr-agent-make"
        data-tip={addr ? 'One signature (no transaction) proves you own this cat — then Crossmint makes its wallet' : 'Connect your wallet first'}>👛 Give it its own wallet</button></div>
      : <div className="cr-ag-on">
        <div className="cr-wid"><span><em>{kind === 'trading' ? '🏇 RIDES · ITS WALLET' : 'ITS WALLET'}</em><b className="m-num">{short(w.address)}</b></span>
          <button type="button" className={`m-btn cr-copy ${copied ? 'is-ok' : ''}`} onClick={copy} data-testid="cr-agent-copy" data-tip="Copy its address — send SOL / USDC here to fund it">{copied ? '✓ copied' : '⧉ Copy'}</button></div>
        <div className="cr-strip is-vitals">
          <span style={{ '--i': 0 }} data-tip="Live SOL in its wallet (Crossmint, every 20s)"><em>SOL</em><b className="m-num" key={bal.sol}>{bal.sol == null ? '…' : bal.sol.toFixed(4)}</b></span>
          <span style={{ '--i': 1 }} data-tip="Live USDC in its wallet"><em>USDC</em><b className="m-num" key={bal.usdc}>{bal.usdc == null ? '…' : bal.usdc.toFixed(2)}</b></span>
          <span style={{ '--i': 2 }} className={bal.sol > 0 || bal.usdc > 0 ? 'is-up' : ''} data-tip="Funded = it has money to work with"><em>STATE</em><b className="m-num">{bal.error ? 'NO READ' : bal.sol > 0 || bal.usdc > 0 ? 'FUNDED' : 'EMPTY'}</b></span>
        </div>
        {kind === 'trading' ? null : <div className="m-seg cr-ag-mode" role="radiogroup" aria-label="How it moves">
          {[['approve', '✋ ASK ME', 'Every AI move waits for your OK'], ['auto', '🚀 DO ITS THING', 'AI moves go ahead on their own, inside its limits']].map(([k, l, tip]) =>
            <button key={k} type="button" role="radio" aria-checked={mode === k} className={mode === k ? 'active' : ''} disabled={busy} onClick={() => mode !== k && send('agent_mode', { mode: k })} data-tip={tip} data-testid={`cr-agent-${k}`}>{l}</button>)}</div>}
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
  const { wallet, connect, signMessage } = useWallet() || {};
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
      : v.real ? `${short(v.wallet)} signs every trade` : 'it proposes · your wallet signs · FEELESS never holds your SOL'}</small></header>
    <AgentWalletCard cat={cat} busy={busy} addr={addr} send={(a, x) => send.current(a, x)} />
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
