import { brainLine, PICK_LENSES } from './ArenaPrime';

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
  expect(PICK_LENSES.map(x => x[0])).toContain('brain');
});
