import { feePlan, outerPlan, spotOf, pulseHz, heightOf, usd, PLACES, centerOf, FOOT, CELL, MCELL, roomsOf, ttLive, moneyShare, METRO, KEYS } from './cityPlan';
import { marketVitals, chipsOf, deskAct } from '../components/FeeCity3D';

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

const POOLS = { cities: { harbor: [{ id: 'H1', sym: 'SOL-USDC', kind: 'v2', proto: 'Raydium', tvl: 9e6, apy: 14 }] },
  pools: [...['v2', 'v3', 'vault', 'lend', 'stake', 'perps', 'rwa'].flatMap(k => Array.from({ length: 8 }, (_, i) => ({ id: `${k}${i}`, sym: `${k.toUpperCase()}-${i}`, kind: k, proto: 'Proto', tvl: 1e6 * (9 - i), apy: i === 0 ? 0 : 5 + i }))),
    { id: 'H1', sym: 'SOL-USDC', kind: 'v2', proto: 'Raydium', tvl: 9e9, apy: 14 }, { id: 'dust', sym: 'DUST', kind: 'v2', proto: 'X', tvl: 50, apy: 900 }] };
const inIsland = (p, x) => { const isl = p.islands.find(i => i.key === (x.island || x.isl)); const c = centerOf(x.rect); return c.x > isl.x && c.x < isl.x + isl.w && c.z > isl.z && c.z < isl.z + isl.d; };

test('🌆 Fee City = a METRO: downtown + eight money districts over canals + six family keys; nothing overlaps, everything on its island, all bridged', () => {
  const p = feePlan(V, MK, POOLS);
  expect(p.islands.map(i => i.key)).toEqual(['fee', ...Object.keys(METRO), ...KEYS.map(k => k.key)]);
  expect(p.lots.map(l => l.id)).toEqual(['fee-0', 'fee-5']);                                     // only the capital's own plots …
  expect(p.lots[0]).toMatchObject({ kind: 'mine', tag: 'SIC', owner: 'c1', island: 'key-rose' }); expect(p.lots[1]).toMatchObject({ kind: 'free', island: 'key-gold' });   // … on the keys, 4 a key
  expect(p.islands.find(i => i.key === 'key-rose').sub).toContain('[SIC]');
  expect(p.markets.find(m => m.key === 'raydium').island).toBe('row'); expect(p.markets.find(m => m.key === 'kamino').island).toBe('lend');
  expect(p.markets.find(m => m.key === 'jito').island).toBe('stake'); expect(p.markets.find(m => m.key === 'jlp').island).toBe('ave');
  expect(p.markets.some(m => m.kind === 'coin')).toBe(false);                                     // 🗼 no field of little coin towers
  const tt = p.places.find(x => x.key === 'tt'); expect(tt).toMatchObject({ isl: 'money', art: 'tt', live: { ready: 1, n: 2, hot: { sym: 'PHP' } } });
  expect(tt.lines.join(' ')).toContain('1 READY'); expect(tt.lines.join(' ')).toContain('HOT $PHP');
  expect([...p.places, ...p.inside].map(x => x.key).sort()).toEqual(PLACES.map(x => x.key).sort());   // every old lens is a place or a room
  expect(p.gates.map(g => [g.key, g.name])).toEqual([['heights', 'Raydium Heights'], ['bay', 'Bonk Bay'], ['harbor', 'Pump Harbor'], ['docks', 'Cartel Docks']]);
  expect(p.bridges).toHaveLength(12 + KEYS.length);                                               // downtown's 4 + the canal ring's 8 + one per key
  for (const b of p.bridges) expect(Math.abs(b.b - b.a)).toBeGreaterThanOrEqual(12);              // water under every bridge
  expect(p.lights.length).toBeGreaterThan(3); expect(p.loops).toHaveLength(p.cars.length);
  expect(p.cars.reduce((a, b) => a + b, 0) + p.bridges.reduce((a, b) => a + (b.cars ?? 2), 0)).toBeLessThanOrEqual(45);   // ⚡ a car budget, not 4 a loop
  const rects = [...p.lots, ...p.marks, ...p.markets, ...p.places.filter(x => !x.virtual && !String(x.isl).startsWith('plaza')), ...p.spare].map(x => x.rect);
  for (let i = 0; i < rects.length; i += 1) for (let j = i + 1; j < rects.length; j += 1) expect(overlap(rects[i], rects[j])).toBe(false);
  const isl = p.islands; for (let i = 0; i < isl.length; i += 1) for (let j = i + 1; j < isl.length; j += 1) expect(overlap(isl[i], isl[j])).toBe(false);
  for (const m of [...p.markets, ...p.lots, ...p.spare, ...p.places.filter(x => !x.virtual && !String(x.isl).startsWith('plaza'))]) expect(inIsland(p, m)).toBe(true);
  expect(spotOf(p, { mk: 'raydium' })).toEqual(centerOf(p.markets.find(m => m.key === 'raydium').rect));
  expect(p.places.find(x => x.key === 'hq').rect).toEqual(p.lots.find(l => l.id === 'fee-0').rect);   // 🏠 your HQ = your home block
  expect(spotOf(p, { isl: 'money' })).toMatchObject({ span: expect.any(Number) }); expect(spotOf(p, { isl: 'keys' })).toEqual(spotOf(p, { isl: 'key-rose' }));   // 🏝 the keys chip flies to yours
  expect(spotOf(p, { place: 'ranked' })).not.toBeNull(); expect(spotOf(p, { lm: 'arena' })).not.toBeNull(); expect(spotOf(p, { id: 'nope' })).toBeNull();
  expect(chipsOf(p).map(c => c.key)).toEqual(['fee', ...Object.keys(METRO), 'keys']);
});

