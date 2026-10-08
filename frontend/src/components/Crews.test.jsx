import { pctTxt, inviteLink, rankNote } from './Crews';

test('crew numbers read plainly: week result, invite link and what a thin crew still needs', () => {
  expect(pctTxt(15)).toBe('+15%'); expect(pctTxt(-2.5)).toBe('-2.5%'); expect(pctTxt(null)).toBe('—');
  expect(inviteLink('https://feeless.xyz', '/terminal/leaderboard', 'ab12 cd')).toBe('https://feeless.xyz/terminal/leaderboard?lens=crews&join=ab12%20cd');
  expect(rankNote({ ranked: true, trades: 12, wonPct: 58, members: 4 })).toBe('12 trades · 58% won');
  expect(rankNote({ ranked: false, trades: 2, members: 1 })).toBe('needs 2+ members to rank'); expect(rankNote({ ranked: false, trades: 2, members: 3 })).toBe('2/5 trades to rank');
});
