import { keepMessage } from './chatPrefs';

test('chat filters keep the right messages', () => {
  const call = { tokens: [{ address: 'x' }] }, plain = { tokens: [] }, ment = { mentions: ['fee'] }, t2 = { tier: 2 };
  expect(keepMessage(plain, 'all')).toBe(true);
  expect([keepMessage(call, 'calls'), keepMessage(plain, 'calls')]).toEqual([true, false]);
  expect([keepMessage(ment, 'mentions', 'fee'), keepMessage(ment, 'mentions', 'bob'), keepMessage(ment, 'mentions')]).toEqual([true, false, false]);
  expect([keepMessage(t2, 'trusted'), keepMessage(plain, 'trusted')]).toEqual([true, false]);
});
