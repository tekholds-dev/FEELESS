// 🔘 HQ row buttons (Fuse builder, Quest engine) show ✓ only on the server's OK and say why otherwise; risky ones need a second tap.
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseBuilder } from './FuseBuilder';
import { QuestEngineAdmin } from './QuestEngineAdmin';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const tap = async b => { await act(async () => { b.click(); }); await act(async () => {}); };
const FUSE = { id: 'f1', name: 'Blue chips', emoji: '⚛️', enabled: true, featured: false, arena: false, creator: 'Abcd1234Wxyz', creatorBps: 1000, index: 100, tvlUsd: 5e6, legs: [], score: { grade: 'A' }, stats: { buys: 3, volumeUsd: 900, creatorEarnedUsd: 4, creatorOwedUsd: 0 } };

test('a Fuse row: Feature shows ✓ on the OK, a refusal shows its state, and Delete needs a second tap', async () => {
  let refuse = false; const posts = [];
  const call = jest.fn(async (path, opt) => { if (!opt) return { fuses: [FUSE] }; posts.push(JSON.parse(opt.body)); if (refuse) throw new Error('Not staff'); return { ok: true }; });
  const el = await mount(<FuseBuilder call={call} />);
  await tap(q(el, 'feature-f1')); expect(posts[0]).toMatchObject({ id: 'f1', featured: true }); expect(q(el, 'feature-f1').dataset.state).toBe('ok');
  refuse = true; await tap(q(el, 'arena-f1')); expect(q(el, 'arena-f1').dataset.state).toBe('fail');
  refuse = false; await tap(q(el, 'fuse-del-f1')); expect(posts.some(p => p.delete)).toBe(false); expect(q(el, 'fuse-del-f1').dataset.state).toBe('armed');
  await tap(q(el, 'fuse-del-f1')); expect(posts[posts.length - 1]).toEqual({ id: 'f1', delete: true });
});

test('a badge row turns on/off through its ActBtn, and awarding the week needs a second tap', async () => {
  const posts = [];
  const call = jest.fn(async (path, opt) => {
    if (!opt) return { badges: [{ id: 'b1', set: 'feeless', name: 'Sniper', tier: 'gold', enabled: true, tasks: [{ label: 'Win 3' }], perks: [] }], daily: [], weekly: [], season: { name: 'S1', paused: false, start: 1 }, stats: {} };
    posts.push([path, JSON.parse(opt.body)]);
    return path.endsWith('/season') ? { season: { name: 'S1', paused: false }, awarded: [] } : { badges: [{ id: 'b1', set: 'feeless', name: 'Sniper', tier: 'gold', enabled: false, tasks: [{ label: 'Win 3' }], perks: [] }] };
  });
  const el = await mount(<QuestEngineAdmin call={call} />);
  await tap(q(el, 'quest-onoff-b1')); expect(posts[0]).toEqual(['/admin/quests', { badges: { b1: { enabled: false } } }]);
  expect(q(el, 'quest-onoff-b1').textContent).toMatch(/Turn on|Saved/);
  await tap(q(el, 'quest-award')); expect(posts).toHaveLength(1);
  await tap(q(el, 'quest-award')); expect(posts[1]).toEqual(['/admin/quests/season', { awardWeek: true }]);
});
