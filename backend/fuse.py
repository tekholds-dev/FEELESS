"""FUSE: fused pools. A Fuse is a named basket of live DEX pools with weights (e.g. SOL/USDC 40% · $FEE/SOL 40% ·
a hot meme 20%). Pure functions, no I/O — every number on a Fuse card comes from here, so it is tested once.

- index(): 100 at launch, then the weighted price move of the legs since launch (what the basket would be worth).
- score(): A–F grade from depth, turnover, volatility and on-chain safety, each component shown with its reason.
- split(): how a SOL amount is divided across legs for "Fuse in" (one normal wallet-signed swap per leg).
- creator_cut(): the creator's share of the FEELESS fee on a Fuse buy (tracked for payout, like FeeBack).
"""
import math

DEX_FEE_EST = 0.0025          # typical pool fee tier used for the APR estimate (shown as an estimate)
MAX_LEGS = 10                 # Cmd Ctr / admin Fuses
USER_MAX_LEGS = 3             # what a trader can fuse in the Fuse Lab
IMPACT_WARN_PCT = 1.0         # a leg bigger than ~1% of its pool's liquidity moves price noticeably
MAX_CREATOR_BPS = 5000        # a creator can take at most half of the FEELESS fee on their Fuse's buys


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def clean_legs(legs):
    """Validated legs: known chain + pair, positive weights normalised to 100, max MAX_LEGS, no duplicates."""
    seen, out = set(), []
    for leg in legs or []:
        pa, ch = str(leg.get('pairAddress') or '').strip(), str(leg.get('chainId') or '').strip()
        w = _f(leg.get('weight'))
        if not pa or not ch or w <= 0 or (ch, pa) in seen:
            continue
        seen.add((ch, pa))
        out.append({'chainId': ch, 'pairAddress': pa, 'weight': w, 'symbol': str(leg.get('symbol') or '')[:16]})
    out = out[:MAX_LEGS]
    total = sum(x['weight'] for x in out)
    for x in out:
        x['weight'] = round(x['weight'] / total * 100, 2) if total else 0
    return out


def leg_meta(pair):
    """What a Fuse card shows per leg, from a DexScreener pair."""
    liq = _f((pair.get('liquidity') or {}).get('usd')); vol = _f((pair.get('volume') or {}).get('h24'))
    tx = (pair.get('txns') or {}).get('h24') or {}
    buys, sells = _f(tx.get('buys')), _f(tx.get('sells'))
    return {'symbol': (pair.get('baseToken') or {}).get('symbol'), 'quote': (pair.get('quoteToken') or {}).get('symbol'),
            'baseAddress': (pair.get('baseToken') or {}).get('address'), 'quoteAddress': (pair.get('quoteToken') or {}).get('address'),
            'priceUsd': _f(pair.get('priceUsd')), 'liquidityUsd': liq, 'volume24h': vol, 'change24h': _f((pair.get('priceChange') or {}).get('h24')),
            'aprEst': round(vol * DEX_FEE_EST / liq * 365 * 100, 1) if liq > 0 else 0.0, 'turnover': round(vol / liq, 2) if liq > 0 else 0.0,
            'buyShare': round(buys / (buys + sells) * 100) if buys + sells else None, 'dex': pair.get('dexId'), 'url': pair.get('url')}


def index(legs, base_prices, prices_now):
    """100 at launch; weighted price ratio of every leg since then. Missing prices count as unchanged."""
    total = sum(leg['weight'] for leg in legs)
    if not total:
        return 100.0
    v = 0.0
    for leg in legs:
        k = leg['pairAddress']; b, n = _f(base_prices.get(k)), _f(prices_now.get(k))
        v += leg['weight'] * ((n / b) if b > 0 and n > 0 else 1.0)
    return round(v / total * 100, 2)


