"""FUSE: fused pools. A Fuse is a named basket of live DEX pools with weights (e.g. SOL/USDC 40% · $FEE/SOL 40% ·
a hot meme 20%). Pure functions, no I/O — every number on a Fuse card comes from here, so it is tested once.

- index(): 100 at launch, then the weighted price move of the legs since launch (what the basket would be worth).
- score(): A–F grade from depth, turnover, volatility and on-chain safety, each component shown with its reason.
- split(): how a SOL amount is divided across legs for "Fuse in" (one normal wallet-signed swap per leg).
- creator_cut(): the creator's share of the FEELESS fee on a Fuse buy (tracked for payout, like FeeBack).
"""
import math

DEX_FEE_EST = 0.0025          # typical pool fee tier used for the APR estimate (shown as an estimate)
MAX_LEGS = 12                 # HQ / admin Fuses (pools + runners together: 6/6, 12 pools or 12 runners)
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


def replay_window(pair, now_ms=None):
    """Honest "last 24h" for a pool: DexScreener's h24 on a pool YOUNGER than 24h is the move since launch (thousands of %),
    so use the newest full window the pool has lived through: 24h → 6h → 1h → 5m. → (pct, hours)."""
    import time as _t
    pc = pair.get('priceChange') or {}
    created = _f(pair.get('pairCreatedAt'))
    age_h = ((now_ms or _t.time() * 1000) - created) / 3.6e6 if created else None
    for key, hours in (('h24', 24), ('h6', 6), ('h1', 1), ('m5', 1 / 12)):
        if age_h is None or age_h >= hours:
            return _f(pc.get(key)), hours
    return 0.0, 0


def dex_paid(pair):
    """💳 DEX paid: DexScreener only shows a token's header / image / links once its team PAID for the token profile
    (Enhanced Token Info) — a cheap, public 'somebody stands behind this' signal. Boosts count too."""
    info = pair.get('info') or {}
    return bool(info.get('header') or _f((pair.get('boosts') or {}).get('active')) > 0 or (info.get('imageUrl') and info.get('websites') and info.get('socials')))


def leg_meta(pair):
    """What a Fuse card shows per leg, from a DexScreener pair."""
    liq = _f((pair.get('liquidity') or {}).get('usd')); vol = _f((pair.get('volume') or {}).get('h24'))
    tx = (pair.get('txns') or {}).get('h24') or {}
    buys, sells = _f(tx.get('buys')), _f(tx.get('sells'))
    return {'symbol': (pair.get('baseToken') or {}).get('symbol'), 'quote': (pair.get('quoteToken') or {}).get('symbol'),
            'baseAddress': (pair.get('baseToken') or {}).get('address'), 'quoteAddress': (pair.get('quoteToken') or {}).get('address'),
            'priceUsd': _f(pair.get('priceUsd')), 'liquidityUsd': liq, 'volume24h': vol, 'change24h': _f((pair.get('priceChange') or {}).get('h24')),
            'aprEst': round(vol * DEX_FEE_EST / liq * 365 * 100, 1) if liq > 0 else 0.0, 'turnover': round(vol / liq, 2) if liq > 0 else 0.0,
            'buyShare': round(buys / (buys + sells) * 100) if buys + sells else None, 'dex': pair.get('dexId'), 'url': pair.get('url'),
            'change1h': _f((pair.get('priceChange') or {}).get('h1')), 'change5m': None if (pair.get('priceChange') or {}).get('m5') is None else _f((pair.get('priceChange') or {}).get('m5')), 'change6h': _f((pair.get('priceChange') or {}).get('h6')),
            'paid': dex_paid(pair), 'boosts': int(_f((pair.get('boosts') or {}).get('active'))),
            **dict(zip(('replayPct', 'replayH'), replay_window(pair)))}


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


