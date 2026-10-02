import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { readChatSession } from '../lib/chatSession';
import { getSolPrice } from '../lib/solPrice';

// 🔁 Card rounds: every card runs 5 auto rounds (rotation / buy-back alerts). +5 = pay now (one SOL transfer YOU sign to the
// fee wallet, checked on-chain) or — when HQ allows it — let the card's compound pay (owed until the next profit take).
let pricing = null;
const loadPricing = () => (pricing ||= fetch(apiUrl('/api/reputation/fees/pricing')).then(r => (r.ok ? r.json() : {})).catch(() => ({}))).then(p => p?.rounds || null);
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'Failed'); return j; });

export function CardRounds({ card, onChange }) {
  const { wallet, provider } = useWallet() || {};
  const [cfg, setCfg] = useState(null); const [busy, setBusy] = useState('');
  useEffect(() => { let alive = true; loadPricing().then(c => alive && setCfg(c)); return () => { alive = false; }; }, []);
  const left = card.roundsLeft ?? 5; const used = card.roundsUsed || 0; const owed = card.roundsOwedUsd || 0;
  const unlimited = left > 1000;
  const send = async (mode, usd) => {
    const addr = wallet?.address; const session = addr && readChatSession(addr);
    if (!session) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    setBusy(mode);
    try {
      let signature = '';
      if (mode !== 'compound' && usd > 0) {
        if (!cfg?.payTo) throw new Error('Fee wallet not set yet — try again later.');
        const sol = usd / ((await getSolPrice()) || 0);
        if (!(sol > 0)) throw new Error('No SOL price right now — try again in a minute.');
        const { batchSend } = await import('../lib/batchSend');
        [signature] = await batchSend({ provider, owner: addr, recipients: [{ address: cfg.payTo, amount: Number(sol.toFixed(9)) }], kind: 'card-rounds' });
      }
      const r = await post('/api/reputation/fuses/rounds', { address: addr, session, id: card.id, mode, signature });
      toast.success(mode === 'settle' ? '✓ Round pack paid' : `🔁 +${cfg?.step || 5} rounds — ${r.roundsLeft} left`); onChange?.(r);
    } catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  if (!cfg) return null;
  const total = Math.max(5, left + used);
  return <section className={`ce-rounds ${left === 0 && !unlimited ? 'is-out' : ''}`} data-testid={`rounds-${card.id}`}>
    <span className="m-label">🔁 AUTO ROUNDS</span>
    {unlimited ? <small className="m-dim">FEELESS card · unlimited rounds</small> : <>
      <span className="ce-rdots" aria-label={`${left} of ${total} rounds left`}>{Array.from({ length: Math.min(total, 20) }, (_, i) => <i key={i} className={i < used ? 'is-used' : ''} style={{ '--i': i }} />)}</span>
      <b className="m-num fl-tick" key={left}>{left} left</b>
      <small className="m-dim">Each rotation or buy-back alert uses 1 round. +{cfg.step} for ${cfg.per5Usd.toFixed(2)}{cfg.compoundPay ? ', or let the card\'s compound pay it (owed until your next profit take)' : ''}.</small>
      <span className="ce-racts">
        <button type="button" className="m-btn primary" disabled={!!busy} onClick={() => send('pay', cfg.per5Usd)} data-testid="rounds-pay">{busy === 'pay' ? '…' : cfg.per5Usd > 0 ? `💳 +${cfg.step} · $${cfg.per5Usd.toFixed(2)}` : `🔁 +${cfg.step} free`}</button>
        {cfg.compoundPay && cfg.per5Usd > 0 && <button type="button" className="m-btn" disabled={!!busy || owed > 0} onClick={() => send('compound')} data-tip="Rounds start now; the card owes the price until your next profit take" data-testid="rounds-compound">♻ Compound pays</button>}
        {owed > 0 && <button type="button" className="m-btn" disabled={!!busy} onClick={() => send('settle', owed)} data-testid="rounds-settle">Settle ${owed.toFixed(2)} owed</button>}
      </span></>}
  </section>;
}
