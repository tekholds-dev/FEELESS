import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { WatchLive, tvHost } from './WatchLive';

const BOARD = { ok: true, games: [{ id: '9', state: 'in', detail: '5:54 - 4th', home: { abbr: 'NY', name: 'Knicks', score: 106, color: '#1d428a', record: '5-4' }, away: { abbr: 'MIL', name: 'Bucks', score: 78, color: '#00471b' }, last: 'Knicks timeout', homeWin: 99.9, tv: ['NBA TV', 'MSG'] },
  { id: '8', state: 'post', detail: 'Final', home: { abbr: 'A', name: 'Aces', score: 1 }, away: { abbr: 'B', name: 'Bees', score: 0 }, homeWin: null, tv: [] }] };
const GAME = { ok: true, win: [50, 62, 80, 99.9], plays: [{ text: 'Brunson makes a three', clock: '6:01', period: 4, score: true }], spread: 'NY -14.5', total: 221.5, by: 'DraftKings' };

test('a live game sits beside the stream: score, win chance, the plays, where it is on TV, and a PoB with its price', async () => {
  const urls = []; global.fetch = jest.fn(u => { urls.push(String(u)); return Promise.resolve({ ok: true, json: () => Promise.resolve(String(u).endsWith('/9') ? GAME : BOARD) }); });
  const onBrowse = jest.fn(); const onCommand = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<WatchLive onBrowse={onBrowse} onCommand={onCommand} price="≈$0.0040 a proof" />); });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(urls[0]).toContain('/api/cats/scores/nba'); expect(urls.some(u => u.endsWith('/api/cats/scores/nba/9'))).toBe(true);   // the live game opens by itself
  expect(q('wl-side').textContent).toContain('Knicks'); expect(q('wl-side').textContent).toContain('NY -14.5'); expect(q('wl-side').textContent).toContain('Brunson makes a three');
  await act(async () => { q('wl-tv-NBA TV').click(); }); expect(onBrowse).toHaveBeenCalledWith('nba.com/watch');
  expect(q('wl-pob').textContent).toContain('≈$0.0040 a proof'); await act(async () => { q('wl-pob').click(); }); expect(onCommand).toHaveBeenCalledWith('file a pob Bucks vs Knicks');
  await act(async () => { q('wl-lg-nfl').click(); }); expect(urls.at(-1)).toContain('/api/cats/scores/nfl');
  expect(tvHost('ESPN2')).toBe('espn.com/watch'); expect(tvHost('MyMi')).toBeNull();
});
