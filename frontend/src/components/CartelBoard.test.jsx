import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { CartelBoard } from './CartelBoard';

const v = { cartels: [{ id: 'cartel-sniper-1', name: 'Block Zero Snipers', tag: 'SN1', role: 'sniper', icon: '🎯', members: 40, hits: 900, coins: 30, active7d: 12, power: 9000, level: 10 },
  { id: 'cartel-funder-4', name: 'Drip Feeders', tag: 'FU4', role: 'funder', icon: '💸', members: 5, hits: 20, coins: 6, active7d: 1, power: 300, level: 1 }],
  blocks: [{ id: 'docks-0', kind: 'cartel', owner: 'cartel-sniper-1' }] };
const q = id => document.querySelector(`[data-testid="${id}"]`);

test('⚖ every rep cartel can be raided from the warehouse — even one without a building; one with a building also flies there', async () => {
  const acts = []; const flown = []; const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CartelBoard v={v} me={{ hitters: [5] }} act={b => acts.push(b)} busy={false} onFly={id => flown.push(id)} />); });
  await act(async () => { q('cw-raid-cartel-funder-4').click(); });
  expect(acts).toEqual([{ act: 'raid', vs: 'cartel-funder-4' }]);
  expect(q('cw-fly-cartel-funder-4')).toBeNull();
  await act(async () => { q('cw-fly-cartel-sniper-1').click(); });
  expect(flown).toEqual(['docks-0']);
  await act(async () => { q('cw-role-funder').click(); });
  expect(q('cartel-cartel-sniper-1')).toBeNull();
  await act(async () => { root.render(<CartelBoard v={v} me={{ hitters: [] }} act={() => {}} busy={false} />); });
  expect(q('cw-raid-cartel-funder-4').disabled).toBe(true);   // no ready hitter → the button says why
  act(() => root.unmount());
});
