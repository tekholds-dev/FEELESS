import React, { useEffect, useState } from 'react';
import NumInput from '../NumInput';
import { toast } from 'sonner';
import { ArrowLeftRight, Fuel, Repeat, ShieldCheck } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { EdgeScore } from '../terminal/EdgeScore';
import { useMarket } from '../../hooks/useMarket';
import { toUnits } from '../../lib/lifiExec';
import { CHAIN, isSol } from '../../lib/bridgeExec';
import { BridgeDesk, ChainOrb, Landed, RouteScene, StepRail, Vitals, stepOf, useBridgeRoute, useSides } from './BridgeDesk';
import { FollowingCalls } from './FollowingCalls';
import { TopPumpCoins } from './TopPumpCoins';
import '../../styles/gasStation.css';

const DustCleanup = React.lazy(() => import('../DustCleanup'));
// The trade desk: Swap (the existing Jupiter/LI.FI flows), Bridge (Solana <-> every EVM chain LI.FI routes, BridgeDesk)
// and Get Gas (turn SOL, or spare gas on one chain, into gas on another). Non-custodial throughout:
// every route is a quote the user reviews, and every transaction is signed in their own wallet.
const NAMES = { ethereum: 'Ethereum', base: 'Base', bsc: 'BNB Chain', arbitrum: 'Arbitrum', avalanche: 'Avalanche', polygon: 'Polygon', optimism: 'Optimism', zksync: 'zkSync', cronos: 'Cronos', unichain: 'Unichain', worldchain: 'World Chain' };
const cleanAmount = v => { const [w, ...f] = v.replace(/[^0-9.]/g, '').split('.'); return f.length ? `${w}.${f.join('')}` : w; };

