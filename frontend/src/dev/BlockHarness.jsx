import React from 'react';
import { FamilyBlock } from '../components/FamilyBlock';

// 🧪 DEV ONLY (`/dev/block?cid=…`): a family's block page from the live backend (public read) with the Family Deck under it — no wallet.
export default function BlockHarness() {
  const q = new URLSearchParams(window.location.search); const cid = q.get('cid') || '22376b';
  const town = q.get('town'); const lp = q.get('lp'); const layout = q.get('layout');   // 🏝 `?layout=town:tt,stand:park,pools,open,…` previews an arrangement (never saved)   // 🏗 `?lp=<wallet>` previews that wallet's LP positions as towers (read-only)   // 🏘 `?town=tt,perps,pools` previews a picked town before the backend serves one
  return <div style={{ padding: 16, background: '#07060a', minHeight: '100vh' }}>
    <FamilyBlock cid={cid} lpOwner={lp} demo={town || layout ? { ...(town ? { town: town.split(','), townMax: 6, townAll: ['tt', 'perps', 'pools', 'trades', 'vault', 'radar', 'cats', 'rep'] } : {}), ...(layout ? { layout: layout.split(',') } : {}) } : null} mine={{ id: cid, book: [{ symbol: 'DEMO', who: 'preview', usd: 2.5, ret: 0.18, holdMin: 34 }] }} tools={() => <p className="m-dim">(the seats table — live on your real family)</p>} />
  </div>;
}
