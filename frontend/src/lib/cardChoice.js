// 🎟 The buyer's pick for a new card: rounds · most swaps in one round · pay up front or start on the free rounds.
// Mirrors backend fuse_hq.card_choice (change both). The server re-computes the price and verifies the payment on-chain.
export const PLAN_ROUNDS = [5, 10, 20, 50];
export const PLAN_SWAPS = [1, 2, 3];
export const FREE_ROUNDS = 5;
export const CHOICE_KEYS = ['rounds', 'swapsPerRound', 'payUpfront'];

export const keepChoice = plan => Object.fromEntries(CHOICE_KEYS.filter(k => plan && plan[k] !== undefined).map(k => [k, plan[k]]));

export function cardChoice(plan, pricing) {
  const pp = pricing?.prepay || pricing || {}; const per5 = Number(pricing?.rounds?.per5Usd ?? pricing?.per5Usd ?? 0);
  const perSwap = Number(pp.perSwapUsd || 0); const on = pp.on !== false && perSwap > 0;
  const p = plan || {};
  if (!PLAN_ROUNDS.includes(p.rounds) && !PLAN_SWAPS.includes(p.swapsPerRound) && p.payUpfront === undefined)
    return { chosen: false, rounds: pp.rounds || FREE_ROUNDS, swapsPerRound: pp.swapsPerRound || 1, upfront: true, packs: 0, roundsUsd: 0, swaps: pp.swaps || 0, swapsUsd: Number(pp.usd || 0), usd: pp.on === false ? 0 : Number(pp.usd || 0) };
  const rounds = PLAN_ROUNDS.includes(p.rounds) ? p.rounds : FREE_ROUNDS;
  const per = PLAN_SWAPS.includes(p.swapsPerRound) ? p.swapsPerRound : 1;
  const upfront = p.payUpfront !== false;
  const packs = Math.max(0, Math.ceil((rounds - FREE_ROUNDS) / 5));
  const r4 = v => Math.round(v * 1e4) / 1e4;
  const roundsUsd = r4(packs * per5); const swaps = rounds * per; const swapsUsd = on ? r4(perSwap * swaps) : 0;
  return { chosen: true, rounds, swapsPerRound: per, upfront, packs, roundsUsd, swaps, swapsUsd, usd: upfront ? r4(roundsUsd + swapsUsd) : 0 };
}
