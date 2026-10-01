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

test('unfuse sells min(bought, held) back to SOL; skips sold / empty legs', () => {
  const { unfuseOrders } = require('./fuseGo');
  const legs = [{ mint: 'A', symbol: 'A', tokens: 100 }, { mint: 'B', symbol: 'B', tokens: 5 }, { mint: 'C', tokens: 1, soldUsd: 2 }, { mint: 'D', tokens: 1 }];
  const o = unfuseOrders(legs, { A: { raw: '250000000', decimals: 6 }, B: { raw: '1500000', decimals: 6 }, D: { raw: '0', decimals: 6 } }, 'W');
  expect(o[0].request).toEqual({ input_mint: 'A', output_mint: SOL_MINT, amount: '100', slippage_bps: 150, wallet: 'W' });
  expect(o[1].request.amount).toBe('1.5');                  // only 1.5 left in the wallet
  expect(o[2].skip).toMatch(/Already/); expect(o[3].skip).toMatch(/Nothing/);
  expect(orderMatches(o[1], { input_mint: 'B', output_mint: SOL_MINT, amount: '1.5' })).toBe(true);
});
