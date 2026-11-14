import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import WeekBoard, { movePost } from './WeekBoard';

const week = { idea: 'Teaser to reveal', style: 'launch', posts: [{ day: 'Mon', platform: 'x', time: '09:00', caption: 'Something is coming' }, { day: 'Wed', platform: 'instagram', time: '18:00', caption: 'Reveal' }] };
const pocs = [{ id: 'p1', n: 4, week }, { id: 'p2', n: 5, week: { ...week, style: 'hype', idea: 'Peak Friday' } }];
const q = id => document.querySelector(`[data-testid="${id}"]`);
const mount = async el => { const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box); await act(async () => root.render(el)); return { box, root }; };
const fire = async (el, type) => act(async () => { el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true })); });
const type = async (el, v) => act(async () => { Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); });

test('a post moves to another day and platform, sorted by day', () => {
  expect(movePost(week.posts, 0, 'Thu', 'tiktok').map(p => `${p.day}/${p.platform}`)).toEqual(['Wed/instagram', 'Thu/tiktok']);
});

test('the board shows each scenario, and a dragged + edited week saves as the owner’s version', async () => {
  const work = jest.fn(async () => ({ pocFolders: pocs }));
  const { box, root } = await mount(<WeekBoard cat={{ id: 'c1' }} work={work} wsId="w1" pocs={pocs} media={[]} />);
  expect(box.textContent).toContain('Teaser to reveal');
  await act(async () => q('week-tab-p2').click()); expect(box.textContent).toContain('Peak Friday');
  await act(async () => q('week-tab-p1').click());
  await fire(q('week-post-0'), 'dragstart'); await fire(q('week-cell-x-Fri'), 'drop');
  await act(async () => q('week-post-1').click());
  await type(q('week-caption'), 'Friday now');
  await act(async () => q('week-save').click());
  expect(work).toHaveBeenCalledWith('c1', { op: 'week_save', job: 'p1', cap: { idea: 'Teaser to reveal', posts: [{ day: 'Wed', platform: 'instagram', time: '18:00', caption: 'Reveal' }, { day: 'Fri', platform: 'x', time: '09:00', caption: 'Friday now' }] } });
  act(() => root.unmount());
});

test('its minds are asked for three weeks', async () => {
  const work = jest.fn(async () => ({ ok: true }));
  const { root } = await mount(<WeekBoard cat={{ id: 'c1' }} work={work} wsId="w1" pocs={[]} media={[]} />);
  expect(q('week-none')).toBeTruthy();
  await type(q('week-topic'), 'shoe drop');
  await act(async () => q('week-make').click());
  expect(work).toHaveBeenCalledWith('c1', { op: 'week_plans', job: 'w1', text: 'shoe drop' });
  act(() => root.unmount());
});
