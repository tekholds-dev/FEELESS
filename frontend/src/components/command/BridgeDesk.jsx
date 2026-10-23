import React, { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { ArrowLeftRight } from 'lucide-react';
import NumInput from '../NumInput';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl } from '../../lib/api';
import { useGlide } from '../../lib/useGlide';
import { toUnits, executeLifi } from '../../lib/lifiExec';
import { BRIDGE_CHAINS, CHAIN, isSol, chainIdOf, decimalsOf, tokenOf, routeVitals, fmtSecs, bridgeQuote, executeSolRoute, trackBridge } from '../../lib/bridgeExec';
import { moneyConfirmed } from '../../lib/moneyConfirm';
import '../../styles/bridge.css';

// 🌉 THE BRIDGE (Trade › Bridge, owner 2026-10-23: "must really bridge tokens … a better bridge design"). SOL / USDC out of Solana to any EVM
// chain LI.FI routes, and back. Drawn: two chain orbs joined by a suspension span, cargo running across it (faster while it's in flight), the
// route's provider on the deck. Live vitals: YOU SEND · YOU GET (the hot number) · COST (fee + gas, % bar) · TIME (ring). The open quote
// refreshes every 10 s (never before you ask). Steps animate QUOTE → CHECK → SIGN → SENT → BRIDGING → LANDED. Your wallet signs; it pays out
// to YOUR wallet on the other side (the address your own wallet hands over); FEELESS never holds anything.
const short = a => (a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '—');
const usd = v => (v == null || Number.isNaN(v) ? '—' : `$${v >= 100 ? Math.round(v).toLocaleString('en-US') : v.toFixed(2)}`);
const amt = v => (v == null ? '—' : v >= 1000 ? Math.round(v).toLocaleString('en-US') : v >= 1 ? v.toFixed(3) : v.toPrecision(3));
const cleanAmount = v => { const [w, ...f] = String(v).replace(/[^0-9.]/g, '').split('.'); return f.length ? `${w}.${f.join('')}` : w; };
const ecoOf = k => (isSol(k) ? 'solana' : 'evm');
export const STEPS = [['quote', 'Quote'], ['check', 'Check'], ['sign', 'Sign'], ['source', 'Sent'], ['bridge', 'Bridging'], ['landed', 'Landed']];
const PHASE_STEP = { quote: 0, switch: 1, approve: 1, sim: 1, sign: 2, source: 3, bridge: 4, landed: 5 };
export const stepOf = phase => PHASE_STEP[phase] ?? 0;

export function ChainOrb({ k, size = 34, ring = false }) {
  const c = CHAIN[k] || { tick: '?', c1: '#45e486', c2: '#0b6b35' };
  return <svg className={`br-orb ${ring ? 'br-orb-big' : ''}`} width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
    <defs><radialGradient id={`br-g-${k}`} cx="35%" cy="30%" r="75%"><stop offset="0" stopColor={c.c2} /><stop offset="1" stopColor={c.c1} /></radialGradient></defs>
    <circle cx="20" cy="20" r="17" fill={`url(#br-g-${k})`} /><circle cx="20" cy="20" r="17" className="br-orb-rim" />
    <ellipse cx="15" cy="12" rx="7" ry="3.5" className="br-orb-shine" />
    <text x="20" y="24" textAnchor="middle" className="br-orb-t" style={{ fontSize: c.tick.length > 3 ? 8.5 : 10.5 }}>{c.tick}</text></svg>;
}

export function ChainRail({ label, value, other, onPick }) {
  return <div className="br-rail" role="radiogroup" aria-label={label}>
    <small className="m-label">{label}</small>
    <div className="m-seg br-chips">{BRIDGE_CHAINS.map(k => <button key={k} type="button" role="radio" aria-checked={value === k} className={value === k ? 'active' : ''}
      data-tip={k === other ? `${CHAIN[k].name} is the other side — tap to flip` : `${label} ${CHAIN[k].name}`} onClick={() => onPick(k)} data-testid={`br-${label.toLowerCase()}-${k}`}>
      <ChainOrb k={k} size={18} />{CHAIN[k].name}</button>)}</div></div>;
}

