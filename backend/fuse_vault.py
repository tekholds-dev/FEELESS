"""FUSE Vault engine: one vault, up to 3 yield pools (v2 constant-product and/or v3 concentrated), SOL in → shares out.

Pure functions, no I/O. This is the spec the on-chain program (`programs/fuse_vault`) mirrors, so every rule is tested
here first. Amounts are in SOL; pool depth (TVL) in USD with sol_usd to convert.

Mechanics
- shares: first deposit mints 1 share per SOL; later deposits mint at NAV per share (no dilution).
- auto_weights(): each pool's live weight = its base weight × yield score × depth score, normalised. A pool whose fee
  APR collapses or whose depth thins is scaled down automatically; a strong one is scaled up (bounded so one pool
  never takes everything).
- allocate(): new SOL goes to pools by live weight, but never past a pool's cap (max % of that pool's TVL, so the
  vault never becomes the market). What doesn't fit spills to pools with room; the rest stays as an idle buffer.
- capacity(): how big the vault can get before every cap binds.
- rebalance(): moves that bring positions back to target when drift > threshold; v3 positions that drift out of
  their price range are flagged to recenter.
- fees(): management fee (yearly bps, accrued by time) + performance fee (bps of gains above the high-water mark),
  paid in SOL to the FEELESS fee wallet set in Command Center › Trading & fees.
- withdraw(): shares → SOL at NAV, taken from the buffer first, then pro-rata from positions.
"""
import math

MAX_POOLS = 3
YEAR = 365 * 86400
KINDS = ('v2', 'v3')


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def kind_of(pair):
    """v3 = concentrated liquidity (CLMM / Whirlpool / DLMM / 'v3' labels), else v2 constant product."""
    tags = ' '.join([str(pair.get('dexId') or '')] + [str(x) for x in (pair.get('labels') or [])]).lower()
    return 'v3' if any(k in tags for k in ('clmm', 'whirlpool', 'dlmm', 'v3', 'concentrated')) else 'v2'


def clean_pools(pools):
    out, seen = [], set()
    for p in pools or []:
        pa = str(p.get('pairAddress') or '').strip()
        if not pa or pa in seen:
            continue
        seen.add(pa)
        kind = p.get('kind') if p.get('kind') in KINDS else 'v2'
        out.append({'pairAddress': pa, 'chainId': p.get('chainId') or 'solana', 'symbol': str(p.get('symbol') or '')[:16], 'kind': kind,
                    'venue': str(p.get('venue') or p.get('dex') or '')[:24], 'weight': max(1.0, _f(p.get('weight')) or 1.0),
                    'capPct': min(10.0, max(0.1, _f(p.get('capPct')) or 2.0)),                   # max % of the pool's TVL
                    'rangePct': min(100.0, max(2.0, _f(p.get('rangePct')) or 20.0)) if kind == 'v3' else None})
    return out[:MAX_POOLS]


def auto_weights(pools, meta, apr_cap=400.0, min_share=0.1, max_share=0.7):
    """Live weights: base × yield score (fee APR, capped) × depth score (log TVL). Bounded to [min_share, max_share] so the
    vault stays diversified, then normalised to 1. Pools with no live data get the minimum."""
    raw = {}
    for p in pools:
        m = meta.get(p['pairAddress']) or {}
        apr = min(apr_cap, max(0.0, _f(m.get('aprEst'))))
        depth = math.log10(max(1.0, _f(m.get('liquidityUsd'))))
        raw[p['pairAddress']] = p['weight'] * (0.25 + apr / apr_cap) * depth if m else 0.0
    total = sum(raw.values())
    if not total:
        return {k: 1 / len(pools) for k in raw} if pools else {}
    w = {k: v / total for k, v in raw.items()}
    for _ in range(10):   # clamp to [min,max] and redistribute the excess until stable
        over = {k: v for k, v in w.items() if v > max_share}; under = {k: v for k, v in w.items() if v < min_share}
        if not over and not under:
            break
        for k in over: w[k] = max_share
        for k in under: w[k] = min_share
        free = [k for k in w if k not in over and k not in under]
        rest = 1 - sum(w[k] for k in over) - sum(w[k] for k in under)
        base = sum(w[k] for k in free)
        for k in free:
            w[k] = rest * (w[k] / base) if base else rest / len(free)
    s = sum(w.values())
    return {k: round(v / s, 6) for k, v in w.items()}


def caps_sol(pools, meta, positions, sol_usd):
    """SOL each pool can still take before hitting its cap (capPct of the pool's TVL, minus what the vault holds)."""
    out = {}
    for p in pools:
        tvl = _f((meta.get(p['pairAddress']) or {}).get('liquidityUsd'))
        cap = (tvl * p['capPct'] / 100) / sol_usd if sol_usd > 0 else 0.0
        out[p['pairAddress']] = max(0.0, cap - _f(positions.get(p['pairAddress'])))
    return out


