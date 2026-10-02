"""FEELESS coin verification: the green check next to a coin's logo, site-wide.

A coin earns it; nobody buys it. Hard gates must all pass (any fail = no check, whatever the score), then
scored checks must reach VERIFY_MIN. Every check says what was measured and where it came from, the same way
case files cite evidence. HQ can grant a gold check (official / reviewed) or revoke one; a revoke
always wins. Pure functions only: the service gathers the facts.
"""

VERIFY_MIN = 75

GATES = (
    ('mint', 'Mint authority revoked', lambda f: f.get('mintAuthority') is None, 'Mint account'),
    ('freeze', 'Freeze authority revoked', lambda f: f.get('freezeAuthority') is None, 'Mint account'),
    ('creator', 'Creator not flagged (blocklist / case file)', lambda f: not f.get('creatorBlocked') and f.get('creatorLevel') not in ('suspect', 'high'), 'FEELESS case file'),
    ('age', 'Trading for 24h+', lambda f: (f.get('ageHours') or 0) >= 24, 'Pool creation time'),
    ('liquidity', 'Liquidity $25K+', lambda f: (f.get('liquidityUsd') or 0) >= 25_000, 'DEX pool'),
    ('whales', 'No whale control (top 10 under 50%)', lambda f: f.get('top10Pct') is not None and f['top10Pct'] < 50, 'Holder scan'),
    ('insiders', 'Insiders under 25%', lambda f: f.get('insidersPct') is not None and f['insidersPct'] < 25, 'Launch forensics'),
)

CRITICAL = ('mint', 'freeze', 'creator', 'liquidity')   # a granted gold check is suspended while any of these fail

SCORED = (
    ('lp', 15, 'Liquidity locked or burned', lambda f: bool(f.get('lpLocked')), 'Pool registry / launchpad'),
    ('top10', 12, 'Top 10 wallets hold under 30%', lambda f: f.get('top10Pct') is not None and f['top10Pct'] < 30, 'Holder scan'),
    ('insiders', 12, 'Snipers/bundlers hold under 10%', lambda f: f.get('insidersPct') is not None and f['insidersPct'] < 10, 'Launch forensics'),
    ('depth', 11, 'Deep pool (liquidity ≥ 10% of market cap)', lambda f: (f.get('liquidityUsd') or 0) >= 0.10 * (f.get('marketCapUsd') or 1e18), 'DEX pool'),
    ('cleanlaunch', 10, 'Clean launch (under 3 bundled, under 5 snipers)', lambda f: (f.get('bundled') or 0) < 3 and (f.get('snipers') or 0) < 5, 'Launch forensics'),
    ('dev', 8, 'Creator holds under 5%', lambda f: f.get('devPct') is not None and f['devPct'] < 5, 'Holder scan'),
    ('socials', 8, 'Website + social linked', lambda f: (f.get('socials') or 0) >= 2, 'Token profile'),
    ('volume', 8, 'Real volume (24h volume ≥ 25% of liquidity)', lambda f: (f.get('volume24h') or 0) >= 0.25 * (f.get('liquidityUsd') or 1), 'DEX pool'),
    ('flow', 8, 'Two-sided flow (buys 35–80% of trades)', lambda f: f.get('buyRatio') is not None and 0.35 <= f['buyRatio'] <= 0.8, 'DEX trades 24h'),
    ('seasoned', 8, 'Survived 72h+', lambda f: (f.get('ageHours') or 0) >= 72, 'Pool creation time'),
)


