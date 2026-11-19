import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import PocStudio, { approveBody, defaultPicks, fileOf, fmt } from './PocStudio';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const $ = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const FILES = ['image', 'video', 'post', 'thread'].flatMap(pc => ['story', 'feed', 'wide'].map(fm => ({ piece: pc, format: fm, url: `/api/cats/media/c/m${pc}${fm}.${pc === 'video' ? 'mp4' : 'jpg'}`, ...(pc === 'post' ? { text: `${fm} post` } : {}), ...(pc === 'thread' ? { text: '1/3 a', cards: ['/c1.jpg', '/c2.jpg', '/c3.jpg'], parts: 3 } : {}) })));
const F = { id: 'poc9', n: 9, cost: 0, studio: { trend: { text: 'Biggest wave ever surfed', source: 'YouTube', signal: 2000000, unit: 'views', url: 'https://youtube.com/x' }, trends: [{}, {}], hook: 'The wave nobody priced', angle: 'film it',
  goal: { type: 'reach', target: 5000, by: 'minds', why: 'a slice' }, files: FILES, maker: { usd: 0 } } };
const SVCS = [{ id: 'uploadpost', name: 'Upload-Post', saved: true, platforms: ['x', 'tiktok', 'youtube', 'instagram', 'bluesky', 'threads', 'linkedin'], thread: true, site: 'https://upload-post.com', how: 'x' },
  { id: 'zernio', name: 'Zernio', saved: false, platforms: ['x', 'tiktok'], thread: false, site: 'https://zernio.com', how: 'y' }, { id: 'ayrshare', name: 'Ayrshare', saved: false, platforms: ['x'], thread: true, site: 'https://ayrshare.com', how: 'z' }];

function mount(f, work) {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onFolders = jest.fn();
  return { el, root, onFolders, render: async ff => act(async () => root.render(<PocStudio cat={{ id: 'c' }} f={ff} work={work} onFolders={onFolders} />)) };
}

test('pure: files by piece and format, the approve body sends only what he switched on, numbers read short', () => {
  expect(fileOf(FILES, 'video', 'wide').url).toContain('mvideowide'); expect(fileOf([{ piece: 'image', format: 'feed', error: 'x' }], 'image', 'feed')).toBeNull();
  const picks = { ...defaultPicks(), tiktok: { on: true, piece: 'video' }, x: { on: true, piece: 'thread' } };
  expect(approveBody('uploadpost', picks, false)).toEqual({ svc: 'uploadpost', platforms: { tiktok: 'video', x: 'thread' } });
  expect(approveBody('ayrshare', picks, true).realPost).toBe(true);
  expect([fmt(950), fmt(1500), fmt(25000), fmt(2000000), fmt(null)]).toEqual(['950', '1.5K', '25K', '2.0M', '—']);
});

test('it shows the trend it rode and every file per format; nothing posts until the owner confirms the exact plan', async () => {
  const work = jest.fn(async (_id, body) => (body.op === 'poc_accounts' ? { services: SVCS } : { pocFolders: [{ ...F, posted: { svc: 'uploadpost', approvedBy: 'owner', platforms: { tiktok: { ok: true, piece: 'video', url: 'https://tiktok.com/v/1' } } } }] }));
  const { el, root, onFolders, render } = mount(F, work);
  await render(F);
  expect($(el, 'pst-trend').textContent).toBe('Biggest wave ever surfed');
  expect($(el, 'pst-img-story').getAttribute('src')).toContain('mimagestory'); expect($(el, 'pst-vid-story')).not.toBeNull();
  await act(async () => $(el, 'pst-fmt-wide').click());
  expect($(el, 'pst-post-wide').textContent).toBe('wide post');
  expect($(el, 'pst-approve-btn').disabled).toBe(true);                                   // nothing switched on → nothing can go
  await act(async () => $(el, 'pst-plat-tiktok').click());
  await act(async () => $(el, 'pst-approve-btn').click());
  expect(work).not.toHaveBeenCalledWith('c', expect.objectContaining({ op: 'poc_approve' }));   // the first click only shows the plan
  expect($(el, 'pst-confirm').textContent).toContain('TikTok gets the video');
  await act(async () => $(el, 'pst-confirm-yes').click());
  expect(work).toHaveBeenCalledWith('c', { op: 'poc_approve', job: 'poc9', tools: { svc: 'uploadpost', platforms: { tiktok: 'video' } } });
  expect(onFolders).toHaveBeenCalled();
  act(() => root.unmount()); el.remove();
});

test('the goal is saved before approving, a TEST needs the owner’s tick, and a posted PoC shows its reads and cost per 1K views', async () => {
  const work = jest.fn(async (_id, body) => (body.op === 'poc_accounts' ? { services: SVCS } : { pocFolders: [F] }));
  const { el, root, render } = mount(F, work);
  const T = { ...F, test: { by: 'Claude' } };
  await render(T);
  await act(async () => $(el, 'pst-goal-buzz').click());
  const n = $(el, 'pst-goal-n'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(n, '40'); n.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => $(el, 'pst-goal-save').click());
  expect(work).toHaveBeenCalledWith('c', { op: 'poc_goal', job: 'poc9', tools: { type: 'buzz', target: 40 } });
  await act(async () => $(el, 'pst-plat-x').click());
  expect($(el, 'pst-approve-btn').disabled).toBe(true);                                   // a TEST never posts unless he ticks it
  await act(async () => $(el, 'pst-real').click());
  expect($(el, 'pst-approve-btn').disabled).toBe(false);
  const P = { ...F, posted: { svc: 'uploadpost', approvedBy: 'owner', platforms: { x: { ok: true, piece: 'image', url: 'https://x.com/1' }, tiktok: { ok: false, piece: 'video', error: 'Expired token' } } },
    reach: { reads: [{ key: 'h24', views: 1500, engagement: 48, grade: { verdict: 'on pace', cpm: 0 } }], last: { views: 1500, engagement: 48, grade: { verdict: 'on pace', cpm: 0 } } } };
  await render(P);
  expect($(el, 'pst-posted').textContent).toContain('Expired token'); expect($(el, 'pst-read-h24').textContent).toContain('1.5K');
  expect($(el, 'pst-read-d7').textContent).toContain('reads 7 d after it posted'); expect($(el, 'pst-cpm').textContent).toBe('$0.00');
  await act(async () => $(el, 'pst-read-now').click());
  expect(work).toHaveBeenCalledWith('c', { op: 'poc_reach', job: 'poc9' });
  act(() => root.unmount()); el.remove();
});
