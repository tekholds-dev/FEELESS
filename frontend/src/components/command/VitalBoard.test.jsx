import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { VitalBoard, RuleCard } from './VitalBoard';
import { vitalTiles, vitalScore } from '../../lib/vitalBoard';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../../lib/agentHub', () => ({ hubLoad: jest.fn(async () => null) }));
jest.mock('../CoinDrawer', () => ({ openCoin: jest.fn() }));

const rule = { key: 'fake candles', icon: '🕯', label: 'Fake candles', what: 'a straight run of green candles', mode: 'rank', strength: 'normal',
  knob: { key: 'run', options: [5, 8, 10], value: 8, word: 'green candles in a row' }, now: 2, examples: [{ mint: 'M1', sym: 'PAINT', why: '9 green' }], record: { n: 12, med: -9, up: 3, verdict: 'right' } };
const cand = { mint: 'M1', symbol: 'PAINT', pair: 'P1', vit: { drain: { s: 70, st: 'DRAIN', xl: 3.4, hd: -6, lq: -12, w: ['top-10 hold 3.4× the pool', 'holders -6%'] },
  tape: ['SELLERS', 120, 480], odds: [62, 410, 21, 'age:<15m'], top10: 34, bundled: 0, snipers: 9, dev: 2, d5: -9, buy: 61, rug: 55, chart: 'BOT LADDER', entry: 'SKIP', taught: { 'fake candles': '9 green candles in a row, no red' },
  soc: { grade: 'STRONG', line: '✅ site shows this exact CA + an X is set', ch: [{ k: 'site', icon: '🌐', state: 'MATCH', word: 'shows THIS exact CA', url: 'https://paint.fun' }, { k: 'x', icon: '𝕏', state: 'HIDDEN', word: 'login wall' }, { k: 'tg', icon: '💬', state: 'NONE', word: 'no Telegram' }], flags: [] } } };

test('tiles carry tone + the line + who reads it; unknown stays unknown; the score names the board', () => {
  const t = vitalTiles(cand); const by = k => t.find(x => x.key === k);
  expect(by('top10').tone).toBe('bad'); expect(by('dev').tone).toBe('good'); expect(by('d5').tone).toBe('bad'); expect(by('rug').tone).toBe('bad');
  expect(by('drain')).toMatchObject({ group: 'drain', tone: 'bad', value: 'DRAIN 70', meter: 0.7 }); expect(by('xl').tone).toBe('bad');
  expect(by('tape')).toMatchObject({ tone: 'bad', split: 0.2 }); expect(by('odds').tone).toBe('bad'); expect(by('odds').line).toContain('410 coins');
  expect(by('organic')).toBeUndefined(); expect(by('holders')).toBeUndefined(); expect(by('dq')).toBeUndefined();
  expect(vitalTiles({}).find(x => x.key === 'odds').tone).toBe('unk');
  expect(by('rule:fake candles')).toMatchObject({ group: 'rules', rule: 'fake candles', line: '9 green candles in a row, no red' });
  expect(vitalScore(t).word).toBe('RED FLAGS'); expect(vitalScore(vitalTiles({})).word).toBe('NOT READ YET');
});

test('tap a vital → its detail; a rule hit tunes the rule in place; socials list each channel with its proof', async () => {
  const call = jest.fn(async () => ({}));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<VitalBoard c={cand} rules={{ rules: [rule] }} call={call} isOwner />); });
  await act(async () => { el.querySelector('[data-testid="vital-top10"]').click(); });
  expect(el.querySelector('[data-testid="vital-detail"]').textContent).toContain('READ BY');
  await act(async () => { el.querySelector('[data-testid="vital-rule-fake-candles"]').click(); });
  await act(async () => { el.querySelector('[data-testid="rule-fake-candles-skip"]').click(); });
  expect(JSON.parse(call.mock.calls[0][1].body)).toEqual({ taughtRule: { key: 'fake candles', mode: 'skip' } });
  await act(async () => { el.querySelector('[data-testid="vital-soc"]').click(); });
  const soc = el.querySelector('[data-testid="soc-report"]');
  expect(soc.textContent).toContain('shows THIS exact CA'); expect(soc.querySelector('a').getAttribute('href')).toBe('https://paint.fun');
  await act(async () => { root.unmount(); });
});

test('a rule card shows its record and its knob, and only the owner can change it', async () => {
  const call = jest.fn(async () => ({}));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<RuleCard r={rule} call={call} isOwner={false} />); });
  expect(el.textContent).toContain('12 coins judged'); expect(el.textContent).toContain('✅ RIGHT');
  await act(async () => { el.querySelector('[data-testid="rule-fake-candles-off"]').click(); });
  expect(call).not.toHaveBeenCalled();
  await act(async () => { root.unmount(); });
});

test('🧹 unread vitals stay folded: a coin nobody read says so in one line, one tap shows every tile', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<VitalBoard c={{ mint: 'M1', symbol: 'NEW' }} call={jest.fn()} isOwner />); });
  expect(el.querySelector('[data-testid="vital-none"]')).not.toBeNull(); expect(el.querySelectorAll('.vbd-tile')).toHaveLength(0);
  await act(async () => { el.querySelector('[data-testid="vital-unread"]').click(); });
  expect(el.querySelectorAll('.vbd-tile').length).toBeGreaterThan(5); expect(el.querySelector('[data-testid="vital-none"]')).toBeNull();
  await act(async () => { root.unmount(); });
});