// the drawn route: two orbs + a suspension span, cargo crossing it (transform only)
export function RouteScene({ from, to, v, step, asset }) {
  const live = step >= 3 && step < 5; const landed = step >= 5;
  return <div className={`br-scene ${live ? 'is-live' : ''} ${landed ? 'is-landed' : ''}`} data-testid="br-scene">
    <svg viewBox="0 0 320 112" preserveAspectRatio="none" className="br-span" aria-hidden="true">
      <path d="M46,74 Q160,4 274,74" className="br-arch" />
      {[78, 104, 130, 160, 190, 216, 242].map((x, i) => { const t = (x - 46) / 228; const y = (1 - t) * (1 - t) * 74 + 2 * (1 - t) * t * 4 + t * t * 74; return <line key={x} x1={x} y1={y} x2={x} y2="80" className="br-cable" style={{ '--i': i }} />; })}
      <rect x="40" y="80" width="240" height="5" rx="2.5" className="br-deck" />
      <path d="M0,104 C60,96 110,108 160,101 C210,94 260,108 320,99" className="br-water" />
    </svg>
    <span className="br-sweep" aria-hidden="true" />
    <span className="br-cargo" aria-hidden="true">{[0, 1, 2, 3].map(i => <i key={i} style={{ '--i': i }} />)}</span>
    <div className="br-end from"><ChainOrb k={from} size={46} ring /><b>{CHAIN[from]?.name}</b><small>{asset === 'usdc' ? 'USDC' : CHAIN[from]?.native}</small></div>
    <div className="br-end to"><ChainOrb k={to} size={46} ring /><b>{CHAIN[to]?.name}</b><small>{asset === 'usdc' ? 'USDC' : CHAIN[to]?.native}</small></div>
    <span className="br-tool" data-tip="The bridge LI.FI picked for this route — FEELESS opened its transaction before your wallet sees it">
      {v?.logo ? <img src={v.logo} alt="" width="14" height="14" /> : null}{v?.tool ? `via ${v.tool}` : 'pick a route'}</span>
  </div>;
}

function Flash({ value, children, className = '' }) {   // the number flashes when the quote moves it
  const [k, setK] = useState(0); const prev = useRef(value);
  useEffect(() => { if (prev.current !== value) { prev.current = value; setK(x => x + 1); } }, [value]);
  return <b key={k} className={`${className} ${k ? 'br-flash' : ''}`}>{children}</b>;
}

export function Vitals({ v, refreshIn }) {
  const sendUsd = useGlide(v ? +v.sendUsd.toFixed(1) : null); const getUsd = useGlide(v ? +v.getUsd.toFixed(1) : null);
  const costW = v ? Math.min(1, v.costPct / 5) : 0; const ring = v ? Math.min(1, v.secs / 600) : 0;
  return <div className="br-vitals" data-testid="br-vitals">
    <div className="br-vt" style={{ '--i': 0 }} data-tip="What leaves your wallet"><small className="m-label">You send</small><Flash value={v?.send}>{v ? `${amt(v.send)} ${v.sendSym}` : '—'}</Flash><em>{usd(sendUsd)}</em></div>
    <div className="br-vt hot" style={{ '--i': 1 }} data-tip="What lands in your wallet on the other side (LI.FI's estimate; the minimum is protected by 1% slippage)"><small className="m-label">You get</small><Flash value={v?.get} className="br-hot">{v ? `${amt(v.get)} ${v.getSym}` : '—'}</Flash><em>{usd(getUsd)}</em></div>
    <div className="br-vt" style={{ '--i': 2 }} data-tip={v ? `Bridge + FEELESS fees ${usd(v.feeUsd)} · network gas ${usd(v.gasUsd)} · everything between send and get ${usd(v.costUsd)}` : 'Fees appear with the quote'}>
      <small className="m-label">Cost</small><b>{v ? usd(v.costUsd) : '—'}</b><span className="br-bar"><i style={{ transform: `scaleX(${costW})` }} className={v && v.costPct > 3 ? 'warn' : ''} /></span><em>{v ? `${v.costPct.toFixed(2)}%` : ''}</em></div>
    <div className="br-vt" style={{ '--i': 3 }} data-tip="How long the bridge usually takes to land"><small className="m-label">Time</small>
      <span className="br-ring"><svg viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="15" className="trk" /><circle cx="18" cy="18" r="15" className="arc" pathLength="100" style={{ strokeDasharray: `${ring * 100} 100` }} /></svg><b>{v ? fmtSecs(v.secs) : '—'}</b></span>
      <em>{refreshIn != null ? `refresh ${refreshIn}s` : ''}</em></div>
  </div>;
}

