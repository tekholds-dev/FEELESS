import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { FamilyBlock3D, BlockCard, TownPicker } from './FamilyBlock3D';
import { errandGo } from './FamilyBlock';
import { blockPlan, spotOf, TOWN } from '../lib/cityPlan';

const BL = { id: 'c1', tag: 'FRT', name: 'Sicario', built: 1, total: 260, open: 4, canBuild: true,
  buildings: [{ key: 'jito', name: 'Jito', sym: 'JitoSOL', kind: 'stake', state: 'built', usd: 260, apy: 4.85, proof: 'mint', band: '$$',
    errands: [{ kind: 'switch', icon: '⚖', text: 'JupSOL pays 5.40% vs your JitoSOL 4.85% — switch?', swap: { from: 'J1', to: 'jup' }, gain: 0.55 }] },
  { key: 'meteora', name: 'Meteora', kind: 'dex', state: 'construction', proof: 'none', why: 'Meteora DLMM positions are program accounts — their reader is not wired yet', errands: [] }],
  catalog: [{ key: 'orca', name: 'Orca', offer: 'Whirlpools', proof: 'nft' }, { key: 'save', name: 'Save', proof: 'none', why: 'not wired' }] };

test('🏙 the block plan: built = a tower with its own sign lines, not yet = scaffolding, plus open plots; the camera finds each', () => {
  const p = blockPlan(BL);
  expect(p.kind).toBe('block'); expect(p.islands).toHaveLength(1);
  expect(p.markets.map(m => m.key)).toEqual(['blk-jito']); expect(p.markets[0].lines[1]).toBe("$260 · APY 4.8%");
  const shut = p.lots.find(l => l.id === 'blk-meteora'); expect(shut.state).toBe('shut'); expect(shut.lines[0]).toBe('Meteora · UNDER CONSTRUCTION');
  expect(p.lots.filter(l => l.open)).toHaveLength(4);
  expect(spotOf(p, { blk: 'jito' })).not.toBeNull(); expect(spotOf(p, { blk: 'meteora' })).not.toBeNull(); expect(spotOf(p, { open: 2 })).not.toBeNull();
});

