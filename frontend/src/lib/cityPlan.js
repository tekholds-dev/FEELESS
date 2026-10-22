// 🗺 THE CITY PLAN (pure — no three.js, no DOM): turns the Familia world (`/familia-world`) + the live markets (`/familia-markets`) into a
// tile map the 3D engine (lib/cityEngine.js) draws. 1 unit = 1 road tile. Owner, 2026-10-21/22: "FEE CITY ×3 bigger, the game lives IN the
// city — ~80 % of the buildings are REAL MARKETS with live vitals, lenses become places you walk into, stoplights, a light per activity".
//
// FEE CITY = the capital (8 × 6 cells: 24 family plots ring the stadium, The House, the Creator's Mansion, Rug Shield HQ, the Launch Pad and
// Fee Plaza) + three market islands joined by bridges: MARKET ROW (east, the DEXes), VAULT DISTRICT (west, lend / perps / stake), NEW MONEY
// (south, today's top coins). The four outer cities are gates on the far shores. A cell = 2 × 2 tiles; roads run between every cell.
export const CELL = 2;
export const STEP = CELL + 1;   // a cell + its road
const spanOf = n => n * STEP + 1;   // n cells wide, roads on both sides
export const rectOf = (ox, oz, [c, r, w = 1, h = 1]) => ({ x: ox + 1 + c * STEP, z: oz + 1 + r * STEP, w: w * STEP - 1, d: h * STEP - 1 });
export const centerOf = r => ({ x: r.x + r.w / 2, z: r.z + r.d / 2 });

// the capital's own map (the same cells the CSS city used, so every plot id stays where the server put it)
export const FEE_PLOTS = [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [0, 1], [0, 2], [0, 3], [1, 3], [6, 3], [7, 3],
  [0, 4], [1, 4], [2, 4], [3, 4], [4, 4], [5, 4], [6, 4], [7, 4], [0, 5], [7, 5]];
export const FEE_MARKS = { arena: [2, 1, 4, 3], house: [1, 1, 1, 2], mansion: [6, 1, 2, 1], shield: [6, 2, 1, 1], launch: [7, 2, 1, 1] };
export const PLAZA = [1, 5, 6, 1];
const CAP = { cols: 8, rows: 6 };

// 📍 the game's places — every old lens is a building you walk into
export const PLACES = [
  { key: 'ranked', lens: 'ranked', name: 'THE LADDER', sub: 'ranked · Street Rat → Kingpin', isl: 'row', art: 'tower', color: '#d4af37' },
  { key: 'raids', lens: 'raids', name: 'THE PRECINCT', sub: 'raids · live + the war log', isl: 'vault', art: 'precinct', color: '#ff5d73' },
  { key: 'rewards', lens: 'shop', name: 'PAWN & GOLD', sub: 'rewards · MP → FEECAT', isl: 'vault', art: 'pawn', color: '#f5c451' },
  { key: 'jobs', lens: 'jobs', name: 'JOB BOARD', sub: 'errands · tap / drag jobs', isl: 'plaza', art: 'board', color: '#45e486' },
  { key: 'gym', lens: 'rc', name: 'THE GYM', sub: 'challenges · win recruits', isl: 'money', art: 'gym', color: '#6ad7ff' },
  { key: 'cards', lens: 'deck', name: 'CARD ROOM', sub: 'your crew deck', isl: 'money', art: 'casino', color: '#b388ff' },
  { key: 'cartels', lens: 'cartels', name: 'CARTEL WAREHOUSE', sub: 'bundlers · snipers · funders', isl: 'money', art: 'warehouse', color: '#3ddc84' },
];

// the market islands: where each one sits next to the capital, its size in cells, which markets fill it
export const ISLANDS = {
  row: { name: 'MARKET ROW', sub: 'the DEXes · pools live', cols: 3, rows: 2, kinds: ['dex'], color: '#45e486' },
  vault: { name: 'VAULT DISTRICT', sub: 'lend · perps · stake', cols: 5, rows: 2, kinds: ['lend', 'perps', 'stake'], color: '#f5c451' },
  money: { name: 'NEW MONEY', sub: "today's top coins", cols: 5, rows: 3, kinds: ['coin'], color: '#ff8fa3' },
};
const GAP = 8;   // water between islands

