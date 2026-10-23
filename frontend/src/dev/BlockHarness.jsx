import React from 'react';
import { FamilyBlock } from '../components/FamilyBlock';

// 🧪 DEV ONLY (`/dev/block?cid=…`): a family's block page from the live backend (public read) with the Family Deck under it — no wallet.
export default function BlockHarness() {
  const q = new URLSearchParams(window.location.search); const cid = q.get('cid') || '22376b';
  const town = q.get('town');   // 🏘 `?town=tt,perps,pools` previews a picked town before the backend serves one
  return <div style={{ padding: 16, background: '#07060a', minHeight: '100vh' }}>
    <FamilyBlock cid={cid} demo={town ? { town: town.split(','), townMax: 6, townAll: ['tt', 'perps', 'pools', 'trades', 'vault', 'radar', 'cats', 'rep'] } : null} mine={{ id: cid, book: [{ symbol: 'DEMO', who: 'preview', usd: 2.5, ret: 0.18, holdMin: 34 }] }} tools={() => <p className="m-dim">(the seats table — live on your real family)</p>} />
  </div>;
}
