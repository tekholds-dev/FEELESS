import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import MusicFind, { ytId } from './MusicFind';

test('ytId reads a YouTube id from any link shape', () => {
  expect(ytId('https://www.youtube.com/watch?v=m1a_GqJf02M')).toBe('m1a_GqJf02M');
  expect(ytId('https://youtu.be/m1a_GqJf02M?t=3')).toBe('m1a_GqJf02M');
  expect(ytId('https://open.spotify.com/track/x')).toBeNull();
});

test('search is debounced, ▶ plays now and ＋ queues; top played resolves a chart song on YouTube', async () => {
  jest.useFakeTimers();
  const vid = { id: 'aaaaaaaaaaa', title: 'Drake - Gods Plan', channel: 'Drake', length: '3:19', views: '1M', url: 'https://www.youtube.com/watch?v=aaaaaaaaaaa', thumb: '' };
  global.fetch = jest.fn(u => Promise.resolve({ json: () => Promise.resolve(String(u).includes('/music/top') ? { source: 'Apple', rows: [{ title: 'Song', artist: 'Art', query: 'Art Song' }] } : { youtube: [vid], spotify: null, spotifyOn: false }) }));
  const onAdd = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<MusicFind onAdd={onAdd} />); });
  const input = el.querySelector('[data-testid="mf-q"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(input, 'drake'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(global.fetch).not.toHaveBeenCalled();                     // debounced
  await act(async () => { jest.advanceTimersByTime(350); }); await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  await act(async () => { el.querySelector('[data-testid="mf-play-0"]').click(); });
  expect(onAdd).toHaveBeenCalledWith({ url: vid.url, title: vid.title }, true);
  await act(async () => { el.querySelector('[data-testid="mf-top"]').click(); }); await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  await act(async () => { el.querySelector('[data-testid="mf-top-0"]').click(); }); await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); });
  expect(onAdd).toHaveBeenLastCalledWith({ url: vid.url, title: 'Art - Song' }, true);
  jest.useRealTimers();
});
