import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SwapPicker, PICK_LENSES } from './ArenaPrime';

jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map() }));
jest.mock('./terminal/PriceChart', () => ({ PriceChart: () => null }));   // the quick look's chart (lightweight-charts is ESM-only)
jest.mock('../lib/candles', () => ({ prefetchAllIntervals: () => {}, prefetchInterval: () => {} }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const tick = () => act(() => new Promise(r => setTimeout(r, 20)));

test('the real-card swap picker has every Lab lens + search, flags thin pools and lookalikes, and picks with its pool', async () => {
  const urls = [];
  global.fetch = jest.fn(async u => { urls.push(String(u));
    if (String(u).includes('list-proof')) return { ok: true, json: async () => ({ lists: { volume: { n: 60, medPct: -1.1, wonPct: 48, src: 'volume-leader callout' }, movers: { n: 60, medPct: -74.9, wonPct: 10, src: 'this list' }, ptrend: { n: 2, src: 'this list' } } }) };
    if (String(u).includes('search')) return { ok: true, json: async () => ({ pools: [{ baseAddress: 'BTC', pairAddress: 'pb', symbol: 'cbBTC', priceUsd: 60000, liquidityUsd: 9e6, real: true }, { baseAddress: 'FAKE', pairAddress: 'pf', symbol: 'BTC', priceUsd: 1, liquidityUsd: 9e6, impostor: true }] }) };
    if (String(u).includes('/fuses/trench')) return { ok: true, json: async () => ({ floor: 8000, checked: [{}, {}], rules: 'strict', rows: [{ mint: 'TR', pairAddress: 'ptr', symbol: 'TRN', price: 0.001, liq: 9000, holders: 512, score: 74, trench: true }, { mint: 'TT', pairAddress: 'ptt', symbol: 'TTHIN', price: 0.001, liq: 4000, trench: true }] }) };
    if (String(u).includes('contenders')) return { ok: true, json: async () => ({ divisions: [{ key: 'dip', rows: [{ mint: 'D', pairAddress: 'pd', symbol: 'DIP', price: 1, liq: 80000, score: 70 }] }],
      all: [{ mint: 'G1', pairAddress: 'pg1', symbol: 'GAUNT', price: 1, liq: 300000, score: 88, divisionLabel: '🌊 Deepest' }, { mint: 'D', pairAddress: 'pd', symbol: 'DIP', price: 1, liq: 80000, score: 70, divisionLabel: '📉 Dip buys', watch: true }] }) };
    return { ok: true, json: async () => ({ pools: [{ baseAddress: 'P', pairAddress: 'pp', symbol: 'POP', priceUsd: 2, liquidityUsd: 400000, change24h: 5 }, { baseAddress: 'T', pairAddress: 'pt', symbol: 'THIN', priceUsd: 2, liquidityUsd: 5000 }] }) }; });
  const picks = [];
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<SwapPicker out={{ symbol: 'WIF' }} have={[]} minLiq={20000} onPick={r => picks.push(r)} onClose={() => {}} />); });
  await tick();
  expect(PICK_LENSES.map(x => x[0])).toEqual(['fresh', 'ptrend', 'double', 'calls', 'fed', 'movers', 'bottom', 'pump', 'volume', 'trench', 'majors', 'arena']);   // every list its OWN set of coins
  // 🚀 it opens on what is MOVING (the live launch feed by hourly move) …
  expect(urls.find(u => u.includes('/fuses/discover'))).toContain('/fuses/discover?lens=fresh');   // 🔄 New to you opens first (every list woven, minus what the card touched in 24h)
  // 📏 every list tab carries its own 1-hour record; the open list explains it (too few settled = "starts now")
  expect(el.querySelector('[data-testid="sp-lp-movers"]').textContent).toBe('-75%');
  expect(el.querySelector('[data-testid="sp-lp-volume"]').textContent).toBe('-1%');
  expect(el.querySelector('[data-testid="sp-lp-ptrend"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="sp-lens-ptrend"]').click(); }); await tick();   // a list with its own record explains it
  expect(el.querySelector('[data-testid="sp-list-record"]').textContent).toMatch(/starts now/);
  expect(el.textContent).toContain('$POP');
  // 🏁 … and "All ranked" is every coin the Gauntlet ranks (each with the division it ranks best in; watch rows are pickable)
  await act(async () => { el.querySelector('[data-testid="sp-lens-arena"]').click(); }); await tick();
  expect(urls.some(u => u.includes('/fuses/contenders'))).toBe(true);
  expect(el.textContent).toContain('$GAUNT'); expect(el.textContent).toContain('🌊 Deepest'); expect(el.textContent).toContain('📉 Dip buys · watch');
  expect(el.querySelector('[data-testid="sp-pick-DIP"]').disabled).toBe(false);
  await act(async () => { el.querySelector('[data-testid="sp-lens-majors"]').click(); }); await tick();
  for (const k of ['majors', 'stocks', 'risers']) expect(urls.some(u => u.includes(`/fuses/discover?lens=${k}`))).toBe(true);   // one tab, three sources
  expect(el.querySelector('[data-testid="sp-pick-THIN"]').disabled).toBe(true);
  await act(async () => { el.querySelector('[data-testid="sp-pick-POP"]').click(); });
  expect(picks[0]).toMatchObject({ mint: 'P', pairAddress: 'pp' });
  await act(async () => { el.querySelector('[data-testid="sp-lens-bottom"]').click(); }); await tick();   // 🟢 dips + buy-bottom coins are ONE tab
  expect(urls.some(u => u.includes('lens=bottom'))).toBe(true); expect(el.querySelector('[data-testid="sp-lens-dip"]')).toBeNull();
  expect(el.querySelector('[data-testid="sp-bottom-note"]').textContent).toMatch(/Dips & bottoms/);
  // 🗑 trench lens: its own pool floor ($9K passes the $8K trench floor even though the card's floor is $20K), holders shown
  await act(async () => { el.querySelector('[data-testid="sp-lens-trench"]').click(); }); await tick();
  expect(el.querySelector('[data-testid="sp-trench-note"]').textContent).toContain('2 scanned');
  expect(el.textContent).toContain('512 holders');
  expect(el.querySelector('[data-testid="sp-pick-TRN"]').disabled).toBe(false);
  expect(el.querySelector('[data-testid="sp-pick-TTHIN"]').disabled).toBe(true);
  await act(async () => { const i = el.querySelector('[data-testid="sp-search"]'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(i, 'btc'); i.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(() => new Promise(r => setTimeout(r, 400)));
  expect(urls.some(u => u.includes('/fuses/search?q=btc'))).toBe(true);
  expect(el.querySelector('[data-testid="sp-pick-BTC"]').disabled).toBe(true);   // lookalike can't be picked
  expect(el.querySelector('[data-testid="sp-pick-cbBTC"]').disabled).toBe(false);
});

test('a flagged creator and a pump pulse are shown on the row, and the pick stays the owner\'s', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ pools: [
    { baseAddress: 'S', pairAddress: 'ps', symbol: 'SIR', priceUsd: 0.00008, liquidityUsd: 23815, warn: 'Creator is HIGH risk (blocklist / rug report / serial sniper). The engine will not buy this coin.' },
    { baseAddress: 'Q', pairAddress: 'pq', symbol: 'PLS', priceUsd: 1, liquidityUsd: 90000, pulse: true }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<SwapPicker out={{ symbol: 'WIF' }} have={[]} minLiq={10000} onPick={() => {}} onClose={() => {}} />); });
  await tick();
  expect(el.querySelector('[data-testid="sp-warn-SIR"]').textContent).toBe('⚠ creator');
  expect(el.querySelector('[data-testid="sp-warn-SIR"]').getAttribute('data-tip')).toContain('it is your pick');
  expect(el.querySelector('[data-testid="sp-pick-SIR"]').disabled).toBe(false);   // $23.8K pool clears the owner's $10K pick floor
  expect(el.querySelector('[data-testid="sp-pulse-PLS"]')).toBeTruthy();
  expect(el.querySelector('[data-testid="sp-warn-PLS"]')).toBeNull();
});

