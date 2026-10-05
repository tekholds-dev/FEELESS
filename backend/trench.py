"""🗑 Trench coins — fresh launches breaking out of the ~$20–30K zone with a real crowd. Pure, tested.

High risk, so the gate is the strictest on the site and FAILS CLOSED (anything unknown = out). Every check is cited:
  • fresh: ≤ maxAgeH old · market cap broke $20K and is still under the cap (the break, not the top)
  • a real crowd: ≥ 400 holders (counted on-chain) · ≥ 250 trades in the last hour · ≥ $10K 1h volume · buyers ≥ 55%
  • momentum: 5-minute AND 1-hour candles green (it is breaking now, not bleeding)
  • clean holders: holder scan done · top-10 < 25% · snipers/bundlers < 8% · ≤ 1 bundled wallet · dev < 5% and NOT selling ·
    no top-10 spike · no flagged funders
  • safe token: mint AND freeze authority revoked (nobody can print more or freeze your coins) · not a mayhem-mode coin
  • reputation: creator not flagged (bot shield / reported rug) and not rated watch / suspect / high — a fresh launch is exactly
    where rugs happen, so here a suspect creator is out even with good numbers
A card holds 1 or 2 of these at most (`arena_prime.TRENCH_COINS`). Ranking only — it never promises a result.
"""
import math

TRENCH = {'maxAgeH': 6.0, 'minMcap': 20_000.0, 'maxMcap': 150_000.0, 'minHolders': 400, 'minTxns1h': 250, 'minVol1h': 10_000.0,
          'minBuyShare': 55.0, 'maxTop10': 25.0, 'maxInsiders': 8.0, 'maxBundled': 1, 'maxDev': 5.0, 'maxTop10Jump': 5.0}
BAD_REP = ('watch', 'suspect', 'high')


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def precheck(c, cfg=None):
    """Every check that needs no extra lookup (cheap — runs on the whole feed). → list of failed checks (empty = worth a holder count)."""
    g = {**TRENCH, **(cfg or {})}
    fails = []
    age = c.get('ageH')
    if age is None or _f(age) > g['maxAgeH']:
        fails.append(f"fresh (≤ {g['maxAgeH']:g}h old)")
    if not g['minMcap'] <= _f(c.get('mcap')) <= g['maxMcap']:
        fails.append(f"market cap broke ${g['minMcap'] / 1000:g}K (under ${g['maxMcap'] / 1000:g}K)")
    if int(_f(c.get('txns1h'))) < g['minTxns1h']:
        fails.append(f"≥ {g['minTxns1h']} trades in 1h")
    if _f(c.get('vol1h')) < g['minVol1h']:
        fails.append(f"≥ ${g['minVol1h'] / 1000:g}K 1h volume")
    if c.get('buyShare') is None or _f(c['buyShare']) < g['minBuyShare']:
        fails.append(f"buyers ≥ {g['minBuyShare']:g}%")
    if _f(c.get('chg5m')) <= 0 or _f(c.get('chg1h')) <= 0:
        fails.append('5m and 1h green (breaking out now)')
    if not c.get('scanned') or c.get('top10') is None or _f(c['top10']) >= g['maxTop10']:
        fails.append(f"top-10 < {g['maxTop10']:g}% (scan done)")
    if _f(c.get('insiders')) >= g['maxInsiders'] or int(_f(c.get('bundled'))) > g['maxBundled']:
        fails.append(f"snipers/bundlers < {g['maxInsiders']:g}% · ≤ {g['maxBundled']} bundled")
    if _f(c.get('dev')) >= g['maxDev'] or c.get('devSold'):
        fails.append(f"dev < {g['maxDev']:g}% and not selling")
    if _f(c.get('top10Jump')) >= g['maxTop10Jump'] or int(_f(c.get('flaggedFunders'))) > 0:
        fails.append('no top-10 spike · no flagged funders')
    if c.get('mayhem'):
        fails.append('not a mayhem-mode coin')
    if c.get('creatorFlagged') or c.get('creatorRep') in BAD_REP:
        fails.append('creator clean (not flagged · not watch / suspect / high)')
    return fails


def gate(c, holders, auth, cfg=None):
    """Full trench gate: precheck + the on-chain crowd and token-safety checks. → (ok, failed checks)."""
    g = {**TRENCH, **(cfg or {})}
    fails = precheck(c, cfg)
    if holders is None or int(_f(holders)) < g['minHolders']:
        fails.append(f"≥ {g['minHolders']} holders")
    if not auth or auth.get('mintAuthority') or auth.get('freezeAuthority'):
        fails.append('mint + freeze authority revoked')
    return not fails, fails


def score(c, holders):
    """0–100 with cited parts: crowd (holders + trades), flow (buyers + volume), momentum, holder spread, creator."""
    parts = []
    def add(part, pts, why):
        parts.append({'part': part, 'points': round(pts, 1), 'why': why})
    add('crowd', min(25.0, int(_f(holders)) / 40 + int(_f(c.get('txns1h'))) / 60), f"{int(_f(holders))} holders · {int(_f(c.get('txns1h')))} trades/1h")
    add('flow', min(20.0, (_f(c.get('buyShare')) - 50) * 1.2 + math.log10(max(1.0, _f(c.get('vol1h')) / 1000)) * 4), f"{_f(c.get('buyShare')):.0f}% buys · ${_f(c.get('vol1h')) / 1000:.0f}K 1h")
    add('momentum', min(20.0, _f(c.get('chg5m')) * 0.8 + _f(c.get('chg1h')) * 0.2), f"5m {_f(c.get('chg5m')):+.0f}% · 1h {_f(c.get('chg1h')):+.0f}%")
    add('spread', max(0.0, 20.0 - _f(c.get('top10')) * 0.6 - _f(c.get('insiders'))), f"top-10 {_f(c.get('top10')):.0f}% · insiders {_f(c.get('insiders')):.0f}%")
    add('creator', 10.0 if c.get('creatorRep') == 'clean' else 4.0, 'clean creator' if c.get('creatorRep') == 'clean' else 'new creator (no record)')
    add('snipers', 5.0 if c.get('snipersOut') else 0.0, 'snipers sold out' if c.get('snipersOut') else 'snipers still in')
    return round(max(0.0, min(100.0, sum(p['points'] for p in parts))), 1), parts


def market_pair(p, now_ms, cfg=None):
    """Cheap first look at a RAW DexScreener pair (before any holder scan): fresh, in the $20K–cap band, busy, buyers ahead, green.
    The runner board only scans the 40 busiest coins — trench finalists are added to that scan so their holder checks can run."""
    g = {**TRENCH, **(cfg or {})}
    age_h = (now_ms - _f(p.get('pairCreatedAt'))) / 3.6e6 if _f(p.get('pairCreatedAt')) else None
    tx = (p.get('txns') or {}).get('h1') or {}
    b, s_ = int(_f(tx.get('buys'))), int(_f(tx.get('sells')))
    pc = p.get('priceChange') or {}
    mcap = _f(p.get('marketCap') or p.get('fdv'))
    return (age_h is not None and age_h <= g['maxAgeH'] and g['minMcap'] <= mcap <= g['maxMcap'] and b + s_ >= g['minTxns1h']
            and _f((p.get('volume') or {}).get('h1')) >= g['minVol1h'] and b / (b + s_) * 100 >= g['minBuyShare'] and _f(pc.get('m5')) > 0 and _f(pc.get('h1')) > 0)
