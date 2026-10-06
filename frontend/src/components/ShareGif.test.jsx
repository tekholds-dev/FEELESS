import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../lib/shareGif', () => ({ renderShareGif: jest.fn(async () => new Blob(['GIF89a'], { type: 'image/gif' })), renderShareCard: jest.fn(async () => new Blob(['PNG'], { type: 'image/png' })),
  DESIGNS: [['royal', '🟩 Royal'], ['nebula', '🌌 Nebula'], ['gold', '🪙 Gold']] }));
jest.mock('sonner', () => ({ toast: { error: jest.fn() } }));

test('share card: opens as a still that spins in, a design re-renders it, 🎞 Animate makes the GIF only when asked', async () => {
  global.URL.createObjectURL = jest.fn(() => 'blob:x'); global.URL.revokeObjectURL = jest.fn();
  const { ShareGifButton } = require('./ShareGif'); const { renderShareGif, renderShareCard } = require('../lib/shareGif');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ShareGifButton card={{ title: 'Moon', tone: 'up' }} />); });
  await act(async () => { el.querySelector('[data-testid="share-gif"]').click(); });
  expect(renderShareCard.mock.calls[0][0].theme).toBeUndefined();          // royal = the original look
  expect(renderShareGif).not.toHaveBeenCalled();                            // no heavy GIF render on open
  const img = () => document.querySelector('[data-testid="share-img"]');
  expect(img().className).toContain('gif-spin'); expect(img().dataset.kind).toBe('png');
  expect(document.querySelector('[data-testid="share-download"]').getAttribute('download')).toBe('feeless-moon.png');
  await act(async () => { document.querySelector('[data-testid="gif-design-gold"]').click(); });
  expect(renderShareCard.mock.calls.at(-1)[0]).toMatchObject({ title: 'Moon', theme: 'gold' });
  await act(async () => { document.querySelector('[data-testid="share-animate"]').click(); });
  expect(renderShareGif.mock.calls.at(-1)[0]).toMatchObject({ theme: 'gold' }); expect(img().dataset.kind).toBe('gif');
  expect(document.querySelector('[data-testid="share-download"]').getAttribute('download')).toBe('feeless-moon.gif');
});
