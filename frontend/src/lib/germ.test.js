import { germView } from './germ';

test('germ view: on the floor with 5m agreeing is hot, past the line is "ran off", under the floor is lost', () => {
  const hot = germView({ d: 3, w: 'floor', d5: 6, w5: 'floor', e: 'confirmed', line: 15, ok: true, run: 80 });
  expect(hot.tone).toBe('hot');
  expect(hot.word).toBe('ON THE GERM');
  expect(hot.tip).toMatch(/inside your 15% germ line/);
  expect(hot.fill).toBeCloseTo(0.8);
  expect(germView({ d: 12, w: 'near', line: 15, ok: true }).tone).toBe('near');
  const far = germView({ d: 40, w: 'far', line: 15, ok: false });
  expect(far.tone).toBe('far');
  expect(far.tip).toMatch(/won't buy it here/);
  expect(germView({ d: -6, w: 'lost', line: 15 }).tone).toBe('lost');
  expect(germView(null)).toBeNull();
  expect(germView({ w: 'floor' })).toBeNull();
});

test('germWhy explains the germ for this coin in three lines', () => {
  const { germWhy } = require('./germ');
  const w = germWhy({ d: 4, w: 'floor', d5: 6, run: 120, sym: 'DOG', line: 15, ok: true });
  expect(w.lines).toHaveLength(3);
  expect(w.lines[0]).toContain('+120%'); expect(w.lines[1]).toContain('$DOG'); expect(w.lines[1]).toContain('agrees');
  expect(germWhy({ d: -5, w: 'lost' }).lines[1]).toContain('UNDER');
  expect(germWhy(null)).toBeNull();
});
