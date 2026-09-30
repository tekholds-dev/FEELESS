"""FEELESS coin verification: the green check next to a coin's logo, site-wide.

A coin earns it; nobody buys it. Hard gates must all pass (any fail = no check, whatever the score), then
scored checks must reach VERIFY_MIN. Every check says what was measured and where it came from, the same way
case files cite evidence. Command Center can grant a gold check (official / reviewed) or revoke one; a revoke
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
    elif official or manual.get('state') == 'granted':
        level, reason = 'gold', 'Official FEELESS coin.' if official else (manual.get('note') or 'Reviewed and granted by FEELESS.')
    elif gates_ok and score >= VERIFY_MIN:
        level, reason = 'verified', f'Passed every safety gate and scored {score}/100.'
    else:
        failed = [g['label'] for g in gates if not g['pass']]
        level, reason = None, (f"Missing: {failed[0]}" + (f' (+{len(failed) - 1} more)' if len(failed) > 1 else '')) if failed else f'Scored {score}/100 (needs {VERIFY_MIN}).'
    return {'level': level, 'score': score, 'gatesPassed': gates_ok, 'gates': gates, 'checks': checks, 'reason': reason, 'min': VERIFY_MIN}