test('trench metas: a visitor taps one to VIEW it, and the weather strip reads the forecast', async () => {
  const { TrenchScan, WeatherStrip } = require('./ArenaPrime');
  const urls = [];
  const metas = [{ key: 'sprout', label: '🌱 Sprout', blurb: 'early', pass: 0, cfg: { maxAgeH: 1, minMcap: 10000, maxMcap: 100000, minHolders: 150, minTxns1h: 120, minVol1h: 5000 } },
    { key: 'flood', label: '🌊 Flood', blurb: 'volume', pass: 2, cfg: { maxAgeH: 12, minMcap: 20000, maxMcap: 600000, minHolders: 300, minTxns1h: 400, minVol1h: 50000 } }];
  global.fetch = jest.fn(async u => { urls.push(String(u));
    if (String(u).includes('forecast')) return { ok: true, json: async () => ({ level: 'rain', avgPct: -7.2, n: 80, trend: 'clearing', breadthPct: 62, buyersPct: 55, coins: 48, outlook: 'mixed', buys: 'real money buys only strong runners in deep pools' }) };
    return { ok: true, json: async () => ({ cfg: { mode: 'auto', meta: 'breakout' }, metas, view: String(u).includes('meta=flood') ? 'flood' : undefined, checked: [], pass: 0, rules: 'r', funnel: [] }) }; });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><WeatherStrip /><TrenchScan /></>); });
  await tick();
  expect(el.querySelector('[data-testid="weather-strip"]').textContent).toContain('RAIN');
  expect(el.querySelector('[data-testid="wx-breadth"]').textContent).toContain('62% of 48 launch coins green');
  expect(el.querySelector('[data-testid="trench-cfg"]')).toBeNull();                 // no settings without HQ
  await act(async () => { el.querySelector('[data-testid="trench-meta-flood"]').click(); }); await tick();
  expect(urls.some(u => u.includes('/fuses/trench?meta=flood'))).toBe(true);
  expect(el.textContent).toContain('VIEWING 🌊 Flood');
});

