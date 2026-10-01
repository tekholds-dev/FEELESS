"""FUSE RUNNERS: the degen engine. Pure functions (no I/O) — the service feeds it live launchpad coins as they arrive.

Coins come to it: every Pump.fun coin the launchpad feed sees (pre-bond on the curve or freshly graduated) is scored
the moment it shows up. Nothing here predicts price; it applies hard safety gates, ranks momentum + real flow, assigns a
lane with a preset exit plan, carries the best runners into the next round, and proves itself on paper.

Lanes (each with its own exits):
  scalp   pre-bond coins racing up the curve (50–98% to graduation): sell ALL into the +50% rush, stop −25%.
  runner  1–48h coins with momentum + real flow: sell ⅓ at +50%, ⅓ at +100%, trail the last ⅓ by 25 pts, stop −30%.
  hold    runners that stayed in the top for 2+ rounds and still score ≥ 70: trail 30 pts, stop −35%.
Proof: each round is played on paper against the prices seen in later rounds; the Fuse button only lights up when the
last 24h of rounds have a positive average AND at least half of them won.
"""
import math

ROUND_SECONDS = 15 * 60
ROUND_SIZE = 5
MAX_AGE_H = 48
EXITS = {
    'scalp': {'ladder': [(50.0, 1.0)], 'trail': None, 'stop': -25.0, 'label': 'Sell all at +50% · stop −25%'},
    'runner': {'ladder': [(50.0, 1 / 3), (100.0, 1 / 3)], 'trail': 25.0, 'stop': -30.0, 'label': '⅓ at +50% · ⅓ at +100% · trail 25 · stop −30%'},
    'hold': {'ladder': [], 'trail': 30.0, 'stop': -35.0, 'label': 'Trail 30 pts · stop −35%'},
}
LIGHT_MIN_ROUNDS = 8


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def candidate(pair, intel=None, creator_flagged=False, snipers_out=False, now_ms=0):
    """A launchpad pair (+ cached forensics) → the flat record the engine reads."""
    intel = intel or {}
    tx = (pair.get('txns') or {}).get('h1') or {}
    buys, sells = _f(tx.get('buys')), _f(tx.get('sells'))
    created = _f(pair.get('pairCreatedAt'))
    pc, vol = pair.get('priceChange') or {}, pair.get('volume') or {}
    return {'mint': (pair.get('baseToken') or {}).get('address'), 'symbol': (pair.get('baseToken') or {}).get('symbol'), 'pairAddress': pair.get('pairAddress'),
            'chainId': 'solana', 'logo': (pair.get('info') or {}).get('imageUrl'), 'dex': pair.get('dexId'),
            'stage': 'graduated' if pair.get('graduated') or pair.get('dexId') not in ('pumpfun', None) else 'curve',
            'curve': _f(pair.get('curveProgress')), 'ageH': round((now_ms - created) / 3.6e6, 2) if created and now_ms else None,
            'mcap': _f(pair.get('marketCap') or pair.get('fdv')), 'liq': _f((pair.get('liquidity') or {}).get('usd')), 'price': _f(pair.get('priceUsd')),
            'vol5m': _f(vol.get('m5')), 'vol1h': _f(vol.get('h1')), 'chg5m': _f(pc.get('m5')), 'chg1h': _f(pc.get('h1')), 'chg24h': _f(pc.get('h24')),
            'txns1h': int(buys + sells), 'buyShare': round(buys / (buys + sells) * 100, 1) if buys + sells else None,
            'quality': _f((pair.get('quality') or {}).get('score')),
            'top10': intel.get('top10Pct'), 'insiders': intel.get('insidersHoldingPct'), 'dev': intel.get('devHoldingPct'),
            'bundled': len(intel.get('bundledWallets') or []), 'scanned': bool(intel), 'creatorFlagged': bool(creator_flagged), 'snipersOut': bool(snipers_out)}


