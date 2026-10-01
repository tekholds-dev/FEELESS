import React, { useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { getChatSession } from '../lib/chatSession';
import { useBadges } from './terminal/Badges';

// Chat ⚙ › "Your badges in chat": tap the earned badges you want next to your name (up to the chat limit).
// Saves only that list (signed by your chat session); everyone sees it on your next message.
export function ChatBadgePicker({ wallet, signMessage, featured = [], limit = 3, onSaved }) {
  const earned = useBadges(wallet?.address) || [];
  const [pick, setPick] = useState(featured);
  const [busy, setBusy] = useState(false);
  if (!wallet?.address || !earned.length) return null;
  const toggle = async id => {
    const next = pick.includes(id) ? pick.filter(x => x !== id) : [...pick, id].slice(-limit);
    setPick(next); setBusy(true);
    try {
      const session = await getChatSession(wallet.address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/profile/featured-badges'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, badges: next }) });
      if (!r.ok) throw new Error('Could not save your badges.');
      const d = await r.json(); setPick(d.featuredBadges); onSaved?.(d.featuredBadges);
    } catch (e) { toast.error(e.message); setPick(pick); } finally { setBusy(false); }
  };
  return <div className="chat-theme-pick" data-testid="chat-badge-picker"><span>Your badges in chat · {pick.length}/{limit}</span>
    <div className="m-row">{earned.map(b => <button key={b.id} type="button" className={`m-chip ${pick.includes(b.id) ? 'ok' : ''}`} aria-pressed={pick.includes(b.id)} disabled={busy} title={b.why || b.label} data-testid={`chat-badge-${b.id}`} onClick={() => toggle(b.id)}>{b.icon ? `${b.icon} ` : ''}{b.label || b.id}</button>)}</div></div>;
}
