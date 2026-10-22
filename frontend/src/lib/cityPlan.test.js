import { feePlan, outerPlan, spotOf, pulseHz, heightOf, usd, PLACES, centerOf } from './cityPlan';
import { marketVitals } from '../components/FeeCity3D';

const V = {
  blocks: [{ id: 'fee-0', b: 'fee', i: 0, owner: 'c1', tag: 'SIC', power: 900, kind: 'family', mine: true, home: true }, { id: 'fee-5', b: 'fee', i: 5 },
    { id: 'harbor-0', b: 'harbor', i: 0, owner: 'cpu-1', tag: 'RUG', kind: 'cpu', power: 50 }, { id: 'piers-3', b: 'piers', i: 3 }],
  landmarks: [{ key: 'arena', name: 'FUSE ARENA', live: { raids: 2 } }, { key: 'house', name: 'THE HOUSE', live: { mp: 1200 } }],
  cities: [{ key: 'fee', name: 'FEE CITY', boroughs: ['fee'], held: 1, plots: 24 }, { key: 'harbor', name: 'Pump Harbor', boroughs: ['harbor', 'piers'], held: 1, plots: 32 },
    { key: 'heights', name: 'Raydium Heights', boroughs: [], held: 0, plots: 32 }, { key: 'bay', name: 'Bonk Bay', boroughs: [], held: 0, plots: 16 }, { key: 'docks', name: 'Cartel Docks', boroughs: [], held: 0, plots: 16 }],
  boroughs: [{ key: 'harbor', name: 'Pump Harbor', col: 0, row: 0, tier: 1 }, { key: 'piers', name: 'The Piers', col: 1, row: 0, tier: 2 }],
  bridges: [{ a: 'harbor', b: 'piers', name: 'Pier Bridge' }],
};
const MK = {
  markets: [{ key: 'raydium', name: 'Raydium', kind: 'dex', tvl: 1.2e9, pool: { vol: 3e5 } }, { key: 'orca', name: 'Orca', kind: 'dex', tvl: 3e8 }, { key: 'kamino', name: 'Kamino', kind: 'lend', tvl: 1.3e9, offer: 'Lending' },
    { key: 'jlp', name: 'Jupiter Perps', kind: 'perps', tvl: 7e8 }, { key: 'jito', name: 'Jito', kind: 'stake', tvl: 1e9 }],
  coins: [{ mint: 'M1', sym: 'PHP', mc: 1.4e6, ch: 1082, vol: 6.6e6, pair: 'P1' }, { mint: 'M2', sym: 'CYBER', mc: 9e5, ch: -12, vol: 2e6, pair: 'P2' }],
};
const overlap = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.z < b.z + b.d && b.z < a.z + a.d;

test('🗺 Fee City: the capital + three market islands, every market on its island, the places, four gates, stoplights and traffic', () => {
  const p = feePlan(V, MK);
  expect(p.islands.map(i => i.key)).toEqual(['fee', 'row', 'vault', 'money']);
  expect(p.lots.map(l => l.id)).toEqual(['fee-0', 'fee-5']);                                     // only the capital's own plots
  expect(p.lots[0]).toMatchObject({ kind: 'mine', tag: 'SIC', owner: 'c1' }); expect(p.lots[1].kind).toBe('free');
  expect(p.markets.find(m => m.key === 'raydium').island).toBe('row');
  expect(p.markets.find(m => m.key === 'kamino').island).toBe('vault'); expect(p.markets.find(m => m.key === 'jito').island).toBe('vault');
  const php = p.markets.find(m => m.name === '$PHP'); expect(php).toMatchObject({ island: 'money', kind: 'coin', move: 1082, tvl: 1.4e6 });
  expect(p.places.map(x => x.key).sort()).toEqual(PLACES.map(x => x.key).sort());                // every old lens is a place
  expect(p.gates.map(g => [g.key, g.name])).toEqual([['heights', 'Raydium Heights'], ['bay', 'Bonk Bay'], ['harbor', 'Pump Harbor'], ['docks', 'Cartel Docks']]);
  expect(p.bridges).toHaveLength(3); expect(p.lights.length).toBeGreaterThan(3); expect(p.loops.length).toBeGreaterThanOrEqual(6);
  // nothing built on top of anything else
  const rects = [...p.lots, ...p.marks, ...p.markets, ...p.places.filter(x => x.isl !== 'plaza'), ...p.spare].map(x => x.rect);
  for (let i = 0; i < rects.length; i += 1) for (let j = i + 1; j < rects.length; j += 1) expect(overlap(rects[i], rects[j])).toBe(false);
  // every market / place sits inside its island
  for (const m of [...p.markets, ...p.places.filter(x => x.isl !== 'plaza')]) { const isl = p.islands.find(i => i.key === (m.island || m.isl)); const c = centerOf(m.rect);
    expect(c.x > isl.x && c.x < isl.x + isl.w && c.z > isl.z && c.z < isl.z + isl.d).toBe(true); }
  expect(spotOf(p, { mk: 'raydium' })).toEqual(centerOf(p.markets.find(m => m.key === 'raydium').rect));
  expect(spotOf(p, { place: 'ranked' })).not.toBeNull(); expect(spotOf(p, { lm: 'arena' })).not.toBeNull(); expect(spotOf(p, { id: 'nope' })).toBeNull();
});

test('🌉 an outer city: its boroughs as islands, a bridge between them, a gate home to Fee City; an unknown city has no plan', () => {
  const p = outerPlan(V, 'harbor');
  expect(p.islands.map(i => i.key)).toEqual(['harbor', 'piers']); expect(p.lots).toHaveLength(2);
  expect(p.bridges).toHaveLength(1); expect(p.gates[0]).toMatchObject({ key: 'fee', name: 'FEE CITY', at: 'w' });
  expect(outerPlan(V, 'mars')).toBeNull();
});

test('💡 live numbers drive the city: roof-light pulse from volume, tower height from TVL, compact $', () => {
  expect(pulseHz({ pool: { vol: 0 } })).toBe(0.4); expect(pulseHz({ vol: 1e9 })).toBeGreaterThan(pulseHz({ vol: 1e4 }));
  expect(heightOf(1.2e9)).toBeGreaterThan(heightOf(1e6)); expect(heightOf(0)).toBe(1);
  expect(usd(1.2e9)).toBe('$1.20B'); expect(usd(3.4e6)).toBe('$3.4M'); expect(usd(null)).toBe('—');
  const p = feePlan(V, MK);
  const v = marketVitals({ mk: 'kamino' }, p); expect(v.title).toBe('Kamino'); expect(JSON.stringify(v.groups)).toContain('$1.30B');
  expect(marketVitals({ place: 'gym' }, p).title).toBe('THE GYM');
});
