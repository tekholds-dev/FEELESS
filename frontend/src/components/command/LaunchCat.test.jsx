import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LaunchCat, BrainPanel, OrderBox, filterModels, planOf, orderWords } from './LaunchCat';

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
  expect(el.querySelector('.lct-grid [data-testid="lct-m-x/big"]')).toBeNull();          // 📈 a Trading cat opens on the trading models…
  click('.lct-cats button');                                                                // …✨ All shows the whole list
  click('.lct-grid [data-testid="lct-m-openai/gpt-oss-20b"]'); click('.lct-grid [data-testid="lct-m-x/big"]');
  click('[data-testid="lct-next"]'); click('[data-testid="lct-mode-battle"]'); click('[data-testid="lct-next"]');
  const set = (sel, v) => act(() => { const i = el.querySelector(sel); const proto = Object.getPrototypeOf(i); Object.getOwnPropertyDescriptor(proto, 'value').set.call(i, v); i.dispatchEvent(new Event('input', { bubbles: true })); });
  set('[data-testid="lct-name"]', 'Duo'); set('[data-testid="lct-prompt"]', 'germ floors only');
  click('[data-testid="lct-next"]');
  expect(el.textContent).toContain('Model calls are OFF');
  await act(async () => { el.querySelector('[data-testid="lct-launch"]').click(); });
  expect(el.querySelector('[data-testid="lct-next-real"]').textContent).toContain('💵 fund it once');   // the launch says what comes next: its own wallet → one signed funding → it trades inside the caps
  expect(posted[0]).toMatchObject({ brains: ['openai/gpt-oss-20b', 'x/big'], brainMode: 'battle', prompt: 'germ floors only', name: 'Duo', maxPositionSol: '0.5', maxDailyLossSol: '0.5', dailyBuyLimitSol: '2', brainKind: 'trading' });
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
  act(() => el.querySelector('.lct-cats button').click()); act(() => el.querySelector('.lct-grid .lct-tile-pick').click());   // no pre-picked models: open All, pick one
  act(() => el.querySelector('[data-testid="lct-next"]').click()); act(() => el.querySelector('[data-testid="lct-next"]').click());
  expect(el.querySelector('[data-testid="shared-handle"]')).not.toBeNull();
  expect(el.querySelector('[data-testid="lct-name"]')).toBeNull();
  expect(el.querySelector('[data-testid="lct-next"]').disabled).toBe(true);     // 'h1' fails the shared rule
  act(() => root.unmount());
});

