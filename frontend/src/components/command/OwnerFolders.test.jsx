import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { FallbackFolder, PayFolder, PoolDesk, PyAgentsFolder, SafetyFolder, SpotsFolder, bandBoost, bandState, moveLoss, useOwnerFolders } from './OwnerFolders';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./HiveBoard', () => ({ ColonyPot: () => <div data-testid="pot" /> }));
const D = { cfg: { collectivePoolPct: 20, reservePct: 20, spotMaxPct: 50, capPct: 3, minStakeUsd: 1 }, defaults: { reservePct: 20, spotMaxPct: 50, capPct: 3, minStakeUsd: 1 }, bounds: { reservePct: [0, 90], spotMaxPct: [5, 100], capPct: [1, 100], minStakeUsd: [0, 1000] }, stake: { compoundUsd: 40, keepUsd: 25, paidUsd: 3, profitUsd: 60 }, stakeAgents: [{ id: 'a', name: 'Happy', x: 1.87, pointsLeft: 15, nowPct: 1.87 }], pools: [{ id: 'p1', pair: 'SOL-USDC', platform: 'meteora', address: 'Addr1', on: true, profitUsd: 60, inUsd: 100, lossUsd: 20, stopPct: 15 }], stops: ['p1'], payLog: [{ at: 1790000000, kind: 'bonus', name: 'Happy', usd: 5, why: 'best proof' }], held: [] };
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return { el, root, q: t => el.querySelector(`[data-testid="${t}"]`) }; };
const click = async n => act(async () => { n.dispatchEvent(new MouseEvent('click', { bubbles: true })); });
const type = async (n, v) => act(async () => { Object.getOwnPropertyDescriptor(n.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype, 'value').set.call(n, v); n.dispatchEvent(new Event(n.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); });

test('pay sooner takes an amount and a source, never more than is there', async () => {
  const save = jest.fn(); const { q, root } = await mount(<PayFolder d={D} save={save} busy={false} />);
  expect(q('ofd-early-go').disabled).toBe(true);
  await type(q('ofd-early-usd'), '50'); expect(q('ofd-early-go').disabled).toBe(true);   // only 40 compounded
  await type(q('ofd-early-usd'), '10'); await click(q('ofd-early-go'));
  expect(save.mock.calls[0][1].payEarly).toMatchObject({ source: 'compound', usd: 10, token: 'USDC' }); expect(save.mock.calls[0][1].payEarly.nonce).toBeTruthy();
  await type(q('ofd-bonus-agent'), 'a'); await type(q('ofd-bonus-usd'), '5'); await click(q('ofd-bonus-go')); expect(save.mock.calls[1][1].bonus).toMatchObject({ cat: 'a', usd: 5 });
  expect(q('ofd-log').textContent).toContain('best proof');
  await act(async () => root.unmount());
});
test('fallbacks show what each can afford today and lead to paying', async () => {
  const onPay = jest.fn(); const { q, root } = await mount(<FallbackFolder d={D} onPay={onPay} />);
  expect(q('ofd-plan-live').textContent).toContain('$60'); expect(q('ofd-plan-compound').textContent).toContain('$40'); expect(q('ofd-plan-keep').textContent).toContain('$25'); expect(q('ofd-plan-go-live')).toBeNull();
  await click(q('ofd-plan-go-keep')); expect(onPay).toHaveBeenCalled();
  await act(async () => root.unmount());
});
test('spots show real numbers, add a pool without moving money, and say it is not advice', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ pools: [{ pool: 'New1', name: 'A-B', venue: 'orca', feePct: 1, tvl: 500000, vol24: 90000, rate: 0.001 }, { pool: 'Addr1', name: 'SOL-USDC', venue: 'meteora', feePct: 0.1, tvl: 900000, vol24: 90000, rate: 0.002 }] }) }));
  const save = jest.fn(); const { el, q, root } = await mount(<SpotsFolder d={D} save={save} busy={false} />); await act(async () => {});
  expect(el.textContent).toContain('not advice'); expect(q('ofd-spot-New1').textContent).toContain('37%'); expect(q('ofd-spot-add-Addr1').disabled).toBe(true); expect(q('ofd-process').textContent).toContain('BY HAND');
  expect(q('ofd-band-nums-New1').textContent).toContain('CONCENTRATION'); await click(q('ofd-band-New1-5')); expect(q('ofd-band-nums-New1').textContent).toContain('IF PRICE MOVES 5%');
  await click(q('ofd-spot-add-New1')); expect(save.mock.calls[0][1].poolAdd).toMatchObject({ platform: 'orca', pair: 'A-B', address: 'New1' });
  await act(async () => root.unmount());
});
test('safety has the stop, warns past a stop, and lists what is not built', async () => {
  const { q, el, root } = await mount(<SafetyFolder d={D} save={jest.fn()} busy={false} c={D.cfg} setC={jest.fn()} />);
  expect(q('ofd-stops').textContent).toContain('SOL-USDC'); expect(q('ofd-missing').textContent).toContain('AutoRange'); expect(q('ofd-missing').textContent).toContain('lawyer'); expect(el.querySelector('[data-testid="ofd-stop-switch"]')).toBeTruthy();
  await act(async () => root.unmount());
});
test('a pool has its own folder, and its numbers save', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ pools: [] }) }));
  const save = jest.fn(); const { q, root } = await mount(<PoolDesk p={D.pools[0]} d={D} save={save} busy={false} />);
  await click(q('ofd-pool-on')); expect(save).toHaveBeenCalledWith(null, { poolSet: { id: 'p1', on: false } });
  await type(q('ofd-pool-sig'), 'sig1'); await click(q('ofd-pool-sig-go'));
  await act(async () => root.unmount());
});
test('the folders appear only when asked, and each listed pool adds one', async () => {
  let apps = null; const call = jest.fn(async () => D); const T = ({ on }) => { apps = useOwnerFolders(call, on); return null; };
  const { root } = await mount(<T on={false} />); expect(apps).toEqual([]); expect(call).not.toHaveBeenCalled();
  await act(async () => { root.render(<T on />); }); await act(async () => {});
  expect(apps.map(a => a.k)).toEqual(['own-pools', 'own-spots', 'own-pay', 'own-fallback', 'own-safety', 'own-py', 'own-pool-p1']);
  await act(async () => root.unmount());
});

