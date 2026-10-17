// 📖 RULE LEGEND (owner, 2026-10-17: "a legend for these R10 etc — what it means and be able to tweak"): every Reaper rule code in plain words,
// whether it is HARD (always sells) or SOFT (can be asked / benched / overruled), and the 🎛 Limits control that tweaks it (null = fixed safety).
export const RULES = [
  ['R0', 'Waiting for the fill / no price yet — nothing is judged', 'info', null],
  ['R1', 'Pool pulled: liquidity under half of what it was at entry', 'hard', null],
  ['R4', 'A whale dumped while sellers lead', 'soft', null], ['R4r', 'Rug radar: creator / top holders selling, or the pool draining fast', 'hard', null],
  ['R4d', 'Drain read: holders leaving + pool shrinking + big bags', 'hard', null], ['R4e', 'Early buyers unloading', 'hard', null],
  ['R4f', 'Sellers took over the tape — banks a green seat', 'soft', 'agentTrail'], ['R4c', 'Buying climax — banks a green seat into the spike', 'soft', 'agentTrail'],
  ['R5', 'Stop line hit', 'hard', 'agentSl'], ['R5t', 'Thesis invalidated: price broke the entry support', 'soft', 'agentSl'],
  ['R5x', '−45% catastrophic floor (nobody can move it)', 'hard', null], ['R5c', 'Your creator stop', 'hard', 'agentSl'],
  ['R5g', 'Your germ stop: lost the germ floor', 'hard', null], ['R5m', 'OSSY / G4 own stop', 'hard', 'agentAiSeat'], ['R5b', 'Your half-lock banked a portion', 'hard', null],
  ['R6', 'Take-profit line hit', 'soft', 'agentTp'], ['R6h', 'Scale-out: part banked at +X%, rest rides', 'soft', 'agentScale'],
  ['R6y', 'Young coin (< 5 min at entry) all banked at +10%', 'soft', null], ['R6m', 'OSSY / G4 own take-profit', 'hard', 'agentAiSeat'],
  ['R7', 'Trailing stop: gave back part of the peak', 'soft', 'agentTrail'], ['R7v', 'Trail tightened: P&L reversing', 'soft', 'agentTrail'],
  ['R7s', 'Structure turned while green', 'soft', 'agentTrail'], ['R7b', 'Breakdown under the thesis line while green', 'soft', 'agentTrail'],
  ['R7m', 'Moon bag lost its germ floor', 'soft', 'agentMoonBag'], ['R8', 'Momentum failed for 15 min', 'soft', 'agentMaxHold'],
  ['R9', 'Time: its windows ran out', 'soft', 'agentMaxHold'], ['R9e', 'No extension earned (flat, not winning)', 'soft', 'agentMaxHold'],
  ['R9c', 'Your creator max hold', 'hard', 'agentMaxHold'], ['R10', 'Hold — nothing says sell', 'info', null],
  ['R10r', 'Riding the volume: a real crowd buying, wide trail', 'soft', 'agentTrail'], ['R11', 'Dead coin: no trades for minutes', 'soft', null],
];
export const ruleOf = code => RULES.find(r => r[0] === String(code || '').split(' ')[0]) || null;
