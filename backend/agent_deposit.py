"""💵 WHAT A DEPOSIT COSTS (owner 2026-11-04), per agent. First deposit: at least $50, 10%. After that: 10% at $50 or more, 5% under $50, and every 3rd deposit under $50 is 10%, so splitting a big deposit into small ones saves little.
Half goes to FEELESS and half to the Collective's Pool wallet in the same transaction, on the receipt before the owner signs. Staff pay nothing. Pure, tested."""
FIRST_MIN_USD = 50.0
BIG_USD = 50.0
RATE_BIG, RATE_SMALL = 10.0, 5.0
EVERY_THIRD = 3


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def small_count(deposits):
    """How many of its deposits so far were under $50, leaving out its first."""
    return sum(1 for d in (deposits or [])[1:] if _f(d.get('usd')) < BIG_USD)


def is_first(cat):
    c = cat or {}
    return not (c.get('deposits') or c.get('agentFunded') or c.get('creditPaid'))


def quote(usd, first, small, staff=False):
    """→ {ratePct, feelessUsd, collectiveUsd, restUsd, third, nextIsThird}. Raises ValueError under the first-deposit minimum."""
    usd = _f(usd)
    if staff:
        return {'ratePct': 0.0, 'feelessUsd': 0.0, 'collectiveUsd': 0.0, 'restUsd': round(usd, 2), 'third': False, 'nextIsThird': False, 'staff': True}
    if first and usd < FIRST_MIN_USD:
        raise ValueError(f'A first deposit starts at ${FIRST_MIN_USD:g}.')
    under = not first and usd < BIG_USD
    third = under and (int(small) + 1) % EVERY_THIRD == 0
    rate = RATE_SMALL if under and not third else RATE_BIG
    half = round(usd * rate / 200, 2)
    return {'ratePct': rate, 'feelessUsd': half, 'collectiveUsd': half, 'restUsd': round(usd - half * 2, 2), 'third': third, 'nextIsThird': (not third) and (int(small) + (1 if under else 0) + 1) % EVERY_THIRD == 0}


def apply(pl, q):
    """Move the cut out of the agent's share of a built plan. Both cuts round up to the smallest unit, so no rounding ever shorts them. Raises ValueError when its model credit would not fit in what is left."""
    if _f(pl.get('creditUsd')) > q['restUsd'] + 1e-9:
        raise ValueError(f"After the {q['ratePct']:g}% only ${q['restUsd']:.2f} is left, so model credit can be at most that.")
    px = _f(pl.get('solUsd')); scale = 1_000_000 if pl.get('token') == 'USDC' else 1_000_000_000
    fee = int(q['feelessUsd'] / px * scale + 0.999999) if px else 0
    col = int(q['collectiveUsd'] / px * scale + 0.999999) if px else 0
    if fee + col > int(pl.get('catLamports') or 0):
        raise ValueError('This deposit is too small to cover its fee.')
    return {**pl, 'feeLamports': int(pl.get('feeLamports') or 0) + fee, 'colonyLamports': col, 'catLamports': int(pl['catLamports']) - fee - col, 'catUsd': round(_f(pl.get('catUsd')) - q['feelessUsd'] - q['collectiveUsd'], 2), 'deposit': q}
