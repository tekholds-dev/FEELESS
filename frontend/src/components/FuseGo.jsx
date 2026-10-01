import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { fuseOrders, orderMatches } from '../lib/fuseGo';
import { readChatSession } from '../lib/chatSession';
import { impactPercent } from '../lib/impactGuard';

// ⚡ One-click Fuse in. Quote + simulate every leg in parallel (refreshed every 10s while open), show the exact
// review (coin, SOL in, est. out, fee), ONE wallet approval for all legs, then send + confirm each leg live.
const REFRESH_MS = 10000;
async function api(path, body) {
  const r = await fetch(apiUrl(`/api/trading${path}`), body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : `Error ${r.status}`); return d;
}
const b64 = u8 => btoa(String.fromCharCode(...u8));
const outOf = o => { const dec = o?.output_metadata?.decimals; const raw = o?.quote?.outAmount; return dec == null || raw == null ? null : Number(raw) / 10 ** dec; };
// What the review screen promises per leg (the "before" half of the receipt).
export function quoteLine(r) {
  const q = r.order?.quote || {}; const usd = Number(q.inUsdValue) || 0; const sol = Number(r.request?.amount) || 0;
  const solUsd = sol > 0 && usd > 0 ? usd / sol : 0;
  const lamports = ['signatureFeeLamports', 'prioritizationFeeLamports'].reduce((a, k) => a + Number(q[k] || 0), 0);
  const tokens = outOf(r.order); const liq = Number(r.leg?.liquidityUsd) || 0;
  const route = [...new Set((q.routePlan || []).map(x => x?.swapInfo?.label).filter(Boolean))];
  return { sig: r.sig, symbol: r.target?.symbol, sol, usd, tokens, feeUsd: usd * (r.order?.feeless_fee?.bps || 0) / 10000, feeBps: r.order?.feeless_fee?.bps || 0,
    networkUsd: lamports / 1e9 * solUsd, impact: impactPercent(q), price: tokens ? usd / tokens : null, weight: Number(r.leg?.weight) || null,
    pool: r.leg?.dex || route[0] || 'best route', route, liq, share: liq ? usd / liq * 100 : null, side: r.request?.input_mint === r.order?.input_mint && r.order?.output_mint === 'So11111111111111111111111111111111111111112' ? 'sell' : 'buy' };
}
const fmt = n => (n == null ? '—' : n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : n >= 1 ? n.toFixed(2) : n.toPrecision(3));

