// 🗺 THE CITY PLAN (pure — no three.js, no DOM): turns the Familia world (`/familia-world`), the live markets (`/familia-markets`) and the Pool
// Hub (`/familia-pools`) into a tile map the 3D engine (lib/cityEngine.js) draws. 1 unit = 1 road tile.
// Owner, 2026-10-21/22: "FEE CITY ×3 bigger, the game lives IN the city — real markets with live vitals, lenses become places, stoplights" ·
// "some areas too congested — no land, no pizza spots; everything outside the heart (Fee City) big af; every outer city has real-money pools".
//
// An island = a GRID of cells (roads between every cell) inside a ring of open LAND (parks, food stalls, a promenade). Family plots are 3 × 3
// tiles; market towers sit on 4 × 4 cells. FEE CITY = the capital (8 × 6 cells: 24 family plots ring the stadium, The House, the Creator's
// Mansion, Rug Shield HQ, the Launch Pad and Fee Plaza) + three market islands over bridges: MARKET ROW (east: the DEXes + the Pool Hall),
// VAULT DISTRICT (west: lend / perps / stake), NEW MONEY (south: today's top coins), FEELESS AVENUE (north: every FEELESS tool as a building
// you walk into — Pump Radar, Runners, the Watchtower, Rep, FeeCat, Fuel, the Newsstand, the $FEE Bank). Each outer city = its boroughs + its
// own POOL DISTRICT. Owner, 2026-10-22: "Fee City 2× bigger, the bridged towns need more space instead of every building side by side" →
// cells are bigger than the buildings on them (FOOT): every building stands in its own yard, with wider land rings and wider water.
// Owner, 2026-10-23: "Fee City BREATHES — far fewer, bigger, spaced-out buildings; every useless / duplicate building cut; open land between
// districts" → one building can hold several rooms (`in`: the Ladder is a room of the Podium, the Precinct + the Cartel Warehouse are rooms of
// the War Room, the Gym / Card Room / Job Board are rooms of your HQ …); the Trench Towers are ONE landmark tower on their own island; market
// islands keep their top 4 by TVL; an empty cell is a PARK, never a filler building. ~47 buildings off the capital → 18.
export const CELL = 5;        // a family plot
export const MCELL = 8;       // a market tower
export const TCELL = 9;       // 🗼 the Trench Towers island (2 × 2 of these, one tower over all four)
export const LAND = 6;        // the open land ring around every island grid
const GAP = 22;               // water between islands
export const FOOT = { lot: 3.4, tower: 5.4, tt: 11 };   // the most a building covers of its cell — the rest is its yard (grass, trees)
export const stepOf = cell => cell + 1;
export const STEP = stepOf(CELL);
const spanOf = (n, cell = CELL) => n * stepOf(cell) + 1;
// a cell [c, r, w, h] on a grid whose origin is (gx, gz) → a rect in tiles
export const rectOf = (gx, gz, [c, r, w = 1, h = 1], cell = CELL) => { const s = stepOf(cell); return { x: gx + 1 + c * s, z: gz + 1 + r * s, w: w * s - 1, d: h * s - 1 }; };
export const centerOf = r => ({ x: r.x + r.w / 2, z: r.z + r.d / 2 });

// the capital's own map (the same cells the CSS city used, so every plot id stays where the server put it)
export const FEE_PLOTS = [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [0, 1], [0, 2], [0, 3], [1, 3], [6, 3], [7, 3],
  [0, 4], [1, 4], [2, 4], [3, 4], [4, 4], [5, 4], [6, 4], [7, 4], [0, 5], [7, 5]];
export const FEE_MARKS = { arena: [2, 1, 4, 3], house: [1, 1, 1, 2], mansion: [6, 1, 2, 1], shield: [6, 2, 1, 1], launch: [7, 2, 1, 1] };
export const PLAZA = [1, 5, 6, 1];
const CAP = { cols: 8, rows: 6 };

