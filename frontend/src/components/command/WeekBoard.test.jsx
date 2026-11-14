import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import WeekBoard, { movePost, nextMonday } from './WeekBoard';

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

test('the week always goes into the coming Monday', () => {
  expect(nextMonday(new Date(2026, 10, 13))).toBe('2026-11-16');   // Friday
  expect(nextMonday(new Date(2026, 10, 16))).toBe('2026-11-23');   // a Monday → the next one
  expect(nextMonday(new Date(2026, 10, 15))).toBe('2026-11-16');   // Sunday
});

test('the saved week goes to Postiz on the owner’s click, and what happened shows on the board', async () => {
  const sent = [{ ...pocs[0], posted: { sent: 1, mode: 'schedule', start: '2030-01-07', results: [{ i: 0, platform: 'x', postId: 'p9' }, { i: 1, platform: 'instagram', error: 'Postiz said 400' }], skipped: [] } }, pocs[1]];
  const work = jest.fn(async (_id, b) => (b.op === 'postiz_channels' ? { channels: [{ id: 'i1', name: 'FEELESS on X', platform: 'x' }] } : { pocFolders: sent }));
  let rows = pocs; const onPocs = jest.fn(r => { rows = r; });
  const { box, root } = await mount(<WeekBoard cat={{ id: 'c1' }} work={work} wsId="w1" pocs={rows} media={[]} onPocs={onPocs} />);
  await act(async () => q('week-chans').click());
  expect(q('week-chan-list').textContent).toContain('FEELESS on X');
  await type(q('week-monday'), '2030-01-07');
  await act(async () => q('week-schedule').click());
  const call = work.mock.calls.find(c => c[1].op === 'week_post')[1];
  expect(call).toMatchObject({ op: 'week_post', job: 'p1', tools: { start: '2030-01-07', mode: 'schedule', again: false } });
  expect(typeof call.tools.tz).toBe('number');
  await act(async () => root.render(<WeekBoard cat={{ id: 'c1' }} work={work} wsId="w1" pocs={rows} media={[]} onPocs={onPocs} />));
  expect(q('week-posted').textContent).toContain('scheduled in Postiz');
  expect(q('week-posted').textContent).toContain('Postiz said 400');
  expect(box.textContent).toContain('Schedule again');
  act(() => root.unmount());
});
