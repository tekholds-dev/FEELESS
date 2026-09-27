import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ArrowLeftRight, Fuel, Repeat, ShieldCheck } from 'lucide-react';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl } from '../../lib/api';

// The trade desk: Swap (the existing Jupiter/LI.FI flows), Bridge (any EVM chain -> any EVM chain)
// and Get Gas (turn what you hold on one chain into gas on another). Non-custodial throughout:
// every route is a quote the user reviews, and every transaction is signed in their own wallet.
const CHAIN_ID = { ethereum: 1, base: 8453, bsc: 56, arbitrum: 42161, avalanche: 43114, polygon: 137, optimism: 10, zksync: 324, zora: 7777777, cronos: 25, unichain: 130, worldchain: 480 };
const NAMES = { ethereum: 'Ethereum', base: 'Base', bsc: 'BNB Chain', arbitrum: 'Arbitrum', avalanche: 'Avalanche', polygon: 'Polygon', optimism: 'Optimism', zksync: 'zkSync', zora: 'Zora', cronos: 'Cronos', unichain: 'Unichain', worldchain: 'World Chain' };
const NATIVE = '0x0000000000000000000000000000000000000000';
const toUnits = (amt, dec) => { const [w, f = ''] = String(amt).split('.'); return BigInt(w || 0) * 10n ** BigInt(dec) + BigInt((f + '0'.repeat(dec)).slice(0, dec) || 0); };
const fromUnits = (v, dec) => Number(BigInt(v || 0)) / 10 ** dec;

async function waitReceipt(provider, hash, tries = 60) {
  for (let i = 0; i < tries; i++) {
    const r = await provider.request({ method: 'eth_getTransactionReceipt', params: [hash] }).catch(() => null);
    if (r) { if (r.status === '0x0') throw new Error('Transaction reverted on-chain.'); return r; }
    await new Promise(res => setTimeout(res, 2000));
  }
  throw new Error('Still pending — check your wallet before retrying.');
}

