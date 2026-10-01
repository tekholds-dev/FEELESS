import React, { useEffect, useState } from 'react';
import { lifiFeeConfig } from '../../lib/lifiFee';
import { CHAIN_ID, NATIVE, toUnits, fromUnits, lifiServerQuote, executeLifi } from '../../lib/lifiExec';
import { apiUrl } from '../../lib/api';
import { toast } from 'sonner';
import { Zap, ArrowLeftRight } from 'lucide-react';
import { useWallet, EVM_CHAINS } from '../../hooks/useWallet';
import { moneyConfirmed, watchBridge } from '../../lib/moneyConfirm';

// EVM swaps + bridging via LI.FI (the router behind Jumper). Non-custodial: the wallet signs every tx.
export const EVM_TRADE_CHAINS = Object.keys(CHAIN_ID);

export function EvmTrade({ pair }) {
  const { wallet, provider, switchTo, connect } = useWallet() || {};
  const chain = pair?.chainId;
  const [side, setSide] = useState('buy');
  const [lifiPct, setLifiPct] = useState(null);
  useEffect(() => { lifiFeeConfig().then(c => setLifiPct(c?.fee ? (c.fee * 100).toFixed(2) : null)); }, []);
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
      const tokenInfo = await (await fetch(apiUrl(`/api/lifi/token?chain=${CHAIN_ID[chain]}&token=${token}`))).json();
      const fromToken = side === 'buy' ? NATIVE : token;
      const toToken = side === 'buy' ? token : NATIVE;
      const fromDec = side === 'buy' ? 18 : tokenInfo.decimals;
      const q = await lifiServerQuote({ fromChain: CHAIN_ID[side === 'buy' ? fromChain : chain], toChain: CHAIN_ID[side === 'buy' ? chain : fromChain], fromToken, toToken, fromAmount: toUnits(amount, fromDec), fromAddress: w.address, slippage: 0.01 });
      if (!q.transactionRequest) throw new Error(q.message || 'No route for this trade.');
      setQuote({ ...q, tokenInfo, outDec: side === 'buy' ? tokenInfo.decimals : 18 });
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in wallet.' : e.message); } finally { setBusy(false); }
  };
  const [step, setStep] = useState('');
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
  const bridging = fromChain !== chain;
  return <aside className="quick-trade evm-trade" data-testid="evm-trade">
    <div className="qt-head"><Zap size={14} /><b>Quick trade</b><span className="qt-chain">{chain}</span><div className="qt-side">{['buy', 'sell'].map(x => <button key={x} type="button" className={side === x ? `active ${x}` : ''} onClick={() => { setSide(x); setQuote(null); }}>{x === 'buy' ? 'Buy' : 'Sell'}</button>)}</div></div>
    <label className="evm-row"><small>{side === 'buy' ? 'Pay with' : 'Receive on'}</small><select value={fromChain} onChange={e => { setFromChain(e.target.value); setQuote(null); }}>{Object.keys(CHAIN_ID).map(k => <option key={k} value={k}>{EVM_CHAINS[k].chainName}{k !== chain ? ' (bridge)' : ''}</option>)}</select></label>
    <label className="evm-row"><small>Amount ({side === 'buy' ? native : `$${pair.baseToken.symbol}`})</small><input inputMode="decimal" value={amount} onChange={e => { setAmount(e.target.value.replace(/[^\d.]/g, '')); setQuote(null); }} /></label>
    {quote && <div className="qt-quote"><div><small>You get ≈</small><b>{fromUnits(quote.estimate.toAmount, quote.outDec).toLocaleString(undefined, { maximumFractionDigits: 6 })} {side === 'buy' ? pair.baseToken.symbol : EVM_CHAINS[fromChain]?.nativeCurrency?.symbol}</b></div><div><small>Route</small><b>{quote.toolDetails?.name || quote.tool}{bridging ? ' · bridge' : ''}</b></div><div><small>Est. time</small><b>{Math.ceil((quote.estimate.executionDuration || 30) / 60)} min</b></div></div>}
    <button type="button" className="btn-primary qt-go m-go" disabled={busy || !(Number(amount) > 0)} onClick={quote ? execute : getQuote}>{busy ? (step || 'Working…') : quote ? `Confirm ${side} in wallet` : bridging ? <><ArrowLeftRight size={14} /> Get bridge quote</> : `Get ${side} quote`}</button>
    <small className="qt-note">{lifiPct ? `FEELESS fee ${lifiPct}% (via LI.FI)` : 'FEELESS platform fee: 0%'} · LI.FI provider and network fees appear in the quote · you sign every step · non-custodial</small>
  </aside>;
}
