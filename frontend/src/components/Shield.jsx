import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { getChatSession } from '../lib/chatSession';

// FEELESS Shield: a creator's signed, public launch promises — checked on-chain every 10 minutes.
// A broken promise is a permanent strike on the creator's reputation. Verification, not custody.
export function ShieldBadge({ mint }) {
  const [s, setS] = useState(null);
  useEffect(() => {
    if (!mint) return undefined;
    let alive = true;
    fetch(apiUrl(`/api/reputation/shield/${mint}`)).then(r => r.json()).then(d => alive && setS(d)).catch(() => {});
    return () => { alive = false; };
  }, [mint]);
  if (!s || s.status === 'none') return null;
  const broken = s.status === 'broken';
  const Icon = broken ? ShieldAlert : ShieldCheck;
  return <section className={`shield-badge ${s.status}`} data-testid="shield-badge">
    <header><Icon size={20} /><div><b>{broken ? 'Shield BROKEN' : s.status === 'active' ? 'FEELESS Shield active' : 'Shield kept'}</b><small>{broken ? 'The creator broke a public launch promise — permanent strike.' : s.status === 'active' ? `Promises checked on-chain · ends ${new Date(s.endsAt * 1000).toLocaleDateString()}` : 'Every promise held to the end.'}</small></div></header>
    <ul>{s.checks.map(c => <li key={c.rule} className={c.ok ? 'ok' : 'bad'}><i>{c.ok ? '✓' : '✗'}</i><span>{c.rule}</span><small>{c.detail}</small></li>)}</ul>
    {s.breaches.length > 0 && <p className="shield-breach">Broken: {s.breaches.map(b => b.rule).join(' · ')}</p>}
  </section>;
}

export function ShieldCommit({ defaultMint = '' }) {
  const { wallet, signMessage, connect } = useWallet() || {};
  const [f, setF] = useState({ mint: defaultMint, devKeepPct: 90, lockDays: 30, maxWalletPct: 5, noKnownSnipers: true });
  const [busy, setBusy] = useState(false);
  const commit = async () => {
    setBusy(true);
    try {
      if (!wallet?.address) { await connect?.('solana'); return; }
      const session = await getChatSession(wallet.address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/shield'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, ...f, devKeepPct: Number(f.devKeepPct), lockDays: Number(f.lockDays), maxWalletPct: Number(f.maxWalletPct) }) });
      const d = await r.json(); if (!r.ok) throw new Error(d.detail);
      toast.success('🛡 Shield live — FEELESS now checks your promises on-chain.');
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const set = k => e => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  return <section className="shield-commit" data-testid="shield-commit">
    <header><ShieldCheck size={22} /><div><h3>Shield your launch</h3><small>Public promises buyers can trust. FEELESS verifies them on-chain every 10 minutes — break one and it's on your record forever.</small></div></header>
    <label><small>Coin mint (Solana)</small><input value={f.mint} onChange={set('mint')} placeholder="Your token's mint address" /></label>
    <div className="shield-terms">
      <label><small>Dev keeps at least</small><div><input type="number" min="50" max="100" value={f.devKeepPct} onChange={set('devKeepPct')} /><em>% of bag</em></div></label>
      <label><small>For</small><div><input type="number" min="7" max="365" value={f.lockDays} onChange={set('lockDays')} /><em>days</em></div></label>
      <label><small>No wallet above</small><div><input type="number" min="0.5" max="20" step="0.5" value={f.maxWalletPct} onChange={set('maxWalletPct')} /><em>% supply</em></div></label>
    </div>
    <label className="shield-check"><input type="checkbox" checked={f.noKnownSnipers} onChange={set('noKnownSnipers')} /><span>No FEELESS-blocklisted snipers or bundlers among early buyers</span></label>
    <button type="button" className="btn-primary" disabled={busy || (wallet?.address && !f.mint)} onClick={commit}>{!wallet?.address ? 'Connect wallet to shield' : busy ? 'Signing…' : 'Sign & activate Shield'}</button>
    <small className="shield-note">Signed with your wallet — no funds move. Shields can't be edited or removed once live.</small>
  </section>;
}
