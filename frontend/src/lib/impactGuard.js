// Price-impact brake for every swap we sign. Jupiter's priceImpactPct is a fraction (-0.12 = 12% worse);
// older quotes carry priceImpact already in percent. 15%+ needs an explicit tick, 50%+ is refused outright.
export const IMPACT_ACK = 15;
export const IMPACT_BLOCK = 50;

export function impactPercent(quote) {
  if (!quote) return null;
  if (quote.priceImpactPct != null && quote.priceImpactPct !== '') {
    const v = Number(quote.priceImpactPct);
    return Number.isFinite(v) ? Math.abs(v * 100) : null;
  }
  const v = Number(quote.priceImpact);
  return quote.priceImpact != null && Number.isFinite(v) ? Math.abs(v) : null;
}

export function impactGate(pct) {
  if (pct == null) return 'ok';
  if (pct >= IMPACT_BLOCK) return 'block';
  return pct >= IMPACT_ACK ? 'ack' : 'ok';
}

// true while the approve button must stay disabled
export const impactBlocks = (pct, ack) => { const g = impactGate(pct); return g === 'block' || (g === 'ack' && !ack); };