test('🏙 no WebGL → the drawn block: lit towers, scaffolding, open plots; tap picks; the card shows real numbers, errands and the add list', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const pick = jest.fn();
  await act(async () => { root.render(<FamilyBlock3D bl={BL} sel={null} onPick={pick} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('blk-jito').className).toContain('is-built'); expect(q('blk-jito').textContent).toContain('$260');
  expect(q('blk-meteora').textContent).toContain('UNDER CONSTRUCTION'); expect(q('blk-meteora').querySelector('.fb3-scaf')).not.toBeNull();
  expect(el.querySelectorAll('.fb3-b.is-open')).toHaveLength(4);
  act(() => q('open-1').click()); expect(pick).toHaveBeenLastCalledWith({ open: 1 });
  const onAct = jest.fn(); const onErrand = jest.fn();
  await act(async () => { root.render(<BlockCard bl={BL} sel={{ blk: 'jito' }} mine onAct={onAct} onErrand={onErrand} />); });
  expect(q('blk-card').textContent).toContain('built · a real position'); expect(q('blk-card').textContent).toContain('$260');
  act(() => q('errand-switch').click()); expect(onErrand.mock.calls[0][0].kind).toBe('switch');
  await act(async () => { root.render(<BlockCard bl={BL} sel={{ blk: 'meteora' }} mine onAct={onAct} onErrand={onErrand} />); });
  expect(q('blk-card').textContent).toContain('not wired yet — it stays under construction');
  await act(async () => { root.render(<BlockCard bl={BL} sel={{ open: 0 }} mine onAct={onAct} onErrand={onErrand} />); });
  act(() => q('blk-add-orca').click()); expect(onAct).toHaveBeenCalledWith('add', 'orca');
  expect(q('blk-add-save').textContent).toContain('no reader yet');
  await act(async () => { root.render(<BlockCard bl={{ ...BL, buildings: [{ ...BL.buildings[0], usd: undefined, errands: undefined }] }} sel={{ blk: 'jito' }} />); });
  expect(q('blk-card').textContent).toContain('$$'); expect(q('errand-switch')).toBeNull();   // a visitor: a band, no errands
  act(() => root.unmount());
});

test('🏙 errands open the real tool: the swap with both coins set, the perps desk, the protocol app', () => {
  const nav = jest.fn(); const open = jest.fn(); const seen = jest.fn(); window.addEventListener('feeless:deck', seen);
  expect(errandGo(BL.buildings[0].errands[0], BL.buildings[0], nav, open)).toBe('swap');
  expect(JSON.parse(sessionStorage.getItem('feeless.swap.pair'))).toEqual({ input: 'J1', output: 'jup' }); expect(nav).toHaveBeenCalledWith('/terminal/trade');
  errandGo({ kind: 'hedge' }, { key: 'jlp' }, nav, open); expect(seen.mock.calls[0][0].detail).toBe('perps');
  errandGo({ kind: 'range' }, { key: 'orca' }, nav, open); expect(open).toHaveBeenCalledWith('https://www.orca.so/portfolio');
  errandGo({ kind: 'build', url: 'https://jito.network' }, { key: 'jito' }, nav, open); expect(open).toHaveBeenLastCalledWith('https://jito.network');
});

test('🏘 the town: the tool buildings the family picked stand on the block (TT burns its READY floors), the picker stands / takes them down, a standing one walks in', async () => {
  const bl = { ...BL, town: ['tt', 'perps'], townMax: 6, townAll: Object.keys(TOWN) };
  const p = blockPlan(bl, { coins: [{ sym: 'PHP', ch: 40, status: 'READY' }, { sym: 'CYB', ch: -3 }] });
  expect(p.places.map(x => [x.key, x.art, x.pick.town])).toEqual([['town-tt', 'tt', 'tt'], ['town-perps', 'perps', 'perps']]);
  expect(p.places[0].live).toMatchObject({ ready: 1, n: 2, hot: { sym: 'PHP' } }); expect(p.places[0].lines[1]).toBe('1 READY · 2 on the intake');
  expect(spotOf(p, { town: 'perps' })).not.toBeNull(); expect(p.lots.filter(l => l.open)).toHaveLength(4);
  const all = [...p.lots, ...p.markets, ...p.places].map(x => `${x.rect.x},${x.rect.z}`); expect(new Set(all).size).toBe(all.length);   // nothing stacked
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onAct = jest.fn(); const onOpen = jest.fn(); const pick = jest.fn();
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<FamilyBlock3D bl={bl} sel={null} onPick={pick} />); });
  act(() => q('town-b-perps').click()); expect(pick).toHaveBeenLastCalledWith({ town: 'perps' });   // the drawn block: a town tower walks in
  await act(async () => { root.render(<TownPicker bl={bl} mine busy={false} onAct={onAct} onOpen={onOpen} open={null} />); });
  expect(q('town-picker').textContent).toContain('2/6'); expect(el.querySelectorAll('.ftp-meter u.on')).toHaveLength(2);
  act(() => q('town-tog-pools').click()); expect(onAct).toHaveBeenLastCalledWith('tadd', 'pools');
  act(() => q('town-tog-perps').click()); expect(onAct).toHaveBeenLastCalledWith('tdel', 'perps');
  act(() => q('town-open-tt').click()); expect(onOpen).toHaveBeenLastCalledWith('tt');
  expect(q('town-open-radar').disabled).toBe(true);                                                    // not standing → nothing to walk into
  await act(async () => { root.render(<TownPicker bl={{ ...bl, town: ['tt', 'perps', 'pools', 'trades', 'vault', 'radar'] }} mine onAct={onAct} onOpen={onOpen} />); });
  expect(q('town-tog-cats').disabled).toBe(true);                                                      // full: take one down first
  await act(async () => { root.render(<TownPicker bl={{ ...bl, canBuild: false }} mine onAct={onAct} onOpen={onOpen} />); });
  expect(q('town-tog-tt')).toBeNull(); expect(q('town-picker').textContent).toContain('Only the Don or the Underboss');
  act(() => root.unmount());
});
