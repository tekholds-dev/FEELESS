import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ArenaPrime, arenaRow, primeRow, allTime } from './ArenaPrime';
import { CardEarnings } from './CardEarnings';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(20); return el; };
const CARD = { id: 'prime-degen', tpl: 'degen', tier: 'blaze', goodDays: 6, loggedDays: 8, lowPct: -7.5, label: '🔥 Prime Blaze', at: 1, lastRotateAt: Date.now() / 1000, startUsd: 100, valueUsd: 112.5, pnlPct: 12.5, compoundedUsd: 12.5, takenUsd: 12.5, feesUsd: 0.9, cash: 0,
  legs: [{ mint: 'S', pairAddress: 'PS', symbol: 'SOL', role: 'anchor', stars: 5, units: 0.1, costUsd: 20, usd: 21, now: 210 }, { mint: 'A', pairAddress: 'PA', symbol: 'AAA', role: 'pool', stars: 4, units: 16.7, costUsd: 25, usd: 25, now: 1.5 }, { mint: 'R', pairAddress: 'PR', symbol: 'RUN', role: 'runner', units: 30, costUsd: 25, usd: 30, now: 1 }],
  events: [{ kind: 'tp', at: Date.now() / 1000 - 600, symbol: 'AAA', usd: 12.5, why: '+50% ≥ +30%', to: ['RUN'] }] };

test('prime cards: live card, compounded $, rotation clock, Buy now loads the Lab, earnings show where the profit went', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD], cfg: { sizeUsd: 100, rotateHours: 6, rotateCount: 2, compound: true } }) }));
  const onLoad = jest.fn();
  const el = await mount(<ArenaPrime onLoad={onLoad} />);
  expect(el.textContent).toContain('+12.5%'); expect(el.textContent).toContain('$12.50');
  await act(async () => { el.querySelector('[data-testid="prime-buy-degen"]').click(); });
  expect(onLoad.mock.calls[0][0].map(l => [l.symbol, l.runner])).toEqual([['SOL', false], ['AAA', false], ['RUN', true]]);
  const card = el.querySelector('[data-testid="prime-degen"]');
  expect(card.className).toContain('tier-blaze'); expect(card.className).toContain('is-hot'); expect(card.textContent).toContain('BLAZE');
  expect(card.textContent).toContain('⚓ anchor'); expect(card.textContent).toContain('★★★★★');
  expect(el.querySelector('[data-testid="prime-rec-degen"]').textContent).toMatch(/6\/8.*-7\.5%/);
  await act(async () => { el.querySelector('[data-testid="prime-earn-degen"]').click(); });
  const ce = document.querySelector('[data-testid="card-earnings"]');
  expect(ce.textContent).toContain('💰 Auto TP'); expect(ce.textContent).toContain('→ $RUN'); expect(ce.textContent).toContain('not in P&L');
});

test('prime row maps to a live card without inventing numbers', () => {
  const r = primeRow(CARD);
  expect(r.legs[2]).toMatchObject({ tokens: 30, usd: 25, valueUsd: 30, role: 'runner' }); expect(r.pnlUsd).toBeCloseTo(12.5);
});

test('Arena real card keeps confirmed-book equity instead of re-summing only visible legs', () => {
  const real = { ...CARD, real: true, startUsd: 4.04, valueUsd: 5.05, realBook: { fundedUsd: 7 },
    legs: CARD.legs.map(l => ({ ...l, costUsd: 1, usd: 1 })) };
  const live = new Map(real.legs.map(l => [l.pairAddress, { price: 0.01 }]));
  const row = arenaRow(real, live);
  expect(row.costUsd).toBe(7);
  expect(row.valueUsd).toBe(5.05);
  expect(row.pnlUsd).toBeCloseTo(-1.95);
  expect(row.pnlPct).toBeCloseTo(-27.857);
});

test('collect is one tap and disabled when the card is not up', async () => {
  const onCollect = jest.fn(); const onClose = jest.fn();
  await mount(<CardEarnings title="Mine" taken={3} compounded={1} gainNow={0} onCollect={onCollect} onClose={onClose} />);
  expect([...document.querySelectorAll('[data-testid="ce-collect"]')].pop().disabled).toBe(true);
  await act(async () => { [...document.querySelectorAll('[data-testid="card-earnings"]')].pop().click(); }); expect(onClose).toHaveBeenCalled();
});

