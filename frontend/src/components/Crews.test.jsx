import { pctTxt, inviteLink, rankNote, costText, seatsLine, PRIZES } from './Crews';

test('crew numbers read plainly: week result, invite link and what a thin crew still needs', () => {
  expect(pctTxt(15)).toBe('+15%'); expect(pctTxt(-2.5)).toBe('-2.5%'); expect(pctTxt(null)).toBe('—');
  expect(inviteLink('https://feeless.xyz', '/terminal/leaderboard', 'ab12 cd')).toBe('https://feeless.xyz/terminal/leaderboard?lens=crews&join=ab12%20cd');
  expect(rankNote({ ranked: true, trades: 12, wonPct: 58, members: 4 })).toBe('12 trades · 58% won');
  expect(rankNote({ ranked: false, trades: 2, members: 1 })).toBe('needs 2+ members to rank'); expect(rankNote({ ranked: false, trades: 2, members: 3 })).toBe('2/5 trades to rank');
});

test('the price shows dollars and SOL, staff see free, seats read as used / bought', () => {
  const q = { free: false, create: { usd: 25, sol: 0.2165 }, seats: { usd: 5, sol: 0.0433 } };
  expect(costText(q, 'create')).toBe('$25 ≈ 0.2165 SOL'); expect(costText(q, 'seats')).toBe('$5 ≈ 0.0433 SOL');
  expect(costText({ ...q, free: true }, 'create')).toBe('free for FEELESS staff'); expect(costText({ create: { usd: 2.5, sol: null } }, 'create')).toBe('$2.50'); expect(costText(null, 'create')).toBe('');
  expect(seatsLine({ members: [1, 2, 3], seats: 5 })).toBe('3/5 seats'); expect(PRIZES).toEqual([150, 100, 60]);
});
