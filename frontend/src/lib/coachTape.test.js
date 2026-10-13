import { tradeCard, tapeLine, gradeRows, coachRows, pullable, signedPct } from './coachTape';

test('🎬 a trade card says only what the records hold', () => {
  const c = tradeCard({ mint: 'A', sym: 'AAA', at: 1000, open: false, buy: { usd: 1, slipPct: 3.1, landSec: 4.2, sig: 'B1' }, why: { tag: '🤖 agents · ⚡ READY (kernel)', structure: 'UPTREND', rule: 'E12', phase: 'PRE-FOMO', size: 0.5, src: ['pump', 'calls'] },
    ai: { stance: 'CAUTION', summary: 'dev unloading', label: 'GROQ', risk_flags: ['bundled', 'no site'] }, sells: [{ sig: 'S1', usd: 1.2, why: 'R7 trail' }], result: { pct: 20, usd: 0.2, peak: 31, heldMin: 5, rule: 'R7 trail' }, judge: { kind: 'win', why: 'banked into the trail' } }, 1600);
  expect(c).toMatchObject({ tone: 'is-up', head: '+20.0%', usd: '$0.20', ago: '10m', slipBad: true, buySig: 'B1' });
  expect(c.buy).toEqual(['$1.00 in', 'filled +3.1% vs market', 'landed 4s']); expect(c.why).toEqual(['⚡ READY (kernel)', 'UPTREND', 'E12', 'phase PRE-FOMO', 'size ×0.5']);
  expect(c.ai).toMatchObject({ stance: 'CAUTION', text: 'dev unloading' }); expect(c.exit).toEqual(['R7 trail', 'held 5m', 'peak +31.0%']); expect(c.judge).toBe('✅ win · banked into the trail');
  const open = tradeCard({ mint: 'B', sym: 'BBB', at: 1590, open: true, buy: { usd: 0.5 } }, 1600);
  expect(open).toMatchObject({ tone: 'is-open', head: 'OPEN', usd: null, ai: null, judge: null }); expect(open.exit).toEqual([]);   // an open trade claims no result
  expect(tradeCard({ sym: 'L', at: 1, result: { pct: -12.34 } }).tone).toBe('is-dn'); expect(signedPct(null)).toBe('—');
});

test('the tape line, the graded lists and the coach rows', () => {
  expect(tapeLine({ n: 4, won: 1, medPct: -6.2, open: 2, medSlipPct: 1.1 })).toBe('4 closed · 1 won · typical -6.2% · 2 open · fills +1.1% vs market');
  expect(tapeLine(null)).toBe('no real agent trade yet');
  const g = gradeRows({ movers: { n: 9, med: -33, won: 1 }, pump: { n: 3, med: 6, won: 2 }, one: { n: 1, med: 50, won: 1 } }, 2);
  expect(g.map(r => r.k)).toEqual(['movers', 'pump']); expect(g[0]).toMatchObject({ tone: 'is-dn', n: 9 }); expect(g[1].tone).toBe('is-up');
  const rows = coachRows({ rules: [{ id: 1, key: 'bundled', by: 'ai', points: -4, why: 'three bundled rugs', left: 7200 }, { id: 2, key: 'crowd fomo', by: 'owner', points: -8, left: 300 }, { id: null, key: 'thin pool', by: 'judge', points: -8 }] });
  expect(rows.map(r => [r.who, r.canBack, r.canKill, r.left])).toEqual([['AI', true, true, '2h left'], ['YOU', false, true, '5m left'], ['JUDGE', false, false, null]]);
  expect(pullable([{ open: true }, { mint: 'A', pair: 'P', buying: true }, { mint: 'B', pair: 'P2', symbol: 'B' }]).map(s => s.mint)).toEqual(['B']);
});
