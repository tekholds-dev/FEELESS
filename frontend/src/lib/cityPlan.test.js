import { feePlan, outerPlan, spotOf, pulseHz, heightOf, usd, PLACES, centerOf, FOOT, CELL, MCELL, roomsOf, ttLive } from './cityPlan';
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
  coins: [{ mint: 'M1', sym: 'PHP', mc: 1.4e6, ch: 1082, vol: 6.6e6, pair: 'P1', status: 'READY' }, { mint: 'M2', sym: 'CYBER', mc: 9e5, ch: -12, vol: 2e6, pair: 'P2' }],
};
const overlap = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.z < b.z + b.d && b.z < a.z + a.d;

test('🗺 Fee City: the capital + four islands (three market + FEELESS AVENUE), every market on its island, the places, four gates, stoplights and traffic', () => {
  const p = feePlan(V, MK);
  expect(p.islands.map(i => i.key)).toEqual(['fee', 'row', 'vault', 'money', 'ave']);
  expect(p.lots.map(l => l.id)).toEqual(['fee-0', 'fee-5']);                                     // only the capital's own plots
  expect(p.lots[0]).toMatchObject({ kind: 'mine', tag: 'SIC', owner: 'c1' }); expect(p.lots[1].kind).toBe('free');
  expect(p.markets.find(m => m.key === 'raydium').island).toBe('row');
  expect(p.markets.find(m => m.key === 'kamino').island).toBe('vault'); expect(p.markets.find(m => m.key === 'jito').island).toBe('vault');
  expect(p.markets.some(m => m.kind === 'coin')).toBe(false);                                     // 🗼 no field of little coin towers
  const tt = p.places.find(x => x.key === 'tt'); expect(tt).toMatchObject({ isl: 'money', art: 'tt', live: { ready: 1, n: 2, hot: { sym: 'PHP' } } });
  expect(tt.lines.join(' ')).toContain('1 READY'); expect(tt.lines.join(' ')).toContain('HOT $PHP');
  expect([...p.places, ...p.inside].map(x => x.key).sort()).toEqual(PLACES.map(x => x.key).sort());   // every old lens is a place or a room
  expect(p.gates.map(g => [g.key, g.name])).toEqual([['heights', 'Raydium Heights'], ['bay', 'Bonk Bay'], ['harbor', 'Pump Harbor'], ['docks', 'Cartel Docks']]);
  expect(p.bridges).toHaveLength(4); expect(p.lights.length).toBeGreaterThan(3); expect(p.loops.length).toBeGreaterThanOrEqual(6);
  // nothing built on top of anything else
  const rects = [...p.lots, ...p.marks, ...p.markets, ...p.places.filter(x => !x.virtual && !String(x.isl).startsWith('plaza')), ...p.spare].map(x => x.rect);
  for (let i = 0; i < rects.length; i += 1) for (let j = i + 1; j < rects.length; j += 1) expect(overlap(rects[i], rects[j])).toBe(false);
  // every market / place sits inside its island
  for (const m of [...p.markets, ...p.places.filter(x => !x.virtual && !String(x.isl).startsWith('plaza'))]) { const isl = p.islands.find(i => i.key === (m.island || m.isl)); const c = centerOf(m.rect);
    expect(c.x > isl.x && c.x < isl.x + isl.w && c.z > isl.z && c.z < isl.z + isl.d).toBe(true); }
  expect(spotOf(p, { mk: 'raydium' })).toEqual(centerOf(p.markets.find(m => m.key === 'raydium').rect));
  expect(p.places.find(x => x.key === 'hq').rect).toEqual(p.lots.find(l => l.id === 'fee-0').rect);   // 🏠 your HQ = your home block
  expect(spotOf(p, { isl: 'money' })).toMatchObject({ span: expect.any(Number) });
  expect(spotOf(p, { place: 'ranked' })).not.toBeNull(); expect(spotOf(p, { lm: 'arena' })).not.toBeNull(); expect(spotOf(p, { id: 'nope' })).toBeNull();
});

test('🌉 an outer city: its boroughs as islands, a bridge between them, a gate home to Fee City; an unknown city has no plan', () => {
  const p = outerPlan(V, 'harbor');
  expect(p.islands.map(i => i.key)).toEqual(['harbor', 'piers', 'hall-harbor']); expect(p.lots).toHaveLength(2);
  expect(p.bridges).toHaveLength(2); expect(p.places).toEqual([expect.objectContaining({ key: 'hall-harbor', lens: 'hall-harbor', tool: true, name: 'PUMP HALL' })]); expect(p.gates[0]).toMatchObject({ key: 'fee', name: 'FEE CITY', at: 'w' });
  expect(outerPlan(V, 'mars')).toBeNull();
  // 🏦 with the Pool Hub: the city's own pool district — real pools as towers over a bridge
  const pools = { cities: { harbor: [{ id: 'P1', sym: 'SOL-USDC', kind: 'v2', proto: 'Raydium', tvl: 9e6, apy: 14, vol: 2e6 }, { id: 'P2', sym: 'MEW-SOL', kind: 'v2', proto: 'Raydium', tvl: 3e6, apy: 59 }] } };
  const q = outerPlan(V, 'harbor', pools);
  expect(q.islands.map(i => i.key)).toEqual(['harbor', 'piers', 'mk-harbor', 'hall-harbor']); expect(q.markets.map(m => [m.name, m.pool, m.apy])).toEqual([['SOL-USDC', true, 14], ['MEW-SOL', true, 59]]);
  expect(q.spare).toHaveLength(6); expect(q.bridges).toHaveLength(3);
  const rects = [...q.lots, ...q.markets, ...q.spare].map(x => x.rect);
  for (let i = 0; i < rects.length; i += 1) for (let j = i + 1; j < rects.length; j += 1) expect(overlap(rects[i], rects[j])).toBe(false);
});