test('HQ: ⇄ replaces one coin on a Prime card, 🃏 re-deals one tier', async () => {
  const { PrimeControls } = require('./ArenaPrime');
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD], cfg: { sizeUsd: 100, rotateHours: 6, rotateCount: 2, compound: true, floorPct: 20, on: true } }) }));
  const call = jest.fn(async () => ({ cfg: {} }));
  const el = await mount(<PrimeControls call={call} />);
  await act(async () => { el.querySelector('[data-testid="prime-swap-degen-PR"]').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body)).toEqual({ replace: { tpl: 'degen', pairAddress: 'PR' } });
  await act(async () => { el.querySelector('[data-testid="prime-redeal-degen"]').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body)).toEqual({ redeal: 'degen' });
});

test('HQ: rotate every — typed minutes save as hours (15 min floor)', async () => {
  const { PrimeControls } = require('./ArenaPrime');
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD], cfg: { sizeUsd: 100, rotateHours: 1, rotateCount: 1, compound: true, floorPct: 20, on: true } }) }));
  const call = jest.fn(async (p, o) => ({ cfg: { sizeUsd: 100, rotateHours: JSON.parse(o.body).cfg.rotateHours ?? 1, rotateCount: 1, compound: true, floorPct: 20, on: true } }));
  const el = await mount(<PrimeControls call={call} />);
  const inp = el.querySelector('[data-testid="prime-rotate-min"]'); expect(inp.value).toBe('60');
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(inp, '45'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { inp.focus(); inp.blur(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body).cfg.rotateHours).toBe(0.75);
});

test('meta config in one click + stop mode switch + parked coins shown on the card', async () => {
  const { PrimeControls, ArenaPrime, PRIME_META } = require('./ArenaPrime');
  const cfg = { sizeUsd: 100, rotateHours: 1, rotateCount: 1, compound: true, floorPct: 20, on: true, slMode: 'replace' };
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [{ ...CARD, why: 'all runners', parked: [{ pairAddress: 'PX', symbol: 'GONE', usd: 18.5, backAt: 0.0012 }] }], cfg }) }));
  const call = jest.fn(async (p, o) => ({ cfg: { ...cfg, ...JSON.parse(o.body).cfg } }));
  const el = await mount(<PrimeControls call={call} />);
  await act(async () => { el.querySelector('[data-testid="prime-meta"]').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body).cfg).toEqual(PRIME_META);
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent === '❄ Hold').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body).cfg).toEqual({ slMode: 'hold' });
  const ap = await mount(<ArenaPrime onLoad={() => {}} />);
  expect(ap.textContent).toContain('🅿 $GONE'); expect(ap.textContent).toContain('$18.50'); expect(ap.textContent).toContain('all runners');
});

test('engine pick: each round length gets its own config, and a losing clock is never called profitable', () => {
  const { enginePick } = require('./ArenaPrime');
  const suggest = { 5: { n: 81, medPct: -40.7, upPct: 16, profitable: false, cfg: { minDrop: '20', confirm: '3', tp: '100', sl: '20' } }, 60: { n: 73, medPct: 4.2, upPct: 58, profitable: true, cfg: { minDrop: '10', confirm: '2', tp: '300', sl: '30' } } };
  const p = enginePick(suggest, 0.08);
  expect(p.mine.clock).toBe(5); expect(p.mine.profitable).toBe(false); expect(p.patch).toEqual({ rotateMinDrop: 20, rotateConfirm: 3 });
  expect(p.top.clock).toBe(60);                                   // the screen points at the clock that did best
  expect(enginePick(suggest, 1).patch).toEqual({ rotateMinDrop: 10, rotateConfirm: 2 });
  expect(enginePick({}, 1)).toBeNull();
});

test('your last real Fuse stays on My cards as a faint card; tapping it opens the run history (real runs only)', async () => {
  const { RecentRuns } = require('./ArenaPrime');
  const React = require('react'); const { act } = require('react'); const { createRoot } = require('react-dom/client');
  global.fetch = jest.fn(async url => ({ ok: true, json: async () => (String(url).endsWith('/safe') ? { runs: [{ at: 200, card: 'safe', label: '💎 Prime Diamond', startUsd: 2.14, endUsd: 1.78, pct: -17, real: true }, { at: 100, card: 'safe', label: '💎 Prime Diamond', startUsd: 100, endUsd: 110, pct: 10 }] } : { runs: [] }) }));
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<RecentRuns cards={[{ tpl: 'safe', tier: 'diamond', label: '💎 Prime Diamond', legs: [], valueUsd: 4, startUsd: 4 }, { tpl: 'ever', legs: [] }]} />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const card = host.querySelector('[data-testid="recent-card"]');
  expect(card).toBeTruthy(); expect(host.textContent).toContain('closed'); expect(host.textContent).toContain('$1.78'); expect(host.querySelector('.rr-list')).toBeNull();
  act(() => card.click());
  expect(host.querySelectorAll('.rr-list li').length).toBe(1);                              // the paper run is not yours
});

