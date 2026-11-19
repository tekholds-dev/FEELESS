import React, { useEffect } from 'react';
import '../styles/meta.css';
import '../styles/features.css';
import { SwapFiled, VideoSwapPanel } from '../components/command/VideoSwap';

// 🧪 Slice 4: the PoC video swap panel + a filed swap on fixtures (?day, ?empty, ?running). Prices come from backend/video_swap.py's own formula
// (H3 768p 10 s = $2.24, 1080p = $3.09, Aleph 10 s = $2.80, a portrait +$0.035 / +$0.07). The clips are FEELESS's own sample files.
const Q = (lines) => ({ usd: Math.round(lines.reduce((a, l) => a + l.usd, 0) * 100) / 100, lines });
const h3 = (r, u, p) => Q([{ what: `MiniMax H3 Max · Recast · 10.0 s · ${r}`, usd: u }, ...(p ? [{ what: 'New person: Seedream 5 Lite portrait', usd: 0.035 }] : [])]);
const al = p => Q([{ what: 'Runway Aleph 2 · 10.0 s', usd: 2.8 }, ...(p ? [{ what: 'New person: Gemini 3.1 Flash Image portrait', usd: 0.07 }] : [])]);
const QUOTE = { 'fal-h3-recast': { '768P': { char: h3('768p', 2.24), make: h3('768p', 2.24, 1) }, '1080P': { char: h3('1080p', 3.09), make: h3('1080p', 3.09, 1) } }, 'or-aleph': { std: { char: al(), make: al(1) } } };
const q = new URLSearchParams(window.location.search);
const PLAN = {
  engines: [{ id: 'fal-h3-recast', label: 'MiniMax H3 Max · Recast', who: 'fal.ai', why: 'Built to recast people: same clip, same sound, the new person in every shot. 5 to 30 s, up to 1080p', ready: false, env: 'FAL_KEY', minS: 5, maxS: 30, res: ['768P', '1080P'], pick: true, sound: 'kept by the engine' },
    { id: 'or-aleph', label: 'Runway Aleph 2', who: 'OpenRouter', why: "Runner-up. Edits real footage; makes no sound, so your clip's own sound is laid back. First 10 s", ready: true, keyFrom: 'Your own OpenRouter key (on your agents)', env: 'OPENROUTER_API_KEY', minS: 1, maxS: 10, res: [], runnerUp: true, sound: 'laid back from your clip' }],
  clips: q.has('empty') ? [] : [{ mid: 'mc1', url: '/media/samples/street-interview.mp4', label: 'Street interview', secs: 10, fit: { 'fal-h3-recast': '', 'or-aleph': '' }, quote: QUOTE },
    { mid: 'mc2', url: '/media/samples/street-omelette.mp4', label: 'Street omelette', secs: 10, fit: { 'fal-h3-recast': '', 'or-aleph': '' }, quote: QUOTE }],
  person: { mid: 'mp', url: '/media/samples/ai-vs-handmade.jpg', prompt: 'The folder\'s AI-made character', source: 'character' },
  allowed: true, cap: 3, dayCap: 10, daySpent: 0, res: '768P', auto: 'or-aleph',
  jobs: q.has('running') ? [{ id: 'v1', label: 'Runway Aleph 2', step: 'running', quote: { usd: 2.8 }, before: { url: '/media/samples/street-interview.mp4' } },
    { id: 'v0', label: 'MiniMax H3 Max · Recast', res: '768P', step: 'failed', why: 'Your provider account is out of credit. Nothing was charged. Top it up on the provider, then try again. (402: Insufficient balance)', quote: { usd: 2.24 } }] : [],
};
const FILED = { id: 'poc1', n: 7, cost: 2.24, swap: { engine: 'MiniMax H3 Max · Recast', res: '768p', sound: 'kept by the engine', paid: 'FEELESS key (HQ › Core, FAL_KEY)', runnerUp: 'Runway Aleph 2', tookS: 190,
  person: { source: 'made' }, before: { url: '/media/samples/street-interview.mp4' }, after: { url: '/media/samples/street-omelette.mp4' }, side: '/media/samples/hotel-lobby.mp4',
  lines: [{ what: 'MiniMax H3 Max · Recast · 10.0 s · 768p', usd: 2.24 }] } };
const realFetch = window.fetch.bind(window);
window.fetch = async (url, opts) => (String(url).includes('/vswap') ? { ok: true, json: async () => PLAN } : realFetch(url, opts));

export default function SwapHarness() {
  useEffect(() => { document.body.classList.toggle('theme-day', q.has('day')); }, []);
  return <main style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: '24px 16px', background: 'var(--m-bg)', display: 'grid', gap: 18, justifyItems: 'center' }}>
    <VideoSwapPanel cat={{ id: 'sicario' }} row={{ id: 'w1' }} work={async () => ({})} />
    <div style={{ width: 'min(1080px, 100%)' }}><SwapFiled f={FILED} /></div>
  </main>;
}