def verify_report(facts: dict, manual: dict = None, official: bool = False) -> dict:
    """facts → {level: 'gold' | 'verified' | 'revoked' | None, score, gates, checks, reason}."""
    manual = manual or {}
    gates = [{'key': k, 'label': label, 'pass': bool(test(facts)), 'source': src} for k, label, test, src in GATES]
    checks = [{'key': k, 'label': label, 'weight': w, 'pass': bool(test(facts)), 'source': src} for k, w, label, test, src in SCORED]
    score = sum(c['weight'] for c in checks if c['pass'])
    gates_ok = all(g['pass'] for g in gates)
    if manual.get('state') == 'revoked':
        level, reason = 'revoked', manual.get('note') or 'Revoked by FEELESS review.'
    elif not official and manual.get('state') == 'granted' and (lost := [g['label'] for g in gates if g['key'] in CRITICAL and not g['pass']]):
        level, reason = None, f'Gold check suspended: {lost[0]} failed — it comes back when the check passes again.'
    elif official or manual.get('state') == 'granted':
        level, reason = 'gold', 'Official FEELESS coin.' if official else (manual.get('note') or 'Reviewed and granted by FEELESS.')
    elif gates_ok and score >= VERIFY_MIN:
        level, reason = 'verified', f'Passed every safety gate and scored {score}/100.'
    else:
        failed = [g['label'] for g in gates if not g['pass']]
        level, reason = None, (f"Missing: {failed[0]}" + (f' (+{len(failed) - 1} more)' if len(failed) > 1 else '')) if failed else f'Scored {score}/100 (needs {VERIFY_MIN}).'
    return {'level': level, 'score': score, 'gatesPassed': gates_ok, 'gates': gates, 'checks': checks, 'reason': reason, 'min': VERIFY_MIN,
            'badges': coin_badges(gates, checks)}


def coin_badges(gates, checks):
    """Coin badges: earned while their checks pass, lost the moment they fail (recomputed on every verify run)."""
    ok = {('g', g['key']): g['pass'] for g in gates} | {('c', c['key']): c['pass'] for c in checks}
    return [{'id': bid, 'icon': icon, 'label': label, 'why': why, 'earned': all(ok.get(k, False) for k in keys)} for bid, icon, label, why, keys in COIN_BADGES]


def transitions(prev, rep):
    """What changed since the last run: verified/gold earned or lost, badges earned or lost — each with the reason."""
    prev = prev or {}
    out = []
    was, now = prev.get('level'), rep.get('level')
    if was != now and prev:
        if now in ('verified', 'gold'):
            out.append({'kind': 'earned', 'id': now, 'label': 'Gold check' if now == 'gold' else 'Verified', 'why': rep.get('reason')})
        if was in ('verified', 'gold') and now not in ('verified', 'gold'):
            out.append({'kind': 'lost', 'id': was, 'label': 'Gold check' if was == 'gold' else 'Verified', 'why': rep.get('reason')})
    had = set(prev.get('badges') or [])
    have = {b['id'] for b in rep.get('badges') or [] if b['earned']}
    if prev:
        out += [{'kind': 'earned', 'id': b['id'], 'label': b['label'], 'why': b['why']} for b in rep['badges'] if b['id'] in have - had]
        out += [{'kind': 'lost', 'id': b['id'], 'label': b['label'], 'why': f"No longer: {b['why']}"} for b in rep['badges'] if b['id'] in had - have]
    return out


COIN_BADGES = (   # id, icon, label, why, checks that must all pass ('g' gate / 'c' scored check)
    ('renounced', '🛡', 'Renounced', 'mint + freeze authority revoked', (('g', 'mint'), ('g', 'freeze'))),
    ('lp-locked', '🔒', 'LP locked', 'liquidity locked or burned', (('c', 'lp'),)),
    ('spread', '💎', 'Spread holders', 'top 10 wallets hold under 30%', (('c', 'top10'),)),
    ('clean', '🧼', 'Clean launch', 'under 3 bundled + under 5 snipers', (('c', 'cleanlaunch'),)),
    ('real-vol', '📈', 'Real volume', '24h volume ≥ 25% of liquidity', (('c', 'volume'),)),
    ('two-way', '⇄', 'Two-way flow', 'buys 35–80% of trades', (('c', 'flow'),)),
    ('survivor', '⏳', 'Survivor', 'trading 72h+', (('c', 'seasoned'),)),
)
