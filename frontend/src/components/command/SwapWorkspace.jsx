import React, { useEffect, useRef, useState } from 'react';
import { VersionedTransaction } from '@solana/web3.js';
import { ArrowDownUp, ArrowUpRight, ShieldCheck, Wallet, RefreshCw, AlertTriangle } from 'lucide-react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '../ui/dialog';
import { useWallet } from '../../hooks/useWallet';
import { useClock } from './WorkspaceChrome';
import { FeeBackPreview } from './FeeBack';
import { formatUSD, shortAddress } from '../../lib/dexscreener';
import { apiUrl } from '../../lib/api';

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
function assetOptionLabel(asset) {
  return `${asset.symbol} · ${asset.name}`;
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

export const SwapWorkspace = ({ pair, feeAsset, feeAssets = [], feeCat, onWallet }) => {
  const { wallet, provider } = useWallet();
  const options = assetOptions(feeAssets, pair);
  const selectedPairAsset = assetFromPair(pair);
  const [inputMint, setInputMint] = useState(SOL);
  const [outputMint, setOutputMint] = useState(selectedPairAsset?.mint || feeAsset?.mint || SOL);
  const inputAsset = options.find(asset => asset.mint === inputMint) || solAsset;
  const outputAsset = options.find(asset => asset.mint === outputMint) || options[1] || solAsset;
  const chain = pair?.chainId || inputAsset.chain || outputAsset.chain || 'solana';
  const [amount, setAmount] = useState('0.01');
  const [slippage, setSlippage] = useState('50'); const [order, setOrder] = useState(null);
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState(''); const [review, setReview] = useState(false);
  const [result, setResult] = useState(null); const lock = useRef(false); const recoveredOrder = useRef(null); const now = useClock();
  const expired = order && now / 1000 >= order.expires_at;
  const remaining = order ? Math.max(0, Math.ceil(order.expires_at - now / 1000)) : 0;
  const quote = order?.quote;
  useEffect(() => {
    if (recoveredOrder.current && readPendingOrder()) return;
    setOrder(null); setResult(null); setMessage(''); setReview(false);
  }, [inputMint, outputMint, chain, amount, slippage, wallet?.address]);
  useEffect(() => {
    const saved = readPendingOrder();
    if (!saved) return undefined;
    recoveredOrder.current = saved.order_id;
    let active = true;
    request(`/order/${encodeURIComponent(saved.order_id)}`).then(data => {
      if (!active) return;
      if (['confirmed', 'failed'].includes(data.state)) {
        forgetPendingOrder();
        recoveredOrder.current = null;
        setResult(data);
        setMessage(data.state === 'confirmed' ? 'Recovered swap is confirmed on-chain.' : 'Recovered swap failed. Inspect the transaction reference.');
      } else if (data.state === 'submitted') {
        setResult(data);
        setMessage('Recovered pending swap. Check confirmation before starting another trade. Nothing was resubmitted.');
      } else {
        forgetPendingOrder();
        recoveredOrder.current = null;
        setResult(null);
        setMessage('Recovered order was never submitted. Nothing was resubmitted; request a fresh quote to continue.');
      }
    }).catch(error => {
      if (!active) return;
      setMessage(`Saved swap found, but status could not be restored: ${error.message} Try checking again when trading is available.`);
    });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (selectedPairAsset?.mint) {
      setOutputMint(selectedPairAsset.mint);
      setInputMint(SOL);
    } else if (feeAsset?.mint && (outputMint === SOL || !options.some(asset => asset.mint === outputMint))) {
      setOutputMint(feeAsset.mint);
      setInputMint(SOL);
    }
  }, [selectedPairAsset?.mint, feeAsset?.mint, options, outputMint]);
  const reverse = () => { setInputMint(outputMint); setOutputMint(inputMint); };
  const loadQuote = async () => {
    if (lock.current) return; lock.current = true; setBusy(true); setMessage(''); setOrder(null); setResult(null);
     try { if (inputMint === outputMint) throw new Error('Choose two different assets.'); const data = await request('/quote', { input_mint: inputMint, output_mint: outputMint, amount, slippage_bps: Number(slippage), wallet: wallet?.chain === 'solana' ? wallet.address : null }); setOrder(data); }
    catch (e) { setMessage(e.message); } finally { lock.current = false; setBusy(false); }
  };
  const simulate = async () => {
    if (lock.current || expired || !quote?.transaction) return;
    lock.current = true; setBusy(true); setMessage('');
    try { await request('/simulate', { order_id: order.order_id }); setReview(true); }
    catch (e) { setMessage(e.message); } finally { lock.current = false; setBusy(false); }
  };
  const sign = async () => {
    if (lock.current || expired || wallet?.chain !== 'solana') return;
    lock.current = true; setBusy(true); setReview(false); setMessage('Review the transaction in Phantom. Nothing is sent until you approve.');
    try {
      if (!provider?.signTransaction || provider.publicKey?.toString() !== wallet.address) throw new Error('Connected Phantom account changed. Reconnect and request a fresh quote.');
      const tx = VersionedTransaction.deserialize(Uint8Array.from(atob(quote.transaction), c => c.charCodeAt(0)));
      if (tx.message.staticAccountKeys[0].toBase58() !== wallet.address) throw new Error('Wallet does not match the quoted fee payer.');
      const signed = await provider.signTransaction(tx);
      const encoded = btoa(String.fromCharCode(...signed.serialize()));
      rememberPendingOrder(order.order_id);
      recoveredOrder.current = order.order_id;
      const response = await request('/execute', { order_id: order.order_id, signed_transaction: encoded });
      setResult(response);
      if (['confirmed', 'failed'].includes(response.state)) forgetPendingOrder();
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
   return <div className="swap-desk" data-testid="swap-workspace"><section className="swap-order"><div className="command-section-title"><span><ArrowDownUp size={17} />EXECUTION DESK</span><small>JUPITER / SOLANA MAINNET</small></div><div className="swap-asset-grid"><label>YOU PAY<select data-testid="swap-input-asset" value={inputMint} onChange={e => setInputMint(e.target.value)} disabled={busy}>{options.map(asset => <option key={asset.mint} value={asset.mint} label={assetOptionLabel(asset)} />)}</select></label><button className="swap-reverse-button" data-testid="swap-reverse" title="Reverse trade direction" onClick={reverse} disabled={busy}><ArrowDownUp size={16} /></button><label>YOU RECEIVE<select data-testid="swap-output-asset" value={outputMint} onChange={e => setOutputMint(e.target.value)} disabled={busy}>{options.map(asset => <option key={asset.mint} value={asset.mint} label={assetOptionLabel(asset)} />)}</select></label></div><div className="swap-pair-heading"><b>{inputAsset.symbol} <span>→</span> {outputAsset.symbol}</b><small>{inputAsset.name} / {outputAsset.name}</small></div><label className="swap-amount-label">AMOUNT<input data-testid="swap-amount" type="text" inputMode="decimal" value={amount} onChange={e => setAmount(e.target.value)} disabled={busy} /><span>{inputAsset.symbol}</span></label><div className="slippage-controls"><span>Slippage cap</span>{[['10', '0.1%'], ['50', '0.5%'], ['100', '1%'], ['300', '3%']].map(([value, title]) => <button key={value} data-testid={`swap-slippage-${value}`} className={slippage === value ? 'active' : ''} onClick={() => setSlippage(value)} disabled={busy}>{title}</button>)}</div><div className="swap-output"><small>ESTIMATED OUTPUT</small><strong data-testid="swap-output-amount">{quote ? units(quote.outAmount, order.output_metadata?.decimals) : 'Awaiting route'}</strong><span>{outputAsset.symbol}</span></div>{chain !== 'solana' && <p className="market-error" data-testid="swap-unsupported-chain">{chain} is intelligence-only. In-app execution currently supports Solana.</p>}{message && <p data-testid="swap-status-message" className="swap-message" role="status">{message}</p>}{!result && <div className="swap-buttons"><button className="btn-outline" data-testid="swap-get-quote" onClick={loadQuote} disabled={busy || chain !== 'solana' || !inputMint || inputMint === outputMint || !/^\d+(\.\d+)?$/.test(amount) || Number(amount) <= 0}><RefreshCw size={14} />{busy ? 'Working…' : quote ? 'Refresh quote' : 'Get best available route'}</button>{wallet?.chain !== 'solana' ? <button className="btn-primary" data-testid="swap-connect-wallet" onClick={onWallet}><Wallet size={15} />Connect Solana wallet</button> : <button className="btn-primary" data-testid="swap-review" onClick={simulate} disabled={busy || !quote?.transaction || expired || !order.output_metadata}><ShieldCheck size={15} />{expired ? 'Quote expired — refresh' : 'Simulate & review'}</button>}</div>}{result && <div className="swap-result" data-testid="swap-result"><b>{result.state.toUpperCase()}</b>{result.signature && <a data-testid="swap-transaction-explorer" href={`https://solscan.io/tx/${result.signature}`} target="_blank" rel="noreferrer">{shortAddress(result.signature)}<ArrowUpRight size={13} /></a>}{result.state === 'submitted' && <button className="btn-outline" data-testid="swap-check-status" onClick={status} disabled={busy}>Check confirmation</button>}{['confirmed', 'failed'].includes(result.state) && <button data-testid="swap-new-order" className="btn-outline" onClick={() => { setOrder(null); setResult(null); setMessage(''); }}>New order</button>}</div>}<p className="swap-safety"><ShieldCheck size={13} />Non-custodial. No silent slippage widening. No automatic resubmission.</p></section><section className="route-intelligence"><div className="command-section-title"><span>ROUTE INTELLIGENCE</span><small data-testid="quote-expiry">{order ? `${remaining}s · ${expired ? 'EXPIRED' : 'QUOTE VALIDITY'}` : 'AWAITING PROVIDER QUOTE'}</small></div>{!quote && <div className="truth-empty"><ActivityIcon /><span>Real route competition.<br />No invented quotes or fee estimates.</span></div>}{quote && <><div className="route-metrics"><div><small>ROUTER</small><b data-testid="quote-router">{quote.router || 'Jupiter'}</b></div><div><small>PRICE IMPACT</small><b data-testid="quote-price-impact">{quote.priceImpactPct != null ? `${quote.priceImpactPct}%` : quote.priceImpact != null ? `${quote.priceImpact}%` : 'Unavailable'}</b></div><div><small>MINIMUM OUTPUT</small><b data-testid="quote-minimum-output">{units(quote.otherAmountThreshold, order.output_metadata?.decimals)}</b></div></div><div className="route-steps">{quote.routePlan?.map((route, i) => <div key={i} data-testid={`quote-route-${i}`}><span>{i + 1}</span><b>{route.swapInfo?.label || route.label || 'Provider route'}</b><small>{route.percent != null ? `${route.percent}%` : route.bps != null ? `${route.bps / 100}%` : 'Provider allocation'}</small></div>)}</div><div className="quoted-fees">{[['Signature fee', quote.signatureFeeLamports], ['Priority fee', quote.prioritizationFeeLamports], ['Rent', quote.rentFeeLamports]].map(([label, value]) => <span key={label}>{label}<b>{value != null ? `${Number(value) / 1e9} SOL` : 'Unavailable'}</b></span>)}</div></>}<FeeBackPreview quote={quote} feeCat={feeCat} /></section><Dialog open={review} onOpenChange={setReview}><DialogContent className="feeless-dialog" data-testid="swap-review-dialog"><DialogTitle>Review your swap</DialogTitle><DialogDescription>Solana mainnet. Simulation passed; execution still requires your explicit wallet approval.</DialogDescription><dl className="review-facts"><div><dt>Pay</dt><dd>{amount} {inputAsset.symbol}</dd></div><div><dt>Expected output</dt><dd>{quote && units(quote.outAmount, order.output_metadata?.decimals)} {outputAsset.symbol}</dd></div><div><dt>Minimum output</dt><dd>{quote && units(quote.otherAmountThreshold, order.output_metadata?.decimals)}</dd></div><div><dt>Slippage</dt><dd>{Number(slippage) / 100}%</dd></div><div><dt>Expiry</dt><dd>{remaining}s</dd></div></dl><p className="market-error">This is a real transaction. Network/DEX fees apply. Fee-Back is not activated.</p><button className="btn-primary" data-testid="swap-approve-wallet" disabled={busy || expired} onClick={sign}>Approve in Phantom<ArrowUpRight size={16} /></button></DialogContent></Dialog></div>;
};
const ActivityIcon = () => <span className="route-pulse"><i /><i /><i /></span>;