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

test('📎 a reference is added by link and an image keeps the picked reference', async () => {
  const doc = { id: 'w1', messages: [{ media: { id: 'mref1', kind: 'image', status: 'done', url: '/api/cats/media/c1/mref1.png', prompt: 'my mascot' } }] };
  const work = jest.fn(async (_id, p) => (p.op === 'media_models' ? { models: MODELS, linked: ['fal'], pick: { image: 'fal-flux-schnell', video: 'fal-wan22-5b' }, providers: PROV } : { doc, id: 'mref2' }));
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={doc} setDoc={() => {}} />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const link = q('media-ref-link'); await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(link, 'https://x.example/hero.png'); link.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => link.form.requestSubmit());
  expect(work).toHaveBeenCalledWith('c1', { op: 'media_ref', job: 'w1', text: 'https://x.example/hero.png' });
  await act(async () => q('media-kind-image').click());
  await act(async () => q('media-ref-mref1').click());
  const ta = q('media-text') || document.querySelector('[aria-label="What to make"]');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, 'him on a beach'); ta.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => q('media-make').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_make', job: 'w1', text: 'him on a beach', tools: { kind: 'image', model: 'fal-flux-schnell', ref: 'mref1' } });
  act(() => root.unmount());
});

test('✏ FLUX Video Edit: your clip + your words on OpenRouter, no character needed, and it waits for what to change', async () => {
  const SWAP = [{ id: 'fal-wan-replace', label: 'Wan 2.2 Animate · Replace', why: 'swap', rate: 0.06, by: 'frames', provider: 'fal', needsChar: true, ready: false }, { id: 'or-flux-edit', label: 'FLUX Video Edit', why: 'edit', rate: 0.03, by: 'seconds', provider: 'openrouter', needsChar: false, ready: true }];
  const work = jest.fn(async (id, b) => (b.op === 'media_models' ? { models: MODELS, linked: ['openrouter'], pick: {}, providers: { ...PROV, openrouter: { name: 'OpenRouter', signup: 'https://openrouter.ai', keys: 'https://openrouter.ai/settings/keys' } }, swap: SWAP, swapMaxS: 15 } : { doc: { messages: [] } }));
  const doc = { messages: [{ media: { id: 'mclip', clip: true, status: 'done', kind: 'video', label: 'Street', secs: 10, fps: 30 } }] };   // no character picture
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={doc} setDoc={() => {}} />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('swap-model-fal-wan-replace').disabled).toBe(true);   // fal.ai is not linked: its swaps cannot be picked
  expect(q('swap-go').disabled).toBe(true); expect(q('media-swap').textContent).toContain('Say what to change');
  await act(async () => { const el = q('swap-note'); Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, 'make it night with neon signs'); el.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(q('media-swap').textContent).toContain('about $0.30 on your OpenRouter');   // 10 s × $0.03
  expect(q('swap-go').textContent).toContain('Edit the clip');
  await act(async () => q('swap-go').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_make', job: 'w1', text: 'make it night with neon signs', tools: { swap: 'or-flux-edit', clip: 'mclip' } });
  await act(async () => root.unmount());
});

test('🎭 swap into a clip: the price comes from the clip, the rights tick gates adding one, and Swap sends the clip + model', async () => {
  const SWAP = [{ id: 'fal-wan-replace', label: 'Wan 2.2 Animate · Replace', why: 'swap', rate: 0.06, by: 'frames', ready: true }, { id: 'fal-kling3-motion', label: 'Kling 3.0 Motion Control', why: 'moves', rate: 0.126, by: 'seconds', ready: true }];
  const work = jest.fn(async (id, b) => (b.op === 'media_models' ? { models: MODELS, linked: ['fal'], pick: { image: 'fal-flux-schnell', video: 'fal-wan22-5b' }, providers: PROV, swap: SWAP, swapMaxS: 15 } : { doc: { messages: [] } }));
  const doc = { character: { mid: 'mc', url: '/api/cats/media/c1/mc.png' }, messages: [{ media: { id: 'mclip', clip: true, status: 'done', kind: 'video', label: 'Dance trend', secs: 10, fps: 32 } }] };
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={doc} setDoc={() => {}} />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('media-swap').textContent).toContain('about $1.20');   // 10 s × 32 fps / 16 × $0.06
  expect(q('swap-file').disabled).toBe(true);
  await act(async () => q('swap-rights').click()); expect(q('swap-file').disabled).toBe(false);
  await act(async () => q('swap-model-fal-kling3-motion').click()); expect(q('media-swap').textContent).toContain('about $1.26');
  await act(async () => q('swap-go').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_make', job: 'w1', text: '', tools: { swap: 'fal-kling3-motion', clip: 'mclip' } });
  await act(async () => root.unmount());
});

test('🎭 Bishop on OpenRouter: Seedance is the default swap, priced in tokens; a Bluesky link or a Spot clip adds a clip with its start', async () => {
  const SWAP = [{ id: 'fal-wan-replace', label: 'Wan 2.2 Animate · Replace', why: 'swap', rate: 0.06, by: 'frames', provider: 'fal', needsChar: true, ready: false },
    { id: 'or-seedance-swap', label: 'Seedance 2.0 · Replace', why: 'clean', rate: 0.0000043, by: 'tokens', provider: 'openrouter', needsChar: true, ready: true },
    { id: 'or-seedance-fast-swap', label: 'Seedance 2.0 Fast · Replace', why: 'quick', rate: 0.000002475, by: 'tokens', provider: 'openrouter', needsChar: true, ready: true }];
  const OR = { ...PROV, openrouter: { name: 'OpenRouter', signup: 'https://openrouter.ai', keys: 'https://openrouter.ai/settings/keys' } };
  const added = { messages: [{ media: { id: 'mnew', clip: true, status: 'done', kind: 'video', label: '@dancer: the dance', secs: 15, fps: 30, source: 'Bluesky' } }] };
  const work = jest.fn(async (id, b) => (b.op === 'media_models' ? { models: MODELS, linked: ['openrouter'], pick: {}, providers: OR, swap: SWAP, swapMaxS: 15 } : { doc: added }));
  localStorage.setItem('feeless.swapClip', JSON.stringify({ url: 'https://bsky.app/profile/dancer.bsky.social/post/3abc', title: '@dancer: the dance' }));
  const doc = { title: 'Bishop', character: { mid: 'mc', url: '/api/cats/media/c1/mc.png' }, messages: [{ media: { id: 'mclip', clip: true, status: 'done', kind: 'video', label: 'Street', secs: 9.6, fps: 30 } }] };
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={doc} setDoc={() => {}} />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('swap-model-or-seedance-swap').getAttribute('aria-checked')).toBe('true');
  expect(q('media-swap').textContent).toContain('about $0.93 on your OpenRouter');   // 921,600 × 24 × 10 s / 1024 × $0.0000043
  expect(q('media-swap').textContent).toContain('replace the main character with Bishop');
  expect(q('swap-spot').textContent).toContain('@dancer'); expect(q('swap-spot-add').disabled).toBe(true);   // the rights tick first
  await act(async () => q('swap-rights').click());
  const type = async (id, v) => act(async () => { const el = q(id); Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); });
  await type('swap-start', '3');
  await act(async () => q('swap-spot-add').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_clip', job: 'w1', text: 'https://bsky.app/profile/dancer.bsky.social/post/3abc', tools: { rights: true, name: '@dancer: the dance', start: 3 } });
  expect(localStorage.getItem('feeless.swapClip')).toBe(null); expect(q('swap-spot')).toBe(null);   // used once, then gone
  await type('swap-link', 'https://cdn.example.com/a.mp4');
  await act(async () => q('swap-link-add').closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_clip', job: 'w1', text: 'https://cdn.example.com/a.mp4', tools: { rights: true, start: 3 } });
  await act(async () => root.unmount());
});

test('🎭 Seedance refuses a clip under 4 s before any call', async () => {
  const SWAP = [{ id: 'or-seedance-swap', label: 'Seedance 2.0 · Replace', why: 'clean', rate: 0.0000043, by: 'tokens', provider: 'openrouter', needsChar: true, ready: true }];
  const work = jest.fn(async () => ({ models: MODELS, linked: ['openrouter'], pick: {}, providers: { ...PROV, openrouter: { name: 'OpenRouter', keys: 'https://openrouter.ai/settings/keys' } }, swap: SWAP, swapMaxS: 15 }));
  const doc = { character: { mid: 'mc', url: '/x.png' }, messages: [{ media: { id: 'm2', clip: true, status: 'done', kind: 'video', label: 'Tiny', secs: 2, fps: 30 } }] };
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={doc} setDoc={() => {}} />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('swap-go').disabled).toBe(true); expect(q('media-swap').textContent).toContain('4 s or more');
  await act(async () => root.unmount());
});

