// 🎛 a cockpit payload for tests: the real card's seats, Reaper's positions, kernel candidates, the decision tape, the owner's review list
export const PUMP = 'So1anaCoinMint1111111111111111111111111pump';
export const D = {
  card: { seats: [
    { symbol: 'CARLO', mint: PUMP, pair: 'P1', kind: 'agent', tag: '🤖 agents', buying: false, pct: 17.3, take: 50, action: 'hold' },
    { symbol: 'BEAR', mint: 'MINTBEAR', pair: 'P2', kind: 'agent', buying: true, pct: null },
    { symbol: null, kind: 'open' }] },
  office: {
    positions: [{ mint: PUMP, pair: 'P1', symbol: 'CARLO', entry: 0.000857, px: 0.001006, pct: 17.39, peak: 20.1, usd: 0.42, heldMin: 4, decision: 'PROTECT', rule: 'R7 trail', evidence: 'peak +20% — trail armed', take: 50, stop: -15,
      supply: 1e9, supplySrc: 'launchpad', exec: 'confirmed', fills: [{ at: 1000, side: 'buy', px: 0.000857, usd: 0.36 }] }],
    seatBoard: [{ seat: 2, mint: 'MINTBEAR', symbol: 'BEAR', buying: true, result: 'HOLD', rule: 'R0 waiting for the fill', why: 'the buy is not confirmed on the ledger yet' }],
    kernel: { candidates: [
      { mint: 'MINTZYN', symbol: 'ZYN', pair: 'P3', status: 'READY', rank: 180, why: 'HOT EARLY MOVE — +12% on 4× pace', trigger: 'ENTER', narrative: 'HOT EARLY MOVE', devil: [['identity', 'WARNING', 'no site']], size: 0.85, sizeWhy: 'newborn', courier: true, unknown: ['early wallets'], price: 0.0004, supply: 1e9, ageMin: 3, vol5m: 9000, move5m: 12, buyShare: 64, liq: 21000 },
      { mint: 'MINTPLAIN', symbol: 'PLAIN', pair: 'P4', status: 'CONTENDING', rank: 90, why: 'BUILDING — rank 90', trigger: 'ARM', devil: [], courier: true, unknown: [], price: 0.002, ageMin: 40 },
      { mint: 'MINTOLD', symbol: 'OLD', pair: 'P5', status: 'TRACKING', rank: 20, trigger: 'NO', devil: [['wall', 'HARD_VETO', 'collapsing']], hard: true, ageMin: null }] },
    tape: [{ id: 1, at: 990, agent: 'trigger', action: 'ENTER', why: 'reclaim', mint: PUMP, symbol: 'CARLO', mc: 850000 },
      { id: 3, at: 1010, agent: 'reaper', action: 'PROTECT', why: 'R7 trail — peak +20%', mint: PUMP, symbol: 'CARLO' },
      { id: 2, at: 1001, agent: 'courier', action: 'FILLED BUY', why: '$0.36', mint: PUMP, symbol: 'CARLO', result: { state: 'filled' } },
      { id: 4, at: 1020, agent: 'devil', action: 'HARD VETO', why: 'collapsing', mint: 'MINTOLD', symbol: 'OLD' }],
    ownerReview: [{ mint: 'MINTREV', symbol: 'REV', mode: 'track', state: 'RESOLVING', why: 'waiting for the next agent pass', pending: ['market'] }],
    mission: { putIn: 32.5, value: 1.88, toBreakeven: -30.62, needX: 17.3, phase: 'RECOVERY', breakevenTarget: 32.5, lives: 7, livesOf: 9, nextDutyIn: 480,
      lastAction: { at: 1000, move: 'fill', sym: 'CARLO', usd: 0.36, why: 'agents filled seat 1', result: { state: 'confirmed' } } },
    ops: { office: 'LIVE', keeper: '1 active', cash: 1.02, execution: 'HEALTHY' },
    execution: { health: 'HEALTHY', why: ['14 of 18 sends confirmed this hour'], sends: 18, fills: 14 },
    cycle: { every: 30, nextIn: 18, at: 1000, read: 62 },
    policy: { manual: false, controls: [{ key: 'agentTp', label: 'Take profit', value: 0, options: [0, 20, 50], unit: '%', who: 'AGENTS CHOOSE', means: 'agents choose the take line' },
      { key: 'agentSl', label: 'Stop loss', value: 25, options: [0, 15, 25], unit: '%', who: 'CREATOR OVERRIDE', means: 'your stop ceiling' }] },
  },
};

