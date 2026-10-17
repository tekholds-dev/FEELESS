import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { snapPath, AiRow } from './AiDecisions';
import { WebSrc } from './AiChat';
import { modelsLine } from './CockpitControls';

test('📸 the chart the model read is drawn beside its answer, with its exit word', async () => {
  expect(snapPath([0, 2, -1], 120, 26).startsWith('M0.0,')).toBe(true);
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ol><AiRow r={{ at: 1, role: 'exit', symbol: 'A', mint: 'M', stance: 'NEUTRAL', summary: 'still bought', snap: [0, 1.2, 3.4, 2.1], snapSrc: 'candles', word: 'RIDE' }} /></ol>); });
  const s = el.querySelector('[data-testid="cai-snap"]');
  expect(s.className).toContain('is-up'); expect(s.textContent).toContain('+2.1%'); expect(s.textContent).toContain('RIDE');
});

test('🌐 web sources are real links; 🤝 each model shows its own exit record', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<WebSrc w={[{ title: 'T', url: 'https://www.example.com/a' }, { title: 'bad', url: 'javascript:alert(1)' }]} />); });
  const a = el.querySelectorAll('a');
  expect(a.length).toBe(1); expect(a[0].textContent).toContain('example.com'); expect(a[0].getAttribute('rel')).toContain('noopener');
  expect(modelsLine({ models: { lan: { RIDE: [4, 2.5, 0], TIGHTEN: [0, null, 0] }, local: { WIDEN: [3, -1, 0] } } })).toBe('🖥 GEMMA: RIDE 4 · +2.5%   💻 QWEN: WIDEN 3 · -1%');
});

test('🔮 predictions: a 15-minute number on each read and each model\'s graded record', async () => {
  const { PredictBox, predictWord } = require('./AiDecisions');
  expect(predictWord({ n: 30, hit: 61, err: 7.5, up: { med: 3.1 }, down: { med: -4 }, proven: true })).toContain('✅ PROVEN');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><PredictBox p={{ lan: { n: 4, hit: 50, err: 9, up: { n: 2, med: 1 }, down: { n: 2, med: -3 } } }} /><ol><AiRow r={{ at: 2, role: 'sherlock', symbol: 'B', stance: 'NEUTRAL', predict: -12 }} /></ol></>); });
  expect(el.querySelector('[data-testid="cai-predbox"]').textContent).toContain('GEMMA');
  expect(el.querySelector('[data-testid="cai-pred"]').textContent).toContain('-12% in 15m');
});
