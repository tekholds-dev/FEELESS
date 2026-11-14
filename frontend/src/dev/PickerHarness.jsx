import React, { useEffect, useState } from 'react';
import ProofPicker from '../components/command/ProofPicker';

// 🧪 DEV ONLY (`/dev/picker?cat=<id>`, never in a production build): the AGX-1 proof picker on an agent's PUBLIC proofs (`/api/cats/<id>`, what a
// visitor sees) for look checks at phone width / day theme. The pot scores here are a spread for colour checks only — the desk uses the pool's real ones.
export default function PickerHarness() {
  const q = new URLSearchParams(window.location.search); const [d, setD] = useState(null);
  useEffect(() => { if (q.has('day')) document.body.classList.add('theme-day'); fetch(`/api/cats/${encodeURIComponent(q.get('cat') || '')}`).then(r => r.json()).then(j => setD(j.cat || {})).catch(() => setD({})); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const w = {}; ['powFolders', 'popFolders', 'pobFolders', 'pocFolders', 'psFolders'].forEach(k => (d?.[k] || []).forEach((f, i) => { w[f.id] = { score: 60 + (i * 37) % 200, top: 300, rank: 'SABCD'[i % 5] }; }));
  return <div style={{ position: 'fixed', inset: 0, background: 'var(--m-bg)' }}>{d ? <ProofPicker d={d} weights={w} onPick={p => console.log('pick', p)} onClose={() => {}} /> : null}</div>;
}
