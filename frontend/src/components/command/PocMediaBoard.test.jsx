import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import PocMediaBoard from './PocMediaBoard';
import { splitWhy } from './MediaStudio';

const q = id => document.querySelector(`[data-testid="${id}"]`);
const mount = async el => { const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box); await act(async () => root.render(el)); return { root, box }; };
const now = () => Math.round(Date.now() / 1000);
const msg = media => ({ by: 'Media', text: media.label, media });

test('🖼 the board shows what is making (its real step and time), every finished one as a tile, clips apart, and failures folded', async () => {
  const doc = { id: 'w1', character: { mid: 'i1' }, messages: [
    msg({ id: 'c1', kind: 'video', label: 'my clip', provider: 'upload', status: 'done', clip: true, url: '/api/cats/media/c/c1.mp4' }),
    msg({ id: 'i1', kind: 'image', label: 'Bishop', provider: 'openrouter', status: 'done', url: '/api/cats/media/c/i1.png', paidUsd: 0.04 }),
    msg({ id: 'v1', kind: 'video', label: 'Aleph swap', provider: 'openrouter', status: 'done', swap: true, url: '/api/cats/media/c/v1.mp4', usd: 2.8 }),
    msg({ id: 'f1', kind: 'video', label: 'Seedance', provider: 'openrouter', status: 'failed', why: "ByteDance's Seedance refuses a clip with a real person in it. Nothing was charged. (400: may contain real person)" }),
    msg({ id: 'r1', kind: 'image', label: 'Flash', provider: 'openrouter', status: 'running', step: 'in_progress', at: now() - 65 }),
  ] };
  const { root, box } = await mount(<PocMediaBoard cat={{ id: 'c' }} doc={doc} work={jest.fn()} setDoc={jest.fn()} />);
  expect(q('poc-board-live').textContent).toContain('Making it · 1m 5s');
  const tiles = q('poc-board-grid').querySelectorAll('li');
  expect(tiles).toHaveLength(2); expect(tiles[0].textContent).toContain('Swap'); expect(tiles[1].textContent).toContain('👤');   // newest first; the character is marked
  expect(q('poc-board-clips').querySelectorAll('button')).toHaveLength(1);
  expect(q('poc-board-failed').textContent).toContain("1 didn't finish"); expect(box.textContent).not.toContain('real person in it');   // folded until asked
  await act(async () => q('poc-board-failed').click());
  expect(box.textContent).toContain('refuses a clip with a real person'); expect(box.textContent).not.toContain('400: may contain');   // the plain words, not the raw
  await act(async () => q('poc-board-v1').click());
  expect(q('poc-board-view').querySelector('[data-testid="media-v1"] video')).toBeTruthy();   // the full card, with its buttons
  await act(async () => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))); expect(q('poc-board-view')).toBeNull();
  act(() => root.unmount());
});

test('🖼 an empty folder says what to do; a refusal splits into one plain sentence and the provider\'s words', async () => {
  const { root, box } = await mount(<PocMediaBoard cat={{ id: 'c' }} doc={{ messages: [] }} work={jest.fn()} setDoc={jest.fn()} />);
  expect(box.textContent).toContain('nothing made yet'); expect(box.textContent).toContain('It shows up here'); act(() => root.unmount());
  expect(splitWhy('The provider is busy right now. Nothing was charged. Try again in a minute. (429: slow down (retry))')).toEqual(['The provider is busy right now. Nothing was charged. Try again in a minute.', '429: slow down (retry)']);
  expect(splitWhy('401: no credit')).toEqual(['401: no credit', '']); expect(splitWhy('')).toEqual(['It did not finish.', '']);
});