// One LI.FI route: quote -> review -> (approve, wait) -> send. Shared by Bridge and Get Gas.
function useRoute() {
  const { wallet, provider, switchTo, connect } = useWallet() || {};
  const [quote, setQuote] = useState(null); const [busy, setBusy] = useState(false);
  const ensureEvm = async chain => { let w = wallet; if (!w || w.chain !== 'evm') w = (await (switchTo ? switchTo(chain) : connect('evm'))).wallet; return w; };
  const getQuote = async ({ fromChain, toChain, fromToken, toToken, amount, decimals = 18 }) => {
    setBusy(true); setQuote(null);
    try {
      const w = await ensureEvm(fromChain);
      const url = `https://li.quest/v1/quote?fromChain=${CHAIN_ID[fromChain]}&toChain=${CHAIN_ID[toChain]}&fromToken=${fromToken}&toToken=${toToken}&fromAmount=${toUnits(amount, decimals)}&fromAddress=${w.address}&slippage=0.01`;
      const q = await (await fetch(url)).json();
      if (!q.transactionRequest) throw new Error(q.message || 'No route found for this amount — try a bit more.');
      setQuote(q);
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in wallet.' : e.message); } finally { setBusy(false); }
  };
  const execute = async () => {
    setBusy(true);
    try {
      const tx = quote.transactionRequest;
      await switchTo?.(Object.keys(CHAIN_ID).find(k => CHAIN_ID[k] === Number(tx.chainId)));
      if (quote.action.fromToken.address !== NATIVE && quote.estimate.approvalAddress) {
        const data = `0x095ea7b3${quote.estimate.approvalAddress.slice(2).padStart(64, '0')}${BigInt(quote.action.fromAmount).toString(16).padStart(64, '0')}`;
        const ah = await provider.request({ method: 'eth_sendTransaction', params: [{ from: wallet.address, to: quote.action.fromToken.address, data }] });
        toast('Approval sent — waiting for it to confirm…');
        await waitReceipt(provider, ah);
      }
      const hash = await provider.request({ method: 'eth_sendTransaction', params: [{ from: wallet.address, to: tx.to, data: tx.data, value: tx.value, gas: tx.gasLimit }] });
      toast.success(`Sent ${hash.slice(0, 10)}… — cross-chain routes land in 1–5 min.`); setQuote(null);
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in wallet — nothing sent.' : e.message); } finally { setBusy(false); }
  };
  return { wallet, quote, busy, getQuote, execute, clear: () => setQuote(null) };
}

function RouteReview({ quote, busy, onExecute, onClear }) {
  if (!quote) return null;
  const out = fromUnits(quote.estimate.toAmount, quote.action.toToken.decimals);
  const gasUsd = (quote.estimate.gasCosts || []).reduce((a, g) => a + Number(g.amountUSD || 0), 0);
  const feeUsd = (quote.estimate.feeCosts || []).reduce((a, g) => a + Number(g.amountUSD || 0), 0);
  return <div className="td-review" data-testid="td-review">
    <div><small>You receive ≈</small><b>{out.toLocaleString(undefined, { maximumFractionDigits: 6 })} {quote.action.toToken.symbol}</b></div>
    <div className="td-review-meta"><span>via {quote.toolDetails?.name || quote.tool}</span><span>network gas ≈ ${gasUsd.toFixed(2)}</span><span>route fees ≈ ${feeUsd.toFixed(2)}</span><span>~{Math.max(1, Math.round((quote.estimate.executionDuration || 30) / 60))} min</span></div>
    <div className="td-review-actions"><button type="button" className="btn-outline" onClick={onClear}>Cancel</button><button type="button" className="btn-primary" disabled={busy} onClick={onExecute}>{busy ? 'Confirm in wallet…' : 'Confirm & sign'}</button></div>
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
    <div className="td-row"><label className="td-field"><small>Asset</small><select value={asset} onChange={e => { setAsset(e.target.value); r.clear(); }}><option value="native">Native gas coin</option><option value="usdc">USDC</option></select></label><label className="td-field"><small>Amount</small><input inputMode="decimal" value={amount} onChange={e => { setAmount(e.target.value.replace(/[^0-9.]/g, '')); r.clear(); }} /></label></div>
    {!r.quote && <button type="button" className="btn-primary td-go" disabled={r.busy || from === to || !Number(amount)} onClick={() => r.getQuote({ fromChain: from, toChain: to, fromToken: tok(from), toToken: tok(to), amount, decimals: asset === 'usdc' ? 6 : 18 })}>{r.busy ? 'Finding the best route…' : from === to ? 'Pick two different chains' : 'Get bridge quote'}</button>}
    <RouteReview quote={r.quote} busy={r.busy} onExecute={r.execute} onClear={r.clear} />
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
      <label className="td-field"><small>Gas to add (USD)</small><input inputMode="decimal" value={usd} onChange={e => { setUsd(e.target.value.replace(/[^0-9.]/g, '')); r.clear(); }} /></label>
      {source ? <button type="button" className="btn-primary td-go" disabled={r.busy || source.chain === target} onClick={() => r.getQuote({ fromChain: source.chain, toChain: target, fromToken: NATIVE, toToken: NATIVE, amount: (Number(usd) / (source.usd / source.balance)).toFixed(8) })}>{r.busy ? 'Routing…' : `Use ${source.symbol} on ${NAMES[source.chain]} → gas on ${NAMES[target]}`}</button>
        : <p className="wp-bio">No chain with enough spare balance to route from — add funds on any chain first.</p>}
    </div>}
    <RouteReview quote={r.quote} busy={r.busy} onExecute={r.execute} onClear={r.clear} />
  </div>;
}

function FeeExplainer() {
  const [f, setF] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/fees/public')).then(x => x.json()).then(setF).catch(() => {}); }, []);
  const pct = f ? (f.platformFeeBps / 100).toFixed(2) : null;
  return <div className="td-fees" data-testid="td-fees">
    <div className="td-fee good"><b>0%</b><span>Trade anything into $FEE (or its coins) — always FEELESS.</span></div>
    <div className="td-fee"><b>{pct == null ? '…' : `${pct}%`}</b><span>Everything else{f && Number(pct) > 0 ? ` — cut up to ${Math.max(...Object.values(f.tierDiscountPct || { 0: 0 }))}% by holding $FEE` : ' — no FEELESS fee right now'}.</span></div>
    <div className="td-fee"><ShieldCheck size={18} /><span>Non-custodial. Every route is shown before you sign; FEELESS never holds your funds.</span></div>
  </div>;
}

export function TradeDesk({ swap }) {
  const [mode, setMode] = useState('swap');
  const modes = [['swap', 'Swap', Repeat], ['bridge', 'Bridge', ArrowLeftRight], ['gas', 'Get gas', Fuel]];
  return <section className="trade-desk" data-testid="trade-desk">
    <FeeExplainer />
    <nav className="td-modes">{modes.map(([k, l, Icon]) => <button key={k} type="button" className={mode === k ? 'active' : ''} onClick={() => setMode(k)} data-testid={`td-mode-${k}`}><Icon size={15} />{l}</button>)}</nav>
    {mode === 'swap' && swap}
    {mode === 'bridge' && <Bridge />}
    {mode === 'gas' && <GetGas />}
  </section>;
}
