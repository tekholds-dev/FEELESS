import { pobKey, pobGroups, runLabel, gameName, sameGame } from './pobGroups';

const T = 1794788221; const okc = [{ id: '401909993' }];
test('🗂 every PoB on the same real game is a reading in one file; a rematch another day is a new file', () => {
  const rows = [
    { id: 'b4', n: 4, at: T + 900, topic: 'Thunder vs Kings parlay slip' },                       // no scoreboard yet: same teams, same day
    { id: 'b3', n: 3, at: T + 600, topic: 'OKC Sacramento', games: okc },                        // other words, same ESPN game
    { id: 'b2', n: 2, at: T + 300, topic: 'Mavericks vs Celtics', games: [{ id: '401909989' }] },
    { id: 'b1', n: 1, at: T, topic: 'Thunder vs Kings team to win', games: okc },
    { id: 'b0', n: 0, at: T - 7 * 86400, topic: 'Thunder vs Kings', games: [{ id: '401900001' }] }, // last week's game
    { id: 'bx', n: 9, at: T },                                                                     // the free-chip board: its own file
  ];
  expect(pobKey(rows[3])).toBe('kings thunder');
  const g = pobGroups(rows);
  expect(g.map(x => x.runs.map(r => r.id))).toEqual([['b4', 'b3', 'b1'], ['b2'], ['b0'], ['bx']]);
  expect(g[0].head.id).toBe('b4'); expect(g[0].key).toBe('b1');
  expect(sameGame(rows[3], rows[4])).toBe(false);
  expect(gameName(rows[3])).toBe('Thunder vs Kings'); expect(gameName({ topic: 'file a pob 49ers vs Cowboys. Test this' })).toBe('49ers vs Cowboys');
  expect(runLabel({ topic: 'Thunder vs Kings parlay slip', kalshi: { orderId: 'o', outcome: 'won' } })).toBe('Parlay slip · Kalshi WON');
});
