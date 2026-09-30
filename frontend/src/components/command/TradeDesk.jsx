import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ArrowLeftRight, Fuel, Repeat, ShieldCheck } from 'lucide-react';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl } from '../../lib/api';
import { EdgeScore } from '../terminal/EdgeScore';
import { useMarket } from '../../hooks/useMarket';
import { lifiFeelessFee } from '../../lib/lifiFee';
import { CHAIN_ID, NATIVE, toUnits, fromUnits, lifiServerQuote, executeLifi } from '../../lib/lifiExec';
import { FollowingCalls } from './FollowingCalls';
import { TopPumpCoins } from './TopPumpCoins';
import { moneyConfirmed, watchBridge } from '../../lib/moneyConfirm';

// The trade desk: Swap (the existing Jupiter/LI.FI flows), Bridge (any EVM chain -> any EVM chain)
// and Get Gas (turn what you hold on one chain into gas on another). Non-custodial throughout:
// every route is a quote the user reviews, and every transaction is signed in their own wallet.
const NAMES = { ethereum: 'Ethereum', base: 'Base', bsc: 'BNB Chain', arbitrum: 'Arbitrum', avalanche: 'Avalanche', polygon: 'Polygon', optimism: 'Optimism', zksync: 'zkSync', zora: 'Zora', cronos: 'Cronos', unichain: 'Unichain', worldchain: 'World Chain' };
const USDC_DECIMALS = { bsc: 18 }; // Binance-Peg USDC has 18 decimals; everywhere else it is 6
const cleanAmount = v => { const [w, ...f] = v.replace(/[^0-9.]/g, '').split('.'); return f.length ? `${w}.${f.join('')}` : w; };