test('pick log: a pick that came in and a refused buy both read plainly, with the keeper reason', () => {
  const { pickLog } = require('./ArenaPrime');
  const rows = pickLog([{ kind: 'rotate', at: 1, symbol: 'PENGU', why: '🎯 your pick — swapped in at the round', to: ['STUDS'] }, { kind: 'compound', at: 2 },
    { kind: 'rotate', at: 3, symbol: 'Sirius', why: "⏳ $Sirius couldn't be bought safely — benched (sells back for 6.8% less (> 6%)) — slot back to card cash" }]);
  expect(rows[0]).toMatchObject({ ok: false });
  expect(rows[0].text).toContain('$Sirius was not bought');
  expect(rows[0].text).toContain('6.8% less');
  expect(rows[0].text).toContain('back in the card');
  expect(rows[1]).toMatchObject({ ok: true, text: '$STUDS came in for $PENGU' });
});

test('activity lists what the card did — recycles and cash put back to work — newest first', async () => {
  const { CardMoves } = require('./ArenaPrime');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CardMoves ago={() => '1m ago'} events={[
    { kind: 'skim', at: 10, symbol: 'SAPLING', usd: 0.08, why: "♻ round 210: 50% of $SAPLING's profit recycled into the card's other coins", to: ['card'] },
    { kind: 'compound', at: 20, usd: 0.27, why: 'idle cash back into the card', to: ['WAIF', 'HIGGS'], n: 3 }, { kind: 'deal', at: 30, why: 'dealt' }]} />); });
  const rows = [...el.querySelectorAll('[data-testid="card-moves"] li')].map(li => li.textContent);
  expect(rows.length).toBe(2);
  expect(rows[0]).toContain('idle cash back into the card → $WAIF, $HIGGS (×3)');
  expect(rows[1]).toContain('$SAPLING');
  expect(rows[1]).toContain('recycled');
});

test('a pick can be swapped in now or wait for the bell', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ pools: [{ baseAddress: 'P', pairAddress: 'pp', symbol: 'POP', priceUsd: 2, liquidityUsd: 400000 }] }) }));
  const picks = [];
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<SwapPicker out={{ symbol: 'WIF' }} have={[]} minLiq={0} onPick={(r, now) => picks.push([r.symbol, now])} onClose={() => {}} />); });
  await tick();
  expect(el.querySelector('[data-testid="sp-pick-POP"]').textContent).toBe('⚡ Swap now');
  await act(async () => { el.querySelector('[data-testid="sp-pick-POP"]').click(); });   // ⚡ Swap now
  await act(async () => { el.querySelector('[data-testid="sp-bell-POP"]').click(); });   // ⏱ at the bell
  expect(picks).toEqual([['POP', true], ['POP', false]]);
});