// 📍 the game's places — every old lens is a building you walk into; the Pool Hall opens the Pool Hub
export const PLACES = [
  { key: 'hq', lens: 'family', name: 'YOUR FAMILY HQ', sub: 'vitals · tools · expand', isl: 'home', art: 'hq', color: '#ffcc4d', virtual: true },
  { key: 'warroom', lens: 'wars', name: 'THE WAR ROOM', sub: 'call-outs · live wars', isl: 'vault', art: 'war', color: '#ff4d5e' },
  { key: 'podium', lens: 'board', name: 'THE PODIUM', sub: 'weekly crowns', isl: 'row', art: 'podium', color: '#ffd36b' },
  { key: 'wire', lens: 'feed', name: 'THE WIRE', sub: 'every family move, live', isl: 'plaza-l', art: 'board', color: '#45e4c8' },
  { key: 'pools', lens: 'pools', name: 'THE POOL HALL', sub: 'every top + rising pool', isl: 'row', art: 'hall', color: '#45e4c8' },
  { key: 'ranked', lens: 'ranked', name: 'THE LADDER', sub: 'ranked · Street Rat → Kingpin', in: 'podium', art: 'tower', color: '#d4af37' },
  { key: 'raids', lens: 'raids', name: 'THE PRECINCT', sub: 'raids · live + the war log', in: 'warroom', art: 'precinct', color: '#ff5d73' },
  { key: 'rewards', lens: 'shop', name: 'PAWN & GOLD', sub: 'rewards · MP → FEECAT', isl: 'vault', art: 'pawn', color: '#f5c451' },
  { key: 'jobs', lens: 'jobs', name: 'JOB BOARD', sub: 'errands · MP every few minutes', in: 'hq', art: 'board', color: '#45e486' },
  { key: 'gym', lens: 'rc', name: 'THE GYM', sub: 'challenges · win recruits', in: 'hq', art: 'gym', color: '#6ad7ff' },
  { key: 'cards', lens: 'deck', name: 'CARD ROOM', sub: 'your crew deck', in: 'hq', art: 'casino', color: '#b388ff' },
  { key: 'cartels', lens: 'cartels', name: 'CARTEL WAREHOUSE', sub: 'bundlers · snipers · funders', in: 'warroom', art: 'warehouse', color: '#3ddc84' },
  // 🗼 TT — ONE landmark tower on its own island (owner, 2026-10-23): READY coins lit on its floors, the hottest coin on its crown; one pop-out
  { key: 'tt', lens: 'tt', name: 'TRENCH TOWERS', sub: "the desk's intake list · trade it right here", isl: 'money', art: 'tt', color: '#ff8fa3', tool: true },
  // 🛣 FEELESS AVENUE — the site's best tools as buildings: each pops out its live vitals + quick tools (`tool: true`, `page` = its full page)
  { key: 'pumpradar', lens: 'pumpradar', name: 'PUMP RADAR', sub: 'hottest Pump coins · one-tap trade', isl: 'ave', art: 'radar', color: '#45e486', tool: true, page: '/terminal/pump' },
  { key: 'runners', lens: 'runners', name: 'RUNNERS TRACK', sub: "FEELESS's live runner calls", in: 'pumpradar', art: 'track', color: '#ff9f45', tool: true, page: '/terminal/fuse?tab=runners' },
  { key: 'watch', lens: 'watch', name: 'THE WATCHTOWER', sub: 'your watchlist · signal alerts', in: 'court', art: 'watch', color: '#6ad7ff', tool: true, page: '/terminal/watchlist' },
  { key: 'court', lens: 'rep', name: 'REP COURTHOUSE', sub: 'case files · check anyone', isl: 'ave', art: 'court', color: '#d4af37', tool: true, page: '/terminal/reputation' },
  { key: 'feecat', lens: 'feecat', name: 'FEECAT TOWER', sub: 'the trading cat, live', isl: 'ave', art: 'cat', color: '#b388ff', tool: true, page: '/terminal/feecat' },
  { key: 'fuel', lens: 'gas', name: 'FUEL STATION', sub: 'gas on 12 chains', in: 'feebank', art: 'fuel', color: '#ffd36b', tool: true, page: '/terminal/trade' },
  { key: 'news', lens: 'feedx', name: 'THE NEWSSTAND', sub: 'FEEd · every call, live', in: 'wire', art: 'news', color: '#45e4c8', tool: true },
  { key: 'feebank', lens: 'feebank', name: 'THE $FEE BANK', sub: '$FEE · rFEE · FEECAT — buys fee-free', isl: 'ave', art: 'bank', color: '#15d16a', tool: true, page: '/terminal/fee' },
  { key: 'perps', lens: 'perps', name: 'THE PERPS DESK', sub: 'perps markets live · funding · leverage', isl: 'ave', art: 'perps', color: '#ff5dbb', tool: true },
  { key: 'trades', lens: 'trades', name: 'THE TRADE CENTER', sub: 'the desk\'s real-money trades · live P&L', isl: 'ave', art: 'trade', color: '#45e486', tool: true },
  { key: 'sleep', lens: 'sleep', name: 'THE NIGHT VAULT', sub: 'money while you sleep · live APY', isl: 'ave', art: 'sleep', color: '#9b8cff', tool: true },
];
// 🚪 the rooms of one building: the host first, then every place that lives inside it (`in`)
export const roomsOf = key => { const p = PLACES.find(x => x.key === key || x.lens === key); const host = p?.in || p?.key; return host ? PLACES.filter(x => x.key === host || x.in === host) : []; };