export function StepRail({ step, failed }) {
  return <ol className="br-steps" data-testid="br-steps">{STEPS.map(([k, l], i) => <li key={k} className={i < step || (i === step && i === 5) ? 'done' : i === step ? (failed ? 'fail' : 'now') : ''} style={{ '--i': i }}><i /><span>{l}</span></li>)}</ol>;
}

// One route, shared by the Bridge and the gas station: quote → (auto-refresh 10 s) → execute on the right side → track until it lands.
export function useBridgeRoute() {
  const w = useWallet() || {};
  const [quote, setQuote] = useState(null); const [busy, setBusy] = useState(false); const [phase, setPhase] = useState('quote');
  const [msg, setMsg] = useState(''); const [failed, setFailed] = useState(false); const [landed, setLanded] = useState(null); const [refreshIn, setRefreshIn] = useState(null);
  const ask = useRef(null);
  const fetchQuote = useCallback(async (p, quiet) => {
    if (!quiet) { setBusy(true); setFailed(false); setLanded(null); setPhase('quote'); setMsg('Finding the best route…'); }
    try { const q = await bridgeQuote(p); setQuote(q); ask.current = p; setRefreshIn(10); if (!quiet) setMsg(''); }
    catch (e) { if (!quiet) { setQuote(null); setMsg(e.message); setFailed(true); toast.error(e.message); } }
    finally { if (!quiet) setBusy(false); }
  }, []);
  useEffect(() => {   // an OPEN quote refreshes every 10 s (CLAUDE.md: never auto-quote before you ask)
    if (!quote || busy || landed) return undefined;
    const t = setInterval(() => setRefreshIn(n => { if (n <= 1) { if (ask.current) fetchQuote(ask.current, true); return 10; } return n - 1; }), 1000);
    return () => clearInterval(t);
  }, [quote, busy, landed, fetchQuote]);
  const step = (text, ph) => { setMsg(text); if (ph) setPhase(ph); };
  const execute = async () => {
    const p = ask.current; if (!quote || !p) return;
    setBusy(true); setFailed(false);
    try {
      let out;
      if (isSol(p.from)) {
        const s = await w.switchTo('solana');
        const sent = await executeSolRoute({ quote, provider: s.provider, address: s.wallet.address, payTo: p.toAddress, onStep: step });
        out = { hash: sent.hash, landed: await trackBridge({ hash: sent.hash, fromChainId: chainIdOf(p.from), toChainId: chainIdOf(p.to), onStep: step }) };
      } else {
        const s = await w.switchTo(p.from);
        out = await executeLifi({ quote, wallet: s.wallet, provider: s.provider, switchTo: w.switchTo, payTo: p.toAddress, onStep: step });
      }
      const st = out.landed?.status || out.status;
      if (st === 'FAILED') throw new Error(out.landed?.message || 'LI.FI reported the bridge failed — check the explorer link.');
      if (st === 'DONE') { setPhase('landed'); setLanded({ ...out.landed, hash: out.hash }); setMsg('');
        moneyConfirmed({ title: 'Bridge landed', chain: p.to, hash: out.landed?.receiving || out.hash, wallet: p.toAddress, detail: out.landed?.got ? `${amt(out.landed.got)} ${out.landed.symbol || ''} arrived on ${CHAIN[p.to]?.name}.` : undefined }); }
      else { setPhase('bridge'); setMsg('Still in flight — it lands on its own; nothing was resent.'); setLanded(null); }
      setQuote(null);
    } catch (e) { setFailed(true); setMsg(e.code === 4001 ? 'Declined in your wallet — nothing was sent.' : e.message); toast.error(e.code === 4001 ? 'Declined in wallet — nothing sent.' : e.message); }
    finally { setBusy(false); }
  };
  const clear = () => { setQuote(null); ask.current = null; setRefreshIn(null); setPhase('quote'); setMsg(''); setFailed(false); setLanded(null); };
  return { ...w, quote, busy, phase, msg, failed, landed, refreshIn, vitals: routeVitals(quote), fetchQuote, execute, clear };
}

