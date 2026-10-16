import { optWord, whoTone, bandTrack, capX, intelRows, hasIntel, aiOf, tradeBar, tickDir, CTRL_GROUPS } from './cockpitControls';

test('every control option reads as a short trader word on its segment', () => {
  expect([0, 50].map(v => optWord('agentTp', v))).toEqual(['AGENTS', '+50%']); expect(optWord('agentSl', 15)).toBe('−15%');
  expect([0, 30, 120].map(v => optWord('agentMaxHold', v))).toEqual(['AGENTS', '30m', '2h']); expect([0, 30].map(v => optWord('agentSeatTarget', v))).toEqual(['AUTO', '30s']);
  expect([0, 0.05, 0.25, 1].map(v => optWord('agentMinAgeH', v))).toEqual(['ANY', '3m', '15m', '1h']);
  expect([0, 12000].map(v => optWord('agentMcMin', v))).toEqual(['NONE', '$12K']); expect([300000, 1000000].map(v => optWord('agentMcMax', v))).toEqual(['$300K', '$1M']);
  expect(optWord('agentEntry', 'go')).toBe('GO ONLY'); expect(optWord('agentSwitch', 'aggressive')).toBe('AGGRESSIVE'); expect(optWord('agentTrail', 'auto')).toBe('AGENTS');
  expect([whoTone('CREATOR OVERRIDE'), whoTone('YOUR BAND'), whoTone('AGENTS CHOOSE')]).toEqual(['is-you', 'is-band', 'is-agents']);
  expect(CTRL_GROUPS.map(g => g[0])).toEqual(['universe', 'volume', 'germ', 'exits', 'g4', 'seats', 'gate']); expect(optWord('agentGermMax', 15)).toBe('≤ 15%'); expect(optWord('agentScale', '20/50')).toBe('+20% · 50%'); expect(CTRL_GROUPS[6][3]).toEqual(['agentGapPct', 'agentBackPct', 'agentPoolMin']); expect(CTRL_GROUPS[0][3]).toContain('agentMcMax');
});

test('the MC band sits on a log track and every real candidate is a dot (lit inside the band, green when READY)', () => {
  expect(capX(1e3)).toBe(0); expect(capX(1e6)).toBe(1); expect(capX(1e4)).toBeCloseTo(1 / 3); expect(capX(0)).toBeNull();
  const t = bandTrack(12000, 300000, [{ symbol: 'A', cap: 40000, status: 'READY' }, { symbol: 'B', price: 0.0004, supply: 1e9, status: 'CONTENDING' }, { symbol: 'C', cap: 8000 }, { symbol: 'D' }]);
  expect(t.dots).toHaveLength(3); expect(t.inside).toBe(1); expect(t.ready).toBe(1); expect(t.dots[1].cap).toBe(400000);   // cap from price × supply when the row has none
  expect(t.lo).toBeCloseTo(capX(12000)); expect(t.hi).toBeCloseTo(capX(300000)); expect(bandTrack(0, 100000, []).lo).toBe(0);
});

test("the model's trench intel reads as labelled rows, and only what it said is drawn", () => {
  const r = intelRows({ narrative: 'AI agent meta, early', creator_context: 'fresh dev, 2 launches', conflict_resolution: null });
  expect(r.map(x => [x.k, x.label])).toEqual([['narrative', 'NARRATIVE'], ['creator_context', 'CREATOR']]); expect(intelRows({})).toEqual([]); expect(intelRows(null)).toEqual([]);
  expect(hasIntel({ risk_flags: ['dev sold 40%'] })).toBe(true); expect(hasIntel({ summary: 'x' })).toBe(true); expect(hasIntel({ stance: 'NEUTRAL' })).toBe(false);
  const notes = { M: { devil: { advice: { stance: 'CAUTION' }, at: 10 }, sherlock: { advice: { stance: 'FAVOR', narrative: 'cat meta' }, at: 20 } } };
  expect(aiOf(notes, 'M').role).toBe('sherlock'); expect(aiOf(notes, 'X')).toBeNull();
});

