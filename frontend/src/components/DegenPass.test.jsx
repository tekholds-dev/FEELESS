import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(node); }); return { el, root }; };

test('goal bar: steps above the card value, the put-in last, progress = value ÷ goal; a picked goal is remembered', async () => {
  const { goalSteps, goalPct, GoalBar } = require('./ArenaPrime');
  expect(goalSteps(2.25, 22.5)[0]).toBe(2.4);   // the owner's "get back to 2.4"
  expect(goalSteps(2.25, 22.5)).toContain(22.5);
  expect(goalSteps(30, 22.5)).not.toContain(22.5);   // already above the put-in: not a goal
  expect(goalPct(2.25, 2.4)).toBeCloseTo(93.75);
  expect(goalPct(3, 2.4)).toBe(100);
  localStorage.removeItem('feeless.cardGoal');
  const { el, root } = await mount(<GoalBar value={2.25} putIn={22.5} />);
  expect(el.querySelector('[data-testid="goal-bar"]').textContent).toContain('$0.15 to go');
  expect(el.textContent).toContain('10% back');
  const sel = el.querySelector('[data-testid="goal-pick"]');
  await act(async () => { sel.value = '22.5'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(localStorage.getItem('feeless.cardGoal')).toBe('22.5');
  await act(async () => { root.unmount(); });
});

test('social icons are real SVGs; a link opens it, set-at-launch opens the Pump page dimmed, none = 🚫', async () => {
  const { SocialIcons } = require('./QuickPulse');
  const { el, root } = await mount(<><SocialIcons r={{ mint: 'Abcpump', site: 'https://a.io', x: true }} /><SocialIcons r={{ mint: 'Z' }} /></>);
  const site = el.querySelector('[data-testid="soc-site"]'); const x = el.querySelector('[data-testid="soc-x"]');
  expect(site.getAttribute('href')).toBe('https://a.io'); expect(site.querySelector('svg')).not.toBeNull();
  expect(x.getAttribute('href')).toBe('https://pump.fun/coin/Abcpump'); expect(x.className).toContain('is-dim');
  expect(el.textContent).toContain('🚫');
  await act(async () => { root.unmount(); });
});

test('socials first keeps links, then set-at-launch, then none (order kept inside each)', () => {
  const { socFirst } = require('./TrenchOpen');
  expect(socFirst([{ s: 'a' }, { s: 'b', x: true }, { s: 'c', tg: 'https://t.me/c' }, { s: 'd' }]).map(r => r.s)).toEqual(['c', 'b', 'a', 'd']);
});

test('a call that loses on its own record is BUSTED (≥ 30 settled, typical hour ≤ −20%)', () => {
  const { busted } = require('./CoinVital');
  expect(busted({ n: 60, medPct: -83.4 })).toBe(true);    // BOND RUN, 2026-10-08
  expect(busted({ n: 60, medPct: -1.9 })).toBe(false);    // SEND IT: losing a little, not busted
  expect(busted({ n: 12, medPct: -83 })).toBe(false);     // too few to call it
});

test('⋯ tray: tiles for profit / sell / swap, and freeze is one tap ON the row', async () => {
  const { RowMore } = require('./ArenaPrime');
  const hit = jest.fn();
  const { el, root } = await mount(<RowMore label="More for $A" testid="more-A"><button type="button" data-testid="tile" onClick={hit}>t</button></RowMore>);
  expect(document.querySelector('[data-testid="tile"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="more-A"]').click(); });
  await act(async () => { document.querySelector('[data-testid="tile"]').click(); });
  expect(hit).toHaveBeenCalled();
  await act(async () => { root.unmount(); });
  const src = require('fs').readFileSync(require('path').join(__dirname, 'ArenaPrime.jsx'), 'utf8');
  const fz = src.indexOf('data-testid={`freeze-${l.symbol}`}'); const more = src.indexOf('<RowMore label={`More for $${l.symbol}`}');
  expect(fz).toBeGreaterThan(0); expect(fz).toBeLessThan(more);   // the freeze button sits on the row, before the ⋯ menu
  for (const id of ['skim-${l.symbol}-card', 'skim-${l.symbol}-park', 'skim-${l.symbol}-cash', 'skim-${l.symbol}-stake', 'swap-${l.symbol}']) expect(src).toContain(id);
});
