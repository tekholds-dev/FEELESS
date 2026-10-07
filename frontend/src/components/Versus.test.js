import { versusLine } from './ArenaPrime';

test('you vs engine: a leader is named only when the server calls one', () => {
  expect(versusLine({ lead: 'engine', gap: 1.7, you: { exits: 9 }, engine: { exits: 9 } })).toMatch(/engine is ahead by 1.7 pts/);
  expect(versusLine({ lead: 'you', gap: 0.7, you: { exits: 9 }, engine: { exits: 9 } })).toMatch(/You are ahead/);
  expect(versusLine({ lead: null, you: { exits: 2 }, engine: { exits: 9 } })).toMatch(/Needs 5 exits/);
  expect(versusLine({ lead: null, you: { exits: 9 }, engine: { exits: 9 } })).toBe('Level');
  expect(versusLine(null)).toBe('');
});

test('a paper card that picks like the owner: which cards and what the tip says', () => {
  const { humanOn, humanTip } = require('./ArenaPrime');
  const h = { tiers: ['next'], picks: 30, need: 8, ready: true, words: ['age 1h–9h (typ. 3h)'] };
  expect(humanOn({ humanStyle: h }, 'next')).toBe(true); expect(humanOn({ humanStyle: h }, 'degen')).toBe(false); expect(humanOn({}, 'next')).toBe(false);
  expect(humanTip(h)).toMatch(/last 30 picks: age 1h–9h/); expect(humanTip(h)).toMatch(/Paper only/);
  expect(humanTip({ ...h, ready: false, picks: 3, words: [] })).toMatch(/3 of 8 noted/);
});
