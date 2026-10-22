import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MissionTrack, hereIndex } from './MissionTrack';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const M = [['01', 'Foundation', 'LIVE', 'globe + war rooms'], ['02', 'Intel', 'LIVE', 'edge'], ['03', 'Execution', 'TESTING', 'routing'], ['04', 'Vault', 'PLANNED', 'shares']];

test('the rocket sits after the last LIVE milestone', () => {
  expect(hereIndex(M)).toBe(1); expect(hereIndex([['01', 'x', 'PLANNED', '']])).toBe(-1);
});

test('the track: a pylon per milestone, the filter dims the rest, a tap drops its text down', async () => {
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<MissionTrack missions={M} filter="LIVE" />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(el.querySelectorAll('.mt-pylon').length).toBe(4); expect(q('mission-03').className).toContain('is-dim'); expect(q('mission-01').className).not.toContain('is-dim');
  expect(el.querySelector('.mt-rocket')).not.toBeNull(); expect(q('mission-drop')).toBeNull();
  await act(async () => { q('mission-03').click(); });
  expect(q('mission-drop').textContent).toContain('routing'); expect(q('mission-03').getAttribute('aria-expanded')).toBe('true');
  await act(async () => { q('mission-03').click(); });
  expect(q('mission-drop')).toBeNull();
  await act(async () => { root.unmount(); });
});
