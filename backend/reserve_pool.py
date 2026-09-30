"""Season badge reserve pool: who gets what share of the Fee Reserve wallet.

Season tiers earn weighted shares of `badgeRewardPct`% of the reserve wallet's SOL. Pure functions only:
the service reads the balance and scores, the owner signs the payout from the reserve wallet (no custody).
"""

TIER_WEIGHTS = {'Legend': 12, 'Diamond': 6, 'Gold': 3, 'Silver': 2, 'Bronze': 1, 'Recruit': 0}
KEEP_SOL = 0.01      # left in the reserve wallet for rent + network fees
DUST_SOL = 0.001     # shares below this are not worth a transfer


def payout_plan(pool_sol: float, pct: float, holders: list, excluded=frozenset(), keep_sol: float = KEEP_SOL, dust_sol: float = DUST_SOL) -> dict:
    """holders: [{address, tier, score}]. Returns the pot and each wallet's weighted share (SOL, 6 dp)."""
    pct = max(0.0, min(100.0, float(pct or 0)))
    pot = round(max(0.0, min(float(pool_sol or 0) * pct / 100, float(pool_sol or 0) - keep_sol)), 6)
    rows = [{'address': h['address'], 'tier': h.get('tier') or 'Recruit', 'score': h.get('score') or 0,
             'weight': TIER_WEIGHTS.get(h.get('tier'), 0)} for h in holders if h.get('address') and h['address'] not in excluded]
    rows = [r for r in rows if r['weight'] > 0]
    dropped = 0
    for _ in range(3):  # drop dust shares and re-split, so the pot goes to wallets that actually get paid
        total = sum(r['weight'] for r in rows)
        for r in rows:
            r['sharePct'] = round(100 * r['weight'] / total, 3) if total else 0
            r['sol'] = int(pot * 1e6 * r['weight'] / total) / 1e6 if total else 0
        dust = [r for r in rows if r['sol'] < dust_sol]
        if not dust:
            break
        dropped += len(dust)
        rows = [r for r in rows if r['sol'] >= dust_sol]
    rows.sort(key=lambda r: (-r['weight'], -r['score']))
    return {'poolSol': round(float(pool_sol or 0), 6), 'pct': pct, 'potSol': pot, 'totalWeight': sum(r['weight'] for r in rows),
            'paidSol': round(sum(r['sol'] for r in rows), 6), 'rows': rows, 'droppedDust': dropped, 'weights': TIER_WEIGHTS}


def wallet_share(plan: dict, address: str):
    return next((r for r in plan['rows'] if r['address'] == address), None)
