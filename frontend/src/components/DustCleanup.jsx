import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { relayConnection } from '../lib/launchRail';
import { SOL_MINT } from '../lib/fuseGo';
import { NATIVE, lifiServerQuote, executeLifi, executeLifiBatch } from '../lib/lifiExec';
import { tiny, usd } from '../lib/num';
import { TokenAvatar } from './terminal/MarketPrimitives';
import '../styles/dustCleanup.css';

// 🧹 Dust cleanup (Trade › 🧹 Dust): reads EVERY coin in your wallet and turns the leftovers back into gas.
//   Solana — swap a coin worth $0.50+ to SOL (normal FEELESS swap: quote → simulate → you sign → execute) or BURN + CLOSE dust / empty
//   accounts so their rent (~0.002 SOL each) comes back. EVM — EVERY chain the wallet holds something on (LI.FI balances + our own Cronos
//   read), grouped by chain; each chain's native coin is its gas, tokens swap to that gas through LI.FI on their own chain.
// Non-custodial: FEELESS builds the transactions, YOUR wallet signs every one. A burned coin is gone — the screen says so first.
const atomsToUi = (raw, dec) => { const s = BigInt(raw).toString().padStart(dec + 1, '0'); const w = s.slice(0, s.length - dec); const f = s.slice(s.length - dec).replace(/0+$/, ''); return f ? `${w}.${f}` : w; };
const b64 = u8 => btoa(String.fromCharCode(...u8));
async function trade(path, body) {
  const r = await fetch(apiUrl(`/api/trading${path}`), body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : `Error ${r.status}`); return d;
}
const LABEL = { swap: '↩ Swap to gas', burn: '🔥 Burn + close', close: '♻ Close (empty)' };
export const CHAINS = [['solana', '◎ Solana'], ['evm', '🌐 EVM · every chain']];
export const keyOf = r => r.pubkey || (r.chainId ? `${r.chainId}:${r.address}` : r.address);
// rows grouped by chain, chains in the order the server ranked them (biggest $ first)
export function grouped(rows, chains) {
  const at = Object.fromEntries((chains || []).map((c, i) => [c.chain, i]));
  return [...rows].sort((a, b) => (at[a.chain] ?? 99) - (at[b.chain] ?? 99) || (b.native ? 1 : 0) - (a.native ? 1 : 0) || (b.usd || 0) - (a.usd || 0));
}

// What a cleanup will do, in plain words (also the confirm line before signing).
// 🛑 a wallet "no" (EIP-1193 code 4001, or its usual wording) ends the whole run — the next prompt must never pop up after you declined one
export const isRejected = e => Number(e?.code) === 4001 || /reject|denied|declin|cancel/i.test(String(e?.message || ''));
// what an EVM sell-all sends: only coins worth swapping (a coin under the swap minimum costs two wallet prompts + gas to return cents) unless asked
export const evmTodo = (q, withDust) => (withDust ? q.swaps.concat(q.dust) : q.swaps);
export function plan(rows, pick, act) {
  const chosen = rows.filter(r => !r.native && pick[keyOf(r)]);
  const by = k => chosen.filter(r => (act[keyOf(r)] || r.best) === k);
  const swaps = by('swap'); const burns = by('burn'); const closes = by('close');
  return { chosen, swaps, burns, closes, dust: by('dust'), rentSol: [...burns, ...closes].reduce((a, r) => a + (r.rentSol || 0), 0),
    swapUsd: swaps.reduce((a, r) => a + (r.usd || 0), 0), burnUsd: burns.reduce((a, r) => a + (r.usd || 0), 0) };
}