def curve_liq(mcap_usd, sol_px=100.0):
    """💧 A Pump.fun coin still on its launch CURVE has no pool, but it is tradable: the curve is a constant-product market with
    virtual reserves (30 SOL against 1.073B coins at launch). Its depth follows from the market cap alone:
    quote reserve (SOL) = √(32.19 × market cap in SOL) → "liquidity" = 2 × that, in $. $37K cap ≈ $24K. Unknown SOL price = $100
    (reads a little thin, never deep)."""
    m, s = _f(mcap_usd), _f(sol_px) or 100.0
    return round(2 * (32.19 * m * s) ** 0.5, 2) if m > 0 else 0.0


# launch curves with no pool figure on DexScreener: Pump.fun, Meteora DBC (stonk.fun & co), LaunchLab, Moonshot. The depth is an
# ESTIMATE from the cap (Pump's curve shape); the keeper's real quote — price gap, sell-back, impact — is what decides a buy.
CURVE_DEXES = ('pumpfun', 'meteoradbc', 'launchlab', 'raydium-launchlab', 'moonshot')


def with_curve(pair, sol_px=100.0):
    """A DexScreener pair of a coin on the Pump curve (no liquidity figure) → the same pair with its curve depth filled in and
    `curve: True`. Any other pair is returned untouched."""
    p = pair if isinstance(pair, dict) else {}
    if p.get('dexId') not in CURVE_DEXES or _f((p.get('liquidity') or {}).get('usd')) > 0 or _f(p.get('priceUsd')) <= 0:
        return pair
    liq = curve_liq(p.get('marketCap') or p.get('fdv'), sol_px)
    return {**p, 'liquidity': {**(p.get('liquidity') or {}), 'usd': liq}, 'curve': True} if liq > 0 else pair


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
        out.append({**leg, **{k: m.get(k) for k in ('quote', 'liquidityUsd', 'volume24h', 'aprEst', 'change24h', 'replayPct', 'replayH', 'dex', 'baseAddress', 'quoteAddress')}, 'sol': s, 'usd': round(s * px, 2),
                    'dailyUsd': round(s * px * min(400.0, _f(m.get('aprEst'))) / 100 / 365, 4), 'missing': not m,
                    'sizePct': round(s * px / liq * 100, 3) if liq > 0 else None})
    usd_in = amt * px
    apr = sum(x['weight'] * min(400.0, _f(x['aprEst'])) for x in out if not x['missing']) / max(1e-9, sum(x['weight'] for x in out if not x['missing'])) if metas_ok else 0.0
    return {'sol': amt, 'usd': round(usd_in, 2), 'solUsd': px, 'legs': out, 'blendedAprPct': round(apr, 1),
            'dailyUsd': round(sum(x['dailyUsd'] for x in out), 4), 'score': score(metas_ok),
            'backtest24hPct': round(sum(x['weight'] * _f(x['replayPct'] if x.get('replayPct') is not None else x['change24h']) for x in out if not x['missing']) / 100, 2),   # honest window per pool
            'impactWarn': [x['symbol'] for x in out if (x['sizePct'] or 0) > IMPACT_WARN_PCT]}


def legs_cap(is_admin):
    return MAX_LEGS if is_admin else USER_MAX_LEGS


def manual_weights(pools):
    """HQ override: the admin's own weights (cleaned like any Fuse: positive, normalised), as fractions."""
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
    # 📉 buy the dip: coins down on the day whose buyers are back (1h green, buys ≥ 55%) — the bounce, never a falling knife
    'dip': {'grade': .30, 'apr': .10, 'momo': .0, 'calm': .0, 'dip': .60},
    # 💳 pump meta: momentum + DEX-paid profiles / boosts (a team paid to be seen) + real flow
    'meta': {'grade': .25, 'apr': .10, 'momo': .35, 'calm': .0, 'paid': .30},
}

