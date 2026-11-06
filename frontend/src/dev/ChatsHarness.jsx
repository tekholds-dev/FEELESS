import React, { useEffect, useState } from 'react';
import { Toaster } from 'sonner';
import { ChatCost, KitPick, LiveCode } from '../components/command/FeaturesFolder';
import EcosystemChat from '../components/EcosystemChat';
import { HoneyTanks } from '../components/command/HoneyTanks';
import { SplitBars } from '../components/command/CollectiveOwner';
import { Signal } from '../components/command/CollectiveLanding';

// 🧪 DEV ONLY (`/dev/chats`): the shared composer in a real room plus the kit picker, on a fake kit list. Nothing is saved.
const KITS = [['heroui', 'HeroUI', 'Polished React components', true], ['shadcn', 'shadcn/ui', 'Components you copy in', false], ['magicui', 'Magic UI', 'Animated landing page components', false], ['motion', 'Motion', 'Animation for React', false], ['daisyui', 'daisyUI', 'Tailwind themes and components', false]].map(([id, name, what, added]) => ({ id, name, what, added, site: 'https://example.com', license: 'MIT', vitals: { items: 148 } }));
let state = { kits: KITS, picks: [], mode: 'auto', max: 3 };
const work = async (_, b) => { if (b.op === 'kit_pick') state = { ...state, picks: b.text ? b.text.split(',') : [], mode: b.job, kits: state.kits.map(k => (b.text.includes(k.id) ? { ...k, added: true } : k)) }; return state; };
const PAGE = Array.from({ length: 60 }, (_, i) => `<section class="row-${i}"><h2>Rapid compound rewards ${i}</h2></section>`).join('\n');
const Money = () => <div className="cll" style={{ minHeight: '100vh', padding: 16, background: '#060914', color: '#e8efff', display: 'grid', gap: 16, alignContent: 'start' }}>
    <HoneyTanks ledger={{ earnedSol: 0.000074, owedSol: 0.000008, owedCount: 2, transferredSol: 0, distributedSol: 0 }} live={{ right: 3, graded: 4 }} px={92} />
    <SplitBars c={{ potPct: 40, sitePct: 20 }} />
    <Signal />
  </div>;
export default function ChatsHarness() {
  return window.location.search.includes('money') ? <Money /> : <Chats />;
}
function Chats() {
  const [n, setN] = useState(1);
  useEffect(() => { const t = setInterval(() => setN(x => (x >= 4 ? 1 : x + 1)), 3000); return () => clearInterval(t); }, []);
  return <div style={{ minHeight: '100vh', boxSizing: 'border-box', padding: 16, background: '#060b08', color: '#e9f7ef', display: 'grid', gap: 14, alignContent: 'start' }}>
    <KitPick cat={{ id: 'dev' }} work={work} />
    <div style={{ maxWidth: 360 }}><ChatCost doc={{ cost: 0.0148, lastCost: 0.0031, busy: { spent: 0.0012 * n } }} /></div>
    <div style={{ height: 220, maxWidth: 700, border: '1px solid #ffffff1f', borderRadius: 12, overflow: 'hidden' }}><LiveCode draft={PAGE.slice(0, n * 800)} by="Mind A" stage="build" /></div>
    <div style={{ height: 520, maxWidth: 560 }}><EcosystemChat ecosystem={{ id: 'solana', name: 'Solana' }} room="dev-room" /></div>
    <Toaster />
  </div>;
}
