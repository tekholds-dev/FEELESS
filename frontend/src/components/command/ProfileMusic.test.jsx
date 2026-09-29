import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProfileMusic } from './ProfileMusic';

const songs = [{ url: 'https://youtu.be/aaaaaaaaaaa', title: 'One' }, { url: 'https://youtu.be/bbbbbbbbbbb', title: 'Two' }];
const mount = ui => { const host = document.createElement('div'); document.body.appendChild(host); act(() => createRoot(host).render(ui)); return host; };

test('play hands the playlist to the Fee player; after that play/pause/skip are commands, and the view mirrors the live track', () => {
  const seen = [];
  const log = e => seen.push([e.type, e.detail]);
  window.addEventListener('feeless:music', log); window.addEventListener('feeless:music-cmd', log);
  const host = mount(<ProfileMusic songs={songs} />);
  act(() => host.querySelector('[data-testid="pm-play"]').click());
  expect(seen[0]).toEqual(['feeless:music', { songs, i: 0 }]);
  // the player reports it is on song two and playing
  act(() => { window.dispatchEvent(new CustomEvent('feeless:music-state', { detail: { playing: true, url: songs[1].url, mode: 'all' } })); });
  expect(host.querySelector('.pm-now b').textContent).toBe('Two');
  expect(host.querySelector('.pm-list li.on').textContent).toContain('Two');
  act(() => host.querySelector('[data-testid="pm-play"]').click());
  expect(seen[1]).toEqual(['feeless:music-cmd', { cmd: 'toggle' }]);
  act(() => host.querySelector('[aria-label="Shuffle"]').click());
  expect(seen[2]).toEqual(['feeless:music-cmd', { cmd: 'mode', mode: 'shuffle' }]);
});

test('owners reorder songs in edit mode', () => {
  const onChange = jest.fn();
  const host = mount(<ProfileMusic songs={songs} edit onChange={onChange} />);
  act(() => host.querySelectorAll('[aria-label="Move down"]')[0].click());
  expect(onChange).toHaveBeenCalledWith([songs[1], songs[0]]);
});