def score(metas, risky=0):
    """A–F: depth (combined liquidity), turnover (volume/liquidity, healthy 0.3–5×), volatility (weighted |24h move|),
    safety (legs flagged risky by forensics). Returns grade, 0–100 points and the reason for each part."""
    if not metas:
        return {'grade': 'F', 'points': 0, 'parts': []}
    liq = sum(m['liquidityUsd'] for m in metas)
    depth = min(30, math.log10(liq + 1) * 5)                                     # $1M ≈ 30
    turns = [m['turnover'] for m in metas]
    healthy = sum(1 for x in turns if 0.3 <= x <= 5) / len(turns)
    turnover = 25 * healthy
    vol = sum(abs(m['change24h']) for m in metas) / len(metas)
    calm = max(0.0, 25 - vol / 4)                                                # 100% daily swings → 0
    safety = max(0.0, 20 - 10 * risky)
    pts = round(depth + turnover + calm + safety)
    grade = 'A' if pts >= 80 else 'B' if pts >= 65 else 'C' if pts >= 50 else 'D' if pts >= 35 else 'F'
    return {'grade': grade, 'points': pts, 'parts': [
        {'part': 'depth', 'points': round(depth), 'why': f'${liq:,.0f} combined liquidity'},
        {'part': 'turnover', 'points': round(turnover), 'why': f'{round(healthy * 100)}% of legs trade 0.3–5× their liquidity a day'},
        {'part': 'volatility', 'points': round(calm), 'why': f'average 24h move {vol:.1f}%'},
        {'part': 'safety', 'points': round(safety), 'why': f'{risky} leg(s) flagged by launch forensics' if risky else 'no leg flagged by launch forensics'}]}


def split(amount_sol, legs):
    """SOL per leg for "Fuse in" (rounded to 6 dp, remainder on the biggest leg so it always sums exactly)."""
    amt = _f(amount_sol)
    if amt <= 0 or not legs:
        return []
    parts = [{'pairAddress': leg['pairAddress'], 'chainId': leg['chainId'], 'symbol': leg.get('symbol'), 'sol': round(amt * leg['weight'] / 100, 6)} for leg in legs]
    diff = round(amt - sum(p['sol'] for p in parts), 6)
    if parts and diff:
        big = max(parts, key=lambda p: p['sol']); big['sol'] = round(big['sol'] + diff, 6)
    return parts


def creator_cut(fee_usd, creator_bps):
    """Creator's share of the FEELESS fee on a Fuse buy (capped at MAX_CREATOR_BPS)."""
    bps = max(0, min(MAX_CREATOR_BPS, int(_f(creator_bps))))
    return round(_f(fee_usd) * bps / 10000, 6)


def real_pools(pairs):
    """Pool picker order: real pools only (24h volume > 0 and liquidity < 2,000× volume — parked/fake pools show huge
    'liquidity' with no trading), busiest first."""
    vol = lambda p: _f((p.get('volume') or {}).get('h24')); liq = lambda p: _f((p.get('liquidity') or {}).get('usd'))
    return sorted((p for p in pairs or [] if vol(p) > 0 and 0 < liq(p) < vol(p) * 2000), key=lambda p: -vol(p))


LENSES = ('popular', 'yield', 'deep', 'new')


def discover(pairs, lens='popular', chain='solana', now_ms=None, limit=30):
    """Fuse Lab pool browser: real pools on one chain, one row per pool, ranked by lens.
    popular = 24h volume · yield = fee APR est. (≥$25K liquidity so tiny pools can't top it) · deep = liquidity ·
    new = created in the last 72h, busiest first."""
    seen, rows = set(), []
    for p in real_pools(pairs):
        pa = p.get('pairAddress')
        if p.get('chainId') != chain or not pa or pa in seen:
            continue
        seen.add(pa)
        rows.append({'chainId': chain, 'pairAddress': pa, 'createdAt': p.get('pairCreatedAt'), 'logo': (p.get('info') or {}).get('imageUrl'),
                     'baseAddress': (p.get('baseToken') or {}).get('address'), **leg_meta(p)})
    if lens == 'yield':
        rows = sorted((r for r in rows if r['liquidityUsd'] >= 25_000), key=lambda r: -r['aprEst'])
    elif lens == 'deep':
        rows.sort(key=lambda r: -r['liquidityUsd'])
    elif lens == 'new':
        cut = (now_ms or 0) - 72 * 3600 * 1000
        rows = [r for r in rows if _f(r['createdAt']) and _f(r['createdAt']) >= cut]
    return rows[:limit]


