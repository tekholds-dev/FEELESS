import React, { useState } from 'react';
import StreetChat from '../components/StreetChat';

// 🧪 DEV ONLY (`/dev/street?heat=3&city=fee`): THE STREETS on a fixture read (no sign-in) — receipts with mini charts, the hits tape, heat, slow mode.
const now = Date.now(); const s = Math.floor(now / 1000);
const FAM = { id: 'c1', tag: 'SIC', name: 'Sicario', color: '#d4af37', badge: { shape: 'heater', c1: '#d4af37', c2: '#7a0f1f', tag: 'SIC' } };
const BNK = { id: 'c2', tag: 'BNK', name: 'Bonkers', color: '#ff5fa2', badge: { shape: 'round', c1: '#ff5fa2', c2: '#2a0a1a', tag: 'BNK' } };
const trail = (xs) => xs.map((x, i) => [s - 7200 + i * 600, x]);
const read = heat => ({ room: 'city-fee', reacts: ['🔥', '💀', '🫡', '💰'], hereN: 9, mod: { staff: true, don: true, famId: 'c1' }, slowChoices: [0, 10, 30, 60],
  slow: heat >= 2 ? { sec: 30, by: '[SIC] Don Vito', left: 1500, wait: 0 } : null,
  here: [{ address: 'w1', name: 'Don Vito', fam: { ...FAM, don: true } }, { address: 'w2', name: 'kid', fam: FAM }, { address: 'w3', name: 'pinky', fam: BNK }, { address: 'w4', name: 'lurker', fam: null }],
  vitals: { spark: [1, 0, 2, 3, 2, 5, 4, 6, 9, 7, 11, 14].map(v => v * (heat + 1) / 2), hour: [2, 9, 30, 64][heat], families: ['SIC', 'BNK'], heat,
    hot: { symbol: 'WIF', peakX: 3.1, x: 2.4, by: 'kid', fam: 'SIC' } },
  hits: [{ symbol: 'WIF', peakX: 3.1, x: 2.4, by: 'kid', ago: 4200, pairAddress: 'P1', chain: 'solana', fam: { tag: 'SIC', color: '#d4af37' } },
    { symbol: 'BONK', peakX: 2.2, x: 1.4, by: 'pinky', ago: 900, pairAddress: 'P2', chain: 'solana', fam: { tag: 'BNK', color: '#ff5fa2' } },
    { symbol: 'POPCAT', peakX: 1.7, x: 0.9, by: 'lurker', ago: 300, pairAddress: 'P3', chain: 'solana', fam: null }],
  pinned: null, typing: ['pinky', 'kid'],
  lines: [
    { id: 'l1', ts: now - 3600e3, name: 'kid', handle: 'kid', text: '📞 CALL $WIF — germ floor held, buyers stacking', fam: FAM, reacts: { '🔥': { n: 7 }, '💰': { n: 3 } },
      calls: [{ symbol: 'WIF', x: 2.4, peakX: 3.1, mcAtCall: 1.2e6, pairAddress: 'P1', chain: 'solana', trail: trail([1, 1.3, 1.9, 2.6, 3.1, 2.7, 2.5, 2.4]) }] },
    { id: 'l2', ts: now - 1500e3, name: 'pinky', text: '@kid ok that one ran. $BONK next?', fam: BNK, atMe: true, reacts: { '🫡': { n: 2 } },
      calls: [{ symbol: 'BONK', x: 1.4, peakX: 2.2, mcAtCall: 8.4e5, pairAddress: 'P2', chain: 'solana', trail: trail([1, 1.1, 1.6, 2.2, 1.8, 1.5, 1.4]) }] },
    { id: 'l3', ts: now - 400e3, name: 'lurker', text: 'aped $POPCAT at the top, rug watch on', fam: null,
      calls: [{ symbol: 'POPCAT', x: 0.62, peakX: 1.05, mcAtCall: 3.1e6, pairAddress: 'P3', chain: 'solana', trail: trail([1, 1.05, 0.9, 0.8, 0.7, 0.62]) }] },
    { id: 'l4', ts: now - 60e3, name: 'Don Vito', text: '🛡 RALLY — [SIC] hold the block', fam: { ...FAM, don: true }, mine: true, reacts: { '🫡': { n: 5, mine: true } } },
    { id: 'l5', ts: now - 30e3, name: 'pinky', text: 'kid that WIF call was clean, holding mine', parentId: 'l1', fam: BNK }] });
export default function StreetHarness() {
  const q = new URLSearchParams(window.location.search);
  const [heat, setHeat] = useState(Math.max(0, Math.min(3, Number(q.get('heat') ?? 2))));
  const city = q.get('city') || 'fee';
  if (!window.__streetFetch) {
    window.__streetFetch = window.fetch;
    window.fetch = (u, o) => (String(u).includes('/familia/street/') && !o ? Promise.resolve({ ok: true, json: () => Promise.resolve(read(window.__heat ?? 2)) }) : Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }));
  }
  window.__heat = heat;
  return <div style={{ minHeight: '100vh', boxSizing: 'border-box', padding: 16, background: '#050407', color: '#f3e6c4', display: 'grid', gap: 10, alignContent: 'start' }}>
    <div className="m-seg" role="group" aria-label="heat">{[0, 1, 2, 3].map(h => <button key={h} type="button" className={h === heat ? 'active' : ''} onClick={() => setHeat(h)}>heat {h}</button>)}</div>
    <div style={{ maxWidth: 760, width: '100%' }}><StreetChat key={heat} city={city} name="FEE CITY" addr="DEV" sess="dev" /></div>
  </div>;
}