// One LI.FI route: quote (FEELESS server, verified) -> review -> secure execute. Shared by Bridge and Get Gas.
function useRoute() {
  const { wallet, provider, switchTo, connect } = useWallet() || {};
  const [quote, setQuote] = useState(null); const [busy, setBusy] = useState(false); const [step, setStep] = useState('');
  const ensureEvm = async chain => { let w = wallet; if (!w || w.chain !== 'evm') w = (await (switchTo ? switchTo(chain) : connect('evm'))).wallet; return w; };
  const getQuote = async ({ fromChain, toChain, fromToken, toToken, amount, decimals = 18 }) => {
    setBusy(true); setQuote(null);
    try {
      const w = await ensureEvm(fromChain);
      setQuote(await lifiServerQuote({ fromChain: CHAIN_ID[fromChain], toChain: CHAIN_ID[toChain], fromToken, toToken, fromAmount: toUnits(amount, decimals), fromAddress: w.address, slippage: 0.01 }));
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in wallet.' : e.message); } finally { setBusy(false); }
  };
  const execute = async () => {
    setBusy(true);
    try {
      const out = await executeLifi({ quote, wallet, provider, switchTo, onStep: setStep });
      const done = out.status === 'DONE'; const fc = quote.action.fromChainId, tc = quote.action.toChainId;
      if (done || fc === tc) moneyConfirmed({ title: fc === tc ? 'Swap confirmed' : 'Bridge delivered', chain: fc, hash: out.hash, wallet: wallet?.address });
      else { toast.info('Bridge sent — source confirmed', { description: 'Cross-chain routes land in 1–5 min. We\'ll confirm when funds arrive.' }); watchBridge({ hash: out.hash, fromChainId: fc, toChainId: tc }); }
      setQuote(null);
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in wallet — nothing sent.' : e.message); } finally { setBusy(false); setStep(''); }
  };
  return { wallet, quote, busy, step, getQuote, execute, clear: () => setQuote(null) };
}

function RouteReview({ quote, busy, step, onExecute, onClear }) {
  if (!quote) return null;
  const out = fromUnits(quote.estimate.toAmount, quote.action.toToken.decimals);
  const gasUsd = (quote.estimate.gasCosts || []).reduce((a, g) => a + Number(g.amountUSD || 0), 0);
  const feeUsd = (quote.estimate.feeCosts || []).reduce((a, g) => a + Number(g.amountUSD || 0), 0);
  return <div className="td-review" data-testid="td-review">
    <div><small>You receive ≈</small><b>{out.toLocaleString(undefined, { maximumFractionDigits: 6 })} {quote.action.toToken.symbol}</b></div>
    <div className="td-review-meta"><span>via {quote.toolDetails?.name || quote.tool}</span><span>network gas ≈ ${gasUsd.toFixed(2)}</span><span>provider / route fees ≈ ${feeUsd.toFixed(2)}</span><span>{lifiFeelessFee(quote) ? `FEELESS fee ${(Number(lifiFeelessFee(quote).percentage || 0) * 100).toFixed(2)}% ≈ $${Number(lifiFeelessFee(quote).amountUSD || 0).toFixed(2)} (included above)` : 'FEELESS platform fee: 0%'}</span><span>~{Math.max(1, Math.round((quote.estimate.executionDuration || 30) / 60))} min</span></div>
    <div className="td-review-actions"><button type="button" className="btn-outline" onClick={onClear}>Cancel</button><button type="button" className="btn-primary" disabled={busy} onClick={onExecute}>{busy ? (step || 'Confirm in wallet…') : 'Confirm & sign'}</button></div>
  </div>;
}

function ChainSelect({ value, onChange, label }) {
  return <label className="td-field"><small>{label}</small><select value={value} onChange={e => onChange(e.target.value)}>{Object.keys(CHAIN_ID).map(c => <option key={c} value={c}>{NAMES[c]}</option>)}</select></label>;
}

function Bridge() {
  const r = useRoute();
  const [from, setFrom] = useState('base'); const [to, setTo] = useState('arbitrum');
  const [asset, setAsset] = useState('native'); const [amount, setAmount] = useState('0.01');
  const tok = c => (asset === 'native' ? NATIVE : 'USDC');
  return <div className="td-panel">
    <div className="td-row"><ChainSelect label="From" value={from} onChange={v => { setFrom(v); r.clear(); }} /><button type="button" className="td-swapbtn" aria-label="Flip chains" onClick={() => { setFrom(to); setTo(from); r.clear(); }}><ArrowLeftRight size={15} /></button><ChainSelect label="To" value={to} onChange={v => { setTo(v); r.clear(); }} /></div>
    <div className="td-row"><label className="td-field"><small>Asset</small><select value={asset} onChange={e => { setAsset(e.target.value); r.clear(); }}><option value="native">Native gas coin</option><option value="usdc">USDC</option></select></label><label className="td-field"><small>Amount</small><input inputMode="decimal" value={amount} onChange={e => { setAmount(cleanAmount(e.target.value)); r.clear(); }} /></label></div>
    {!r.quote && <button type="button" className="btn-primary td-go" disabled={r.busy || from === to || !Number(amount)} onClick={() => r.getQuote({ fromChain: from, toChain: to, fromToken: tok(from), toToken: tok(to), amount, decimals: asset === 'usdc' ? (USDC_DECIMALS[from] ?? 6) : 18 })}>{r.busy ? 'Finding the best route…' : from === to ? 'Pick two different chains' : 'Get bridge quote'}</button>}
    <RouteReview quote={r.quote} busy={r.busy} step={r.step} onExecute={r.execute} onClear={r.clear} />
  </div>;
}

function GetGas() {
  const r = useRoute();
  const [gas, setGas] = useState(null); const [target, setTarget] = useState(null); const [usd, setUsd] = useState('2');
  const address = r.wallet?.chain === 'evm' ? r.wallet.address : null;
  useEffect(() => {
    if (!address) { setGas(null); return undefined; }
    let alive = true;
    fetch(apiUrl(`/api/reputation/gas/${address}`)).then(x => x.json()).then(d => alive && setGas(d)).catch(() => {});
    return () => { alive = false; };
  }, [address]);
  if (!address) return <div className="td-panel td-empty"><Fuel size={22} /><p>Connect an EVM wallet — FEELESS checks your gas on all 12 chains at once and routes what you already hold into gas where you're empty.</p></div>;
  if (!gas) return <div className="td-panel"><p className="wp-bio">Checking gas on 12 chains…</p></div>;
  const source = gas.chains.find(c => c.enough && c.usd > Number(usd) * 1.5);
  return <div className="td-panel">
    <div className="td-gas-grid">{gas.chains.map(c => <button key={c.chain} type="button" className={`td-gas ${c.enough ? 'ok' : 'low'} ${target === c.chain ? 'on' : ''}`} onClick={() => { setTarget(c.chain); r.clear(); }}>
      <b>{NAMES[c.chain] || c.chain}</b><small>{c.balance == null ? 'unavailable' : `${c.balance.toFixed(4)} ${c.symbol}`}</small><em>{c.enough ? '✓ gas ok' : '⛽ needs gas'}</em></button>)}</div>
    {target && <div className="td-row">
      <label className="td-field"><small>Gas to add (USD)</small><input inputMode="decimal" value={usd} onChange={e => { setUsd(cleanAmount(e.target.value)); r.clear(); }} /></label>
      {source ? <button type="button" className="btn-primary td-go" disabled={r.busy || source.chain === target} onClick={() => r.getQuote({ fromChain: source.chain, toChain: target, fromToken: NATIVE, toToken: NATIVE, amount: (Number(usd) / (source.usd / source.balance)).toFixed(8) })}>{r.busy ? 'Routing…' : `Use ${source.symbol} on ${NAMES[source.chain]} → gas on ${NAMES[target]}`}</button>
        : <p className="wp-bio">No chain with enough spare balance to route from — add funds on any chain first.</p>}
    </div>}
    <RouteReview quote={r.quote} busy={r.busy} step={r.step} onExecute={r.execute} onClear={r.clear} />
  </div>;
}

function FeeExplainer() {
  const [f, setF] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/fees/public')).then(x => x.json()).then(setF).catch(() => {}); }, []);
  const pct = f ? (f.platformFeeBps / 100).toFixed(2) : null;
  const best = f ? Math.max(...Object.values(f.tierDiscountPct || { 0: 0 })) : 0;
  return <div className="td-fees" data-testid="td-fees">
    <span className="td-fee good" title="Buying $FEE, FEECAT or rFEE with SOL, USDC or USDT is free. Selling them pays the platform fee."><b>0%</b>buying $FEE · FEECAT · rFEE</span>
    <span className="td-fee" title={f && Number(pct) > 0 ? `Charged on eligible Solana swaps, reduced up to ${best}% by holder tier. The exact fee is shown on every quote before you sign.` : 'No FEELESS fee is active right now.'}><b>{pct == null ? '…' : Number(pct) > 0 ? `≤${pct}%` : '0%'}</b>other Solana swaps</span>
    <span className="td-fee" title={f?.lifi ? 'EVM swaps, bridges and gas carry the FEELESS fee through LI.FI (LI.FI adds its own 0.25%); shown on every quote before you sign.' : 'No FEELESS fee on EVM routes yet; provider and network fees are itemized before signing.'}><ShieldCheck size={14} /><b>{f?.lifi ? `${(f.lifi.fee * 100).toFixed(2)}%` : '0%'}</b>bridge &amp; gas</span>
  </div>;
}

export function TradeDesk({ swap }) {
  const [mode, setMode] = useState('swap');
  const modes = [['swap', 'Swap', Repeat], ['bridge', 'Bridge', ArrowLeftRight], ['gas', 'Get gas', Fuel]];
  return <section className="trade-desk" data-testid="trade-desk">
    <nav className="td-modes">{modes.map(([k, l, Icon]) => <button key={k} type="button" className={mode === k ? 'active' : ''} onClick={() => setMode(k)} data-testid={`td-mode-${k}`}><Icon size={15} />{l}</button>)}</nav>
    {mode === 'swap' && swap}
    {mode === 'bridge' && <Bridge />}
    {mode === 'gas' && <GetGas />}
    <FeeExplainer />
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
      <div><b>Bridge</b><span>Move native coins or USDC between 12 EVM chains. Most routes land in 1–5 minutes.</span></div>
      <div><b>Gas</b><span>Empty on a chain? FEELESS turns coin you already hold elsewhere into gas there — one route, one signature.</span></div>
    </div>
  </div>;
}
