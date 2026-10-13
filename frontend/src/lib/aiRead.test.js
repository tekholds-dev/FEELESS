import { agreeOf, aiRows, deltaFill, agreeStats, STANCE_TONE } from './aiRead';

test('the model is read against the kernel, never instead of it', () => {
  expect(agreeOf({ stance: 'AVOID', kernel: 'READY' }).word).toBe('DISAGREES');
  expect(agreeOf({ stance: 'ENTER', kernel: 'READY' }).word).toBe('AGREES');
  expect(agreeOf({ stance: 'WAIT', kernel: 'CONTENDING' }).word).toBe('AGREES');
  expect(agreeOf({ stance: 'ENTER', kernel: 'CONTENDING' }).word).toBe('MORE EAGER');
  expect(agreeOf({ stance: 'WATCH', kernel: 'HELD' }).word).toBe('CAUTIOUS');
  expect(agreeOf({ stance: 'AVOID', kernel: 'closed -12.0%' })).toBeNull();
  expect(agreeOf({ stance: null, kernel: 'READY' })).toBeNull();
  expect(STANCE_TONE.EXIT).toBe('is-bad');
});

test('the log is newest first and filters by coin and desk', () => {
  const ai = { log: [{ at: 1, mint: 'A', role: 'devil', stance: 'WAIT', kernel: 'CONTENDING' }, { at: 3, mint: 'B', role: 'sherlock', stance: 'ENTER', kernel: 'CONTENDING' }, { at: 2, mint: 'A', role: 'sherlock', stance: 'AVOID', kernel: 'READY' }] };
  expect(aiRows(ai).map(r => r.at)).toEqual([3, 2, 1]);
  expect(aiRows(ai, { mint: 'A' }).length).toBe(2);
  expect(aiRows(ai, { role: 'devil' }).length).toBe(1);
  expect(aiRows(null)).toEqual([]);
  expect(agreeStats(ai)).toEqual({ n: 3, agree: 1, pct: 33 });
  expect(deltaFill(0.25)).toBe(1); expect(deltaFill(-0.5)).toBe(-1); expect(deltaFill('x')).toBe(0);
});
