import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { ProofCalc, WatchRoom, exitLadder, perpMaths, playerFor, splitThread } from './ProofRooms';
import { DeskWidgets } from './DeskWidgets';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return { el, root, q: t => el.querySelector(`[data-testid="${t}"]`) }; };
test('perp maths: liquidation, reward to risk, and a stop past liquidation is flagged', () => {
  const m = perpMaths({ size: 100, lev: 5, entry: 100, stop: 95, target: 115, long: true });
  expect(m.margin).toBe(20); expect(m.liq).toBeCloseTo(80.5); expect(m.win).toBeCloseTo(15); expect(m.loss).toBeCloseTo(-5); expect(m.rr).toBeCloseTo(3); expect(m.stopSafe).toBe(true);
  expect(perpMaths({ size: 100, lev: 50, entry: 100, stop: 95, target: 115, long: true }).stopSafe).toBe(false);
  const s = perpMaths({ size: 100, lev: 5, entry: 100, stop: 105, target: 85, long: false }); expect(s.liq).toBeCloseTo(119.5); expect(s.win).toBeCloseTo(15); expect(s.stopSafe).toBe(true);
});
test('an exit ladder counts costs both ways', () => {
  const m = exitLadder({ buy: 100, cost: 2, rungs: [[2, 50], [4, 50]] }); expect(m.out).toBeCloseTo(288); expect(m.even).toBeCloseTo(1.0417, 3);
});
test('a thread splits on words and never over the limit', () => {
  const parts = splitThread('word '.repeat(200), 50); expect(parts.every(p => p.length <= 50)).toBe(true); expect(parts.join(' ').split(' ').length).toBe(200); expect(splitThread('')).toEqual([]);
});
test('only official YouTube and Twitch players, and nothing else, ever embed', () => {
  expect(playerFor('https://www.youtube.com/watch?v=abc123DEF')).toBe('https://www.youtube-nocookie.com/embed/abc123DEF');
  expect(playerFor('https://youtu.be/abc123DEF')).toContain('/embed/abc123DEF'); expect(playerFor('https://www.youtube.com/live/abc123DEF')).toContain('/embed/abc123DEF');
  expect(playerFor('https://www.twitch.tv/espn', 'feeless.app')).toBe('https://player.twitch.tv/?channel=espn&parent=feeless.app');
  for (const bad of ['https://freestreams.example/nfl', 'javascript:alert(1)', 'nonsense', 'https://www.youtube.com/watch?v=<script>', 'https://youtube.com.evil.co/watch?v=abc123']) expect(playerFor(bad)).toBeNull();
});
test('the watch room plays a real link, refuses others, and opens services in its browser', async () => {
  const browse = jest.fn(); const { q, el, root } = await mount(<WatchRoom onBrowse={browse} />); const type = v => act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(q('prm-link'), v); q('prm-link').dispatchEvent(new Event('input', { bubbles: true })); });
  await type('https://pirate.example/game'); await act(async () => { q('prm-play').click(); }); expect(q('prm-player')).toBeNull(); expect(el.textContent).toContain('Paste a YouTube or Twitch link');
  await type('https://youtu.be/abc123DEF'); await act(async () => { q('prm-play').click(); }); expect(q('prm-player').getAttribute('src')).toContain('youtube-nocookie');
  await act(async () => { q('prm-svc-ESPN').click(); }); expect(browse).toHaveBeenCalledWith('espn.com/watch');
  await act(async () => root.unmount());
});
test('each proof folder has its tool', async () => {
  for (const [k, t] of [['pow', 'prm-coin'], ['pop', 'prm-perp'], ['content', 'prm-post']]) { const { q, root } = await mount(<ProofCalc kind={k} />); expect(q(t)).toBeTruthy(); await act(async () => root.unmount()); }
  const { el } = await mount(<ProofCalc kind="nothing" />); expect(el.textContent).toBe('');
});
test('the widgets show only real numbers and open their folder', async () => {
  const open = jest.fn(); const d = { powFolders: [{ pnlPct: 10 }, { pnlPct: -2 }], popFolders: [{ noTrade: true, roePct: 5 }], pobFolders: [{ graded: 'right' }], jobs: [{}, { done: true }], signedIn: ['a'], logins: [] };
  const { q, root } = await mount(<DeskWidgets d={d} pool={{ pool: { owedUsd: 1 }, stake: { pointsLeft: 18.7, sentUsd: 10, nowPct: 1.87 } }} openWin={open} />);
  expect(q('dwg-dash').textContent).toContain('2 / 1'); expect(q('dwg-money').textContent).toContain('18.7'); expect(q('dwg-money').textContent).toContain('1.87%');
  await act(async () => { q('dwg-money').click(); }); expect(open).toHaveBeenCalledWith('boost');
  await act(async () => root.unmount());
});