# 🧬 BRED strategies: weight sets the engine made itself from the arena's own record (`breed_style`). The service fills this from
# fuse_hq.json; they run in the arena like any style and are scrapped when they lose (`fuse_hq.bred_cycle`).
BRED = {}
GENES = ('grade', 'apr', 'momo', 'calm', 'dip', 'paid')
GENE_MIN, GENE_MAX = {'momo': -0.30}, 0.80   # only momentum may go negative (= fade what already ran)


def style_weights(style):
    return STYLES.get(style) or BRED.get(style) or STYLES['yield']


def breed_style(board, table, seed=0, step=0.5, min_runs=3):
    """🧬 One NEW strategy from the record: start at the best judged style's weights and move further along the line from the worst
    to the best (what the winner does more of, the child does even more; what the loser leans on, less), plus a small seeded
    wobble so two children are never the same. board = arena_board rows; table = {style: weights} of every style ever judged.
    Returns {weights, parent, against} or None when fewer than two styles have a record. Ranking only — never a promise."""
    import random
    judged = [r for r in board or [] if r.get('style') in table and int(r.get('runs') or 0) >= min_runs]
    if len(judged) < 2:
        return None
    rank = lambda r: (_f(r.get('medPct', r.get('avgPct'))), _f(r.get('avgPct')))
    best, worst = max(judged, key=rank), min(judged, key=rank)
    b, w = table[best['style']], table[worst['style']]
    rng = random.Random(f"{seed}:{best['style']}:{worst['style']}")
    taken = {tuple(round(_f(t.get(g)), 2) for g in GENES) for t in table.values()}
    for _ in range(12):
        raw = {g: max(GENE_MIN.get(g, 0.0), min(GENE_MAX, _f(b.get(g)) + step * (_f(b.get(g)) - _f(w.get(g))) + rng.uniform(-0.06, 0.06))) for g in GENES}
        tot = sum(abs(v) for v in raw.values()) or 1.0
        child = {g: round(v / tot, 2) for g, v in raw.items()}
        if tuple(child[g] for g in GENES) not in taken and sum(v for v in child.values() if v > 0) > 0:
            return {'weights': child, 'parent': best['style'], 'against': worst['style']}
    return None



def dip_score(m):
    """0–100 per coin: how good a dip-buy it is right now. Needs a real drop (24h ≤ −8%) AND buyers back (1h ≥ 0, buys ≥ 55%);
    a coin still dumping (1h red or sellers in charge) only gets 30% of the points."""
    ch = _f(m.get('change24h'))
    if ch > -8:
        return 0.0
    back = _f(m.get('change1h')) >= 0 and _f(m.get('buyShare')) >= 55
    return round(min(40.0, -ch) * 2.5 * (1.0 if back else 0.3), 1)
NET_FEE_SOL = 0.0001          # ≈ base + capped priority fee per swap (estimate for fee drag)


def min_share(n):
    """Floor per pool: 10% for small fuses, shrinking for big HQ fuses so weights can still differ (≤ half of equal)."""
    return min(0.1, 0.5 / max(1, n))


def _weights_for(genome, metas):
    import fuse_vault   # local import keeps fuse.py importable on its own
    return fuse_vault.auto_weights([{'pairAddress': pa, 'weight': 1} for pa in genome], metas, min_share=min_share(len(genome)))


def fitness(genome, metas, style='yield', sol=0.05, sol_usd=150.0):
    """Score one basket. Returns {fitness, parts} — every part is shown in the UI."""
    st = style_weights(style)
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
    dip = sum(w[pa] * dip_score(metas[pa]) for pa in genome)
    paid = sum(w[pa] * (100.0 if metas[pa].get('paid') else 0.0) for pa in genome)
    f = (st['grade'] * sc['points'] + st['apr'] * apr + st['momo'] * momo * 2 + st['calm'] * calm + st.get('dip', 0) * dip + st.get('paid', 0) * paid
         - 15 * impact - 10 * dupes - min(40.0, drag * 2))
    return {'fitness': round(f, 2), 'parts': {'grade': sc['grade'], 'points': sc['points'], 'aprScore': round(apr, 1), 'momentum24h': round(momo, 2),
                                             'calm': round(calm, 1), 'impactLegs': impact, 'dupes': dupes, 'feeDragPct': round(drag, 2),
                                             'dipScore': round(dip, 1), 'paidPct': round(paid)}}


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