// ⛽ THE FUEL STATION (Trade › Get gas, 2026-10-22 meta redo of the SmolRefuel-style list): every chain is a drawn GAUGE — the needle sits at your
// gas in $ against that chain's own minimum (red zone = below it, a full tank = 4× it) — the count of chains running dry on top, preset amounts,
// and the route drawn from the chain you pay from to the one you fill (LI.FI quote, itemised, your wallet signs). 2026-10-23: pay with SOL (Solana-
// first), every tank read even when the keyed RPC is spent, Zora off (LI.FI dropped it); the quote's vitals + step rail are the bridge desk's.
export const gasFill = c => (c?.usd == null ? 0 : Math.max(0, Math.min(1, c.usd / ((c.minUsd || 0.25) * 4))));
export function Gauge({ c, on, onPick }) {
  const f = gasFill(c); const a = -95 + f * 190;   // the arc's ends sit level with the pivot: empty points left, full points right
  return <button type="button" className={`gs-gauge ${c.enough ? 'ok' : 'low'} ${on ? 'on' : ''}`} onClick={onPick} aria-pressed={on}
    data-tip={c.balance == null ? `${NAMES[c.chain] || c.chain}: balance unavailable` : `${NAMES[c.chain] || c.chain}: ${c.balance.toFixed(5)} ${c.symbol}${c.usd != null ? ` ≈ $${c.usd}` : ''} · needs ≥ $${c.minUsd}`} data-testid={`gas-${c.chain}`}>
    <svg viewBox="0 0 100 64" aria-hidden="true"><path d="M12,56 A40,40 0 1 1 88,56" className="trk" /><path d="M12,56 A40,40 0 0 1 22.6,28.5" className="red" />
      <path d="M12,56 A40,40 0 1 1 88,56" className="fill" pathLength="100" style={{ strokeDasharray: `${f * 100} 100` }} />
      <g className="ndl" style={{ transform: `rotate(${a}deg)` }}><path d="M50,56 L50,22" /><circle cx="50" cy="56" r="4" /></g></svg>
    <b>{NAMES[c.chain] || c.chain}</b><small>{c.balance == null ? 'unavailable' : c.usd != null ? `$${c.usd.toFixed(2)}` : `${c.balance.toFixed(4)} ${c.symbol}`}</small>
    <em>{c.enough ? '✓ fuelled' : '⛽ running dry'}</em></button>;
}
export function GetGas() {
  const r = useBridgeRoute();
  const sides = useSides(r, 'solana', 'base'); const sol = sides.from; const evm = sides.to;
  const [gas, setGas] = useState(null); const [target, setTarget] = useState(null); const [usd, setUsd] = useState('2'); const [payWith, setPayWith] = useState(null);
  useEffect(() => {
    if (!evm) { setGas(null); return undefined; }
    let alive = true;
    fetch(apiUrl(`/api/reputation/gas/${evm}${sol ? `?sol=${sol}` : ''}`)).then(x => x.json()).then(d => alive && setGas(d)).catch(() => {});
    return () => { alive = false; };
  }, [evm, sol, r.landed]);
  if (!evm) return <div className="td-panel td-empty gs-empty"><span className="gs-pump" aria-hidden="true"><i /><u /></span><p>FEELESS reads your gas on every chain at once and fills any tank from SOL — or from spare gas on another chain. Your wallet signs; the gas lands in your own wallet.</p>
    <button type="button" className="btn-primary m-go" data-tip="Your wallet hands over its EVM address (the tanks); nothing is signed" onClick={() => sides.need('base').catch(e => toast.error(e.message))} data-testid="gas-connect">⛽ Read my tanks</button></div>;
  if (!gas) return <div className="td-panel gs-load"><span className="gs-pump" aria-hidden="true"><i /><u /></span><p className="wp-bio">Reading your tanks…</p></div>;
  const want = Number(usd) || 0; const spare = c => c && c.usd != null && c.balance > 0 && c.usd > want * 1.5;
  const sources = [gas.solana, ...gas.chains.filter(c => c.enough)].filter(c => spare(c) && c.chain !== target);
  const source = sources.find(c => c.chain === payWith) || sources[0];
  const dry = gas.chains.filter(c => !c.enough).length;
  const quote = () => { const units = toUnits((want / (source.usd / source.balance)).toFixed(isSol(source.chain) ? 9 : 12), isSol(source.chain) ? 9 : 18);
    r.fetchQuote({ from: source.chain, to: target, asset: 'native', amountUnits: units, fromAddress: isSol(source.chain) ? sol : evm, toAddress: evm }); };
  const step = stepOf(r.phase);
  return <div className="td-panel gs">
    <header className="gs-head"><b className={dry ? 'is-low' : 'is-ok'}>{dry ? `${dry} of ${gas.chains.length} chains running dry` : `All ${gas.chains.length} chains fuelled`}</b><small>tap a tank to fill it{gas.solana ? ` · ◎ ${gas.solana.balance.toFixed(3)} SOL ready to pay` : ''}</small></header>
    <div className="gs-grid">{gas.chains.map((c, i) => <span key={c.chain} style={{ '--i': i }}><Gauge c={c} on={target === c.chain} onPick={() => { setTarget(c.chain); r.clear(); }} /></span>)}</div>
    {target && <div className="gs-fill">
      <div className="m-seg gs-pre" role="radiogroup" aria-label="Gas to add">{['1', '2', '5', '10'].map(v => <button key={v} type="button" role="radio" aria-checked={usd === v} className={usd === v ? 'active' : ''} onClick={() => { setUsd(v); r.clear(); }}>${v}</button>)}</div>
      <label className="td-field"><small>or USD</small><NumInput inputMode="decimal" value={usd} onChange={e => { setUsd(cleanAmount(e.target.value)); r.clear(); }} /></label>
      {sources.length ? <div className="m-seg gs-pay" role="radiogroup" aria-label="Pay with">{sources.slice(0, 4).map(c => <button key={c.chain} type="button" role="radio" aria-checked={source === c} className={source === c ? 'active' : ''}
        data-tip={`Pay with ${c.symbol} on ${CHAIN[c.chain]?.name || c.chain} · $${c.usd} there`} onClick={() => { setPayWith(c.chain); r.clear(); }}><ChainOrb k={c.chain} size={16} />{c.symbol} ${c.usd}</button>)}</div>
        : <p className="wp-bio">No chain with enough spare to pay from — add SOL (or gas on any chain) first.</p>}
    </div>}
    {target && source ? <RouteScene from={source.chain} to={target} v={r.vitals} step={r.quote || r.busy || r.landed ? step : -1} asset="native" /> : null}
    {target && source ? <><Vitals v={r.vitals} refreshIn={r.quote && !r.busy ? r.refreshIn : null} /><StepRail step={r.quote || r.busy || r.landed || r.failed ? step : -1} failed={r.failed} /></> : null}
    {r.msg ? <p className={`br-msg ${r.failed ? 'bad' : ''}`} role="status">{r.msg}</p> : null}
    <Landed landed={r.landed} to={target} />
    {target && source ? <div className="br-go">{r.quote ? <><button type="button" className="m-btn" onClick={r.clear} disabled={r.busy}>Cancel</button>
      <button type="button" className="btn-primary td-go m-go" disabled={r.busy} onClick={r.execute} data-testid="gas-sign">{r.busy ? (r.msg || 'Confirm in wallet…') : `⛽ Sign + fill $${usd}`}</button></>
      : <button type="button" className="btn-primary td-go m-go" disabled={r.busy || !want} onClick={quote} data-testid="gas-quote">{r.busy ? 'Finding the best route…' : `⛽ Quote $${usd} of gas`}</button>}</div> : null}
  </div>;
}