GATES = (   # key, label, test — ALL must pass (unknown forensics fail closed except where noted)
    ('age', 'Under 48h old', lambda c: c['ageH'] is not None and 0 <= c['ageH'] <= MAX_AGE_H),
    ('size', 'Market cap ≥ $8K', lambda c: c['mcap'] >= 8_000),
    ('volume', '1h volume ≥ $5K', lambda c: c['vol1h'] >= 5_000),
    ('flow', 'Two-sided flow (40–85% buys, 50+ trades/h)', lambda c: c['buyShare'] is not None and 40 <= c['buyShare'] <= 85 and c['txns1h'] >= 50),
    ('scan', 'Holder scan done', lambda c: c['scanned']),
    ('top10', 'Top 10 under 30%', lambda c: c['top10'] is not None and c['top10'] < 30),
    ('insiders', 'Snipers/bundlers under 15%', lambda c: (c['insiders'] or 0) < 15 and c['bundled'] < 3),
    ('dev', 'Dev holds under 10%', lambda c: (c['dev'] or 0) < 10),
    ('creator', 'Creator not flagged (Bot shield / blocklist)', lambda c: not c['creatorFlagged']),
)


def failed_gates(c):
    return [label for _, label, test in GATES if not test(c)]


def score(c):
    """0–100 with the reason for every part (shown on the board)."""
    mom = max(0.0, min(30.0, c['chg1h'] / 10))                                   # +300%/h → 30
    acc = max(0.0, min(15.0, c['chg5m'] / 2))                                    # +30%/5m → 15
    vel = max(0.0, min(20.0, (c['vol1h'] / c['mcap'] * 10) if c['mcap'] else 0))  # turnover 2×/h → 20
    flow = max(0.0, 10 - abs((c['buyShare'] or 0) - 60) / 2)                     # sweet spot ~60% buys
    curve = 10.0 if c['stage'] == 'curve' and 60 <= c['curve'] <= 95 else 5.0 if c['stage'] == 'graduated' else 0.0
    bonus = (8.0 if c['snipersOut'] else 0.0) + min(7.0, c['quality'] / 14)
    pts = round(min(100.0, mom + acc + vel + flow + curve + bonus), 1)
    return pts, [{'part': 'momentum', 'points': round(mom, 1), 'why': f"{c['chg1h']:+.0f}% in 1h"},
                 {'part': 'acceleration', 'points': round(acc, 1), 'why': f"{c['chg5m']:+.0f}% in 5m"},
                 {'part': 'velocity', 'points': round(vel, 1), 'why': f"1h volume = {c['vol1h'] / c['mcap'] if c['mcap'] else 0:.1f}× market cap"},
                 {'part': 'flow', 'points': round(flow, 1), 'why': f"{c['buyShare']}% buys" if c['buyShare'] is not None else 'no flow'},
                 {'part': 'stage', 'points': curve, 'why': f"{c['curve']:.0f}% up the curve" if c['stage'] == 'curve' else 'graduated (own pool)'},
                 {'part': 'bonus', 'points': round(bonus, 1), 'why': ('snipers sold out · ' if c['snipersOut'] else '') + f"quality {c['quality']:.0f}"}]


def lane_of(c, streak=0, pts=0):
    if streak >= 2 and pts >= 70:
        return 'hold'
    if c['stage'] == 'curve' and 50 <= c['curve'] <= 98:
        return 'scalp'
    return 'runner'


def board(cands):
    """Every arriving coin, gated + scored: {passing: [...best first], dropped: [...with reasons]}."""
    passing, dropped = [], []
    for c in cands:
        if not c.get('mint'):
            continue
        bad = failed_gates(c)
        pts, parts = score(c)
        row = {**c, 'score': pts, 'parts': parts, 'gates': bad}
        (dropped if bad else passing).append(row)
    passing.sort(key=lambda r: -r['score'])
    return {'passing': passing, 'dropped': sorted(dropped, key=lambda r: -r['score'])[:30]}


