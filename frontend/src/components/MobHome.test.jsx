import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { PowerSkyline, SeasonHud, TheWire, nextMove, seasonClock } from './MobHome';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const rank = (name, tier) => ({ name, div: 'II', tier, pct: 40, next: 900 });
const BASE = { season: { name: '🎃 Haunted Trenches' }, rules: { turfMax: 12, fuseMinMp: 2000 }, cartels: [{}, {}],
  blocks: [{ id: 'fee-1', b: 'fee', i: 1 }, { id: 'harbor-2', b: 'harbor', i: 2, owner: 'fa', home: true }],
  ranked: [{ id: 'fa', tag: 'AAA', name: 'Alpha', power: 900, place: 1, rank: rank('Underboss', 4) }, { id: 'fb', tag: 'BBB', name: 'Bravo', power: 300, place: 2, rank: rank('Capo', 3) }],
  ffuse: { fights: [{ status: 'live' }] }, raids: [], log: [{ at: 2, what: '⚔ Family Fuse: [AAA] beat [BBB]' }, { at: 1, what: 'bought fee-3' }] };
const ME = { id: 'fa', tag: 'AAA', bank: 5000, pts: 120, turf: ['harbor-5'], rank: rank('Underboss', 4), place: 1, prices: { 'fee-1': 6000 }, hitters: [3], errands: [{ lvl: 1, ready: 40 }], metrics: { raidsWon: 4 }, boss: true };
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);

test('the next move follows the family: join → errand → turf → raid → fuse → build', () => {
  expect(nextMove(BASE).go).toBe('join');
  expect(nextMove({ ...BASE, me: { ...ME, errands: [{ lvl: 1, ready: 0 }] } }).k).toBe('earn');
  expect(nextMove({ ...BASE, me: { ...ME, bank: 7000 } }).k).toBe('turf');
  expect(nextMove({ ...BASE, me: ME }).k).toBe('raid');
  expect(nextMove({ ...BASE, me: { ...ME, hitters: [] } }).k).toBe('fuse');
  expect(nextMove({ ...BASE, me: { ...ME, hitters: [], bank: 10, boss: false } }).k).toBe('build');
  const c = seasonClock(Date.UTC(2026, 9, 21, 12)); expect(c.d).toBe(10); expect(c.pct).toBeGreaterThan(0.6);
});

test('the HUD: a ghost slot before you join, your rank + resources after; the wire lists the city', async () => {
  const join = jest.fn();
  const a = await mount(<SeasonHud v={BASE} onJoin={join} />);
  expect(q(a, 'season-hud').textContent).toContain('Your family goes here'); expect(q(a, 'season-hud').textContent).toContain('1/2');
  await act(async () => { q(a, 'hud-join').click(); }); expect(join).toHaveBeenCalled();
  const b = await mount(<SeasonHud v={{ ...BASE, me: ME }} onJoin={join} />);
  expect(q(b, 'season-hud').textContent).toContain('5,000 MP'); expect(q(b, 'rank-badge').textContent).toContain('Underboss');
  const w = await mount(<TheWire log={BASE.log} />); expect(q(w, 'the-wire').children).toHaveLength(2);
});

test('the HUD names the next move and goes there; the skyline flies to a family; empty spots are claimable', async () => {
  const go = jest.fn(); const pick = jest.fn(); const empty = jest.fn();
  const el = await mount(<SeasonHud v={{ ...BASE, me: ME }} onJoin={() => {}} go={go} />);
  expect(q(el, 'hud-next').textContent).toContain('hitter'); await act(async () => { q(el, 'hud-next').click(); }); expect(go).toHaveBeenLastCalledWith('raids');
  const s = await mount(<PowerSkyline v={BASE} onPick={pick} onEmpty={empty} />);
  expect(q(s, 'tower-AAA').style.getPropertyValue('--h')).toBe('1');
  await act(async () => { q(s, 'tower-BBB').click(); }); expect(pick).toHaveBeenCalledWith(expect.objectContaining({ id: 'fb' }));
  await act(async () => { q(s, 'tower-empty-0').click(); }); expect(empty).toHaveBeenCalled();
});
