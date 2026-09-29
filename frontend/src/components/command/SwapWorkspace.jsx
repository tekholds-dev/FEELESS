import { useDraft } from '../../lib/useDraft';
import { ReceiptsCard } from './ReceiptsCard';
import { ReceiptPreview } from './ReceiptPreview';
import { TokenPicker } from './TokenPicker';
import { SlippagePicker } from './SlippagePicker';
import { EvmSwap } from './EvmSwap';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { VersionedTransaction } from '@solana/web3.js';
import { ArrowDownUp, ArrowRight, ArrowUpRight, ShieldCheck, Wallet, RefreshCw } from 'lucide-react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '../ui/dialog';
import { keepReceipt } from '../../lib/receipts';
import { useWallet } from '../../hooks/useWallet';
import { useClock } from './WorkspaceChrome';
import { FeeBackPreview } from './FeeBack';
import { shortAddress } from '../../lib/dexscreener';
import { apiUrl } from '../../lib/api';
import { ReputationBadge } from '../terminal/ReputationBadge';

const API = apiUrl('/api/trading');
const SOL = 'So11111111111111111111111111111111111111112';
const PENDING_ORDER_STORAGE_KEY = 'feeless.pending-swap-order';
const solAsset = { id: 'sol', mint: SOL, symbol: 'SOL', name: 'Solana', chain: 'solana', decimals: 9 };
function assetFromPair(pair) {
  if (!pair?.baseToken?.address) return null;
  return { id: `pair-${pair.baseToken.address}`, mint: pair.baseToken.address, symbol: pair.baseToken.symbol || 'TOKEN', name: pair.baseToken.name || pair.baseToken.symbol || 'Selected token', chain: pair.chainId, pair };
}
function assetOptions(feeAssets, pair) {
  const values = [solAsset, ...(feeAssets || []).filter(asset => asset?.mint).map(asset => ({ id: asset.id, mint: asset.mint, symbol: asset.label || asset.id?.toUpperCase(), name: asset.label || asset.id?.toUpperCase(), chain: asset.chain })), assetFromPair(pair)].filter(Boolean);
  return values.filter((asset, index, list) => list.findIndex(candidate => candidate.mint === asset.mint) === index);
}
async function request(path, body) {
  const res = await fetch(`${API}${path}`, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to process this swap request.');
  return data;
}
function readPendingOrder() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(PENDING_ORDER_STORAGE_KEY) || 'null');
    return saved && typeof saved.order_id === 'string' && saved.order_id.length >= 32 ? { order_id: saved.order_id } : null;
  } catch {
    return null;
  }
}
function rememberPendingOrder(orderId) {
  try {
    window.localStorage.setItem(PENDING_ORDER_STORAGE_KEY, JSON.stringify({ order_id: orderId }));
  } catch {
    // A storage failure must not block a wallet-approved transaction.
  }
}
function forgetPendingOrder() {
  try {
    window.localStorage.removeItem(PENDING_ORDER_STORAGE_KEY);
  } catch {
    // Storage may be unavailable in privacy-restricted browsers.
  }
}
export function units(value, decimals) {
  if (value == null) return 'Unavailable';
  if (decimals == null) return `${value} base units`;
  try { const raw = BigInt(value); const base = 10n ** BigInt(decimals); const fraction = (raw % base).toString().padStart(decimals, '0').replace(/0+$/, ''); return `${raw / base}${fraction ? `.${fraction}` : ''}`; }
  catch { return 'Unavailable'; }
}

