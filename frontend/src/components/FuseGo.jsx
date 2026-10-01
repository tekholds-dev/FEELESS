import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { fuseOrders, orderMatches } from '../lib/fuseGo';
import { readChatSession } from '../lib/chatSession';

// ⚡ One-click Fuse in. Quote + simulate every leg in parallel (refreshed every 10s while open), show the exact
// review (coin, SOL in, est. out, fee), ONE wallet approval for all legs, then send + confirm each leg live.
const REFRESH_MS = 10000;
async function api(path, body) {
  const r = await fetch(apiUrl(`/api/trading${path}`), body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : `Error ${r.status}`); return d;
}
const b64 = u8 => btoa(String.fromCharCode(...u8));
const outOf = o => { const dec = o?.output_metadata?.decimals; const raw = o?.quote?.outAmount; return dec == null || raw == null ? null : Number(raw) / 10 ** dec; };
const fmt = n => (n == null ? '—' : n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : n >= 1 ? n.toFixed(2) : n.toPrecision(3));

export function FuseGo({ legs, onClose, fuse }) {
  const { wallet, provider, connect, switchTo } = useWallet() || {};
  const addr = wallet?.chain === 'solana' ? wallet.address : null;
  const [rows, setRows] = useState([]);       // {leg, target, request, order, err, state, sig, skip}
  const [phase, setPhase] = useState('quote'); // quote | review | signing | sending | done
  const seq = useRef(0);

  const quoteAll = async () => {
    const plan = fuseOrders(legs, addr); const my = ++seq.current;
    const got = await Promise.all(plan.map(async o => {
      if (o.skip) return o;
      try { const order = await api('/quote', o.request); await api('/simulate', { order_id: order.order_id }); return orderMatches(o, order) ? { ...o, order } : { ...o, err: 'Quote did not match — refreshing' }; }
      catch (e) { return { ...o, err: e.message }; }
    }));
    if (my === seq.current) { setRows(got); setPhase(p => (p === 'quote' ? 'review' : p)); }
  };
  useEffect(() => {
    if (!addr || !['quote', 'review'].includes(phase)) return undefined;
    if (phase === 'quote') quoteAll();
    const t = setInterval(() => { if (!document.hidden) quoteAll(); }, REFRESH_MS);
    return () => clearInterval(t);
  }, [addr, phase === 'review' || phase === 'quote']); // eslint-disable-line react-hooks/exhaustive-deps

  const ready = rows.filter(r => r.order && !r.err);
  const signAll = async () => {
    if (!ready.length) return;
    if (!provider || provider.publicKey?.toString() !== addr) { toast.error('Reconnect your Solana wallet and try again.'); return; }
    seq.current++; setPhase('signing');
    try {
      const { VersionedTransaction } = await import('@solana/web3.js');
      const txs = ready.map(r => VersionedTransaction.deserialize(Uint8Array.from(atob(r.order.quote.transaction), c => c.charCodeAt(0))));
      const signed = provider.signAllTransactions ? await provider.signAllTransactions(txs) : await txs.reduce(async (acc, tx) => [...await acc, await provider.signTransaction(tx)], Promise.resolve([]));
      if (!Array.isArray(signed) || signed.length !== txs.length) throw new Error('Wallet did not sign every swap — nothing was sent.');
      setPhase('sending');
      const landed = [];
      const up = (id, patch) => setRows(list => list.map(x => (x.order?.order_id === id ? { ...x, ...patch } : x)));
      await Promise.all(ready.map(async (r, i) => {
        const id = r.order.order_id;
        try {
          let res = await api('/execute', { order_id: id, signed_transaction: b64(signed[i].serialize()) }); up(id, { state: res.state, sig: res.signature });
          for (let k = 0; k < 30 && res.signature && !['confirmed', 'failed'].includes(res.state); k++) { await new Promise(z => setTimeout(z, 2000)); try { res = await api(`/order/${id}`); up(id, { state: res.state }); } catch { /* keep polling */ } }
          if (res.state === 'confirmed') landed.push({ pairAddress: r.leg.pairAddress, chainId: r.leg.chainId || 'solana', symbol: r.target.symbol, signature: res.signature });
          if (res.state === 'confirmed') window.dispatchEvent(new CustomEvent('feeless:trade-confirmed', { detail: { mint: r.target.mint, side: 'buy', signature: res.signature, usd: Number(r.order.quote?.inUsdValue) || 0, wallet: addr, tokens: outOf(r.order) } }));
        } catch (e) { up(id, { state: 'failed', err: e.message }); }
      }));
      setPhase('done');
      // Fuse P&L: the server re-checks every signature is your confirmed FEELESS buy (retried while the fill is read).
      const ses = landed.length && readChatSession(addr);
      if (ses) [5000, 20000].forEach(ms => setTimeout(() => fetch(apiUrl('/api/reputation/fuses/position'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, session: ses, name: fuse?.name || 'Lab fuse', fuseId: fuse?.id || '', legs: landed }) }).then(() => window.dispatchEvent(new Event('feeless:fuse-pnl'))).catch(() => {}), ms));
      if (ses && fuse?.id) landed.forEach(l => [6000, 25000].forEach(ms => setTimeout(() => fetch(apiUrl(`/api/reputation/fuses/${fuse.id}/buy`), { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, session: ses, signature: l.signature }) }).catch(() => {}), ms)));   // creator's cut
    } catch (e) { toast.error(/reject|cancel/i.test(e.message) ? 'Cancelled in your wallet — nothing was sent.' : e.message); setPhase('review'); }
  };

  const totalSol = ready.reduce((a, r) => a + Number(r.request.amount), 0);
  const feeUsd = ready.reduce((a, r) => a + (Number(r.order.quote?.inUsdValue) || 0) * (r.order.feeless_fee?.bps || 0) / 10000, 0);
  if (!addr) return <div className="fg"><p className="m-dim">Connect a Solana wallet to fuse in — one approval covers every pool.</p>
    <div className="fg-acts"><button type="button" className="m-btn primary m-go" onClick={() => (wallet && switchTo ? switchTo('solana') : connect?.('solana'))}>Connect Solana wallet</button><button type="button" className="m-btn" onClick={onClose}>Back</button></div></div>;
  return <div className="fg" data-testid="fuse-go">
    <div className="fg-head"><span className="m-label">{phase === 'done' ? 'FUSED' : phase === 'sending' ? 'SENDING' : phase === 'signing' ? 'APPROVE IN WALLET' : 'REVIEW · LIVE QUOTES'}</span>{['quote', 'review'].includes(phase) && <i className="fg-pulse" title="Quotes refresh every 10s" />}</div>
    <ul className="fg-legs">{(rows.length ? rows : fuseOrders(legs, addr)).map((r, i) => <li key={r.leg.pairAddress} className={`fg-leg s-${r.state || (r.err || r.skip ? 'err' : r.order ? 'ok' : 'wait')}`} style={{ animationDelay: `${i * 40}ms` }}>
      <b>{r.target?.symbol || r.leg.symbol}</b><span className="m-num">{r.request?.amount ?? r.leg.sol} SOL</span>
      <span className="m-num m-dim">{r.skip || r.err || (r.order ? `≈ ${fmt(outOf(r.order))} ${r.target.symbol}` : 'quoting…')}</span>
      <em>{r.state === 'confirmed' ? <a href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noopener noreferrer">✓ done</a> : r.state === 'failed' ? '✕ failed' : r.state ? '… landing' : r.order ? '✓ simulated' : ''}</em></li>)}</ul>
    {phase !== 'done' ? <>
      <div className="fg-sum"><span>{ready.length} swap{ready.length === 1 ? '' : 's'} · {totalSol.toFixed(4)} SOL</span><span className="m-dim">FEELESS fee ≈ ${feeUsd.toFixed(2)}</span></div>
      <div className="fg-acts"><button type="button" className="m-btn primary m-go" disabled={!ready.length || phase !== 'review'} onClick={signAll} data-testid="fg-sign">{phase === 'signing' ? 'Waiting for wallet…' : phase === 'sending' ? 'Sending…' : `⚡ Approve ${ready.length} swap${ready.length === 1 ? '' : 's'} · 1 click`}</button>
        <button type="button" className="m-btn" disabled={['signing', 'sending'].includes(phase)} onClick={onClose}>Cancel</button></div>
      <small className="m-dim">Each pool is a normal swap your wallet signs. You approve them together; each lands on its own.</small>
    </> : <div className="fg-acts"><button type="button" className="m-btn" onClick={onClose}>Done</button></div>}
  </div>;
}