export function FuseGo({ legs, onClose, fuse, orders, side = 'buy', position }) {
  const sell = side === 'sell';
  const { wallet, provider, connect, switchTo } = useWallet() || {};
  const addr = wallet?.chain === 'solana' ? wallet.address : null;
  const [rows, setRows] = useState([]);       // {leg, target, request, order, err, state, sig, skip}
  const [phase, setPhase] = useState('quote'); // quote | review | signing | sending | done
  const seq = useRef(0);
  const [rcpt, setRcpt] = useState(null);       // after: quoted vs paid (server receipt)

  const quoteAll = async () => {
    const plan = orders || fuseOrders(legs, addr); const my = ++seq.current;
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
          if (res.state === 'confirmed') window.dispatchEvent(new CustomEvent('feeless:trade-confirmed', { detail: { mint: r.target.mint, side, signature: res.signature, usd: Number(r.order.quote?.inUsdValue) || 0, wallet: addr, tokens: outOf(r.order) } }));
        } catch (e) { up(id, { state: 'failed', err: e.message }); }
      }));
      setPhase('done');
      // After receipt: quoted vs exact fills (fills are read from chain a few seconds after confirm).
      const quoted = ready.map(r => ({ ...quoteLine(r), sig: landed.find(l => l.pairAddress === r.leg.pairAddress)?.signature })).filter(q => q.sig);
      if (quoted.length) [4000, 15000, 40000].forEach(ms => setTimeout(() => fetch(apiUrl('/api/reputation/fuses/receipt'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, legs: quoted }) }).then(r => r.json()).then(d => d?.legs && setRcpt(d)).catch(() => {}), ms));
      // Fuse P&L: the server re-checks every signature is your confirmed FEELESS buy (retried while the fill is read).
      const ses = landed.length && readChatSession(addr);
      if (ses && sell && position) [5000, 20000].forEach(ms => setTimeout(() => fetch(apiUrl('/api/reputation/fuses/position/close'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, session: ses, id: position, signatures: landed.map(l => l.signature) }) }).then(() => window.dispatchEvent(new Event('feeless:fuse-pnl'))).catch(() => {}), ms));
      if (ses && !sell) [5000, 20000].forEach(ms => setTimeout(() => fetch(apiUrl('/api/reputation/fuses/position'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, session: ses, name: fuse?.name || 'Lab fuse', fuseId: fuse?.id || '', legs: landed }) }).then(() => window.dispatchEvent(new Event('feeless:fuse-pnl'))).catch(() => {}), ms));
      if (ses && !sell && fuse?.id) landed.forEach(l => [6000, 25000].forEach(ms => setTimeout(() => fetch(apiUrl(`/api/reputation/fuses/${fuse.id}/buy`), { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, session: ses, signature: l.signature }) }).catch(() => {}), ms)));   // creator's cut
    } catch (e) { toast.error(/reject|cancel/i.test(e.message) ? 'Cancelled in your wallet — nothing was sent.' : e.message); setPhase('review'); }
  };

  const lines = ready.map(quoteLine);
  const tot = lines.reduce((a, l) => ({ sol: a.sol + l.sol, usd: a.usd + l.usd, fee: a.fee + l.feeUsd, net: a.net + l.networkUsd }), { sol: 0, usd: 0, fee: 0, net: 0 });
  const usd2 = v => `$${(v || 0).toFixed(v > 0 && v < 0.1 ? 3 : 2)}`;
  if (!addr) return <div className="fg"><p className="m-dim">Connect a Solana wallet to fuse in — one approval covers every pool.</p>
    <div className="fg-acts"><button type="button" className="m-btn primary m-go" onClick={() => (wallet && switchTo ? switchTo('solana') : connect?.('solana'))}>Connect Solana wallet</button><button type="button" className="m-btn" onClick={onClose}>Back</button></div></div>;
  return <div className="fg" data-testid="fuse-go">
    <div className="fg-head"><span className="m-label">{phase === 'done' ? (sell ? 'UNFUSED' : 'FUSED') : phase === 'sending' ? 'SENDING' : phase === 'signing' ? 'APPROVE IN WALLET' : 'REVIEW · LIVE QUOTES'}</span>{['quote', 'review'].includes(phase) && <i className="fg-pulse" title="Quotes refresh every 10s" />}</div>
    <ul className="fg-legs">{(rows.length ? rows : orders || fuseOrders(legs, addr)).map((r, i) => <li key={r.leg.pairAddress} className={`fg-leg s-${r.state || (r.err || r.skip ? 'err' : r.order ? 'ok' : 'wait')}`} style={{ animationDelay: `${i * 40}ms` }}>
      <b>{r.target?.symbol || r.leg.symbol}</b><span className="m-num">{r.request?.amount ?? r.leg.sol} SOL</span>
      <span className="m-num m-dim">{r.skip || r.err || (r.order ? `≈ ${fmt(outOf(r.order))} ${r.target.symbol}` : 'quoting…')}</span>
      <em>{r.state === 'confirmed' ? <a href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noopener noreferrer">✓ done</a> : r.state === 'failed' ? '✕ failed' : r.state ? '… landing' : r.order ? '✓ simulated' : ''}</em></li>)}</ul>
    {phase !== 'done' ? <>
      {lines.length > 0 && <div className="fg-rcpt" data-testid="fg-before"><div className="fg-rcpt-head"><span className="m-label">RECEIPT · BEFORE YOU SIGN</span></div>
        <table><thead><tr><th>Coin</th><th>Pay</th><th>Get ≈</th><th>FEELESS fee</th><th>Network</th><th>Impact</th></tr></thead>
          <tbody>{lines.map(l => <tr key={l.symbol}><td>{l.symbol}</td><td>{l.sol} SOL<small>{usd2(l.usd)}</small></td><td>{fmt(l.tokens)}</td><td>{usd2(l.feeUsd)}</td><td>{usd2(l.networkUsd)}</td><td className={l.impact > 1 ? 'm-neg' : ''}>{l.impact != null ? `${l.impact.toFixed(2)}%` : '—'}</td></tr>)}</tbody>
          <tfoot><tr><td>Total</td><td>{tot.sol.toFixed(4)} SOL<small>{usd2(tot.usd)}</small></td><td /><td>{usd2(tot.fee)}</td><td>{usd2(tot.net)}</td><td /></tr></tfoot></table>
        {!sell && <details className="fg-how" data-testid="fg-how"><summary>How your money moves</summary>
          <ol className="fg-flow"><li><b>1</b>Your wallet sends {tot.sol.toFixed(4)} SOL ({usd2(tot.usd)}) — split by the Fuse weights.</li>
            {lines.map(l => <li key={l.symbol}><b>{l.symbol}</b><span>{l.weight ? `${Math.round(l.weight)}% → ` : ''}{l.sol} SOL ({usd2(l.usd)}) is swapped through <em>{l.route.length ? l.route.join(' → ') : l.pool}</em>
              {l.liq ? <> (pool depth {usd2(l.liq)}; your slice is <em>{l.share < 0.01 ? '<0.01' : l.share.toFixed(2)}%</em> of it{l.impact > 1 ? ' — big enough to move the price' : ''})</> : null}.
              You get ≈ {fmt(l.tokens)} {l.symbol}{l.price ? <> at ≈ ${l.price < 0.01 ? l.price.toPrecision(3) : l.price.toFixed(4)} each</> : null}.
              {l.feeUsd > 0 ? <> {usd2(l.feeUsd)} ({(l.feeBps / 100).toFixed(2)}%) is the FEELESS fee</> : <> No FEELESS fee</>}; {usd2(l.networkUsd)} goes to Solana validators.</span></li>)}
            <li><b>✓</b>The coins land in <em>your</em> wallet. FEELESS never holds them. From here each one moves with its own price — up or down. You don't earn the pool's trading fees (that's for liquidity providers); you own the coins.</li>
            <li><b>↩</b>Exit any time with Unfuse (one approval, same fees once) or set 🎯 limits to get pinged at your target.</li></ol>
        </details>}
        <p className="fg-rcpt-note">Costs {usd2(tot.fee + tot.net)} = <b>{tot.usd ? ((tot.fee + tot.net) / tot.usd * 100).toFixed(1) : 0}%</b> of {usd2(tot.usd)}. {tot.usd && (tot.fee + tot.net) / tot.usd > 0.05 ? 'High for this size — fewer pools or more SOL keeps more working.' : 'Quotes refresh every 10s until you sign.'}</p></div>}
      <div className="fg-acts"><button type="button" className="m-btn primary m-go" disabled={!ready.length || phase !== 'review'} onClick={signAll} data-testid="fg-sign">{phase === 'signing' ? 'Waiting for wallet…' : phase === 'sending' ? 'Sending…' : `${sell ? '↩ Unfuse' : '⚡ Approve'} ${ready.length} ${sell ? 'sell' : 'swap'}${ready.length === 1 ? '' : 's'} · 1 click`}</button>
        <button type="button" className="m-btn" disabled={['signing', 'sending'].includes(phase)} onClick={onClose}>Cancel</button></div>
      <small className="m-dim">Each pool is a normal swap your wallet signs. You approve them together; each lands on its own.</small>
    </> : <>
      <div className="fg-rcpt is-after" data-testid="fg-after"><div className="fg-rcpt-head"><span className="m-label">RECEIPT · AFTER</span><small className="m-dim">{!rcpt ? 'reading exact fills from chain…' : rcpt.settled ? 'exact fills' : 'some fills still landing'}</small></div>
        {rcpt && <table><thead><tr><th>Coin</th><th>Quoted</th><th>Paid</th><th>Fees</th><th>Got</th><th>Slip</th></tr></thead>
          <tbody>{rcpt.legs.map(l => <tr key={l.sig}><td>{l.symbol}</td><td>{usd2(l.quotedUsd)}</td><td>{l.pending ? '…' : usd2(l.paidUsd)}</td><td>{l.pending ? '…' : usd2(l.paidFeesUsd)}</td><td>{l.pending ? '…' : fmt(l.gotTokens)}</td>
            <td className={l.slippagePct > 1 ? 'm-neg' : 'm-pos'}>{l.slippagePct == null ? '—' : `${l.slippagePct.toFixed(2)}%`}</td></tr>)}</tbody>
          <tfoot><tr><td>Total</td><td>{usd2(rcpt.quotedUsd)}</td><td>{usd2(rcpt.paidUsd)}</td><td>{usd2(rcpt.paidFeesUsd)}</td><td colSpan={2}>{rcpt.feePct}% in fees</td></tr></tfoot></table>}
        {rcpt && <p className="fg-rcpt-note"><b>What happened:</b> {usd2(rcpt.paidUsd)} left your wallet; {usd2(rcpt.paidFeesUsd)} of it was fees; the rest became the coins above, now in your wallet. "Slip" = fewer coins than quoted because the price moved while it landed. Your Fuse P&L now tracks these exact fills live.</p>}</div>
      <div className="fg-acts"><button type="button" className="m-btn" onClick={onClose}>Done</button></div></>}
  </div>;
}
