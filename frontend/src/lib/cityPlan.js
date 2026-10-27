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
// Owner, 2026-10-23 (SIMCITY SCALE): "a bigger capital; ~80 % of the city real-money buildings (pools, vaults, lend, perps, LSTs, the desk)
// spread across districts, not packed on one island; family blocks as their own islands off the capital" → FEE CITY is now a METRO: downtown
// (the civic halls + the desk's money buildings) in the middle, EIGHT money districts round it over canals (DEX Row, Stake Heights, Lend Street,
// the Flats, Vault Row, CLMM Heights, FEELESS Avenue, TT) filled from the live markets + the Pool Hub, and SIX FAMILY KEYS (4 plots each) off
// the shore. `moneyShare` proves the ~80 %.
export const CELL = 5;        // a family plot
export const MCELL = 8;       // a market tower (and every downtown / district cell)
export const TCELL = 9;       // (kept for old callers — the TT island now stands on MCELL cells)
export const LAND = 6;        // the open land ring around every island grid
const GAP = 22;               // open water: the gates out, and the family keys off the shore
const CANAL = 12;             // 🌊 the canals between the metro's districts — one city cut by water
export const FOOT = { lot: 3.4, tower: 5.4, tt: 11 };   // the most a building covers of its cell — the rest is its yard (grass, trees)
export const stepOf = cell => cell + 1;
export const STEP = stepOf(CELL);
const spanOf = (n, cell = CELL) => n * stepOf(cell) + 1;
// a cell [c, r, w, h] on a grid whose origin is (gx, gz) → a rect in tiles
export const rectOf = (gx, gz, [c, r, w = 1, h = 1], cell = CELL) => { const s = stepOf(cell); return { x: gx + 1 + c * s, z: gz + 1 + r * s, w: w * s - 1, d: h * s - 1 }; };
export const centerOf = r => ({ x: r.x + r.w / 2, z: r.z + r.d / 2 });

// 🏛 DOWNTOWN (MCELL cells, 6 × 4): the stadium in the middle, the House, the Mansion, Rug Shield, the Launch Pad, Fee Plaza — and its top row is
// the desk's money street (Trade Center · Your Money · the $FEE Bank) between the Podium, the War Room and Pawn & Gold
export const CAP = { cols: 6, rows: 4 };
export const FEE_MARKS = { house: [0, 1, 1, 2], arena: [1, 1, 3, 2], mansion: [4, 1, 2, 1], shield: [4, 2, 1, 1], launch: [5, 2, 1, 1] };
export const PLAZA = [0, 3, 4, 1];
export const CORE = { podium: [0, 0], warroom: [1, 0], trades: [2, 0], mymoney: [3, 0], feebank: [4, 0], rewards: [5, 0] };
// 🏝 the six FAMILY KEYS: 4 plots each (the server's fee-0 … fee-23 in order), each off the shore of a corner district over its own bridge
export const KEYS = [
  { key: 'key-rose', name: 'ROSE KEY', color: '#ff8fa3', of: 'clmm', side: 'w' }, { key: 'key-gold', name: 'GOLD KEY', color: '#d4af37', of: 'stake', side: 'e' },
  { key: 'key-noir', name: 'NOIR KEY', color: '#b388ff', of: 'flats', side: 'w' }, { key: 'key-ivory', name: 'IVORY KEY', color: '#e8e3d6', of: 'lend', side: 'e' },
  { key: 'key-ash', name: 'ASH KEY', color: '#9aa3b2', of: 'clmm', side: 'n' }, { key: 'key-jade', name: 'JADE KEY', color: '#45e486', of: 'stake', side: 'n' },
];
export const keyOfPlot = i => ({ k: Math.floor(i / 4) % KEYS.length, cell: [i % 2, Math.floor((i % 4) / 2)] });

