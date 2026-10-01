import { PanelBoundary } from '../PanelBoundary';
import { TradeTimeline } from '../TradeTimeline';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { impactPercent, impactBlocks } from '../../lib/impactGuard';
import { ImpactNote } from '../command/ImpactNote';
import { toast } from 'sonner';
import { Zap, Wallet, ArrowUpRight, Settings2 } from 'lucide-react';
import { keepReceipt } from '../../lib/receipts';
import { ShareGifButton } from '../ShareGif';
import { useWallet } from '../../hooks/useWallet';
import { useMarket } from '../../hooks/useMarket';
import { apiUrl, cleanAmount, errorText } from '../../lib/api';
import { EvmTrade, EVM_TRADE_CHAINS } from './EvmTrade';
import { formatUSD } from '../../lib/dexscreener';
import { SlippagePicker } from '../command/SlippagePicker';
import { ShieldNote } from '../command/ShieldNote';
import { useShield, usePoints } from '../../lib/tradeIntel';

const SOL = 'So11111111111111111111111111111111111111112';
const PRESETS = { SOL: ['0.1', '0.5', '1'], USD: ['10', '50', '100'] };
const QUOTE_REFRESH_MS = 10000;
const WALLET_TIMEOUT_MS = 60000;
const PREFS_KEY = 'feeless-quicktrade';
const DEFAULT_PREFS = { unit: 'SOL', slippage: '100', presetsSOL: PRESETS.SOL, presetsUSD: PRESETS.USD };
const readPrefs = () => { try { return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') }; } catch { return { ...DEFAULT_PREFS }; } };
const presetsFor = (prefs, unit) => (unit === 'USD' ? prefs.presetsUSD : prefs.presetsSOL) || PRESETS[unit];

async function tradeApi(path, body) {
  const res = await fetch(apiUrl(`/api/trading${path}`), body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errorText(data, res.status));
  return data;
}

const units = (raw, decimals) => (raw == null || decimals == null ? null : Number(raw) / 10 ** decimals);
// Exact atoms -> decimal string, so a sell of 25% of a 6-decimals coin never carries a 7th decimal (the API rejects those).
const rawToUi = (raw, dec) => { const s = raw.toString().padStart(dec + 1, '0'); const w = s.slice(0, s.length - dec); const f = s.slice(s.length - dec).replace(/0+$/, ''); return f ? `${w}.${f}` : w; };

// Compact buy/sell box that lives next to every chart. Real Jupiter routes, simulated before
// signing, your wallet signs — nothing custodial. Anything into $FEE carries no FEELESS fee.
function QuickTradeInner({ pair }) {
  const { wallet, provider, connect, switchTo } = useWallet() || {};
  const assets = useMarket('/assets', 300000);
  const feeMint = (assets.data?.assets || []).find(a => a.id === 'fee')?.mint;
  const [side, setSide] = useState('buy');
  const [prefs, setPrefs] = useState(readPrefs);
  const [amount, setAmount] = useState(() => presetsFor(readPrefs(), readPrefs().unit)[0]);
  const [showSettings, setShowSettings] = useState(false);
  const box = useRef(null);
  // Opened from a "snipers out" alert (?buy=1): bring the buy box into view, ready to quote.
  // The quote at your default amount is already live (see below) — you still approve in your wallet.
  useEffect(() => { if (new URLSearchParams(window.location.search).get('buy') === '1') box.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }); }, []);
  // Auto-match the wallet to the coin's network: same wallet, Solana side, no popup if already trusted.
  useEffect(() => {
    if (pair?.chainId === 'solana' && wallet?.chain === 'evm' && connect) connect('solana', undefined, { silent: true }).catch(() => {});
  }, [pair?.chainId, wallet?.chain]); // eslint-disable-line react-hooks/exhaustive-deps
  const [sellPct, setSellPct] = useState(50);
  // One-tap exit from the chart's P&L badge: switch to Sell at the requested % (you still review + sign).
  useEffect(() => {
    // Only the box trading that coin answers (war room + trenches can both be mounted).
    const onExit = e => { if (e.detail?.mint && e.detail.mint !== pair?.baseToken?.address) return; setSide('sell'); setSellPct(e.detail?.pct || 100); box.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }); };
    window.addEventListener('feeless:quick-exit', onExit);
    return () => window.removeEventListener('feeless:quick-exit', onExit);
  }, [pair?.baseToken?.address]);
  const [counter, setCounter] = useState('SOL');
  const [solUsd, setSolUsd] = useState(null);
  const [bal, setBal] = useState(null); const [balErr, setBalErr] = useState(false);
  const balance = bal?.amount ?? null;
  const [order, setOrder] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null); const [tl, setTl] = useState(null);
  const mint = pair?.baseToken?.address;
  const symbol = pair?.baseToken?.symbol || 'token';
  const tokenUsd = Number(pair?.priceUsd) || null;
  const sellAmount = balance == null ? null : balance * sellPct / 100;
  useEffect(() => { try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch {} }, [prefs]);
  useEffect(() => {
    let alive = true;
    fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL}`).then(r => r.json()).then(d => alive && setSolUsd(Number(d?.[SOL]?.usdPrice) || null)).catch(() => {});
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    setOrder(null); setResult(null); setShareCard(null);
    setBal(null); setBalErr(false); setTl(null);
  }, [side, wallet?.address, mint]);
  // Sell side: the real on-chain balance, refreshed every 8s and right after any of your trades confirms.
  // A failed read keeps the last good number (never a fake "0") and says so.
  const loadBal = useCallback(() => {
    if (side !== 'sell' || !wallet?.address || !mint) return;
    fetch(apiUrl(`/api/reputation/balance/${wallet.address}/${mint}`)).then(r => (r.ok ? r.json() : Promise.reject(new Error('busy'))))
      .then(d => { setBal({ amount: Number(d.amount) || 0, decimals: d.decimals, raw: d.raw }); setBalErr(false); }).catch(() => setBalErr(true));
  }, [side, wallet?.address, mint]);
  useEffect(() => {
    loadBal(); const t = setInterval(loadBal, 8000);
    const onTrade = () => { setTimeout(loadBal, 1500); setTimeout(loadBal, 6000); };
    window.addEventListener('feeless:trade-confirmed', onTrade);
    return () => { clearInterval(t); window.removeEventListener('feeless:trade-confirmed', onTrade); };
  }, [loadBal]);
  const counterMint = counter === 'FEE' && feeMint ? feeMint : SOL;
  // Rug shield on buys: a 'danger' coin needs an explicit tick before the one-tap buy signs.
  const shield = useShield(side === 'buy' ? mint : null);
  const [shieldAck, setShieldAck] = useState(false);
  useEffect(() => { setShieldAck(false); }, [mint, side]);
  const shieldBlocks = side === 'buy' && shield?.level === 'danger' && !shieldAck;
  const [impactAck, setImpactAck] = useState(false);
  const [shareCard, setShareCard] = useState(null);
  useEffect(() => { setImpactAck(false); }, [mint, side, amount, sellPct]);
  const points = usePoints(wallet?.chain === 'solana' ? wallet.address : null, result?.signature);
  const payAmount = () => {
    if (side === 'sell') {
      if (!balance) return null;
      if (bal?.raw != null && bal.decimals != null) { const r = (BigInt(bal.raw) * BigInt(sellPct)) / 100n; return r > 0n ? rawToUi(r, bal.decimals) : null; }
      return Number((balance * sellPct) / 100).toFixed(bal?.decimals ?? 6).replace(/\.?0+$/, '');
    }
    const n = Number(amount);
    if (!(n > 0)) return null;
    if (counter === 'SOL') { const sol = prefs.unit === 'USD' ? (solUsd ? n / solUsd : null) : n; return sol ? sol.toFixed(9).replace(/\.?0+$/, '') : null; }
    return null; // paying with $FEE uses its own balance flow via the full Trade page
  };
  // Instant trading: the route is quoted + simulated in the background as soon as the amount is set and kept
  // fresh every 10s, so one tap goes straight to the wallet. Newest request wins; stale answers are dropped.
  const solanaReady = pair?.chainId === 'solana' && wallet?.chain === 'solana' && Boolean(wallet?.address) && Boolean(mint);
  const request = solanaReady ? (() => { const amt = payAmount(); return amt && { input_mint: side === 'buy' ? counterMint : mint, output_mint: side === 'buy' ? mint : counterMint, amount: amt, slippage_bps: Number(prefs.slippage), wallet: wallet.address }; })() : null;
  const requestKey = request ? JSON.stringify(request) : '';
  const quoteSeq = useRef(0);
  const [routing, setRouting] = useState(false);
  const [quoteError, setQuoteError] = useState('');
  const fetchOrder = async () => {
    if (!request || busy) return;
    const seq = ++quoteSeq.current;
    setRouting(true);
    try {
      const data = await tradeApi('/quote', request);
      await tradeApi('/simulate', { order_id: data.order_id });
      if (seq === quoteSeq.current) { setOrder({ ...data, key: requestKey, at: Date.now() }); setQuoteError(''); }
    } catch (e) { if (seq === quoteSeq.current) { setOrder(null); setQuoteError(e.message); } } finally { if (seq === quoteSeq.current) setRouting(false); }
  };
  useEffect(() => {
    quoteSeq.current++; setOrder(null); setQuoteError(''); setRouting(false);
    if (!requestKey) return undefined;
    const first = setTimeout(fetchOrder, 250);
    const refresh = setInterval(() => { if (!document.hidden) fetchOrder(); }, QUOTE_REFRESH_MS);
    return () => { clearTimeout(first); clearInterval(refresh); };
  }, [requestKey]); // eslint-disable-line react-hooks/exhaustive-deps
  if (pair?.chainId !== 'solana') return EVM_TRADE_CHAINS.includes(pair?.chainId) ? <EvmTrade pair={pair} /> : <aside className="quick-trade qt-unsupported" data-testid="quick-trade"><Zap size={14} /> In-app swaps cover Solana and EVM chains. Use the DEX link for {pair?.chainId || 'this chain'}.</aside>;

  // Button when no live quote yet: connect / switch the wallet, or explain what's missing.
  const quote = async () => {
    if (!wallet?.address) { try { await connect?.('solana'); } catch { toast.error('Connect a Solana wallet to trade.'); } return; }
    if (wallet.chain !== 'solana') { try { await (switchTo ? switchTo('solana') : connect?.('solana')); } catch { toast.error('Open your wallet and enable its Solana account to trade this pair.'); } return; }
    if (!request) { toast.error(side === 'sell' ? 'No balance to sell.' : 'Enter an amount.'); return; }
    fetchOrder();
  };
  const approve = async () => {
    if (!order || order.key !== requestKey || shieldBlocks || impactBlocks(impactPercent(order.quote), impactAck)) return;
    quoteSeq.current++; setBusy(true);
    const q0 = order.quote || {}; const feeBps = order.feeless_fee?.bps || 0; const tUsd = Number(q0.inUsdValue) || 0;
    const step = patch => setTl(t => ({ ...t, ...patch }));
    setTl({ side, symbol, quotedAt: order.at, route: `${q0.router || 'Jupiter'} · simulated OK`, wallet: wallet.name, feePct: feeBps / 100, feeUsd: tUsd * feeBps / 10000,
      networkSol: ['signatureFeeLamports', 'prioritizationFeeLamports'].reduce((a, k) => a + Number(q0[k] || 0), 0) / 1e9 || null, solUsd });
    try {
      if (!provider?.signTransaction || provider.publicKey?.toString() !== wallet.address) throw new Error('Reconnect Phantom and get a fresh quote.');
      const { VersionedTransaction } = await import('@solana/web3.js');
      const tx = VersionedTransaction.deserialize(Uint8Array.from(atob(order.quote.transaction), c => c.charCodeAt(0)));
      const signed = await Promise.race([provider.signTransaction(tx), new Promise((_, rej) => setTimeout(() => rej(new Error('Wallet did not respond. Open your wallet (check for a blocked popup) and tap again.')), WALLET_TIMEOUT_MS))]);
      step({ signedAt: Date.now(), signer: wallet.address });
      const tradeUsd = Number(order.quote?.inUsdValue) || 0;
      const outDec = order.output_metadata?.decimals;
      const got = units(order.quote?.outAmount, outDec);
      const feePct = order.feeless_fee?.bps ? order.feeless_fee.bps / 100 : 0;
      let res = await tradeApi('/execute', { order_id: order.order_id, signed_transaction: btoa(String.fromCharCode(...signed.serialize())) });
      setResult(res); setOrder(null); step({ sentAt: Date.now(), signature: res.signature, state: res.state, doneAt: ['confirmed', 'failed'].includes(res.state) ? Date.now() : undefined });
      // Still landing? Keep asking (never resending) until the chain answers: that check is also what records the fee,
      // season points and the confirmation notification on the server.
      for (let i = 0; i < 30 && res.signature && !['confirmed', 'failed'].includes(res.state); i++) {
        if (i === 0) toast.message?.('Submitted — confirming on Solana…');
        await new Promise(r => setTimeout(r, 2000));
        try { res = await tradeApi(`/order/${order.order_id}`); setResult(res); if (['confirmed', 'failed'].includes(res.state)) step({ state: res.state, doneAt: Date.now() }); } catch { /* keep polling */ }
      }
      if (res.state === 'confirmed') {
        window.dispatchEvent(new CustomEvent('feeless:trade-confirmed', { detail: { mint, side, signature: res.signature, usd: tradeUsd, wallet: wallet.address, tokens: Number(side === 'buy' ? got : order.amount) || 0 } }));
        keepReceipt(res.signature, wallet.address, side);
        // Shareable receipt (GIF): what you sold / bought, what you got, the fee, the tx.
        const sold = side === 'sell';
        setShareCard({ kicker: sold ? 'SOLD ON FEELESS' : 'BOUGHT ON FEELESS', title: `$${symbol}`, imageUrl: apiUrl(`/api/reputation/token-logo/${mint}`), tone: sold ? 'down' : 'up',
          big: got != null ? `${sold ? '+' : ''}${Number(got).toLocaleString(undefined, { maximumFractionDigits: sold ? 4 : 0 })} ${sold ? (toFee ? '$FEE' : 'SOL') : symbol}` : sold ? 'SOLD' : 'BOUGHT',
          lines: [tradeUsd ? `Trade value ${formatUSD(tradeUsd)}` : null, feePct ? `FEELESS fee ${feePct.toFixed(2)}%` : 'Fee-free buy', `tx ${res.signature.slice(0, 6)}…${res.signature.slice(-4)}`, 'Signed in my own wallet · feeless'].filter(Boolean) });
      }
      toast[res.state === 'failed' ? 'error' : 'success'](res.state === 'confirmed' ? `${side === 'buy' ? 'Buy' : 'Sell'} confirmed on-chain.` : res.state === 'failed' ? 'Swap failed. Nothing moved.' : 'Still confirming — check the transaction link before trading again.');
    } catch (e) { toast.error(e.code === 4001 ? 'Approval declined — nothing was sent.' : e.message); setOrder(null); setTl(t => (t?.sentAt ? t : null)); } finally { setBusy(false); fetchOrder(); }
  };
  const outDecimals = order?.output_metadata?.decimals;
  const out = order ? units(order.quote?.outAmount, outDecimals) : null;
  const minOut = order ? units(order.quote?.otherAmountThreshold, outDecimals) : null;
  const impact = order ? impactPercent(order.quote) : null;
  const impactStop = order ? impactBlocks(impact, impactAck) : false;
  const toFee = counter === 'FEE';
  return <aside ref={box} className="quick-trade" data-testid="quick-trade">
    <div className="qt-head"><Zap size={13} /><b>Quick trade</b><button type="button" className={`qt-gear ${showSettings ? 'active' : ''}`} onClick={() => setShowSettings(v => !v)} title="Quick trade settings" aria-label="Quick trade settings"><Settings2 size={13} /></button><button type="button" className="qt-slip-chip" onClick={() => setShowSettings(true)} title="Max slippage (change in settings)">Slip {Number(prefs.slippage) / 100}%</button><div className="qt-side">{['buy', 'sell'].map(s => <button type="button" key={s} className={`${s} ${side === s ? 'active' : ''}`} onClick={() => setSide(s)}>{s === 'buy' ? 'Buy' : 'Sell'}</button>)}</div></div>
    {showSettings && <div className="qt-settings" data-testid="quick-trade-settings">
      <small>Max slippage</small>
      <SlippagePicker value={prefs.slippage} onChange={v => setPrefs(p => ({ ...p, slippage: v }))} disabled={busy} />
      <small>Your buy presets</small>
      {['SOL', 'USD'].map(u => <div key={u} className="qt-settings-row"><span>{u}</span>{presetsFor(prefs, u).map((v, i) => <input key={i} type="number" min="0" step="any" value={v} onChange={e => { const next = [...presetsFor(prefs, u)]; next[i] = e.target.value; setPrefs(p => ({ ...p, [u === 'USD' ? 'presetsUSD' : 'presetsSOL']: next })); }} aria-label={`${u} preset ${i + 1}`} />)}</div>)}
      <div className="qt-settings-row"><button type="button" onClick={() => { setPrefs({ ...DEFAULT_PREFS }); setAmount(PRESETS.SOL[0]); }}>Reset</button><button type="button" className="qt-settings-done" onClick={() => setShowSettings(false)}>Done</button></div>
    </div>}
    {side === 'buy' ? <>
      <div className="qt-row"><span>Amount in</span><div className="qt-seg">{['SOL', 'USD'].map(u => <button type="button" key={u} className={prefs.unit === u ? 'active' : ''} onClick={() => { setPrefs(p => ({ ...p, unit: u })); setAmount(presetsFor(prefs, u)[0]); }}>{u}</button>)}</div></div>
      <div className="qt-presets">{presetsFor(prefs, prefs.unit).map(v => <button type="button" key={v} className={amount === v ? 'active' : ''} onClick={() => setAmount(v)}>{prefs.unit === 'USD' ? `$${v}` : `${v} SOL`}</button>)}<input type="text" inputMode="decimal" value={amount} onChange={e => setAmount(cleanAmount(e.target.value))} aria-label="Custom amount" /></div>
      <small className="qt-note">{prefs.unit === 'USD'
        ? `≈ ${solUsd && Number(amount) > 0 ? `${(Number(amount) / solUsd).toFixed(4)} SOL` : '…'} at $${solUsd ? solUsd.toFixed(2) : '…'}/SOL`
        : `≈ ${solUsd && Number(amount) > 0 ? formatUSD(Number(amount) * solUsd) : '…'}`}</small>
    </> : <>
      <div className="qt-row"><span>Selling</span><b>{sellAmount == null ? '—' : `${sellAmount.toLocaleString(undefined, { maximumFractionDigits: 5 })} ${symbol}`}</b></div>
      <div className="qt-presets">{[25, 50, 100].map(p => <button type="button" key={p} className={sellPct === p ? 'active' : ''} onClick={() => setSellPct(p)}>{p}%</button>)}</div>
      <small className="qt-note">{!wallet?.address ? 'Connect to load your balance.' : balance == null ? (balErr ? <>Balance read failed · <button type="button" className="qt-retry" onClick={loadBal}>retry</button></> : 'Loading balance…') : balance === 0 ? `You hold no ${symbol} in this wallet${balErr ? ' (last read)' : ''}.` : <>You hold {balance.toLocaleString(undefined, { maximumFractionDigits: 4 })} {symbol}{tokenUsd ? ` · ≈ ${formatUSD(balance * tokenUsd)} total / ${formatUSD((sellAmount || 0) * tokenUsd)} selected` : ''}</>}</small>
      <div className="qt-row"><span>Receive</span><div className="qt-seg">{[['SOL', 'SOL'], ['FEE', '$FEE']].map(([id, l]) => <button type="button" key={id} disabled={id === 'FEE' && !feeMint} className={counter === id ? 'active' : ''} onClick={() => setCounter(id)}>{l}</button>)}</div></div>
      {toFee && <small className="qt-fee-free">Buying $FEE · 0% FEELESS fee</small>}
    </>}
    {order && <div className="qt-quote"><div className="qt-fee" data-testid="qt-fee"><small>FEELESS fee</small><b>{order.feeless_fee?.bps ? `${(order.feeless_fee.bps / 100).toFixed(2)}%` : 'Free'}</b>{order.feeless_fee?.notes?.length ? <em>{order.feeless_fee.notes.join(' · ')}</em> : null}</div><div><small>You get ≈</small><b>{out != null ? `${out.toLocaleString(undefined, { maximumFractionDigits: 6 })} ${side === 'buy' ? symbol : toFee ? '$FEE' : 'SOL'}` : '—'}</b></div><div><small>Min received</small><b>{minOut != null ? minOut.toLocaleString(undefined, { maximumFractionDigits: 6 }) : '—'}</b></div><div><small>Price impact</small><b className={impact > 5 ? 'negative' : ''}>{impact != null ? `${impact.toFixed(2)}%` : '—'}</b></div></div>}
    {order && <ImpactNote pct={impact} ack={impactAck} onAck={setImpactAck} />}
    {side === 'buy' && shield && shield.level !== 'ok' && <ShieldNote shield={shield} ack={shieldAck} onAck={setShieldAck} />}
    {quoteError && !order && <small className="qt-note qt-error" role="status">{quoteError}</small>}
    {order && order.key === requestKey
      ? <button type="button" className={`qt-go ${side}${side === 'buy' ? ' m-go' : ''}`} disabled={busy || shieldBlocks || impactStop} onClick={approve} data-testid="quick-trade-approve">{busy ? 'Waiting for wallet…' : `${side === 'buy' ? 'Buy' : 'Sell'} ${symbol} in ${wallet?.name || 'Phantom'}`}</button>
      : <button type="button" className={`qt-go ${side}`} disabled={busy || routing} onClick={quote} data-testid="quick-trade-quote">{!wallet?.address ? <><Wallet size={14} />Connect wallet</> : wallet.chain !== 'solana' ? 'Switch wallet to Solana' : routing ? 'Routing…' : quoteError ? 'Retry quote' : `Get ${side === 'buy' ? 'buy' : 'sell'} quote`}</button>}
    <TradeTimeline t={tl} />
    {shareCard && result?.state === 'confirmed' && <ShareGifButton label="🎞 Share receipt GIF" card={shareCard} className="m-btn qt-share" />}
    {result?.signature && <a className="qt-result" href={`https://solscan.io/tx/${result.signature}`} target="_blank" rel="noopener noreferrer">{result.state.toUpperCase()} · view transaction <ArrowUpRight size={11} /></a>}
    <small className="qt-foot">{side === 'buy' && shield?.level === 'ok' ? '🛡 Rug shield clear · ' : ''}{points?.points > 0 ? `⚡ ${points.points.toLocaleString('en-US')} FEE pts · ` : ''}Jupiter route · simulated before you sign · non-custodial{side === 'buy' && prefs.unit === 'USD' ? ` · ${formatUSD(Number(amount))}` : ''}</small>
  </aside>;
}

// Safety net: a broken quick trade never takes the page down (see PanelBoundary).
export function QuickTrade(props) {
  return <PanelBoundary name="Quick trade" resetKey={JSON.stringify(props.pair?.pairAddress || props.room || props.mint || '')}><QuickTradeInner {...props} /></PanelBoundary>;
}
