import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AgentDemo, walk, DEMO_FEED } from './AgentDemo';
import { AgentCritter, cleanAgent, MOVES } from './Critters';
import { LaunchCat, ApiDrawer, VenuePick } from './LaunchCat';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); const root = createRoot(el); await act(async () => { root.render(node); }); return el; };
const click = (el, sel) => act(() => el.querySelector(sel).click());

test('the demo walk is seeded and valid candles', () => {
  const a = walk(3, 30); expect(walk(3, 30)).toEqual(a); expect(a).toHaveLength(30);
  a.forEach(b => { expect(b.h).toBeGreaterThanOrEqual(Math.max(b.o, b.c)); expect(b.l).toBeLessThanOrEqual(Math.min(b.o, b.c)); });
});

test('🛸 trader demo = two drawn chart windows; general = two browsers; both say DEMO', async () => {
  const t = await mount(<AgentDemo kind="trading" models={[{ name: 'x: Ossy' }]} />);
  expect(t.querySelectorAll('.agd-win')).toHaveLength(2); expect(t.querySelectorAll('svg.agd-chart')).toHaveLength(2);
  expect(t.textContent).toContain('DEMO'); expect(t.textContent).toContain('Ossy'); expect(t.querySelector('.agd-feed li').textContent).toBe(DEMO_FEED.trading[0]);
  const g = await mount(<AgentDemo kind="general" />);
  expect(g.querySelectorAll('.agd-browser')).toHaveLength(2); expect(g.querySelector('.agd-chart')).toBeNull();
});

test('🧭 the demo sits in How they work (step 2), not on the model list', async () => {
  const CAT = { models: [{ id: 'a/b', name: 'a/b', provider: 'a', ctx: 1, perDecision: 0.001, perTask: 0.01, cats: ['trading'], intel: 1, created: 1 }], cats: [], modes: [], billing: [{ key: 'profit', label: 'p' }], budget: { start: 10, liveAsks: 3 } };
  const el = await mount(<LaunchCat api={() => Promise.resolve(CAT)} ownerId={() => 'o'} />);
  await act(async () => {});
  expect(el.querySelector('[data-testid="agent-demo"]')).toBeNull();
  click(el, '[data-testid="lct-m-a/b"]'); click(el, '[data-testid="lct-next"]');
  expect(el.querySelector('[data-testid="agent-demo"]')).not.toBeNull();
  expect(el.querySelector('[data-testid="venue-pick"]')).not.toBeNull();       // 📈 FEELESS rails only
});

test('📈 venues keep at least one FEELESS rail; 🔐 the drawer shows last 4 only', async () => {
  const onChange = jest.fn(); const v = await mount(<VenuePick value={['trench']} onChange={onChange} />);
  click(v, '[data-testid="venue-trench"]'); expect(onChange).toHaveBeenLastCalledWith(['trench']);
  click(v, '[data-testid="venue-perps"]'); expect(onChange).toHaveBeenLastCalledWith(['trench', 'perps']);
  const onDrop = jest.fn(); const d = await mount(<ApiDrawer rows={[{ provider: 'openrouter', saved: true, last4: 'abcd' }]} draft={{}} onDrop={onDrop} onSave={jest.fn()} />);
  expect(d.textContent).toContain('••••abcd'); click(d, '[data-testid="akd-drop-openrouter"]'); expect(onDrop).toHaveBeenCalledWith('openrouter');
  expect(d.querySelector('[data-testid="akd-birdeye"]').type).toBe('password');
});

test('🐜 the bodies: queen (wings + crown), fly (compound eyes), two worker ants; unknown keys fall back', async () => {
  expect(cleanAgent({ species: 'dragon', ant: 'x', wing: 'nope' })).toEqual({ species: 'cat', ant: 'fire', fly: 'house', wing: 'clear', flutter: 'buzz' });
  const q = await mount(<AgentCritter agent={{ species: 'queen', wing: 'gold' }} gesture="flutter" />);
  expect(q.querySelectorAll('.crt-wing')).toHaveLength(4); expect(q.querySelector('.crt-crown')).not.toBeNull(); expect(q.querySelector('.do-flutter')).not.toBeNull();
  expect(q.querySelectorAll('.crt-leg')).toHaveLength(6);
  const f = await mount(<AgentCritter agent={{ species: 'fly' }} />); expect(f.querySelectorAll('.crt-wing')).toHaveLength(2);
  const a = await mount(<AgentCritter agent={{ species: 'ants' }} gesture="carry" />); expect(a.querySelectorAll('svg')).toHaveLength(2); expect(a.querySelector('.crt-coin')).not.toBeNull();
  expect(MOVES.fly).toContain('groom');
});

test('🛸 live view: each brain thinks its own latest calls; held coins chart first, then what it just sold', async () => {
  const { catMinds, catCoins, AgentLive, asModel } = require('./AgentLive');
  const cat = { brainsCfg: { brains: ['a/ossy', 'b/g4'], decisions: [{ word: 'BUY', sym: 'GERM', by: 'ossy', why: 'germ floor' }, { word: 'SKIP', sym: 'RUG', by: 'g4' }] },
    positions: [{ pairAddress: 'P1', symbol: 'GERM', currentChange: 12 }], exits: [{ pairAddress: 'P0', symbol: 'OLD' }, { pairAddress: 'P1', symbol: 'GERM' }] };
  const x = catMinds(cat); expect(x.thoughts).toEqual([['BUY $GERM'], ['SKIP $RUG']]); expect(x.feed[0]).toContain('BUY $GERM');
  expect(catCoins(cat).map(c => [c.symbol, c.open])).toEqual([['GERM', true], ['OLD', false]]);
  const el = await mount(<AgentLive minds={[{ model: asModel('a/ossy'), thoughts: ['BUY $GERM'], live: true, label: 'ossy' }]} coins={[]} feed={['🔎 hunting']} />);
  expect(el.querySelectorAll('.agd-win')).toHaveLength(2); expect(el.textContent).toContain('PREVIEW'); expect(el.querySelectorAll('.lct-orb')).toHaveLength(2);
  expect(el.querySelector('.lct-orb.is-idle')).not.toBeNull();   // the empty second mind is still
});