test('💡 live numbers drive the city: roof-light pulse from volume, tower height from TVL, compact $', () => {
  expect(pulseHz({ pool: { vol: 0 } })).toBe(0.4); expect(pulseHz({ vol: 1e9 })).toBeGreaterThan(pulseHz({ vol: 1e4 }));
  expect(heightOf(1.2e9)).toBeGreaterThan(heightOf(1e6)); expect(heightOf(0)).toBe(1);
  expect(usd(1.2e9)).toBe('$1.20B'); expect(usd(3.4e6)).toBe('$3.4M'); expect(usd(null)).toBe('—');
  const p = feePlan(V, MK);
  const v = marketVitals({ mk: 'kamino' }, p); expect(v.title).toBe('Kamino'); expect(JSON.stringify(v.groups)).toContain('$1.30B');
  expect(marketVitals({ place: 'gym' }, p).title).toBe('THE GYM');
});

test('🛣 FEELESS AVENUE: every site tool is a building on its own island (a pop-out with a full page), over a bridge north of the capital; the Heights gate moved past it', () => {
  const p = feePlan(V, MK); const ave = p.islands.find(i => i.key === 'ave'); const cap = p.islands.find(i => i.key === 'fee');
  const tools = p.places.filter(x => x.tool);
  expect(tools.map(x => x.lens).sort()).toEqual(['feebank', 'feecat', 'perps', 'pumpradar', 'rep', 'sleep', 'trades', 'tt']);
  for (const t of tools.filter(x => x.key !== 'tt')) { expect(t.isl).toBe('ave'); const c = centerOf(t.rect); expect(c.x > ave.x && c.x < ave.x + ave.w && c.z > ave.z && c.z < ave.z + ave.d).toBe(true); }
  expect(new Set(PLACES.map(x => x.lens)).size).toBe(PLACES.length);                                  // one lens per place (the Wire keeps 'feed')
  expect(ave.z + ave.d).toBeLessThan(cap.z);                                                         // north of the capital, water between
  expect(p.bridges.find(b => b.key === 'b-ave')).toMatchObject({ axis: 'z', a: ave.z + ave.d, b: cap.z });
  expect(p.gates.find(g => g.key === 'heights').b).toBe(ave.z);
});

test('🌳 more space: every cell is bigger than the building on it — each stands in its own yard, the land and the water are wide', () => {
  expect(FOOT.lot).toBeLessThan(CELL - 1); expect(FOOT.tower).toBeLessThan(MCELL - 1.5);
  const p = feePlan(V, MK); const [cap, row] = p.islands;
  expect(row.x - (cap.x + cap.w)).toBeGreaterThanOrEqual(22);                                         // water between the capital and Market Row
  expect(cap.w).toBeGreaterThanOrEqual(50);                                                           // the capital alone, ~2× the old 39 × 31 floor
  const q = outerPlan(V, 'harbor'); expect(q.islands[1].x - (q.islands[0].x + q.islands[0].w)).toBeGreaterThanOrEqual(22);
});

test('🌆 Fee City BREATHES (owner, 2026-10-23): far fewer, bigger buildings — duplicates are rooms inside one building, TT is ONE tower, empty cells are parks', () => {
  const many = { markets: Array.from({ length: 30 }, (_, i) => ({ key: `m${i}`, name: `M${i}`, kind: ['dex', 'lend', 'stake', 'perps'][i % 4], tvl: 1e6 * (i + 1) })), coins: MK.coins };
  const p = feePlan(V, many);
  const off = p.markets.length + p.places.filter(x => !x.virtual && !String(x.isl).startsWith('plaza')).length;
  expect(off).toBeLessThanOrEqual(20);                                                                // was ~47 market / tool buildings off the capital
  expect(p.markets.filter(m => m.island === 'row')).toHaveLength(4); expect(p.markets.filter(m => m.island === 'vault')).toHaveLength(4);
  expect(p.markets.filter(m => m.island === 'row').map(m => m.name)).toEqual(['M28', 'M24', 'M20', 'M16']);   // the biggest DEXes stand
  expect(p.spare.every(x => x.park)).toBe(true);                                                      // open land, never a filler building
  // rooms: no building of their own, the camera flies to the host, the pop-out lists the host's rooms
  expect(p.inside.find(x => x.key === 'ranked')).toMatchObject({ host: 'podium', rect: p.places.find(x => x.key === 'podium').rect });
  expect(spotOf(p, { place: 'raids' })).toEqual(centerOf(p.places.find(x => x.key === 'warroom').rect));
  expect(roomsOf('raids').map(x => x.key)).toEqual(['warroom', 'raids', 'cartels']); expect(roomsOf('rc').map(x => x.key)).toEqual(['hq', 'jobs', 'gym', 'cards']);
  expect(roomsOf('tt').map(x => x.key)).toEqual(['tt']);
  // the TT tower covers the whole TT island grid (one landmark), and is far bigger than a market tower
  const tt = p.places.find(x => x.key === 'tt'); const mkt = p.markets[0];
  expect(tt.rect.w * tt.rect.d).toBeGreaterThan(4 * mkt.rect.w * mkt.rect.d); expect(FOOT.tt).toBeGreaterThan(2 * FOOT.tower - 1);
  expect(ttLive([])).toMatchObject({ n: 0, ready: 0, hot: null }); expect(ttLive([{ sym: 'A', ch: 2 }, { sym: 'B', ch: 9, status: 'ready' }])).toMatchObject({ ready: 1, hot: { sym: 'B' } });
});
