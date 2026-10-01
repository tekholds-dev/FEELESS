import { fuseOrders, legTarget, orderMatches, SOL_MINT } from './fuseGo';

test('each leg buys its pool coin with SOL; SOL/X pools buy X; dust and SOL/SOL are skipped', () => {
  expect(legTarget({ baseAddress: 'BONK', symbol: 'BONK' })).toEqual({ mint: 'BONK', symbol: 'BONK' });
  expect(legTarget({ baseAddress: SOL_MINT, quoteAddress: 'USDC', quote: 'USDC' })).toEqual({ mint: 'USDC', symbol: 'USDC' });
  const o = fuseOrders([{ baseAddress: 'A', symbol: 'A', sol: 0.6 }, { baseAddress: SOL_MINT, quoteAddress: SOL_MINT, sol: 1 }, { baseAddress: 'C', sol: 0.0001 }], 'W');
  expect(o[0].request).toEqual({ input_mint: SOL_MINT, output_mint: 'A', amount: '0.6', slippage_bps: 100, wallet: 'W' });
  expect(o[1].skip).toMatch(/SOL\/SOL/); expect(o[2].skip).toMatch(/small/);
  expect(orderMatches(o[0], { input_mint: SOL_MINT, output_mint: 'A', amount: '0.6' })).toBe(true);
  expect(orderMatches(o[0], { input_mint: SOL_MINT, output_mint: 'B', amount: '0.6' })).toBe(false);
  expect(orderMatches(o[0], { input_mint: SOL_MINT, output_mint: 'A', amount: '0.7' })).toBe(false);
});
