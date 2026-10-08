import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { relayConnection } from '../lib/launchRail';
import { SOL_MINT } from '../lib/fuseGo';
import { NATIVE, lifiServerQuote, executeLifi } from '../lib/lifiExec';
import { tiny, usd } from '../lib/num';
import { TokenAvatar } from './terminal/MarketPrimitives';
import '../styles/dustCleanup.css';

// 🧹 Dust cleanup (Trade › 🧹 Dust): reads EVERY coin in your wallet and turns the leftovers back into gas.
//   Solana — swap a coin worth $0.50+ to SOL (normal FEELESS swap: quote → simulate → you sign → execute) or BURN + CLOSE dust / empty
//   accounts so their rent (~0.002 SOL each) comes back. Cronos — swap any listed token to CRO through LI.FI.
// Non-custodial: FEELESS builds the transactions, YOUR wallet signs every one. A burned coin is gone — the screen says so first.
const atomsToUi = (raw, dec) => { const s = BigInt(raw).toString().padStart(dec + 1, '0'); const w = s.slice(0, s.length - dec); const f = s.slice(s.length - dec).replace(/0+$/, ''); return f ? `${w}.${f}` : w; };
const b64 = u8 => btoa(String.fromCharCode(...u8));
async function trade(path, body) {
  const r = await fetch(apiUrl(`/api/trading${path}`), body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : `Error ${r.status}`); return d;
}
const LABEL = { swap: '↩ Swap to gas', burn: '🔥 Burn + close', close: '♻ Close (empty)' };
export const CHAINS = [['solana', '◎ Solana'], ['cronos', '🔷 Cronos']];

// What a cleanup will do, in plain words (also the confirm line before signing).
export function plan(rows, pick, act) {
  const chosen = rows.filter(r => pick[r.pubkey || r.address]);
  const by = k => chosen.filter(r => (act[r.pubkey || r.address] || r.best) === k);
  const swaps = by('swap'); const burns = by('burn'); const closes = by('close');
  return { chosen, swaps, burns, closes, rentSol: [...burns, ...closes].reduce((a, r) => a + (r.rentSol || 0), 0),
    swapUsd: swaps.reduce((a, r) => a + (r.usd || 0), 0), burnUsd: burns.reduce((a, r) => a + (r.usd || 0), 0) };
}