// the market islands: size in cells, which markets fill them (top `top` by TVL — the rest are a tap away in the Pool Hall)
export const ISLANDS = {
  row: { name: 'MARKET ROW', sub: 'the DEXes · pools live', cols: 3, rows: 2, kinds: ['dex'], top: 4, color: '#45e486' },
  vault: { name: 'VAULT DISTRICT', sub: 'lend · perps · stake', cols: 3, rows: 2, kinds: ['lend', 'perps', 'stake'], top: 4, color: '#f5c451' },
  money: { name: 'TT · TRENCH TOWERS', sub: "the desk's intake list · one tower", cols: 2, rows: 2, kinds: [], cell: TCELL, color: '#ff8fa3' },
  ave: { name: 'FEELESS AVENUE', sub: 'the FEELESS tools · one tap', cols: 4, rows: 2, kinds: [], color: '#15d16a' },
};
// 🗼 the TT tower's live crown: READY count (lit floors) + the hottest coin (`coins` = the intake list)
export function ttLive(coins) {
  const cs = (coins || []).filter(c => c && (c.sym || c.symbol)); const ready = cs.filter(c => String(c.status || '').toUpperCase() === 'READY').length;
  const hot = cs.slice().sort((a, b) => (Number(b.ch) || -1e9) - (Number(a.ch) || -1e9))[0] || null;
  return { n: cs.length, ready, hot: hot ? { sym: hot.sym || hot.symbol, ch: hot.ch ?? null, pair: hot.pair || null, mint: hot.mint || null } : null, top: cs.slice(0, 3).map(c => ({ sym: c.sym || c.symbol, ch: c.ch ?? null })) };
}
// each outer city's pool district (the Pool Hub's `cities`)
export const DISTRICTS = {
  harbor: { name: 'HARBOR POOLS', sub: 'v2 · constant product', color: '#ff9f45' }, heights: { name: 'HEIGHTS LIQUIDITY', sub: 'v3 · concentrated', color: '#6ad7ff' },
  bay: { name: 'BAY BINS + STAKES', sub: 'DLMM · liquid staking', color: '#ffd36b' }, docks: { name: 'THE LAUNDROMAT', sub: 'vaults · lending · RWA', color: '#3ddc84' },
};
// 🏛 each outer city's CITY HALL — that platform's live tools in a click (a radar of its own launchpad board, or the Rep court for the docks)
export const HALLS = {
  harbor: { name: 'PUMP HALL', sub: 'Pump.fun live · one-tap trade', art: 'radar', color: '#45e486', scope: 'pump' },
  heights: { name: 'RAYDIUM HALL', sub: 'LaunchLab live · one-tap trade', art: 'radar', color: '#6ad7ff', scope: 'raydium' },
  bay: { name: 'BONK HALL', sub: 'LetsBONK live · one-tap trade', art: 'radar', color: '#ffd36b', scope: 'bonk' },
  docks: { name: 'DOCKS COURT', sub: 'the cartels caught this week', art: 'court', color: '#3ddc84', scope: null },
};
export const POOL_KIND = { v2: 'V2 · AMM', v3: 'V3 · CLMM', dlmm: 'DLMM', vault: 'AUTO-COMPOUND VAULT', lend: 'LENDING', stake: 'LIQUID STAKING', perps: 'PERPS', rwa: 'RWA' };

