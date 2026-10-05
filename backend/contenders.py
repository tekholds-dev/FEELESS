"""🏁 Arena contenders — the qualifier league behind every card seat (pure, tested).

Every list a trader can pick from is its own DIVISION. Coins in a division are scored on what they are doing RIGHT NOW (cited parts),
ranked, and the best coin that is not on a card yet is ⏭ NEXT UP for a seat. Ranks are compared with the round before (▲ ▼ NEW), and a
coin that holds #1 builds a streak. Ranking only: it never trades and never promises a result — the card engine still runs every gate.
"""
import math

# key → (label, one-line rule shown on screen, role the seat feeds on a card)
DIVISIONS = {
    'majors':   ('🪙 Anchors', 'The real majors, ranked by volume and how much they are moving', 'anchor'),
    'risers':   ('🚀 New majors', 'Young coins that arrived big: ≤14 days, real volume, deep pool', 'runner'),
    'yield':    ('💸 Top yield', 'Busiest pools for their size (pool APR), $50K+ deep', 'pool'),
    'deep':     ('🌊 Deepest', 'The deepest pools still trading', 'pool'),
    'popular':  ('🔥 Popular', 'Most traded today', 'pool'),
    'fresh':    ('⚡ Fresh runners', 'Under 12h old, passing every gate and pumping now', 'runner'),
    'proven':   ('🏃 Proven runners', '12h+ old, passing every gate and still pumping', 'runner'),
    'new':      ('🆕 New 72h', 'Pools born in the last 72 hours with real flow', 'pool'),
    'dip':      ('📉 Dip buys', 'Down 8%+ on the day and buyers are back: 1h green, 55%+ buys', 'pool'),
    'paid':     ('💳 Dex paid', 'A team paid for its DexScreener profile / boosts, with real flow', 'pool'),
}
STABLES = {'USDC', 'USDT', 'USDS', 'PYUSD', 'USD1', 'DAI', 'USDE', 'FDUSD'}
TOP_N = 6
PROVEN_H = 12.0


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _log(v, lo, hi):
    """0…1 on a log scale between lo and hi (volume / depth span orders of magnitude)."""
    v = _f(v)
    if v <= lo:
        return 0.0
    return min(1.0, math.log10(v / lo) / math.log10(hi / lo))


def norm(row):
    """One shape for every source (Lab pools, majors, runner board rows)."""
    liq = row.get('liquidityUsd', row.get('liq'))
    bs = _f(row.get('buyShare')); bs = bs * 100 if 0 < bs <= 1 else bs
    return {'mint': row.get('baseAddress') or row.get('mint'), 'pairAddress': row.get('pairAddress'), 'symbol': row.get('symbol'), 'logo': row.get('logo'),
            'price': _f(row.get('priceUsd', row.get('price'))), 'liq': _f(liq), 'vol24h': _f(row.get('volume24h')), 'vol1h': _f(row.get('vol1h')),
            'chg24h': _f(row.get('change24h', row.get('chg24h'))), 'chg1h': _f(row.get('chg1h', row.get('change1h'))), 'buyShare': bs, 'apr': _f(row.get('aprEst')),
            'ageH': row.get('ageH'), 'runnerScore': _f(row.get('score')), 'mcap': _f(row.get('mcap')),
            'paid': bool(row.get('paid')), 'boosts': int(_f(row.get('boosts')))}


def pumping(r):
    """A runner that is really running: green over the hour, buyers in control, real volume."""
    return _f(r.get('chg1h')) > 0 and _f(r.get('buyShare')) >= 55 and _f(r.get('vol1h')) >= 5000


