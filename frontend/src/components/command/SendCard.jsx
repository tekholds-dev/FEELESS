import React, { useEffect, useState } from 'react';
import NumInput from '../NumInput';
import { apiUrl, cleanAmount } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';
import { agentAuthQuery } from '../../lib/chatSession';

const SOL = 'So11111111111111111111111111111111111111112';
const B58 = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
// 📤 SEND (owner 2026-11-01: "in the swap tab a way to send to another wallet, with a dropdown of my assigned wallets — family, agents"): SOL or a
// coin you hold, from YOUR wallet — dry-run first, then one approval in your wallet (lib/batchSend). Your agents' wallets are one tap away.
export function SendCard({ wallet, provider, holdings }) {
  const [mint, setMint] = useState(SOL); const [amount, setAmount] = useState(''); const [to, setTo] = useState(''); const [mine, setMine] = useState([]);
  const [status, setStatus] = useState(''); const [busy, setBusy] = useState(false); const [review, setReview] = useState(false);
  useEffect(() => { let on = true; fetch(apiUrl(`/api/cats?${agentAuthQuery()}`)).then(r => (r.ok ? r.json() : null)).then(d => on && setMine((d?.cats || []).filter(c => c.agentWallet?.address)
    .map(c => ({ label: `🤖 ${c.name} — its wallet`, address: c.agentWallet.address })))).catch(() => {}); return () => { on = false; }; }, [wallet?.address]);
  const toks = [{ mint: SOL, label: 'SOL', amount: Number((holdings || []).find(t => t.mint === SOL)?.amount || 0) },
    ...(holdings || []).filter(t => t.mint !== SOL && Number(t.amount) > 0).map(t => ({ mint: t.mint, label: t.symbol ? `$${t.symbol}` : shortAddress(t.mint), amount: Number(t.amount) }))];
  const tok = toks.find(t => t.mint === mint) || toks[0]; const n = Number(amount);
  const why = !wallet?.address ? 'Connect your wallet first.' : !B58.test(to.trim()) ? 'Pick or paste a Solana address.' : to.trim() === wallet.address ? 'That is this wallet.'
    : !(n > 0) ? 'Type an amount.' : n > tok.amount - (mint === SOL ? 0.002 : 0) ? `You hold ${tok.amount.toLocaleString(undefined, { maximumFractionDigits: 6 })} ${tok.label}${mint === SOL ? ' (0.002 kept for fees)' : ''}.` : '';
  const send = async () => { setBusy(true); setStatus('');
    try { const { batchSend } = await import('../../lib/batchSend');
      await batchSend({ provider, owner: wallet.address, mint: mint === SOL ? null : mint, recipients: [{ address: to.trim(), amount: n }], onStatus: setStatus, kind: 'send' });
      setStatus(`✓ Sent ${n} ${tok.label} to ${shortAddress(to.trim())}`); setAmount(''); setReview(false); }
    catch (e) { setStatus(`✗ ${e.message}`); } finally { setBusy(false); } };
  return <div className="jup-send" data-testid="swap-send">
    <div className="jup-panel"><div className="jup-panel-head"><small>You send</small><span className="jup-bal">Balance {tok.amount.toLocaleString(undefined, { maximumFractionDigits: 6 })}</span></div>
      <div className="jup-row"><select className="m-input jup-send-tok" value={mint} onChange={e => setMint(e.target.value)} aria-label="Coin to send" data-testid="send-token">{toks.map(t => <option key={t.mint} value={t.mint}>{t.label}</option>)}</select>
        <NumInput className="jup-amount" data-testid="send-amount" type="text" inputMode="decimal" placeholder="0.00" aria-label="Amount to send" value={amount} onChange={e => setAmount(cleanAmount(e.target.value))} /></div></div>
    <div className="jup-panel"><div className="jup-panel-head"><small>To</small></div>
      {mine.length ? <select className="m-input" value={mine.some(m => m.address === to) ? to : ''} onChange={e => setTo(e.target.value)} aria-label="One of your wallets" data-testid="send-mine">
        <option value="">Your wallets & agents…</option>{mine.map(m => <option key={m.address} value={m.address}>{m.label} · {shortAddress(m.address)}</option>)}</select> : null}
      <input className="m-input" placeholder="…or paste any Solana address" value={to} onChange={e => setTo(e.target.value.trim())} aria-label="Recipient address" data-testid="send-to" spellCheck={false} /></div>
    {why ? <p className="jup-send-why">{why}</p> : null}
    {!review ? <button type="button" className="m-btn m-go jup-send-go" disabled={!!why || busy} onClick={() => setReview(true)} data-testid="send-review">Review send</button>
      : <div className="jup-send-review" data-testid="send-confirm"><span>Send <b>{n} {tok.label}</b> to <code>{shortAddress(to.trim())}</code>? It's simulated first, then your wallet asks once.</span>
        <button type="button" className="m-btn" onClick={() => setReview(false)} disabled={busy}>Back</button><button type="button" className="m-btn m-go" onClick={send} disabled={busy || !!why} data-testid="send-go">{busy ? 'Sending…' : 'Send'}</button></div>}
    {status ? <p className="jup-send-status" role="status">{status}</p> : null}
  </div>;
}