# ---- Real majors on Solana: the ONLY mints Fuse treats as SOL / BTC / ETH / … (lookalike tickers are flagged, never trusted) ----
MAJORS = {   # mint → (symbol, name)
    'So11111111111111111111111111111111111111112': ('SOL', 'Solana (wrapped SOL)'),
    'cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij': ('cbBTC', 'Coinbase Wrapped BTC'),
    '3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh': ('WBTC', 'Wrapped BTC (Wormhole)'),
    '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs': ('ETH', 'Ether (Wormhole)'),
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': ('USDC', 'USD Coin'),
    'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn': ('JitoSOL', 'Jito staked SOL'),
    'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN': ('JUP', 'Jupiter'),
    'jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL': ('JTO', 'Jito'),
    'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3': ('PYTH', 'Pyth Network'),
    '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R': ('RAY', 'Raydium'),
    'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263': ('BONK', 'Bonk'),
    'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm': ('WIF', 'dogwifhat'),
    # big movers that are majors on Solana now (deep pools, real volume) — anchors that actually MOVE
    'pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn': ('PUMP', 'Pump.fun'),
    '7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr': ('POPCAT', 'Popcat'),
    '6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN': ('TRUMP', 'Official Trump'),
    '2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv': ('PENGU', 'Pudgy Penguins'),
    '9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump': ('FARTCOIN', 'Fartcoin'),
    'rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof': ('RENDER', 'Render'),
    'hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux': ('HNT', 'Helium'),
    '85VBFQZC9TZkfaptBWjvUw7YbZjy52A6mjtPGjstQAmQ': ('W', 'Wormhole'),
    'orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE': ('ORCA', 'Orca'),
    'DriFtupJYLTosbwoN8koMbEYSx54aFAVLddWsbksjwg7': ('DRIFT', 'Drift'),
    'MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5': ('MEW', 'cat in a dogs world'),
    'HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC': ('AI16Z', 'ai16z'),
    'ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY': ('MOODENG', 'Moo Deng'),
    '63LfDmNb3MQ8mw9MtZ2To9bEA2M71kZUUGq5tiJxcqj9': ('GIGA', 'GIGACHAD'),
}
# Majors that never act as a card ANCHOR: stables and liquid-staked SOL track a peg, so a card sitting in them "never moves".
# 📈 STOCKS AS MAJORS: tokenized stocks that trade in real Solana pools (xStocks; mints taken from Jupiter's VERIFIED list on
# 2026-10-05, each ≥ $800K deep; a $1 buy with SOL and straight back cost ~0%). They sit beside the crypto majors: an anchor seat,
# the Majors list, the swap picker. Their own table (the majors batch call is capped at 30 mints) — add a ticker only with its
# verified mint, never from memory. Issuer rules apply (not offered in every country): the owner decides who may buy them.
STOCKS = {   # mint → (symbol, name)
    'Xsc9qvGR1efVDFGLrVsmkzv3qi45LTBjeUKSPmx9qEh': ('NVDAx', 'NVIDIA xStock'),
    'XsoCS1TfEyfFhfvj8EtZ528L3CaKBDBRqRapnBbDF2W': ('SPYx', 'S&P 500 xStock'),
    'Xs3oZwbHvqis4NYcf4YKWmEia2eC84wSiVrcYcTqpH8': ('SPCXx', 'SpaceX xStock'),
    'Xs8S1uUs1zvS2p7iwtsG3b6fkhpvmwz4GYU3gWAmWHZ': ('QQQx', 'Nasdaq 100 xStock'),
    'XsueG8BtpquVJX9LVLLEGuViXUungE6WmK5YZ3p3bd1': ('CRCLx', 'Circle xStock'),
    'XsDoVfqeBukxuZHWhdvWHBhgEHjGNst4MLodqsJHzoB': ('TSLAx', 'Tesla xStock'),
    'XsP7xzNPvEHS1m6qfanPUGjNmdnmsLKEoNAnHjdxxyZ': ('MSTRx', 'MicroStrategy xStock'),
    'Xs7ZdzSHLU9ftNJsii5fCeJhoRWSC32SQGzGQtePxNu': ('COINx', 'Coinbase xStock'),
    'Xsa62P5mvPszXL1krVUnU5ar38bBSVcWAB6fmPCo5Zu': ('METAx', 'Meta xStock'),
    'XsvNBAYkrDRNhA7wPHQfX3ZUXZyZLdnCQDfHZ56bzpg': ('HOODx', 'Robinhood xStock'),
    'XspzcW1PRtgf6Wj92HCiZdjzKCyFekVD8P5Ueh3dRMX': ('MSFTx', 'Microsoft xStock'),
}
STOCK_MIN_LIQ = 250_000.0   # a stock row needs a real pool: thinner = not listed (it would move on a card-sized buy)
ALL_MAJORS = {**MAJORS, **STOCKS}   # every protected ticker (lookalike checks read this)
ANCHOR_SKIP = {'USDC', 'JitoSOL'}
MAJOR_ALIASES = {'BTC': {'cbBTC', 'WBTC'}, 'BITCOIN': {'cbBTC', 'WBTC'}, 'ETH': {'ETH'}, 'ETHEREUM': {'ETH'}, 'WETH': {'ETH'}, 'SOL': {'SOL', 'JitoSOL'}, 'SOLANA': {'SOL'}}


