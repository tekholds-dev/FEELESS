"""🧲 FEEDERS — Pump, 2026-10-08: "any newly launched tokens which are paired with an existing runner will directly route every single
buy through the runner's pool, generating more buy pressure and deeper liquidity for the existing community."

So a runner with new coins launching AGAINST it gets bought every time one of those coins is bought. Pump's own coin record says which
coin a launch is paired with (`quote_mint`; the all-ones address / wrapped SOL = plain SOL). This module turns Pump's newest + most
recently traded coins into, per runner: how many coins are paired with it, how many are brand new, how many traded in the last few
minutes and how much cap sits on top of it — the FEED. Pure, tested. A read of where buys are being routed, never a promise.
"""
NATIVE = {'11111111111111111111111111111111', 'So11111111111111111111111111111111111111112'}
DOLLARS = {'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB', 'USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB',
           '2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo'}
FRESH_MIN = 60        # a paired coin under an hour old counts as a fresh feeder
ACTIVE_MIN = 5        # ... and one traded in the last 5 minutes is feeding right now
KIDS_MAX = 6
SOURCES = (('created_timestamp', (0, 50, 100, 150)), ('last_trade_timestamp', (0, 50, 100, 150)))   # Pump /coins pages read for it


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def _ms(v):
    t = _f(v)
    return t if t > 1e12 else t * 1000


def paired(coin):
    """The coin a Pump launch is paired with (its buys route through that coin's pool), or None for a plain SOL / dollar pair."""
    q = (coin or {}).get('quote_mint') if isinstance(coin, dict) else None
    if not isinstance(q, str) or not q.isalnum() or not 32 <= len(q) <= 44 or q in NATIVE or q in DOLLARS or q == coin.get('mint'):
        return None
    return q


def feed_score(n, fresh, active, cap_usd):
    """0–100: how hard new launches are feeding a runner — paired coins, how many are new, how many are trading NOW, the cap riding on it."""
    raw = min(1.0, n / 10) * 35 + min(1.0, fresh / 5) * 20 + min(1.0, active / 4) * 30 + min(1.0, cap_usd / 100_000) * 15
    return int(round(max(0.0, min(100.0, raw))))


def board(coins, now_ms=0.0):
    """→ {'runners': {runner mint: {n, fresh, active, capUsd, score, kids}}, 'kids': {coin mint: runner mint}, 'seen': coins read}."""
    by, kids, seen = {}, {}, set()
    for c in coins or []:
        if not isinstance(c, dict):
            continue
        m = c.get('mint')
        if not isinstance(m, str) or m in seen or c.get('is_banned') or c.get('nsfw'):
            continue
        seen.add(m)
        q = paired(c)
        if not q:
            continue
        born, last = _ms(c.get('created_timestamp')), _ms(c.get('last_trade_timestamp'))
        age = (now_ms - born) / 60000 if now_ms and born else None
        quiet = (now_ms - last) / 60000 if now_ms and last else None
        kids[m] = q
        by.setdefault(q, []).append({'mint': m, 'symbol': str(c.get('symbol') or '')[:16], 'mcap': round(_f(c.get('usd_market_cap'))), 'ageMin': None if age is None else round(max(0.0, age)),
                                     'lastMin': None if quiet is None else round(max(0.0, quiet), 1), 'graduated': bool(c.get('complete'))})
    runners = {}
    for q, ks in by.items():
        fresh = sum(1 for k in ks if k['ageMin'] is not None and k['ageMin'] <= FRESH_MIN)
        active = sum(1 for k in ks if k['lastMin'] is not None and k['lastMin'] <= ACTIVE_MIN)
        cap = sum(k['mcap'] for k in ks)
        ks.sort(key=lambda k: (k['lastMin'] is None, k['lastMin'] if k['lastMin'] is not None else 1e9, -k['mcap']))
        runners[q] = {'n': len(ks), 'fresh': fresh, 'active': active, 'capUsd': cap, 'score': feed_score(len(ks), fresh, active, cap), 'kids': ks[:KIDS_MAX]}
    return {'runners': runners, 'kids': kids, 'seen': len(seen)}


def ranked(b, min_n=2):
    """Runner mints with at least `min_n` paired coins, hardest-fed first."""
    rs = (b or {}).get('runners') or {}
    return sorted((m for m, r in rs.items() if r['n'] >= min_n), key=lambda m: (-rs[m]['score'], -rs[m]['n']))


def label(r):
    """One line under the ticker: '🧲 13 coins paired · 4 trading now'."""
    r = r or {}
    n, a, f = int(_f(r.get('n'))), int(_f(r.get('active'))), int(_f(r.get('fresh')))
    return f"🧲 {n} coin{'' if n == 1 else 's'} paired" + (f" · {a} trading now" if a else '') + (f" · {f} new this hour" if f else '')
