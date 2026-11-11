import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MadeLibrary, VideoEditor } from './PocEditor';

const ROWS = [{ id: 'h', type: 'image', proof: 'AI', title: 'AI vs handmade', src: '/media/samples/ai-vs-handmade.jpg', q: '', pub: true, happy: true, at: 0, cat: 'happy', agent: 'Happy', from: 'Gemini 3.1 Flash Image · $0.07 · 9s to make' },
  { id: 'a', type: 'image', proof: 'PoW', title: 'rugcheck.xyz', src: '/api/cats/c/powshot/pw1/a.jpg', q: '', at: 3, cat: 'c', agent: 'Happy', from: 'PoW #3 · $BONK' },
  { id: 'b', type: 'image', proof: 'PoB', title: 'gmgn.ai', src: '/api/cats/c/powshot/pb1/b.jpg', q: '', at: 2, cat: 'c', agent: 'Happy', from: 'PoB #1' },
  { id: 'v', type: 'video', proof: 'PoB', title: 'PoB ad', src: '/api/cats/c/showad/pob', q: 'ws=w1', at: 1, cat: 'c', agent: 'Happy', from: 'Showcase ad' }];
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`); const qa = (el, id) => [...el.querySelectorAll(`[data-testid="${id}"]`)];
async function mount(type, onUse) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<MadeLibrary cat={{ id: 'c' }} work={async (_c, b) => (b.op === 'media_library' ? { rows: ROWS } : {})} type={type} onUse={onUse} />); }); return el; }

test('each tab shows only its own kind, filters by proof, and Use hands over the signed link', async () => {
  const got = []; const el = await mount('image', async (r, url) => { got.push([r.id, url]); });
  expect(q(el, 'pcm-count').textContent).toBe('3'); expect(qa(el, 'pcm-row')).toHaveLength(3); expect(q(el, 'pcm-rail').textContent).toContain('HAPPY · AI'); expect(q(el, 'pcm-rail').textContent).toContain('PoW #3 · $BONK');
  await act(async () => { q(el, 'pcm-k-PoB').click(); }); expect(qa(el, 'pcm-row')).toHaveLength(1); expect(q(el, 'pcm-rail').textContent).toContain('gmgn.ai');
  await act(async () => { q(el, 'pcm-use').click(); }); expect(got[0][0]).toBe('b'); expect(got[0][1]).toMatch(/\/api\/cats\/c\/powshot\/pb1\/b\.jpg\?ownerId=.*&session=/);
  await act(async () => { q(el, 'pcm-view').click(); }); expect(q(el, 'pcm-big')).not.toBeNull(); await act(async () => { q(el, 'pcm-big-close').click(); }); expect(q(el, 'pcm-big')).toBeNull();
});

test('a video keeps its own attempt and an empty kind says so plainly', async () => {
  const got = []; const el = await mount('video', async (r, url) => { got.push(url); });
  await act(async () => { q(el, 'pcm-use').click(); }); expect(got[0]).toMatch(/showad\/pob\?.*&ws=w1$/);
  const e3 = await mount('3d', async () => {}); expect(q(e3, 'pcm-empty').textContent).toContain('No 3D scenes yet');
});

test('a failed Use shows why and the shelf folds away', async () => {
  const el = await mount('image', async () => { throw new Error('Sign in with your wallet to use it.'); });
  await act(async () => { q(el, 'pcm-use').click(); }); expect(q(el, 'pcm-err').textContent).toContain('Sign in');
  await act(async () => { q(el, 'pcm-fold').click(); }); expect(q(el, 'pcm-rail')).toBeNull();
});

test("Happy's public results load with no sign-in, and an empty video editor plays one with Use", async () => {
  const got = []; const el = await mount('image', async (r, url) => { got.push(url); });
  await act(async () => { q(el, 'pcm-use').click(); }); expect(got[0]).toBe('/media/samples/ai-vs-handmade.jpg');
  const used = []; const box = document.createElement('div'); document.body.appendChild(box);
  const S = [{ id: 's', type: 'video', title: 'Street interview', src: '/media/samples/street-interview.mp4', from: 'Veo 3.1 fast · $0.40 · 58s to make', happy: true }];
  await act(async () => { createRoot(box).render(<VideoEditor cat={{ id: 'c' }} work={async () => ({})} samples={S} onSample={async r => { used.push(r.id); }} />); });
  expect(q(box, 'pce-empty-made').textContent).toContain('MADE BY HAPPY · Street interview · Veo 3.1 fast'); expect(q(box, 'pce-empty').querySelector('video').getAttribute('src')).toBe('/media/samples/street-interview.mp4');
  await act(async () => { q(box, 'pce-empty-use').click(); }); expect(used).toEqual(['s']);
});
