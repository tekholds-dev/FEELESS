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

test('👤 a done image animates and becomes the character; the character badge rides the card (owner 2026-11-12, Bishop)', async () => {
  const img = { id: 'mi1', kind: 'image', label: 'Flash Image', provider: 'openrouter', prompt: 'Bishop in the latest gear', at: 1, status: 'done', kept: true, url: '/api/cats/media/c1/mi1.png' };
  const work = jest.fn(async () => ({ doc: { messages: [] } }));
  const setDoc = jest.fn();
  let { root } = await mount(<MediaCard m={{ media: img }} cat={{ id: 'c1' }} doc={{ id: 'w1', character: null }} work={work} setDoc={setDoc} />);
  await act(async () => q('media-life').click());
  expect(work).toHaveBeenLastCalledWith('c1', expect.objectContaining({ op: 'media_make', job: 'w1', tools: { kind: 'video', img: 'mi1' } }));
  expect(work.mock.calls.at(-1)[1].text).toContain('This exact person comes alive');
  await act(async () => q('media-char').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_char', job: 'w1', text: 'mi1' });
  expect(setDoc).toHaveBeenCalled(); act(() => root.unmount());
  // already the character: badge on, button unsets
  ({ root } = await mount(<MediaCard m={{ media: img }} cat={{ id: 'c1' }} doc={{ id: 'w1', character: { mid: 'mi1', url: img.url } }} work={work} setDoc={setDoc} />));
  expect(q('media-ischar').textContent).toContain('THE CHARACTER');
  await act(async () => q('media-char').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_char', job: 'w1', text: '' });
  act(() => root.unmount());
  // a video card never offers it
  ({ root } = await mount(<MediaCard m={{ media: { ...img, id: 'mv1', kind: 'video', url: '/api/cats/media/c1/mv1.mp4' } }} cat={{ id: 'c1' }} doc={{ id: 'w1' }} work={work} setDoc={setDoc} />));
  expect(q('media-life')).toBeNull(); expect(q('media-char')).toBeNull();
  act(() => root.unmount());
});

test('👤 the composer says the character leads a video, and Not this time sends noChar', async () => {
  const work = jest.fn(async (_id, b) => (b.op === 'media_models' ? { models: MODELS, linked: ['fal'], pick: { image: 'fal-flux-schnell', video: 'fal-wan22-5b' }, providers: PROV } : { doc: { messages: [] } }));
  const doc = { messages: [], character: { mid: 'mi1', url: '/api/cats/media/c1/mi1.png' } };
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={doc} setDoc={() => {}} seed="Bishop walks" />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('media-charline').textContent).toContain('Starts from your character');
  await act(async () => q('media-nochar').click());
  expect(q('media-charline').textContent).toContain('sits this one out');
  await act(async () => q('media-make').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_make', job: 'w1', text: 'Bishop walks', tools: { kind: 'video', model: 'fal-wan22-5b', noChar: true } });
  act(() => root.unmount());
});

jest.mock('./PocPlay', () => ({ __esModule: true, default: p => <div data-testid="poc-play-mock"><button type="button" data-testid="pp-save" onClick={() => p.onSave('data:image/png;base64,AAAA', 'phone')}>s</button><button type="button" data-testid="pp-close" onClick={p.onClose}>x</button><i data-testid="pp-src">{p.src}|{p.kind}|{p.media.map(m => m.id).join(',')}</i></div> }));

test('🎨 POC-PLAY: a done picture or video opens the playground, and Save files a new version into the same proof', async () => {
  const img = { id: 'mi1', kind: 'image', label: 'Flash', provider: 'fal', prompt: 'a shoe', at: 1, status: 'done', kept: true, url: '/api/cats/media/c1/mi1.png' };
  const other = { media: { id: 'mi2', kind: 'image', status: 'done', url: '/api/cats/media/c1/mi2.png' } };
  const work = jest.fn(async () => ({ doc: { messages: [] } })); const setDoc = jest.fn();
  let { root } = await mount(<MediaCard m={{ media: img }} cat={{ id: 'c1' }} doc={{ id: 'w1', messages: [{ media: img }, other] }} work={work} setDoc={setDoc} />);
  expect(q('poc-play-mock')).toBeNull();
  await act(async () => q('media-play').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('pp-src').textContent).toMatch(/mi1\.png\|image\|mi2$/);                    // the proof's OTHER pictures ride along
  await act(async () => q('pp-save').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_play', job: 'w1', text: 'data:image/png;base64,AAAA', tools: { from: 'mi1', template: 'phone' } });
  expect(setDoc).toHaveBeenCalled();
  await act(async () => q('pp-close').click()); expect(q('poc-play-mock')).toBeNull(); act(() => root.unmount());
  ({ root } = await mount(<MediaCard m={{ media: { ...img, status: 'running' } }} cat={{ id: 'c1' }} doc={{ id: 'w1' }} work={work} setDoc={setDoc} />));
  expect(q('media-play')).toBeNull(); act(() => root.unmount());                         // not until it is done
  ({ root } = await mount(<MediaCard m={{ media: img }} />)); expect(q('media-play')).toBeNull(); act(() => root.unmount());   // read-only card: no playground
});
