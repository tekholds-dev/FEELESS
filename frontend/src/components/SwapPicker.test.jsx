import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SwapPicker, PICK_LENSES } from './ArenaPrime';

jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map() }));
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
  expect(PICK_LENSES.map(x => x[0])).toEqual(['ptrend', 'movers', 'bottom', 'pump', 'volume', 'trench', 'majors', 'arena']);   // every list its OWN set of coins
  // 🚀 it opens on what is MOVING (the live launch feed by hourly move) …
  expect(urls.find(u => u.includes('/fuses/discover'))).toContain('/fuses/discover?lens=ptrend');   // 🔥 Pump's Trending tab opens first
  // 📏 every list tab carries its own 1-hour record; the open list explains it (too few settled = "starts now")
  expect(el.querySelector('[data-testid="sp-lp-movers"]').textContent).toBe('-75%');
  expect(el.querySelector('[data-testid="sp-lp-volume"]').textContent).toBe('-1%');
  expect(el.querySelector('[data-testid="sp-lp-ptrend"]')).toBeNull();
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
  expect(el.querySelector('[data-testid="when-now"]').getAttribute('aria-pressed')).toBe('true');   // ⚡ now is the default
  await act(async () => { el.querySelector('[data-testid="sp-pick-POP"]').click(); });
  await act(async () => { el.querySelector('[data-testid="when-bell"]').click(); });
  await act(async () => { el.querySelector('[data-testid="sp-pick-POP"]').click(); });
  expect(picks).toEqual([['POP', true], ['POP', false]]);
});
