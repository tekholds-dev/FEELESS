import { tapeRow } from './FeeCatLive';

test('⚡ the tape turns a sentence into chips: coin · SOL · move · P&L · 🔮 FeeCat AI · tag (the sentence stays on hover)', () => {
  const buy = tapeRow({ type: 'BUY', detail: 'Bought 0.06 SOL of SQUADS at live price — 🔮 FeeCat AI favored it; 🔮 FeeCat AI over: lost 6/8 (half size)' });
  expect(buy).toMatchObject({ coin: 'SQUADS', sol: 0.06, ai: true, tag: '½ SIZE' });
  const sell = tapeRow({ type: 'SELL', pnlSol: 0.004, detail: 'Sold PAIR at +4.1% — her AI desk said exit. P&L +0.0040 SOL' });
  expect(sell).toMatchObject({ coin: 'PAIR', move: 4.1, pnl: 0.004, ai: true });
  expect(tapeRow({ type: 'SELL', detail: 'Sold Bunnett at -7.0% — thesis broken: sellers dumping' })).toMatchObject({ coin: 'Bunnett', move: -7, tag: 'STOP', ai: false });
  expect(tapeRow({ type: 'LEARN', detail: 'Discipline: negative expectancy (-0.0008 SOL/trade) — smaller size.' }).tag).toBe('Discipline');
  expect(tapeRow(null)).toMatchObject({ coin: null, ai: false });
});
