import React, { useEffect } from 'react';
import { AttnExplained, DatasetPulse, examVerdict } from '../components/command/CompExplain';
import '../styles/modelLab.css';

// 🧪 DEV ONLY (`/dev/comp[?day]`, never in a production build): AGX-5's explained COMP views on sample shapes, for look checks.
const attn = { tokens: ['P', 'o', 'W', ' ', 'l', 'i', 'q', ' ', 'u', 'p', ' ', '→'], heads: [0, 1, 2, 3].map(h => Array.from({ length: 12 }, (_, i) => Array.from({ length: 12 }, (__, j) => (j > i ? 0 : [0.3, 0.05, 0.1, 0.02, 0.6 - h * 0.1, 0.5, 0.4, 0.02, 0.2 + h * 0.1, 0.15, 0.02, 0.1][j])))) };
const d = { rows: 412, pairs: 96, duels: 3, goals: { rows: 1000, pairs: 200 }, kinds: [{ kind: 'PoB', rows: 171, won: 90, lost: 75, flat: 6, open: 4 }, { kind: 'PoW', rows: 159, won: 70, lost: 85, flat: 4, open: 2 }, { kind: 'PoP', rows: 52, won: 30, lost: 22, flat: 0, open: 1 }, { kind: 'PoC', rows: 18, won: 12, lost: 6, flat: 0, open: 7 }, { kind: 'PoStatic', rows: 12, won: 9, lost: 3, flat: 0, open: 3 }] };
const exam = { examinees: [{ id: 'comp', kind: 'local', name: 'COMP v2', score: { acc: 0.62 } }, { id: 'baseline', kind: 'baseline', name: 'Majority', score: { acc: 0.55 } }, { id: 'claude', kind: 'flagship', name: 'Claude Sonnet', score: { acc: 0.7 } }] };
export default function CompHarness() {
  useEffect(() => { if (new URLSearchParams(window.location.search).has('day')) document.body.classList.add('theme-day'); }, []);
  return <div className="mlb" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)', display: 'grid', gap: 14, alignContent: 'start' }}>
    <AttnExplained peek={{ step: 600, attn }} />
    <section className="mlb-sec"><h4>THE DATASET · LIVE FROM THE STASH</h4><DatasetPulse d={d} /></section>
    <p className="cex-verdict">{examVerdict(exam)}</p></div>;
}
