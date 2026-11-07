import { deskSet, iconsOnPage } from './DeskShell';

const win = (over = {}) => ({ open: true, min: false, max: false, x: 10, y: 10, ...over });

describe('windows and folders stay on the page', () => {
  test('a folder past any edge shows in a free cell inside the page, and a good spot stays', () => {
    const got = iconsOnPage({ a: { x: 0, y: 0 }, b: { x: 3000, y: 96 }, c: { x: 0, y: 2000 }, d: { x: -96, y: -96 } }, 800, 600, 96);
    expect(got.a).toEqual({ x: 0, y: 0 });
    Object.values(got).forEach(p => { expect(p.x).toBeGreaterThanOrEqual(0); expect(p.x + 116).toBeLessThanOrEqual(800); expect(p.y).toBeGreaterThanOrEqual(0); expect(p.y + 162).toBeLessThanOrEqual(600); });
    expect(new Set(Object.values(got).map(p => `${p.x},${p.y}`)).size).toBe(4);
  });

  test('taking a half sends the other open window to the other half', () => {
    const n = deskSet({ a: win(), b: win(), c: win({ open: false }) }, 'a', { tile: 'left' });
    expect(n.a.tile).toBe('left'); expect(n.b.tile).toBe('right'); expect(n.c.tile).toBeUndefined();
  });

  test('the next folder opened fills the empty half, and a third floats', () => {
    let n = deskSet({ a: win(), b: win({ open: false }), c: win({ open: false }) }, 'a', { tile: 'right' });
    n = deskSet(n, 'b', { open: true, min: false }); expect(n.b.tile).toBe('left');
    n = deskSet(n, 'c', { open: true, min: false }); expect(n.c.tile).toBeFalsy();
  });

  test('swapping sides, filling the screen and closing all leave no stale half', () => {
    let n = deskSet({ a: win({ tile: 'left' }), b: win({ tile: 'right' }) }, 'a', { tile: 'right' });
    expect(n.a.tile).toBe('right'); expect(n.b.tile).toBeNull();
    n = deskSet(n, 'a', { max: true }); expect(n.a.tile).toBeNull(); expect(n.a.max).toBe(true);
    n = deskSet({ a: win({ tile: 'left' }) }, 'a', { open: false }); expect(n.a.tile).toBeNull();
  });
});
