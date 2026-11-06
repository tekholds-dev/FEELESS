import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { FallbackFolder, PayFolder, PoolDesk, PyAgentsFolder, FolderTabs, GrowFolder, SafetyFolder, groupApps, curveOf, payOf, bandBoost, bandState, moveLoss, useOwnerFolders } from './OwnerFolders';

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
test('the money folder compares real options, shows what they did after price moves, and adds to the plan without moving money', async () => {
  const row = { pool: 'New1', name: 'A-B', venue: 'orca', feePct: 1, tvl: 500000, vol24: 90000, rate: 0.001, price: 1, step: 4, readOnly: true };
  const rows = [{ id: 'New1', kind: 'pool', name: 'A-B', venue: 'orca', tvl: 500000, yearPct: 36.5, per1k24: 1, risk: 'half', readOnly: true, pool: row }, { id: 'llama:u', kind: 'lend', name: 'USDC on kamino', venue: 'kamino-lend', tvl: 9e6, yearPct: 6, per1k24: 0.16, risk: 'none', llama: 'u' }, { id: 'stock:s', kind: 'stock', name: 'SPYx', venue: 'raydium', tvl: 2e6, yearPct: 0, per1k24: 0, risk: 'coin', pair: 's' }];
  const pts = n => Array.from({ length: n }, (_, i) => ({ t: 1000 + i * 3600, a: 1 - i * 0.001, b: 1, fee: 0.0005 }));
  const call = jest.fn(async u => (u === '/admin/grow' ? { rows } : { id: 'x', points: pts(30), single: u.includes('llama') || u.includes('stock'), why: '' }));
  const save = jest.fn(); const { el, q, root } = await mount(<GrowFolder d={D} save={save} busy={false} call={call} />); await act(async () => {}); await act(async () => {});
  expect(el.textContent).toContain('not advice'); expect(q('grow-result-New1').textContent).toContain('EARNED'); expect(q('grow-result-llama:u')).not.toBeNull(); expect(q('grow-result-stock:s').textContent).toContain('NET');
  expect(q('grow-row-stock:s').textContent).toContain('MOVES WITH THE COIN'); expect(q('grow-row-New1').textContent).toContain('read only');
  await click(q('grow-tick-stock:s')); expect(q('grow-result-stock:s')).toBeNull();
  await click(q('grow-add-llama:u')); expect(save.mock.calls[0][1].poolAdd).toMatchObject({ platform: 'other', pair: 'USDC on kamino' });
  await click(q('grow-band-New1')); expect(q('ofd-band-nums-New1').textContent).toContain('CONCENTRATION'); await click(q('ofd-spot-add-New1')); expect(save.mock.calls[1][1].poolAdd).toMatchObject({ platform: 'orca', pair: 'A-B', address: 'New1' });
  await act(async () => root.unmount());
});
test('the same maths for every option: a pool feels price moves by the square root, a single coin in full, and only earnings ever pay', () => {
  const pts = [{ t: 0, a: 100, b: 1, fee: 0 }, { t: 3600, a: 81, b: 1, fee: 0.01 }];
  const lp = curveOf({ points: pts, single: false }, 24, 1000); expect(lp.moved).toBeCloseTo(-100); expect(lp.earned).toBeCloseTo(10); expect(lp.net).toBeCloseTo(-90);
  const one = curveOf({ points: pts, single: true }, 24, 1000); expect(one.moved).toBeCloseTo(-190);
  expect(curveOf({ points: [pts[0]] }, 24, 1000)).toBeNull(); expect(payOf(0, 24, 10, 20)).toBeNull();
  const pay = payOf(10, 24, 10, 20); expect(pay.month).toBeCloseTo(300); expect(pay.piece).toBeCloseTo(60); expect(pay.agents).toBeCloseTo(30); expect(pay.back).toBeCloseTo(210);
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
  expect(apps.map(a => a.k)).toEqual(['own-grow', 'own-safety', 'own-py']);
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
  expect(q('ofd-seat-tally').textContent).toContain('3 of 4 real sends passed'); await click(q('ofd-py-ossy')); await act(async () => {});
  expect(JSON.parse(call.mock.calls.at(-1)[1].body)).toEqual({ who: 'ossy' }); expect(q('ofd-py-run').textContent).toContain('Do this');
  await act(async () => root.unmount());
});

test('the agents desktop is four folders by job, every old folder a tab, and only the open tab runs', async () => {
  const app = k => ({ k, ic: 'x', label: k, body: <p data-testid={`body-${k}`}>{k}</p> });
  const out = groupApps(['colony', 'collective', 'pow', 'prompts', 'stash', 'ready', 'slots'].map(app), ['own-grow', 'own-safety', 'own-py', 'own-pool-x'].map(app));
  expect(out.map(a => a.k)).toEqual(['own-grow', 'own-collective', 'own-proofs', 'own-setup', 'own-pool-x']);
  const { q, root } = await mount(out[2].body);
  expect(q('body-pow')).not.toBeNull(); expect(q('body-stash')).toBeNull(); await click(q('ftab-own-proofs-own-py')); expect(q('body-own-py')).not.toBeNull(); expect(q('body-pow')).toBeNull();
  await act(async () => root.unmount());
  expect(groupApps([app('pow')], []).map(a => a.k)).toEqual(['own-proofs']);   // before the owner's folders load, what is there still shows
});
