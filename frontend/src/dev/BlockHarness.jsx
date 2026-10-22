import React from 'react';
import { FamilyBlock } from '../components/FamilyBlock';

// 🧪 DEV ONLY (`/dev/block?cid=…`): a family's block page from the live backend (public read) with the Family Deck under it — no wallet.
export default function BlockHarness() {
  const cid = new URLSearchParams(window.location.search).get('cid') || '22376b';
  return <div style={{ padding: 16, background: '#07060a', minHeight: '100vh' }}>
    <FamilyBlock cid={cid} mine={{ id: cid, book: [{ symbol: 'DEMO', who: 'preview', usd: 2.5, ret: 0.18, holdMin: 34 }] }} tools={() => <p className="m-dim">(the seats table — live on your real family)</p>} />
  </div>;
}