const EXTRA_KEY = 'feeless.dustTokens';
export default function DustCleanup() {
  const { wallet, provider, connect, switchTo } = useWallet() || {};
  const [chain, setChain] = useState('solana');
  // 👁 read ANY address (no wallet needed to look); cleaning still needs that wallet connected to sign
  const [lookAt, setLookAt] = useState('');
  // ＋ Cronos contracts the owner tracks by hand (a coin no list or index knows): kept in this browser, sent with every read
  const [extra, setExtra] = useState(() => { try { return localStorage.getItem(EXTRA_KEY) || ''; } catch { return ''; } }); const [draft, setDraft] = useState('');
  const addExtra = () => { const got = (draft.match(/0x[0-9a-fA-F]{40}/g) || []).map(x => x.toLowerCase()); if (!got.length) return;
    const next = [...new Set([...extra.split(',').filter(Boolean), ...got])].slice(0, 40).join(','); setExtra(next); setDraft(''); try { localStorage.setItem(EXTRA_KEY, next); } catch { /* private window */ } };
  const own = chain === 'solana' ? (wallet?.chain === 'solana' ? wallet.address : null) : (wallet?.chain === 'evm' ? wallet.address : null);
  const lookOk = chain === 'solana' ? /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(lookAt.trim()) : /^0x[0-9a-fA-F]{40}$/.test(lookAt.trim());
  const addr = own || (lookOk ? lookAt.trim() : null);
  const canSign = Boolean(own) && addr === own;
  const [data, setData] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const [pick, setPick] = useState({}); const [act, setAct] = useState({}); const [state, setState] = useState({});
  const [log, setLog] = useState([]); const [ack, setAck] = useState(false);
  const [evmDust, setEvmDust] = useState(false); const stop = React.useRef(false);   // EVM: dust is skipped unless asked · ⏹ Stop / a wallet "no" ends the run
  const note = (text, tone = '') => setLog(l => [{ t: Date.now(), text, tone }, ...l].slice(0, 40));
  const load = useCallback(async () => {
    if (!addr) return; setErr(''); setData(null);
    try { const r = await fetch(apiUrl(`/api/reputation/wallet-dust/${chain}/${addr}${chain !== 'solana' && extra ? `?add=${extra}` : ''}`)); const d = await r.json(); if (!r.ok) throw new Error(d.detail || 'Could not read the wallet.');
      setData(d); setPick({}); setAct({}); setState({}); setAck(false); note(`Read ${d.rows.length} coin${d.rows.length === 1 ? '' : 's'} on ${chain}.`); }
    catch (e) { setErr(e.message); }
  }, [addr, chain, extra]);
  useEffect(() => { load(); }, [load]);
  const rows = grouped(data?.rows || [], data?.chains);
  const key = keyOf;
  const chainUsd = Object.fromEntries((data?.chains || []).map(c => [c.chain, c]));
  const p = plan(rows, pick, act);
  const selectDust = () => setPick(Object.fromEntries(rows.filter(r => !r.native).filter(r => r.best === 'burn' || r.best === 'close' || r.best === 'dust').map(r => [key(r), true])));
  const mark = (ks, s) => setState(o => ({ ...o, ...Object.fromEntries(ks.map(k => [k, s])) }));

  const runSolana = async q => {
    if (!provider || provider.publicKey?.toString() !== addr) throw new Error('Reconnect your Solana wallet and try again.');
    const { web3, connection } = await relayConnection();
    const quoted = [];
    const quoteOne = async r => {   // 4 at a time — 30 coins quote in a few seconds, not one by one
      mark([key(r)], 'quoting');
      try { const order = await trade('/quote', { input_mint: r.mint, output_mint: SOL_MINT, amount: atomsToUi(r.raw, r.decimals), slippage_bps: 300, wallet: addr });
        await trade('/simulate', { order_id: order.order_id }); quoted.push({ r, order }); mark([key(r)], 'ready'); }
      catch (e) { mark([key(r)], 'failed'); note(`$${r.symbol}: no swap route — ${e.message}`, 'bad'); }
    };
    for (let i = 0; i < q.swaps.length; i += 4) await Promise.all(q.swaps.slice(i, i + 4).map(quoteOne));
    let closeTxs = [];
    const closeRows = [...q.burns, ...q.closes];
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

  // EVM: every token swaps on ITS OWN chain into that chain's gas. Per chain: quote them all, then ONE wallet request for the lot when the wallet can
  // batch (EIP-5792); a plain wallet signs them one after another by itself — no further click here either way.
  const runEvm = async q => {
    const todo = evmTodo(q, evmDust); const chains = [...new Set(todo.map(r => r.chainId))];
    stop.current = false;
    if (!evmDust && q.dust.length) note(`Skipped ${q.dust.length} coin${q.dust.length === 1 ? '' : 's'} worth under ${usd(data?.swapMinUsd || 0.5)} each — selling them costs more in gas than they return (tick "include dust" to sell them anyway).`);
    for (const cid of chains) {
      if (stop.current) break;
      const mine = todo.filter(r => r.chainId === cid); const quoted = [];
      const gas = (rows.find(x => x.native && x.chainId === cid) || {}).symbol || 'gas';
      const quoteOne = async r => { mark([key(r)], 'quoting');
        try { quoted.push({ r, quote: await lifiServerQuote({ fromChain: cid, toChain: cid, fromToken: r.address, toToken: NATIVE, fromAmount: r.raw, fromAddress: addr, slippage: 0.01 }) }); mark([key(r)], 'ready'); }
        catch (e) { mark([key(r)], 'failed'); note(`$${r.symbol}: ${e.message}`, 'bad'); } };
      for (let i = 0; i < mine.length; i += 4) await Promise.all(mine.slice(i, i + 4).map(quoteOne));
      if (!quoted.length) continue;
      const ks = quoted.map(x => key(x.r));
      let batched = null;
      try { mark(ks, 'sending'); batched = await executeLifiBatch({ quotes: quoted.map(x => x.quote), wallet, provider, switchTo, onStep: s => note(`${mine[0].chain}: ${s}`) }); }
      catch (e) { mark(ks, 'failed'); if (isRejected(e)) { stop.current = true; note('You declined the request in your wallet — stopped.', 'bad'); } else note(`${mine[0].chain}: ${e.message}`, 'bad'); continue; }
      if (batched) { mark(ks, 'done'); note(`↩ ${quoted.length} coin${quoted.length === 1 ? '' : 's'} → ${gas} on ${mine[0].chain} in one approval (${usd(quoted.reduce((a, x) => a + (x.r.usd || 0), 0))})`, 'good'); continue; }
      note(`${mine[0].chain}: this wallet signs one transaction at a time, so it will ask about ${quoted.length * 2} times (allow + swap for each of ${quoted.length} coin${quoted.length === 1 ? '' : 's'}). Decline once, or press Stop, and nothing more is asked.`);
      for (const { r, quote } of quoted) {
        const k = key(r);
        if (stop.current) { mark([k], ''); continue; }
        mark([k], 'sending');
        try { await executeLifi({ quote, wallet, provider, switchTo, onStep: s => note(`$${r.symbol} (${r.chain}): ${s}`) }); mark([k], 'done'); note(`↩ $${r.symbol} → ${gas} on ${r.chain} (${usd(r.usd)})`, 'good'); }
        catch (e) { mark([k], 'failed');
          if (isRejected(e)) { stop.current = true; note(`You declined $${r.symbol} in your wallet — stopped. Nothing else will be asked.`, 'bad'); }
          else note(`$${r.symbol}: ${e.message}`, 'bad'); }
      }
    }
  };

  // 🧹 ONE CLICK, no second box (owner, 2026-10-08: "not one click then click to confirm each"): every coin that isn't gas, each with its best
  // action. The button itself says how many will be BURNED; the wallet's own approval is the confirmation. Solana = ONE approval for everything;
  // EVM = one request per chain when the wallet can batch, else the wallet asks per transaction.
  const allPick = () => Object.fromEntries(rows.filter(r => !r.native && state[key(r)] !== 'done').map(r => [key(r), true]));
  const allPlan = plan(rows, allPick(), act);
  const cleanAll = async () => { const pk = allPick(); const q = plan(rows, pk, act); if (!q.chosen.length) return; setPick(pk); setAck(true); await go(q, true); };
  const go = async (q = p, acked = ack) => {
    if (!q?.chosen?.length) return;
    if (!canSign) { toast.error('You are only looking at this address — connect that wallet to clean it.'); return; }
    if (q.burns.length && !acked) { toast.error('Tick the box: burned coins are gone for good.'); return; }
    setBusy(true); setErr('');
    try { if (chain === 'solana') await runSolana(q); else await runEvm(q); toast.success('Cleanup finished — see the activity below.'); }
    catch (e) { setErr(e.message); note(e.message, 'bad'); }
    finally { setBusy(false); setTimeout(load, 4000); }
  };

  return <section className="m-card m-live dc" data-testid="dust-cleanup">
    <header className="dc-head"><div><span className="m-label">🧹 DUST CLEANUP</span><b>Turn leftovers back into gas</b>
      <small className="m-dim">Reads every coin in your wallet. Swap what is worth something, burn + close the rest to get the account rent back. Your wallet signs every step.</small></div>
      <div className="m-seg" role="radiogroup" aria-label="Chain">{CHAINS.map(([k, l]) => <button type="button" key={k} role="radio" aria-checked={chain === k} className={chain === k ? 'active' : ''} onClick={() => { setChain(k); setData(null); setErr(''); setLookAt(''); }} data-testid={`dc-chain-${k}`}>{l}</button>)}</div></header>
    {!own && <div className="dc-look"><input className="m-input" value={lookAt} onChange={e => setLookAt(e.target.value)} placeholder={chain === 'solana' ? 'or paste any Solana address to look' : 'or paste any 0x… address to look (every chain)'} aria-label="Address to read" data-testid="dc-look" />
      {lookAt && !lookOk && <small className="dc-err">Not a {chain === 'solana' ? 'Solana' : '0x'} address.</small>}</div>}
    {chain !== 'solana' && <div className="dc-look dc-track" data-testid="dc-track"><input className="m-input" value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => e.key === 'Enter' && addExtra()} placeholder="Missing a Cronos coin? Paste its contract (0x…) to track it" aria-label="Cronos token contract to track" data-testid="dc-track-input" />
      <button type="button" className="m-btn" disabled={!/0x[0-9a-fA-F]{40}/.test(draft)} onClick={addExtra} data-testid="dc-track-add">＋ Track</button>
      {data?.cronos?.checked > 0 && <small className="m-dim" data-testid="dc-cronos-meta">Cronos: {data.cronos.checked} contracts checked on-chain{data.cronos.indexed ? ' — every coin a wallet index reports for this address, plus the swap and DEX lists' : ' — lists only right now (the wallet index did not answer); paste a contract if one is missing'}{extra ? ` · ${extra.split(',').length} tracked by you` : ''}.</small>}</div>}
    {err && !addr && <p className="dc-err" role="alert">{err}</p>}
    {!addr ? <div className="dc-empty"><p className="m-dim">Connect your {chain === 'solana' ? 'Solana' : 'EVM (MetaMask, Crypto.com DeFi, Trust, Rabby…)'} wallet to read and clean its coins.</p>
      <button type="button" className="m-btn primary m-go" onClick={() => Promise.resolve(chain === 'solana' ? connect?.('solana') : connect?.('evm')).catch(e => setErr(e.message))} data-testid="dc-connect">Connect wallet</button></div>
      : <>
      <div className="dc-sum" data-testid="dc-summary">
        <span><small>Coins</small><b className="m-num">{data ? rows.length : '…'}</b></span>
        {chain === 'solana' ? <><span><small>Dust / empty</small><b className="m-num">{data?.summary?.dust ?? '…'}</b></span><span><small>Rent to win back</small><b className="m-num">◎{(data?.summary?.rentBackSol || 0).toFixed(4)}</b></span></>
          : <><span><small>Chains</small><b className="m-num">{data?.summary?.chains ?? '…'}</b></span><span><small>Wallet total</small><b className="m-num">{usd(data?.summary?.usd || 0)}</b></span></>}
        <span><small>Worth swapping</small><b className="m-num">{usd(data?.summary?.swapUsd || 0)}</b></span>
        <span className="dc-tools"><button type="button" className="m-btn" onClick={selectDust} disabled={!rows.length || busy} data-testid="dc-select-dust">Select dust</button>
          <button type="button" className="m-btn" onClick={load} disabled={busy} data-testid="dc-refresh">↻ Re-read</button></span></div>
      {canSign && rows.some(r => !r.native) && <button type="button" className="m-btn primary m-go dc-all" disabled={busy} onClick={cleanAll} data-testid="dc-clean-all">{busy ? 'Working…'
        : chain === 'solana' ? `🧹 Sell all ${allPlan.chosen.length} coins → gas — one click${allPlan.burns.length ? ` · 🔥 burns ${allPlan.burns.length} worthless (${usd(allPlan.burnUsd)})` : ''}`
          : `🧹 Sell all ${evmTodo(allPlan, evmDust).length} coins → gas — one click`}</button>}
      {busy && chain !== 'solana' && <button type="button" className="m-btn dc-stop" onClick={() => { stop.current = true; note('Stopping — no more wallet requests after the one on screen.', 'bad'); }} data-testid="dc-stop">⏹ Stop</button>}
      {canSign && chain !== 'solana' && allPlan.dust.length > 0 && <label className="dc-dustopt" data-tip="A coin worth under the swap minimum costs two wallet prompts and more gas than it returns. Off = those are left alone."><input type="checkbox" checked={evmDust} disabled={busy} onChange={e => setEvmDust(e.target.checked)} data-testid="dc-evm-dust" /> include {allPlan.dust.length} dust coin{allPlan.dust.length === 1 ? '' : 's'} (+{allPlan.dust.length * 2} wallet prompts)</label>}
      {err && <p className="dc-err" role="alert">{err}</p>}
      {!canSign && <p className="m-note dc-ro">👁 Looking only — connect this wallet to clean it.</p>}
      {!data ? <div className="dc-loading" aria-busy="true"><i /><i /><i /></div> : !rows.length ? <p className="m-dim dc-empty">No coins in this wallet — nothing to clean.</p>
        : <ul className="dc-list">{rows.map((r, i) => { const k = key(r); const a = act[k] || r.best; const st = state[k];
          const head = chain === 'evm' && (i === 0 || rows[i - 1].chain !== r.chain) ? chainUsd[r.chain] : null;
          return <React.Fragment key={k}>{head && <li className="dc-chain" data-testid={`dc-chain-head-${r.chain}`}><b>{r.chain}</b><small className="m-dim">{head.coins} coin{head.coins === 1 ? '' : 's'} · {usd(head.usd)}</small></li>}
          <li className={`dc-row ${pick[k] ? 'is-on' : ''} ${st ? `is-${st}` : ''}`} style={{ '--i': Math.min(i, 12) }}>
            <label className="dc-pick"><input type="checkbox" checked={!!pick[k]} disabled={busy || st === 'done' || r.native} onChange={e => setPick(o => ({ ...o, [k]: e.target.checked }))} aria-label={`Pick $${r.symbol}`} /></label>
            <TokenAvatar pair={{ chainId: r.chain || chain, baseToken: { address: r.mint || r.address, symbol: r.symbol }, info: { imageUrl: r.logo } }} size={26} />
            <span className="dc-coin"><b>${r.symbol}</b><small className="m-dim">{tiny(r.ui, 4)} · {r.usd == null ? 'no price' : usd(r.usd)}{r.rentSol ? ` · ◎${r.rentSol.toFixed(4)} rent` : ''}</small></span>
            {r.native ? <span className="dc-gas" data-testid={`dc-gas-${r.chain}`}>⛽ gas</span> : <select className="m-input dc-act" value={a} disabled={busy || st === 'done'} onChange={e => setAct(o => ({ ...o, [k]: e.target.value }))} aria-label={`What to do with $${r.symbol}`} data-testid={`dc-act-${r.symbol}`}>
              {(r.actions?.length ? r.actions : ['swap']).map(x => <option key={x} value={x}>{LABEL[x]}</option>)}</select>}
            <i className={`dc-st ${st || ''}`}>{st === 'done' ? '✓' : st === 'failed' ? '✕' : st ? '…' : ''}</i>
          </li></React.Fragment>; })}</ul>}
      {p.chosen.length > 0 && <div className="dc-go">
        <p>{p.swaps.length + p.dust.length ? `↩ ${p.swaps.length + p.dust.length} swap${p.swaps.length + p.dust.length === 1 ? '' : 's'} to ${chain === 'solana' ? 'SOL' : 'gas'} (${usd(p.swapUsd)})` : ''}
          {p.burns.length ? ` · 🔥 ${p.burns.length} burn${p.burns.length === 1 ? '' : 's'} (${usd(p.burnUsd)} destroyed)` : ''}
          {p.burns.length + p.closes.length ? ` · ♻ ◎${p.rentSol.toFixed(4)} rent back` : ''}</p>
        {p.burns.length > 0 && <label className="dc-ack"><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} data-testid="dc-ack" /> Burned coins are gone for good — I only burn what I don't want.</label>}
        <button type="button" className="m-btn primary m-go" disabled={busy} onClick={() => go()} data-testid="dc-go">{busy ? 'Working…' : `🧹 Clean up ${p.chosen.length}`}</button></div>}
      {log.length > 0 && <ol className="dc-log" aria-live="polite" data-testid="dc-log">{log.map(l => <li key={l.t + l.text} className={l.tone}><time>{new Date(l.t).toLocaleTimeString()}</time>{l.text}</li>)}</ol>}
    </>}
  </section>;
}
