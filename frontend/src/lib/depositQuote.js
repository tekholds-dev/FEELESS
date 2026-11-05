// 💵 What a deposit costs (agent_deposit.py decides; this shows it before a receipt). 10% first and at $50+, 5% under $50, every 3rd under $50 is 10%. Half FEELESS, half the Collective.
export const FIRST_MIN = 50; export const BIG = 50;
export const smallCount = deposits => (deposits || []).slice(1).filter(d => Number(d.usd) < BIG).length;
export function depositQuote(usd, first, small, staff) {
  const u = Number(usd) || 0;
  if (staff) return { ratePct: 0, feelessUsd: 0, collectiveUsd: 0, restUsd: u, third: false, nextIsThird: false, staff: true };
  const under = !first && u < BIG; const third = under && (small + 1) % 3 === 0; const rate = under && !third ? 5 : 10; const half = Math.round(u * rate / 2) / 100;
  return { ratePct: rate, feelessUsd: half, collectiveUsd: half, restUsd: Math.round((u - half * 2) * 100) / 100, third, nextIsThird: !third && (small + (under ? 1 : 0) + 1) % 3 === 0, belowFirst: first && u < FIRST_MIN };
}
