import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentDesk } from './AgentDesk';
import { heat, reasonsOf, scopeOf, docketOf, listFor, CardNow, GrowthCards, PowerLadder } from './AgentScreens';

const row = (mint, symbol, d5, lean, trig, dev, go, drivers, rug) => ({ mint, symbol, pair: `P${mint}`, go, nums: { d5, pace: 2, buy: 60 }, why: { lean, drivers }, trigger: [trig, 'why t'], devil: [dev, dev === 'object' ? 'its read is BOND RUN' : ''], vitals: { top10: 40, rug, organic: 3 } });
const table = [row('A', 'GOOD', 4, 2.4, 'enter', 'agree', true, [['surge', 1, 'volume surging'], ['buyers', 0.5, 'buyers in charge']], 10),
  row('B', 'RUN', 9, 1.9, 'enter', 'object', false, [['surge', 1, 'volume surging'], ['swarm', -1, 'copy-paste callers']], 70), row('C', 'MEH', -2, 0.2, 'wait', '—', false, [], 20)];
const view = { agents: [['tally', '📊', 'Tally'], ['sherlock', '🔍', 'Sherlock'], ['trigger', '⏱', 'Trigger'], ['devil', '⚖', 'Devil']].map(([key, icon, name]) => ({ key, icon, name, job: 'job', n: 12, med: 1, right: 55 })),
  stage: { h: 5, conquered: [], needN: 30, needWin: 55 }, desk: { start: 20, now: 20, x: 1, best: 1, busts: 0, trades: 0 }, road: { pct: 3, paper: { done: false, x: 1, need: 10, n: 0, needN: 30 }, real: { open: false, n: 0, needN: 10 } },
  bar: 1.5, perf: { tally: 1, sherlock: 2, trigger: 1, devil: 1, coins: 3, at: Date.now() / 1000 - 10 }, tasks: { tally: 'read 3 coins' }, life: {}, thoughts: [], table, cfg: { agentLearn: true },
  growth: { tally: { level: 2, icon: '🧒', name: 'Rookie', xp: 40, next: 60, nextName: '🦾 Veteran', pct: 33, earned: 57, gen: 1, stunted: false, genes: [], skills: [], scars: 0 },
    sherlock: { level: 1, icon: '🐣', name: 'Hatchling', xp: 44, next: 30, nextName: '🧒 Rookie', pct: 0, earned: 31, gen: 2, stunted: true, genes: ['callers piling in (-6%)'], skills: [], scars: 1 } },
  power: { seats: 1, held: 1, steps: [{ key: 'learn', icon: '🎓', seats: 1, on: true, done: true, pct: 100, need: 'your switch' }, { key: 'trust', icon: '🤝', seats: 2, on: false, done: false, pct: 30, need: '3/10 closed · +8.0%' }, { key: 'proven', icon: '🏆', seats: 3, on: true, done: false, pct: 7, need: '1.17× of 10× · 12/30 calls' }] },
  card: { tpl: 'degen', seats: [{ symbol: 'BOT', pair: 'P1', mint: 'M1', kind: 'agent', pct: 5, take: 10, action: 'hold', why: '+5.0% — holding until +10%' }, { symbol: 'MINE', pair: 'P2', mint: 'M2', kind: 'yours', pct: null }, { kind: 'open', symbol: null, pct: null }] } };

test('screen helpers: heat, reasons (who carries them), the scope (bar at the middle), the docket and the click-through order', () => {
  expect(heat(0)).toBe(0.12); expect(heat(-5)).toBe(0.5); expect(heat(40)).toBe(1);
  const rs = reasonsOf(table); expect(rs[0]).toMatchObject({ key: 'surge', n: 2, w: 1, mints: ['A', 'B'] }); expect(rs.find(r => r.key === 'swarm').w).toBe(-1);
  const sc = scopeOf([{ mint: 'X', symbol: 'X', nums: { d5: 0 }, why: { lean: 1.5 }, trigger: ['enter'], go: true }], 1.5);
  expect(sc[0]).toMatchObject({ go: true, call: 'enter', y: 0.5 }); expect(sc[0].x).toBeCloseTo(1 / 3);
  expect(docketOf(table).map(x => [x.sym, x.ok, x.go, x.rug])).toEqual([['GOOD', true, true, 10], ['RUN', false, false, 70]]);
  expect(listFor('tally', table)).toEqual(['A', 'B', 'C']); expect(listFor('devil', table)).toEqual(['A', 'B']); expect(listFor('trigger', table)[0]).toBe('A');
  expect(listFor('sherlock', table, 'swarm')).toEqual(['B']); expect(listFor('devil', [table[2]])).toEqual(['C']);   // no ENTER → the whole pass
});

