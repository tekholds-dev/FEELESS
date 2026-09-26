import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Zap, Wallet, ArrowUpRight, Settings2 } from 'lucide-react';
import { keepReceipt } from '../../lib/receipts';
import { useWallet } from '../../hooks/useWallet';
import { useMarket } from '../../hooks/useMarket';
import { apiUrl } from '../../lib/api';
import { formatUSD } from '../../lib/dexscreener';

const SOL = 'So11111111111111111111111111111111111111112';
const PRESETS = { SOL: ['0.1', '0.5', '1'], USD: ['10', '50', '100'] };
const SLIPPAGE = [['50', '0.5%'], ['100', '1%'], ['300', '3%']];
const PREFS_KEY = 'feeless-quicktrade';
const DEFAULT_PREFS = { unit: 'SOL', slippage: '100', presetsSOL: PRESETS.SOL, presetsUSD: PRESETS.USD };
const readPrefs = () => { try { return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') }; } catch { return { ...DEFAULT_PREFS }; } };
const presetsFor = (prefs, unit) => (unit === 'USD' ? prefs.presetsUSD : prefs.presetsSOL) || PRESETS[unit];

async function tradeApi(path, body) {
  const res = await fetch(apiUrl(`/api/trading${path}`), body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Trade request failed.');
  return data;
}

const units = (raw, decimals) => (raw == null || decimals == null ? null : Number(raw) / 10 ** decimals);

// Compact buy/sell box that lives next to every chart. Real Jupiter routes, simulated before
// signing, your wallet signs — nothing custodial. Anything into $FEE carries no FEELESS fee.
export function QuickTrade({ pair }) {
  const { wallet, provider, connect, switchTo } = useWallet() || {};
  const assets = useMarket('/assets', 300000);
  const feeMint = (assets.data?.assets || []).find(a => a.id === 'fee')?.mint;
  const [side, setSide] = useState('buy');
  const [prefs, setPrefs] = useState(readPrefs);
  const [amount, setAmount] = useState(() => presetsFor(readPrefs(), readPrefs().unit)[0]);
  const [showSettings, setShowSettings] = useState(false);
  const [sellPct, setSellPct] = useState(50);
  const [counter, setCounter] = useState('SOL');
  const [solUsd, setSolUsd] = useState(null);
  const [balance, setBalance] = useState(null);
  const [order, setOrder] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const mint = pair?.baseToken?.address;
  const symbol = pair?.baseToken?.symbol || 'token';
  useEffect(() => { try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch {} }, [prefs]);
  useEffect(() => {
    let alive = true;
    fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL}`).then(r => r.json()).then(d => alive && setSolUsd(Number(d?.[SOL]?.usdPrice) || null)).catch(() => {});
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    setOrder(null); setResult(null);
    if (side !== 'sell' || !wallet?.address || !mint) { setBalance(null); return; }
    fetch(apiUrl(`/api/reputation/balance/${wallet.address}/${mint}`)).then(r => r.json()).then(d => setBalance(Number(d.amount) || 0)).catch(() => setBalance(null));
  }, [side, wallet?.address, mint]);
  useEffect(() => { setOrder(null); }, [amount, sellPct, counter, prefs.slippage, prefs.unit]);
  if (pair?.chainId !== 'solana') return <aside className="quick-trade qt-unsupported" data-testid="quick-trade"><Zap size={14} /> Quick trade supports Solana pairs. Use the DEX link for {pair?.chainId || 'this chain'}.</aside>;

  const counterMint = counter === 'FEE' && feeMint ? feeMint : SOL;
  const payAmount = () => {
    if (side === 'sell') return balance ? String((balance * sellPct) / 100) : null;
    const n = Number(amount);
    if (!(n > 0)) return null;
    if (counter === 'SOL') return prefs.unit === 'USD' ? (solUsd ? String(n / solUsd) : null) : String(n);
    return null; // paying with $FEE uses its own balance flow via the full Trade page
  };
  const quote = async () => {
    if (!wallet?.address) { try { await connect?.('solana'); } catch { toast.error('Connect a Solana wallet to trade.'); } return; }
    if (wallet.chain !== 'solana') { try { await (switchTo ? switchTo('solana') : connect?.('solana')); toast.success(`Switched ${wallet.name || 'wallet'} to Solana — tap again to quote.`); } catch { toast.error('Open your wallet and enable its Solana account to trade this pair.'); } return; }
    const amt = payAmount();
    if (!amt) { toast.error(side === 'sell' ? 'No balance to sell.' : 'Enter an amount.'); return; }
    setBusy(true); setResult(null);
    try {
      const data = await tradeApi('/quote', { input_mint: side === 'buy' ? counterMint : mint, output_mint: side === 'buy' ? mint : counterMint, amount: Number(amt).toFixed(9).replace(/\.?0+$/, ''), slippage_bps: Number(prefs.slippage), wallet: wallet.address });
      await tradeApi('/simulate', { order_id: data.order_id });
      setOrder(data);
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const approve = async () => {
    if (!order) return;
    setBusy(true);
    try {
      if (!provider?.signTransaction || provider.publicKey?.toString() !== wallet.address) throw new Error('Reconnect Phantom and get a fresh quote.');
      const { VersionedTransaction } = await import('@solana/web3.js');
      const tx = VersionedTransaction.deserialize(Uint8Array.from(atob(order.quote.transaction), c => c.charCodeAt(0)));
      const signed = await provider.signTransaction(tx);
      const res = await tradeApi('/execute', { order_id: order.order_id, signed_transaction: btoa(String.fromCharCode(...signed.serialize())) });
      setResult(res); setOrder(null);
      if (res.signature && res.state !== 'failed') keepReceipt(res.signature, wallet.address, side);
      toast[res.state === 'failed' ? 'error' : 'success'](res.state === 'confirmed' ? 'Swap confirmed on-chain.' : res.state === 'failed' ? 'Swap failed.' : 'Submitted — confirming.');
    } catch (e) { toast.error(e.code === 4001 ? 'Approval declined — nothing was sent.' : e.message); } finally { setBusy(false); }
  };
  const outDecimals = order?.output_metadata?.decimals;
  const out = order ? units(order.quote?.outAmount, outDecimals) : null;
  const minOut = order ? units(order.quote?.otherAmountThreshold, outDecimals) : null;
  const impact = order ? Number(order.quote?.priceImpactPct ?? order.quote?.priceImpact) : null;
  const toFee = counter === 'FEE';
  return <aside className="quick-trade" data-testid="quick-trade">
    <div className="qt-head"><Zap size={13} /><b>Quick trade</b><button type="button" className={`qt-gear ${showSettings ? 'active' : ''}`} onClick={() => setShowSettings(v => !v)} title="Quick trade settings" aria-label="Quick trade settings"><Settings2 size={13} /></button><div className="qt-side">{['buy', 'sell'].map(s => <button type="button" key={s} className={`${s} ${side === s ? 'active' : ''}`} onClick={() => setSide(s)}>{s === 'buy' ? 'Buy' : 'Sell'}</button>)}</div></div>
    {showSettings && <div className="qt-settings" data-testid="quick-trade-settings">
      <small>Your buy presets</small>
      {['SOL', 'USD'].map(u => <div key={u} className="qt-settings-row"><span>{u}</span>{presetsFor(prefs, u).map((v, i) => <input key={i} type="number" min="0" step="any" value={v} onChange={e => { const next = [...presetsFor(prefs, u)]; next[i] = e.target.value; setPrefs(p => ({ ...p, [u === 'USD' ? 'presetsUSD' : 'presetsSOL']: next })); }} aria-label={`${u} preset ${i + 1}`} />)}</div>)}
      <div className="qt-settings-row"><button type="button" onClick={() => { setPrefs({ ...DEFAULT_PREFS }); setAmount(PRESETS.SOL[0]); }}>Reset</button><button type="button" className="qt-settings-done" onClick={() => setShowSettings(false)}>Done</button></div>
    </div>}
    {side === 'buy' ? <>
      <div className="qt-row"><span>Amount in</span><div className="qt-seg">{['SOL', 'USD'].map(u => <button type="button" key={u} className={prefs.unit === u ? 'active' : ''} onClick={() => { setPrefs(p => ({ ...p, unit: u })); setAmount(presetsFor(prefs, u)[0]); }}>{u}</button>)}</div></div>
      <div className="qt-presets">{presetsFor(prefs, prefs.unit).map(v => <button type="button" key={v} className={amount === v ? 'active' : ''} onClick={() => setAmount(v)}>{prefs.unit === 'USD' ? `$${v}` : `${v} SOL`}</button>)}<input type="number" min="0" step="any" value={amount} onChange={e => setAmount(e.target.value)} aria-label="Custom amount" /></div>
      {prefs.unit === 'USD' && <small className="qt-note">≈ {solUsd && Number(amount) > 0 ? `${(Number(amount) / solUsd).toFixed(4)} SOL` : '…'} at ${solUsd ? solUsd.toFixed(2) : '…'}/SOL</small>}
    </> : <>
      <div className="qt-presets">{[25, 50, 100].map(p => <button type="button" key={p} className={sellPct === p ? 'active' : ''} onClick={() => setSellPct(p)}>{p}%</button>)}</div>
      <small className="qt-note">{!wallet?.address ? 'Connect to load your balance.' : balance == null ? 'Loading balance…' : `You hold ${balance.toLocaleString(undefined, { maximumFractionDigits: 4 })} ${symbol}`}</small>
      <div className="qt-row"><span>Receive</span><div className="qt-seg">{[['SOL', 'SOL'], ['FEE', '$FEE']].map(([id, l]) => <button type="button" key={id} disabled={id === 'FEE' && !feeMint} className={counter === id ? 'active' : ''} onClick={() => setCounter(id)}>{l}</button>)}</div></div>
      {toFee && <small className="qt-fee-free">Selling into $FEE · 0% FEELESS fee</small>}
    </>}
    <div className="qt-row"><span>Slippage</span><div className="qt-seg">{SLIPPAGE.map(([v, l]) => <button type="button" key={v} className={prefs.slippage === v ? 'active' : ''} onClick={() => setPrefs(p => ({ ...p, slippage: v }))}>{l}</button>)}</div></div>
    {order && <div className="qt-quote"><div className="qt-fee" data-testid="qt-fee"><small>FEELESS fee</small><b>{order.feeless_fee?.bps ? `${(order.feeless_fee.bps / 100).toFixed(2)}%` : 'Free'}</b>{order.feeless_fee?.notes?.length ? <em>{order.feeless_fee.notes.join(' · ')}</em> : null}</div><div><small>You get ≈</small><b>{out != null ? `${out.toLocaleString(undefined, { maximumFractionDigits: 6 })} ${side === 'buy' ? symbol : toFee ? '$FEE' : 'SOL'}` : '—'}</b></div><div><small>Min received</small><b>{minOut != null ? minOut.toLocaleString(undefined, { maximumFractionDigits: 6 }) : '—'}</b></div><div><small>Price impact</small><b className={impact > 5 ? 'negative' : ''}>{Number.isFinite(impact) ? `${impact.toFixed(2)}%` : '—'}</b></div></div>}
    {!order ? <button type="button" className={`qt-go ${side}`} disabled={busy} onClick={quote} data-testid="quick-trade-quote">{!wallet?.address ? <><Wallet size={14} />Connect wallet</> : busy ? 'Routing…' : `Get ${side === 'buy' ? 'buy' : 'sell'} quote`}</button>
      : <button type="button" className={`qt-go ${side}`} disabled={busy} onClick={approve}>{busy ? 'Waiting for wallet…' : `Approve ${side} in Phantom`}</button>}
    {result?.signature && <a className="qt-result" href={`https://solscan.io/tx/${result.signature}`} target="_blank" rel="noopener noreferrer">{result.state.toUpperCase()} · view transaction <ArrowUpRight size={11} /></a>}
    <small className="qt-foot">Jupiter route · simulated before you sign · non-custodial{side === 'buy' && prefs.unit === 'USD' ? ` · ${formatUSD(Number(amount))}` : ''}</small>
  </aside>;
}
