import { act } from 'react';
import { createRoot } from 'react-dom/client';
import ProofLive, { proofOf, proofsOf, subject } from './ProofLive';
import { SCENES, SCENE_NAME, readyScenes, pickLook, drawFrame } from '../../lib/proofFx';

jest.mock('../../lib/candles', () => { const calls = []; return { calls, fetchFeelessCandles: (...a) => { calls.push(a); return Promise.resolve({ candles: [[1, 1, 1.2, 0.9, 1.1, 5], [2, 1.1, 1.3, 1, 1.25, 7], [3, 1.25, 1.4, 1.2, 1.3, 9]] }); } }; });

test('a running proof is named from the desk state; a plain ask or nothing running is null', () => {
  expect(proofOf({ powFolder: { phase: 'scout' } }, true)).toBe('pow');
  expect(proofOf({ popFolder: {} }, true)).toBe('pop');
  expect(proofOf({ task: { proofKind: 'pos' } }, true)).toBe('pos');
  expect(proofOf({ task: {} }, true)).toBe(null);
  expect(proofOf({ task: {} }, false)).toBe(null);
});

test('no data, no scene: every view needs the run\'s real numbers or words; a run keeps its look', () => {
  expect(readyScenes('pow', {})).toHaveLength(0);
  expect(readyScenes('pow', { coins: [{ sym: 'BONK' }] }).map(f => f.name)).toEqual(['coins']);
  expect(readyScenes('pop', { roe: [1.2, -0.4] }).map(f => f.name)).toEqual(['roe']);
  expect(readyScenes('pob', { game: { home: 'NYJ', hs: 12 } }).map(f => f.name)).toEqual(['score']);
  Object.values(SCENES).flat().forEach(f => expect(typeof f.ready).toBe('function'));
  expect(pickLook('pow', 'run-1')).toEqual(pickLook('pow', 'run-1'));
});

test('the stage fetches the coin\'s real candles, shows the live vitals and hands back to the chat', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const { calls } = require('../../lib/candles');
  const show = jest.fn(); const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  await act(async () => { root.render(<ProofLive kind="pow" name="Happy" spent={0.0123} onShowChat={show}
    d={{ task: { id: 't1' }, powFolder: { phase: 'scout', sym: 'BONK', pair: 'P1', mint: 'M1', coins: [{ sym: 'BONK', mint: 'M1' }], talk: [{ by: 'A', text: 'liquidity is real' }] }, chat: [{ by: 'cats', text: 'Reading dexscreener' }] }}
    wins={[{ model: 'tencent/hy4', status: 'working', steps: [{ action: 'open', detail: 'dexscreener.com', at: 1 }], bubble: 'reading the pool' }, { model: 'z-ai/glm', status: 'idle', steps: [] }]} />); });
  expect(calls[0]).toEqual(['solana', 'P1', '1m', null, 'M1']);
  const t = host.textContent;
  expect(t).toContain('PROOF OF WORK'); expect(t).toContain('$BONK'); expect(t).toContain('reading the pool'); expect(t).toContain('Reading dexscreener');
  await act(async () => { host.querySelector('[data-testid="proof-live-chat"]').click(); });
  expect(show).toHaveBeenCalled();
  await act(async () => { root.unmount(); });
});

test('the desk picker lists every running proof (server list first) and each stage shows only its own run', () => {
  expect(proofsOf({ activeProofs: ['PoB', 'PoC'] }, false)).toEqual(['pob', 'poc']);
  expect(proofsOf({ activeProofs: ['PoB'], task: { proofKind: 'poc' } }, true)).toEqual(['pob', 'poc']);
  expect(proofsOf({ powFolder: {}, pobRun: {} }, false)).toEqual(['pow', 'pob']);
  expect(proofsOf(null, true)).toEqual([]);
  const d = { powFolder: { sym: 'BONK' }, pobRun: { topic: 'NBA tonight' } };
  expect(subject('pob', d)).toBe('NBA tonight'); expect(subject('pow', d)).toBe('$BONK');
});

// 🐞 owner 2026-11-15 screenshot: VIEW read '$' (a minified function name) and a PoB's transcript drew under the mind boxes.
test('every scene has a written name, and no scene draws when the panels leave no open band', () => {
  Object.values(SCENES).flat().forEach(f => expect(SCENE_NAME.get(f)).toMatch(/^[A-Z][a-z ]+$/));
  const calls = []; const ctx = new Proxy({}, { get: (o, k) => (k in o ? o[k] : (...a) => { calls.push(k); return { addColorStop() {} }; }), set: (o, k, v) => { o[k] = v; return true; } });
  const look = pickLook('pob', 'r'); const data = { talk: [{ mind: 0, text: 'hi' }] };
  expect(drawFrame(ctx, { w: 700, h: 470, t: 1, kind: 'pob', look, data, band: [60, 300] }).scene).toBe('Minds talking');
  expect(drawFrame(ctx, { w: 700, h: 470, t: 1, kind: 'pob', look, data, band: [60, 80] }).scene).toBe('');   // too tight: nothing drawn under the panels
});