// the destination is always YOUR wallet on the other side: whatever address your own wallet hands over
export function useSides(r, from, to) {
  const [addr, setAddr] = useState({});
  useEffect(() => {
    let alive = true;
    if (!r.peekAddress) return undefined;
    Promise.all(['solana', 'evm'].map(t => r.peekAddress(t, { silent: true }).catch(() => null))).then(([solana, evm]) => alive && setAddr({ solana, evm }));
    return () => { alive = false; };
  }, [r.wallet?.address]); // eslint-disable-line react-hooks/exhaustive-deps
  const need = async k => { const t = ecoOf(k); if (addr[t]) return addr[t]; const a = await r.peekAddress(t); setAddr(x => ({ ...x, [t]: a })); return a; };
  return { from: addr[ecoOf(from)], to: addr[ecoOf(to)], need };
}

export function Landed({ landed, to }) {
  if (!landed) return null;
  const link = landed.receivingLink || landed.explorer;
  return <div className="br-landed" data-testid="br-landed"><b>✓ Landed on {CHAIN[to]?.name}</b><span>{landed.got != null ? `${amt(landed.got)} ${landed.symbol || ''} in your wallet` : 'Funds arrived in your wallet'}</span>
    {link ? <a className="m-btn" href={link} target="_blank" rel="noopener noreferrer" data-tip="Open the destination transaction">View tx ↗</a> : null}</div>;
}