test('every tab filters by its own calls and opens the quick look (chart + vitals + pick) from the ticker', async () => {
  const { callLanes } = require('./ArenaPrime');
  const rows = [{ tv: { call: ['🚀', 'BREAKOUT', 'good'] } }, { tv: { call: ['🚀', 'BREAKOUT', 'good'] } }, { tv: { call: ['🧯', 'BLOW-OFF TOP', 'bad'] } }, { tv: { call: ['👀', 'WATCH', 'warn'] } }, {}];
  expect(callLanes(rows)).toEqual([['BREAKOUT', 'good', '🚀', 2], ['WATCH', 'warn', '👀', 1], ['BLOW-OFF TOP', 'bad', '🧯', 1]]);   // good first, then by count
  global.fetch = jest.fn(async u => (String(u).includes('list-proof') ? { ok: true, json: async () => ({ lists: {} }) } : String(u).includes('sparks') ? { ok: true, json: async () => ({ sparks: {} }) }
    : { ok: true, json: async () => ({ pools: [{ baseAddress: 'A', pairAddress: 'pa', symbol: 'RUN', priceUsd: 2, liquidityUsd: 400000, vol1h: 90000, top10: 18, tv: { kind: 'mover', call: ['🚀', 'BREAKOUT', 'good'], meters: [['🚀', 80], ['🧯', 20]], tags: [] } },
      { baseAddress: 'B', pairAddress: 'pb', symbol: 'TOP', priceUsd: 2, liquidityUsd: 400000, tv: { kind: 'mover', call: ['🧯', 'BLOW-OFF TOP', 'bad'], meters: [['🚀', 30], ['🧯', 90]], tags: [] } }] }) }));
  const picks = [];
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<SwapPicker out={{ symbol: 'WIF' }} have={[]} onPick={(r, now) => picks.push([r.symbol, now])} onClose={() => {}} />); });
  await tick();
  expect(el.querySelector('[data-testid="sp-call-all"]').textContent).toBe('All 2');
  await act(async () => { el.querySelector('[data-testid="sp-call-BLOW-OFF-TOP"]').click(); });
  expect(el.querySelector('[data-testid="sp-open-TOP"]')).not.toBeNull(); expect(el.querySelector('[data-testid="sp-open-RUN"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="sp-call-all"]').click(); });
  await act(async () => { el.querySelector('[data-testid="sp-open-RUN"]').click(); }); await tick();
  const q = document.querySelector('[data-testid="trench-quick"]');
  expect(q).not.toBeNull(); expect(q.textContent).toContain('$RUN'); expect(q.querySelector('[data-testid="tql-vitals"]').textContent).toContain('18%');   // top-10 tile from the row
  expect(q.querySelector('.tql-safe')).toBeNull();   // a list with no safety scan says nothing about safety (never a made-up "unscanned")
  await act(async () => { q.querySelector('[data-testid="tql-pick"]').click(); });
  expect(picks).toEqual([['RUN', true]]); expect(document.querySelector('[data-testid="trench-quick"]')).toBeNull();
});