test('💵 ~80 % of Fee City is REAL MONEY (owner): pools / LSTs / lend / perps / vaults across the districts, the desk downtown; no pool twice, no dust', () => {
  const many = { markets: [...MK.markets, { key: 'orca2', name: 'Phoenix', kind: 'dex', tvl: 2e7 }, { key: 'save', name: 'Save', kind: 'lend', tvl: 8e7 }], coins: MK.coins };
  const p = feePlan(V, many, POOLS);
  expect(moneyShare(p)).toBeGreaterThanOrEqual(0.8); expect(p.share).toBe(moneyShare(p)); expect(p.islands[0].sub).toMatch(/\d+% real money/);
  const dead = p.markets.filter(m => !deskAct(m)); expect(dead.map(m => m.key)).toEqual([]);                   // 💸 every market building is ACTIVE: tap → its own in-place desk / swap
  expect(marketVitals({ mk: p.markets[0].key }, p).act.word).toMatch(/^⚡ /);
  const pools = p.markets.filter(m => m.pool); expect(new Set(pools.map(m => m.key)).size).toBe(pools.length);
  expect(pools.some(m => m.name === 'DUST')).toBe(false);                                         // under $100K TVL never stands
  expect(pools.some(m => m.key === 'pool-H1')).toBe(false);                                        // already in an outer city's district → fresh ones first
  expect(p.markets.filter(m => m.island === 'clmm').every(m => m.kind === 'v3')).toBe(true); expect(p.markets.filter(m => m.island === 'vault').every(m => m.kind === 'vault')).toBe(true);
  expect(p.markets.filter(m => m.island === 'flats')).toHaveLength(6); expect(p.markets.filter(m => m.island === 'lend').map(m => m.kind)).toEqual(['lend', 'lend', 'rwa', 'rwa', 'lend', 'lend', 'lend'].slice(0, p.markets.filter(m => m.island === 'lend').length));
  expect(p.markets.filter(m => m.island === 'flats')[0].apy).toBeGreaterThan(0);                  // a paying pool before a 0 % one
  for (const k of ['mymoney', 'feebank']) expect(p.places.find(x => x.key === k).isl).toBe('fee');   // the desk's money street downtown
  expect(p.places.find(x => x.key === 'trades')).toBeUndefined();   // 🚪 the Trade Center is a room of Pump Radar now (owner 2026-10-27), not a building
  expect(p.places.find(x => x.key === 'sleep')).toBeUndefined(); expect(p.places.find(x => x.key === 'pools').isl).toBe('row');   // 🚪 the Night Vault is a room of the Pool Hall (owner 2026-10-27)
  // with no pool hub the city still stands — districts fall back to parks
  const bare = feePlan(V, MK); expect(bare.spare.every(x => x.park)).toBe(true); expect(bare.markets.length).toBe(MK.markets.length);
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

test('🛣 FEELESS AVENUE north of downtown (its tools + the perps strip); the Heights gate past it; every tool still a place', () => {
  const p = feePlan(V, MK, POOLS); const ave = p.islands.find(i => i.key === 'ave'); const cap = p.islands.find(i => i.key === 'fee');
  expect(p.places.filter(x => x.tool).map(x => x.lens).sort()).toEqual(['feebank', 'feecat', 'mymoney', 'perps', 'pumpradar', 'rep', 'tt']);
  for (const k of ['pumpradar', 'court', 'feecat', 'perps']) expect(p.places.find(x => x.key === k).isl).toBe('ave');
  expect(new Set(PLACES.map(x => x.lens)).size).toBe(PLACES.length);                                  // one lens per place (the Wire keeps 'feed')
  expect(ave.z + ave.d).toBeLessThan(cap.z);                                                         // north of downtown, water between
  expect(p.bridges.find(b => b.key === 'b-ave-fee')).toMatchObject({ axis: 'z', a: ave.z + ave.d, b: cap.z });
  expect(p.gates.find(g => g.key === 'heights').b).toBe(ave.z);
});

test('🌳 more space: every cell is bigger than the building on it, the canals and the open water are wide, the metro is SimCity big', () => {
  expect(FOOT.lot).toBeLessThan(CELL - 1); expect(FOOT.tower).toBeLessThan(MCELL - 1.5);
  const p = feePlan(V, MK, POOLS); const cap = p.islands[0]; const row = p.islands.find(i => i.key === 'row');
  expect(row.x - (cap.x + cap.w)).toBeGreaterThanOrEqual(12);                                         // a canal between downtown and DEX Row
  expect(cap.w).toBeGreaterThanOrEqual(60); expect(p.view.x1 - p.view.x0).toBeGreaterThan(200);       // downtown alone 67 wide; the metro > 200
  const key = p.islands.find(i => i.key === 'key-rose'); const clmm = p.islands.find(i => i.key === 'clmm'); expect(clmm.x - (key.x + key.w)).toBeGreaterThanOrEqual(22);   // keys sit OFF the capital
  const q = outerPlan(V, 'harbor'); expect(q.islands[1].x - (q.islands[0].x + q.islands[0].w)).toBeGreaterThanOrEqual(22);
});

test('🌆 Fee City BREATHES: duplicates are rooms inside one building, TT is ONE tower, empty cells are parks', () => {
  const p = feePlan(V, MK, POOLS);
  expect(p.spare.every(x => x.park)).toBe(true);
  expect(p.inside.find(x => x.key === 'ranked')).toMatchObject({ host: 'podium', rect: p.places.find(x => x.key === 'podium').rect });
  expect(spotOf(p, { place: 'raids' })).toEqual(centerOf(p.places.find(x => x.key === 'warroom').rect));
  expect(roomsOf('raids').map(x => x.key)).toEqual(['warroom', 'raids', 'cartels']); expect(roomsOf('rc').map(x => x.key)).toEqual(['hq', 'jobs', 'gym', 'cards']);
  expect(roomsOf('tt').map(x => x.key)).toEqual(['tt']);
  const tt = p.places.find(x => x.key === 'tt'); const mkt = p.markets[0];
  expect(tt.rect.w * tt.rect.d).toBeGreaterThan(4 * mkt.rect.w * mkt.rect.d); expect(FOOT.tt).toBeGreaterThan(2 * FOOT.tower - 1); expect(Math.min(tt.rect.w, tt.rect.d)).toBeGreaterThan(FOOT.tt);
  expect(ttLive([])).toMatchObject({ n: 0, ready: 0, hot: null }); expect(ttLive([{ sym: 'A', ch: 2 }, { sym: 'B', ch: 9, status: 'ready' }])).toMatchObject({ ready: 1, hot: { sym: 'B' } });
});
