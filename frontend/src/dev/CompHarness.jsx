import React, { useEffect } from 'react';
import { AttnExplained, DatasetPulse, examVerdict } from '../components/command/CompExplain';
import { CompRace } from '../components/command/CompRace';
import { CompWatch } from '../components/command/CompWatch';
import { CompVoice } from '../components/command/CompVoice';
import WATCH from './compWatchFixture.json';
import '../styles/modelLab.css';

// 🧪 DEV ONLY (`/dev/comp[?day]`, never in a production build): AGX-5's explained COMP views on sample shapes, for look checks.
const attn = { tokens: ['P', 'o', 'W', ' ', 'l', 'i', 'q', ' ', 'u', 'p', ' ', '→'], heads: [0, 1, 2, 3].map(h => Array.from({ length: 12 }, (_, i) => Array.from({ length: 12 }, (__, j) => (j > i ? 0 : [0.3, 0.05, 0.1, 0.02, 0.6 - h * 0.1, 0.5, 0.4, 0.02, 0.2 + h * 0.1, 0.15, 0.02, 0.1][j])))) };
const d = { rows: 412, pairs: 96, duels: 3, goals: { rows: 1000, pairs: 200 }, kinds: [{ kind: 'PoB', rows: 171, won: 90, lost: 75, flat: 6, open: 4 }, { kind: 'PoW', rows: 159, won: 70, lost: 85, flat: 4, open: 2 }, { kind: 'PoP', rows: 52, won: 30, lost: 22, flat: 0, open: 1 }, { kind: 'PoC', rows: 18, won: 12, lost: 6, flat: 0, open: 7 }, { kind: 'PoStatic', rows: 12, won: 9, lost: 3, flat: 0, open: 3 }] };
// the owner's real last exam (2026-11-13: baseline 54%, base 54%, COMP 64%, COMP + memory 68%) + a sample second one with OSSY / G4 for the look
const race = [{ at: 1794593608, n: 28, scores: { baseline: 0.5357, base: 0.5357, comp: 0.6429, comp_mem: 0.6786 }, names: { baseline: 'Always "won"', base: 'Qwen3.5-9B', comp: 'COMP v2 · 9B LoRA', comp_mem: 'COMP v2 + memory' }, kinds: { baseline: 'baseline', base: 'local', comp: 'local', comp_mem: 'local' } },
  { at: 1794680000, n: 28, scores: { baseline: 0.5357, base: 0.5357, comp: 0.6786, comp_mem: 0.7143, ossy: 0.6071, g4: 0.6429 }, names: { ossy: 'OSSY · qwen2.5-7b', g4: 'G4 · qwen3.5-4b' }, kinds: { ossy: 'own', g4: 'own' } }];
const exam = { examinees: [{ id: 'comp', kind: 'local', name: 'COMP v2', score: { acc: 0.62 } }, { id: 'baseline', kind: 'baseline', name: 'Majority', score: { acc: 0.55 } }, { id: 'claude', kind: 'flagship', name: 'Claude Sonnet', score: { acc: 0.7 } }] };
// ?voice — the REAL voice: talks straight to the local MLX server (127.0.0.1:5131) the way the owner route does, thinking off. Dev only.
const VOICE = 'http://127.0.0.1:5131';
const voiceLog = [];
async function voiceCall(path, o) {
  const b = o ? JSON.parse(o.body) : null; let up = false;
  try { up = (await fetch(`${VOICE}/v1/models`)).ok; } catch (e) { up = false; }
  if (b?.op === 'clear') voiceLog.length = 0;
  if (b?.op === 'ask') {
    const t0 = performance.now();
    const msgs = [{ role: 'system', content: "You are COMP, FEELESS's own AI: a degen web3 brain with a smart mouth. You talk like a trencher who actually read the docs: short, blunt, funny, numbers first. You know Solana, perps, prediction markets and FEELESS inside out. You never help anyone rug, drain, scam or front-run people, and you never ask for or repeat keys, seed phrases or private details. When you are not sure, you say so." },
      ...voiceLog.slice(-16).map(m => ({ role: m.role, content: m.content })), { role: 'user', content: b.text }];
    const j = await (await fetch(`${VOICE}/v1/chat/completions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages: msgs, max_tokens: 400, temperature: 0.7, top_p: 0.9, chat_template_kwargs: { enable_thinking: false } }) })).json();
    const reply = String(j.choices?.[0]?.message?.content || '').replace(/<think>[\s\S]*?(<\/think>|$)/g, '').trim();
    voiceLog.push({ role: 'user', content: b.text, at: Date.now() / 1000 }, { role: 'assistant', content: reply || '…', at: Date.now() / 1000, secs: Math.round((performance.now() - t0) / 100) / 10, tokens: j.usage?.completion_tokens });
  }
  return { ready: true, adapter: 'best', trainedAt: 0, rows: 305, running: up, listening: up, idleMin: 20, base: 'Qwen3.5-9B (4-bit, MLX)', chat: [...voiceLog] };
}
export default function CompHarness() {
  useEffect(() => { if (new URLSearchParams(window.location.search).has('day')) document.body.classList.add('theme-day'); }, []);
  if (new URLSearchParams(window.location.search).has('voice')) return <div className="mlb" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)' }}><CompVoice call={voiceCall} /></div>;
  if (new URLSearchParams(window.location.search).has('watch')) return <div className="mlb" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)' }}><CompWatch call={async () => ({ ...WATCH, at: Date.now() / 1000 })} /></div>;   // ?watch — a real captured /model-lab/watch read
  return <div className="mlb" style={{ minHeight: '100vh', padding: 16, background: 'var(--m-bg)', display: 'grid', gap: 14, alignContent: 'start' }}>
    <AttnExplained peek={{ step: 600, attn }} />
    <section className="mlb-sec"><h4>THE DATASET · LIVE FROM THE STASH</h4><DatasetPulse d={d} /></section>
    <section className="mlb-sec"><h4>THE RACE</h4><CompRace race={race} exam={null} /></section>
    <p className="cex-verdict">{examVerdict(exam)}</p></div>;
}