def preview(pools, metas, sol, sol_usd, weights):
    """What one Fuse-in of `sol` SOL does across the picked pools (weights from fuse_vault.auto_weights): SOL + $ per pool,
    est. daily fee yield of each pool at that size, blended APR, grade. Weights are fractions summing to 1."""
    amt = max(0.0, _f(sol)); px = max(0.0, _f(sol_usd))
    legs = [{'pairAddress': p['pairAddress'], 'chainId': p.get('chainId', 'solana'), 'symbol': (metas.get(p['pairAddress']) or {}).get('symbol') or p.get('symbol'),
             'weight': round(_f(weights.get(p['pairAddress'])) * 100, 2)} for p in pools]
    parts = {x['pairAddress']: x['sol'] for x in split(amt, legs)}
    out, metas_ok = [], []
    for leg in legs:
        m = metas.get(leg['pairAddress']) or {}
        if m:
            metas_ok.append({**m, 'weight': leg['weight']})
        s = parts.get(leg['pairAddress'], 0.0)
        liq = _f(m.get('liquidityUsd'))
        out.append({**leg, **{k: m.get(k) for k in ('quote', 'liquidityUsd', 'volume24h', 'aprEst', 'change24h', 'dex', 'baseAddress', 'quoteAddress')}, 'sol': s, 'usd': round(s * px, 2),
                    'dailyUsd': round(s * px * min(400.0, _f(m.get('aprEst'))) / 100 / 365, 4), 'missing': not m,
                    'sizePct': round(s * px / liq * 100, 3) if liq > 0 else None})
    usd_in = amt * px
    apr = sum(x['weight'] * min(400.0, _f(x['aprEst'])) for x in out if not x['missing']) / max(1e-9, sum(x['weight'] for x in out if not x['missing'])) if metas_ok else 0.0
    return {'sol': amt, 'usd': round(usd_in, 2), 'solUsd': px, 'legs': out, 'blendedAprPct': round(apr, 1),
            'dailyUsd': round(sum(x['dailyUsd'] for x in out), 4), 'score': score(metas_ok),
            'backtest24hPct': round(sum(x['weight'] * _f(x['change24h']) for x in out if not x['missing']) / 100, 2),   # if fused 24h ago
            'impactWarn': [x['symbol'] for x in out if (x['sizePct'] or 0) > IMPACT_WARN_PCT]}


def legs_cap(is_admin):
    return MAX_LEGS if is_admin else USER_MAX_LEGS


def manual_weights(pools):
    """Cmd Ctr override: the admin's own weights (cleaned like any Fuse: positive, normalised), as fractions."""
    return {x['pairAddress']: x['weight'] / 100 for x in clean_legs(pools)}


# ---- 🧬 Fuse Evolution: breed baskets over generations (pure, seeded, tested) ------------------------------------
# Genome = a set of pools. Fitness = the strategy's mix of grade, fee APR, 24h momentum, minus a size-impact penalty and
# a fee-drag penalty (network fees eat tiny buys). Each generation keeps the elite, breeds the rest by crossover +
# mutation. Nothing here predicts profit: it ranks baskets on the same cited numbers the Lab shows.
STYLES = {   # weights for (grade points 0–100, APR 0–100 scaled, momentum 24h %, stability)
    'yield': {'grade': .35, 'apr': .55, 'momo': .0, 'calm': .10},
    'momentum': {'grade': .30, 'apr': .15, 'momo': .45, 'calm': .10},
    'steady': {'grade': .55, 'apr': .15, 'momo': .0, 'calm': .30},
    'degen': {'grade': .15, 'apr': .40, 'momo': .45, 'calm': .0},
}
NET_FEE_SOL = 0.0001          # ≈ base + capped priority fee per swap (estimate for fee drag)


def min_share(n):
    """Floor per pool: 10% for small fuses, shrinking for big Cmd Ctr fuses so weights can still differ (≤ half of equal)."""
    return min(0.1, 0.5 / max(1, n))


def _weights_for(genome, metas):
    import fuse_vault   # local import keeps fuse.py importable on its own
    return fuse_vault.auto_weights([{'pairAddress': pa, 'weight': 1} for pa in genome], metas, min_share=min_share(len(genome)))