// pure: compact $ (TVL / volume / caps)
export const usd = v => { const n = Number(v); if (!Number.isFinite(n) || n <= 0) return '—'; return n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${Math.round(n)}`; };
export const apyTxt = v => (v == null || !Number.isFinite(Number(v)) ? '—' : `${Number(v) >= 100 ? Math.round(v) : Number(v).toFixed(1)}%`);
// pure: how fast a market's activity light pulses (0.4 – 2.4 Hz) from its 24h volume (or its TVL when no volume is known)
export const pulseHz = m => { const v = Number(m?.pool?.vol) || Number(m?.vol) || Number(m?.tvl) / 50 || 0; return Math.round((0.4 + Math.min(2, Math.log10(1 + v) / 4)) * 100) / 100; };
// pure: tower height (tiles) from TVL / market cap — a $1B DEX is a skyscraper, a fresh coin is a shop
export const heightOf = v => Math.round((1 + Math.min(4.2, Math.max(0, Math.log10(1 + (Number(v) || 0)) - 4) * 0.85)) * 100) / 100;
export const hash = s => { let h = 7; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };

// an island: its open land (x, z, w, d) around a grid of cells whose origin is (gx, gz)
function island(key, gx, gz, cols, rows, cell, extra = {}) {
  return { key, gx, gz, cols, rows, cell, gw: spanOf(cols, cell), gd: spanOf(rows, cell), x: gx - LAND, z: gz - LAND, w: spanOf(cols, cell) + 2 * LAND, d: spanOf(rows, cell) + 2 * LAND, ...extra };
}
// the grid's road centre line k (0 … cols / rows)
const lineX = (i, k) => i.gx + k * stepOf(i.cell) + 0.5;
const lineZ = (i, k) => i.gz + k * stepOf(i.cell) + 0.5;

// a grid's roads: every grid line, cut where a landmark / plaza spans it → straight lane segments + crossings
function roadsOf(i, solid = []) {
  const { gx, gz, cols, rows, gw: W, gd: D } = i; const segs = []; const nodes = [];
  const inside = (x, z) => solid.some(r => x > r.x - 0.5 && x < r.x + r.w + 0.5 && z > r.z - 0.5 && z < r.z + r.d + 0.5);
  for (let k = 0; k <= cols; k += 1) { const x = lineX(i, k); let start = null;
    for (let z = gz; z <= gz + D; z += 0.5) { const ok = z < gz + D && !inside(x, z); if (ok && start == null) start = z; if (!ok && start != null) { segs.push({ axis: 'z', x, z0: start, z1: z }); start = null; } } }
  for (let j = 0; j <= rows; j += 1) { const z = lineZ(i, j); let start = null;
    for (let x = gx; x <= gx + W; x += 0.5) { const ok = x < gx + W && !inside(x, z); if (ok && start == null) start = x; if (!ok && start != null) { segs.push({ axis: 'x', z, x0: start, x1: x }); start = null; } } }
  for (let k = 0; k <= cols; k += 1) for (let j = 0; j <= rows; j += 1) { const x = lineX(i, k); const z = lineZ(i, j); if (!inside(x, z)) nodes.push({ x, z, edge: k === 0 || j === 0 || k === cols || j === rows }); }
  return { key: i.key, segs, nodes };
}
// a car loop: a rectangle on road centre lines; cars drive its edges, holding at red lights on the way
const loop = (x0, z0, x1, z1) => [[x0, z0], [x1, z0], [x1, z1], [x0, z1]];
const ringOf = i => loop(lineX(i, 0), lineZ(i, 0), lineX(i, i.cols), lineZ(i, i.rows));

// a pool-hub row → a building in a district
function poolMarket(r, rect, isl) {
  return { key: `pool-${r.id}`, pick: { mk: `pool-${r.id}` }, kind: r.kind, pool: true, name: r.sym, proto: r.proto, tvl: r.tvl, apy: r.apy, move: r.ch ?? null,
    hz: pulseHz({ vol: r.vol, tvl: r.tvl }), h: heightOf(r.tvl) * 1.15, rect, island: isl, m: r };
}

function boundsOf(isl) {
  return { x0: Math.min(...isl.map(i => i.x)) - GAP, x1: Math.max(...isl.map(i => i.x + i.w)) + GAP, z0: Math.min(...isl.map(i => i.z)) - GAP, z1: Math.max(...isl.map(i => i.z + i.d)) + GAP };
}

// pure: the Fee City plan. `v` = the world payload, `mk` = { markets, coins } (either may be missing — the city still draws)
export function feePlan(v, mk) {
  const markets = (mk?.markets || []).slice(); const coins = (mk?.coins || []).slice(0, 12); const tt = ttLive(coins);
  const cap = island('fee', 0, 0, CAP.cols, CAP.rows, CELL, { name: 'FEE CITY', sub: 'capital of the trenches', color: '#d4af37', capital: true });
  const midZ = lineZ(cap, 3); const midX = lineX(cap, 4); const sM = stepOf(MCELL);
  // market islands, placed so each bridge lands ON one of their avenues
  const row = island('row', cap.x + cap.w + GAP + LAND, midZ - 0.5 - sM * Math.floor(ISLANDS.row.rows / 2), ISLANDS.row.cols, ISLANDS.row.rows, MCELL, { name: ISLANDS.row.name, sub: ISLANDS.row.sub, color: ISLANDS.row.color });
  const vw = spanOf(ISLANDS.vault.cols, MCELL);
  const vault = island('vault', cap.x - GAP - LAND - vw, midZ - 0.5 - sM * Math.floor(ISLANDS.vault.rows / 2), ISLANDS.vault.cols, ISLANDS.vault.rows, MCELL, { name: ISLANDS.vault.name, sub: ISLANDS.vault.sub, color: ISLANDS.vault.color });
  const money = island('money', midX - 0.5 - stepOf(TCELL), cap.z + cap.d + GAP + LAND, ISLANDS.money.cols, ISLANDS.money.rows, TCELL, { name: ISLANDS.money.name, sub: tt.n ? `${tt.ready} READY · ${tt.n} on the intake` : ISLANDS.money.sub, color: ISLANDS.money.color });
  const ave = island('ave', midX - 0.5 - sM * Math.floor(ISLANDS.ave.cols / 2), cap.z - GAP - LAND - spanOf(ISLANDS.ave.rows, MCELL), ISLANDS.ave.cols, ISLANDS.ave.rows, MCELL, { name: ISLANDS.ave.name, sub: ISLANDS.ave.sub, color: ISLANDS.ave.color });
  const isl = [cap, row, vault, money, ave]; const byKey = { row, vault, money, ave };
  // family plots (server ids fee-*) on the capital
  const lots = (v?.blocks || []).filter(b => b.b === 'fee').map(b => ({ id: b.id, pick: { id: b.id }, kind: b.mine ? 'mine' : b.kind === 'cpu' ? 'cpu' : b.kind === 'cartel' ? 'cartel' : b.owner ? 'family' : 'free',
    tag: b.tag || null, owner: b.owner || null, home: !!b.home, power: b.power || 0, link: b.link || null, state: b.state || null, fundH: b.fundH ?? null, launch: b.launch || null, rect: rectOf(cap.gx, cap.gz, FEE_PLOTS[b.i] || [0, 0]), seed: hash(b.id) }));
  const marks = Object.entries(FEE_MARKS).map(([k, c]) => { const m = (v?.landmarks || []).find(l => l.key === k); return { key: k, pick: { lm: k }, name: m?.name || k.toUpperCase(), live: m?.live || null, rect: rectOf(cap.gx, cap.gz, c) }; });
  const plaza = rectOf(cap.gx, cap.gz, PLAZA);
  // markets onto their islands, biggest first; then the places; an island never overflows
  const slots = { row: [], vault: [], money: [], ave: [] };
  for (const k of ['row', 'vault', 'ave']) { const s = ISLANDS[k]; for (let r = 0; r < s.rows; r += 1) for (let c = 0; c < s.cols; c += 1) slots[k].push([c, r]); }
  const take = k => slots[k].shift();
  const placesOn = k => PLACES.filter(p => p.isl === k && !p.in);
  const at = (k, c) => rectOf(byKey[k].gx, byKey[k].gz, c, byKey[k].cell);
  const mk_ = [];
  for (const k of ['row', 'vault']) {
    const want = markets.filter(m => ISLANDS[k].kinds.includes(m.kind)).sort((a, b) => (b.tvl || 0) - (a.tvl || 0));
    const room = Math.min(ISLANDS[k].top || 99, slots[k].length - placesOn(k).length);
    want.slice(0, room).forEach(m => { const r = at(k, take(k));
      mk_.push({ key: m.key, pick: { mk: m.key }, kind: m.kind, name: m.name, tvl: m.tvl, move: m.move ?? m.ch ?? m.change ?? null, hz: pulseHz(m), h: heightOf(m.tvl) * 1.45, rect: r, island: k, m }); });
  }
  const home = lots.find(l => l.home && l.kind === 'mine');   // 🏠 your family HQ = your home block when it stands in Fee City, else the Mansion
  const ttRect = rectOf(money.gx, money.gz, [0, 0, 2, 2], TCELL);
  const places = PLACES.filter(p => !p.in).map(p => {
    if (p.isl === 'home') return { ...p, pick: { place: p.key }, rect: (home || marks.find(m => m.key === 'mansion')).rect };
    if (p.isl === 'plaza') return { ...p, pick: { place: p.key }, rect: { x: plaza.x + plaza.w - 7, z: plaza.z, w: 7, d: plaza.d } };
    if (p.isl === 'plaza-l') return { ...p, pick: { place: p.key }, rect: { x: plaza.x, z: plaza.z, w: 7, d: plaza.d } };
    if (p.key === 'tt') return { ...p, pick: { place: p.key }, rect: ttRect, live: tt, lines: [`🗼 ${p.name}`, tt.n ? `${tt.ready} READY · ${tt.n} on the intake` : p.sub, ...(tt.hot ? [`HOT $${tt.hot.sym}${tt.hot.ch != null ? ` ${tt.hot.ch >= 0 ? '+' : ''}${Number(tt.hot.ch).toFixed(1)}% 5m` : ''}`] : [])] };
    const c = take(p.isl); return c ? { ...p, pick: { place: p.key }, rect: at(p.isl, c) } : null; }).filter(Boolean);
  // 🚪 rooms inside another building: no building of their own — the camera flies to their host, the pop-out shows the host's rooms as tabs
  const inside = PLACES.filter(p => p.in).map(p => { const h = places.find(x => x.key === p.in); return h ? { ...p, pick: { place: p.key }, rect: h.rect, host: h.key } : null; }).filter(Boolean);
  // 🌳 an empty cell is a PARK (owner: "open land, not every building side by side") — the engine draws grass, trees, a lamp, no building
  const spare = Object.entries(slots).flatMap(([k, cs]) => cs.map(c => ({ key: `park-${k}-${c.join('-')}`, island: k, park: true, rect: at(k, c) })));
  const roads = isl.map(i => roadsOf(i, i.key === 'fee' ? [...marks.map(m => m.rect), plaza] : i.key === 'money' ? [ttRect] : []));
  // bridges land on avenues on both shores; the gates to the outer cities stand on the far shores
  const bridges = [
    { key: 'b-row', axis: 'x', z: midZ, a: cap.x + cap.w, b: row.x, name: 'Fee Street Bridge' },
    { key: 'b-vault', axis: 'x', z: midZ, a: vault.x + vault.w, b: cap.x, name: 'Vault Bridge' },
    { key: 'b-money', axis: 'z', x: midX, a: cap.z + cap.d, b: money.z, name: 'New Money Bridge' },
    { key: 'b-ave', axis: 'z', x: midX, a: ave.z + ave.d, b: cap.z, name: 'Avenue Bridge' },
  ];
  const cityOf = k => (v?.cities || []).find(c => c.key === k);
  const gates = [
    { key: 'heights', axis: 'z', x: midX, a: ave.z - GAP, b: ave.z, at: 'n' },
    { key: 'bay', axis: 'x', z: lineZ(row, 1), a: row.x + row.w, b: row.x + row.w + GAP, at: 'e' },
    { key: 'harbor', axis: 'x', z: lineZ(vault, 1), a: vault.x - GAP, b: vault.x, at: 'w' },
    { key: 'docks', axis: 'z', x: lineX(money, 1), a: money.z + money.d, b: money.z + money.d + GAP, at: 's' },
  ].map(g => ({ ...g, name: cityOf(g.key)?.name || g.key.toUpperCase(), held: cityOf(g.key) ? `${cityOf(g.key).held}/${cityOf(g.key).plots} held` : '' }));
  const lights = [...roads[0].nodes.filter(n => !n.edge).slice(0, 14), ...roads.slice(1).flatMap(r => r.nodes.filter(n => !n.edge).slice(0, 3))];
  const loops = [ringOf(cap), loop(lineX(cap, 0), lineZ(cap, 4), lineX(cap, 8), lineZ(cap, 6)), loop(lineX(cap, 6), lineZ(cap, 0), lineX(cap, 8), lineZ(cap, 3)), ...[row, vault, money, ave].map(ringOf)];
  // 📺 two billboards on the capital's shore (by the Avenue bridge + the TT bridge): every family ad rotates on them as a slideshow
  const billboards = [{ x: midX + 5, z: cap.z + 2.2, ads: v?.boards || [] }, { x: midX - 5, z: cap.z + cap.d - 2.2, ads: v?.boards || [] }];
  return { kind: 'fee', islands: isl, lots, marks, plaza, markets: mk_, places, inside, spare, roads, bridges, gates, lights, loops, billboards, bounds: boundsOf(isl), center: { x: cap.x + cap.w / 2, z: cap.z + cap.d / 2 + 6 } };
}

// pure: an outer city's plan — its boroughs as 4 × 4 islands joined by bridges, its POOL DISTRICT (real pools from the hub) on the east shore,
// a gate home to Fee City on the west
export function outerPlan(v, cityKey, pools = null) {
  const city = (v?.cities || []).find(c => c.key === cityKey); if (!city) return null;
  const bors = (v?.boroughs || []).filter(b => city.boroughs.includes(b.key)); if (!bors.length) return null;
  const c0 = Math.min(...bors.map(b => b.col)); const r0 = Math.min(...bors.map(b => b.row)); const S = spanOf(4) + 2 * LAND;
  const isl = bors.map(b => island(b.key, (b.col - c0) * (S + GAP) + LAND, (b.row - r0) * (S + GAP) + LAND, 4, 4, CELL, { name: b.name, sub: `×${b.tier} production`, color: '#b388ff', boom: v?.boom?.borough === b.key }));
  const lots = (v?.blocks || []).filter(x => city.boroughs.includes(x.b)).map(x => { const i = isl.find(k => k.key === x.b);
    return { id: x.id, pick: { id: x.id }, kind: x.mine ? 'mine' : x.kind === 'cpu' ? 'cpu' : x.kind === 'cartel' ? 'cartel' : x.owner ? 'family' : 'free', tag: x.tag || null, owner: x.owner || null, home: !!x.home, state: x.state || null, fundH: x.fundH ?? null, launch: x.launch || null,
      power: x.power || 0, link: x.link || null, rect: rectOf(i.gx, i.gz, [x.i % 4, Math.floor(x.i / 4)]), seed: hash(x.id) }; });
  const bridges = (v?.bridges || []).map(br => { const a = isl.find(i => i.key === br.a); const b = isl.find(i => i.key === br.b); if (!a || !b) return null;
    if (a.gz === b.gz) { const [l, r] = a.x < b.x ? [a, b] : [b, a]; return { key: br.name, axis: 'x', z: lineZ(l, 2), a: l.x + l.w, b: r.x, name: br.name }; }
    const [t, u] = a.z < b.z ? [a, b] : [b, a]; return { key: br.name, axis: 'z', x: lineX(t, 2), a: t.z + t.d, b: u.z, name: br.name }; }).filter(Boolean);
  // 🏦 the city's pool district: up to 8 real pools as towers, a bridge from the eastmost borough
  const rows = (pools?.cities?.[cityKey] || []).slice(0, 8); const markets = []; const spare = [];
  const east = isl.reduce((m, i) => (i.x + i.w > m.x + m.w ? i : m), isl[0]);
  if (rows.length) {
    const sM = stepOf(MCELL); const ds = DISTRICTS[cityKey] || { name: 'POOL DISTRICT', sub: 'real pools', color: '#45e4c8' };
    const d = island(`mk-${cityKey}`, east.x + east.w + GAP + LAND, lineZ(east, 2) - 0.5 - sM, 4, 2, MCELL, { name: ds.name, sub: ds.sub, color: ds.color, district: true });
    isl.push(d);
    for (let k = 0; k < 8; k += 1) { const rect = rectOf(d.gx, d.gz, [k % 4, Math.floor(k / 4)], MCELL); if (rows[k]) markets.push(poolMarket(rows[k], rect, d.key)); else spare.push({ key: `spare-${d.key}-${k}`, island: d.key, rect }); }
    bridges.push({ key: `b-${d.key}`, axis: 'x', z: lineZ(east, 2), a: east.x + east.w, b: d.x, name: `${ds.name} Bridge` });
  }
  // 🏛 the City Hall stands on its own islet west of the city, over a bridge — the gate home to Fee City moves past it
  const west = isl.reduce((m, i) => (i.x < m.x ? i : m), isl[0]); const places = [];
  const hd = HALLS[cityKey]; let gateFrom = west;
  if (hd) {
    const hs = spanOf(1, MCELL); const hall = island(`hall-${cityKey}`, west.x - GAP - LAND - hs, lineZ(west, 2) - 0.5, 1, 1, MCELL, { name: hd.name, sub: hd.sub, color: hd.color });
    isl.push(hall); bridges.push({ key: `b-hall-${cityKey}`, axis: 'x', z: lineZ(west, 2), a: hall.x + hall.w, b: west.x, name: `${hd.name} Bridge` });
    places.push({ key: `hall-${cityKey}`, lens: `hall-${cityKey}`, name: hd.name, sub: hd.sub, art: hd.art, color: hd.color, tool: true, isl: hall.key, pick: { place: `hall-${cityKey}` }, rect: rectOf(hall.gx, hall.gz, [0, 0], MCELL) });
    gateFrom = hall;
  }
  const roads = isl.map(i => roadsOf(i));
  const fee = (v?.cities || []).find(c => c.key === 'fee');
  const gates = fee ? [{ key: 'fee', axis: 'x', z: lineZ(west, 2), a: gateFrom.x - GAP, b: gateFrom.x, at: 'w', name: 'FEE CITY', held: `${fee.held}/${fee.plots} held` }] : [];
  const lights = roads.flatMap(r => r.nodes.filter(n => !n.edge).slice(0, 2));
  const b = boundsOf(isl);
  return { kind: 'outer', key: cityKey, name: city.name, islands: isl, lots, marks: [], plaza: null, markets, places, spare, roads, bridges, gates, lights, loops: isl.map(ringOf),
    bounds: { ...b, x0: b.x0 - GAP }, center: { x: (b.x0 + b.x1) / 2, z: (b.z0 + b.z1) / 2 } };
}

// 🏘 THE TOWN's tool buildings (backend block_markets.TOWN): what each looks like on the family's block — every one opens its real tool
export const TOWN = {
  tt: { name: 'TRENCH TOWERS', sub: 'the intake list · trade it', art: 'tt', color: '#ff8fa3' },
  perps: { name: 'PERPS DESK', sub: 'funding · leverage · US venues', art: 'perps', color: '#ff5dbb' },
  pools: { name: 'POOL HALL', sub: 'APY · 24h earned · range tuner', art: 'hall', color: '#45e4c8' },
  trades: { name: 'TRADE CENTER', sub: "the desk's real trades · live P&L", art: 'trade', color: '#45e486' },
  vault: { name: 'NIGHT VAULT', sub: 'earn while you sleep · live APY', art: 'sleep', color: '#9b8cff' },
  radar: { name: 'PUMP RADAR', sub: 'hottest Pump coins · one tap', art: 'radar', color: '#45e486' },
  cats: { name: 'FEECAT TOWER', sub: 'FeeCat live · your cats', art: 'cat', color: '#b388ff' },
  rep: { name: 'REP MARKET', sub: 'call it right → chips → points', art: 'casino', color: '#ffd36b' },
};

// 🏙 pure: a FAMILY BLOCK in the 3D city (owner, 2026-10-22: "my block supposed to look like the new city design and expanding — me adding
// buildings for markets i wanna use, under construction until i actually buy … shows open plots"). One island that grows with the family's
// market buildings: BUILT = a tower sized by the position's $ value with its live APY on the sign · NOT YET = scaffolding + a crane · OPEN PLOTS
// = surveyed land with stakes, tap one to add a market. `bl` = /familia-block.
export function blockPlan(bl, live = {}) {
  const blds = bl?.buildings || []; const open = Math.max(0, bl?.open ?? 3); const town = (bl?.town || []).filter(k => TOWN[k]); const n = blds.length + town.length + open;
  const cols = Math.max(3, Math.min(5, Math.ceil(Math.sqrt(n * 1.6)))); const rows = Math.max(2, Math.ceil(n / cols));
  const isl = island('block', 0, 0, cols, rows, MCELL, { name: `[${bl?.tag || '?'}] ${String(bl?.name || 'THE BLOCK').toUpperCase()}`, sub: `${bl?.built || 0}/${blds.length} built${bl?.total ? ` · ${usd(bl.total)}` : ''}`, color: '#d4af37' });
  const at = k => rectOf(isl.gx, isl.gz, [k % cols, Math.floor(k / cols)], MCELL);
  const markets = []; const lots = [];
  blds.forEach((b, k) => {
    const rect = at(k); const pick = { blk: b.key };
    if (b.state === 'built') {
      const v = Number(b.usd) || 0;
      markets.push({ key: `blk-${b.key}`, pick, kind: b.kind, name: b.sym || b.name, proto: b.name, pool: true, tvl: v || b.tvl, apy: b.apy, hz: pulseHz({ tvl: v * 50 }),
        h: v ? heightOf(v * 40) * 1.2 : 2.6, rect, island: 'block', m: b,
        lines: [`${b.sym || b.name}`, v ? `${usd(v)}${b.apy != null ? ` · APY ${apyTxt(b.apy)}` : ''}` : `${b.n || 1} position${(b.n || 1) > 1 ? 's' : ''}`, (b.errands || []).length ? `${b.errands.length} errand${b.errands.length > 1 ? 's' : ''}` : b.name] });
    } else lots.push({ id: `blk-${b.key}`, pick, kind: 'mine', tag: bl?.tag, owner: bl?.id, state: 'shut', power: 3000, rect, seed: hash(b.key), lines: [`${b.name} · UNDER CONSTRUCTION`, b.why ? 'no position reader yet' : 'open a position to build it'] });
  });
  // 🏘 the town: the tool buildings the family picked, each a real tool (the TT tower burns its READY floors here too)
  // 🏘 each sign carries its tool's own live number (live.town = lib/townLive → backend/town_live.py); a quiet source keeps the subtitle
  const places = town.map((k, j) => { const t = TOWN[k]; const tt = k === 'tt' ? ttLive(live.coins) : null; const tl = live.town?.[k];
    return { key: `town-${k}`, lens: k, pick: { town: k }, name: t.name, sub: t.sub, art: t.art, color: t.color, tool: true, isl: 'block', rect: at(blds.length + j), live: tt,
      lines: [t.name, tl?.line || (tt?.n ? `${tt.ready} READY · ${tt.n} on the intake` : t.sub)] }; });
  for (let k = 0; k < open; k += 1) lots.push({ id: `open-${k}`, pick: { open: k }, kind: 'free', open: true, rect: at(blds.length + town.length + k), seed: k });
  const roads = [roadsOf(isl)];
  return { kind: 'block', key: bl?.id || 'block', islands: [isl], lots, marks: [], plaza: null, markets, places, spare: [], roads, bridges: [], gates: [],
    lights: roads[0].nodes.filter(nd => !nd.edge).slice(0, 6), loops: [ringOf(isl)], billboards: [], bounds: boundsOf([isl]), center: { x: isl.x + isl.w / 2, z: isl.z + isl.d / 2 } };
}

// pure: where the camera looks for a picked thing (plot id, landmark, market, place, island)
export function spotOf(plan, sel) {
  if (!plan || !sel) return null;
  if (sel.isl) { const i = plan.islands.find(x => x.key === sel.isl); return i ? { x: i.x + i.w / 2, z: i.z + i.d / 2, span: Math.max(i.w, i.d) } : null; }
  if (sel.town) { const t = plan.places.find(p => p.pick?.town === sel.town); return t ? centerOf(t.rect) : null; }   // 🏘 a town building
  if (sel.blk || sel.open != null) { const id = sel.blk ? `blk-${sel.blk}` : `open-${sel.open}`; const b = plan.lots.find(l => l.id === id) || plan.markets.find(m => m.key === id); return b ? centerOf(b.rect) : null; }   // 🏙 the family block
  const hit = sel.id ? plan.lots.find(l => l.id === sel.id) : sel.lm ? plan.marks.find(m => m.key === sel.lm) : sel.mk ? plan.markets.find(m => m.key === sel.mk) : sel.place ? (plan.places.find(p => p.key === sel.place) || (plan.inside || []).find(p => p.key === sel.place)) : null;
  return hit ? centerOf(hit.rect) : null;
}
