import React, { useEffect, useRef, useState } from 'react';
import NumInput from '../NumInput';
import { ArrowDownUp, ChevronDown, RefreshCw, Search, ShieldCheck, Wallet } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { useWallet, EVM_CHAINS } from '../../hooks/useWallet';
import { CHAIN_ID, NATIVE, toUnits, fromUnits, lifiServerQuote, executeLifi } from '../../lib/lifiExec';
import { moneyConfirmed } from '../../lib/moneyConfirm';

// Same-chain swaps on EVM networks (Base, Ethereum, BNB, Arbitrum, …) through LI.FI, in the same compact card
// as the Solana swap. Quotes come from the FEELESS server (key + fee server-side, route verified); execution
// re-checks the route in the browser, switches the wallet to the right network and approves exact amounts only.
export const SWAP_NETWORKS = [['solana', 'Solana'], ['base', 'Base'], ['ethereum', 'Ethereum'], ['bsc', 'BNB'], ['arbitrum', 'Arbitrum'], ['polygon', 'Polygon'], ['optimism', 'Optimism'], ['avalanche', 'Avalanche']];
const PREVIEW_ADDRESS = '0x0000000000000000000000000000000000000001';   // quote preview before a wallet connects

const nativeToken = chain => ({ address: NATIVE, symbol: EVM_CHAINS[chain]?.nativeCurrency?.symbol || 'ETH', name: EVM_CHAINS[chain]?.nativeCurrency?.name || 'Native', decimals: 18 });

async function rpc(chain, method, params) {
  const url = EVM_CHAINS[chain]?.rpcUrls?.[0];
  if (!url) return null;
  try {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) });
    return (await r.json()).result;
  } catch { return null; }
}
async function balanceOf(chain, token, owner) {
  const raw = token.address === NATIVE
    ? await rpc(chain, 'eth_getBalance', [owner, 'latest'])
    : await rpc(chain, 'eth_call', [{ to: token.address, data: `0x70a08231${owner.slice(2).toLowerCase().padStart(64, '0')}` }, 'latest']);
  return raw && raw !== '0x' ? fromUnits(BigInt(raw), token.decimals) : null;
}

function EvmTokenPicker({ chain, value, onChange, onNetwork, testId }) {
  const [open, setOpen] = useState(false); const [q, setQ] = useState(''); const [rows, setRows] = useState([]);
  const box = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const out = e => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    document.addEventListener('pointerdown', out); return () => document.removeEventListener('pointerdown', out);
  }, [open]);
  useEffect(() => {
    if (!open) return undefined;
    let alive = true;
    const t = setTimeout(() => fetch(apiUrl(`/api/lifi/tokens?chain=${CHAIN_ID[chain]}&q=${encodeURIComponent(q.trim())}`)).then(r => r.json()).then(d => alive && setRows(d.tokens || [])).catch(() => {}), 200);
    return () => { alive = false; clearTimeout(t); };
  }, [open, q, chain]);
  const pick = t => { onChange({ address: t.address, symbol: t.symbol, name: t.name, decimals: t.decimals, logoURI: t.logoURI }); setOpen(false); setQ(''); };
  const av = t => (t?.logoURI ? <img className="tkp-av" src={t.logoURI} alt="" /> : <span className="tkp-av">{t?.symbol?.slice(0, 1)}</span>);
  return <div className="tkp" ref={box}>
    <button type="button" className="tkp-btn" data-testid={testId} aria-expanded={open} onClick={() => setOpen(o => !o)}>{av(value)}<b>{value?.symbol}</b><ChevronDown size={14} /></button>
    {open && <div className="tkp-pop" role="listbox">
      <nav>{SWAP_NETWORKS.map(([id, name]) => <button key={id} type="button" className={chain === id ? 'on' : ''} onClick={() => { if (id !== chain) { onNetwork(id); setOpen(false); } }}>{name}</button>)}</nav>
      <div className="tkp-search"><Search size={13} /><input autoFocus aria-label="Search tokens" placeholder={`Search ${EVM_CHAINS[chain]?.chainName || chain} tokens or paste an address`} value={q} onChange={e => setQ(e.target.value)} /></div>
      <div className="tkp-list">
        {!q && <button type="button" role="option" aria-selected={value?.address === NATIVE} onClick={() => pick(nativeToken(chain))}>{av(nativeToken(chain))}<b>{nativeToken(chain).symbol}</b><em>{nativeToken(chain).name}</em><code>native</code></button>}
        {rows.filter(t => t.address !== NATIVE).map(t => <button key={t.address} type="button" role="option" aria-selected={value?.address === t.address} className={value?.address === t.address ? 'sel' : ''} onClick={() => pick(t)}>
          {av(t)}<b>{t.symbol}</b><em>{t.name}</em><code>{t.priceUSD ? `$${Number(t.priceUSD) < 0.01 ? Number(t.priceUSD).toPrecision(2) : Number(t.priceUSD).toFixed(2)}` : `${t.address.slice(0, 6)}…`}</code></button>)}
        {!rows.length && q && <p>No match on {EVM_CHAINS[chain]?.chainName}. Paste the token's contract address.</p>}
      </div>
    </div>}
  </div>;
}