// pure: compact $ (TVL / volume / caps)
export const usd = v => { const n = Number(v); if (!Number.isFinite(n) || n <= 0) return '—'; return n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${Math.round(n)}`; };
// pure: how fast a market's activity light pulses (0.4 – 2.4 Hz) from its 24h volume (or its TVL when no volume is known)
export const pulseHz = m => { const v = Number(m?.pool?.vol) || Number(m?.vol) || Number(m?.tvl) / 50 || 0; return Math.round((0.4 + Math.min(2, Math.log10(1 + v) / 4)) * 100) / 100; };
// pure: tower height (tiles) from TVL / market cap — a $1B DEX is a skyscraper, a fresh coin is a shop
export const heightOf = v => Math.round((1 + Math.min(4.2, Math.max(0, Math.log10(1 + (Number(v) || 0)) - 4) * 0.85)) * 100) / 100;
export const hash = s => { let h = 7; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };

// a city's roads: every grid line of an island, cut where a landmark / plaza spans it → straight lane segments + crossings
function roadsOf(ox, oz, cols, rows, solid = []) {
  const W = spanOf(cols); const D = spanOf(rows); const segs = []; const nodes = [];
  const inside = (x, z) => solid.some(r => x > r.x - 0.5 && x < r.x + r.w + 0.5 && z > r.z - 0.5 && z < r.z + r.d + 0.5);
  for (let i = 0; i <= cols; i += 1) { const x = ox + i * STEP + 0.5; let start = null;
    for (let z = oz; z <= oz + D; z += 0.5) { const ok = z < oz + D && !inside(x, z); if (ok && start == null) start = z; if (!ok && start != null) { segs.push({ axis: 'z', x, z0: start, z1: z }); start = null; } } }
  for (let j = 0; j <= rows; j += 1) { const z = oz + j * STEP + 0.5; let start = null;
    for (let x = ox; x <= ox + W; x += 0.5) { const ok = x < ox + W && !inside(x, z); if (ok && start == null) start = x; if (!ok && start != null) { segs.push({ axis: 'x', z, x0: start, x1: x }); start = null; } } }
  for (let i = 0; i <= cols; i += 1) for (let j = 0; j <= rows; j += 1) { const x = ox + i * STEP + 0.5; const z = oz + j * STEP + 0.5; if (!inside(x, z)) nodes.push({ x, z, edge: i === 0 || j === 0 || i === cols || j === rows }); }
  return { segs, nodes };
}

// a car loop: a rectangle on road centre lines; cars drive its edges, holding at red lights on the way
const loop = (x0, z0, x1, z1) => [[x0, z0], [x1, z0], [x1, z1], [x0, z1]];

function island(key, ox, oz, cols, rows, extra = {}) {
  return { key, x: ox, z: oz, w: spanOf(cols), d: spanOf(rows), cols, rows, ...extra };
}

// pure: the Fee City plan. `v` = the world payload, `mk` = { markets, coins } (either may be missing — the city still draws)
export function feePlan(v, mk) {
  const markets = (mk?.markets || []).slice(); const coins = (mk?.coins || []).slice(0, 12);
  const capW = spanOf(CAP.cols); const capD = spanOf(CAP.rows);
  const cap = island('fee', 0, 0, CAP.cols, CAP.rows, { name: 'FEE CITY', sub: 'capital of the trenches', color: '#d4af37', capital: true });
  const pos = {
    row: { x: capW + GAP, z: Math.round((capD - spanOf(ISLANDS.row.rows)) / 2) },
    vault: { x: -GAP - spanOf(ISLANDS.vault.cols), z: Math.round((capD - spanOf(ISLANDS.vault.rows)) / 2) },
    money: { x: Math.round((capW - spanOf(ISLANDS.money.cols)) / 2), z: capD + GAP },
  };
  const isl = [cap, ...Object.entries(ISLANDS).map(([k, s]) => island(k, pos[k].x, pos[k].z, s.cols, s.rows, { name: s.name, sub: s.sub, color: s.color }))];
  const byKey = Object.fromEntries(isl.map(i => [i.key, i]));
  // family plots (server ids fee-*) on the capital
  const blocks = (v?.blocks || []).filter(b => b.b === 'fee');
  const lots = blocks.map(b => ({ id: b.id, pick: { id: b.id }, kind: b.mine ? 'mine' : b.kind === 'cpu' ? 'cpu' : b.kind === 'cartel' ? 'cartel' : b.owner ? 'family' : 'free',
    tag: b.tag || null, owner: b.owner || null, home: !!b.home, power: b.power || 0, rect: rectOf(0, 0, FEE_PLOTS[b.i] || [0, 0]), seed: hash(b.id) }));
  const marks = Object.entries(FEE_MARKS).map(([k, c]) => { const m = (v?.landmarks || []).find(l => l.key === k); return { key: k, pick: { lm: k }, name: m?.name || k.toUpperCase(), live: m?.live || null, rect: rectOf(0, 0, c) }; });
  const plaza = rectOf(0, 0, PLAZA);
  // markets onto their islands, biggest first; then the places; an island never overflows (the rest wait for a bigger city)
  const slots = { row: [], vault: [], money: [] };
  for (const k of Object.keys(ISLANDS)) { const s = ISLANDS[k]; for (let r = 0; r < s.rows; r += 1) for (let c = 0; c < s.cols; c += 1) slots[k].push([c, r]); }
  const take = k => slots[k].shift();
  const placesOn = k => PLACES.filter(p => p.isl === k);
  const mk_ = [];
  for (const k of Object.keys(ISLANDS)) {
    const want = k === 'money' ? coins.map(c => ({ ...c, kind: 'coin', key: `coin-${c.mint || c.sym}`, name: (c.sym || c.symbol) ? `$${c.sym || c.symbol}` : c.name, tvl: c.mc || c.liq }))
      : markets.filter(m => ISLANDS[k].kinds.includes(m.kind)).sort((a, b) => (b.tvl || 0) - (a.tvl || 0));
    const room = slots[k].length - placesOn(k).length;
    want.slice(0, room).forEach(m => { const c = take(k); const r = rectOf(byKey[k].x, byKey[k].z, c);
      mk_.push({ key: m.key, pick: { mk: m.key }, kind: m.kind, name: m.name, tvl: m.tvl, move: m.move ?? m.ch ?? m.change ?? null, hz: pulseHz(m), h: heightOf(m.tvl), rect: r, island: k, m }); });
  }
  const places = PLACES.map(p => {
    if (p.isl === 'plaza') return { ...p, pick: { place: p.key }, rect: { x: plaza.x + plaza.w - 4, z: plaza.z, w: 4, d: plaza.d } };
    const c = take(p.isl); return c ? { ...p, pick: { place: p.key }, rect: rectOf(byKey[p.isl].x, byKey[p.isl].z, c) } : null; }).filter(Boolean);
  // empty market slots still hold a building (a lot "coming soon"), never a hole
  const spare = Object.entries(slots).flatMap(([k, cs]) => cs.map(c => ({ key: `spare-${k}-${c.join('-')}`, island: k, rect: rectOf(byKey[k].x, byKey[k].z, c) })));
  // roads: the capital cut by its landmarks + plaza; the islands are full grids
  const solid = [...marks.map(m => m.rect), plaza];
  const roads = isl.map(i => ({ key: i.key, ...roadsOf(i.x, i.z, i.cols, i.rows, i.key === 'fee' ? solid : []) }));
  // bridges: capital ↔ each market island (road centre lines line up with a crossing) + the gates to the outer cities on the far shores
  const midZ = i => i.z + STEP * Math.floor(i.rows / 2) + 0.5; const midX = i => i.x + STEP * Math.floor(i.cols / 2) + 0.5;
  const capMidZ = STEP * 3 + 0.5; const capMidX = STEP * 4 + 0.5;
  const bridges = [
    { key: 'b-row', axis: 'x', z: capMidZ, a: capW, b: byKey.row.x, name: 'Fee Street Bridge' },
    { key: 'b-vault', axis: 'x', z: capMidZ, a: byKey.vault.x + byKey.vault.w, b: 0, name: 'Vault Bridge' },
    { key: 'b-money', axis: 'z', x: capMidX, a: capD, b: byKey.money.z, name: 'New Money Bridge' },
  ];
  const cityName = k => (v?.cities || []).find(c => c.key === k);
  const gates = [
    { key: 'heights', axis: 'z', x: capMidX, a: -GAP, b: 0, at: 'n' },
    { key: 'bay', axis: 'x', z: midZ(byKey.row), a: byKey.row.x + byKey.row.w, b: byKey.row.x + byKey.row.w + GAP, at: 'e' },
    { key: 'harbor', axis: 'x', z: midZ(byKey.vault), a: byKey.vault.x - GAP, b: byKey.vault.x, at: 'w' },
    { key: 'docks', axis: 'z', x: midX(byKey.money), a: byKey.money.z + byKey.money.d, b: byKey.money.z + byKey.money.d + GAP, at: 's' },
  ].map(g => ({ ...g, name: cityName(g.key)?.name || g.key.toUpperCase(), held: cityName(g.key) ? `${cityName(g.key).held}/${cityName(g.key).plots} held` : '' }));
  // stoplights where the avenues cross inside the capital + one at each bridge head
  const lights = roads[0].nodes.filter(n => !n.edge && (Math.round(n.x - 0.5) % (STEP * 2) === 0 || Math.round(n.z - 0.5) % (STEP * 2) === 0)).slice(0, 14)
    .concat([{ x: capW - 0.5, z: capMidZ }, { x: 0.5, z: capMidZ }, { x: capMidX, z: capD - 0.5 }]);
  // car loops: the capital ring, two inner avenues, each island's ring
  const loops = [loop(0.5, 0.5, capW - 0.5, capD - 0.5), loop(0.5, STEP * 4 + 0.5, capW - 0.5, capD - 0.5), loop(STEP * 6 + 0.5, 0.5, capW - 0.5, STEP * 3 + 0.5),
    ...isl.slice(1).map(i => loop(i.x + 0.5, i.z + 0.5, i.x + i.w - 0.5, i.z + i.d - 0.5))];
  const W0 = Math.min(...isl.map(i => i.x)) - GAP; const W1 = Math.max(...isl.map(i => i.x + i.w)) + GAP;
  const D0 = Math.min(...isl.map(i => i.z)) - GAP; const D1 = Math.max(...isl.map(i => i.z + i.d)) + GAP;
  return { kind: 'fee', islands: isl, lots, marks, plaza, markets: mk_, places, spare, roads, bridges, gates, lights, loops,
    bounds: { x0: W0, x1: W1, z0: D0, z1: D1 }, center: { x: capW / 2, z: capD / 2 + 4 } };
}

// pure: an outer city's plan — its boroughs as 4 × 4 islands joined by bridges, a gate back to Fee City
export function outerPlan(v, cityKey) {
  const city = (v?.cities || []).find(c => c.key === cityKey); if (!city) return null;
  const bors = (v?.boroughs || []).filter(b => city.boroughs.includes(b.key)); if (!bors.length) return null;
  const c0 = Math.min(...bors.map(b => b.col)); const r0 = Math.min(...bors.map(b => b.row)); const S = spanOf(4);
  const isl = bors.map(b => island(b.key, (b.col - c0) * (S + GAP), (b.row - r0) * (S + GAP), 4, 4, { name: b.name, sub: `×${b.tier} production`, color: '#b388ff', boom: v?.boom?.borough === b.key }));
  const lots = (v?.blocks || []).filter(x => city.boroughs.includes(x.b)).map(x => { const i = isl.find(k => k.key === x.b);
    return { id: x.id, pick: { id: x.id }, kind: x.mine ? 'mine' : x.kind === 'cpu' ? 'cpu' : x.kind === 'cartel' ? 'cartel' : x.owner ? 'family' : 'free', tag: x.tag || null, owner: x.owner || null, home: !!x.home,
      power: x.power || 0, rect: rectOf(i.x, i.z, [x.i % 4, Math.floor(x.i / 4)]), seed: hash(x.id) }; });
  const roads = isl.map(i => ({ key: i.key, ...roadsOf(i.x, i.z, 4, 4) }));
  const bridges = (v?.bridges || []).map(br => { const a = isl.find(i => i.key === br.a); const b = isl.find(i => i.key === br.b); if (!a || !b) return null;
    if (a.z === b.z) { const [l, r] = a.x < b.x ? [a, b] : [b, a]; return { key: br.name, axis: 'x', z: l.z + STEP * 2 + 0.5, a: l.x + l.w, b: r.x, name: br.name }; }
    const [t, u] = a.z < b.z ? [a, b] : [b, a]; return { key: br.name, axis: 'z', x: t.x + STEP * 2 + 0.5, a: t.z + t.d, b: u.z, name: br.name }; }).filter(Boolean);
  const west = isl.reduce((m, i) => (i.x < m.x ? i : m), isl[0]);
  const fee = (v?.cities || []).find(c => c.key === 'fee');
  const gates = fee ? [{ key: 'fee', axis: 'x', z: west.z + STEP * 2 + 0.5, a: west.x - GAP, b: west.x, at: 'w', name: 'FEE CITY', held: `${fee.held}/${fee.plots} held` }] : [];
  const lights = roads.flatMap(r => r.nodes.filter(n => !n.edge).slice(0, 2));
  const loops = isl.map(i => loop(i.x + 0.5, i.z + 0.5, i.x + i.w - 0.5, i.z + i.d - 0.5));
  const X1 = Math.max(...isl.map(i => i.x + i.w)); const Z1 = Math.max(...isl.map(i => i.z + i.d));
  return { kind: 'outer', key: cityKey, name: city.name, islands: isl, lots, marks: [], plaza: null, markets: [], places: [], spare: [], roads, bridges, gates, lights, loops,
    bounds: { x0: -GAP * 2, x1: X1 + GAP, z0: -GAP, z1: Z1 + GAP }, center: { x: X1 / 2, z: Z1 / 2 } };
}

// pure: where the camera looks for a picked thing (plot id, landmark, market, place)
export function spotOf(plan, sel) {
  if (!plan || !sel) return null;
  const hit = sel.id ? plan.lots.find(l => l.id === sel.id) : sel.lm ? plan.marks.find(m => m.key === sel.lm) : sel.mk ? plan.markets.find(m => m.key === sel.mk) : sel.place ? plan.places.find(p => p.key === sel.place) : null;
  return hit ? centerOf(hit.rect) : null;
}