test('the band maths', () => {
  expect(bandBoost(5)).toBeGreaterThan(bandBoost(40)); expect(bandBoost(40)).toBeGreaterThan(1);
  expect(moveLoss(0)).toBeCloseTo(0); expect(moveLoss(100)).toBeCloseTo(-0.0572, 3);
  expect(bandState(100, 90, 110)).toBe('in'); expect(bandState(91, 90, 110)).toBe('edge'); expect(bandState(120, 90, 110)).toBe('out'); expect(bandState(100, 0, 0)).toBeNull();
});
test('a pool folder reads its live price against its band', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ pools: [{ pool: 'Addr1', price: 150, tvl: 1, vol24: 1, fees24: 1 }] }) }));
  const { q, root } = await mount(<PoolDesk p={{ ...D.pools[0], bandLow: 100, bandHigh: 120 }} d={D} save={jest.fn()} busy={false} />); await act(async () => {});
  expect(q('ofd-range-state').textContent).toContain('OUT OF RANGE');
  await act(async () => root.unmount());
});

test('the py agents folder shows real records and a proposal changes nothing but the page', async () => {
  const seats = [{ k: 'tally', name: 'Tally', does: 'Numbers', checked: 4, passed: 3, lastNo: 'No real profit' }]; const call = jest.fn(async (u, o) => (o ? { seats, runs: [{ by: 'ossy', at: 1790000000, proposals: [{ seat: 'tally', risk: 'low', weak: 'Weak here', fix: 'Do this' }] }] } : { seats, runs: [] }));
  const { q, root } = await mount(<PyAgentsFolder call={call} />); await act(async () => {});
  expect(q('ofd-seat-tally').textContent).toContain('3 of 4 passed'); await click(q('ofd-py-ossy')); await act(async () => {});
  expect(JSON.parse(call.mock.calls.at(-1)[1].body)).toEqual({ who: 'ossy' }); expect(q('ofd-py-run').textContent).toContain('Do this');
  await act(async () => root.unmount());
});
