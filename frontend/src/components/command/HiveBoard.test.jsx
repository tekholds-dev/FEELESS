import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { HiveBoard } from './HiveBoard';
import { HiveSwitch } from './CatWorkbench';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({}) }));

const HIVE = { epoch: 20755, left: 3600 * 5, filed: 3, graded: 2, board: [{ cat: 'h1', name: 'Happy', honey: 3, cells: 2, graded: 2, right: 2 }],
  cells: [{ id: 'c1', name: 'Happy', sym: 'HUSS', call: 'BUY', why: 'volume 3x', honey: 2, move: 25 }, { id: 'c2', name: 'Happy', sym: 'RUG', call: 'AVOID', why: 'pool thin', honey: 1, move: -8 }, { id: 'c3', name: 'Happy', sym: 'NEW', call: 'WATCH', why: 'no edge', honey: null }] };

test('🐝 the Hive board: epoch ring, filed / graded, a honeycomb cell per call (right ones glow), the honey board', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HiveBoard api={async () => HIVE} />); });
  const comb = el.querySelector('[data-testid="hive-comb"]'); const cells = comb.querySelectorAll('li');
  expect(cells).toHaveLength(3); expect(cells[0].className).toContain('is-buy'); expect(cells[0].className).toContain('is-right'); expect(cells[2].textContent).toContain('⏳');
  expect(el.querySelector('[data-testid="hive-board"]').textContent).toContain('Happy'); expect(el.querySelector('[data-testid="hive-board"]').textContent).toContain('2/2 right');
  expect(el.textContent).toContain('5h 00m');
});

test('🐝 Colonize opens the popout (what it is + the FEECAT stake), confirms at the picked pace, shows a refused stake, and leaves in one click', async () => {
  const sent = []; let refuse = true;
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); sent.push(b); if (refuse && b.on) { refuse = false; return { ok: false, status: 402, json: async () => ({ detail: 'Colonizing needs $25 of FEECAT in your wallet — it holds $3.10.' }) }; } return { ok: true, status: 200, json: async () => ({ hive: { on: b.on, every: b.cap } }) }; };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HiveSwitch cat={{ id: 'h1', name: 'Kit', hive: { on: false, every: 300 } }} />); });
  await act(async () => { el.querySelector('[data-testid="hive-toggle"]').click(); });
  expect(sent).toHaveLength(0); const pop = document.body.querySelector('[data-testid="colonize-pop"]');
  expect(pop.textContent).toContain('$25 of FEECAT'); expect(pop.textContent).toContain('never pooled'); expect(pop.textContent).toContain('Colonize Kit');
  await act(async () => { document.body.querySelector('[data-testid="colonize-pace-900"]').click(); });
  await act(async () => { document.body.querySelector('[data-testid="colonize-go"]').click(); });
  expect(sent.at(-1)).toMatchObject({ op: 'hive', on: true, cap: 900 }); expect(document.body.querySelector('[data-testid="colonize-err"]').textContent).toContain('holds $3.10');
  await act(async () => { document.body.querySelector('[data-testid="colonize-go"]').click(); });
  expect(document.body.querySelector('[data-testid="colonize-pop"]')).toBeNull(); expect(el.querySelector('[data-testid="hive-toggle"]').textContent).toContain('COLONIZED');
  const sel = el.querySelector('[data-testid="hive-pace"]');
  await act(async () => { sel.value = '3600'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(sent.at(-1)).toMatchObject({ op: 'hive', on: true, cap: 3600 });
  await act(async () => { el.querySelector('[data-testid="hive-toggle"]').click(); });
  expect(sent.at(-1)).toMatchObject({ op: 'hive', on: false });
});