def mark_real(rows, q=''):
    """Search safety: rows whose coin IS a listed major get `real`; rows that only LOOK like one (same/alias ticker, other mint)
    get `impostor`. Real first, impostors last — so 'BTC' always finds the real BTC on Solana, never a pump copy."""
    names = {v[0].upper() for v in MAJORS.values()} | set(MAJOR_ALIASES)
    out = []
    for r in rows:
        base = r.get('baseAddress'); sym = str(r.get('symbol') or '').upper()
        real = base in MAJORS
        out.append({**r, 'real': real, 'impostor': (not real) and (sym in names or sym.lstrip('$W') in names)})
    want = {s.upper() for s in MAJOR_ALIASES.get(str(q).upper(), {str(q).upper()})}
    return sorted(out, key=lambda r: (not r['real'], r['impostor'], str(r.get('symbol') or '').upper() not in want, -_f(r.get('liquidityUsd'))))


def majors_pools(pairs_by_mint, table=None):
    """One row per real major: its deepest Solana pool (pairs_by_mint = {mint: [dexscreener pairs]}). `table` = MAJORS (default)
    or STOCKS — stock rows carry `stock: True` and need a pool ≥ STOCK_MIN_LIQ."""
    rows = []
    stocks = table is STOCKS
    for m, (sym, name) in (MAJORS if table is None else table).items():
        ps = [p for p in pairs_by_mint.get(m) or [] if p.get('chainId') == 'solana' and (p.get('baseToken') or {}).get('address') == m]
        if not ps:
            continue
        p = max(ps, key=lambda x: _f((x.get('liquidity') or {}).get('usd')))
        if stocks and _f((p.get('liquidity') or {}).get('usd')) < STOCK_MIN_LIQ:
            continue
        rows.append({'chainId': 'solana', 'pairAddress': p.get('pairAddress'), 'createdAt': p.get('pairCreatedAt'), 'logo': (p.get('info') or {}).get('imageUrl'),
                     **leg_meta(p), 'name': name, 'real': True, 'impostor': False, **({'stock': True} if stocks else {})})
    return rows


