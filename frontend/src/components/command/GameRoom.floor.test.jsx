import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Court } from './GameRoom';

// 🏟 Owner 2026-11-13: no basketball court on every sport — each sport draws its own floor.
test('the shot chart draws the floor of its own sport', async () => {
  const plays = [{ id: 1, x: 10, y: 10, side: 'a', made: true }];
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  for (const [sport, floor] of [['nba', 'hoops'], ['nfl', 'grid'], ['nhl', 'rink'], ['epl', 'pitch'], ['mlb', 'diamond'], ['ufc', 'cage'], ['??', 'grid']]) {
    await act(async () => { root.render(<Court plays={plays} sport={sport} />); });
    expect(el.querySelector('[data-testid="grm-court"]').dataset.floor).toBe(floor);
  }
  await act(async () => { root.render(<Court plays={[]} sport="nba" />); });
  expect(el.querySelector('[data-testid="grm-court"]')).toBeNull();   // no spots, no floor
  await act(async () => root.unmount()); el.remove();
});
