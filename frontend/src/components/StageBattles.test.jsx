import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./RunnersPanel', () => ({ Countdown: () => <b>4:12</b> }));
const seat = (n, win) => ({ seat: n, a: { symbol: `A${n}`, pct: win === 'a' ? 5 : -2 }, b: { symbol: `B${n}`, pct: win === 'b' ? 5 : -2 }, win });
const pair = (an, bn, aNow, bNow, wins) => ({ a: { key: an, name: an, emoji: '🔥', start: 0, now: aNow }, b: { key: bn, name: bn, emoji: '🧬', start: 0, now: bNow }, duels: { seats: wins.map((w, i) => seat(i + 1, w)) } });

test('fight read: sparks decide the leader, the card move breaks a tie, the rope pulls toward the leader', () => {
  const { fightRead } = require('./StageBattles');
  const r = fightRead(pair('Alpha', 'Beta', 1, 4, ['a', 'a', 'a', 'a', 'b', '']));
  expect([r.sa, r.sb, r.lead]).toEqual([4, 1, 'a']); expect(r.pull).toBeGreaterThan(0); expect(r.call).toContain('running away'); expect(r.call).toContain('4–1');
  const t = fightRead(pair('Alpha', 'Beta', 1, 4, ['a', 'b'])); expect(t.lead).toBe('b'); expect(t.pull).toBeLessThan(0);   // level on sparks → the bigger move leads
  expect(fightRead(pair('Alpha', 'Beta', 0, 0, [])).call).toContain('Dead level');
});

test('main stage shows at most TWO live fights with corners, rope, spark pips, the bell and a call; one button opens the full fight', async () => {
  const { StageBattles } = require('./StageBattles'); const onFull = jest.fn();
  const b = { endsAt: 9e9, pairs: [pair('Alpha', 'Beta', 2, -1, ['a', 'a', 'b']), pair('Gamma', 'Delta', 0, 3, ['b', 'b', 'b', 'b']), pair('Extra', 'Third', 0, 0, [])] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<StageBattles b={b} onFull={onFull} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(el.querySelectorAll('.sbt-fight').length).toBe(2); expect(q('stage-battles').textContent).toContain('2 FIGHTS'); expect(q('stage-battles').textContent).toContain('4:12');
  const f0 = q('stage-fight-0'); expect(f0.textContent).toContain('Alpha'); expect(f0.textContent).toContain('+2.0%'); expect(f0.textContent).toContain('-1.0%');
  expect(f0.querySelector('.sbt-corner.is-a').className).toContain('is-lead'); expect(f0.querySelectorAll('.sbt-pips li.is-a').length).toBe(2); expect(f0.querySelectorAll('.sbt-pips li.is-b').length).toBe(1);
  expect(q('stage-fight-1').querySelector('.sbt-corner.is-b').className).toContain('is-lead'); expect(q('stage-call-1').textContent).toContain('Delta');
  // each corner shows the fighter's real Fuse card when the card is on the board (an emoji only when it is not)
  await act(async () => { root.render(<StageBattles b={b} onFull={onFull} cardNode={(key, mom) => (key === 'Alpha' ? <div data-testid="real-card">{key}:{mom}</div> : null)} />); });
  expect(q('stage-fight-0').querySelector('[data-testid="stage-card-a"] [data-testid="real-card"]').textContent).toBe('Alpha:2'); expect(q('stage-fight-0').querySelector('.sbt-corner.is-b .sbt-emoji')).not.toBeNull();
  await act(async () => { q('stage-battles-full').click(); }); expect(onFull).toHaveBeenCalled();
  await act(async () => { root.render(<StageBattles b={{ pairs: [] }} onFull={onFull} />); }); expect(q('stage-battles')).toBeNull();
  await act(async () => { root.unmount(); });
});
