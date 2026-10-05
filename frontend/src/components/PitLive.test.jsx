
test('six duels: a spark per seat won, the leader is lit, Overload / Live Wire / Blown Fuse come from the numbers', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { DuelBoard } = require('./PitLive');
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  const seat = (n, a, b, win) => ({ seat: n, a: { symbol: `A${n}`, pct: a }, b: { symbol: `B${n}`, pct: b, sub: n === 2 }, win, gap: Math.abs(a - b) });
  const p = { a: { name: 'Blaze', emoji: '🔥' }, b: { name: 'Beta', emoji: '🌐' },
    duels: { a: 2, b: 1, seats: [seat(1, 5, 3, 'a'), seat(2, -2, 4, 'b'), seat(3, 1, -3, 'a'), seat(4, 0, 0.02, null)], liveWire: { symbol: 'A1', pct: 5, side: 'a' }, blownFuse: { symbol: 'A2', pct: -2, side: 'a', gap: 6 }, overload: null } };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<DuelBoard p={p} />); });
  const rows = [...el.querySelectorAll('.pl-seats li')];
  expect(rows.map(r => r.className)).toEqual(['is-a', 'is-b', 'is-a', 'is-tie']);
  expect(el.querySelector('.pl-score .is-lead').textContent).toContain('2');
  expect(rows[1].textContent).toContain('$B2 ⇄');                                       // a coin subbed in mid-game is marked
  expect(el.textContent).toContain('Live Wire $A1 +5.0%'); expect(el.textContent).toContain('Blown Fuse $A2');
  expect(el.textContent).not.toContain('OVERLOAD');
  const el2 = document.createElement('div'); document.body.appendChild(el2);
  await act(async () => { createRoot(el2).render(<DuelBoard p={{ ...p, duels: { ...p.duels, overload: 'a' } }} />); });
  expect(el2.textContent).toContain('OVERLOAD — Blaze');
  const el3 = document.createElement('div'); document.body.appendChild(el3);
  await act(async () => { createRoot(el3).render(<DuelBoard p={{ ...p, duels: null }} />); });
  expect(el3.querySelector('[data-testid="pit-duels"]')).toBeNull();                    // a fight from before the rule shows no board
});