// 📍 the game's places — every old lens is a building you walk into; the Pool Hall opens the Pool Hub
export const PLACES = [
  { key: 'hq', lens: 'family', name: 'YOUR FAMILY HQ', sub: 'vitals · tools · expand', isl: 'home', art: 'hq', color: '#ffcc4d', virtual: true },
  { key: 'warroom', lens: 'wars', name: 'THE WAR ROOM', sub: 'call-outs · live wars', isl: 'fee', art: 'war', color: '#ff4d5e' },
  { key: 'podium', lens: 'board', name: 'THE PODIUM', sub: 'weekly crowns', isl: 'fee', art: 'podium', color: '#ffd36b' },
  { key: 'wire', lens: 'feed', name: 'THE WIRE', sub: 'every family move, live', isl: 'plaza-l', art: 'board', color: '#45e4c8' },
  { key: 'pools', lens: 'pools', name: 'THE POOL HALL', sub: 'every top + rising pool', isl: 'row', art: 'hall', color: '#45e4c8', money: true },
  { key: 'ranked', lens: 'ranked', name: 'THE LADDER', sub: 'ranked · Street Rat → Kingpin', in: 'podium', art: 'tower', color: '#d4af37' },
  { key: 'raids', lens: 'raids', name: 'THE PRECINCT', sub: 'raids · live + the war log', in: 'warroom', art: 'precinct', color: '#ff5d73' },
  { key: 'rewards', lens: 'shop', name: 'PAWN & GOLD', sub: 'rewards · MP → FEECAT', isl: 'fee', art: 'pawn', color: '#f5c451' },
  { key: 'jobs', lens: 'jobs', name: 'JOB BOARD', sub: 'errands · MP every few minutes', in: 'hq', art: 'board', color: '#45e486' },
  { key: 'gym', lens: 'rc', name: 'THE GYM', sub: 'challenges · win recruits', in: 'hq', art: 'gym', color: '#6ad7ff' },
  { key: 'cards', lens: 'deck', name: 'CARD ROOM', sub: 'your crew deck', in: 'hq', art: 'casino', color: '#b388ff' },
  { key: 'cartels', lens: 'cartels', name: 'CARTEL WAREHOUSE', sub: 'bundlers · snipers · funders', in: 'warroom', art: 'warehouse', color: '#3ddc84' },
  // 🗼 TT — ONE landmark tower on its own island (owner, 2026-10-23): READY coins lit on its floors, the hottest coin on its crown; one pop-out
  { key: 'tt', lens: 'tt', name: 'TRENCH TOWERS', sub: "the desk's intake list · trade it right here", isl: 'money', art: 'tt', color: '#ff8fa3', tool: true, money: true },
  // 🛣 FEELESS AVENUE — the site's best tools as buildings: each pops out its live vitals + quick tools (`tool: true`, `page` = its full page)
  { key: 'pumpradar', lens: 'pumpradar', name: 'PUMP RADAR', sub: 'hot Pump coins · runners · the desk\'s trades', isl: 'ave', art: 'radar', color: '#45e486', tool: true, money: true, page: '/terminal/pump' },
  { key: 'runners', lens: 'runners', name: 'RUNNERS TRACK', sub: "FEELESS's live runner calls", in: 'pumpradar', art: 'track', color: '#ff9f45', tool: true, page: '/terminal/fuse?tab=runners' },
  { key: 'watch', lens: 'watch', name: 'THE WATCHTOWER', sub: 'your watchlist · signal alerts', in: 'court', art: 'watch', color: '#6ad7ff', tool: true, page: '/terminal/watchlist' },
  { key: 'court', lens: 'rep', name: 'REP COURTHOUSE', sub: 'case files · check anyone', isl: 'ave', art: 'court', color: '#d4af37', tool: true, page: '/terminal/reputation' },
  { key: 'feecat', lens: 'feecat', name: 'FEECAT TOWER', sub: 'the trading cat, live', isl: 'ave', art: 'cat', color: '#b388ff', tool: true, page: '/terminal/feecat' },
  { key: 'fuel', lens: 'gas', name: 'FUEL STATION', sub: 'gas on 12 chains', in: 'feebank', art: 'fuel', color: '#ffd36b', tool: true, page: '/terminal/trade' },
  { key: 'news', lens: 'feedx', name: 'THE NEWSSTAND', sub: 'FEEd · every call, live', in: 'wire', art: 'news', color: '#45e4c8', tool: true },
  { key: 'feebank', lens: 'feebank', name: 'THE $FEE BANK', sub: '$FEE · rFEE · FEECAT — buys fee-free', isl: 'fee', art: 'bank', color: '#15d16a', tool: true, money: true, page: '/terminal/fee' },
  { key: 'perps', lens: 'perps', name: 'THE PERPS DESK', sub: 'perps markets live · funding · leverage', isl: 'ave', art: 'perps', color: '#ff5dbb', tool: true, money: true },
  { key: 'trades', lens: 'trades', name: 'THE TRADE CENTER', sub: 'the desk\'s real-money trades · live P&L', in: 'pumpradar', art: 'trade', color: '#45e486', tool: true, money: true },   // 🚪 a room of Pump Radar (owner 2026-10-27: one building)
  { key: 'sleep', lens: 'sleep', name: 'THE NIGHT VAULT', sub: 'money while you sleep · live APY', isl: 'vault', art: 'sleep', color: '#9b8cff', tool: true, money: true },
  // 💵 YOUR MONEY (owner 1e): every position FEELESS can prove for your wallet, priced live — the Avenue's last cell
  // 🏦 THE BROKERAGE (DECISIONS #9): your own broker linked to your wallet — stocks · ETFs · crypto, live, trade from $1
  { key: 'brokers', lens: 'brokers', name: 'THE BROKERAGE', sub: 'your broker linked · stocks · crypto · live', in: 'mymoney', art: 'bank', color: '#ffd36b', tool: true, money: true },
  { key: 'mymoney', lens: 'mymoney', name: 'YOUR MONEY', sub: 'every proved position · live', isl: 'fee', art: 'money', color: '#45e486', tool: true, money: true },
];
// 🚪 the rooms of one building: the host first, then every place that lives inside it (`in`)
export const roomsOf = key => { const p = PLACES.find(x => x.key === key || x.lens === key); const host = p?.in || p?.key; return host ? PLACES.filter(x => x.key === host || x.in === host) : []; };

