import { duoState } from './duo';

const win = (w, h, { coarse = true, segs = 1 } = {}) => ({ innerWidth: w, innerHeight: h, navigator: { viewportSegments: segs === 2 ? [{}, {}] : undefined },
  matchMedia: q => ({ matches: q.includes('pointer: coarse') ? coarse : q.includes('viewport-segments: 2') ? segs === 2 : false }) });

test('📱📱 duo = a wide touch screen or a hinge; a phone sideways = landscape; a desktop never', () => {
  expect(duoState(win(390, 844))).toEqual({ duo: false, split: false, land: false, wide: false });          // a phone, upright
  expect(duoState(win(844, 390))).toEqual({ duo: true, split: false, land: true, wide: true });            // the same phone, sideways
  expect(duoState(win(780, 900))).toEqual({ duo: true, split: false, land: false, wide: false });   // unfolded, upright
  expect(duoState(win(890, 626))).toEqual({ duo: true, split: false, land: false, wide: true });    // iPhone Duo open, wide (one slim bar, crease split)
  expect(duoState(win(626, 890))).toMatchObject({ duo: true, wide: false });                        // iPhone Duo open, upright
  expect(duoState(win(466, 678)).duo).toBe(false);                                                  // iPhone Duo folded = a phone
  expect(duoState(win(1400, 900, { coarse: false })).duo).toBe(false);                          // a laptop
  expect(duoState(win(540, 720, { segs: 2 })).split).toBe(true);                               // a hinge
});
