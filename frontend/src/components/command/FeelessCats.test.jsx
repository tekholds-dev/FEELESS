import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CatBuilder, surprise, BACKDROPS } from './CatBuilder';
import { ALL_CHARACTERS } from '../../lib/wireface';
import { FeeCatShell, FC_NAV } from './FeeCatShell';
import { CAT_VARIATIONS, catByName } from './catCoats';
import { readMyCat } from '../../lib/myCat';
import { gateTiles, exitLadder } from './FeeCatBrainPage';
import { feeHeadline } from '../../lib/feeLeader';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
beforeEach(() => { localStorage.clear(); global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ cat: { balanceSol: 26, startingBalanceSol: 25, positions: [] }, discipline: { lives: 7, maxLives: 9 }, stats: { roiPct: 4, trades: 3 } }) })); });
afterEach(() => { document.body.innerHTML = ''; window.history.pushState({}, '', '/'); });
const mount = node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); act(() => root.render(node)); return { el, root, q: id => el.querySelector(`[data-testid="${id}"]`) }; };

test('🎨 the coats are 25 real ones (the 25 "… Spots" copies are gone) and an old saved name still resolves', () => {
  expect(CAT_VARIATIONS).toHaveLength(25); expect(new Set(CAT_VARIATIONS.map(c => c[1])).size).toBe(25);
  expect(catByName('Solaris')[0]).toBe('Solaris'); expect(catByName('Solaris Spots')).toEqual(['Solaris', '#ffbf69', '#d94e41', 'spots']); expect(catByName('???')).toBe(CAT_VARIATIONS[0]);
});

test('🎭 Build an agent: no animal bodies, every character is there, and it saves and goes on to a job', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CatBuilder />); });
  expect(el.querySelectorAll('.chr-tile')).toHaveLength(24); expect(el.textContent).not.toMatch(/Queen ant|Worker fly|Panther/);
  await act(async () => { el.querySelector('[data-testid="abx-rex"]').click(); });
  expect(el.querySelector('[data-testid="abx-rex"]').getAttribute('aria-pressed')).toBe('true');
  await act(async () => { const n = el.querySelector('[data-testid="abx-name"]'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(n, 'Specter'); n.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="abx-keep"]').click(); });
  expect(readMyCat()).toMatchObject({ face: 'rex', name: 'Specter' });
});

test('🎲 Surprise me picks a real character and backdrop', () => {
  const s = surprise(() => 0.5);
  expect(ALL_CHARACTERS.some(c => c[0] === s.face)).toBe(true); expect(BACKDROPS.some(b => b[0] === s.backdrop)).toBe(true);
});

test('🐱 the FeeCat shell: one nav for all five FeeCat pages (Create an agent ≠ Build a cat), Fee live in the bar, your built cat in the corner', async () => {
  localStorage.setItem('feeless.myCat', JSON.stringify({ coat: 0, pattern: 'patch', look: { gear: 'crown' }, name: 'Specter' }));
  const { el, root, q } = mount(<FeeCatShell tab="lore"><p>body</p></FeeCatShell>);
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(FC_NAV.map(n => n[0])).toEqual(['desk', 'lore', 'agents', 'build']);   // her brain lives inside Lore now (owner 2026-10-31)
  expect(q('fcx-lore').getAttribute('aria-current')).toBe('page'); expect(q('fcx-agents').textContent).toContain('create a cat that trades'); expect(q('fcx-build').textContent).toContain('BUILD AN AGENT');
  expect(q('fcx-mine').textContent).toContain('SPECTER'); expect(q('fcx-mine').querySelector('.g-crown')).not.toBeNull();
  expect(el.querySelectorAll('.fcx-lives i.on')).toHaveLength(7); expect(el.textContent).toContain('+4.0%');
  act(() => q('fcx-lore').click()); expect(window.location.pathname + window.location.search).toBe('/terminal/feecat?view=lore');
  act(() => q('fcx-focus').click()); expect(document.body.classList.contains('fcx-focus')).toBe(true); expect(localStorage.getItem('feeless.fcx.focus')).toBe('1');   // ⤒ hide the top bars
  act(() => q('fcx-focus').click()); expect(document.body.classList.contains('fcx-focus')).toBe(false);
  act(() => q('fcx-focus').click()); act(() => root.unmount()); expect(document.body.classList.contains('fcx-focus')).toBe(false);   // leaving FeeCat brings the site bars back
  localStorage.removeItem('feeless.fcx.focus');
});

test('🧠 her brain: the entry gate shows what her auto-strength tightened; the exit ladder is ordered stop → entry → takes', () => {
  const rules = { minLiquidity: 10000, minVolume24h: 20000, minMarketCap: 20000, maxMarketCap: 1e7, h1Min: 3, h1Max: 40, minBuySellRatio: 1.2, maxM5Chase: 4, maxTop10Pct: 25, maxSnipers: 6, maxBundled: 6,
    hardStop: -25, protectAt: 20, takeProfit1: 30, takeProfit1Sell: 0.4, takeProfit2: 75, takeProfit2Sell: 0.4, add1At: -15, add1Fraction: 0 };
  const t = gateTiles(rules, { minLiquidity: { now: 40000, default: 10000 }, maxSnipers: { now: 6, default: 6 } });
  const liq = t.find(x => x[0] === 'minLiquidity'); expect(liq[2]).toBe('$40K'); expect(liq[5]).toMatchObject({ now: 40000, default: 10000 });
  expect(t.find(x => x[0] === 'maxSnipers')[5]).toBeNull(); expect(t.find(x => x[0] === 'mc')[2]).toBe('$20K – $10M');
  const lad = exitLadder(rules); expect(lad.marks.map(m => m.l)).toEqual(['HARD STOP', 'ENTRY', 'PROTECT', 'TAKE 40%', 'TAKE 40%']);   // a 0-size add is not drawn
  expect(lad.marks.every((m, i, a) => !i || m.at > a[i - 1].at)).toBe(true);
  expect(feeHeadline({ cat: { balanceSol: 20, startingBalanceSol: 25, positions: [{}] }, discipline: { lives: 0, pause: true }, stats: { roiPct: -20 } })).toMatchObject({ bal: 20, open: 1, lives: 0, nap: true, roi: -20 });
});