test('the live trade bar carries now, the peak, the worst it saw and the trail; a tick has a direction', () => {
  const b = tradeBar({ entry: 1, stop: -15, take: 50, mfe: 30, mae: -6, trailAt: 15, armAt: 6 }, 1.2);
  expect(b.pct).toBeCloseTo(20); expect(b.peak).toBe(30); expect(b.giveBack).toBeCloseTo(10); expect(b.trail).toBe(15); expect(b.stop).toBe(-15);
  expect(b.lowAt).toBeLessThan(b.zero); expect(b.zero).toBeLessThan(b.trailAt); expect(b.trailAt).toBeLessThan(b.at); expect(b.at).toBeLessThan(b.peakAt); expect(b.peakAt).toBeLessThan(b.takeAt);
  expect(tradeBar({ entry: 1, stop: 10, take: 20 }, 2).at).toBeGreaterThan(0.95);                   // past the take: the bar widens, now stays on it
  expect([tickDir(1, 2), tickDir(2, 1), tickDir(1, 1), tickDir(null, 1)]).toEqual([1, -1, 0, 0]);
});

test('🛂 the buy gate counts the keeper\'s refusals by the limit that refused them; the scout reads as chips; a lab row reads in words', () => {
  const { gateCounts, scoutChips, labLine, optWord } = require('./cockpitControls');
  const g = gateCounts([{ why: 'buy price 3.1% above market (> 2.5%)' }, { why: 'live pool too thin: $2,533 liquidity < $8,000' }, { why: 'live pool too thin: $6,287' },
    { why: 'sells back for 5.0% less (> 3.5%) — tax / thin / one-way' }, { why: 'Jupiter route unavailable (HTTP 429)' }]);
  expect([g.total, g.gap, g.pool, g.back, g.route]).toEqual([5, 1, 2, 1, 1]);
  expect([optWord('agentEntry', 'armed'), optWord('agentGapPct', 0), optWord('agentGapPct', 6), optWord('agentPoolMin', 5000)]).toEqual(['ARMED', '2.5%', '≤ 6%', '$5K']);
  expect(scoutChips({ original: false, thesis: 'swarm', tech: 75 }).map(c => c[1])).toEqual(['📋 COPYCAT', '🗣 SWARM LINE', '⚙ TECH 75']);
  expect(labLine({ test: { n: 7, avg: -12, rest: -3.1 } })).toBe('unseen 7: -12.0% vs -3.1%');
  expect(labLine({ lossHits: 4 })).toBe('4 recent real losses fit it');
});

test('😴 the regret line: each check\'s held-back coins vs the coins taken, its verdict, and what the agents tuned it to', () => {
  const { regretRows } = require('./cockpitControls');
  const rows = regretRows({ record: { taken: { n: 20, med: -6 }, 'gate:gap': { n: 14, med: 12, ran: 30 }, 'gate:pool': { n: 15, med: -20, ran: 5 }, 'flow:PEAK': { n: 3, med: 4 } },
    tune: { agentGapPct: { value: 4, why: 'x' } } });
  expect(rows.map(r => [r.k, r.verdict])).toEqual([['gate:gap', 'costly'], ['gate:pool', 'right'], ['flow:PEAK', 'learning']]);
  expect(rows[0].tuned.value).toBe(4);
  expect(regretRows(null)).toEqual([]);
});

test('💰 the capital desk read: one verdict, the seat size, win vs loss bars on one scale, and where the losses come from', () => {
  const { capitalRead } = require('./cockpitControls');
  const c = capitalRead({ on: true, state: 'STEADY', mult: 0.5, why: 'w', record: { n: 30, wonPct: 57, avgWin: 15.8, avgLoss: -19.1, payoff: 0.83, expPct: 0.7, kelly: 0.04 },
    leaks: [{ rule: 'R5 stop', n: 7, sumPct: -146.8 }, { rule: 'R7 trail', n: 9, sumPct: 80 }] });
  expect([c.word, c.size, c.loss]).toEqual(['⚖ STEADY', 0.5, 1]);
  expect(c.win).toBeCloseTo(15.8 / 19.1); expect(c.line).toBe('30 real exits · 57% won · +0.7% a bet');
  expect(c.facts).toEqual(['R5 stop -146.8% over 7']);                                   // only what LOST is a leak
  expect(capitalRead({ on: false, state: 'GROW', mult: 1, record: { n: 25, avgWin: 20, avgLoss: -10 } }).size).toBeNull();   // switched off = sizes nothing
  expect(capitalRead(null).n).toBe(0);
});

