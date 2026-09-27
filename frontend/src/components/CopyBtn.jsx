import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Copy, Check, UserRound } from 'lucide-react';

// Icon-only copy button that sits beside any address. Never triggers a surrounding link/row.
// `profile` adds a profile icon for wallet addresses (not token mints / pool addresses).
export function CopyBtn({ value, label = 'Copy address', profile = false }) {
  const [done, setDone] = useState(false);
  const navigate = useNavigate();
  if (!value) return null;
  const copy = e => { e.preventDefault(); e.stopPropagation(); navigator.clipboard?.writeText(value).then(() => { setDone(true); setTimeout(() => setDone(false), 1200); }).catch(() => {}); };
  const open = e => { e.preventDefault(); e.stopPropagation(); navigate(`/terminal/profile/${value}`); };
  return <>
    {profile && <button type="button" className="copy-btn profile-btn" onClick={open} title="Open FEELESS profile" aria-label="Open FEELESS profile"><UserRound size={12} /></button>}
    <button type="button" className={`copy-btn ${done ? 'done' : ''}`} onClick={copy} title={done ? 'Copied' : label} aria-label={label}>{done ? <Check size={12} /> : <Copy size={12} />}</button>
  </>;
}
