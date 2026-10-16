import React, { useState } from 'react';
import { toast } from 'sonner';

// ⧉ copy a coin's CA — one tap anywhere in the Agents tab. A span (not a button): it sits inside clickable seat cards / rows,
// so it stops the click from also opening the coin, and works with Enter / Space.
export function CopyCa({ mint, sym, testid }) {
  const [done, setDone] = useState(false);
  if (!mint) return null;
  const go = e => {
    e.stopPropagation(); e.preventDefault();
    Promise.resolve(navigator.clipboard?.writeText(mint)).then(() => { setDone(true); toast.success(`${sym ? `$${sym} ` : ''}CA copied`); setTimeout(() => setDone(false), 1200); })
      .catch(() => toast.error('copy failed'));
  };
  return <span role="button" tabIndex={0} className={`cca ${done ? 'is-done' : ''}`} data-testid={testid || 'copy-ca'} data-tip={`Copy CA · ${mint}`}
    onClick={go} onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && go(e)}>{done ? '✓' : '⧉'}</span>;
}