def risers(pairs, now_ms, max_age_d=14, min_mcap=800_000, max_mcap=50_000_000, min_vol=300_000, min_liq=100_000, limit=24):
    """🚀 New majors: coins that ARRIVED big — young (≤14d), $800K–$50M mcap, real volume + depth (PAID / HOOKED style).
    One row per coin (deepest pool), ranked by 24h volume × (1 + positive 24h move)."""
    best = {}
    for p in real_pools(pairs):
        if p.get('chainId') != 'solana':
            continue
        mc = _f(p.get('marketCap') or p.get('fdv')); vol = _f((p.get('volume') or {}).get('h24')); liq = _f((p.get('liquidity') or {}).get('usd'))
        age_d = (now_ms - _f(p.get('pairCreatedAt'))) / 8.64e7 if p.get('pairCreatedAt') else 999
        if not (min_mcap <= mc <= max_mcap and vol >= min_vol and liq >= min_liq and age_d <= max_age_d):
            continue
        k = (p.get('baseToken') or {}).get('address')
        if k not in best or liq > _f((best[k].get('liquidity') or {}).get('usd')):
            best[k] = p
    score = lambda p: _f((p.get('volume') or {}).get('h24')) * (1 + max(0.0, _f((p.get('priceChange') or {}).get('h24'))) / 100)
    out = [{'chainId': 'solana', 'pairAddress': p.get('pairAddress'), 'createdAt': p.get('pairCreatedAt'), 'mcap': _f(p.get('marketCap') or p.get('fdv')), 'logo': (p.get('info') or {}).get('imageUrl'), **leg_meta(p)}
           for p in sorted(best.values(), key=score, reverse=True)[:limit]]
    return out


def pump_majors(pairs, have=(), top=40, min_mcap=300_000, min_liq=50_000):
    """🟢 Pump's biggest: graduated Pump.fun coins (PumpSwap / '…pump' mints) with real depth, top `top` by 24h volume — so the
    New majors lens always carries the pump leaders too. One row per coin, skips coins already listed (`have`)."""
    best = {}
    for p in real_pools(pairs):
        b = (p.get('baseToken') or {}).get('address') or ''
        if p.get('chainId') != 'solana' or not (p.get('dexId') in ('pumpswap', 'pumpfun-amm') or b.endswith('pump')) or b in set(have):
            continue
        if _f(p.get('marketCap') or p.get('fdv')) < min_mcap or _f((p.get('liquidity') or {}).get('usd')) < min_liq or p.get('dexId') == 'pumpfun':
            continue
        if b not in best or _f((p.get('liquidity') or {}).get('usd')) > _f((best[b].get('liquidity') or {}).get('usd')):
            best[b] = p
    rows = sorted(best.values(), key=lambda p: -_f((p.get('volume') or {}).get('h24')))[:top]
    return [{'chainId': 'solana', 'pairAddress': p.get('pairAddress'), 'createdAt': p.get('pairCreatedAt'), 'mcap': _f(p.get('marketCap') or p.get('fdv')), 'pump': True, 'logo': (p.get('info') or {}).get('imageUrl'), **leg_meta(p)} for p in rows]


# 🪙 A NEW MAJOR MUST TRADE LIKE ONE. 2026-10-06: $VSOF took a real-card seat through the new-major door — a "$667M" market cap on
# $735K of daily volume (0.1% of its size), a pool turning over 0.3× a day, no logo. A coin whose size nobody trades is a number,
# not a major. Majors carry weight on a card, so the bar is: real trading for its size, a pool that turns over, an identity.
MAJOR_MIN_VOL_MCAP = 1.0    # 24h volume ≥ 1% of market cap
MAJOR_MIN_TURNOVER = 0.5    # 24h volume ≥ half the pool
MAJOR_MAX_MCAP = 250_000_000   # a days-old coin "worth" more than this is not judged a new major (established majors live in MAJORS)


