import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PocDash, PocHome, pocNumbers } from './PocDash';
import { RecordFold } from './TrueRecord';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const $ = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const files = ['story', 'feed', 'wide'].flatMap(f => [{ piece: 'video', format: f, url: `/m/v${f}.mp4` }, { piece: 'image', format: f, url: `/m/i${f}.jpg` }, { piece: 'post', format: f, url: `/m/p${f}.txt` }]);
const clip = (n, extra = {}) => ({ id: `p${n}`, n, at: n, cost: 0.002, studio: { hook: `Hook ${n}`, files, goal: { type: 'reach', target: 1000 }, clip: { s: 7, e: 44, from: 'ohara', rank: 1 }, ...extra.studio }, ...extra.f });
const POSTED = clip(3, { f: { posted: { at: 100, svc: 'uploadpost', platforms: { tiktok: {}, youtube: {} } }, reach: { last: { label: '24 h', views: 4000, grade: { cpm: 0.5, verdict: 'on pace' } } } }, studio: { slot: 'Wed', maker: { usd: 0 } } });
const POCS = [clip(1, { studio: { slot: 'Mon' } }), clip(2), POSTED, { id: 'old', n: 0, topic: 'week plan', cost: 0.004 }];

test('pure: reach, cost per 1,000 views, what waits for approve and the week all come from its folders', () => {
  const n = pocNumbers(POCS, 2);
  expect(n.views).toBe(4000); expect(n.goal).toBe(1000); expect(n.cpm).toBeCloseTo(0.002 / 4000 * 1000, 8);
  expect(n.waiting.map(f => f.id)).toEqual(['p2', 'p1']); expect(n.posted.map(f => f.id)).toEqual(['p3']);
  expect(n.week.find(w => w.day === 'Mon').rows.map(f => f.id)).toEqual(['p1']); expect(n.week.find(w => w.day === 'Wed').today).toBe(true);
  expect(n.planned).toBe(2); expect(n.unplanned).toBe(1); expect(n.all.map(f => f.n)).toEqual([3, 2, 1, 0]);
  expect(pocNumbers([]).cpm).toBeNull();   // nobody has seen it yet: no number is made up
});

test('the dashboard: hero numbers, each tab opens its rows, a tap opens that PoC, the trend row puts the filing in the chat box', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ sources: [{ name: 'Bluesky', on: true, use: 'clips' }], clips: [{ url: 'https://bsky.app/profile/a/post/b', by: 'a.bsky.social', text: 'A wild clip', likes: 900 }], trends: { news: ['Topic one'] } }) }));
  try { localStorage.removeItem('feeless.pocDashTab'); } catch { /* jsdom */ }
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onOpen = jest.fn(); const onCommand = jest.fn();
  await act(async () => root.render(<PocDash pocs={POCS} onOpen={onOpen} onCommand={onCommand} />));
  expect($(el, 'pcd-views').textContent).toBe('4.0K'); expect($(el, 'pcd-cpm').textContent).toBe('$0.0005'); expect($(el, 'pcd-waiting').textContent).toBe('2');
  expect(String(global.fetch.mock.calls[0][0])).toContain('/api/cats/tools/content');
  await act(async () => { $(el, 'pcd-angle-0').click(); }); expect(onCommand.mock.calls[0][0]).toMatch(/file a poc on the angle behind this trending clip: "A wild clip"/);
  await act(async () => { $(el, 'pcd-kpi-approve').click(); }); expect(el.querySelectorAll('[data-testid^="pcd-approve-"]')).toHaveLength(2);
  await act(async () => { $(el, 'pcd-approve-p1').click(); }); expect(onOpen).toHaveBeenLastCalledWith(POCS[0]);
  await act(async () => { $(el, 'pcd-tab-posts').click(); }); expect($(el, 'pcd-post-p3').textContent).toMatch(/4\.0K/); expect($(el, 'pcd-post-p3').textContent).toMatch(/on pace/);
  await act(async () => { $(el, 'pcd-tab-week').click(); }); expect($(el, 'pcd-week').textContent).toMatch(/MonHook 1/);
  await act(async () => { $(el, 'pcd-tab-filed').click(); }); expect(el.querySelectorAll('[data-testid^="pdk-open-"]')).toHaveLength(4);
  expect(localStorage.getItem('feeless.pocDashTab')).toBe('filed');   // the tab he left it on comes back
  await act(async () => root.unmount()); el.remove();
});

test('the home keeps the live tools beside the dashboard; the record folds into one slim row that opens on tap', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ clips: [], trends: {} }) }));
  const f = { id: 'r1', n: 14, at: 9, test: { agent: 'Happy' }, proofChecks: [{ key: 'minds', label: 'Minds', ok: true, why: '' }, { key: 'moments', label: 'Both minds', ok: false, why: 'one mind' }], ran: [{ ok: true, asked: 'tencent/hy4', answered: ['tencent/hy4'], calls: 1 }], read: { sites: [] }, foot: { pct: 57 }, kits: ['a', 'b'] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<><RecordFold kind="poc" folders={[f]} /><PocHome pocs={[]} onOpen={() => {}} side={<p data-testid="side-tool">tool</p>} /></>));
  expect($(el, 'pcd-wrap').querySelector('aside [data-testid="side-tool"]')).not.toBeNull();
  const row = $(el, 'rfold-poc-row'); expect(row.textContent).toMatch(/1\/2checks/); expect(row.textContent).toMatch(/MOMENTS/); expect(row.textContent).toMatch(/hy4/); expect(row.textContent).toMatch(/57%/);
  expect($(el, 'trc-poc')).toBeNull();   // folded: no full-width bars until he taps
  await act(async () => { row.click(); }); expect($(el, 'trc-poc')).not.toBeNull(); expect(row.getAttribute('aria-expanded')).toBe('true');
  await act(async () => root.unmount()); el.remove();
});
