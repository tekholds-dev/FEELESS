// 📊 MARKET CAP FIRST on every chart (owner, 2026-10-12): when the live record has no cap yet (a fresh curve coin the pairs feed has not
// indexed), a launchpad mint's cap is its price × its fixed 1B supply (Pump · Bonk launch with exactly 1,000,000,000 tokens). Other coins:
// the cap the caller knows, else none (then the chart says price, honestly).
export const LAUNCH_SUPPLY = 1e9;
export const isLaunchpadMint = mint => typeof mint === 'string' && /(pump|bonk)$/i.test(mint);
export function mcapOf(price, knownMc, mint) {
  const p = Number(price), mc = Number(knownMc);
  if (mc > 0) return mc;
  if (p > 0 && isLaunchpadMint(mint)) return p * LAUNCH_SUPPLY;
  return null;
}
