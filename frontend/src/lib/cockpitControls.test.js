import { optWord, whoTone, bandTrack, capX, vitalRows, hasVitals, aiOf, tradeBar, tickDir, TIMING_TONE, CTRL_GROUPS } from './cockpitControls';

test('every control option reads as a short trader word on its segment', () => {
  expect([0, 50].map(v => optWord('agentTp', v))).toEqual(['AGENTS', '+50%']); expect(optWord('agentSl', 15)).toBe('−15%');
  expect([0, 30, 120].map(v => optWord('agentMaxHold', v))).toEqual(['AGENTS', '30m', '2h']); expect([0, 30].map(v => optWord('agentSeatTarget', v))).toEqual(['AUTO', '30s']);
  expect([0, 0.05, 0.25, 1].map(v => optWord('agentMinAgeH', v))).toEqual(['ANY', '3m', '15m', '1h']);
  expect([0, 12000].map(v => optWord('agentMcMin', v))).toEqual(['NONE', '$12K']); expect([300000, 1000000].map(v => optWord('agentMcMax', v))).toEqual(['$300K', '$1M']);
  expect(optWord('agentEntry', 'go')).toBe('GO ONLY'); expect(optWord('agentSwitch', 'aggressive')).toBe('AGGRESSIVE'); expect(optWord('agentTrail', 'auto')).toBe('AGENTS');
  expect([whoTone('CREATOR OVERRIDE'), whoTone('YOUR BAND'), whoTone('AGENTS CHOOSE')]).toEqual(['is-you', 'is-band', 'is-agents']);
  expect(CTRL_GROUPS.map(g => g[0])).toEqual(['universe', 'exits', 'seats']); expect(CTRL_GROUPS[0][3]).toContain('agentMcMax');
});

test('the MC band sits on a log track and every real candidate is a dot (lit inside the band, green when READY)', () => {
  expect(capX(1e3)).toBe(0); expect(capX(1e6)).toBe(1); expect(capX(1e4)).toBeCloseTo(1 / 3); expect(capX(0)).toBeNull();
  const t = bandTrack(12000, 300000, [{ symbol: 'A', cap: 40000, status: 'READY' }, { symbol: 'B', price: 0.0004, supply: 1e9, status: 'CONTENDING' }, { symbol: 'C', cap: 8000 }, { symbol: 'D' }]);
  expect(t.dots).toHaveLength(3); expect(t.inside).toBe(1); expect(t.ready).toBe(1); expect(t.dots[1].cap).toBe(400000);   // cap from price × supply when the row has none
  expect(t.lo).toBeCloseTo(capX(12000)); expect(t.hi).toBeCloseTo(capX(300000)); expect(bandTrack(0, 100000, []).lo).toBe(0);
});

test("the model's vitals read as meters — rug inverted — and only what it said is drawn", () => {
  const r = vitalRows({ vitals: { rug: 80, narrative: 70, crowd: 20, momentum: 45 } });
  expect(r.map(x => [x.k, x.tone])).toEqual([['rug', 'is-bad'], ['narrative', 'is-good'], ['crowd', 'is-bad'], ['momentum', 'is-warn']]);
  expect(vitalRows({ vitals: { rug: 10 } })[0].tone).toBe('is-good'); expect(vitalRows({})).toEqual([]); expect(vitalRows({ vitals: { rug: null } })).toEqual([]);
  expect(hasVitals({ timing: 'EARLY' })).toBe(true); expect(hasVitals({ stance: 'WAIT' })).toBe(false); expect(TIMING_TONE.CHASE).toBe('is-bad');
  const notes = { M: { devil: { advice: { stance: 'WAIT' }, at: 10 }, sherlock: { advice: { stance: 'WATCH', vitals: { rug: 40 } }, at: 20 } } };
  expect(aiOf(notes, 'M').role).toBe('sherlock'); expect(aiOf(notes, 'X')).toBeNull();
});

test('the live trade bar carries now, the peak, the worst it saw and the trail; a tick has a direction', () => {
  const b = tradeBar({ entry: 1, stop: -15, take: 50, mfe: 30, mae: -6, trailAt: 15, armAt: 6 }, 1.2);
  expect(b.pct).toBeCloseTo(20); expect(b.peak).toBe(30); expect(b.giveBack).toBeCloseTo(10); expect(b.trail).toBe(15); expect(b.stop).toBe(-15);
  expect(b.lowAt).toBeLessThan(b.zero); expect(b.zero).toBeLessThan(b.trailAt); expect(b.trailAt).toBeLessThan(b.at); expect(b.at).toBeLessThan(b.peakAt); expect(b.peakAt).toBeLessThan(b.takeAt);
  expect(tradeBar({ entry: 1, stop: 10, take: 20 }, 2).at).toBeGreaterThan(0.95);                   // past the take: the bar widens, now stays on it
  expect([tickDir(1, 2), tickDir(2, 1), tickDir(1, 1), tickDir(null, 1)]).toEqual([1, -1, 0, 0]);
});
