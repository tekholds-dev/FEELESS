import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { BlockArranger, MyPoolsCard, startCells, swap, newIsland, removable } from './BlockArranger';
import { blockPlan, blockCells, myPools, spotOf } from '../lib/cityPlan';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const BL = { id: 'c1', tag: 'FRT', name: 'Sicario', built: 1, canBuild: true, islandCells: 15, islandsPaid: 1, islandMp: 3000, layoutSaved: true,
  buildings: [{ key: 'jito', name: 'Jito', sym: 'JitoSOL', state: 'built', usd: 260, apy: 4.8 }, { key: 'orca', name: 'Orca', state: 'construction' }], town: ['tt'],
  layout: ['town:tt', 'stand:park', 'blk:jito', 'pools', 'open', 'blk:orca'] };

test('🏝 the block follows the family layout: moved buildings, beauty plots, MY POOLS; a new island + bridge every 15 lots', () => {
  const lp = [{ id: 'P1', sym: 'PANGEA-SOL', valueUsd: 12.5, feeUsd: 0.3, inRange: true }];
  expect(blockCells(BL, lp)).toEqual(['town:tt', 'stand:park', 'blk:jito', 'pools', 'open', 'blk:orca', 'lp:P1']);   // your LP towers follow the family's last market
  const p = blockPlan(BL, { lp });
  expect(p.places.map(x => x.key)).toEqual(['town-tt', 'stand-0', 'my-pools']);
  expect(p.places[1]).toMatchObject({ art: 'stand', stand: 'park' }); expect(p.places[2].lines[1]).toBe('$273 · 2 positions · +$0.300 fees');
  expect(myPools(BL, lp)).toMatchObject({ usd: 272.5, n: 2, inRange: 1 });
  expect(p.islands).toHaveLength(1); expect(p.bridges).toHaveLength(0);
  expect(spotOf(p, { pools: true })).not.toBeNull(); expect(spotOf(p, { stand: 0 })).not.toBeNull();
  const big = blockPlan({ ...BL, layout: [...BL.layout, ...Array(14).fill('open')] });
  expect(big.islands.map(i => i.key)).toEqual(['block', 'block-1']); expect(big.bridges).toHaveLength(1);
  const rects = [...big.markets, ...big.places, ...big.lots].map(x => `${x.rect.x},${x.rect.z}`); expect(new Set(rects).size).toBe(rects.length);   // nothing stacked
  expect(blockCells({ ...BL, layoutSaved: false, open: 2 })).toEqual([...BL.layout, 'open', 'open']);   // never saved: the open plots still show
});

test('✋ arrange: tap two lots to swap, add beauty plots + MY POOLS once, a new island costs MP (shown before save), buildings never binned', async () => {
  expect(swap(['a', 'b', 'c'], 0, 2)).toEqual(['c', 'b', 'a']); expect(newIsland(Array(15).fill('open'))).toHaveLength(18); expect(newIsland(Array(14).fill('x'))).toHaveLength(18);
  expect(removable('blk:jito')).toBe(false); expect(removable('stand:park')).toBe(true); expect(startCells({ layout: ['a'], open: 2 })).toEqual(['a', 'open', 'open']);
  const save = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<BlockArranger bl={BL} busy={false} onSave={save} onClose={() => {}} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('bar-cell-0').click(); }); await act(async () => { q('bar-cell-2').click(); });
  expect(q('bar-cell-0').textContent).toContain('JitoSOL');                                     // moved
  expect(q('bar-add-pools').disabled).toBe(true);                                               // MY POOLS stands once
  await act(async () => { q('bar-add-stand-pond').click(); });
  await act(async () => { q('bar-cell-2').click(); }); expect(q('bar-bin').disabled).toBe(true);   // a tower can't be binned here
  await act(async () => { q('bar-cell-2').click(); });
  await act(async () => { q('bar-add-island').click(); });
  expect(q('bar-cost').textContent).toBe('−3,000 MP');
  await act(async () => { q('bar-save').click(); });
  const cells = save.mock.calls[0][0]; expect(cells[0]).toBe('blk:jito'); expect(cells).toContain('stand:pond'); expect(cells).toHaveLength(18);
  act(() => root.unmount()); document.body.innerHTML = '';
});

test('💧 MY POOLS card: every position biggest first with its bar, the total on top', async () => {
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<MyPoolsCard bl={BL} lp={[{ id: 'P1', sym: 'PANGEA-SOL', valueUsd: 12.5, feeUsd: 0.3, inRange: true }]} />); });
  expect(el.querySelector('.mpc-head strong').textContent).toBe('$273');
  expect([...el.querySelectorAll('.mpc-rows li b')].map(b => b.textContent)).toEqual(['JitoSOL', 'PANGEA-SOL']);
  act(() => root.unmount());
});
