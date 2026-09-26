import React, { useState } from 'react';
import { toast } from 'sonner';
import { Zap, ArrowLeftRight } from 'lucide-react';
import { useWallet, EVM_CHAINS } from '../../hooks/useWallet';

// EVM swaps + bridging via LI.FI (the router behind Jumper). Non-custodial: the wallet signs every tx.
const CHAIN_ID = { ethereum: 1, base: 8453, bsc: 56, arbitrum: 42161, avalanche: 43114, polygon: 137 };
const NATIVE = '0x0000000000000000000000000000000000000000';
const toUnits = (amt, dec) => { const [w, f = ''] = String(amt).split('.'); return BigInt(w || 0) * 10n ** BigInt(dec) + BigInt((f + '0'.repeat(dec)).slice(0, dec) || 0); };
const fromUnits = (v, dec) => Number(BigInt(v)) / 10 ** dec;

export function EvmTrade({ pair }) {
  const { wallet, provider, switchTo, connect } = useWallet() || {};
  const chain = pair?.chainId;
  const [side, setSide] = useState('buy');
  const [amount, setAmount] = useState('0.01');
  const [fromChain, setFromChain] = useState(chain);
  const [quote, setQuote] = useState(null);
  const [busy, setBusy] = useState(false);
  const native = EVM_CHAINS[fromChain]?.nativeCurrency?.symbol || 'ETH';
  const token = pair?.baseToken?.address;
  const getQuote = async () => {
    setBusy(true); setQuote(null);
    try {
      let w = wallet;
      if (!w || w.chain !== 'evm') w = (await (switchTo ? switchTo(fromChain) : connect('evm'))).wallet;
      const tokenInfo = await (await fetch(`https://li.quest/v1/token?chain=${CHAIN_ID[chain]}&token=${token}`)).json();
      const fromToken = side === 'buy' ? NATIVE : token;
      const toToken = side === 'buy' ? token : NATIVE;
      const fromDec = side === 'buy' ? 18 : tokenInfo.decimals;
      const q = await (await fetch(`https://li.quest/v1/quote?fromChain=${CHAIN_ID[side === 'buy' ? fromChain : chain]}&toChain=${CHAIN_ID[side === 'buy' ? chain : fromChain]}&fromToken=${fromToken}&toToken=${toToken}&fromAmount=${toUnits(amount, fromDec)}&fromAddress=${w.address}&slippage=0.01`)).json();
      if (!q.transactionRequest) throw new Error(q.message || 'No route for this trade.');
      setQuote({ ...q, tokenInfo, outDec: side === 'buy' ? tokenInfo.decimals : 18 });
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in wallet.' : e.message); } finally { setBusy(false); }
  };
  const execute = async () => {
    setBusy(true);
    try {
      const tx = quote.transactionRequest;
      await switchTo?.(Object.keys(CHAIN_ID).find(k => CHAIN_ID[k] === Number(tx.chainId)) || fromChain);
      if (quote.action.fromToken.address !== NATIVE && quote.estimate.approvalAddress) {
        const data = `0x095ea7b3${quote.estimate.approvalAddress.slice(2).padStart(64, '0')}${BigInt(quote.action.fromAmount).toString(16).padStart(64, '0')}`;
        await provider.request({ method: 'eth_sendTransaction', params: [{ from: wallet.address, to: quote.action.fromToken.address, data }] });
        toast('Approval sent — confirm the swap next.');
      }
      const hash = await provider.request({ method: 'eth_sendTransaction', params: [{ from: wallet.address, to: tx.to, data: tx.data, value: tx.value, gas: tx.gasLimit }] });
      toast.success(`Submitted: ${hash.slice(0, 10)}…`); setQuote(null);
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in wallet — nothing sent.' : e.message); } finally { setBusy(false); }
  };
  const bridging = fromChain !== chain;
  return <aside className="quick-trade evm-trade" data-testid="evm-trade">
    <div className="qt-head"><Zap size={14} /><b>Quick trade</b><span className="qt-chain">{chain}</span><div className="qt-side">{['buy', 'sell'].map(x => <button key={x} type="button" className={side === x ? `active ${x}` : ''} onClick={() => { setSide(x); setQuote(null); }}>{x === 'buy' ? 'Buy' : 'Sell'}</button>)}</div></div>
    <label className="evm-row"><small>{side === 'buy' ? 'Pay with' : 'Receive on'}</small><select value={fromChain} onChange={e => { setFromChain(e.target.value); setQuote(null); }}>{Object.keys(CHAIN_ID).map(k => <option key={k} value={k}>{EVM_CHAINS[k].chainName}{k !== chain ? ' (bridge)' : ''}</option>)}</select></label>
    <label className="evm-row"><small>Amount ({side === 'buy' ? native : `$${pair.baseToken.symbol}`})</small><input inputMode="decimal" value={amount} onChange={e => { setAmount(e.target.value.replace(/[^\d.]/g, '')); setQuote(null); }} /></label>
    {quote && <div className="qt-quote"><div><small>You get ≈</small><b>{fromUnits(quote.estimate.toAmount, quote.outDec).toLocaleString(undefined, { maximumFractionDigits: 6 })} {side === 'buy' ? pair.baseToken.symbol : EVM_CHAINS[fromChain]?.nativeCurrency?.symbol}</b></div><div><small>Route</small><b>{quote.toolDetails?.name || quote.tool}{bridging ? ' · bridge' : ''}</b></div><div><small>Est. time</small><b>{Math.ceil((quote.estimate.executionDuration || 30) / 60)} min</b></div></div>}
    <button type="button" className="btn-primary qt-go" disabled={busy || !(Number(amount) > 0)} onClick={quote ? execute : getQuote}>{busy ? 'Working…' : quote ? `Confirm ${side} in wallet` : bridging ? <><ArrowLeftRight size={14} /> Get bridge quote</> : `Get ${side} quote`}</button>
    <small className="qt-note">Routed by LI.FI (Jumper) · bridges between chains · you sign every step · non-custodial</small>
  </aside>;
}
