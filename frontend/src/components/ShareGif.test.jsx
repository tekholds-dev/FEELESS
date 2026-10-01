import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../lib/shareGif', () => ({ renderShareGif: jest.fn(async () => new Blob(['GIF89a'], { type: 'image/gif' })), DESIGNS: [['royal', '🟩 Royal'], ['nebula', '🌌 Nebula'], ['gold', '🪙 Gold']] }));
jest.mock('sonner', () => ({ toast: { error: jest.fn() } }));

test('share GIF: pick a design and it re-renders in that look (royal = the original)', async () => {
  global.URL.createObjectURL = jest.fn(() => 'blob:x'); global.URL.revokeObjectURL = jest.fn();
  const { ShareGifButton } = require('./ShareGif'); const { renderShareGif } = require('../lib/shareGif');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ShareGifButton card={{ title: 'Moon', tone: 'up' }} />); });
  await act(async () => { el.querySelector('[data-testid="share-gif"]').click(); });
  expect(renderShareGif.mock.calls[0][0].theme).toBeUndefined();
  await act(async () => { document.querySelector('[data-testid="gif-design-gold"]').click(); });
  expect(renderShareGif.mock.calls.at(-1)[0]).toMatchObject({ title: 'Moon', theme: 'gold' });
});
