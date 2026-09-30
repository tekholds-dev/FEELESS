import { launchTerms, receiptLinks, coinErrors, socialLink } from './cmdLaunch';

test('terms show the chosen config, toll only on house configs that charge one', () => {
  const house = { label: 'Reserve coins', params: { initialMarketCap: 40, migrationMarketCap: 600, quote: 'SOL', poolCreationFeeSol: 5 } };
  const t = Object.fromEntries(launchTerms('house', house));
  expect(t.Config).toBe('Reserve coins'); expect(t['Opens → graduates']).toBe('40 → 600 SOL'); expect(t['Launch toll']).toMatch(/^5 SOL/);
  expect(Object.fromEntries(launchTerms('feeless', { params: {} }))['Launch toll']).toBeUndefined();
  expect(launchTerms('pump')[0][1]).toMatch(/Pump/);
});

test('receipt links: pump link only for pump coins', () => {
  expect(receiptLinks('pump', 'MINT', 'SIG')[0]).toEqual(['pump.fun', 'https://pump.fun/coin/MINT']);
  expect(receiptLinks('house', 'MINT', 'SIG').some(([l]) => l === 'pump.fun')).toBe(false);
});

test('coin form checks', () => {
  expect(coinErrors({ name: 'Fee', symbol: 'FEE', imageUrl: '/x' })).toEqual({});
  const e = coinErrors({ name: '', symbol: 'TOO-LONG-TICKER', devBuy: '9' }, { maxDevBuySol: 5 });
  expect(Object.keys(e).sort()).toEqual(['devBuy', 'imageUrl', 'name', 'symbol']);
  expect(socialLink('twitter', '@fee')).toBe('https://x.com/fee');
});
