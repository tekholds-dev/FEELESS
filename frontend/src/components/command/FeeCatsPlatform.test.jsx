
test('💵 the funding receipt: the buy + the live FEELESS fee + gas = what your wallet should hold', () => {
  const { fundPlan } = require('./FundReceipt');
  expect(fundPlan(0.05, 100)).toEqual({ fee: 0.0005, need: 0.05 + 0.0005 + 0.003 });
  expect(fundPlan(0.1, 0).fee).toBe(0); expect(fundPlan(0.1, null).need).toBeCloseTo(0.103);
});
