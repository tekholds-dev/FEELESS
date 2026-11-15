import React from 'react';
import ProofLive from '../components/command/ProofLive';
import '../styles/meta.css';

// 🧪 DEV ONLY (`/dev/stage`): the live proof stage beside the chat, as a PoB (no step row) and a PoW (step row), on fixture runs.
const wins = [{ model: 'tencent/hy4', status: 'working', bubble: 'Starting Yahoo site search for Mavericks Celtics rest travel', steps: [{ action: 'open', detail: 'https://sports.yahoo.com', at: 1, said: 'Reading the markets in its own windows first' }, { action: 'read', detail: 'https://sports.yahoo.com/nba', at: 2, said: 'Celtics to win headline, no odds yet' }] },
  { model: 'openai/gpt-6.1-terra', status: 'done', bubble: 'diverted to sports.yahoo.com — no repeats', steps: [{ action: 'open', detail: 'https://cbssports.com', at: 1, said: 'CBS has the Celtics favoured' }] }];
const chat = [{ by: 'cats', text: '🌐 Researching Mavericks vs Celtics: sports.yahoo.com, cbssports.com, oddsshark.com and more, in its own windows. Snapshots go in the folder.' }];
export default function StageHarness() {
  return <main style={{ minHeight: '100vh', padding: 16, display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 730px))', background: 'var(--m-bg)', color: 'var(--m-text)' }}>
    <section style={{ height: 480, display: 'grid' }}><ProofLive kind="pob" name="Happy Assistant" spent={0.0321} wins={wins} d={{ task: { id: 't1', proofKind: 'pob' }, pobRead: { topic: 'Mavericks vs Celtics' }, chat }} onShowChat={() => {}} /></section>
    <section style={{ height: 480, display: 'grid' }}><ProofLive kind="pow" name="Happy Assistant" spent={0.0123} wins={wins} d={{ task: { id: 't2' }, powFolder: { phase: 'scout', sym: 'BONK', coins: [{ sym: 'BONK' }], talk: [{ by: 'A', text: 'liquidity is real' }] }, chat }} onShowChat={() => {}} /></section>
  </main>;
}
