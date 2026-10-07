import { versusLine } from './ArenaPrime';

test('you vs engine: a leader is named only when the server calls one', () => {
  expect(versusLine({ lead: 'engine', gap: 1.7, you: { exits: 9 }, engine: { exits: 9 } })).toMatch(/engine is ahead by 1.7 pts/);
  expect(versusLine({ lead: 'you', gap: 0.7, you: { exits: 9 }, engine: { exits: 9 } })).toMatch(/You are ahead/);
  expect(versusLine({ lead: null, you: { exits: 2 }, engine: { exits: 9 } })).toMatch(/Needs 5 exits/);
  expect(versusLine({ lead: null, you: { exits: 9 }, engine: { exits: 9 } })).toBe('Level');
  expect(versusLine(null)).toBe('');
});
