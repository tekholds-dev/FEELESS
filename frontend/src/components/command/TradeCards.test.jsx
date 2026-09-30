import { tradeCardGif } from './ProfileExtras';

jest.mock('react-router-dom', () => ({ Link: ({ children }) => children }), { virtual: true });

test('a winning sell becomes a green GIF card with its % and realized $, a buy shows its size', () => {
  const sell = tradeCardGif({ side: 'sell', symbol: 'PAID', token: 'Mint111', usd: 6, pnlUsd: 2, pnlPct: 50, feeUsd: 0.06, tx: 'abcdef123456' });
  expect(sell).toMatchObject({ kicker: 'SOLD ON FEELESS', title: '$PAID', tone: 'up', bigValue: 50, bigPrefix: '+' });
  expect(sell.lines[0]).toBe('+$2 realized on $6');
  const buy = tradeCardGif({ side: 'buy', token: 'Mint111', usd: 12.5, tx: 'abcdef123456' });
  expect(buy).toMatchObject({ kicker: 'BOUGHT ON FEELESS', big: '$12.5', tone: 'up' });
  expect(buy.lines[1]).toBe('Fee-free');
});
