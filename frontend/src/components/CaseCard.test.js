jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { caseCard } from './CaseFile';

test('coin case GIF: coin image + $SYMBOL, score, and the facts as coloured stats', () => {
  const c = { kind: 'coin', address: 'Mint1111111111111111111111111111111111111', score: 40, level: 'caution', summary: 'Creator is on the blocklist',
    authorities: { mintAuthority: null, freezeAuthority: 'F' }, holders: { top10Pct: 31, devHoldingPct: 0 }, launch: { snipers: 1, bundled: 0 },
    evidence: [{ weight: 40, claim: 'Creator wallet is on the FEELESS blocklist.' }] };
  const coin = { baseToken: { symbol: 'COL', name: 'Collateral' }, info: { imageUrl: 'https://img/col.png' }, liquidity: { usd: 85000 }, marketCap: 822000 };
  const card = caseCard(c, coin);
  expect(card.title).toBe('$COL · Collateral'); expect(card.imageUrl).toContain('/api/reputation/token-logo/Mint1111'); expect(card.big).toBe('40/100');
  expect(card.stats.map(s => [s.label, s.value, s.tone])).toEqual([
    ['Mint authority', 'revoked ✓', 'ok'], ['Freeze authority', 'LIVE ⚠', 'bad'], ['Top 10 hold', '31%', 'warn'],
    ['Dev holds', '0.0%', 'ok'], ['Snipers · bundled', '1 · 0', 'ok'], ['Liq · MC', '$85.0K · $822.0K', undefined]]);
  expect(card.lines[0]).toBe('Creator is on the blocklist');
  expect(caseCard({ ...c, summary: '' }).lines[0]).toBe('CAUTION — 1 red flag on record');
});