def fitness(genome, metas, style='yield', sol=0.05, sol_usd=150.0):
    """Score one basket. Returns {fitness, parts} — every part is shown in the UI."""
    st = STYLES.get(style, STYLES['yield'])
    w = _weights_for(genome, metas)
    ms = [{**metas[pa], 'weight': w[pa] * 100} for pa in genome]
    sc = score(ms)
    apr = sum(w[pa] * min(400.0, _f(metas[pa].get('aprEst'))) for pa in genome) / 4      # 0–100
    momo = max(-50.0, min(50.0, sum(w[pa] * _f(metas[pa].get('change24h')) for pa in genome)))
    calm = max(0.0, 100 - sum(abs(_f(metas[pa].get('change24h'))) for pa in genome) / len(genome) * 2)
    impact = sum(1 for pa in genome if _f(metas[pa].get('liquidityUsd')) > 0 and sol * w[pa] * sol_usd / _f(metas[pa]['liquidityUsd']) * 100 > IMPACT_WARN_PCT)
    drag = (NET_FEE_SOL * len(genome)) / sol * 100 if sol > 0 else 100.0          # % of the buy lost to network fees
    bases = [metas[pa].get('baseAddress') or metas[pa].get('symbol') for pa in genome]
    dupes = len(bases) - len(set(bases))
    f = st['grade'] * sc['points'] + st['apr'] * apr + st['momo'] * momo * 2 + st['calm'] * calm - 15 * impact - 10 * dupes - min(40.0, drag * 2)
    return {'fitness': round(f, 2), 'parts': {'grade': sc['grade'], 'points': sc['points'], 'aprScore': round(apr, 1), 'momentum24h': round(momo, 2),
                                             'calm': round(calm, 1), 'impactLegs': impact, 'dupes': dupes, 'feeDragPct': round(drag, 2)}}


def evolve(metas, legs=3, generations=12, population=24, style='yield', sol=0.05, sol_usd=150.0, seed=7, seeds=()):
    """Genetic search over baskets of `legs` pools. Returns per-generation best/avg (the evolution chart), the top 3
    champions with their fitness breakdown, and a lineage line for the winner."""
    import random
    rng = random.Random(seed)
    pool = sorted(metas)
    legs = max(2, min(MAX_LEGS, int(legs), len(pool)))
    if len(pool) < 2:
        return {'history': [], 'champions': [], 'pool': len(pool)}
    key = lambda g: tuple(sorted(g))
    cache = {}
    def fit(g):
        k = key(g)
        if k not in cache:
            cache[k] = fitness(list(k), metas, style, sol, sol_usd)
        return cache[k]['fitness']
    pop = [list(g) for g in seeds if len(set(g)) == legs and all(p in metas for p in g)][:population // 2]   # bloodline
    pop += [rng.sample(pool, legs) for _ in range(population - len(pop))]
    history, born = [], {}
    for gen in range(generations):
        pop = sorted({key(g): g for g in pop}.values(), key=lambda g: -fit(g))
        for g in pop:
            born.setdefault(key(g), gen)
        scores = [fit(g) for g in pop]
        history.append({'gen': gen, 'best': scores[0], 'avg': round(sum(scores) / len(scores), 2), 'unique': len(pop)})
        elite = pop[:max(2, population // 5)]
        nxt = [list(g) for g in elite]
        while len(nxt) < population:
            a, b = rng.sample(elite + pop[:population // 2], 2)
            child = list(dict.fromkeys(rng.sample(a, legs // 2 + 1) + [x for x in b if x not in a]))[:legs]   # crossover
            while len(child) < legs:
                child.append(rng.choice([p for p in pool if p not in child]))
            if rng.random() < 0.35:                                                                         # mutation
                child[rng.randrange(legs)] = rng.choice([p for p in pool if p not in child] or child)
            nxt.append(list(dict.fromkeys(child)) if len(set(child)) == legs else rng.sample(pool, legs))
        pop = nxt
    final = sorted({key(g): g for g in pop}.values(), key=lambda g: -fit(g))[:3]
    champs = [{'pools': list(key(g)), 'bornGen': born.get(key(g), generations - 1), **cache[key(g)],
               'weights': {k: round(v * 100, 1) for k, v in _weights_for(list(key(g)), metas).items()}} for g in final]
    return {'history': history, 'champions': champs, 'pool': len(pool), 'style': style, 'legs': legs, 'evaluated': len(cache)}
