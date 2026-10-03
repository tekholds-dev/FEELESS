import { fuseOrders, legTarget, orderMatches, SOL_MINT } from './fuseGo';

test('each leg buys its pool coin with SOL; SOL/X pools buy X; dust and SOL/SOL are skipped', () => {
  expect(legTarget({ baseAddress: 'BONK', symbol: 'BONK' })).toEqual({ mint: 'BONK', symbol: 'BONK' });
  expect(legTarget({ baseAddress: SOL_MINT, quoteAddress: 'USDC', quote: 'USDC' })).toEqual({ mint: 'USDC', symbol: 'USDC' });
  const o = fuseOrders([{ baseAddress: 'A', symbol: 'A', sol: 0.6 }, { baseAddress: SOL_MINT, quoteAddress: SOL_MINT, sol: 1 }, { baseAddress: 'C', sol: 0.0001 }], 'W');
  expect(o[0].request).toEqual({ input_mint: SOL_MINT, output_mint: 'A', amount: '0.6', slippage_bps: 200, wallet: 'W' });   // unknown depth → 2%
  expect(o[1].skip).toMatch(/SOL\/SOL/); expect(o[2].skip).toMatch(/small/);
  expect(orderMatches(o[0], { input_mint: SOL_MINT, output_mint: 'A', amount: '0.6' })).toBe(true);
  expect(orderMatches(o[0], { input_mint: SOL_MINT, output_mint: 'B', amount: '0.6' })).toBe(false);
  expect(orderMatches(o[0], { input_mint: SOL_MINT, output_mint: 'A', amount: '0.7' })).toBe(false);
});

test('unfuse sells min(bought, held) back to SOL; skips sold / empty legs', () => {
  const { unfuseOrders } = require('./fuseGo');
  const legs = [{ mint: 'A', symbol: 'A', tokens: 100 }, { mint: 'B', symbol: 'B', tokens: 5 }, { mint: 'C', tokens: 1, soldUsd: 2 }, { mint: 'D', tokens: 1 }];
  const o = unfuseOrders(legs, { A: { raw: '250000000', decimals: 6 }, B: { raw: '1500000', decimals: 6 }, D: { raw: '0', decimals: 6 } }, 'W');
  expect(o[0].request).toEqual({ input_mint: 'A', output_mint: SOL_MINT, amount: '100', slippage_bps: 250, wallet: 'W' });   // sells +0.5%
  expect(o[1].request.amount).toBe('1.5');                  // only 1.5 left in the wallet
  expect(o[2].skip).toMatch(/Already/); expect(o[3].skip).toMatch(/Nothing/);
  expect(orderMatches(o[1], { input_mint: 'B', output_mint: SOL_MINT, amount: '1.5' })).toBe(true);
});

test('rebalance: sell the over-weight leg, buy the under-weight one, leave near-target legs', () => {
  const { rebalanceOrders } = require('./fuseGo');
  const r = { legs: [
    { pairAddress: 'A', mint: 'MA', symbol: 'A', usd: 10, heldUsd: 30 },   // target 20 of 40 → sell $10
    { pairAddress: 'B', mint: 'MB', symbol: 'B', usd: 10, heldUsd: 9 },    // target 20 → buy $11
    { pairAddress: 'C', mint: 'MC', symbol: 'C', usd: 0.1, heldUsd: 1, soldUsd: 2 } ] };
  const o = rebalanceOrders(r, { MA: { raw: '100000000', decimals: 6 } }, { A: 0.5, B: 1 }, 100, 'W');
  expect(o).toHaveLength(2);
  expect(o[0].request).toMatchObject({ input_mint: 'MA', output_mint: SOL_MINT, amount: '21' });          // held $39 → target $19.50 each: sell $10.50 = 21 tokens
  expect(o[1].request).toMatchObject({ input_mint: SOL_MINT, output_mint: 'MB', amount: '0.105' });      // buy $10.50 / $100
  expect(rebalanceOrders({ legs: [{ pairAddress: 'A', mint: 'MA', usd: 5, heldUsd: 5.1 }, { pairAddress: 'B', mint: 'MB', usd: 5, heldUsd: 5 }] }, {}, { A: 1, B: 1 }, 100, 'W')).toEqual([]);
});


test('smart slippage: deep pools tight, thin pools and runners wider, capped at 8%', () => {
  const { smartSlippage } = require('./fuseGo');
  expect(smartSlippage({ liquidityUsd: 5e6 })).toBe(100);
  expect(smartSlippage({ liquidityUsd: 3e5 })).toBe(200);
  expect(smartSlippage({ liquidityUsd: 8e4 })).toBe(300);
  expect(smartSlippage({ liquidityUsd: 1e4 })).toBe(500);
  expect(smartSlippage({ liquidityUsd: 5e6, runner: true })).toBe(300);
  expect(smartSlippage({ liquidityUsd: 1e4 }, true)).toBe(550);
});
