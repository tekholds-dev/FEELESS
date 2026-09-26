import React, { useEffect, useState } from 'react';

// Snipe-risk chip (reads only cached FEELESS intel, so lists stay fast).
const riskCache = {}; let pending = new Set(); let timer = null; const subs = new Set();
function queue(mint) {
  if (!mint || mint in riskCache) return; pending.add(mint);
  clearTimeout(timer); timer = setTimeout(() => { const batch = [...pending]; pending = new Set(); fetch(`/api/reputation/snipe-risk?mints=${batch.join(',')}`).then(r => r.json()).then(d => { batch.forEach(m => { riskCache[m] = d.risk?.[m] || null; }); subs.forEach(f => f()); }).catch(() => {}); }, 250);
}
export function SnipeRisk({ mint }) {
  const [, force] = useState(0);
  useEffect(() => { const f = () => force(x => x + 1); subs.add(f); queue(mint); return () => subs.delete(f); }, [mint]);
  const r = riskCache[mint];
  if (!r) return null;
  return <span className={`snipe-chip lvl-${r.level}`} title={`Snipe risk ${r.risk}/100 · ${r.snipers} snipers · ${r.bundled} bundled · top 10 hold ${Number(r.top10).toFixed(0)}%`}>🎯 {r.level}</span>;
}