def allocate(sol, weights, room):
    """Split new SOL by weight, never past a pool's room; overflow re-spread to pools with room; leftover = buffer."""
    left = _f(sol); alloc = {k: 0.0 for k in weights}; active = {k for k in weights if room.get(k, 0) > 1e-12}
    for _ in range(MAX_POOLS + 1):
        if left <= 1e-12 or not active:
            break
        wsum = sum(weights[k] for k in active)
        spent = 0.0
        for k in list(active):
            want = left * weights[k] / wsum if wsum else 0.0
            take = min(want, room[k] - alloc[k])
            alloc[k] += take; spent += take
            if room[k] - alloc[k] <= 1e-12:
                active.discard(k)
        left -= spent
        if spent <= 1e-12:
            break
    return {k: round(v, 9) for k, v in alloc.items()}, round(max(0.0, left), 9)


def capacity(pools, meta, sol_usd):
    """Largest vault (SOL) before every pool's cap binds."""
    return round(sum(caps_sol(pools, meta, {}, sol_usd).values()), 6)


def nav(positions, buffer_sol):
    return round(sum(_f(v) for v in positions.values()) + _f(buffer_sol), 9)


def shares_for_deposit(sol, total_shares, nav_sol):
    sol = _f(sol)
    if sol <= 0:
        return 0.0
    return round(sol if total_shares <= 0 or nav_sol <= 0 else sol * total_shares / nav_sol, 9)


def withdraw(shares, total_shares, positions, buffer_sol):
    """SOL out for `shares` at NAV: buffer first, then pro-rata from positions. Returns (sol_out, take_from_each, new_buffer)."""
    if shares <= 0 or total_shares <= 0:
        return 0.0, {}, _f(buffer_sol)
    v = nav(positions, buffer_sol); out = v * min(1.0, shares / total_shares)
    from_buf = min(out, _f(buffer_sol)); rest = out - from_buf
    pos_total = sum(_f(x) for x in positions.values())
    take = {k: round(rest * _f(x) / pos_total, 9) for k, x in positions.items()} if pos_total > 0 and rest > 0 else {}
    return round(out, 9), take, round(_f(buffer_sol) - from_buf, 9)


def rebalance(positions, buffer_sol, weights, threshold=0.05, v3_out_of_range=()):
    """Moves (SOL, + = add, − = remove) toward target weights when any pool drifts past `threshold`; v3 pools out of
    range are always recentered (withdraw + re-add)."""
    v = nav(positions, buffer_sol)
    if v <= 0:
        return {'moves': {}, 'drift': 0.0, 'recenter': list(v3_out_of_range)}
    drift = max((abs(_f(positions.get(k)) / v - w) for k, w in weights.items()), default=0.0)
    moves = {k: round(w * v - _f(positions.get(k)), 9) for k, w in weights.items()} if drift > threshold else {}
    return {'moves': moves, 'drift': round(drift, 4), 'recenter': list(v3_out_of_range)}


def fees(nav_sol, total_shares, hwm_per_share, mgmt_bps, perf_bps, seconds):
    """FEELESS fees in SOL: management (yearly bps × time) + performance (bps of gains above the high-water mark).
    Returns (fee_sol, new_hwm_per_share)."""
    if total_shares <= 0 or nav_sol <= 0:
        return 0.0, hwm_per_share
    mgmt = nav_sol * max(0, mgmt_bps) / 10000 * max(0.0, seconds) / YEAR
    pps = (nav_sol - mgmt) / total_shares
    perf = max(0.0, pps - hwm_per_share) * total_shares * max(0, perf_bps) / 10000 if hwm_per_share > 0 else 0.0
    new_hwm = max(hwm_per_share, (nav_sol - mgmt - perf) / total_shares) if hwm_per_share > 0 else (nav_sol - mgmt) / total_shares
    return round(mgmt + perf, 9), round(new_hwm, 12)


def simulate(pools, meta, sol_usd, deposit_sol, mgmt_bps, perf_bps):
    """Command Center simulator: where a deposit goes, what spills to the buffer, vault capacity, blended APR, and the
    yearly FEELESS fee at that size (management + performance on the blended APR)."""
    w = auto_weights(pools, meta)
    room = caps_sol(pools, meta, {}, sol_usd)
    alloc, buf = allocate(deposit_sol, w, room)
    placed = sum(alloc.values())
    apr = sum(alloc[k] * min(400.0, _f((meta.get(k) or {}).get('aprEst'))) for k in alloc) / placed if placed else 0.0
    yearly_yield = placed * apr / 100
    fee_year = deposit_sol * mgmt_bps / 10000 + max(0.0, yearly_yield) * perf_bps / 10000
    return {'weights': w, 'allocation': alloc, 'bufferSol': buf, 'capacitySol': capacity(pools, meta, sol_usd), 'blendedAprPct': round(apr, 1),
            'yearlyYieldSol': round(yearly_yield, 4), 'yearlyFeeSol': round(fee_year, 4)}