def solid_major(row):
    """→ [] when a new-major row trades like a real one, else the plain reasons it does not. Unknown numbers = not solid."""
    mc, vol, liq = _f(row.get('mcap')), _f(row.get('volume24h')), _f(row.get('liquidityUsd') or row.get('liquidity') or row.get('liq'))
    why = []
    if mc <= 0 or vol <= 0 or liq <= 0:
        return ['no size / volume / pool reading']
    if mc > MAJOR_MAX_MCAP:
        why.append(f'${mc / 1e6:,.0f}M market cap on a coin days old')
    if vol / mc * 100 < MAJOR_MIN_VOL_MCAP:
        why.append(f'only {vol / mc * 100:.1f}% of its size traded in 24h')
    if vol / liq < MAJOR_MIN_TURNOVER:
        why.append(f'pool turns over {vol / liq:.1f}× a day')
    if not row.get('logo'):
        why.append('no logo')
    return why


def rank_anchors(majors, risers=(), now_ms=0, max_new=4, min_liq=250_000):
    """⚓ The anchor basket, ranked by what the coin is DOING — never by name (SOL gets no head start). Real majors (not stables /
    LSTs, `ANCHOR_SKIP`) + big NEW majors (risers ≥ $5M mcap, ≥ $300K pool, ≥ 1 day old, at most `max_new`). Score = turnover
    (24h volume ÷ pool) + how much it moves (1h / 6h / 24h, either way) + buyers in charge + depth; a coin falling hard (24h ≤ −15%)
    pays 15. Each row carries `anchorScore` + the cited `anchorWhy`."""
    rows = []
    def score(r):
        liq, turn = _f(r.get('liquidityUsd')), _f(r.get('turnover')) or (_f(r.get('volume24h')) / _f(r.get('liquidityUsd')) if _f(r.get('liquidityUsd')) else 0.0)
        c1, c6, c24, bs = _f(r.get('change1h')), _f(r.get('change6h')), _f(r.get('change24h')), _f(r.get('buyShare'))
        parts = [('turnover', min(30.0, turn * 15), f"volume {turn:.1f}× its pool"), ('moving', min(20.0, abs(c1) * 4) + min(15.0, abs(c6) * 1.5) + min(25.0, abs(c24) * 1.5),
                 f"1h {c1:+.1f}% · 6h {c6:+.1f}% · 24h {c24:+.1f}%"), ('buyers', 5.0 if bs >= 52 else 0.0, f"{bs:.0f}% buys"),
                 ('depth', max(0.0, min(10.0, 5 * math.log10(liq / min_liq))) if liq > min_liq else 0.0, f"${liq / 1e6:.1f}M pool")]
        if c24 <= -15:
            parts.append(('falling', -15.0, f"24h {c24:+.0f}% — falling knife"))
        return round(sum(p for _, p, _ in parts), 1), [{'part': k, 'points': round(p, 1), 'why': w} for k, p, w in parts if p]
    for r in majors or []:
        if str(r.get('symbol')) in ANCHOR_SKIP or _f(r.get('priceUsd')) <= 0 or _f(r.get('liquidityUsd')) < min_liq:
            continue
        sc, why = score(r)
        rows.append({**r, 'anchorScore': sc, 'anchorWhy': why})
    have = {r.get('baseAddress') for r in rows}
    new = []
    for r in risers or []:
        old_enough = not now_ms or not r.get('createdAt') or (now_ms - _f(r.get('createdAt'))) >= 8.64e7
        if r.get('baseAddress') in have or _f(r.get('priceUsd')) <= 0 or _f(r.get('mcap')) < 5_000_000 or _f(r.get('liquidityUsd')) < 300_000 or not old_enough:
            continue
        sc, why = score(r)
        new.append({**r, 'anchorScore': sc, 'anchorWhy': why, 'newMajor': True})
    new = sorted(new, key=lambda r: -r['anchorScore'])[:max_new]
    return sorted(rows + new, key=lambda r: -r['anchorScore'])
