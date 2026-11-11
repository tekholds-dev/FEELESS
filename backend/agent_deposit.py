"""💵 WHAT A DEPOSIT COSTS (owner 2026-11-04), per agent: 10% of every deposit, a first one starts at $50, and all of it goes to the Collective wallet in the same transaction, on the receipt before the owner signs. Nothing from an agent goes to a FEELESS wallet. Staff pay nothing. The rate lives in the owner's Collective folder. Pure, tested."""
from fnum import plain as _f
FIRST_MIN_USD = 50.0
RATE_PCT = 10.0



def is_first(cat):
    c = cat or {}
    return not (c.get('deposits') or c.get('agentFunded') or c.get('creditPaid'))


def quote(usd, first, staff=False, rate_pct=RATE_PCT, first_min=FIRST_MIN_USD):
    """→ {ratePct, collectiveUsd, restUsd}. Raises ValueError under the first-deposit minimum."""
    usd = _f(usd)
    if staff:
        return {'ratePct': 0.0, 'collectiveUsd': 0.0, 'restUsd': round(usd, 2), 'staff': True}
    if first and usd < first_min:
        raise ValueError(f'A first deposit starts at ${first_min:g}.')
    cut = round(usd * rate_pct / 100, 2)
    return {'ratePct': rate_pct, 'collectiveUsd': cut, 'restUsd': round(usd - cut, 2)}


def apply(pl, q):
    """Move the cut out of the agent's share of a built plan. It rounds up to the smallest unit, so rounding never shorts it. Raises ValueError when its model credit would not fit in what is left."""
    if _f(pl.get('creditUsd')) > q['restUsd'] + 1e-9:
        raise ValueError(f"After the {q['ratePct']:g}% only ${q['restUsd']:.2f} is left, so model credit can be at most that.")
    px = _f(pl.get('solUsd')); scale = 1_000_000 if pl.get('token') == 'USDC' else 1_000_000_000
    col = int(q['collectiveUsd'] / px * scale + 0.999999) if px else 0
    if col > int(pl.get('catLamports') or 0):
        raise ValueError('This deposit is too small to cover its fee.')
    return {**pl, 'colonyLamports': col, 'catLamports': int(pl['catLamports']) - col, 'catUsd': round(_f(pl.get('catUsd')) - q['collectiveUsd'], 2), 'deposit': q}