export function EvmSwap({ chain, onNetwork }) {
  const { wallet, provider, switchTo, connect } = useWallet() || {};
  const evm = wallet?.chain === 'evm' ? wallet : null;
  const [from, setFrom] = useState(() => nativeToken(chain));
  const [to, setTo] = useState(null);
  const [amount, setAmount] = useState('0.01');
  const [slippage, setSlippage] = useState(0.005);
  const [quote, setQuote] = useState(null);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState('');
  const [err, setErr] = useState('');
  const [bal, setBal] = useState(null);
  // New network: native coin → USDC by default.
  useEffect(() => {
    setFrom(nativeToken(chain)); setTo(null); setQuote(null); setErr('');
    fetch(apiUrl(`/api/lifi/tokens?chain=${CHAIN_ID[chain]}&q=usdc`)).then(r => r.json()).then(d => { const u = (d.tokens || []).find(t => t.symbol === 'USDC') || d.tokens?.[0]; if (u) setTo(u); }).catch(() => {});
  }, [chain]);
  useEffect(() => { if (!evm) { setBal(null); return; } balanceOf(chain, from, evm.address).then(setBal); }, [chain, from, evm?.address]); // eslint-disable-line react-hooks/exhaustive-deps
  const valid = to && from.address !== to.address && /^\d+(\.\d+)?$/.test(amount) && Number(amount) > 0;
  const loadQuote = async () => {
    if (!valid) return;
    setBusy(true); setErr('');
    try { setQuote(await lifiServerQuote({ fromChain: CHAIN_ID[chain], toChain: CHAIN_ID[chain], fromToken: from.address, toToken: to.address, fromAmount: toUnits(amount, from.decimals), fromAddress: evm?.address || PREVIEW_ADDRESS, slippage })); }
    catch (e) { setQuote(null); setErr(e.message); } finally { setBusy(false); }
  };
  useEffect(() => { setQuote(null); if (!valid) return undefined; const t = setTimeout(loadQuote, 700); return () => clearTimeout(t); }, [chain, from.address, to?.address, amount, slippage, evm?.address]); // eslint-disable-line react-hooks/exhaustive-deps
  const swap = async () => {
    setBusy(true); setErr('');
    try {
      let q = quote;
      if (!q || q.action.fromAddress.toLowerCase() !== evm.address.toLowerCase()) q = await lifiServerQuote({ fromChain: CHAIN_ID[chain], toChain: CHAIN_ID[chain], fromToken: from.address, toToken: to.address, fromAmount: toUnits(amount, from.decimals), fromAddress: evm.address, slippage });
      const out = await executeLifi({ quote: q, wallet: evm, provider, switchTo, onStep: setStep });
      moneyConfirmed({ title: `Swap confirmed on ${EVM_CHAINS[chain]?.chainName}`, chain: q.action.fromChainId, hash: out.hash, wallet: evm.address });
      setQuote(null); balanceOf(chain, from, evm.address).then(setBal);
    } catch (e) { setErr(e.code === 4001 ? 'Declined in wallet — nothing sent.' : e.message); } finally { setBusy(false); setStep(''); }
  };
  const est = quote?.estimate;
  const out = est ? fromUnits(est.toAmount, quote.action.toToken.decimals) : null;
  const min = est ? fromUnits(est.toAmountMin, quote.action.toToken.decimals) : null;
  const gasUsd = (est?.gasCosts || []).reduce((a, g) => a + Number(g.amountUSD || 0), 0);
  const note = quote?.feeless?.note;
  return <section className="swap-order jup-card evm-swap" data-testid="evm-swap">
    <div className="jup-head"><span className="jup-title"><ArrowDownUp size={15} />Swap · {EVM_CHAINS[chain]?.chainName}</span>
      <button type="button" className="jup-chip" onClick={() => setSlippage(s => (s === 0.005 ? 0.01 : s === 0.01 ? 0.03 : 0.005))} title="Tap to change max slippage">Slippage {(slippage * 100).toFixed(1)}%</button>
      <button type="button" className="jup-icon" onClick={loadQuote} disabled={busy || !valid} aria-label="Refresh quote"><RefreshCw size={14} className={busy ? 'spin' : ''} /></button></div>
    <div className="jup-panel"><div className="jup-panel-head"><small>You pay</small>{bal != null && <span className="jup-bal">Balance {bal.toLocaleString(undefined, { maximumFractionDigits: 5 })}<button type="button" onClick={() => setAmount(String(from.address === NATIVE ? Math.max(0, Math.floor(bal * 0.97 * 1e6) / 1e6) : bal))}>Max</button></span>}</div>
      <div className="jup-row"><EvmTokenPicker chain={chain} value={from} onChange={t => setFrom(t)} onNetwork={onNetwork} testId="evm-swap-from" />
        <NumInput className="jup-amount" inputMode="decimal" placeholder="0.00" value={amount} onChange={e => setAmount(e.target.value.replace(/[^0-9.]/g, ''))} aria-label="Amount" /></div></div>
    <button type="button" className="swap-reverse-button jup-flip" aria-label="Reverse" onClick={() => { if (to) { setFrom(to); setTo(from); } }}><ArrowDownUp size={16} /></button>
    <div className="jup-panel is-receive"><div className="jup-panel-head"><small>You receive</small></div>
      <div className="jup-row">{to ? <EvmTokenPicker chain={chain} value={to} onChange={t => setTo(t)} onNetwork={onNetwork} testId="evm-swap-to" /> : <span className="cc-empty">Loading…</span>}
        <strong className="jup-out" data-testid="evm-swap-out">{out != null ? out.toLocaleString(undefined, { maximumFractionDigits: 6 }) : busy ? '…' : '0'}</strong></div></div>
    {quote && <div className="jup-rate"><span>Min received <b>{min.toLocaleString(undefined, { maximumFractionDigits: 6 })} {quote.action.toToken.symbol}</b></span><span>Gas ≈ ${gasUsd.toFixed(2)}</span><span>via {quote.toolDetails?.name || quote.tool}</span></div>}
    {quote && <p className="evm-safety"><ShieldCheck size={12} />Route verified: LI.FI contract on {EVM_CHAINS[chain]?.chainName}{quote.feeless?.feeBps ? ` · FEELESS fee ${(quote.feeless.feeBps / 100).toFixed(2)}% (+ LI.FI 0.25%)` : ''}{note ? ` · ${note}` : ''}</p>}
    {err && <p className="swap-message" role="alert">{err}</p>}
    <div className="swap-buttons jup-cta">{!evm
      ? <button type="button" className="btn-primary" onClick={() => (switchTo ? switchTo(chain) : connect('evm')).catch(e => setErr(e.message))}><Wallet size={15} />Connect EVM wallet</button>
      : <button type="button" className="btn-primary" data-testid="evm-swap-go" disabled={busy || !valid || !quote} onClick={swap}><ShieldCheck size={15} />{busy ? (step || 'Getting the best route…') : !quote ? 'Getting quote…' : `Swap on ${EVM_CHAINS[chain]?.chainName}`}</button>}</div>
    <p className="swap-safety"><ShieldCheck size={13} />Non-custodial. Exact-amount approvals only. The wallet checks network and contract before you sign.</p>
  </section>;
}
