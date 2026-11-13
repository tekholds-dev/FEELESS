import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { mediaAsk, mediaPrompt, MediaModelChip } from './MediaStudio';

test('a chat line asking for a picture or a clip goes to the media models; everything else stays with the minds', () => {
  expect(mediaAsk('make a video of him walking at dusk')).toBe('video');
  expect(mediaAsk('bring him to life')).toBe('video');
  expect(mediaAsk('generate a poster for this')).toBe('image');
  expect(mediaAsk('image: a chrome tombstone')).toBe('image'); expect(mediaAsk('video: slow push in')).toBe('video');
  expect(mediaAsk('write me 3 hooks for this video')).toBe(null);   // no make-verb on a media noun it should make → the minds answer
  expect(mediaAsk('what do you think of the caption?')).toBe(null);
});

test('a short or pointing ask carries this PoC so the model knows who "him" is; a full brief goes as written', () => {
  const carry = 'Bishop, a man in a black leather jacket and silver chains, photoreal handheld phone footage.';
  expect(mediaPrompt('make a video of him walking', carry)).toContain('From this PoC: Bishop, a man in a black leather jacket');
  const full = 'A chrome rat dances on a neon tombstone at night while the camera slowly pushes in, green rim light, rain on the stone';
  expect(mediaPrompt(full, carry)).toBe(full);
  expect(mediaPrompt('image: a chrome tombstone', '')).toBe('a chrome tombstone');
});

test('the composer chip lists ready image and video models and remembers the pick', async () => {
  const work = jest.fn(async () => ({ models: [{ id: 'bytedance/seedance', kind: 'video', label: 'Seedance', providerName: 'fal.ai', usd: 0.15, ready: true },
    { id: 'google/gemini-3.1-flash-image', kind: 'image', label: 'Gemini 3.1 Flash Image', providerName: 'OpenRouter', usd: 0.04, ready: true },
    { id: 'x/locked', kind: 'video', label: 'Locked', providerName: 'Replicate', ready: false }] }));
  const setPick = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<MediaModelChip cat={{ id: 'h' }} work={work} pick={{}} setPick={setPick} />); });
  expect(el.querySelector('[data-testid="media-chip"]').getAttribute('aria-label')).toBe('Image model Auto, video model Auto');
  await act(async () => { el.querySelector('[data-testid="media-chip"]').click(); });
  await act(async () => { await Promise.resolve(); });
  expect(document.querySelector('[data-testid="media-chip-x/locked"]')).toBeNull();   // the picker opens at page level, always on screen
  expect(document.querySelector('[data-testid="media-chip-video-x/locked"]').disabled).toBe(true);
  await act(async () => { document.querySelector('[data-testid="media-chip-video-bytedance/seedance"]').click(); });
  expect(setPick).toHaveBeenCalledWith('video', 'bytedance/seedance');
});
