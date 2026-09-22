import { coinIdentity, coinRoom, isNewPoolDeal, MARKET_RETENTION_DAYS, NEW_POOL_DEAL_PERCENT } from './dexscreener';

const NOW = 1_700_000_000_000;
const DAY = 24 * 60 * 60 * 1000;

function pair(ageInDays, drawdown) {
  return {
    pairCreatedAt: NOW - ageInDays * DAY,
    priceChange: { h24: drawdown },
  };
}

test('accepts provider pool deals only inside the fourteen-day window', () => {
  expect(isNewPoolDeal(pair(1, -NEW_POOL_DEAL_PERCENT), NOW)).toBe(true);
  expect(isNewPoolDeal(pair(MARKET_RETENTION_DAYS, -10), NOW)).toBe(true);
  expect(isNewPoolDeal(pair(MARKET_RETENTION_DAYS + 1, -20), NOW)).toBe(false);
});

test('requires at least a five percent 24h drawdown and rejects future pools', () => {
  expect(isNewPoolDeal(pair(1, -4.99), NOW)).toBe(false);
  expect(isNewPoolDeal(pair(-1, -20), NOW)).toBe(false);
  expect(isNewPoolDeal({ pairCreatedAt: NOW - DAY, priceChange: {} }, NOW)).toBe(false);
});

test('builds isolated rooms from the exact chain and pair identity', () => {
  const solana = { chainId: 'solana', pairAddress: 'shared-name' };
  const ethereum = { chainId: 'ethereum', pairAddress: 'shared-name' };

  expect(coinIdentity(solana)).toEqual({ chainId: 'solana', pairAddress: 'shared-name', key: 'solana:shared-name' });
  expect(coinRoom(solana, 'bulls')).toBe('coin-solana-shared-name-bulls');
  expect(coinRoom(ethereum, 'bulls')).not.toBe(coinRoom(solana, 'bulls'));
  expect(coinRoom({ chainId: 'solana' }, 'bulls')).toBeNull();
});