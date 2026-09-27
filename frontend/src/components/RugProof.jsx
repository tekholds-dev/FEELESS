import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';

// Three on-chain checks: mint can't inflate, holders can't be frozen, liquidity can't be pulled.
// All three → RUG-PROOF badge; otherwise a compact checklist so buyers see exactly what's open.
export function RugProof({ mint }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    if (!mint || mint.startsWith('0x')) { setD(null); return undefined; }
    let alive = true;
    fetch(apiUrl(`/api/reputation/rugproof/${mint}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setD(x)).catch(() => {});
    return () => { alive = false; };
  }, [mint]);
  if (!d) return null;
  const rows = [['Mint revoked', d.mintRevoked], ['Freeze revoked', d.freezeRevoked], ['LP locked forever', d.lpLocked.ok]];
  return <span className={`rugproof ${d.rugProof ? 'ok' : ''}`} title={rows.map(([l, ok]) => `${ok ? '✓' : '✗'} ${l}`).join('\n') + `\n${d.lpLocked.how}`} data-testid="rugproof">
    {d.rugProof ? '🛡 RUG-PROOF' : rows.map(([l, ok]) => <i key={l} className={ok ? 'y' : 'n'}>{ok ? '✓' : '✗'} {l.split(' ')[0]}</i>)}
  </span>;
}