// 🏙 the metro's districts round downtown (`at` = [col, row] of the 3 × 3 metro, downtown = [0, 0]); `fill` = what stands there after its
// places: [source, kinds, how many] — live markets (`mk`) by TVL, then Pool Hub rows (`pool`), freshest to Fee City + paying first. A cell
// nothing fills is a PARK. West column = 3 cols, east column = 4 cols, every district 2 rows: the canal bridges land on shared avenues.
export const METRO = {
  ave: { name: 'FEELESS AVENUE', sub: 'the tools + the perps strip', at: [0, -1], cols: 4, rows: 2, color: '#15d16a', fill: [['mk', ['perps'], 1], ['pool', ['perps'], 3]] },
  stake: { name: 'STAKE HEIGHTS', sub: 'liquid staking · every LST', at: [1, -1], cols: 4, rows: 2, color: '#6ad7ff', fill: [['mk', ['stake'], 4], ['pool', ['stake'], 4]] },
  row: { name: 'DEX ROW', sub: 'the DEXes + the Pool Hall', at: [1, 0], cols: 4, rows: 2, color: '#45e486', fill: [['mk', ['dex'], 5], ['pool', ['v2', 'dlmm'], 2]] },
  lend: { name: 'LEND STREET', sub: 'lending + treasuries', at: [1, 1], cols: 4, rows: 2, color: '#f5c451', fill: [['mk', ['lend'], 3], ['pool', ['rwa'], 2], ['pool', ['lend'], 3]] },
  money: { name: 'TT · TRENCH TOWERS', sub: "the desk's intake list · one tower", at: [0, 1], cols: 2, rows: 2, color: '#ff8fa3', fill: [] },
  flats: { name: 'THE FLATS', sub: 'v2 pools · constant product', at: [-1, 1], cols: 3, rows: 2, color: '#ff9f45', fill: [['pool', ['v2'], 6]] },
  vault: { name: 'VAULT ROW', sub: 'auto-compound vaults · the Night Vault', at: [-1, 0], cols: 3, rows: 2, color: '#3ddc84', fill: [['pool', ['vault'], 5]] },
  clmm: { name: 'CLMM HEIGHTS', sub: 'concentrated liquidity · v3 + DLMM', at: [-1, -1], cols: 3, rows: 2, color: '#9b8cff', fill: [['pool', ['v3', 'dlmm'], 6]] },
};
export const ISLANDS = METRO;   // the old name
const FILL_ORDER = ['row', 'stake', 'lend', 'ave', 'vault', 'clmm', 'flats', 'money'];   // who picks pools first (no pool stands twice)
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
export const dollarsSmall = v => { const n = Number(v) || 0; return n >= 1000 ? usd(n) : n >= 1 ? `$${n.toFixed(2)}` : `$${n.toFixed(3)}`; };   // small money keeps its cents
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

// a bridge between two neighbouring islands, on a road line both grids share (the plan lines the grids up) — the shared line nearest the middle
function bridgeOf(a, b, name, extra = {}) {
  const side = a.x + a.w <= b.x || b.x + b.w <= a.x; const [l, r] = side ? (a.x < b.x ? [a, b] : [b, a]) : (a.z < b.z ? [a, b] : [b, a]);
  const lines = i => Array.from({ length: (side ? i.rows : i.cols) + 1 }, (_, k) => (side ? lineZ(i, k) : lineX(i, k)));
  const mid = side ? (Math.max(l.z, r.z) + Math.min(l.z + l.d, r.z + r.d)) / 2 : (Math.max(l.x, r.x) + Math.min(l.x + l.w, r.x + r.w)) / 2;
  const at = lines(l).filter(v => lines(r).some(u => Math.abs(u - v) < 0.01)).sort((p, q) => Math.abs(p - mid) - Math.abs(q - mid))[0];
  if (at == null) return null;
  return side ? { key: `b-${a.key}-${b.key}`, axis: 'x', z: at, a: l.x + l.w, b: r.x, name, ...extra } : { key: `b-${a.key}-${b.key}`, axis: 'z', x: at, a: l.z + l.d, b: r.z, name, ...extra };
}
// pure: the share of the city's buildings that are real money (markets, pools, the desk's money places) — the owner's ~80 %
// 2026-10-23 (owner: "80 % ACTIVE real money buildings"): a building counts only when tapping it does real money right there — every market /
// pool opens its own desk (FeeCity3D.deskAct), a coin needs its mint for the swap dock, a place needs `money` (an in-place money tool).
export const activeMoney = x => (x?.pick?.mk ? (x.kind !== 'coin' || !!(x.m?.mint || x.m?.address)) : !!x?.money);
export function moneyShare(p) {
  const bld = [...(p?.markets || []), ...(p?.places || []).filter(x => !x.virtual), ...(p?.marks || [])];
  const money = bld.filter(activeMoney).length; return bld.length ? Math.round((money / bld.length) * 100) / 100 : 0;
}

