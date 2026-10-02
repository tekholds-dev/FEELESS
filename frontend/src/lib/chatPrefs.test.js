import { keepMessage } from './chatPrefs';

test('chat filters keep the right messages', () => {
  const call = { tokens: [{ address: 'x' }] }, plain = { tokens: [] }, ment = { mentions: ['fee'] }, t2 = { tier: 2 };
  expect(keepMessage(plain, 'all')).toBe(true);
  expect([keepMessage(call, 'calls'), keepMessage(plain, 'calls')]).toEqual([true, false]);
  expect([keepMessage(ment, 'mentions', 'fee'), keepMessage(ment, 'mentions', 'bob'), keepMessage(ment, 'mentions')]).toEqual([true, false, false]);
  expect([keepMessage(t2, 'trusted'), keepMessage(plain, 'trusted')]).toEqual([true, false]);
});

test('dead or rugged calls leave the room; live calls and plain messages stay', () => {
  const { deadCall } = require('./chatPrefs');
  const live = { pair: { pairAddress: 'P' }, priceUsd: 1 };
  expect(deadCall({ tokens: [{ symbol: 'ZKL' }] }, [])).toBe(true);                                  // no market at all
  expect(deadCall({ tokens: [live] }, [{ pairAddress: 'P', x: 0.05 }])).toBe(true);                   // −95% since posted
  expect(deadCall({ tokens: [live] }, [{ pairAddress: 'P', x: 1.4 }])).toBe(false);
  expect(deadCall({ tokens: [{ symbol: 'ZKL' }, live] }, [])).toBe(false);                            // one live coin keeps it
  expect(deadCall({ text: 'gm' }, [])).toBe(false);
  expect(deadCall({ tokens: [{ symbol: 'ZKL', pairAddress: 'Z' }] }, [{ pairAddress: 'Z', x: 1, peakX: 1 }])).toBe(true);   // the screenshot: never priced
});
