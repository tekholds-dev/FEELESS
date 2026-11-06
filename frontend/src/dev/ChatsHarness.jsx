import React from 'react';
import { Toaster } from 'sonner';
import { KitPick } from '../components/command/FeaturesFolder';
import EcosystemChat from '../components/EcosystemChat';

// 🧪 DEV ONLY (`/dev/chats`): the shared composer in a real room plus the kit picker, on a fake kit list. Nothing is saved.
const KITS = [['heroui', 'HeroUI', 'Polished React components', true], ['shadcn', 'shadcn/ui', 'Components you copy in', false], ['magicui', 'Magic UI', 'Animated landing page components', false], ['motion', 'Motion', 'Animation for React', false], ['daisyui', 'daisyUI', 'Tailwind themes and components', false]].map(([id, name, what, added]) => ({ id, name, what, added, site: 'https://example.com', license: 'MIT', vitals: { items: 148 } }));
let state = { kits: KITS, picks: [], mode: 'auto', max: 3 };
const work = async (_, b) => { if (b.op === 'kit_pick') state = { ...state, picks: b.text ? b.text.split(',') : [], mode: b.job, kits: state.kits.map(k => (b.text.includes(k.id) ? { ...k, added: true } : k)) }; return state; };
export default function ChatsHarness() {
  return <div style={{ minHeight: '100vh', boxSizing: 'border-box', padding: 16, background: '#060b08', color: '#e9f7ef', display: 'grid', gap: 14, alignContent: 'start' }}>
    <KitPick cat={{ id: 'dev' }} work={work} />
    <div style={{ height: 520, maxWidth: 560 }}><EcosystemChat ecosystem={{ id: 'solana', name: 'Solana' }} room="dev-room" /></div>
    <Toaster />
  </div>;
}