test('🏷 the picker: a 17 s reel priced per model, four sorts, the model used last picked, and your cap greys out a swap above it', async () => {
  const S = (id, label, rate, maxS, added, rec) => ({ id, label, why: label, rate, by: 'tokens', provider: 'openrouter', needsChar: true, ready: true, maxS, added, rec });
  const SWAP = [S('or-seedance-swap', 'Seedance 2.0', 0.0000043, 15, '2026-04-14', 1), S('or-seedance25-flash-swap', 'Seedance 2.5 Flash', 0.0000043, 30, '2026-11-15', 2),
    S('or-seedance25-swap', 'Seedance 2.5', 0.0000064, 30, '2026-08-07', 3), S('or-seedance-mini-swap', 'Seedance 2.0 Mini', 0.0000021, 15, '2026-08-11', 5)];
  const work = jest.fn(async (id, b) => (b.op === 'media_cap' ? { swapCapUsd: Number(b.text) }
    : { models: MODELS, linked: ['openrouter'], pick: {}, providers: { ...PROV, openrouter: { name: 'OpenRouter', keys: 'https://openrouter.ai/settings/keys' } }, swap: SWAP, swapMaxS: 30,
      swapCapUsd: 2, swapUsed: { 'or-seedance-mini-swap': 3, 'or-seedance25-flash-swap': 1 }, swapLast: 'or-seedance25-flash-swap', publicRefs: false }));
  const doc = { title: 'Bishop', character: { mid: 'mc', url: '/x.png' }, messages: [{ media: { id: 'm17', clip: true, status: 'done', kind: 'video', label: 'IG reel', secs: 17, fps: 30 } }] };
  const { root } = await mount(<MediaButton cat={{ id: 'c1' }} row={{ id: 'w1' }} work={work} doc={doc} setDoc={() => {}} />);
  await act(async () => q('media-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const order = () => [...document.querySelectorAll('[data-testid^="swap-model-"]')].map(x => x.dataset.testid.replace('swap-model-', ''));
  expect(order()).toEqual(['or-seedance-swap', 'or-seedance25-flash-swap', 'or-seedance25-swap', 'or-seedance-mini-swap']);
  expect(q('swap-model-or-seedance25-flash-swap').getAttribute('aria-checked')).toBe('true');   // the one used last
  expect(q('swap-model-or-seedance25-flash-swap').textContent).toContain('$1.58 · up to 30 s · used 1×');   // the whole 17 s
  expect(q('swap-model-or-seedance-swap').textContent).toContain('makes the first 15 s');
  await act(async () => q('swap-sort-new').click()); expect(order()[0]).toBe('or-seedance25-flash-swap');
  await act(async () => q('swap-sort-cheap').click()); expect(order()[0]).toBe('or-seedance-mini-swap');
  await act(async () => q('swap-sort-used').click()); expect(order().slice(0, 2)).toEqual(['or-seedance-mini-swap', 'or-seedance25-flash-swap']);
  expect(q('media-swap').textContent).toContain('private 2-hour https link');
  await act(async () => q('swap-model-or-seedance25-swap').click());   // $2.35 > the $2 cap
  expect(q('swap-go').disabled).toBe(true); expect(q('media-swap').textContent).toContain('over your $2.00 cap per swap');
  const cap = q('swap-cap'); await act(async () => { Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(cap, '3'); cap.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { cap.dispatchEvent(new FocusEvent('focusout', { bubbles: true })); });
  expect(work).toHaveBeenCalledWith('c1', { op: 'media_cap', text: '3' }); expect(q('media-swap').textContent).not.toContain('over your');
  await act(async () => root.unmount());
});