test('quick-look live panels: socials (bad links dropped), flow by the window that fits the chart, Pump callout, feeders, edge tiles', async () => {
  const { Socials, FlowWindows, PumpCall, Feeders, socialLinks, flowShift, FuseBanner } = require('./QuickPulse');
  const { edgeTiles } = require('./TrenchQuick');
  expect(socialLinks({ mint: 'ABCpump', site: 'https://a.xyz', x: 'javascript:alert(1)', tg: null }).map(l => l[1])).toEqual(['Site', 'Pump']);   // only http(s) links; Pump page from the mint
  const win = { '5m': { buyPct: 72, organicPct: 3, netBuyers: 9, traders: 25, avgTrade: 10, holderChg: 1.5, liqChg: -20, vol: 400, volChg: 10 }, '1h': { buyPct: 55, organicPct: 30, netBuyers: -4, traders: 300, vol: 9000 } };
  expect(flowShift(win)).toEqual(['⏫', 'buyers stepping in (+17 pts vs the hour)', 'good']); expect(flowShift({})).toBeNull();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const row = { symbol: 'RUN', mint: 'ABCpump', fd: { n: 3, fresh: 2, active: 1, capUsd: 9000, score: 44, kids: [{ mint: 'k1', symbol: 'KID', mcap: 3000, ageMin: 4, lastMin: 1 }] }, pairedWith: { symbol: 'BIG' } };
  await act(async () => { root.render(<div><Socials r={{ mint: 'x' }} /><FlowWindows win={win} tf="1m" /><PumpCall pc={{ calls: 3, callers: 2, verified: 1, heat: 61, views: 755, firstMc: 6736, lastAt: Date.now(), lead: { user: 'sh4', thesis: 'ca is posted', mult: 1.9 } }} />
    <Feeders r={row} /><FuseBanner out={{ symbol: 'WIF' }} count={42} good={5} tick={1} lensLabel="🧲 Fed runners" /></div>); });
  expect(el.querySelector('[data-testid="qp-socials"]').textContent).toContain('no socials set');
  const flow = el.querySelector('[data-testid="qp-flow"]');
  expect(flow.textContent).toContain('FLOW · LAST 5M · follows the chart'); expect(flow.textContent).toContain('72%'); expect(flow.textContent).toContain('+9');   // 1m chart → the 5-minute window
  await act(async () => { el.querySelector('[data-testid="qp-win-1h"]').click(); });
  expect(flow.textContent).toContain('FLOW · LAST 1H'); expect(flow.textContent).toContain('-4');
  expect(el.querySelector('[data-testid="qp-call"]').textContent).toContain('@sh4'); expect(el.querySelector('[data-testid="qp-call"]').textContent).toContain('first called at $6.7K');
  expect(el.querySelector('[data-testid="qp-feeders"]').textContent).toContain('3 COINS PAIRED WITH IT'); expect(el.querySelector('[data-testid="qp-paired"]').textContent).toContain('$BIG');
  expect(el.querySelector('[data-testid="swap-banner"]').textContent).toContain('Swap $WIF for…');
  const t = Object.fromEntries(edgeTiles({ vol1h: 9000, txns1h: 3000, mcap: 60000, liq: 1200, fd: row.fd }).map(x => [x[0], [x[1], x[2]]]));
  expect(t['AVG TRADE']).toEqual(['$3.0', true]); expect(t.TURNOVER).toEqual(['15.0%/h', false]); expect(t['EXIT DEPTH']).toEqual(['2.0%', true]); expect(t.FEEDERS[0]).toBe('3 · 1 live');
});

test('caller scoreboard tab, proven-caller line and the call-rush alert select', async () => {
  const { PumpCallouts, PumpCall, CallAlert } = require('./QuickPulse');
  const feed = { top: [{ id: 't', mint: 'M', symbol: 'BUN', user: 'one', mult: 0.9, atMc: 1e6, views: 5 }], latest: [], n: 3, alertCapK: 0, alertCaps: [0, 50, 100],
    callers: [{ user: 'ace', n: 4, medMult: 1.6, wonPct: 75, best: 3, proven: true }, { user: 'rug', n: 2, medMult: 0.4, wonPct: 0, best: 0.9, proven: false }] };
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(feed) }));
  const posts = []; const call = jest.fn((path, o) => { posts.push([path, JSON.parse(o.body)]); return Promise.resolve({}); });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<div><PumpCallouts /><PumpCall pc={{ calls: 2, callers: 2, heat: 40, pro: 1, pros: ['ace'], lead: { user: 'x' } }} /><CallAlert call={call} /></div>); });
  await act(async () => { await Promise.resolve(); });
  await act(async () => { el.querySelector('[data-testid="pcl-best"]').click(); });
  const b = el.querySelector('[data-testid="pcl-callers"]');
  expect(b.textContent).toContain('🎯 @ace'); expect(b.textContent).toContain('1.6×'); expect(b.textContent).toContain('@rug'); expect(el.querySelector('[data-testid="pcl-first"]')).toBeNull();
  expect(el.querySelector('[data-testid="qp-pro"]').textContent).toContain('1 proven caller on it: @ace');
  const sel = el.querySelector('[data-testid="call-alert-cap"]'); expect([...sel.options].map(o => o.textContent)).toEqual(['off', 'coins under $50K', 'coins under $100K']);
  await act(async () => { sel.value = '100'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(posts).toEqual([['/admin/arena/prime', { callAlert: { capK: 100 } }]]);
});
