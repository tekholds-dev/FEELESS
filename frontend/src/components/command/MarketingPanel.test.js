import { feecatPosts } from './MarketingPanel';

test('FeeCat posts: open trade with entry MC + reason, wins green, cuts crimson, always labelled paper', () => {
  const { open, closed } = feecatPosts({
    positions: [{ symbol: 'SPEED', mint: 'M1', pairAddress: 'P1', currentChange: 42.3, peakChange: 60, entryMarketCapUsd: 250000, costSol: 0.5, reason: 'volume spike + clean holders' }],
    exits: [{ symbol: 'WIN', pairAddress: 'P2', changeAtExit: 35, pnlSol: 0.12, why: 'take-profit at +35%', exitAt: 1700000000 },
      { symbol: 'LOSS', pairAddress: 'P3', changeAtExit: -18, pnlSol: -0.05, why: 'stop-loss', exitAt: 1700000100 }],
  });
  expect(open[0].post).toContain('+42.3% since entry at $250.0K MC');
  expect(open[0].post).toContain('Why in: volume spike + clean holders');
  expect(open[0].card).toMatchObject({ mascot: 'feecat', tone: 'up', kicker: 'FEECAT TRADE · OPEN · PAPER' });
  const [loss, win] = closed;  // newest first
  expect(loss.card.tone).toBe('down');
  expect(loss.post).toContain('FeeCat cut $LOSS at −18.0%');
  expect(win.card.tone).toBe('up');
  expect(win.card.kicker).toContain('PAPER');
});