test('🧠 the brain socket: YOUR built cat sits in it, each picked brain is a lit orb wired into its head, an empty socket waits', async () => {
  const { BrainSocket } = require('./LaunchCat');
  const { createRoot: cr } = require('react-dom/client'); const { act: a } = require('react');
  localStorage.setItem('feeless.myCat', JSON.stringify({ coat: 2, pattern: 'spots', look: { gear: 'halo' }, name: 'Specter' }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = cr(el);
  await a(async () => { root.render(<BrainSocket picked={[]} />); });
  expect(el.querySelectorAll('.lct-node.on')).toHaveLength(0); expect(el.querySelectorAll('.lct-wires .w.on')).toHaveLength(0);
  expect(el.querySelector('.g-halo')).not.toBeNull();                                     // your cat, wearing what you built
  await a(async () => { root.render(<BrainSocket picked={[{ id: 'a', name: 'OpenAI: GPT-5', tag: 'G4' }, { id: 'b', name: 'Qwen3 4B' }]} />); });
  expect([...el.querySelectorAll('.lct-node.on')].map(n => n.querySelector('.lct-orb b').textContent + n.querySelector(':scope > u').textContent)).toEqual(['OPA', 'QWB']);   // the maker's monogram + its A / B badge (never a name cut to 4 letters)
  expect(el.querySelectorAll('.lct-wires .w.on')).toHaveLength(2);
  a(() => root.unmount()); localStorage.removeItem('feeless.myCat');
});

test('🧭 a General cat takes orders in plain words: examples fill the box, each order shows what it understood and what happened', async () => {
  expect(orderWords({ side: 'buy', coin: 'JUP', sol: 0.05 })).toBe('BUY 0.05 SOL · $JUP'); expect(orderWords({ side: 'sell', coin: 'WIF', fraction: 0.5 })).toBe('SELL 50% · $WIF');
  const cat = { id: 'g1', mode: 'real', orders: [{ at: 1, text: 'buy 0.05 SOL of $JUP', order: { side: 'buy', coin: 'JUP', sol: 0.05 }, state: 'proposed', why: '✍ buy 0.05 SOL — waiting for your signature' },
    { at: 2, text: 'buy 1 SOL of $RUG', order: { side: 'buy', coin: 'RUG', sol: 1 }, state: 'refused', why: '💧 pool $3,000 — under the $5,000 floor' }] };
  const act_ = jest.fn(async () => true); const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<OrderBox cat={cat} act={act_} />); });
  const rows = el.querySelectorAll('.lct-order-log li');
  expect(rows[0].className).toBe('is-stop'); expect(rows[0].textContent).toContain('💧 pool $3,000'); expect(rows[1].className).toBe('is-prop');
  expect(el.textContent).toContain('a proposal your wallet signs');
  await act(async () => { el.querySelector('.lct-order-ex button').click(); });
  expect(el.querySelector('[data-testid="order-text"]').value).toBe('buy 0.05 SOL of $JUP');
  await act(async () => { el.querySelector('.lct-order-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(act_).toHaveBeenCalledWith('order', { text: 'buy 0.05 SOL of $JUP' });
  act(() => root.unmount());
});

test('🧭 the General wizard: real prices on every model + an ABOUT dropdown, its 3 job categories first, how the minds work (no trading modes), true signing words', async () => {
  const { signWord, mono } = require('./LaunchCat');
  const G = { ...CAT, models: [M('a/agent', { perTask: 0.0123, inUsd: 0.5, outUsd: 1.5, cats: ['agent'], desc: 'Drives tools over long tasks.' }), M('b/writer', { perTask: 0.002, cats: ['content'] })],
    rec: [], cats: [{ key: 'meta', label: '👁 Meta', why: '', n: 0 }, { key: 'agent', label: '🌐 Agent', why: '', n: 1, general: true }, { key: 'content', label: '✍ Content', why: '', n: 1, general: true }, { key: 'code', label: '💻 Code', why: '', n: 0, general: true }],
    personas: { general: [{ key: 'researcher', label: '🔎 Researcher', job: 'researcher', brief: 'Research any topic deeply and cite every source you use.' }] } };
  const posted = []; const api = jest.fn((u, o) => { if (o) { posted.push(JSON.parse(o.body)); return Promise.resolve({ cat: { id: 'g1' } }); } return Promise.resolve(G); });
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<LaunchCat api={api} ownerId={() => 'o'} kind="general" />); });
  const $ = s => el.querySelector(s); const click = s => act(() => $(s).click());
  expect([...el.querySelectorAll('.lct-cats button')].map(b => b.textContent.split(' ')[1])).toEqual(['All', 'Agent', 'Content', 'Code', 'Meta']);   // jobs lead
  const tile = $('[data-testid="lct-m-a/agent"]').closest('.lct-tile');
  expect(tile.textContent).toContain('IN · 1M'); expect(tile.textContent).toContain('$0.50'); expect(tile.textContent).toContain('$1.50'); expect(tile.textContent).toContain('TASK EST.$0.0123');
  expect(tile.querySelector('details.lct-desc').textContent).toContain('Drives tools over long tasks.');
  click('[data-testid="lct-m-a/agent"]'); click('[data-testid="lct-m-b/writer"]'); click('[data-testid="lct-next"]');
  expect($('[data-testid="lct-flow"]').children).toHaveLength(4); expect($('[data-testid="lct-mode-battle"]')).toBeNull();
  expect([...el.querySelectorAll('.lct-mind strong')].map(s => s.textContent)).toEqual(['a/agent', 'b/writer']); expect($('.lct-mind em').textContent).toContain('LEADS');
  expect($('.lct-foot').textContent).toContain('≈ $0.0072 a task');
  click('[data-testid="lct-next"]'); act(() => { const i = $('[data-testid="lct-name"]'); Object.getOwnPropertyDescriptor(Object.getPrototypeOf(i), 'value').set.call(i, 'Scout'); i.dispatchEvent(new Event('input', { bubbles: true })); });
  expect($('[data-testid="lct-gsetup"]').textContent).not.toMatch(/paper|daily loss|max position|sealed for life/i);   // FC10: no trader fields
  click('[data-testid="lct-job-researcher"]'); const brief = $('[data-testid="lct-prompt"]').value;
  expect(brief).toContain('cite every source'); expect(brief).toContain('HOW YOU TWO WORK'); expect(brief).toContain('RULES');   // generator: job + both minds + rules
  click('[data-testid="lct-cap-0.25"]');
  click('[data-testid="lct-next"]');
  expect($('[data-testid="lct-bill-profit"]')).toBeNull(); expect($('[data-testid="lct-next-real"]').textContent).toContain('it checks with you');
  expect(el.textContent).not.toMatch(/you sign every trade|your wallet signs every/i);
  await act(async () => { $('[data-testid="lct-launch"]').click(); });
  expect(posted[0]).toMatchObject({ brainKind: 'general', billing: 'payg', brainMode: 'turns', taskCap: 0.25, job: 'researcher' });
  expect(signWord({ agentWallet: { mode: 'auto' } })).toContain('no signing'); expect(signWord({ agentWallet: { mode: 'approve' } })).toContain('one tap'); expect(signWord({})).toContain('your wallet signs');
  expect(mono({ provider: 'nvidia' })).toBe('NV');
  act(() => root.unmount());
});