test('where am I down: coins on the card now + already sold always add up to all-time', () => {
  const { whereDown } = require('./ArenaPrime');
  const c = { valueUsd: 4.69, legs: [{ usd: 1.43, costUsd: 1.43 }, { usd: 1.37, costUsd: 1.37 }, { usd: 1.06, costUsd: 1.07 }, { usd: 0.77, costUsd: 0.87 }, { usd: 0.05, costUsd: 0 }] };
  const w = whereDown(c, 5);
  expect(w).toEqual({ held: -0.11, sold: -0.2, all: -0.31 });   // your screenshot: −$0.11 on coins now, −$0.20 already sold
  expect(Math.round((w.held + w.sold) * 100) / 100).toBe(w.all);
});

test('all-time P&L leaves out the network fees the card paid (fees shown apart)', () => {
  const { allTime, whereDown } = require('./ArenaPrime');
  const c = { valueUsd: 4.69, cardFeesUsd: 0.02, math: { pnlUsd: -0.29 }, legs: [{ usd: 0.77, costUsd: 0.87 }] };
  expect(allTime(c, 5)).toBe(-0.29);
  expect(allTime({ valueUsd: 4.69, cardFeesUsd: 0.02 }, 5)).toBeCloseTo(-0.29);
  expect(whereDown(c, 5)).toEqual({ held: -0.1, sold: -0.19, all: -0.29 });
});

test('trench scan shows each finalist with what it passed or failed', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { TrenchScan } = require('./ArenaPrime');
  global.fetch = jest.fn(async () => ({ json: async () => ({ pass: 1, rules: '≥ 400 holders', checked: [
    { mint: 'A', symbol: 'TRN', ok: true, holders: 520, mcap: 28000, ageH: 1.5, trenchWhy: [{ why: '520 holders · 900 trades/1h' }] },
    { mint: 'B', symbol: 'RUG', ok: false, holders: 120, mcap: 24000, ageH: 0.5, fails: ['≥ 400 holders', 'mint + freeze authority revoked'] }] }) }));
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<TrenchScan />); });
  await act(() => new Promise(r => setTimeout(r, 10)));
  expect(el.textContent).toContain('1 PASS NOW'); expect(el.textContent).toContain('✅ $TRN'); expect(el.textContent).toContain('520 holders · $28K mc');
  expect(el.textContent).toContain('❌ $RUG'); expect(el.textContent).toContain('mint + freeze authority revoked');
});

test('swap steps: one transaction at a time — sold (done) → buying (sending) → next; nothing when idle', async () => {
  const { SwapFlow } = require('./ArenaPrime');
  const k = { flow: [{ side: 'sell', symbol: 'POPCAT', state: 'done', usd: 0.6 }, { side: 'buy', symbol: 'ore', state: 'failed', usd: 0.6, err: 'live pool too thin' },
    { side: 'buy', symbol: 'baton', state: 'sending', usd: 0.59 }, { side: 'buy', symbol: 'ORCA', state: 'next', usd: 0.4 }] };
  const el = await mount(<SwapFlow k={k} />);
  const steps = [...el.querySelectorAll('[data-testid="swap-flow"] li')];
  expect(steps.map(s => s.className)).toEqual(['is-done', 'is-failed', 'is-sending', 'is-next']);
  expect(steps[0].textContent).toContain('SELL $POPCAT'); expect(steps[0].textContent).toContain('done');
  expect(steps[2].textContent).toContain('BUY $baton'); expect(steps[2].textContent).toContain('sending');
  expect(steps[1].getAttribute('data-tip')).toBe('live pool too thin');
  const held = await mount(<SwapFlow k={{ flow: [], holdingSell: true }} />);
  expect(held.textContent).toContain('old coin kept');
  const idle = await mount(<SwapFlow k={{ flow: [] }} />);
  expect(idle.querySelector('[data-testid="swap-flow"]')).toBeNull();
});

