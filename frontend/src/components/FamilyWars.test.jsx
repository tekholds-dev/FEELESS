import { clockWord, tug } from './FamilyWars';

test('clockWord reads a countdown', () => {
  expect(clockWord(3 * 86400 + 3600)).toBe('3d 1h');
  expect(clockWord(3725)).toBe('1h 2m');
  expect(clockWord(42)).toBe('42s');
});

test('tug leans to the side winning, even when one side has not traded', () => {
  expect(tug({ a: { pct: 10 }, b: { pct: -10 } })).toBeGreaterThan(0.9);
  expect(tug({ a: { pct: null }, b: { pct: null } })).toBe(0.5);
  expect(tug({ a: { pct: 2 }, b: { pct: null } })).toBeGreaterThan(0.5);
});

test('🏟 an empty war room is drawn, never a bare line: the ring, who could step in (ranked by this week), how a war runs, a way in', () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  const { QuietFront } = require('./FamilyWars');
  const el = document.createElement('div'); const root = createRoot(el); const join = jest.fn();
  const rows = [{ id: 'a', tag: 'SIC', name: 'Sicario', members: 3, seats: 15, pct: 12.4 }, { id: 'b', tag: 'BNK', name: 'Bonkers', members: 5, seats: 5, pct: -3.1 }];
  act(() => root.render(<QuietFront rows={rows} note="No war on." cta={<button type="button" data-testid="war-join" onClick={join} />} />));
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('war-quiet').textContent).toContain('THE RING IS EMPTY'); expect(q('war-quiet').textContent).toContain('No war on.');
  expect(el.querySelectorAll('.fwr-contenders li')).toHaveLength(2); expect(el.querySelector('.fwr-contenders li em').textContent).toBe('+12.4%');
  expect(el.querySelector('.fwr-contenders li:nth-child(2) s').className).toBe('dn');
  expect(el.querySelectorAll('.fwr-howto li')).toHaveLength(4);
  act(() => q('war-join').click()); expect(join).toHaveBeenCalled();
  act(() => root.render(<QuietFront rows={[]} note="x" />)); expect(el.querySelector('.fwr-contenders')).toBeNull();
  act(() => root.unmount());
});