test('combined category and price range filters retain only matching models', () => {
  const models = [M('a', { cats: ['code', 'thinking'], perTask: .02 }), M('b', { cats: ['code'], perTask: .01 }), M('c', { cats: ['code','thinking'], perTask: .5 })];
  expect(filterModels(models, { cat: ['code','thinking'], min: .01, max: .1, kind: 'general' }).map(m => m.id)).toEqual(['a']);
  expect(planOf([M('a'), M('b'), M('c')], 'together', CAT.budget).calls).toBe(3);
});

test('🧭 a job picks the models fit for it: category, the tools / vision it needs, ranked', () => {
  const { JOBS } = require('./LaunchCat');
  const ms = [M('a/agent', { cats: ['agent'], tools: true, intel: 50 }), M('b/eye', { cats: ['agent'], tools: true, vision: true, intel: 40 }), M('c/plain', { cats: ['content'], intel: 70 })];
  const job = k => JOBS.find(j => j[0] === k)[2];
  expect(filterModels(ms, { cat: [job('research').cat], need: job('research').need }).map(m => m.id)).toEqual(['a/agent', 'b/eye']);
  expect(filterModels(ms, { need: job('trade').need }).map(m => m.id)).toEqual(['b/eye']);       // reading charts needs vision + tools
  expect(filterModels(ms, { cat: ['content'] }).map(m => m.id)).toEqual(['c/plain']);
});

test('🧠 step 1 starts with two EMPTY boxes (no pre-picked models) and a Next up top that wakes when one is picked', async () => {
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<LaunchCat api={jest.fn(() => Promise.resolve(CAT))} ownerId={() => 'o'} />); });
  expect(el.querySelector('[data-testid="lct-slot-0"]')).not.toBeNull(); expect(el.querySelector('[data-testid="lct-slot-1"]')).not.toBeNull();
  expect(el.textContent).not.toContain('FEELESS PICKS'); expect(el.querySelector('[data-testid="lct-next-top"]').disabled).toBe(true);
  act(() => el.querySelector('.lct-cats button').click()); act(() => el.querySelector('.lct-grid .lct-tile-pick').click());
  expect(el.querySelector('[data-testid="lct-slot-0"]')).toBeNull(); expect(el.querySelector('.lct-slots .lct-tile')).not.toBeNull();
  expect(el.querySelector('[data-testid="lct-next-top"]').disabled).toBe(false);
  act(() => root.unmount());
});

test('🪟 the model pop-out shows the FULL smart list and hands back the picked model', async () => {
  const { ModelPop } = require('./LaunchCat'); const got = []; const closed = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ModelPop d={CAT} title="👑 MODEL A · HER LEAD" onPick={id => got.push(id)} onClose={closed} />); });
  const pop = document.querySelector('[data-testid="model-pop"]'); expect(pop).not.toBeNull(); expect(pop.querySelector('[data-testid="lct-q"]')).not.toBeNull();
  act(() => pop.querySelector('.lct-cats button').click()); act(() => pop.querySelector('[data-testid="lct-m-x/big"]').click());
  expect(got).toEqual(['x/big']); expect(closed).toHaveBeenCalled();
  act(() => root.unmount()); el.remove();
});
