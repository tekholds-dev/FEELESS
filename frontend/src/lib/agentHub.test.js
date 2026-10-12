import { selectors, freshness } from './agentHub';

test('one store, normalized selectors: agent · mint · seat · hunter · position · bench · metrics', () => {
  const d = { office: { at: 100, agents: [{ key: 'reaper', name: 'Reaper' }], generations: [{ role: 'reaper', generation: 2, status: 'ACTIVE' }],
    kernel: { lanes: [{ lane: 1, state: 'HUNTING' }], candidates: [{ mint: 'M', symbol: 'M', decidedAgo: 3 }], metrics: { mints: 9 } },
    seatBoard: [{ seat: 1, empty: true }], positions: [{ mint: 'P' }], bench: [{ mint: 'B' }], rpcStats: { logical: 10, physical: 7, saved: 3 } } };
  const s = selectors(d, 130);
  expect(s.getAgent('reaper').generation.generation).toBe(2); expect(s.getMint('M').symbol).toBe('M'); expect(s.getCandidate('X')).toBeNull();
  expect(s.getSeat(1).empty).toBe(true); expect(s.getHunter(1).state).toBe('HUNTING'); expect(s.getPosition('P')).toEqual({ mint: 'P' });
  expect(s.getBench()).toHaveLength(1); expect(s.getMetrics().rpc.saved).toBe(3); expect(s.snapshotAge()).toBe(30);
});

test('market freshness and decision freshness are kept apart', () => {
  const f = freshness({ decidedAgo: 45, ages: { price: 50, research: 300 } }, { at: Date.now() - 2000 });
  expect(f.market).toBe(2); expect(f.decision).toBe(45); expect(f.research).toBe(300);
});
