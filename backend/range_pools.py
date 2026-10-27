"""🤖 RANGE POOLS — the concentrated pools AutoRange can really open in (owner 2026-10-26: "wire AutoRange's real opens and re-centers").

Two venues, each read from its OWN public API, normalized to one row the desk + the browser SDKs use:
  • Raydium CLMM  — api-v3.raydium.io/pools/info/mint (poolType=concentrated): fee tier, tick spacing, 24h volume + the fees LPs earned.
  • Meteora DLMM  — dlmm.datapi.meteora.ag/pools: bin step, base fee, 24h volume + fees, fee ÷ TVL.
`rate` = what $1 of the pool's liquidity earned in fees over the last 24h (fees_24h ÷ TVL) — the real number the AutoRange engine scales by
the band's edge. Pure: no network here (the service fetches + caches).
"""
from fnum import nan_safe as _f

SOL = 'So11111111111111111111111111111111111111112'
USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
MIN_TVL = 20000.0


def raydium(rows):
    out = []
    for r in rows or []:
        if not isinstance(r, dict) or str(r.get('type') or '').lower() != 'concentrated':
            continue
        a, b, day = r.get('mintA') or {}, r.get('mintB') or {}, r.get('day') or {}
        tvl, fees = _f(r.get('tvl')), _f(day.get('volumeFee'))
        if tvl < MIN_TVL or not r.get('id'):
            continue
        out.append({'venue': 'raydium', 'pool': r['id'], 'program': r.get('programId'), 'name': f"{a.get('symbol')}-{b.get('symbol')}",
                    'mintX': a.get('address'), 'mintY': b.get('address'), 'symX': a.get('symbol'), 'symY': b.get('symbol'),
                    'decX': a.get('decimals'), 'decY': b.get('decimals'), 'feePct': round(_f(r.get('feeRate')) * 100, 4),
                    'step': (r.get('config') or {}).get('tickSpacing'), 'tvl': round(tvl, 2), 'vol24': round(_f(day.get('volume')), 2),
                    'fees24': round(fees, 2), 'rate': fees / tvl if tvl > 0 else 0.0, 'price': _f(r.get('price'))})
    return out


def meteora(rows):
    out = []
    for r in rows or []:
        if not isinstance(r, dict) or r.get('is_blacklisted'):
            continue
        x, y, cfg = r.get('token_x') or {}, r.get('token_y') or {}, r.get('pool_config') or {}
        tvl, fees = _f(r.get('tvl')), _f((r.get('fees') or {}).get('24h'))
        if tvl < MIN_TVL or not r.get('address'):
            continue
        out.append({'venue': 'meteora', 'pool': r['address'], 'program': 'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo', 'name': r.get('name') or f"{x.get('symbol')}-{y.get('symbol')}",
                    'mintX': x.get('address'), 'mintY': y.get('address'), 'symX': x.get('symbol'), 'symY': y.get('symbol'),
                    'decX': x.get('decimals'), 'decY': y.get('decimals'), 'feePct': _f(cfg.get('base_fee_pct')), 'step': cfg.get('bin_step'),
                    'tvl': round(tvl, 2), 'vol24': round(_f((r.get('volume') or {}).get('24h')), 2), 'fees24': round(fees, 2),
                    'rate': fees / tvl if tvl > 0 else 0.0, 'price': _f(r.get('current_price'))})
    return out


def for_token(rows, mint, quote=None):
    """The rangeable pools holding `mint` (optionally paired with `quote`), deepest first."""
    hit = [r for r in rows if mint in (r.get('mintX'), r.get('mintY')) and (not quote or quote in (r.get('mintX'), r.get('mintY')))]
    return sorted(hit, key=lambda r: -r['tvl'])


def busiest(rows, n=8):
    """The pools paying the most fees per $ right now, among ones deep enough to range in (TVL ≥ $100K)."""
    return sorted([r for r in rows if r['tvl'] >= 100000 and r['rate'] > 0], key=lambda r: -r['rate'])[:n]


ALERT_EVERY = 2 * 3600   # one "move due" ping per band per 2 h at most


def watch_step(band, price, now):
    """One watcher pass for one armed band → (band updated, alert text or None). Out of range = the pool's own price outside [lo, hi];
    a ping only after it has sat out `wait` minutes (no paying for a wick), at most once per ALERT_EVERY, and the clock resets when it is back in."""
    b = dict(band or {})
    if not (price and price > 0) or not (b.get('lo', 0) > 0 and b.get('hi', 0) > b.get('lo', 0)):
        return b, None
    if b['lo'] <= price <= b['hi']:
        b.pop('outSince', None); b.pop('alertedAt', None)
        return b, None
    b['outSince'] = b.get('outSince') or now
    mins = (now - b['outSince']) / 60
    if mins < float(b.get('wait') or 15) or (b.get('alertedAt') and now - b['alertedAt'] < ALERT_EVERY):
        return b, None
    b['alertedAt'] = now
    side = 'above' if price > b['hi'] else 'below'
    return b, f"🤖 AutoRange: your {b.get('sym') or 'pool'} band has sat {side} its range for {int(mins)} min — it earns 0 out there. Tap to re-center (your wallet signs)."
