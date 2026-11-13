import { FRAMES, FRAME_KEYS, alpha, cropFor, fitInto, frameLayers, history, push, redo, reframe, reorder, undo, KEEP_STEPS } from './pocPlay';

const T = { bg: 'b', text: 't', accent: 'a', accentInk: 'ai', dim: 'd', ink: 'i', line: 'l', shade: 's', clear: 'c', sky: 'k', glow: 'g', note: 'n', noteInk: 'ni' };
const IMG = { src: '/x.png', w: 2000, h: 1000 };

test('🎨 every frame builds: locked decor under, one movable main picture that stays inside the frame', () => {
  expect(FRAME_KEYS).toEqual(['free', 'post', 'story', 'thumb', 'phone', 'billboard', 'shelf', 'launch', 'ideas']);
  for (const k of FRAME_KEYS) {
    const ls = frameLayers(k, IMG, T); const F = FRAMES[k]; const main = ls.filter(l => l.main);
    expect(main).toHaveLength(1); expect(main[0].deco).toBeFalsy();
    expect(main[0].x).toBeGreaterThanOrEqual(-0.01); expect(main[0].y).toBeGreaterThanOrEqual(-0.01);
    expect(main[0].x + main[0].width).toBeLessThanOrEqual(F.w + 0.01); expect(main[0].y + main[0].height).toBeLessThanOrEqual(F.h + 0.01);
    expect(ls[0].deco).toBe(true);                                                    // the backdrop is first and locked
    expect(JSON.stringify(ls)).not.toMatch(/#[0-9a-f]{3,8}\b/i);                     // colours only from the page tokens
  }
  expect(frameLayers('post', null, T).some(l => l.main)).toBe(false);               // no picture yet: the frame still draws
});

test('🎨 the shelf stands the product ON the shelf; ideas puts five notes round it', () => {
  const m = frameLayers('shelf', IMG, T).find(l => l.main); expect(m.y + m.height).toBeCloseTo(878);
  expect(frameLayers('ideas', IMG, T).filter(l => l.type === 'note')).toHaveLength(5);
});

test('🎨 fit and crop never stretch the picture', () => {
  const c = fitInto(2000, 1000, 0, 0, 500, 500); expect(c.width / c.height).toBeCloseTo(2); expect(c.y).toBeCloseTo(125);
  const v = fitInto(2000, 1000, 0, 0, 500, 500, 'cover'); expect(v.height).toBeCloseTo(500); expect(v.width).toBeCloseTo(1000);
  const k = cropFor(2000, 1000, 1); expect(k).toEqual({ x: 500, y: 0, width: 1000, height: 1000 });
  expect(cropFor(1000, 2000, 16 / 9).height).toBeCloseTo(562.5); expect(cropFor(0, 0, 1)).toEqual({ x: 0, y: 0, width: 0, height: 0 });
});

test('🎨 undo / redo walk the steps, a new edit drops the redo trail, and only 60 steps are kept', () => {
  let h = history([]); h = push(h, [1]); h = push(h, [1, 2]);
  h = undo(h); expect(h.now).toEqual([1]); h = redo(h); expect(h.now).toEqual([1, 2]);
  h = undo(h); h = push(h, [9]); expect(h.future).toEqual([]); expect(undo(undo(undo(h))).now).toEqual([]);
  for (let i = 0; i < 100; i += 1) h = push(h, [i]);
  expect(h.past).toHaveLength(KEEP_STEPS); expect(push(h, h.now)).toBe(h);
});

test('🎨 layers move up / down / front / back but never under the locked decor', () => {
  const ls = [{ id: 'bg', deco: true }, { id: 'a' }, { id: 'b' }, { id: 'c' }];
  expect(reorder(ls, 'a', 'front').map(l => l.id)).toEqual(['bg', 'b', 'c', 'a']);
  expect(reorder(ls, 'c', 'back').map(l => l.id)).toEqual(['bg', 'c', 'a', 'b']);
  expect(reorder(ls, 'a', 'down')).toBe(ls); expect(reorder(ls, 'b', 'up').map(l => l.id)).toEqual(['bg', 'a', 'c', 'b']);
});

test('🎨 a frame change keeps what you added and rebuilds the frame', () => {
  const mine = { id: 'u1', type: 'text', user: true, text: 'mine' };
  const out = reframe([...frameLayers('post', IMG, T), mine], 'phone', IMG, T);
  expect(out.at(-1)).toBe(mine); expect(out.filter(l => l.main)).toHaveLength(1); expect(out.some(l => l.text === 'Your caption here')).toBe(false);
});

test('🎨 a token colour at an opacity for the canvas (it cannot read color-mix)', () => {
  expect(alpha('#19e68c', 0.2)).toBe('rgba(25,230,140,0.2)'); expect(alpha('#fff', 1)).toBe('rgba(255,255,255,1)');
  expect(alpha('rgb(1, 2, 3)', 0.5)).toBe('rgba(1,2,3,0.5)'); expect(alpha('', 0.5)).toBe('rgba(0,0,0,.2)');
});
