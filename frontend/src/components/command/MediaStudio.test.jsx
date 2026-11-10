import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MediaButton, MediaCard } from './MediaStudio';

const PROV = { fal: { name: 'fal.ai', signup: 'https://fal.ai/login', keys: 'https://fal.ai/dashboard/keys' }, replicate: { name: 'Replicate', signup: 'https://replicate.com/signin', keys: 'https://replicate.com/account/api-tokens' } };
const MODELS = [{ id: 'fal-wan22-5b', provider: 'fal', providerName: 'fal.ai', kind: 'video', label: 'Wan 2.2 5B', why: 'cheap', usd: 0.15, ready: true },
  { id: 'rep-wan22-fast', provider: 'replicate', providerName: 'Replicate', kind: 'video', label: 'Wan 2.2 fast', why: 'cheap', usd: null, ready: false },
  { id: 'fal-flux-schnell', provider: 'fal', providerName: 'fal.ai', kind: 'image', label: 'FLUX.1 schnell', why: 'stills', usd: null, ready: true }];
const q = id => document.querySelector(`[data-testid="${id}"]`);
const mount = async el => { const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box); await act(async () => root.render(el)); await act(async () => { await new Promise(r => setTimeout(r, 0)); }); return { box, root }; };

test('🎬 nothing linked: three steps to link your own fal.ai or Replicate, and Link seals the key', async () => {
  const work = jest.fn(async () => ({ models: MODELS.map(m => ({ ...m, ready: false })), linked: [], pick: { image: null, video: null }, providers: PROV }));
  globalThis.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ cat: {} }) }));
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={{ messages: [] }} setDoc={() => {}} />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('media-link').textContent).toContain('Make an account'); expect(q('media-link').querySelectorAll('li')).toHaveLength(3);
  await act(async () => q('media-prov-replicate').click());
  const input = q('media-key'); await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'r8_' + 'A'.repeat(37)); input.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => q('media-key-save').click());
  expect(JSON.parse(globalThis.fetch.mock.calls[0][1].body)).toMatchObject({ action: 'api_key', provider: 'replicate', secret: 'r8_' + 'A'.repeat(37) });
  expect(work).toHaveBeenCalledTimes(2);   // reads the providers again once linked
  act(() => root.unmount());
});

test('🎬 linked: the cheap pick is chosen, a model on an unlinked provider is off, and Make sends kind + model + prompt', async () => {
  const work = jest.fn(async (_id, b) => (b.op === 'media_models' ? { models: MODELS, linked: ['fal'], pick: { image: 'fal-flux-schnell', video: 'fal-wan22-5b' }, providers: PROV } : { doc: { messages: [] } }));
  const setDoc = jest.fn();
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={{ messages: [] }} setDoc={setDoc} seed="A chrome rat on a tombstone" />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('media-model-fal-wan22-5b').getAttribute('aria-pressed')).toBe('true'); expect(q('media-model-rep-wan22-fast').disabled).toBe(true);
  expect(q('media-model-fal-wan22-5b').textContent).toContain('$0.15'); expect(q('media-prompt').value).toBe('A chrome rat on a tombstone');
  await act(async () => q('media-make').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_make', job: 'w1', text: 'A chrome rat on a tombstone', tools: { kind: 'video', model: 'fal-wan22-5b' } });
  expect(setDoc).toHaveBeenCalled(); expect(q('media-pop')).toBeNull();
  act(() => root.unmount());
});

test('🎬 the card shows the real state: making, done with the file, failed with why', async () => {
  const base = { id: 'm1', kind: 'video', label: 'Wan 2.2 5B', provider: 'fal', usd: 0.15, prompt: 'a rat', at: Math.round(Date.now() / 1000) - 75 };
  let { root, box } = await mount(<MediaCard m={{ media: { ...base, status: 'running', step: 'in_progress' } }} />);
  expect(box.textContent).toContain('making it · 1m 15s'); act(() => root.unmount());
  ({ root, box } = await mount(<MediaCard m={{ media: { ...base, status: 'done', url: '/api/cats/media/c1/m1.mp4', kept: true } }} />));
  expect(box.querySelector('video').getAttribute('src')).toContain('/api/cats/media/c1/m1.mp4'); expect(q('media-save')).toBeTruthy(); act(() => root.unmount());
  ({ root, box } = await mount(<MediaCard m={{ media: { ...base, status: 'failed', why: '401: no credit' } }} />));
  expect(box.textContent).toContain('401: no credit'); expect(box.querySelector('video')).toBeNull(); act(() => root.unmount());
});
