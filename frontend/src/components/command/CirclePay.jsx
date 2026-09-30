import React, { useState } from 'react';
import { toast } from 'sonner';
import { errorText } from '../../lib/api';
import { useMoneyPulse, circleFor, refreshPulse } from '../../lib/moneyPulse';

// Pools whose wallet is a Circle wallet can't be connected in Phantom: Circle holds the key and signs on the
// server. So the owner pays here instead: type "PAY <total>", Circle sends one transfer per holder.
// Circle wallets come from the shared money pulse (one request a minute for every card).
export function useCircleWallet(call, address) {
  const { data } = useMoneyPulse(call);
  return circleFor(data, address);
}

export const payPhrase = rows => `PAY ${Math.round(rows.reduce((a, r) => a + Number(r.sol || 0), 0) * 1e6) / 1e6}`;

export function CirclePay({ call, circle, rows, path, onDone, label = 'Pay via Circle' }) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState('');
  const [busy, setBusy] = useState(false);
  if (!circle || !rows?.length) return null;
  const phrase = payPhrase(rows);
  const sol = circle.balances?.find(b => b.symbol === 'SOL')?.amount;
  const go = async () => {
    setBusy(true);
    try {
      const r = await call(path, { method: 'POST', body: JSON.stringify({ confirm: typed.trim() }) });
      if (r.failed?.length) toast.error(`Circle sent ${r.paidSol} SOL to ${r.wallets}; ${r.failed.length} failed. Retry sends only those.`);
      else toast.success(`Circle is sending ${r.paidSol} SOL to ${r.wallets} wallets.`);
      setOpen(false); setTyped(''); refreshPulse(true); onDone?.();
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(false); }
  };
  if (!open) return <button type="button" className="btn-primary circle-pay-btn" data-testid="circle-pay" onClick={() => setOpen(true)}>◎ {label}</button>;
  return <div className="m-note circle-pay" data-testid="circle-pay-confirm">
    <p><b>Circle wallet “{circle.name || 'Circle'}”</b> holds {sol ?? '?'} SOL. Circle signs {rows.length} transfer{rows.length > 1 ? 's' : ''} from it — no Phantom needed. Retries never pay the same holder twice.</p>
    <label className="m-field"><span>Type <code>{phrase}</code> to send</span><input className="m-input" autoFocus value={typed} onChange={e => setTyped(e.target.value)} placeholder={phrase} data-testid="circle-pay-input" /></label>
    <div className="m-row"><button type="button" className="m-btn primary" disabled={busy || typed.trim() !== phrase} onClick={go}>{busy ? 'Sending…' : `Send ${phrase.slice(4)} SOL`}</button><button type="button" className="m-btn" disabled={busy} onClick={() => setOpen(false)}>Cancel</button></div>
  </div>;
}