def score(r, div):
    """0–100 with the parts that made it (every point cited, like the runner score)."""
    parts = []
    def add(name, pts, why):
        if pts > 0:
            parts.append({'part': name, 'points': round(pts, 1), 'why': why})
    if div in ('fresh', 'proven'):
        add('runner score', min(45.0, r['runnerScore'] * 0.45), f"gate score {r['runnerScore']:.0f}")
        add('momentum', min(30.0, max(0.0, r['chg1h']) * 0.3), f"{r['chg1h']:+.0f}% in 1h")
        add('buyers', max(0.0, min(15.0, (r['buyShare'] - 50) * 0.6)), f"{r['buyShare']:.0f}% buys")
        add('volume', 10 * _log(r['vol1h'], 5_000, 500_000), f"${r['vol1h']:,.0f} traded in 1h")
    elif div == 'majors':
        add('volume', 45 * _log(r['vol24h'], 100_000, 500_000_000), f"${r['vol24h']:,.0f} traded today")
        add('depth', 20 * _log(r['liq'], 100_000, 50_000_000), f"${r['liq']:,.0f} pool")
        add('moving', min(20.0, abs(r['chg24h']) * 1.5 + abs(r['chg1h']) * 3), f"{r['chg24h']:+.1f}% today · {r['chg1h']:+.1f}% 1h")   # a major that sits still is a weak anchor
        add('trend', max(0.0, min(15.0, 7.5 + r['chg24h'] * 1.5)), f"{r['chg24h']:+.1f}% today")
    elif div == 'dip':
        add('the dip', min(40.0, -r['chg24h']), f"{r['chg24h']:+.0f}% on the day")
        add('bounce', min(20.0, r['chg1h'] * 2), f"{r['chg1h']:+.1f}% in 1h")
        add('buyers', max(0.0, min(20.0, (r['buyShare'] - 50) * 1.5)), f"{r['buyShare']:.0f}% buys")
        add('depth', 20 * _log(r['liq'], 50_000, 5_000_000), f"${r['liq']:,.0f} pool")
    elif div == 'yield':
        add('pool APR', 55 * _log(r['apr'], 20, 5_000), f"{r['apr']:,.0f}% pool APR")
        add('depth', 25 * _log(r['liq'], 50_000, 5_000_000), f"${r['liq']:,.0f} pool")
        add('buyers', max(0.0, min(20.0, (r['buyShare'] - 40) * 1.0)), f"{r['buyShare']:.0f}% buys")
    elif div == 'deep':
        add('depth', 65 * _log(r['liq'], 100_000, 50_000_000), f"${r['liq']:,.0f} pool")
        add('volume', 35 * _log(r['vol24h'], 50_000, 100_000_000), f"${r['vol24h']:,.0f} traded today")
    else:   # popular · risers · new · paid
        if div == 'paid':
            add('dex paid', 10.0 + min(10.0, r['boosts'] / 10), 'DexScreener profile paid' + (f" · {r['boosts']} boosts" if r['boosts'] else ''))
        add('volume', 45 * _log(r['vol24h'], 50_000, 50_000_000), f"${r['vol24h']:,.0f} traded today")
        add('trend', max(0.0, min(25.0, r['chg24h'] * 0.25)), f"{r['chg24h']:+.0f}% today")
        add('buyers', max(0.0, min(15.0, (r['buyShare'] - 45) * 1.0)), f"{r['buyShare']:.0f}% buys")
        add('depth', 15 * _log(r['liq'], 25_000, 5_000_000), f"${r['liq']:,.0f} pool")
    return round(min(100.0, sum(p['points'] for p in parts)), 1), parts


def eligible(r, div):
    if not r.get('mint') or not r.get('pairAddress') or r['price'] <= 0:
        return False
    if div != 'majors' and str(r.get('symbol') or '').upper().replace('ERC20-', '') in STABLES:
        return False   # a dollar coin can't compete: it never moves
    if div == 'fresh':
        return r.get('ageH') is not None and _f(r['ageH']) < PROVEN_H and pumping(r)
    if div == 'proven':
        return r.get('ageH') is not None and _f(r['ageH']) >= PROVEN_H and pumping(r)
    if div == 'yield':
        return r['liq'] >= 50_000 and r['apr'] > 0
    if div == 'dip':
        return r['liq'] >= 50_000 and r['chg24h'] <= -8 and r['chg24h'] > -70 and r['chg1h'] >= 0 and r['buyShare'] >= 55
    if div == 'paid':
        return r['paid'] and r['liq'] >= 25_000 and r['vol24h'] >= 50_000 and r['buyShare'] >= 50
    if div in ('deep', 'popular', 'risers', 'new'):
        return r['liq'] >= 25_000
    return True


def league(sources, on_card=(), prev=None, top_n=TOP_N):
    """sources: {division: [raw rows]} · on_card: mints already on a tier / Arena card · prev: the last league (for ▲▼ and streaks).
    → {'divisions': [{key, label, rule, role, rows: [...], nextUp}], 'nextUp': {mint: division}}"""
    on_card, prev_div = set(on_card or ()), {d['key']: d for d in (prev or {}).get('divisions') or []}
    out, next_up, seated = [], {}, set()
    for key, (label, rule, role) in DIVISIONS.items():
        rows = []
        for raw in sources.get(key) or []:
            r = norm(raw)
            if not eligible(r, key) or any(x['mint'] == r['mint'] for x in rows):
                continue
            sc, parts = score(r, key)
            rows.append({**r, 'score': sc, 'parts': parts})
        rows.sort(key=lambda x: -x['score'])
        rows = rows[:top_n]
        was = {x['mint']: x for x in (prev_div.get(key) or {}).get('rows') or []}
        nxt = None
        for i, r in enumerate(rows):
            p = was.get(r['mint'])
            r['rank'] = i + 1
            r['move'] = 'new' if not p else 'up' if p['rank'] > i + 1 else 'down' if p['rank'] < i + 1 else 'same'
            r['streak'] = (int(p.get('streak') or 0) + 1 if p and p['rank'] == 1 else 1) if i == 0 else 0
            r['seat'] = 'card' if r['mint'] in on_card else ''
            # ⏭ one seat per coin: a coin already next up in an earlier division doesn't take a second seat
            if nxt is None and not r['seat'] and r['mint'] not in seated:
                r['seat'] = 'next'; nxt = r['mint']; seated.add(r['mint']); next_up[r['mint']] = key
        out.append({'key': key, 'label': label, 'rule': rule, 'role': role, 'rows': rows, 'nextUp': nxt})
    return {'divisions': out, 'nextUp': next_up}
