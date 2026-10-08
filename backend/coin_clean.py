"""🧼 CLEAN SCORE — 10 checks, one point each, so a pick list can say at a glance whether a coin looks like a 10x setup or a rug.
Every point is a number read from the chain or the market, never an opinion. An UNKNOWN number scores 0 and is named as unknown
(a coin is never called clean because a read failed). A score, never a promise: a clean coin can still go to zero."""

def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


CHECKS = (
    # key, label, the test (row, intel, rep) → True / False / None (unknown)
    ('top10', 'top-10 wallets under 20%', lambda r, i, rep: None if i.get('top10Pct') is None else _f(i['top10Pct']) < 20),
    ('dev', 'creator holds under 5%', lambda r, i, rep: None if i.get('devHoldingPct') is None else _f(i['devHoldingPct']) < 5),
    ('insiders', 'snipers + bundlers hold under 5%', lambda r, i, rep: None if i.get('insidersHoldingPct') is None else _f(i['insidersHoldingPct']) < 5),
    ('bundled', 'at most 1 bundled wallet', lambda r, i, rep: None if i.get('bundledWallets') is None else len(i['bundledWallets'] or []) <= 1),
    ('snipers', 'snipers hold under 3%', lambda r, i, rep: None if i.get('snipersHoldingPct') is None else _f(i['snipersHoldingPct']) < 3),
    ('funders', 'no flagged funders or wallets', lambda r, i, rep: None if not i else not (i.get('flaggedFunders') or i.get('flaggedHoldings'))),
    ('creator', 'creator not flagged (suspect / high risk)', lambda r, i, rep: None if not i.get('creator') else rep not in ('suspect', 'high')),
    ('buyers', 'buyers 55%+ of trades', lambda r, i, rep: None if r.get('buyShare') is None else _f(r['buyShare']) >= 55),
    ('pool', 'pool $25K+', lambda r, i, rep: None if r.get('liquidityUsd') is None and r.get('liq') is None else _f(r.get('liquidityUsd', r.get('liq'))) >= 25_000),
    ('flow', '$20K+ traded this hour, not dumping', lambda r, i, rep: None if r.get('vol1h') is None else _f(r['vol1h']) >= 20_000 and _f(r.get('change1h', r.get('chg1h'))) > -15),
)


def score(row, intel, creator_rep=None):
    """→ {score 0–10, tier clean|mixed|risky, fails [labels], unknown [labels]}."""
    row, intel = row or {}, intel or {}
    ok, fails, unknown = 0, [], []
    for _k, label, test in CHECKS:
        try:
            v = test(row, intel, creator_rep)
        except Exception:
            v = None
        if v is True:
            ok += 1
        elif v is False:
            fails.append(label)
        else:
            unknown.append(label)
    return {'score': ok, 'tier': 'clean' if ok >= 8 else 'mixed' if ok >= 5 else 'risky', 'fails': fails, 'unknown': unknown}
