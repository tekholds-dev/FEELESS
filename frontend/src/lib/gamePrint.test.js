import { gameSegments, gradeMarks, marketReads, placeAt, printStage, shotPoint, statRidges, GAME_RINGS } from './gamePrint';

test('the print grows from the core to the outer ridge with the game clock', () => {
  expect(placeAt(0).ring).toBe(0); expect(placeAt(0.5).ring).toBe(GAME_RINGS / 2); expect(placeAt(1).ring).toBe(GAME_RINGS - 1); expect(placeAt(9).ring).toBe(GAME_RINGS - 1);
});
test('a score draws heavier, and every play gets its stretch', () => {
  const s = gameSegments('g', [{ id: 'a', at: 0.1, side: 'a' }, { id: 'b', at: 0.11, side: 'b', pts: 3 }]);
  expect(s).toHaveLength(2); expect(s[1].w).toBeGreaterThan(s[0].w); expect(s[1].bright).toBe(true); expect(s[0].d.startsWith('M')).toBe(true);
});
test('it is only FINAL after the horn and every grade', () => {
  expect(printStage('pre', [])).toBe('pre'); expect(printStage('in', [{ won: true }])).toBe('live');
  expect(printStage('post', [{ won: null }])).toBe('grading'); expect(printStage('post', [{ won: true }, { won: false }])).toBe('final'); expect(printStage('post', [])).toBe('final');
});
test('grades mark right and wrong', () => {
  const m = gradeMarks('g', [{ won: true }, { won: false }]); expect(m[0].ink).not.toBe(m[1].ink); expect(gradeMarks('g', [])).toEqual([]);
});
test('a stat with no last season inks only this season', () => {
  const [a, b] = statRidges('t', [{ abbr: 'PTS', now: 80, last: null, score: 50 }, { abbr: 'REB', now: 30, last: 28, score: 60 }]); expect(a.last).toBeNull(); expect(b.last).toBeTruthy();
});
test('away shots land on the left basket and home on the right', () => {
  expect(shotPoint({ x: 25, y: 5, side: 'a' })[0]).toBeLessThan(94); expect(shotPoint({ x: 25, y: 5, side: 'b' })[0]).toBeGreaterThan(94);
});
test('markets disagreeing is read only past 2 points', () => {
  expect(marketReads({}, {}, { short: 'V', chance: 0.9, kalshi: 0.85 })[0].k).toBe('MARKETS DISAGREE'); expect(marketReads({}, {}, { chance: 0.9, kalshi: 0.89 })).toEqual([]);
});
