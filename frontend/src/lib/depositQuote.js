// 💵 What a deposit costs (agent_deposit.py decides; this shows it before a receipt). The rate from the owner's Collective folder, all of it to the Collective wallet.
export function depositQuote(usd, first, staff, ratePct = 10, firstMin = 50) {
  const u = Number(usd) || 0;
  if (staff) return { ratePct: 0, collectiveUsd: 0, restUsd: u, staff: true };
  const cut = Math.round(u * ratePct) / 100;
  return { ratePct, collectiveUsd: cut, restUsd: Math.round((u - cut) * 100) / 100, belowFirst: first && u < firstMin };
}
