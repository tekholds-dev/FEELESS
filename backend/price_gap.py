"""📐 PRICE GAPS — the same token priced differently across its pools (owner 2026-10-29, L02, the lootcollector.online idea: "identify price
gaps … add-on to AutoCompound / pools / Night Vault to speed up daily earnings"). Pure, tested (tests/test_price_gap.py). READ-ONLY: it
never trades, never routes, never signs.

From one DexScreener /token-pairs read per token (the TOKENS deepest) of the tokens the Night Vault's pools hold: every pool of each token with a real pool (≥ MIN_LIQ), real
volume (≥ MIN_VOL a day) and trades this hour — its USD price for THAT token (base side = priceUsd; quote side = priceUsd ÷ priceNative).
gap = richest ÷ cheapest − 1; net = gap − a swap's cost on each side (COST_PCT). A gap only counts as OPEN once it is still there on the next
read (`persist`): one stale DexScreener row is not a gap. What a holder does with it: compound / enter through the cheap pool (Jupiter routes
there for you), and a gap that stays open is arbitrage volume — fees for that pool's LPs."""

MIN_LIQ = 30_000.0   # (owner 2026-10-31: "way more price gap options") — still a real pool, never dust
MIN_VOL = 5_000.0
MIN_TX1H = 5
COST_PCT = 0.3          # % per swap leg: pool fee + slippage at a small size
SHOW = 30               # tokens returned, widest gap first
POOLS = 6               # pools drawn per token
FORGET_SEC = 900.0      # a gap not seen for 15 min is forgotten
TOKENS = 30             # tokens read a minute (one DexScreener /token-pairs read each, in parallel — 30/min, far under its 300/min)
QUOTES = {'So11111111111111111111111111111111111111112': 'SOL', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'USDC',
          'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB': 'USDT'}   # a pool counts only against a quote whose USD price is solid (an exotic stable invents gaps)


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def pool_px(p, mint):
    """The USD price of `mint` in pair `p` (None when the pair does not hold it or has no price)."""
    b, q = (p.get('baseToken') or {}).get('address'), (p.get('quoteToken') or {}).get('address')
    usd, nat = _f(p.get('priceUsd')), _f(p.get('priceNative'))
    if usd <= 0:
        return None
    if b == mint:
        return usd
    if q == mint and nat > 0:
        return usd / nat
    return None


def _ok(p):
    return (_f((p.get('liquidity') or {}).get('usd')) >= MIN_LIQ and _f((p.get('volume') or {}).get('h24')) >= MIN_VOL
            and sum(_f(v) for v in ((p.get('txns') or {}).get('h1') or {}).values()) >= MIN_TX1H)


def gaps(pairs, mints, cost=COST_PCT):
    """DexScreener pairs + the mints to judge → [{mint, sym, n, lo, hi, gapPct, netPct, pools}] widest gap first. Tokens with under two
    real pools are left out (no gap to measure)."""
    out = []
    want = set(mints or ())
    for m in want:
        rows, sym = [], None
        for p in pairs or []:
            if not isinstance(p, dict) or p.get('chainId', 'solana') != 'solana' or not _ok(p):
                continue
            px = pool_px(p, m)
            ends = {(p.get('baseToken') or {}).get('address'), (p.get('quoteToken') or {}).get('address')}
            if px is None or not (ends - {m}) & set(QUOTES):
                continue
            side = p.get('baseToken') if (p.get('baseToken') or {}).get('address') == m else p.get('quoteToken')
            other = p.get('quoteToken') if side is p.get('baseToken') else p.get('baseToken')
            sym = sym or (side or {}).get('symbol')
            rows.append({'dex': p.get('dexId'), 'pair': p.get('pairAddress'), 'px': px, 'liq': round(_f((p.get('liquidity') or {}).get('usd'))),
                         'vs': (other or {}).get('symbol')})
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: r['px'])
        lo, hi = rows[0], rows[-1]
        gap = (hi['px'] / lo['px'] - 1) * 100
        deep = sorted(rows, key=lambda r: -r['liq'])[:POOLS]
        out.append({'mint': m, 'sym': sym, 'n': len(rows), 'lo': lo, 'hi': hi, 'gapPct': round(gap, 3), 'netPct': round(gap - 2 * cost, 3),
                    'pools': [{**r, 'at': round((r['px'] / lo['px'] - 1) * 100, 3)} for r in sorted(deep, key=lambda r: r['px'])]})
    out.sort(key=lambda g: -g['gapPct'])
    return out[:SHOW]


def persist(book, rows, now):
    """A gap is OPEN only once it beats its costs on two reads in a row (one stale row is not a gap). Marks each row `open` + `openSec`;
    `book` = {mint: {since, seen}} (memory only)."""
    for g in rows or []:
        e = book.get(g['mint'])
        if g['netPct'] > 0:
            if not e:
                e = book[g['mint']] = {'since': now, 'seen': now, 'n': 0}
            e['seen'], e['n'] = now, e['n'] + 1
            g['open'] = e['n'] >= 2
            g['openSec'] = round(now - e['since']) if g['open'] else 0
        else:
            book.pop(g['mint'], None)
            g['open'], g['openSec'] = False, 0
    for m in [k for k, v in book.items() if now - _f(v.get('seen')) > FORGET_SEC]:
        book.pop(m, None)
    return rows
