import React, { useEffect, useState } from 'react';
import { Toaster } from 'sonner';
import { ChatCost, KitPick, LiveCode } from '../components/command/FeaturesFolder';
import EcosystemChat from '../components/EcosystemChat';
import { HoneyTanks } from '../components/command/HoneyTanks';
import { DealFlow } from '../components/command/CollectiveOwner';
import { Signal } from '../components/command/CollectiveLanding';
import { GitFolder } from '../components/command/GitFolder';
import { FolderRidge } from '../components/command/ProofKit';

// 🧪 DEV ONLY (`/dev/chats`): the shared composer in a real room plus the kit picker, on a fake kit list. Nothing is saved.
const KITS = [['heroui', 'HeroUI', 'Polished React components', true], ['shadcn', 'shadcn/ui', 'Components you copy in', false], ['magicui', 'Magic UI', 'Animated landing page components', false], ['motion', 'Motion', 'Animation for React', false], ['daisyui', 'daisyUI', 'Tailwind themes and components', false]].map(([id, name, what, added]) => ({ id, name, what, added, site: 'https://example.com', license: 'MIT', vitals: { items: 148 } }));
KITS.push({ id: 'new-base-ui', name: '@base-ui/react', what: 'Unstyled UI components', added: false, found: true, site: 'https://base-ui.com', license: 'MIT', kinds: ['pos'] });
let state = { kits: KITS, picks: [], mode: 'auto', max: 3 };
const work = async (_, b) => { if (b.op === 'kit_pick') state = { ...state, picks: b.text ? b.text.split(',') : [], mode: b.job, kits: state.kits.map(k => (b.text.includes(k.id) ? { ...k, added: true } : k)) }; return state; };
const PAGE = Array.from({ length: 60 }, (_, i) => `<section class="row-${i}"><h2>Rapid compound rewards ${i}</h2></section>`).join('\n');
const Money = () => <div className="cll" style={{ minHeight: '100vh', padding: 16, background: '#060914', color: '#e8efff', display: 'grid', gap: 16, alignContent: 'start' }}>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14 }} data-testid="dev-prints">{['pow', 'pop', 'pob', 'poc', 'pos', 'poe'].flatMap(k => [1, 2].map(n => <span key={k + n} style={{ display: 'grid', justifyItems: 'center', fontSize: 11 }}><FolderRidge fid={`${k}${n}a`} kind={k} size={84} />{k}</span>))}</div>
    <HoneyTanks ledger={{ earnedSol: 0.000074, owedSol: 0.000008, owedCount: 2, transferredSol: 0, distributedSol: 0 }} live={{ right: 3, graded: 4 }} px={92} />
    <DealFlow c={{ collectivePoolPct: 20 }} cutsPct={6} />
    <Signal />
  </div>;
function Git() {   // ?git: this machine's real files from public/dev-git.json (gitignored). Nothing leaves the page
  const [d, setD] = useState(null);
  useEffect(() => { fetch('/dev-git.json').then(r => r.json()).then(setD); }, []);
  if (!d) return null;
  const shot = 'snapshots/rugcheck/sample.jpg';
  const fake = async (_, b) => (b.op === 'git_state' ? { files: d.files, link: {}, tree: [], sealed: true, sort: { on: true, counts: { good: 12, bad: 3, disputed: 1, trash_ask: 1, unsorted: 28 }, items: { [shot]: { status: 'trash_ask', votes: { ossy: { verdict: 'trash', why: 'A bot check, nothing readable' }, g4: { verdict: 'trash', why: 'Blank page behind a check' } } } } } } : b.op === 'git_read' ? d.read[b.job] : b.op === 'sort_set' ? { item: b.tools } : b.op === 'sort_trash' ? { item: { status: b.on ? 'trash' : 'bad', by: 'owner' } } : b.op === 'kit_list' || b.op === 'kit_pick' ? work(_, b) : {});
  return <div style={{ minHeight: '100vh', padding: 12, background: '#060b08' }}><GitFolder cat={{ id: 'dev', handle: 'dev' }} work={fake} scope="collective" /></div>;
}
export default function ChatsHarness() {
  if (window.location.search.includes('git')) return <Git />;
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
