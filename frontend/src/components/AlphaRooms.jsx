import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { getChatSession } from '../lib/chatSession';
import EcosystemChat from './EcosystemChat';

// Holder-gated alpha rooms: $100 → $1K → $10K → $1M held in $FEE. The server enforces the gate on
// both reading and posting (signed session), so a locked room can't be peeked at through the API.
export function AlphaRooms({ compact = false }) {
  const { wallet, signMessage, connect } = useWallet() || {};
  const [d, setD] = useState(null); const [open, setOpen] = useState(null); const [ready, setReady] = useState(false);
  const address = wallet?.address;
  useEffect(() => {
    let alive = true;
    fetch(apiUrl(`/api/reputation/alpha-rooms${address ? `?address=${address}` : ''}`)).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    return () => { alive = false; };
  }, [address]);
  const enter = async r => {
    if (!address) { connect?.('solana'); return; }
    if (!r.unlocked) return;
    try { await getChatSession(address, signMessage); setReady(true); setOpen(r); } catch { /* declined */ }
  };
  const wanted = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('room') : null;
  useEffect(() => { const r = !compact && wanted && d?.rooms?.find(x => x.id === wanted); if (r?.unlocked && address) enter(r); }, [d, address]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return null;
  const held = d.holdingUsd || 0;
  // Compact strip for chat floors / profiles: one line, each pill links into the rooms page.
  if (compact) return <nav className="alpha-strip" aria-label="Holder rooms">{d.rooms.map(r => <Link key={r.id} to={`/terminal/alpha?room=${r.id}`} className={r.unlocked ? 'on' : ''}>{r.unlocked ? r.icon : <Lock size={11} />}{r.name}</Link>)}</nav>;
  return <section className="alpha-rooms" data-testid="alpha-rooms">
    <header><h3>Alpha rooms</h3><small>{address ? `You hold $${held.toLocaleString()} in $FEE` : 'Connect a wallet holding $FEE'}</small></header>
    <div className="alpha-grid">{d.rooms.map((r, i) => { const pct = Math.min(100, (held / r.minUsd) * 100); return <button key={r.id} type="button" className={`alpha-card tier-${i} ${r.unlocked ? 'unlocked' : 'locked'} ${open?.id === r.id ? 'active' : ''}`} onClick={() => enter(r)} data-testid={`alpha-${r.id}`}>
      <span className="alpha-icon">{r.unlocked ? r.icon : <Lock size={18} />}</span><b>{r.name}</b><small>{r.vibe}</small>
      {r.unlocked ? <em className="alpha-open">{r.messages} msgs · enter →</em> : <><i className="alpha-bar"><i style={{ width: `${pct}%` }} /></i><em>${Math.max(0, r.minUsd - held).toLocaleString(undefined, { maximumFractionDigits: 0 })} more $FEE to unlock</em></>}
    </button>; })}</div>
    {open && ready && <div className="alpha-room-chat"><header><b>{open.icon} {open.name}</b><button type="button" className="btn-outline" onClick={() => setOpen(null)}>Close</button></header><EcosystemChat key={open.id} compact room={open.id} ecosystem={{ id: open.id, name: open.name }} /></div>}
  </section>;
}