export default function DustCleanup() {
  const { wallet, provider, connect, switchTo } = useWallet() || {};
  const [chain, setChain] = useState('solana');
  // 👁 read ANY address (no wallet needed to look); cleaning still needs that wallet connected to sign
  const [lookAt, setLookAt] = useState('');
  const own = chain === 'solana' ? (wallet?.chain === 'solana' ? wallet.address : null) : (wallet?.chain === 'evm' ? wallet.address : null);
  const lookOk = chain === 'solana' ? /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(lookAt.trim()) : /^0x[0-9a-fA-F]{40}$/.test(lookAt.trim());
  const addr = own || (lookOk ? lookAt.trim() : null);
  const canSign = Boolean(own) && addr === own;
  const [data, setData] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const [pick, setPick] = useState({}); const [act, setAct] = useState({}); const [state, setState] = useState({});
  const [log, setLog] = useState([]); const [ack, setAck] = useState(false);
  const note = (text, tone = '') => setLog(l => [{ t: Date.now(), text, tone }, ...l].slice(0, 40));
  const load = useCallback(async () => {
    if (!addr) return; setErr(''); setData(null);
    try { const r = await fetch(apiUrl(`/api/reputation/wallet-dust/${chain}/${addr}`)); const d = await r.json(); if (!r.ok) throw new Error(d.detail || 'Could not read the wallet.');
      setData(d); setPick({}); setAct({}); setState({}); setAck(false); note(`Read ${d.rows.length} coin${d.rows.length === 1 ? '' : 's'} on ${chain}.`); }
    catch (e) { setErr(e.message); }
  }, [addr, chain]);
  useEffect(() => { load(); }, [load]);
  const rows = data?.rows || [];
  const key = r => r.pubkey || r.address;
  const p = plan(rows, pick, act);
  const selectDust = () => setPick(Object.fromEntries(rows.filter(r => r.best === 'burn' || r.best === 'close' || r.best === 'dust').map(r => [key(r), true])));
  const mark = (ks, s) => setState(o => ({ ...o, ...Object.fromEntries(ks.map(k => [k, s])) }));

  const runSolana = async () => {
    if (!provider || provider.publicKey?.toString() !== addr) throw new Error('Reconnect your Solana wallet and try again.');
    const { web3, connection } = await relayConnection();
    const quoted = [];
    for (const r of p.swaps) {
      mark([key(r)], 'quoting');
      try { const order = await trade('/quote', { input_mint: r.mint, output_mint: SOL_MINT, amount: atomsToUi(r.raw, r.decimals), slippage_bps: 300, wallet: addr });
        await trade('/simulate', { order_id: order.order_id }); quoted.push({ r, order }); mark([key(r)], 'ready'); }
      catch (e) { mark([key(r)], 'failed'); note(`$${r.symbol}: no swap route — ${e.message}`, 'bad'); }
    }
    let closeTxs = [];
    const closeRows = [...p.burns, ...p.closes];
    if (closeRows.length) {
      const res = await fetch(apiUrl('/api/reputation/wallet-dust/solana/close-tx'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr, accounts: closeRows.map(r => r.pubkey) }) });
      const d = await res.json(); if (!res.ok) throw new Error(d.detail || 'Could not build the cleanup.');
      closeTxs = d.txs.map(x => ({ ...x, tx: web3.Transaction.from(Uint8Array.from(atob(x.tx), c => c.charCodeAt(0))) }));
    }
    const { VersionedTransaction } = web3;
    const swapTxs = quoted.map(q => VersionedTransaction.deserialize(Uint8Array.from(atob(q.order.quote.transaction), c => c.charCodeAt(0))));
    const all = [...swapTxs, ...closeTxs.map(c => c.tx)];
    if (!all.length) throw new Error('Nothing left to send.');
    note(`Approve ${all.length} transaction${all.length === 1 ? '' : 's'} in your wallet…`);
    const signed = provider.signAllTransactions ? await provider.signAllTransactions(all) : await all.reduce(async (a, tx) => [...await a, await provider.signTransaction(tx)], Promise.resolve([]));
    if (!Array.isArray(signed) || signed.length !== all.length) throw new Error('Your wallet did not sign every transaction — nothing was sent.');
    await Promise.all(quoted.map(async (q, i) => {
      const k = key(q.r); mark([k], 'sending');
      try { let res = await trade('/execute', { order_id: q.order.order_id, signed_transaction: b64(signed[i].serialize()) });
        for (let n = 0; n < 30 && !['confirmed', 'failed'].includes(res.state); n++) { await new Promise(z => setTimeout(z, 2000)); try { res = await trade(`/order/${q.order.order_id}`); } catch { /* keep polling */ } }
        mark([k], res.state === 'confirmed' ? 'done' : 'failed');
        note(res.state === 'confirmed' ? `↩ $${q.r.symbol} → SOL (${usd(q.r.usd)})` : `$${q.r.symbol}: swap did not land`, res.state === 'confirmed' ? 'good' : 'bad');
      } catch (e) { mark([k], 'failed'); note(`$${q.r.symbol}: ${e.message}`, 'bad'); }
    }));
    await Promise.all(closeTxs.map(async (c, j) => {
      mark(c.accounts, 'sending');
      try { const sig = await connection.sendRawTransaction(signed[swapTxs.length + j].serialize(), { maxRetries: 3 });
        await connection.confirmTransaction(sig, 'confirmed'); mark(c.accounts, 'done');
        note(`♻ ${c.accounts.length} account${c.accounts.length === 1 ? '' : 's'} closed${c.burns ? ` (${c.burns} burned)` : ''} — ◎${c.rentSol.toFixed(5)} rent back`, 'good');
      } catch (e) { mark(c.accounts, 'failed'); note(`Close failed: ${e.message}`, 'bad'); }
    }));
  };

  const runCronos = async () => {
    for (const r of p.swaps.concat(p.chosen.filter(x => (act[key(x)] || x.best) === 'dust'))) {
      const k = key(r); mark([k], 'quoting');
      try { const quote = await lifiServerQuote({ fromChain: 25, toChain: 25, fromToken: r.address, toToken: NATIVE, fromAmount: r.raw, fromAddress: addr, slippage: 0.01 });
        mark([k], 'sending');
        await executeLifi({ quote, wallet, provider, switchTo, onStep: s => note(`$${r.symbol}: ${s}`) });
        mark([k], 'done'); note(`↩ $${r.symbol} → CRO (${usd(r.usd)})`, 'good');
      } catch (e) { mark([k], 'failed'); note(`$${r.symbol}: ${e.message}`, 'bad'); }
    }
  };

  const go = async () => {
    if (!p.chosen.length) return;
    if (!canSign) { toast.error('You are only looking at this address — connect that wallet to clean it.'); return; }
    if (p.burns.length && !ack) { toast.error('Tick the box: burned coins are gone for good.'); return; }
    setBusy(true); setErr('');
    try { if (chain === 'solana') await runSolana(); else await runCronos(); toast.success('Cleanup finished — see the activity below.'); }
    catch (e) { setErr(e.message); note(e.message, 'bad'); }
    finally { setBusy(false); setTimeout(load, 4000); }
  };

  return <section className="m-card m-live dc" data-testid="dust-cleanup">
    <header className="dc-head"><div><span className="m-label">🧹 DUST CLEANUP</span><b>Turn leftovers back into gas</b>
      <small className="m-dim">Reads every coin in your wallet. Swap what is worth something, burn + close the rest to get the account rent back. Your wallet signs every step.</small></div>
      <div className="m-seg" role="radiogroup" aria-label="Chain">{CHAINS.map(([k, l]) => <button type="button" key={k} role="radio" aria-checked={chain === k} className={chain === k ? 'active' : ''} onClick={() => { setChain(k); setData(null); setErr(''); setLookAt(''); }} data-testid={`dc-chain-${k}`}>{l}</button>)}</div></header>
    {!own && <div className="dc-look"><input className="m-input" value={lookAt} onChange={e => setLookAt(e.target.value)} placeholder={chain === 'solana' ? 'or paste any Solana address to look' : 'or paste any 0x… Cronos address to look'} aria-label="Address to read" data-testid="dc-look" />
      {lookAt && !lookOk && <small className="dc-err">Not a {chain === 'solana' ? 'Solana' : '0x'} address.</small>}</div>}
    {err && !addr && <p className="dc-err" role="alert">{err}</p>}
    {!addr ? <div className="dc-empty"><p className="m-dim">Connect your {chain === 'solana' ? 'Solana' : 'Cronos (EVM — Crypto.com DeFi, MetaMask, Trust…)'} wallet to read and clean its coins.</p>
      <button type="button" className="m-btn primary m-go" onClick={() => Promise.resolve(chain === 'solana' ? connect?.('solana') : connect?.('evm', undefined, { chain: 'cronos' })).catch(e => setErr(e.message))} data-testid="dc-connect">Connect wallet</button></div>
      : <>
      <div className="dc-sum" data-testid="dc-summary">
        <span><small>Coins</small><b className="m-num">{data ? rows.length : '…'}</b></span>
        {chain === 'solana' ? <><span><small>Dust / empty</small><b className="m-num">{data?.summary?.dust ?? '…'}</b></span><span><small>Rent to win back</small><b className="m-num">◎{(data?.summary?.rentBackSol || 0).toFixed(4)}</b></span></>
          : <span><small>CRO now</small><b className="m-num">{data ? tiny(data.nativeCro, 4) : '…'}</b></span>}
        <span><small>Worth swapping</small><b className="m-num">{usd(data?.summary?.swapUsd || 0)}</b></span>
        <span className="dc-tools"><button type="button" className="m-btn" onClick={selectDust} disabled={!rows.length || busy} data-testid="dc-select-dust">Select dust</button>
          <button type="button" className="m-btn" onClick={load} disabled={busy} data-testid="dc-refresh">↻ Re-read</button></span></div>
      {err && <p className="dc-err" role="alert">{err}</p>}
      {!canSign && <p className="m-note dc-ro">👁 Looking only — connect this wallet to clean it.</p>}
      {!data ? <div className="dc-loading" aria-busy="true"><i /><i /><i /></div> : !rows.length ? <p className="m-dim dc-empty">No coins in this wallet — nothing to clean.</p>
        : <ul className="dc-list">{rows.map((r, i) => { const k = key(r); const a = act[k] || r.best; const st = state[k];
          return <li key={k} className={`dc-row ${pick[k] ? 'is-on' : ''} ${st ? `is-${st}` : ''}`} style={{ '--i': Math.min(i, 12) }}>
            <label className="dc-pick"><input type="checkbox" checked={!!pick[k]} disabled={busy || st === 'done'} onChange={e => setPick(o => ({ ...o, [k]: e.target.checked }))} aria-label={`Pick $${r.symbol}`} /></label>
            <TokenAvatar pair={{ chainId: chain, baseToken: { address: r.mint || r.address, symbol: r.symbol }, info: { imageUrl: r.logo } }} size={26} />
            <span className="dc-coin"><b>${r.symbol}</b><small className="m-dim">{tiny(r.ui, 4)} · {r.usd == null ? 'no price' : usd(r.usd)}{r.rentSol ? ` · ◎${r.rentSol.toFixed(4)} rent` : ''}</small></span>
            <select className="m-input dc-act" value={a} disabled={busy || st === 'done'} onChange={e => setAct(o => ({ ...o, [k]: e.target.value }))} aria-label={`What to do with $${r.symbol}`} data-testid={`dc-act-${r.symbol}`}>
              {(chain === 'solana' ? r.actions : ['swap']).map(x => <option key={x} value={x}>{LABEL[x]}</option>)}</select>
            <i className={`dc-st ${st || ''}`}>{st === 'done' ? '✓' : st === 'failed' ? '✕' : st ? '…' : ''}</i>
          </li>; })}</ul>}
      {p.chosen.length > 0 && <div className="dc-go">
        <p>{p.swaps.length ? `↩ ${p.swaps.length} swap${p.swaps.length === 1 ? '' : 's'} to ${chain === 'solana' ? 'SOL' : 'CRO'} (${usd(p.swapUsd)})` : ''}
          {p.burns.length ? ` · 🔥 ${p.burns.length} burn${p.burns.length === 1 ? '' : 's'} (${usd(p.burnUsd)} destroyed)` : ''}
          {p.burns.length + p.closes.length ? ` · ♻ ◎${p.rentSol.toFixed(4)} rent back` : ''}</p>
        {p.burns.length > 0 && <label className="dc-ack"><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} data-testid="dc-ack" /> Burned coins are gone for good — I only burn what I don't want.</label>}
        <button type="button" className="m-btn primary m-go" disabled={busy} onClick={go} data-testid="dc-go">{busy ? 'Working…' : `🧹 Clean up ${p.chosen.length}`}</button></div>}
      {log.length > 0 && <ol className="dc-log" aria-live="polite" data-testid="dc-log">{log.map(l => <li key={l.t + l.text} className={l.tone}><time>{new Date(l.t).toLocaleTimeString()}</time>{l.text}</li>)}</ol>}
    </>}
  </section>;
}