test('tap a mini screen → the zoom: tap a mark or step ‹ › through the coins, switch agent, filter by a reason, Esc closes', async () => {
  const call = jest.fn(async () => view); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesk call={call} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('screen-tally').textContent).toContain('3'); expect(q('screen-devil').textContent).toContain('1/2'); expect(q('ags-zoom')).toBeNull();
  await act(async () => { q('screen-tally').click(); });
  expect(q('ags-zoom')).not.toBeNull(); expect(q('tile-GOOD')).not.toBeNull(); expect(q('ags-dossier').textContent).toContain('$GOOD'); expect(q('ags-dossier').textContent).toContain('1 / 3');
  await act(async () => { q('tile-RUN').click(); });
  expect(q('ags-dossier').textContent).toContain('$RUN'); expect(q('ags-dossier').textContent).toContain('OBJECTED'); expect(q('ags-dossier').textContent).toContain('BOND RUN');
  await act(async () => { q('ags-next').click(); });
  expect(q('ags-dossier').textContent).toContain('$MEH');
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' })); });
  expect(q('ags-dossier').textContent).toContain('$GOOD');   // wraps
  await act(async () => { q('zoom-sherlock').click(); });
  expect(q('reason-surge').textContent).toContain('×2'); expect(q('chip-MEH')).not.toBeNull();
  await act(async () => { q('reason-swarm').click(); });
  expect(q('chip-MEH')).toBeNull(); expect(q('chip-GOOD')).toBeNull(); expect(q('ags-dossier').textContent).toContain('$RUN');   // only the coins with that reason
  await act(async () => { q('zoom-devil').click(); });
  expect(q('ticket-GOOD').textContent).toContain('GO'); expect(q('ticket-RUN').textContent).toContain('✕');
  await act(async () => { q('zoom-trigger').click(); });
  expect(q('dot-GOOD')).not.toBeNull();
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(q('ags-zoom')).toBeNull();
  expect(q('ags-card').textContent).toContain('$BOT'); expect(q('ags-pow').textContent).toContain('1 / 1 seats');   // the real card strip is always on screen
  await act(async () => { root.unmount(); });
});

test('the real card as seats, growth cards and the seat ladder', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<><CardNow card={view.card} power={view.power} cfg={view.cfg} /><GrowthCards growth={view.growth} agents={view.agents} /><PowerLadder power={view.power} /></>); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('seat-BOT').className).toContain('is-agent'); expect(q('seat-BOT').textContent).toContain('+5.0%'); expect(q('seat-BOT').textContent).toContain('⏳');
  expect(q('seat-MINE').textContent).toContain('—'); expect(q('ags-card').textContent).toContain('open');   // no price = "—", never a fake 0%
  expect(q('grow-tally').textContent).toContain('Rookie'); expect(q('grow-tally').textContent).toContain('40/60'); expect(q('grow-tally').textContent).toContain('57% earned');
  expect(q('grow-sherlock').className).toContain('is-stunted'); expect(q('grow-sherlock').textContent).toContain('⚠ stunted'); expect(q('grow-sherlock').textContent).toContain('☠×1'); expect(q('grow-sherlock').textContent).toContain('🧬 callers piling in');
  expect(q('rung-learn').textContent).toContain('✓ live'); expect(q('rung-trust').textContent).toContain('3/10 closed'); expect(q('rung-trust').textContent).toContain('switch off'); expect(q('ags-ladder').textContent).toContain('1 held of 1');
  await act(async () => { root.render(<CardNow card={{}} cfg={{}} />); });
  expect(q('ags-card').textContent).toContain('paper only');
  await act(async () => { root.unmount(); });
});