export const SwapWorkspace = ({ pair, feeAsset, feeAssets = [], feeCat, onWallet, fontScale = 'normal' }) => {
  const { wallet, provider } = useWallet();
  const reviewScale = ['large', 'xlarge'].includes(fontScale) ? fontScale : 'normal';
  useEffect(() => {
    const scale = reviewScale === 'large' ? '1.12' : reviewScale === 'xlarge' ? '1.24' : '1';
    document.body.style.setProperty('--swap-review-readable-scale', scale);
    return () => document.body.style.removeProperty('--swap-review-readable-scale');
  }, [reviewScale]);
  const [found, setFound] = useState([]);   // tokens picked from search join the pickers
  const addFound = t => setFound(f => [{ id: `s-${t.mint}`, mint: t.mint, symbol: t.symbol, name: t.name, icon: t.icon, chain: 'solana' }, ...f.filter(x => x.mint !== t.mint)].slice(0, 12));
  const [slipOpen, setSlipOpen] = useState(false);
  const [network, setNetwork] = useState('solana');   // 'solana' = Jupiter; EVM networks swap through LI.FI
  // Coins picked elsewhere on the page (Top 10 on Pump) load into the receive side.
  useEffect(() => {
    const onPick = e => { const t = e.detail; if (!t?.mint) return; addFound(t); setOutputMint(t.mint); setOrder(null); };
    window.addEventListener('feeless:swap-set-output', onPick);
    return () => window.removeEventListener('feeless:swap-set-output', onPick);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  // Wallet coins (SOL + tokens, by USD value) power "your coins first" in the pickers and Balance / Max.
  const [holdings, setHoldings] = useState([]);
  useEffect(() => {
    if (wallet?.chain !== 'solana' || !wallet?.address) { setHoldings([]); return undefined; }
    let alive = true;
    const load = () => fetch(`${API}/holdings/${wallet.address}`).then(r => (r.ok ? r.json() : null)).then(d => alive && d && setHoldings(d.tokens || [])).catch(() => {});
    load(); const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [wallet?.address, wallet?.chain]);
  const [routeOpen, setRouteOpen] = useState(false);
  const options = useMemo(() => {
    const base = assetOptions(feeAssets, pair);
    return [...base, ...found.filter(t => !base.some(o => o.mint === t.mint))];
  }, [feeAssets, pair, found]);
  const selectedPairAsset = assetFromPair(pair);
  const [inputMint, setInputMint] = useState(SOL);
  const [outputMint, setOutputMint] = useState(selectedPairAsset?.mint || feeAsset?.mint || SOL);
  const inputAsset = options.find(asset => asset.mint === inputMint) || solAsset;
  const outputAsset = options.find(asset => asset.mint === outputMint) || options[1] || solAsset;
  const chain = pair?.chainId || inputAsset.chain || outputAsset.chain || 'solana';
  const [amount, setAmount] = useDraft('swap-amount', '0.01');
  const [slippage, setSlippage] = useState('50'); const [order, setOrder] = useState(null);
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState(''); const [review, setReview] = useState(false);
  const [result, setResult] = useState(null); const [recoveryUnavailable, setRecoveryUnavailable] = useState(false); const lock = useRef(false); const recoveredOrder = useRef(null); const now = useClock();
  const expired = order && now / 1000 >= order.expires_at;
  const remaining = order ? Math.max(0, Math.ceil(order.expires_at - now / 1000)) : 0;
  // Only trust an order that was quoted for exactly the coins and amount on screen. A slow earlier quote
  // (e.g. the default $FEE pick) must never be shown — or signed — under a coin picked afterwards.
  const orderMatches = Boolean(order) && (!order.output_mint || (order.input_mint === inputMint && order.output_mint === outputMint && String(order.amount) === String(amount)));
  const quote = orderMatches ? order.quote : undefined;
  const QUOTE_REFRESH_MS = 10000;
  const [quotedAt, setQuotedAt] = useState(0); const quoteSeq = useRef(0); const refreshing = useRef(false);
  const refreshIn = order ? Math.max(0, Math.ceil((quotedAt + QUOTE_REFRESH_MS - now) / 1000)) : 0;
  const applyRecoveredStatus = data => {
    setRecoveryUnavailable(false);
    if (['confirmed', 'failed'].includes(data.state)) {
      forgetPendingOrder();
      recoveredOrder.current = null;
      setResult(data);
      setMessage(data.state === 'confirmed' ? 'Recovered swap is confirmed on-chain.' : 'Recovered swap failed. Inspect the transaction reference.');
    } else if (data.state === 'submitted') {
      setResult(data);
      setMessage('Recovered pending swap. Check confirmation before starting another trade. Nothing was resubmitted.');
    } else {
      setResult(null);
      setMessage('Saved order is not awaiting confirmation. Nothing was resubmitted; choose a fresh order if you want to quote again.');
    }
  };
  const recoverSavedOrder = async (isActive = () => true) => {
    const saved = readPendingOrder();
    const orderId = recoveredOrder.current || saved?.order_id;
    if (!orderId) return;
    recoveredOrder.current = orderId;
    setBusy(true);
    setRecoveryUnavailable(false);
    try {
      const data = await request(`/order/${encodeURIComponent(orderId)}`);
      if (!isActive()) return;
      applyRecoveredStatus(data);
    } catch (error) {
      if (!isActive()) return;
      setRecoveryUnavailable(true);
      setMessage(`Saved swap found, but status could not be restored: ${error.message}`);
    } finally {
      if (isActive()) setBusy(false);
    }
  };
  const startFreshOrder = () => {
    forgetPendingOrder();
    recoveredOrder.current = null;
    setRecoveryUnavailable(false);
    setOrder(null);
    setResult(null);
    setMessage('');
    setReview(false);
  };
  useEffect(() => {
    if (recoveredOrder.current && readPendingOrder()) return;
    setOrder(null); setResult(null); setMessage(''); setReview(false);
  }, [inputMint, outputMint, chain, amount, slippage, wallet?.address]);
  useEffect(() => {
    const saved = readPendingOrder();
    if (!saved) return undefined;
    recoveredOrder.current = saved.order_id;
    let active = true;
    recoverSavedOrder(() => active).catch(() => {});
    return () => { active = false; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (selectedPairAsset?.mint) {
      setOutputMint(selectedPairAsset.mint);
      setInputMint(SOL);
    } else if (feeAsset?.mint && (outputMint === SOL || !options.some(asset => asset.mint === outputMint))) {
      setOutputMint(feeAsset.mint);
      setInputMint(SOL);
    }
  }, [selectedPairAsset?.mint, feeAsset?.mint, options, outputMint]);
  const payHolding = holdings.find(h => h.mint === inputMint);   // after inputMint is declared
  const reverse = () => { setInputMint(outputMint); setOutputMint(inputMint); };
  // Tell the page which coin is being traded (the non-SOL side) so context panels like the Edge score follow it.
  useEffect(() => {
    const target = outputMint !== SOL ? outputMint : inputMint !== SOL ? inputMint : null;
    window.dispatchEvent(new CustomEvent('feeless:swap-target', { detail: { mint: target } }));
  }, [inputMint, outputMint]);
  const outputIsPair = pair && outputAsset.mint === selectedPairAsset?.mint;
  const impactPct = quote?.priceImpactPct != null ? Number(quote.priceImpactPct) : quote?.priceImpact != null ? Number(quote.priceImpact) : null;
  // Jupiter's priceImpactPct is a fraction (-0.0092 = 0.92% worse); show it as a plain positive percent.
  const impactShown = quote?.priceImpactPct != null ? Math.abs(Number(quote.priceImpactPct) * 100) : quote?.priceImpact != null ? Math.abs(Number(quote.priceImpact)) : null;
  const impactTier = impactPct == null ? '' : Math.abs(impactPct) >= 5 ? 'impact-high' : Math.abs(impactPct) >= 1 ? 'impact-medium' : 'impact-low';
  // Newest request wins: every call takes a ticket and only the latest ticket may set the order.
  // silent = background refresh: keep the current quote on screen until the new one lands.
  const loadQuote = async (silent = false) => {
    if (lock.current) return; // review / signing in progress
    const seq = ++quoteSeq.current;
    if (!silent) { setBusy(true); setMessage(''); setOrder(null); setResult(null); } else refreshing.current = true;
    try { if (inputMint === outputMint) throw new Error('Choose two different assets.'); const data = await request('/quote', { input_mint: inputMint, output_mint: outputMint, amount, slippage_bps: Number(slippage), wallet: wallet?.chain === 'solana' ? wallet.address : null }); if (seq !== quoteSeq.current) return; setOrder(data); setQuotedAt(Date.now());
      // Pre-simulate in the background so "Review swap" opens instantly. A failure here is not shown:
      // the Review click simulates again and reports it.
      if (data.quote?.transaction) request('/simulate', { order_id: data.order_id }).then(() => { if (seq === quoteSeq.current) setOrder(o => (o?.order_id === data.order_id ? { ...o, simulated: true } : o)); }).catch(() => {}); }
    catch (e) { if (seq === quoteSeq.current && !silent) setMessage(e.message); }
    finally { if (silent) refreshing.current = false; if (seq === quoteSeq.current && !silent) setBusy(false); }
  };
  // Like Jupiter: keep the price live — re-quote every 10s while the card is idle and visible.
  useEffect(() => {
    if (!orderMatches || review || result || busy || lock.current || refreshing.current || chain !== 'solana' || document.hidden) return;
    if (now - quotedAt >= QUOTE_REFRESH_MS) loadQuote(true);
  }, [now]); // eslint-disable-line react-hooks/exhaustive-deps
  // Like Jupiter: re-quote shortly after the amount or a coin changes (never on first render).
  const autoQuoteReady = useRef(false);
  useEffect(() => {
    if (!autoQuoteReady.current) { autoQuoteReady.current = true; return undefined; }
    if (chain !== 'solana' || !inputMint || inputMint === outputMint || !/^\d+(\.\d+)?$/.test(amount) || Number(amount) <= 0 || result) return undefined;
    const t = setTimeout(() => { loadQuote(); }, 300);
    return () => clearTimeout(t);
  }, [amount, inputMint, outputMint, slippage]); // eslint-disable-line react-hooks/exhaustive-deps
  const simulate = async () => {
    if (lock.current || expired || !quote?.transaction) return;
    lock.current = true; quoteSeq.current++; setBusy(true); setMessage('');
    try { if (!order.simulated) await request('/simulate', { order_id: order.order_id }); setReview(true); }
    catch (e) { setMessage(e.message); } finally { lock.current = false; setBusy(false); }
  };
  const sign = async () => {
    if (lock.current || expired || !quote?.transaction || wallet?.chain !== 'solana') return;
    lock.current = true; quoteSeq.current++; setBusy(true); setReview(false); setMessage('Review the transaction in Phantom. Nothing is sent until you approve.');
    try {
      if (!provider?.signTransaction || provider.publicKey?.toString() !== wallet.address) throw new Error('Connected Phantom account changed. Reconnect and request a fresh quote.');
      const tx = VersionedTransaction.deserialize(Uint8Array.from(atob(quote.transaction), c => c.charCodeAt(0)));
      if (tx.message.staticAccountKeys[0].toBase58() !== wallet.address) throw new Error('Wallet does not match the quoted fee payer.');
      // Never hang: if the wallet popup is blocked or ignored, stop after 60s and say so.
      const signed = await Promise.race([provider.signTransaction(tx), new Promise((_, rej) => setTimeout(() => rej(new Error('Wallet did not respond. Open your wallet (check for a blocked popup), then get a fresh quote.')), 60000))]);
      const encoded = btoa(String.fromCharCode(...signed.serialize()));
      rememberPendingOrder(order.order_id);
      recoveredOrder.current = order.order_id;
      const response = await request('/execute', { order_id: order.order_id, signed_transaction: encoded });
      setResult(response);
      if (response.signature && response.state !== 'failed') keepReceipt(response.signature, wallet.address, 'swap');
      if (['confirmed', 'failed'].includes(response.state)) forgetPendingOrder();
      if (response.state === 'confirmed') window.dispatchEvent(new CustomEvent('feeless:trade-confirmed', { detail: { mint: outputMint === SOL ? inputMint : outputMint } }));
      setMessage(response.state === 'confirmed' ? 'Swap confirmed on-chain.' : response.state === 'failed' ? 'Swap failed. Inspect the transaction reference.' : 'Submitted / confirmation pending. Check status before another trade.');
    } catch (e) { setMessage(e.code === 4001 ? 'Wallet approval declined. No transaction submitted.' : e.message || 'Wallet rejected the request.'); }
    finally { lock.current = false; setBusy(false); }
  };
  const status = async () => {
    const orderId = order?.order_id || result?.order_id;
    if (!orderId) return;
    setBusy(true);
    try {
      const data = await request(`/order/${encodeURIComponent(orderId)}`);
      setResult(data);
      if (['confirmed', 'failed'].includes(data.state)) forgetPendingOrder();
      setMessage(data.state === 'confirmed' ? 'Swap confirmed on-chain.' : data.state === 'failed' ? 'Swap failed. Inspect the transaction reference.' : data.state === 'quoted' ? 'Order is still awaiting submission. Nothing was resubmitted; request a fresh quote.' : `Transaction status: ${data.state}.`);
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  };
  if (network !== 'solana') return <div className="swap-desk" data-testid="swap-workspace"><EvmSwap chain={network} onNetwork={setNetwork} /></div>;
  return <div className="swap-desk" data-testid="swap-workspace"><section className="swap-order jup-card">
    <div className="jup-head"><span className="jup-title"><ArrowDownUp size={15} />Swap</span>
      <button type="button" className={`jup-chip ${slipOpen ? 'on' : ''}`} onClick={() => setSlipOpen(o => !o)} data-testid="swap-slippage-toggle">Slippage {Number(slippage) / 100}%</button>
      <button type="button" className="jup-icon" data-testid="swap-get-quote" title={quote ? 'Refresh quote' : 'Get best route'} aria-label={quote ? 'Refresh quote' : 'Get best available route'} onClick={() => loadQuote()} disabled={busy || chain !== 'solana' || !inputMint || inputMint === outputMint || !/^\d+(\.\d+)?$/.test(amount) || Number(amount) <= 0}><RefreshCw size={14} className={busy ? 'spin' : ''} /></button></div>
    {slipOpen && <div className="slippage-controls"><span>Max slippage</span><SlippagePicker value={slippage} onChange={setSlippage} disabled={busy} /></div>}
    <div className="jup-panel"><div className="jup-panel-head"><small>You pay</small>{payHolding && <span className="jup-bal">Balance {Number(payHolding.amount).toLocaleString(undefined, { maximumFractionDigits: 4 })}<button type="button" onClick={() => setAmount(String(inputMint === SOL ? Math.max(0, Math.floor((payHolding.amount - 0.01) * 1e6) / 1e6) : payHolding.amount))} disabled={busy}>Max</button></span>}</div>
      <div className="jup-row"><TokenPicker testId="swap-input-asset" onNetwork={setNetwork} holdings={holdings} value={inputMint} options={options} onChange={setInputMint} onPickRemote={t => { addFound(t); setInputMint(t.mint); setOrder(null); }} disabled={busy} />
        <input className="jup-amount" data-testid="swap-amount" type="text" inputMode="decimal" placeholder="0.00" aria-label={`Amount of ${inputAsset.symbol}`} value={amount} onChange={e => setAmount(e.target.value.replace(/[^0-9.]/g, ''))} disabled={busy} /></div>
      <div className="jup-quick">{['0.1', '0.5', '1'].map(v => inputMint === SOL && <button key={v} type="button" onClick={() => setAmount(v)} disabled={busy}>{v} SOL</button>)}</div></div>
    <button className="swap-reverse-button jup-flip" data-testid="swap-reverse" title="Reverse trade direction" aria-label="Reverse trade direction" onClick={reverse} disabled={busy}><ArrowDownUp size={16} /></button>
    <div className="jup-panel is-receive"><div className="jup-panel-head"><small>You receive</small>{outputIsPair && <span className="jup-trust"><ReputationBadge pair={pair} compact /></span>}</div>
      <div className="jup-row"><TokenPicker testId="swap-output-asset" onNetwork={setNetwork} holdings={holdings} value={outputMint} options={options} onChange={setOutputMint} onPickRemote={t => { addFound(t); setOutputMint(t.mint); setOrder(null); }} disabled={busy} />
        <strong className="jup-out" data-testid="swap-output-amount">{quote ? units(quote.outAmount, order.output_metadata?.decimals) : busy ? '…' : '0'}</strong></div></div>
    {quote && <div className="jup-rate" data-testid="swap-rate"><span>Min received <b>{units(quote.otherAmountThreshold, order.output_metadata?.decimals)} {outputAsset.symbol}</b></span><span className={impactTier}>Impact {impactShown != null ? `${impactShown.toFixed(2)}%` : '—'}</span><span data-testid="swap-feeless-fee">{order?.feeless_fee?.bps ? `FEELESS fee ${(order.feeless_fee.bps / 100).toFixed(2)}%` : (order?.feeless_fee?.notes?.[0] || 'No FEELESS fee')}</span><span data-testid="swap-quote-refresh">{expired ? 'Quote expired' : `Refresh ${refreshIn}s`}</span></div>}
    {chain !== 'solana' && <p className="market-error" data-testid="swap-unsupported-chain">{chain} is intelligence-only. In-app execution currently supports Solana.</p>}{message && <p data-testid="swap-status-message" className="swap-message" role="status">{message}</p>}{recoveryUnavailable && <div className="swap-recovery-actions" data-testid="swap-recovery-actions"><button type="button" className="btn-outline" data-testid="swap-retry-recovery" onClick={() => recoverSavedOrder()} disabled={busy}><RefreshCw size={14} />{busy ? 'Checking…' : 'Retry status check'}</button><button type="button" className="btn-outline" data-testid="swap-fresh-order" onClick={startFreshOrder} disabled={busy}>Start a fresh order</button></div>}{!result && <div className="swap-buttons jup-cta">{wallet?.chain !== 'solana' ? <button className="btn-primary" data-testid="swap-connect-wallet" onClick={onWallet}><Wallet size={15} />Connect Solana wallet</button> : <button className="btn-primary" data-testid="swap-review" onClick={quote && !expired ? simulate : () => loadQuote()} disabled={busy || (quote && !expired && (!quote?.transaction || !order.output_metadata))}><ShieldCheck size={15} />{busy ? 'Working…' : !quote ? 'Get quote' : expired ? 'Quote expired — refresh' : 'Review swap'}</button>}</div>}{result && <div className="swap-result" data-testid="swap-result"><b>{result.state.toUpperCase()}</b>{result.signature && <a data-testid="swap-transaction-explorer" href={`https://solscan.io/tx/${result.signature}`} target="_blank" rel="noreferrer">{shortAddress(result.signature)}<ArrowUpRight size={13} /></a>}{result.state === 'submitted' && <button className="btn-outline" data-testid="swap-check-status" onClick={status} disabled={busy}>Check confirmation</button>}{['confirmed', 'failed'].includes(result.state) && <button data-testid="swap-new-order" className="btn-outline" onClick={startFreshOrder}>New order</button>}</div>}<p className="swap-safety"><ShieldCheck size={13} />Non-custodial. No silent slippage widening. No automatic resubmission.</p></section>{quote && !expired && <ReceiptPreview order={order} amount={amount} inputAsset={inputAsset} outputAsset={outputAsset} wallet={wallet?.address} />}<details className="route-intelligence" open={Boolean(quote) && routeOpen} onToggle={e => setRouteOpen(e.currentTarget.open)}><summary data-testid="swap-route-details">Route details{quote ? ` · ${quote.router || 'Jupiter'}` : ''}</summary><div className="command-section-title"><span>ROUTE INTELLIGENCE</span><small data-testid="quote-expiry">{order ? `${remaining}s · ${expired ? 'EXPIRED' : 'QUOTE VALIDITY'}` : 'AWAITING PROVIDER QUOTE'}</small></div>{!quote && <div className="truth-empty"><ActivityIcon /><span>Real route competition.<br />No invented quotes or fee estimates.</span></div>}{quote && <><div className="route-metrics"><div><small>ROUTER</small><b data-testid="quote-router">{quote.router || 'Jupiter'}</b></div><div><small>PRICE IMPACT</small><b data-testid="quote-price-impact" className={impactTier}>{impactShown != null ? `${impactShown.toFixed(2)}%` : 'Unavailable'}</b></div><div><small>MINIMUM OUTPUT</small><b data-testid="quote-minimum-output">{units(quote.otherAmountThreshold, order.output_metadata?.decimals)}</b></div></div><div className="route-steps">{quote.routePlan?.map((route, i) => <div key={i} data-testid={`quote-route-${i}`}><span>{i + 1}</span><b>{route.swapInfo?.label || route.label || 'Provider route'}</b><small>{route.percent != null ? `${route.percent}%` : route.bps != null ? `${route.bps / 100}%` : 'Provider allocation'}</small></div>)}</div><div className="quoted-fees">{[['Signature fee', quote.signatureFeeLamports], ['Priority fee', quote.prioritizationFeeLamports], ['Rent', quote.rentFeeLamports]].map(([label, value]) => <span key={label}>{label}<b>{value != null ? `${Number(value) / 1e9} SOL` : 'Unavailable'}</b></span>)}</div></>}<FeeBackPreview quote={quote} feeCat={feeCat} />{wallet?.address && <div className="swap-receipts"><ReceiptsCard address={wallet.address} /></div>}</details><Dialog open={review} onOpenChange={setReview}><DialogContent className="feeless-dialog" data-testid="swap-review-dialog"><DialogTitle>Review your swap</DialogTitle><DialogDescription>Solana mainnet. Simulation passed; execution still requires your explicit wallet approval.</DialogDescription>{quote && (() => { const out = Number(units(quote.outAmount, order.output_metadata?.decimals)); const rate = Number(amount) > 0 && Number.isFinite(out) ? out / Number(amount) : null; const impact = Number(quote.priceImpactPct || 0) * 100; const secs = Math.max(0, remaining || 0);
  return <div className="swap-review-hero" data-testid="swap-review-hero">
    <div className="srh-side"><small>You pay</small><b>{amount}</b><span>{inputAsset.symbol}</span></div>
    <div className="srh-flow" aria-hidden="true"><ArrowRight size={20} /></div>
    <div className="srh-side get"><small>You get ≈</small><b>{Number.isFinite(out) ? out.toLocaleString(undefined, { maximumFractionDigits: 6 }) : '—'}</b><span>{outputAsset.symbol}</span></div>
    <div className="srh-meta">{rate && <span>1 {inputAsset.symbol} = {rate.toLocaleString(undefined, { maximumFractionDigits: 6 })} {outputAsset.symbol}</span>}<span className={`srh-impact ${impact > 3 ? 'bad' : impact > 1 ? 'mid' : 'good'}`}>impact {Math.abs(impact).toFixed(2)}%</span>
      <span className="srh-clock" style={{ '--p': `${Math.min(100, (secs / 60) * 100)}%` }}><em>{secs}s</em></span></div>
  </div>; })()}<dl className="review-facts"><div><dt>Minimum output</dt><dd>{quote && units(quote.otherAmountThreshold, order.output_metadata?.decimals)}</dd></div><div><dt>Slippage</dt><dd>{Number(slippage) / 100}%</dd></div>{(() => {
        // USD everywhere: pay / get values, FEELESS fee, chain fees, total cost.
        const usd = v => (Number.isFinite(v) ? `$${v < 0.01 && v > 0 ? v.toFixed(4) : v.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '—');
        const inUsd = Number(quote?.inUsdValue);
        const outUsd = Number(quote?.outUsdValue);
        // SOL's USD price straight from this quote (Jupiter prices both legs) — no extra request.
        const outN = Number(units(quote?.outAmount, order?.output_metadata?.decimals));
        const solUsd = inputMint === SOL && Number(amount) > 0 && inUsd ? inUsd / Number(amount) : outputMint === SOL && outN > 0 && outUsd ? outUsd / outN : null;
        const feeBps = Number(order?.feeless_fee?.bps || 0);
        const feeUsd = Number.isFinite(inUsd) ? inUsd * feeBps / 10000 : NaN;
        const feeSol = solUsd && Number.isFinite(feeUsd) ? feeUsd / solUsd : NaN;
        const chainSol = ['signatureFeeLamports', 'prioritizationFeeLamports', 'rentFeeLamports'].reduce((a, k) => a + Number(quote?.[k] || 0), 0) / 1e9;
        const chainUsd = solUsd ? chainSol * solUsd : NaN;
        return <><div><dt>You pay (USD)</dt><dd>{usd(inUsd)}</dd></div><div><dt>You get (USD)</dt><dd>{usd(outUsd)}</dd></div>
          <div className="rf-fee"><dt>FEELESS fee</dt><dd>{feeBps ? `${(feeBps / 100).toFixed(2)}% · ${Number.isFinite(feeSol) ? feeSol.toFixed(6) : '—'} SOL · ${usd(feeUsd)}` : (order?.feeless_fee?.notes?.[0] || 'Free')}</dd></div>
          <div><dt>Chain fees</dt><dd>{chainSol.toFixed(6)} SOL · {usd(chainUsd)}</dd></div>
          <div className="rf-total"><dt>Total cost</dt><dd>{usd((Number.isFinite(inUsd) ? inUsd : 0) + (Number.isFinite(chainUsd) ? chainUsd : 0))}</dd></div></>;
      })()}</dl><ul className="review-checks" data-testid="swap-review-checks" aria-label="Security checks">{['Simulated on mainnet', 'Min output locked', 'Your wallet pays + signs', 'Non-custodial'].map(c => <li key={c}>{c}</li>)}</ul><p className="review-real">Real transaction · you approve in your wallet · Fee-Back not active</p><button className="btn-primary" data-testid="swap-approve-wallet" disabled={busy} onClick={expired ? () => { setReview(false); loadQuote(); } : sign}>{expired ? 'Quote expired — get fresh quote' : `Approve in ${wallet?.name || 'wallet'}`}{!expired && <ArrowUpRight size={16} />}</button></DialogContent></Dialog></div>;
};
// Search every Solana token (Jupiter's index): name, ticker or contract. Verified first, then by liquidity.

const ActivityIcon = () => <span className="route-pulse"><i /><i /><i /></span>;
