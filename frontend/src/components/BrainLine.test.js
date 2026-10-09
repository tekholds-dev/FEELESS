import { brainLine, stopsLine, PICK_LENSES } from './ArenaPrime';

test('trench brain line: learning, then judged with its proof', () => {
  expect(brainLine(null)).toMatch(/Learning — 0 trench coins/);
  expect(brainLine({ n: 0, open: 12, tp: 50, sl: 30 })).toMatch(/12 trench coins being watched.*\+50%.*−30%/);
  const b = { n: 200, open: 90, tp: 50, sl: 30, how: { hit: 50, cut: 120 }, proof: { n: 80, top: 12, bottom: -30 }, ready: true,
    lessons: { best: [{ cell: 'soc:site+x & top10:<15', med: 22, n: 14 }] } };
  const s = brainLine(b);
  expect(s).toMatch(/200 judged · 25% hit \+50% first · watching 90/);
  expect(s).toMatch(/top third played \+12% vs bottom -30%/);
  expect(s).toMatch(/PROVEN/);
  expect(s).toMatch(/soc:site\+x & top10:<15 → \+22% \(n 14\)/);
  expect(brainLine({ ...b, ready: false })).toMatch(/still learning, a list only/);
  expect(PICK_LENSES.map(x => x[0])).toEqual(expect.arrayContaining(['live', 'trench']));
  expect(PICK_LENSES.map(x => x[0])).not.toContain('brain');   // the brain lives inside the trench tab
});

test('stops line: every ticket stop replayed on the same paths, the learned one named', () => {
  expect(stopsLine(null)).toBe('');
  const st = { best: 50, by: { 30: { n: 40, avg: -12.5, shook: 6 }, 50: { n: 40, avg: 3.1, shook: 1 }, 0: { n: 40, avg: -8, shook: 0 } } };
  const s = stopsLine(st);
  expect(s).toMatch(/replayed on 40 coins/); expect(s).toMatch(/−30% -12.5% \(6 shaken out, then ran\)/); expect(s).toMatch(/tickets use −50% 🧠/);
  expect(stopsLine({ ...st, best: null })).toMatch(/needs 30 coins/);
});
