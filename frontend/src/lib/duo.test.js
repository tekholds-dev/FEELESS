import { duoState } from './duo';

const win = (w, h, { coarse = true, segs = 1 } = {}) => ({ innerWidth: w, innerHeight: h, navigator: { viewportSegments: segs === 2 ? [{}, {}] : undefined },
  matchMedia: q => ({ matches: q.includes('pointer: coarse') ? coarse : q.includes('viewport-segments: 2') ? segs === 2 : false }) });

test('📱📱 duo = a wide touch screen or a hinge; a phone sideways = landscape; a desktop never', () => {
  expect(duoState(win(390, 844))).toEqual({ duo: false, split: false, land: false });          // a phone, upright
  expect(duoState(win(844, 390))).toEqual({ duo: true, split: false, land: true });            // the same phone, sideways
  expect(duoState(win(780, 900))).toEqual({ duo: true, split: false, land: false });           // unfolded
  expect(duoState(win(1400, 900, { coarse: false })).duo).toBe(false);                          // a laptop
  expect(duoState(win(540, 720, { segs: 2 })).split).toBe(true);                               // a hinge
});
