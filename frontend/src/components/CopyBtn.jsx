import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

// Icon-only copy button that sits beside any address. Never triggers a surrounding link/row.
export function CopyBtn({ value, label = 'Copy address' }) {
  const [done, setDone] = useState(false);
  if (!value) return null;
  const copy = e => { e.preventDefault(); e.stopPropagation(); navigator.clipboard?.writeText(value).then(() => { setDone(true); setTimeout(() => setDone(false), 1200); }).catch(() => {}); };
  return <button type="button" className={`copy-btn ${done ? 'done' : ''}`} onClick={copy} title={done ? 'Copied' : label} aria-label={label}>{done ? <Check size={12} /> : <Copy size={12} />}</button>;
}
