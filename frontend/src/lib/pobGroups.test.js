import { pobKey, pobGroups, runLabel } from './pobGroups';

test('🗂 a refile of the same game is a run inside one folder, not a folder of its own', () => {
  const rows = [{ id: 'b3', n: 3, topic: 'Thunder vs Kings team to win' }, { id: 'b2', n: 2, topic: 'Mavericks vs Celtics' }, { id: 'b1', n: 1, topic: 'file a pob Kings vs Thunder. Test this: pace' }, { id: 'b0', n: 0 }];
  expect(pobKey(rows[0])).toBe(pobKey(rows[2]));
  const g = pobGroups(rows);
  expect(g.map(x => x.runs.map(r => r.id))).toEqual([['b3', 'b1'], ['b2'], ['b0']]);
  expect(g[0].head.id).toBe('b3');
  expect(runLabel({ topic: 'Thunder vs Kings parlay slip', kalshi: { orderId: 'o', outcome: 'won' } })).toBe('Parlay slip · Kalshi WON');
});