def next_round(prev, passing, now, size=ROUND_SIZE, rid=''):
    """Best runners STAY for another round (streak + 1, may graduate to the hold lane); the rest of the slots go to the
    best newcomers. prev = last round or None."""
    by = {r['mint']: r for r in passing}
    keep_cut = passing[min(len(passing), size * 2) - 1]['score'] if passing else 0   # stays if still in the top 2×size
    picks = []
    for p in (prev or {}).get('picks') or []:
        r = by.get(p['mint'])
        if r and r['score'] >= keep_cut and len(picks) < size:
            streak = p.get('streak', 1) + 1
            picks.append({**r, 'streak': streak, 'entry': p['entry'], 'enteredAt': p['enteredAt'], 'lane': lane_of(r, streak, r['score'])})
    for r in passing:
        if len(picks) >= size:
            break
        if r['mint'] not in {x['mint'] for x in picks} and r['price'] > 0:
            picks.append({**r, 'streak': 1, 'entry': r['price'], 'enteredAt': now, 'lane': lane_of(r, 1, r['score'])})
    kept = {x['mint'] for x in picks if x['streak'] > 1}
    out = [p for p in (prev or {}).get('picks') or [] if p['mint'] not in kept]
    return {'id': rid, 'at': now, 'picks': picks, 'out': [{'mint': p['mint'], 'symbol': p.get('symbol')} for p in out]}


def play_exits(lane, entry, path):
    """Paper-play a lane's exit plan on the prices seen after entry → realized multiple (1.0 = flat).
    Ladder rungs sell their slice when hit; trail sells the rest when it falls `trail` pts below the peak gain;
    stop sells everything left. Whatever is left at the end is marked at the last price."""
    if entry <= 0:
        return 1.0
    plan = EXITS[lane]
    left, cash, peak, rungs = 1.0, 0.0, 0.0, list(plan['ladder'])
    for px in path:
        g = (px / entry - 1) * 100
        peak = max(peak, g)
        while rungs and g >= rungs[0][0] and left > 1e-9:
            take = min(left, rungs.pop(0)[1]); cash += take * px / entry; left -= take
        if left <= 1e-9:
            return round(cash, 4)
        if g <= plan['stop'] or (plan['trail'] and peak > 0 and peak - g >= plan['trail']):
            return round(cash + left * px / entry, 4)
    return round(cash + left * (path[-1] / entry if path else 1.0), 4)


def proof(rounds, paths, now, window=24 * 3600):
    """Each round in the window (at least one later price seen): equal-$ basket of its picks played with their lane exits.
    lights = enough rounds, positive average, ≥50% won."""
    rows = []
    for r in rounds:
        if now - r['at'] > window or not r.get('picks'):
            continue
        mults = []
        for p in r['picks']:
            path = [px for t, px in paths.get(p['mint'], []) if t > r['at']]
            if path:
                mults.append(play_exits(p['lane'], p['entry'], path))
        if mults:
            rows.append(sum(mults) / len(mults))
    n = len(rows)
    avg = round((sum(rows) / n - 1) * 100, 2) if n else 0.0
    win = round(sum(1 for m in rows if m > 1) / n * 100) if n else 0
    return {'rounds': n, 'avgPct': avg, 'winRate': win, 'lights': n >= LIGHT_MIN_ROUNDS and avg > 0 and win >= 50,
            'per1': round(1 + avg / 100, 3), 'need': max(0, LIGHT_MIN_ROUNDS - n)}


def addon(legs, runners, slice_pct=20.0, n=2):
    """Runner add-on: bolt the top `n` runners onto any Fuse as a small slice (default 20%, split evenly); the basket's
    own legs keep their proportions in the rest."""
    rs = [r for r in runners if r.get('pairAddress')][:n]
    if not rs:
        return [dict(l) for l in legs]
    slice_pct = max(5.0, min(40.0, _f(slice_pct)))
    total = sum(_f(l.get('weight')) for l in legs) or 1
    base = [{**l, 'weight': round(_f(l.get('weight')) / total * (100 - slice_pct), 2)} for l in legs]
    return base + [{'chainId': 'solana', 'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'baseAddress': r.get('mint'), 'logo': r.get('logo'),
                    'weight': round(slice_pct / len(rs), 2), 'runner': True, 'lane': r.get('lane'), 'exits': EXITS[r.get('lane') or 'runner']['label']} for r in rs]