const PRESETS = [5, 25, 100];
export function BridgeDesk() {
  const r = useBridgeRoute();
  const [from, setFrom] = useState('solana'); const [to, setTo] = useState('base');
  const [asset, setAsset] = useState('usdc'); const [amount, setAmount] = useState('10'); const [px, setPx] = useState(null);
  const sides = useSides(r, from, to);
  useEffect(() => {   // the price of what you send, for $ presets + the $ under the amount
    if (asset === 'usdc') { setPx(1); return undefined; }
    let alive = true; setPx(null);
    fetch(apiUrl(`/api/lifi/token?chain=${chainIdOf(from)}&token=${tokenOf(from, 'native')}`)).then(x => x.json()).then(d => alive && setPx(Number(d.priceUSD) || null)).catch(() => {});
    return () => { alive = false; };
  }, [from, asset]);
  const pick = side => k => { r.clear(); if (side === 'from') { if (k === to) setTo(from); setFrom(k); } else { if (k === from) setFrom(to); setTo(k); } };
  const flip = () => { r.clear(); setFrom(to); setTo(from); };
  const go = async () => {
    try {
      const fa = await sides.need(from); const ta = await sides.need(to);
      if (!fa) throw new Error(`Connect a wallet on ${CHAIN[from].name} first.`);
      if (!ta) throw new Error(`Your wallet has no ${isSol(to) ? 'Solana' : 'EVM'} side to receive on — connect one.`);
      r.fetchQuote({ from, to, asset, amountUnits: toUnits(amount, decimalsOf(from, asset)), fromAddress: fa, toAddress: ta });
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in your wallet.' : e.message); }
  };
  const step = stepOf(r.phase); const v = r.vitals; const usdNow = px && Number(amount) ? Number(amount) * px : null;
  return <div className="td-panel br m-live" data-testid="bridge-desk">
    <header className="br-head"><b>🌉 Bridge</b><small>SOL · USDC · ETH between Solana and {BRIDGE_CHAINS.length - 1} EVM chains — your wallet signs, it pays out to your own wallet</small></header>
    <ChainRail label="From" value={from} other={to} onPick={pick('from')} />
    <div className="br-mid">
      <button type="button" className="br-flip" aria-label="Flip chains" data-tip="Flip: send the other way" onClick={flip}><ArrowLeftRight size={15} /></button>
      <div className="m-seg br-asset" role="radiogroup" aria-label="Asset">{[['usdc', 'USDC'], ['native', 'Native gas coin']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={asset === k}
        className={asset === k ? 'active' : ''} onClick={() => { setAsset(k); r.clear(); }} data-tip={k === 'usdc' ? 'USDC on both sides' : `${CHAIN[from].native} → ${CHAIN[to].native}`}>{l}</button>)}</div>
    </div>
    <ChainRail label="To" value={to} other={from} onPick={pick('to')} />
    <RouteScene from={from} to={to} v={v} step={r.quote || r.busy || r.landed ? step : -1} asset={asset} />
    <div className="br-amt">
      <label className="td-field"><small>Amount · {asset === 'usdc' ? 'USDC' : CHAIN[from].native}</small><NumInput inputMode="decimal" value={amount} onChange={e => { setAmount(cleanAmount(e.target.value)); r.clear(); }} /></label>
      <div className="m-seg br-pre" role="radiogroup" aria-label="Quick amounts">{PRESETS.map(d => <button key={d} type="button" disabled={!px} data-tip={px ? `Send $${d}` : 'Reading the price…'}
        onClick={() => { setAmount(asset === 'usdc' ? String(d) : (d / px).toPrecision(4)); r.clear(); }}>${d}</button>)}</div>
      <em className="br-usd">{usd(usdNow)}</em>
    </div>
    <p className="br-dest" data-tip="The bridge pays out to the address your own wallet handed over — never anyone else's">
      <span>from <b>{short(sides.from)}</b></span><i aria-hidden="true">→</i><span>to your {CHAIN[to].name} wallet <b>{short(sides.to)}</b></span></p>
    <Vitals v={v} refreshIn={r.quote && !r.busy ? r.refreshIn : null} />
    <StepRail step={r.quote || r.busy || r.landed || r.failed ? step : -1} failed={r.failed} />
    {r.msg ? <p className={`br-msg ${r.failed ? 'bad' : ''}`} role="status">{r.msg}</p> : null}
    <Landed landed={r.landed} to={to} />
    <div className="br-go">
      {r.quote ? <><button type="button" className="m-btn" onClick={r.clear} disabled={r.busy}>Cancel</button>
        <button type="button" className="btn-primary td-go m-go" disabled={r.busy} onClick={r.execute} data-testid="br-sign">{r.busy ? (r.msg || 'Confirm in wallet…') : `Sign + bridge ${v ? usd(v.sendUsd) : ''}`}</button></>
        : <button type="button" className="btn-primary td-go m-go" disabled={r.busy || from === to || !Number(amount)} onClick={go} data-testid="br-quote">{r.busy ? 'Finding the best route…' : 'Get bridge quote'}</button>}
    </div>
  </div>;
}