// pure: the Fee City plan. `v` = the world payload, `mk` = { markets, coins }, `pools` = the Pool Hub (any may be missing — the city still draws)
export function feePlan(v, mk, pools = null) {
  const markets = (mk?.markets || []).slice(); const coins = (mk?.coins || []).slice(0, 12); const tt = ttLive(coins); const sM = stepOf(MCELL);
  const cap = island('fee', 0, 0, CAP.cols, CAP.rows, MCELL, { name: 'FEE CITY', sub: 'downtown · the capital of the trenches', color: '#d4af37', capital: true });
  // 🏙 the eight districts: west / east columns flush on the canals, north / south rows flush on theirs, the middle row and column on downtown's avenues
  const gxOf = d => (d.at[0] < 0 ? cap.x - CANAL - LAND - spanOf(d.cols, MCELL) : d.at[0] > 0 ? cap.x + cap.w + CANAL + LAND : cap.gx + sM * Math.round((CAP.cols - d.cols) / 2));
  const gzOf = d => (d.at[1] < 0 ? cap.z - CANAL - LAND - spanOf(d.rows, MCELL) : d.at[1] > 0 ? cap.z + cap.d + CANAL + LAND : cap.gz + sM * Math.round((CAP.rows - d.rows) / 2));
  const byKey = { fee: cap };
  for (const [k, d] of Object.entries(METRO)) byKey[k] = island(k, gxOf(d), gzOf(d), d.cols, d.rows, MCELL, { name: d.name, sub: k === 'money' && tt.n ? `${tt.ready} READY · ${tt.n} on the intake` : d.sub, color: d.color });
  const metro = [cap, ...Object.keys(METRO).map(k => byKey[k])];
  // 🏝 the family keys: each off its corner district, one of its avenues lined up with one of the district's
  const keys = KEYS.map(K => { const d = byKey[K.of]; const s = spanOf(2, CELL);
    if (K.side === 'n') { const x = lineX(d, Math.floor(d.cols / 2)); return island(K.key, x - 0.5 - STEP, d.z - GAP - LAND - s, 2, 2, CELL, { name: K.name, color: K.color, key_: true }); }
    const z = lineZ(d, 1); const gx = K.side === 'w' ? d.x - GAP - LAND - s : d.x + d.w + GAP + LAND; return island(K.key, gx, z - 0.5 - STEP, 2, 2, CELL, { name: K.name, color: K.color, key_: true }); });
  // family plots (server ids fee-*) on the keys
  const lots = (v?.blocks || []).filter(b => b.b === 'fee').map(b => { const { k, cell } = keyOfPlot(b.i || 0); const ki = keys[k];
    return { id: b.id, pick: { id: b.id }, kind: b.mine ? 'mine' : b.kind === 'cpu' ? 'cpu' : b.kind === 'cartel' ? 'cartel' : b.owner ? 'family' : 'free', island: ki.key,
      tag: b.tag || null, owner: b.owner || null, home: !!b.home, power: b.power || 0, link: b.link || null, state: b.state || null, fundH: b.fundH ?? null, launch: b.launch || null, rect: rectOf(ki.gx, ki.gz, cell), seed: hash(b.id) }; });
  keys.forEach(ki => { const on = lots.filter(l => l.island === ki.key); const held = on.filter(l => l.kind !== 'free');
    ki.sub = held.length ? `${held.map(l => (l.tag ? `[${l.tag}]` : 'held')).slice(0, 3).join(' ')} · ${4 - held.length} open` : '4 open plots · claim one'; });
  const marks = Object.entries(FEE_MARKS).map(([k, c]) => { const m = (v?.landmarks || []).find(l => l.key === k); return { key: k, pick: { lm: k }, name: m?.name || k.toUpperCase(), live: m?.live || null, rect: rectOf(cap.gx, cap.gz, c, MCELL) }; });
  const plaza = rectOf(cap.gx, cap.gz, PLAZA, MCELL);
  // the slots: every district cell row by row; downtown's are fixed (CORE)
  const slots = {}; for (const [k, d] of Object.entries(METRO)) { slots[k] = []; for (let r = 0; r < d.rows; r += 1) for (let c = 0; c < d.cols; c += 1) slots[k].push([c, r]); }
  const at = (k, c) => rectOf(byKey[k].gx, byKey[k].gz, c, MCELL);
  const home = lots.find(l => l.home && l.kind === 'mine');   // 🏠 your family HQ = your home block on its key, else the Mansion
  const ttRect = at('money', [0, 0, 2, 2]); slots.money = [];
  const places = PLACES.filter(p => !p.in).map(p => {
    if (p.isl === 'home') return { ...p, pick: { place: p.key }, rect: (home || marks.find(m => m.key === 'mansion')).rect };
    if (p.isl === 'plaza-l') return { ...p, pick: { place: p.key }, rect: { x: plaza.x, z: plaza.z, w: 7, d: plaza.d } };
    if (p.key === 'tt') return { ...p, pick: { place: p.key }, rect: ttRect, live: tt, lines: [`🗼 ${p.name}`, tt.n ? `${tt.ready} READY · ${tt.n} on the intake` : p.sub, ...(tt.hot ? [`HOT $${tt.hot.sym}${tt.hot.ch != null ? ` ${tt.hot.ch >= 0 ? '+' : ''}${Number(tt.hot.ch).toFixed(1)}% 5m` : ''}`] : [])] };
    if (p.isl === 'fee') return CORE[p.key] ? { ...p, pick: { place: p.key }, rect: rectOf(cap.gx, cap.gz, CORE[p.key], MCELL) } : null;
    const c = slots[p.isl]?.shift(); return c ? { ...p, pick: { place: p.key }, rect: at(p.isl, c) } : null; }).filter(Boolean);
  // 🚪 rooms inside another building: no building of their own — the camera flies to their host, the pop-out shows the host's rooms as tabs
  const inside = PLACES.filter(p => p.in).map(p => { const h = places.find(x => x.key === p.in); return h ? { ...p, pick: { place: p.key }, rect: h.rect, host: h.key } : null; }).filter(Boolean);
  // 🏦 the money: live markets by TVL, then the Pool Hub's rows — freshest to Fee City (not already in an outer city's district) and paying first
  const shown = new Set(Object.values(pools?.cities || {}).flat().map(r => r?.id));
  const rows = (pools?.pools || []).filter(r => r && r.id && (Number(r.tvl) || 0) >= 1e5); const used = new Set(); const mk_ = [];
  const rank = r => (shown.has(r.id) ? 2 : 0) + (Number(r.apy) > 0 ? 0 : 1);
  for (const k of FILL_ORDER) for (const [src, kinds, n] of METRO[k].fill) {
    const room = Math.min(n, slots[k].length); if (!room) continue;
    if (src === 'mk') markets.filter(m => kinds.includes(m.kind) && !used.has(m.key)).sort((a, b) => (b.tvl || 0) - (a.tvl || 0)).slice(0, room).forEach(m => { used.add(m.key);
      mk_.push({ key: m.key, pick: { mk: m.key }, kind: m.kind, name: m.name, tvl: m.tvl, move: m.move ?? m.ch ?? m.change ?? null, hz: pulseHz(m), h: heightOf(m.tvl) * 1.45, rect: at(k, slots[k].shift()), island: k, m }); });
    else rows.filter(r => kinds.includes(r.kind) && !used.has(r.id)).sort((a, b) => rank(a) - rank(b) || (b.tvl || 0) - (a.tvl || 0)).slice(0, room).forEach(r => { used.add(r.id); mk_.push(poolMarket(r, at(k, slots[k].shift()), k)); });
  }
  // 🌳 an empty cell is a PARK (owner: "open land, not every building side by side") — downtown's two spare cells too
  const spare = [...Object.entries(slots).flatMap(([k, cs]) => cs.map(c => ({ key: `park-${k}-${c.join('-')}`, island: k, park: true, rect: at(k, c) }))),
    ...[[4, 3], [5, 3]].map(c => ({ key: `park-fee-${c.join('-')}`, island: 'fee', park: true, rect: rectOf(cap.gx, cap.gz, c, MCELL) }))];
  const isl = [...metro, ...keys];
  const roads = isl.map(i => roadsOf(i, i.key === 'fee' ? [...marks.map(m => m.rect), plaza] : i.key === 'money' ? [ttRect] : []));
  // 🌉 bridges: downtown's four (busy, a car each way), the canal ring round it, and each key's own
  const B = byKey; const pair = (a, b, name, extra) => bridgeOf(B[a] || keys.find(x => x.key === a), B[b], name, extra);
  const bridges = [pair('ave', 'fee', 'Avenue Bridge', { cars: 1 }), pair('fee', 'money', 'New Money Bridge', { cars: 1 }), pair('vault', 'fee', 'Vault Bridge', { cars: 1 }), pair('fee', 'row', 'Fee Street Bridge', { cars: 1 }),
    pair('clmm', 'ave', 'Heights Canal', { cars: 0 }), pair('ave', 'stake', 'Stake Canal', { cars: 0 }), pair('stake', 'row', 'Row Canal', { cars: 0 }), pair('row', 'lend', 'Lend Canal', { cars: 0 }),
    pair('lend', 'money', 'Lend Street Bridge', { cars: 0 }), pair('money', 'flats', 'Flats Bridge', { cars: 0 }), pair('flats', 'vault', 'Flats Canal', { cars: 0 }), pair('vault', 'clmm', 'Vault Canal', { cars: 0 }),
    ...KEYS.map(K => pair(K.key, K.of, `${K.name} Bridge`, { cars: 0 }))].filter(Boolean);
  const cityOf = k => (v?.cities || []).find(c => c.key === k);
  const { ave, row, vault, money } = byKey;
  const gates = [
    { key: 'heights', axis: 'z', x: lineX(ave, 2), a: ave.z - GAP, b: ave.z, at: 'n' },
    { key: 'bay', axis: 'x', z: lineZ(row, 1), a: row.x + row.w, b: row.x + row.w + GAP, at: 'e' },
    { key: 'harbor', axis: 'x', z: lineZ(vault, 1), a: vault.x - GAP, b: vault.x, at: 'w' },
    { key: 'docks', axis: 'z', x: lineX(money, 1), a: money.z + money.d, b: money.z + money.d + GAP, at: 's' },
  ].map(g => ({ ...g, name: cityOf(g.key)?.name || g.key.toUpperCase(), held: cityOf(g.key) ? `${cityOf(g.key).held}/${cityOf(g.key).plots} held` : '' }));
  const lights = [...roads[0].nodes.filter(n => !n.edge).slice(0, 12), ...roads.slice(1, metro.length).flatMap(r => r.nodes.filter(n => !n.edge).slice(0, 2))];
  const loops = [ringOf(cap), loop(lineX(cap, 0), lineZ(cap, 0), lineX(cap, CAP.cols), lineZ(cap, 1)), loop(lineX(cap, 0), lineZ(cap, 3), lineX(cap, CAP.cols), lineZ(cap, CAP.rows)), ...metro.slice(1).map(ringOf), ...keys.map(ringOf)];
  const cars = [5, 3, 3, ...metro.slice(1).map(() => 2), ...keys.map(() => 1)];   // 🚗 a car budget: busy downtown, calm keys (the old city ran ~4 a loop)
  // 📺 two billboards on downtown's shore (by the Avenue bridge + the TT bridge): every family ad rotates on them as a slideshow
  const midX = lineX(cap, CAP.cols / 2);
  const billboards = [{ x: midX + 5, z: cap.z + 2.2, ads: v?.boards || [] }, { x: midX - 5, z: cap.z + cap.d - 2.2, ads: v?.boards || [] }];
  const out = { kind: 'fee', islands: isl, lots, marks, plaza, markets: mk_, places, inside, spare, roads, bridges, gates, lights, loops, cars, billboards, bounds: boundsOf(isl),
    view: boundsOf(metro), center: { x: cap.x + cap.w / 2, z: cap.z + cap.d / 2 + 6 } };
  const share = moneyShare(out); cap.sub = `downtown · ${mk_.length + places.filter(p => p.money).length} money buildings · ${Math.round(share * 100)}% real money`; out.share = share;
  return out;
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

// 🏝 THE TOWN EXPANDS (owner, 2026-10-23): the family's own arrangement (backend block_markets.layout_of) — cells in order, ISLAND_CELLS an
// island; a new island (and its bridge) every 15. Stands dress the streets; MY POOLS is one combo building of every position the block holds.
export const ISLAND_CELLS = 15;
export const STAND = { kiosk: { name: 'KIOSK', sub: 'coffee · street talk', color: '#ffd36b', icon: '☕' }, food: { name: 'FOOD STALL', sub: 'tacos for the trench', color: '#ff8fa3', icon: '🌮' },
  sign: { name: 'BILLBOARD', sub: "the family's sign", color: '#45e486', icon: '🪧' }, fountain: { name: 'FOUNTAIN', sub: 'make a wish', color: '#7fe0ff', icon: '⛲' },
  park: { name: 'PARK', sub: 'trees + a bench', color: '#5fd38a', icon: '🌳' }, garden: { name: 'GARDEN', sub: 'flower beds in bloom', color: '#ff7ac8', icon: '🌷' },
  statue: { name: 'STATUE', sub: 'the Don in gold', color: '#ffcf5c', icon: '🗽' }, plaza: { name: 'PLAZA', sub: 'tiles + lamp posts', color: '#c9b6ff', icon: '🏛' },
  pond: { name: 'POND', sub: 'koi + lily pads', color: '#5fc9ff', icon: '🪷' }, palms: { name: 'PALMS', sub: 'a beach corner', color: '#3ddc97', icon: '🌴' } };
export const MY_POOLS = { name: 'MY POOLS', sub: 'every LP · stake · lend position, live', art: 'money', color: '#45e4c8' };

// pure: the block's cells in order — the family's saved layout (✋ Arrange), else its buildings → your LP towers → the town → open plots.
// Your LP towers are yours (not the family's), so they always follow the family's last market building.
export function blockCells(bl, lps = []) {
  const town = (bl?.town || []).filter(k => TOWN[k]);
  const base = Array.isArray(bl?.layout) && bl.layout.length ? bl.layout.filter(c => !String(c).startsWith('town:') || TOWN[String(c).slice(5)])
    : [...(bl?.buildings || []).map(b => `blk:${b.key}`), ...town.map(k => `town:${k}`)];
  const last = base.reduce((i, c, j) => (String(c).startsWith('blk:') ? j : i), -1);
  const cells = [...base.slice(0, last + 1), ...lps.map(p => `lp:${p.id}`), ...base.slice(last + 1)];
  if (!bl?.layoutSaved) for (let k = 0; k < Math.max(0, bl?.open ?? 3); k += 1) cells.push('open');
  return cells;
}

// pure: MY POOLS' live number — every built market building + every LP position the block shows ($ worth now, fees not claimed)
export function myPools(bl, lps = []) {
  const blds = (bl?.buildings || []).filter(b => b.state === 'built');
  const v = blds.reduce((a, b) => a + (Number(b.usd) || 0), 0) + lps.reduce((a, p) => a + (Number(p.valueUsd) || 0), 0);
  return { usd: v, fees: lps.reduce((a, p) => a + (Number(p.feeUsd) || 0), 0), n: blds.length + lps.length, inRange: lps.filter(p => p.inRange).length, rows: [...blds.map(b => ({ key: `blk-${b.key}`, sym: b.sym || b.name, usd: Number(b.usd) || 0, apy: b.apy, kind: b.kind })),
    ...lps.map(p => ({ key: `lp-${p.id}`, sym: p.sym, usd: Number(p.valueUsd) || 0, fees: Number(p.feeUsd) || 0, inRange: !!p.inRange, kind: 'lp' }))] };
}

// 🏙 pure: a FAMILY BLOCK in the 3D city (owner, 2026-10-22: "my block supposed to look like the new city design and expanding — me adding
// buildings for markets i wanna use, under construction until i actually buy … shows open plots"). Islands that grow with the family's market
// buildings: BUILT = a tower sized by the position's $ value with its live APY on the sign · NOT YET = scaffolding + a crane · OPEN PLOTS =
// surveyed land with stakes, tap one to add a market. `bl` = /familia-block (its `layout` places every cell; 15 cells an island + a bridge).
export function blockPlan(bl, live = {}) {
  const blds = bl?.buildings || []; const byKey = Object.fromEntries(blds.map(b => [b.key, b]));
  const lps = (live.lp || []).filter(p => p && !p.empty); const lpBy = Object.fromEntries(lps.map(p => [p.id, p]));   // 🏗 your LP positions: a tower each, lit while IN RANGE
  const cells = blockCells(bl, lps); const per = Math.max(4, bl?.islandCells || ISLAND_CELLS);
  const chunks = []; for (let i = 0; i < cells.length; i += per) chunks.push(cells.slice(i, i + per)); if (!chunks.length) chunks.push([]);
  const islands = []; const slot = []; let gx = 0;
  chunks.forEach((ch, j) => {
    const n = Math.max(1, ch.length); const cols = chunks.length === 1 ? Math.max(3, Math.min(5, Math.ceil(Math.sqrt(n * 1.6)))) : 5; const rows = Math.max(2, Math.ceil(n / cols));
    const isl = island(j ? `block-${j}` : 'block', gx, 0, cols, rows, MCELL, j ? { name: `[${bl?.tag || '?'}] ISLAND ${j + 1}`, sub: `${ch.length} lots`, color: '#d4af37' }
      : { name: `[${bl?.tag || '?'}] ${String(bl?.name || 'THE BLOCK').toUpperCase()}`, sub: `${bl?.built || 0}/${blds.length} built${bl?.total ? ` · ${usd(bl.total)}` : ''}`, color: '#d4af37' });
    islands.push(isl); ch.forEach((_, k) => slot.push({ rect: rectOf(isl.gx, isl.gz, [k % cols, Math.floor(k / cols)], MCELL), island: isl.key }));
    gx = isl.x + isl.w + GAP + LAND;
  });
  const bridges = islands.slice(1).map((isl, j) => bridgeOf(islands[j], isl, `${bl?.tag || 'Family'} Bridge ${j + 1}`)).filter(Boolean);
  const markets = []; const lots = []; const places = []; let openK = 0; let standK = 0;
  cells.forEach((c, k) => {
    const { rect, island: isk } = slot[k]; const [kind, ...rest] = String(c).split(':'); const id = rest.join(':');
    if (kind === 'blk' && byKey[id]) {
      const b = byKey[id]; const pick = { blk: b.key };
      if (b.state === 'built') {
        const v = Number(b.usd) || 0;
        markets.push({ key: `blk-${b.key}`, pick, kind: b.kind, name: b.sym || b.name, proto: b.name, pool: true, tvl: v || b.tvl, apy: b.apy, hz: pulseHz({ tvl: v * 50 }),
          h: v ? heightOf(v * 40) * 1.2 : 2.6, rect, island: isk, m: b,
          lines: [`${b.sym || b.name}`, v ? `${usd(v)}${b.apy != null ? ` · APY ${apyTxt(b.apy)}` : ''}` : `${b.n || 1} position${(b.n || 1) > 1 ? 's' : ''}`, (b.errands || []).length ? `${b.errands.length} errand${b.errands.length > 1 ? 's' : ''}` : b.name] });
      } else lots.push({ id: `blk-${b.key}`, pick, kind: 'mine', tag: bl?.tag, owner: bl?.id, state: 'shut', power: 3000, rect, island: isk, seed: hash(b.key), lines: [`${b.name} · UNDER CONSTRUCTION`, b.why ? 'no position reader yet' : 'open a position to build it'] });
    } else if (kind === 'lp' && lpBy[id]) {
      const p = lpBy[id]; const v = Number(p.valueUsd) || 0; const f = Number(p.feeUsd) || 0;
      markets.push({ key: `lp-${p.id}`, pick: { lp: p.id }, kind: 'damm', name: p.sym, proto: 'Meteora DAMM v2', pool: true, tvl: v, apy: p.feeDay != null ? p.feeDay * 36500 : null, hz: p.inRange ? 1.8 : 0.4,
        h: heightOf(Math.max(1, v) * 4000) * 1.2, rect, island: isk, m: p, tone: p.inRange ? '#45e486' : '#6b6f78',
        lines: [p.sym, `${dollarsSmall(v)} · fees +${dollarsSmall(f)}`, p.inRange ? `IN RANGE · ${p.feeDay != null ? `${(p.feeDay * 100).toFixed(1)}%/day` : 'earning'}` : 'OUT OF RANGE · earning 0'] });
    } else if (kind === 'town' && TOWN[id]) {   // 🏘 a tool building — each sign carries its tool's own live number (lib/townLive)
      const t = TOWN[id]; const tt = id === 'tt' ? ttLive(live.coins) : null; const tl = live.town?.[id];
      places.push({ key: `town-${id}`, lens: id, pick: { town: id }, name: t.name, sub: t.sub, art: t.art, color: t.color, tool: true, isl: isk, rect, live: tt,
        lines: [t.name, tl?.line || (tt?.n ? `${tt.ready} READY · ${tt.n} on the intake` : t.sub)] });
    } else if (kind === 'pools') {   // 💧 MY POOLS: one combo building of every position the block holds, its live total on the sign
      const mp = myPools(bl, lps);
      places.push({ key: 'my-pools', lens: 'pools', pick: { pools: true }, name: MY_POOLS.name, sub: MY_POOLS.sub, art: MY_POOLS.art, color: MY_POOLS.color, tool: true, isl: isk, rect, money: true,
        lines: [MY_POOLS.name, mp.n ? `${usd(mp.usd)} · ${mp.n} position${mp.n > 1 ? 's' : ''}${mp.fees ? ` · +${dollarsSmall(mp.fees)} fees` : ''}` : 'no positions yet — open one'] });
    } else if (kind === 'stand' && STAND[id]) {   // ☕ a little street stand (dressing, never money)
      const st = STAND[id]; places.push({ key: `stand-${standK}`, lens: 'stand', pick: { stand: standK }, name: st.name, sub: st.sub, art: 'stand', stand: id, color: st.color, isl: isk, rect, lines: [`${st.icon} ${st.name}`, st.sub] }); standK += 1;
    } else if (kind === 'open') { lots.push({ id: `open-${openK}`, pick: { open: openK }, kind: 'free', open: true, rect, island: isk, seed: openK }); openK += 1; }
    // 'gap' (or a building that left the block) = bare land
  });
  const roads = islands.map(i => roadsOf(i));
  return { kind: 'block', key: bl?.id || 'block', islands, lots, marks: [], plaza: null, markets, places, spare: [], roads, bridges, gates: [],
    lights: roads.flatMap(r => r.nodes.filter(nd => !nd.edge).slice(0, 6)), loops: islands.map(ringOf), billboards: [], bounds: boundsOf(islands),
    center: { x: (islands[0].x + islands[islands.length - 1].x + islands[islands.length - 1].w) / 2, z: islands[0].z + islands[0].d / 2 } };
}

// pure: where the camera looks for a picked thing (plot id, landmark, market, place, island)
export function spotOf(plan, sel) {
  if (!plan || !sel) return null;
  if (sel.isl === 'keys') { const mine = plan.lots.find(l => l.kind === 'mine'); const k = mine?.island || plan.islands.find(x => x.key_)?.key; return k ? spotOf(plan, { isl: k }) : null; }   // 🏝 your key (or the first)
  if (sel.isl) { const i = plan.islands.find(x => x.key === sel.isl); return i ? { x: i.x + i.w / 2, z: i.z + i.d / 2, span: Math.max(i.w, i.d) } : null; }
  if (sel.town) { const t = plan.places.find(p => p.pick?.town === sel.town); return t ? centerOf(t.rect) : null; }   // 🏘 a town building
  if (sel.pools) { const t = plan.places.find(p => p.pick?.pools); return t ? centerOf(t.rect) : null; }   // 💧 MY POOLS
  if (sel.stand != null) { const t = plan.places.find(p => p.pick?.stand === sel.stand); return t ? centerOf(t.rect) : null; }   // ☕ a stand
  if (sel.lp) { const b = plan.markets.find(m => m.key === `lp-${sel.lp}`); return b ? centerOf(b.rect) : null; }   // 🏗 an LP position's tower
  if (sel.blk || sel.open != null) { const id = sel.blk ? `blk-${sel.blk}` : `open-${sel.open}`; const b = plan.lots.find(l => l.id === id) || plan.markets.find(m => m.key === id); return b ? centerOf(b.rect) : null; }   // 🏙 the family block
  const hit = sel.id ? plan.lots.find(l => l.id === sel.id) : sel.lm ? plan.marks.find(m => m.key === sel.lm) : sel.mk ? plan.markets.find(m => m.key === sel.mk) : sel.place ? (plan.places.find(p => p.key === sel.place) || (plan.inside || []).find(p => p.key === sel.place)) : null;
  return hit ? centerOf(hit.rect) : null;
}