test('trench settings: engine tunes by default; My settings shows the soft checks only and saves a pick', async () => {
  const { TrenchScan } = require('./ArenaPrime');
  const base = { pass: 0, checked: [], rules: 'r', options: { minHolders: [100, 200, 400], minTxns1h: [60, 250], minVol1h: [5000, 10000], minMcap: [20000], maxMcap: [150000], maxAgeH: [6, 12] } };
  let cfg = { mode: 'auto', minHolders: 400, minTxns1h: 250, minVol1h: 10000, minMcap: 20000, maxMcap: 150000, maxAgeH: 6 };
  global.fetch = jest.fn(async () => ({ json: async () => ({ ...base, cfg }) }));
  const call = jest.fn(async (_p, o) => { cfg = JSON.parse(o.body).trenchCfg; return {}; });
  const el = await mount(<TrenchScan call={call} />);
  expect(el.querySelector('[data-testid="trench-auto"]').className).toBe('on');
  expect(el.querySelector('[data-testid="trench-minHolders"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="trench-own"]').click(); }); await tick(20);
  expect(call.mock.calls[0][0]).toBe('/admin/arena/prime'); expect(cfg.mode).toBe('own');
  expect(el.textContent).toContain('YOUR SETTINGS');
  expect([...el.querySelectorAll('.tscan-own select')].map(s => s.getAttribute('data-testid'))).toEqual(['trench-minHolders', 'trench-minTxns1h', 'trench-minVol1h', 'trench-minMcap', 'trench-maxMcap', 'trench-maxAgeH']);
  const sel = el.querySelector('[data-testid="trench-minHolders"]');
  await act(async () => { sel.value = '200'; sel.dispatchEvent(new Event('change', { bubbles: true })); }); await tick(20);
  expect(cfg.minHolders).toBe(200);
  const viewer = await mount(<TrenchScan />);          // no admin call → read-only (no settings shown)
  expect(viewer.querySelector('[data-testid="trench-cfg"]')).toBeNull();
});

test('real card face shows the same all-time number as the header: price result, fees apart', () => {
  const c = { id: 'x', label: 'Blaze', real: true, valueUsd: 3.12, startUsd: 3.73, cardFeesUsd: 0.28, realBook: { fundedUsd: 5 }, legs: [] };
  const r = primeRow(c);
  expect(r.pnlUsd).toBeCloseTo(-1.6, 2); expect(r.pnlPct).toBeCloseTo(-32, 1);          // not −1.88 / −37.5% (that mixed the fees in)
  expect(r.pnlUsd).toBeCloseTo(allTime(c, 5), 6);
  const paper = primeRow({ id: 'p', label: 'P', valueUsd: 110, startUsd: 100, legs: [] });
  expect(paper.pnlUsd).toBeCloseTo(10, 6); expect(paper.pnlPct).toBeCloseTo(10, 6);
});

test('swap picker rows carry the 5-minute and 1-hour move, and falling coins are flagged like the engine flags them', () => {
  const { pickRow, isFalling } = require('./ArenaPrime');
  expect(pickRow({ mint: 'm', pairAddress: 'p', symbol: 'X', chg5m: -4.2, chg1h: 6 })).toMatchObject({ chg5m: -4.2, chg1h: 6 });
  expect(pickRow({ baseAddress: 'm', pairAddress: 'p', symbol: 'X', change5m: 1.5, change1h: -2 })).toMatchObject({ chg5m: 1.5, chg1h: -2 });
  expect(pickRow({ mint: 'm', pairAddress: 'p' }).chg5m).toBeNull();
  expect(isFalling(-3, 10)).toBe(true); expect(isFalling(1, -8)).toBe(true);
  expect(isFalling(-2.9, -7.9)).toBe(false); expect(isFalling(null, null)).toBe(false);
});

test('real card settings include profit skim (when + where) and bank at the lock', () => {
  const src = require('fs').readFileSync(require('path').join(__dirname, 'ArenaPrime.jsx'), 'utf8');
  for (const k of ["['skimAt'", "['skimTo'", "['lockBankPct'", 'data-testid={`skim-${l.symbol}`}', 'data-testid={`coin-${l.symbol}`}', 'skim: { tpl: c.tpl, pairAddress: l.pairAddress, to }'])
    expect(src).toContain(k);
  expect(src).toMatch(/rows\(\[[^\]]*'skimAt', 'skimTo'/);                               // both settings are actually on the Exits tab
});