// Fee chips are BUTTONS (owner: "all btns route and work"): 0% → loads $FEE into the swap · the % chip → why that fee (tier discounts) ·
// bridge & gas → opens the Bridge tab.
const FEE_MINT = '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump';
function FeeExplainer({ onMode }) {
  const [f, setF] = useState(null); const [why, setWhy] = useState(false);
  useEffect(() => { fetch(apiUrl('/api/reputation/fees/public')).then(x => x.json()).then(setF).catch(() => {}); }, []);
  const pct = f ? (f.platformFeeBps / 100).toFixed(2) : null;
  const best = f ? Math.max(...Object.values(f.tierDiscountPct || { 0: 0 })) : 0;
  return <div className="td-fees" data-testid="td-fees">
    <button type="button" className="td-fee good" data-tip="Buying $FEE, FEECAT or rFEE with SOL, USDC or USDT is free. Selling them pays the platform fee. Tap: load $FEE into the swap."
      onClick={() => { onMode?.('swap'); window.dispatchEvent(new CustomEvent('feeless:swap-set-output', { detail: { mint: FEE_MINT, symbol: 'FEE', name: 'FEELESS' } })); }} data-testid="td-fee-free"><b>0%</b>buying $FEE · FEECAT · rFEE</button>
    <button type="button" className="td-fee" aria-expanded={why} onClick={() => setWhy(w => !w)} data-testid="td-fee-sol"><b>{pct == null ? '…' : Number(pct) > 0 ? `≤${pct}%` : '0%'}</b>other Solana swaps</button>
    {why && <p className="td-fee-more">{f && Number(pct) > 0 ? `Charged on eligible Solana swaps, cut by up to ${best}% by your $FEE holder tier. The exact fee is on every quote before you sign — never a surprise.` : 'No FEELESS fee is active right now.'}</p>}
    <button type="button" className="td-fee" data-tip="EVM swaps, bridges and gas go through LI.FI; every fee is itemised on the quote before you sign. Tap: open Bridge." onClick={() => onMode?.('bridge')} data-testid="td-fee-bridge">
      <ShieldCheck size={14} /><b>{f?.lifi ? `${(f.lifi.fee * 100).toFixed(2)}%` : '0%'}</b>bridge &amp; gas</button>
  </div>;
}

