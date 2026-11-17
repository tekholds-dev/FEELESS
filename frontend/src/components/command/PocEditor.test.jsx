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

const PROJ = { aspect: '9:16', sources: [{ id: 's1', name: 'street.mp4', dur: 10, kind: 'video' }, { id: 's2', name: 'intro.mp4', dur: 4, kind: 'video' }],
  clips: [{ id: 'c1', src: 's1', in: 0, out: 10, speed: 1, fade: 0, mute: false }, { id: 'c2', src: 's2', in: 0, out: 4, speed: 1, fade: 0, mute: false }], texts: [], music: [] };
async function editor(work) { const box = document.createElement('div'); document.body.appendChild(box); let root; await act(async () => { root = createRoot(box); root.render(<VideoEditor cat={{ id: 'c' }} work={work} />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); }); return { box, root }; }
const typeIn = async (el, v) => act(async () => { Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); });

test('🧾 an agent edit is shown line by line before you keep it, and Undo all brings yours back', async () => {
  const work = jest.fn(async (_c, b) => (b.op === 'playc_get' ? { project: PROJ, files: [], canAsk: true, canPaid: true, pocs: [{ id: 'w1', name: 'Bishop' }] }
    : b.op === 'playc_ask' ? { project: { ...PROJ, clips: [{ ...PROJ.clips[0], out: 6 }], texts: [{ id: 't9', at: 0, dur: 2.5, text: 'WAIT FOR IT', y: 0.2, size: 0.07, color: '#ffffff' }] }, say: 'Tighter.', usd: 0.001 } : { ok: true }));
  const { box, root } = await editor(work);
  expect(q(box, 'pce-safe-zones').children).toHaveLength(3);   // 9:16: top bar, handle + caption, like · share
  await typeIn(q(box, 'pce-ask'), 'make it tighter with a hook');
  await act(async () => q(box, 'pce-send').closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  const ch = q(box, 'pce-changes');
  expect(ch.textContent).toContain('Tighter.'); expect(ch.textContent).toContain('Trimmed street.mp4: 10.0 s → 6.0 s'); expect(ch.textContent).toContain('Cut intro.mp4 (4.0 s)'); expect(ch.textContent).toContain('WAIT FOR IT');
  expect(q(box, 'pce-clock').textContent).toContain('0:06.0');
  await act(async () => q(box, 'pce-undo-agent').click());
  expect(q(box, 'pce-changes')).toBeNull(); expect(q(box, 'pce-clock').textContent).toContain('0:14.0');
  await act(async () => root.unmount());
});

test('🎭 a swap ask in the editor points to Post; + Hook adds words in the safe area; Post lists your PoC folders and needs the rights tick', async () => {
  const work = jest.fn(async (_c, b) => (b.op === 'playc_get' ? { project: PROJ, files: [], canAsk: true, canPaid: false, pocs: [{ id: 'w1', name: 'Bishop' }] } : { ok: true }));
  const { box, root } = await editor(work);
  await typeIn(q(box, 'pce-ask'), 'swap the guy for my character');
  await act(async () => q(box, 'pce-send').closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  expect(q(box, 'pce-said').textContent).toContain('📤 Post'); expect(work.mock.calls.some(([, b]) => b.op === 'playc_ask')).toBe(false);
  expect(q(box, 'pce-captions').disabled).toBe(true);   // no OpenRouter key on this agent
  await act(async () => q(box, 'pce-hook').click()); expect(q(box, 'pce-words').value).toBe('THE PAYOFF FIRST');
  await act(async () => q(box, 'pce-post').click());
  expect([...q(box, 'pce-post-to').options].map(o => o.textContent)).toEqual(['A new PoC folder named “Video edit”', 'Bishop']);
  expect(q(box, 'pce-post-go').disabled).toBe(true); await act(async () => q(box, 'pce-post-rights').click()); expect(q(box, 'pce-post-go').disabled).toBe(false);
  await act(async () => q(box, 'pce-safe').click()); expect(q(box, 'pce-safe-zones')).toBeNull();
  await act(async () => root.unmount());
});
