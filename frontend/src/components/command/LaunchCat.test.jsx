import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LaunchCat, BrainPanel, filterModels, planOf } from './LaunchCat';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const M = (id, o = {}) => ({ id, name: id, provider: id.split('/')[0], ctx: 131072, inUsd: 0.02, outUsd: 0.09, perDecision: 0.0001, cats: ['degen'], intel: 40, created: 1, desc: '', ...o });
const CAT = { models: [M('openai/gpt-oss-20b', { tag: 'OSSY' }), M('x/big', { perDecision: 0.01, cats: ['meta'], intel: 60, created: 5 })], rec: [M('openai/gpt-oss-20b', { tag: 'OSSY', why: 'ours' })],
  cats: [{ key: 'meta', label: '👁 Meta', why: 'pictures', n: 1 }], modes: [{ key: 'turns', label: '🔁 Take turns', why: '' }, { key: 'battle', label: '⚔ Battle', why: '' }],
  billing: [{ key: 'profit', label: 'profit pays' }, { key: 'payg', label: 'payg' }], budget: { start: 10, liveAsks: 3, alertPct: 10 }, live: false };

test('filter + sort and the plan math match the server', () => {
  expect(filterModels(CAT.models, { cat: 'meta' }).map(m => m.id)).toEqual(['x/big']);
  expect(filterModels(CAT.models, { sort: 'cheap' })[0].id).toBe('openai/gpt-oss-20b');
  const p = planOf([CAT.models[0], CAT.models[1]], 'together', CAT.budget);
  expect(p.calls).toBe(2); expect(p.perTrade).toBeCloseTo(((0.0001 + 0.01) / 2) * 2 * 4); expect(p.trades).toBe(Math.floor(10 / p.perTrade));
});

test('pick two brains, choose battle, write the brief, launch', async () => {
  const posted = [];
  const api = jest.fn((u, o) => { if (o) { posted.push(JSON.parse(o.body)); return Promise.resolve({ cat: { id: 'c1' } }); } return Promise.resolve(CAT); });
  const onCreated = jest.fn(); const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<LaunchCat api={api} ownerId={() => 'o'} onCreated={onCreated} />); });
  const click = sel => act(() => el.querySelector(sel).click());
  click('.lct-rec [data-testid="lct-m-openai/gpt-oss-20b"]'); click('.lct-grid [data-testid="lct-m-x/big"]');
  click('[data-testid="lct-next"]'); click('[data-testid="lct-mode-battle"]'); click('[data-testid="lct-next"]');
  const set = (sel, v) => act(() => { const i = el.querySelector(sel); const proto = Object.getPrototypeOf(i); Object.getOwnPropertyDescriptor(proto, 'value').set.call(i, v); i.dispatchEvent(new Event('input', { bubbles: true })); });
  set('[data-testid="lct-name"]', 'Duo'); set('[data-testid="lct-prompt"]', 'germ floors only');
  click('[data-testid="lct-next"]');
  expect(el.textContent).toContain('Model calls are OFF');
  await act(async () => { el.querySelector('[data-testid="lct-launch"]').click(); });
  expect(posted[0]).toMatchObject({ brains: ['openai/gpt-oss-20b', 'x/big'], brainMode: 'battle', prompt: 'germ floors only', name: 'Duo', maxPositionSol: '0.5', maxDailyLossSol: '0.5', dailyBuyLimitSol: '2' });
  expect(posted[1]).toEqual({ action: 'start' });                          // starts trading at once, like Create a Cat
  expect(onCreated).toHaveBeenCalled();
  act(() => root.unmount());
});

test('the brain panel shows credit and decisions and sends a chime', async () => {
  const cat = { id: 'c1', status: 'running', brainsCfg: { brains: ['openai/gpt-oss-20b'], brainMode: 'turns', credit: 7.5, asks: 4, spent: 2.5, owed: 0, billing: 'profit', prompt: 'p',
    decisions: [{ at: 1, word: 'BUY', sym: 'AAA', by: 'gpt-oss-20b', why: 'germ floor' }], chime: [] } };
  const api = jest.fn((u, o) => Promise.resolve({ cat: { ...cat, brainsCfg: { ...cat.brainsCfg, chime: o ? [{ text: 'hi' }] : [] } } }));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<BrainPanel cat={cat} api={api} onChanged={() => {}} />); });
  expect(el.textContent).toContain('$7.50'); expect(el.textContent).toContain('germ floor');
  await act(async () => { const i = el.querySelector('[data-testid="brain-chime"]'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(i, 'watch the dev'); i.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('.lct-chime').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(api).toHaveBeenCalledWith('/api/cats/c1/action', expect.objectContaining({ method: 'POST' }));
  act(() => root.unmount());
});

test('Launch a Cat asks the SAME identity + look + risk fields as Create a Cat when they are handed in', async () => {
  const api = jest.fn(() => Promise.resolve(CAT));
  const Fields = ({ form, update }) => <input data-testid="shared-handle" value={form.handle} onChange={e => update('handle', e.target.value)} />;
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<LaunchCat api={api} ownerId={() => 'o'} Fields={Fields} newForm={() => ({ name: 'x', handle: 'h1' })} formOk={f => f.handle.length > 2} />); });
  act(() => el.querySelector('.lct-rec [data-testid="lct-m-openai/gpt-oss-20b"]').click());
  act(() => el.querySelector('[data-testid="lct-next"]').click()); act(() => el.querySelector('[data-testid="lct-next"]').click());
  expect(el.querySelector('[data-testid="shared-handle"]')).not.toBeNull();
  expect(el.querySelector('[data-testid="lct-name"]')).toBeNull();
  expect(el.querySelector('[data-testid="lct-next"]').disabled).toBe(true);     // 'h1' fails the shared rule
  act(() => root.unmount());
});
