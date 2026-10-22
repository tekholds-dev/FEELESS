import React, { useEffect, useState } from 'react';
import { usePresence, PRESENCE_MODES, readMode, setMode } from '../lib/presence';
import '../styles/presence.css';

// 🟢 a wallet's dot: online (green, breathing) · away (moon gold) · offline (grey)
export function PresenceDot({ address, status, label = false }) {
  const m = usePresence(status ? [] : [address]); const s = status || m[address] || 'offline';
  return <span className={`prs prs-${s}`} data-tip={s === 'online' ? 'Online now' : s === 'away' ? 'Away' : 'Offline'} data-testid="presence-dot"><i aria-hidden="true" />{label ? <em>{s}</em> : null}</span>;
}

// ⚙ your own status (profile settings): Online · Away · Invisible — remembered in this browser, applied on the next heartbeat (now)
export function PresencePicker() {
  const [m, setM] = useState(readMode);
  useEffect(() => { const f = () => setM(readMode()); window.addEventListener('feeless:presence', f); return () => window.removeEventListener('feeless:presence', f); }, []);
  return <div className="prs-pick m-seg" role="radiogroup" aria-label="Your online status" data-testid="presence-picker">{PRESENCE_MODES.map(([k, w, tip]) =>
    <button key={k} type="button" role="radio" aria-checked={m === k} className={m === k ? 'active' : ''} onClick={() => setMode(k)} data-tip={tip} data-testid={`presence-${k}`}>{w}</button>)}</div>;
}