test('💰 doors + 🧯 brake + 👁 trail lab reads', () => {
  const { capitalRead, trailRead } = require('./cockpitControls');
  const c = capitalRead({ on: true, state: 'STEADY', mult: 0.5, record: { n: 30, wonPct: 60, avgWin: 12, avgLoss: -10, expPct: 3 }, brake: { on: true, downPct: 18 },
    doors: { armed: { label: '🎯 armed', state: 'GROW', mult: 0.75, record: { n: 22, wonPct: 68, expPct: 6 } }, ready: { label: '⚡ ready', state: 'PROTECT', mult: 0.25, record: { n: 5, wonPct: 20, expPct: -9 } }, x: { record: { n: 0 } } } });
  expect(c.brake.downPct).toBe(18); expect(c.rug).toBeNull();
  expect(capitalRead({ on: true, state: 'PROTECT', record: { n: 30 }, rug: { on: true, rugs: 18, n: 134, avgPct: -74, capPct: 10.8 } }).rug).toBe('☠ 18 of the last 134 seats rugged (avg -74%) — a seat ≤ 10.8% of the card');
  expect(c.doors.map(d => [d.k, d.state, d.size])).toEqual([['armed', 'GROW', 0.75], ['ready', 'PROVING', null]]);   // 5 exits: not sized by its own door yet
  expect(trailRead(null).n).toBe(0); expect(trailRead({ n: 0, watching: 3 }).line).toMatch(/watching 3 exits/);
  const t = trailRead({ n: 40, need: 30, pays: true, left: 4.2, live: { arm: 4, give: 35, avg: 1.1 }, best: { arm: 8, give: 50, avg: 5.3 },
    shadow: { key: 'giveBackPct', live: 35, value: 40, n: 6, need: 20, from: 'model coach' } });
  expect(t.line).toBe('a wider trail pays +4.2% a trade'); expect(t.best.word).toBe('arm +8% · give 50%'); expect(t.shadow).toMatch(/35 → 40 · 6\/20 exits · 🧠 asked by the model/);
  expect(trailRead({ n: 9, need: 30 }).line).toBe('9 of 30 whole moves on file');
  expect(trailRead({ n: 31, need: 30, asked: { key: 'stopPct', dir: 'down', refused: 'no notch left that way' } }).asked).toMatch(/refused: no notch/);
});

test('🔥 volume limits read as short words on their buttons', () => {
  expect(optWord('agentMinVol1h', 50000)).toBe('$50K/h'); expect(optWord('agentMaxAgeH', 72)).toBe('3d'); expect(optWord('agentMaxAgeH', 6)).toBe('6h');
  expect(optWord('agentPumpTrend', 'first')).toBe('🔥 FIRST'); expect(optWord('agentPumpTrend', 'off')).toBe('OFF');
  expect(optWord('agentMcMax', 5000000)).toBe('$5M');
});

test('exit read line: graded / needed, typical move, LIVE only when proven and switched on', () => {
  const { exitLine } = require('../components/command/CockpitControls');
  const x = { rec: { RIDE: [4, 1.2, 0], TIGHTEN: [22, -3.1, 1] }, min: 20, on: 1, reads: [] };
  expect(exitLine(x)).toBe('RIDE 4/20 · +1.2% in 15m · shadow  ·  TIGHTEN 22/20 · -3.1% in 15m · ✅ LIVE');
  expect(exitLine({ ...x, on: 0 })).toContain('TIGHTEN 22/20 · -3.1% in 15m · shadow');
  expect(exitLine(null)).toBeNull();
});
