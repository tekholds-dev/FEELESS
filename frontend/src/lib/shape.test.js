import { shaped } from './shape';

test('every default key is there, wrong kinds fall back, one nested level is filled, extras pass through', () => {
  const s = shaped({ rows: [], counts: { bot: 0, clean: 0 }, total: 0, name: '' });
  expect(s({})).toEqual({ rows: [], counts: { bot: 0, clean: 0 }, total: 0, name: '' });
  expect(s(null)).toEqual(s(undefined));
  expect(s([1, 2])).toEqual(s({}));
  expect(s({ rows: { a: 1 }, counts: { bot: 3 }, total: NaN, extra: 7 })).toEqual({ rows: [], counts: { bot: 3, clean: 0 }, total: 0, name: '', extra: 7 });
  expect(s({ rows: [1], total: 5, name: 'x' }).rows).toEqual([1]);
});
