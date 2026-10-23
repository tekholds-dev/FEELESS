import React from 'react';
import { FamilyBlock } from '../components/FamilyBlock';
import { BlockArranger } from '../components/BlockArranger';

// `?arrange` opens ✋ ARRANGE on a fixture block (build-here + drag; Save only logs)
const ARR = { canBuild: true, islandCells: 15, islandsPaid: 1, islandMp: 3000, layoutSaved: true, layout: ['town:tt', 'stand:park', 'blk:jito', 'pools', 'open', 'blk:orca', 'open'],
  buildings: [{ key: 'jito', name: 'Jito', sym: 'JitoSOL', state: 'built' }, { key: 'orca', name: 'Orca', state: 'construction' }],
  catalog: [{ key: 'jito', name: 'Jito', offer: 'stake SOL', proof: 'mint' }, { key: 'kamino', name: 'Kamino', offer: 'lend USDC · loop SOL', proof: 'kamino' }, { key: 'meteora', name: 'Meteora DLMM', offer: 'tight bins, hot fees', proof: 'none', why: 'no reader yet' }, { key: 'jupiter', name: 'Jupiter Lend', offer: 'earn on USDC', proof: 'mint' }, { key: 'raydium', name: 'Raydium CLMM', offer: 'concentrated LP', proof: 'nft' }] };

// 🧪 DEV ONLY (`/dev/block?cid=…`): a family's block page from the live backend (public read) with the Family Deck under it — no wallet.
export default function BlockHarness() {
  if (new URLSearchParams(window.location.search).has('arrange')) return <div style={{ background: '#07060a', minHeight: '100vh' }}><BlockArranger bl={ARR} busy={false} onSave={c => console.log('save', c)} onClose={() => {}} /></div>;
  const q = new URLSearchParams(window.location.search); const cid = q.get('cid') || '22376b';
  const town = q.get('town'); const lp = q.get('lp'); const layout = q.get('layout');   // 🏝 `?layout=town:tt,stand:park,pools,open,…` previews an arrangement (never saved)   // 🏗 `?lp=<wallet>` previews that wallet's LP positions as towers (read-only)   // 🏘 `?town=tt,perps,pools` previews a picked town before the backend serves one
  return <div style={{ padding: 16, background: '#07060a', minHeight: '100vh' }}>
    <FamilyBlock cid={cid} lpOwner={lp} demo={town || layout ? { ...(town ? { town: town.split(','), townMax: 6, townAll: ['tt', 'perps', 'pools', 'trades', 'vault', 'radar', 'cats', 'rep'] } : {}), ...(layout ? { layout: layout.split(',') } : {}) } : null} mine={{ id: cid, book: [{ symbol: 'DEMO', who: 'preview', usd: 2.5, ret: 0.18, holdMin: 34 }] }} tools={() => <p className="m-dim">(the seats table — live on your real family)</p>} />
  </div>;
}
