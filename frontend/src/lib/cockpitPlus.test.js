import { ghostMarkers, rugMark, diamondOf, leagueOf, answerCard, rideCard } from './cockpitPlus';

test('would-sell ghosts sit at the price the agents would have sold', () => {
  const m = ghostMarkers({ entry: 1, ghosts: [{ at: 100, pct: 10, rule: 'R7' }] });
  expect(m[0]).toMatchObject({ time: 100, text: '✂', price: 1.1, action: 'WOULD SELL +10.0%' });
  expect(ghostMarkers({ ghosts: [{ at: 1, pct: 1 }] })).toEqual([]);
});
test('the rug marker lights only when the pool starts draining', () => {
  expect(rugMark({ open: false, drain: { state: 'DRAIN', why: ['holders leaving'] } }).level).toBe('bad');
  expect(rugMark({ open: false, liqPct: 82 }).level).toBe('warn');
  expect(rugMark({ open: false, liqPct: 98 })).toBeNull(); expect(rugMark({ open: true, liqPct: 10 })).toBeNull();
});
test('diamond hands = your result minus the agents first would-sell, on your closed trades only', () => {
  const rows = [{ who: 'you', sym: 'ELON', result: { pct: 120 }, replay: { would: [{ pct: 3.4 }] } }, { who: 'you', sym: 'X', result: { pct: -20 }, replay: { would: [{ pct: -5 }] } },
    { who: 'agents', result: { pct: 50 }, replay: { would: [{ pct: 1 }] } }];
  const d = diamondOf(rows);
  expect(d.n).toBe(2); expect(d.best.sym).toBe('ELON'); expect(d.won).toBe(1); expect(Math.round(d.avg * 10) / 10).toBe(50.8);
  expect(diamondOf([])).toEqual({ n: 0 });
});
test('the G4 vs OSSY league names who leads', () => {
  expect(leagueOf({ rec: { G4: { n: 3, won: 67, med: 2 }, OSSY: { n: 2, won: 50, med: -1 } } }).lead).toBe('G4');
  expect(leagueOf({}).word).toBe('no closed paper trades yet');
});
test('a long answer becomes a card with its number first and the coins it names', () => {
  const c = answerCard('Holding paid. The agents would have sold $ELON at +3.4% but you held to +128%. Your losers bleed longer. Tighten stops on red seats. sources: x');
  expect(c.head).toContain('+3.4%'); expect(c.coins).toEqual(['ELON']); expect(c.bullets.length).toBeLessThanOrEqual(3);
  expect(answerCard('yo')).toBeNull();
});
test('a held seat becomes a ride share card', () => {
  const c = rideCard({ symbol: 'ELON', pct: 116, pnlUsd: 0.16, peak: 128, kind: 'yours', entryMc: 203600, mc: 440400, heldMin: 170 }, { ghosts: [{ pct: 3.4, rule: 'R4r' }] });
  expect(c.title).toBe('$ELON ride'); expect(c.lines[1]).toContain('+3.4%'); expect(c.theme).toBe('gold'); expect(c.bigSub).toBeUndefined();
  expect(rideCard({ symbol: 'A', pct: 40, pnlUsd: 0.06, usd: 0.19, path: [0, 50, 128, 40] }, { ghosts: [{ pct: 36 }] })).toMatchObject({ spark: [0, 50, 128, 40], marks: [36] });
  expect(rideCard({ symbol: 'A', pct: 40, pnlUsd: 0.06, usd: 0.19 }).lines[0]).toBe('$0.13 in → $0.19 now (+$0.06)');
  expect(rideCard({ open: true })).toBeNull();
});

test('a ride card carries the hazard design fields and the hazard design is offered', () => {
  const c = rideCard({ symbol: 'ELON', pct: -12, pnlUsd: -0.2, usd: 1.5, kind: 'agents', entryMc: 50000, mc: 44000, heldMin: 9, path: [0, -3, -12] }, {});
  expect(c.trade).toMatchObject({ sym: 'ELON', side: 'AGENTS', held: '9m', entry: '$50K', exit: '$44K', bonus: '−$0.20', bonusUnit: 'lost' });
  expect(require('./shareGif').DESIGNS[0][0]).toBe('hazard');
});