export function TradeDesk({ swap }) {
  const [mode, setMode] = useState('swap');
  const modes = [['swap', 'Swap', Repeat], ['bridge', 'Bridge', ArrowLeftRight], ['gas', 'Get gas', Fuel], ['dust', '🧹 Dust', null]];
  return <section className="trade-desk" data-testid="trade-desk">
    <nav className="td-modes">{modes.map(([k, l, Icon]) => <button key={k} type="button" className={mode === k ? 'active' : ''} onClick={() => setMode(k)} data-testid={`td-mode-${k}`}>{Icon ? <Icon size={15} /> : null}{l}</button>)}</nav>
    {mode === 'swap' && swap}
    {mode === 'bridge' && <BridgeDesk />}
    {mode === 'gas' && <GetGas />}
    {mode === 'dust' && <React.Suspense fallback={<p className="m-dim">Loading…</p>}><DustCleanup /></React.Suspense>}
    <FeeExplainer onMode={setMode} />
  </section>;
}

// Live status of everything a trade touches — so users know it's healthy before they sign.
function StatusStrip() {
  const [st, setSt] = useState({});
  useEffect(() => {
    let alive = true;
    const ping = async (k, url, ok) => { const t = performance.now(); try { const r = await fetch(url); const d = await r.json().catch(() => ({})); if (alive) setSt(x => ({ ...x, [k]: { up: r.ok && ok(d), ms: Math.round(performance.now() - t) } })); } catch { if (alive) setSt(x => ({ ...x, [k]: { up: false } })); } };
    const run = () => { ping('swap', apiUrl('/api/trading/status'), d => d.execution_ready); ping('bridge', 'https://li.quest/v1/chains?chainTypes=EVM', d => Array.isArray(d.chains)); ping('data', apiUrl('/api/reputation/site'), () => true); };
    run(); const t = setInterval(run, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const chip = (k, label) => { const s = st[k]; return <span key={k} className={`td-status ${s ? (s.up ? 'up' : 'down') : ''}`}><i />{label}{s?.up && s.ms ? ` · ${s.ms}ms` : s && !s.up ? ' · down' : ''}</span>; };
  return <div className="td-statuses" data-testid="td-status">{chip('swap', 'Solana swaps')}{chip('bridge', 'Bridge routes')}{chip('data', 'FEELESS data')}</div>;
}

// Simple trade page: one swap box, optional Edge score, a little context. Nothing else.
export function SimpleTrade({ swap, pair }) {
  // The Edge score follows whatever coin is in the swap box, not just the page's default coin.
  const [target, setTarget] = useState(null);
  useEffect(() => {
    const onTarget = e => setTarget(e.detail?.mint || null);
    window.addEventListener('feeless:swap-target', onTarget);
    return () => window.removeEventListener('feeless:swap-target', onTarget);
  }, []);
  const needLookup = target && target !== pair?.baseToken?.address;
  const { data } = useMarket(needLookup ? `/search?q=${encodeURIComponent(target)}` : null, 60000);
  const found = needLookup ? (data?.pairs || []).filter(p => p.baseToken?.address === target).sort((a, b) => (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0))[0] : null;
  const edgePair = needLookup ? found : pair;
  return <div className="trade-simple" data-testid="trade-simple">
    <div className="trade-main"><div className="trade-left"><TopPumpCoins /><FollowingCalls /></div><div className="trade-center"><TradeDesk swap={swap} /></div></div>
    <StatusStrip />
    {edgePair && <section className="td-edge" data-testid="trade-edge"><h3>FEELESS Edge score · ${edgePair.baseToken?.symbol || 'this coin'}</h3><EdgeScore pair={edgePair} /></section>}
    <div className="td-info">
      <div><b>Swap</b><span>Best route across Solana DEXs (Jupiter) or any EVM chain (LI.FI). You see the exact output, price impact and fees before signing.</span></div>
      <div><b>Bridge</b><span>Move SOL, USDC or ETH between Solana and 11 EVM chains. Most routes land in seconds to a few minutes.</span></div>
      <div><b>Gas</b><span>Empty on a chain? FEELESS turns SOL (or spare gas elsewhere) into gas there — one route, one signature.</span></div>
    </div>
  </div>;
}
