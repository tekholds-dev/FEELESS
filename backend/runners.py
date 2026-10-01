"""FUSE RUNNERS: the degen engine. Pure functions (no I/O) — the service feeds it live launchpad coins as they arrive.

Coins come to it: every Pump.fun coin the launchpad feed sees (pre-bond on the curve or freshly graduated) is scored
the moment it shows up. Nothing here predicts price; it applies hard safety gates, ranks momentum + real flow, assigns a
lane with a preset exit plan, carries the best runners into the next round, and proves itself on paper.

PRE-BOND ONLY (still on the Pump.fun curve, never mayhem-mode), creator reputation gated.
Lanes (each with its own exits):
  scalp   50%+ up the curve, racing to graduate: sell ALL into the +50% rush, stop −25%.
  runner  earlier on the curve with momentum + real flow: ⅓ at +50%, ⅓ at +100%, trail the last ⅓ by 25 pts, stop −30%.
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


def candidate(pair, intel=None, creator_flagged=False, snipers_out=False, now_ms=0, mayhem=False, creator_rep=None):
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
            'bundled': len(intel.get('bundledWallets') or []), 'scanned': bool(intel), 'creatorFlagged': bool(creator_flagged), 'snipersOut': bool(snipers_out),
            'mayhem': bool(mayhem or pair.get('mayhem') or pair.get('is_mayhem_mode')), 'creatorRep': creator_rep}


# Cmd Ctr › Runners settings. Every key is range-checked by clean_cfg(); defaults = the tested engine.
DEFAULT_CFG = {'roundSize': 5, 'minMcap': 8000, 'minVol1h': 5000, 'maxTop10': 30, 'maxInsiders': 15, 'maxDev': 10,
               'scalpTp': 50, 'scalpStop': 25, 'runnerTp1': 50, 'runnerTp2': 100, 'runnerTrail': 25, 'runnerStop': 30, 'holdTrail': 30, 'holdStop': 35, 'lightRounds': 8}
CFG_RANGES = {'roundSize': (2, 10), 'minMcap': (1000, 1_000_000), 'minVol1h': (500, 1_000_000), 'maxTop10': (10, 60), 'maxInsiders': (2, 40), 'maxDev': (1, 30),
              'scalpTp': (10, 300), 'scalpStop': (5, 80), 'runnerTp1': (10, 300), 'runnerTp2': (20, 1000), 'runnerTrail': (5, 80), 'runnerStop': (5, 80),
              'holdTrail': (5, 80), 'holdStop': (5, 80), 'lightRounds': (3, 48)}


def clean_cfg(p):
    out = dict(DEFAULT_CFG)
    for k, (lo, hi) in CFG_RANGES.items():
        if k in (p or {}):
            out[k] = int(min(hi, max(lo, _f(p[k]))))
    out['runnerTp2'] = max(out['runnerTp2'], out['runnerTp1'] + 10)
    return out


def gates(cfg=None):
    g = clean_cfg(cfg)
    return (   # key, label, test — ALL must pass (unknown forensics fail closed)
        ('prebond', 'Pre-bond (still on the curve)', lambda c: c['stage'] == 'curve'),
        ('mayhem', 'Not a mayhem-mode coin', lambda c: not c.get('mayhem')),
        ('age', 'Under 48h old', lambda c: c['ageH'] is not None and 0 <= c['ageH'] <= MAX_AGE_H),
        ('size', f"Market cap ≥ ${g['minMcap'] / 1000:g}K", lambda c: c['mcap'] >= g['minMcap']),
        ('volume', f"1h volume ≥ ${g['minVol1h'] / 1000:g}K", lambda c: c['vol1h'] >= g['minVol1h']),
        ('flow', 'Two-sided flow (40–85% buys, 50+ trades/h)', lambda c: c['buyShare'] is not None and 40 <= c['buyShare'] <= 85 and c['txns1h'] >= 50),
        ('scan', 'Holder scan done', lambda c: c['scanned']),
        ('top10', f"Top 10 under {g['maxTop10']}%", lambda c: c['top10'] is not None and c['top10'] < g['maxTop10']),
        ('insiders', f"Snipers/bundlers under {g['maxInsiders']}%", lambda c: (c['insiders'] or 0) < g['maxInsiders'] and c['bundled'] < 3),
        ('dev', f"Dev holds under {g['maxDev']}%", lambda c: (c['dev'] or 0) < g['maxDev']),
        ('creator', 'Creator not flagged (Bot shield / blocklist)', lambda c: not c['creatorFlagged']),
        ('rep', 'Creator reputation not suspect / high-risk', lambda c: c.get('creatorRep') not in ('suspect', 'high')),
    )


GATES = gates()


def exits(cfg=None):
    g = clean_cfg(cfg)
    return {'scalp': {'ladder': [(float(g['scalpTp']), 1.0)], 'trail': None, 'stop': -float(g['scalpStop']), 'label': f"Sell all at +{g['scalpTp']}% · stop −{g['scalpStop']}%"},
            'runner': {'ladder': [(float(g['runnerTp1']), 1 / 3), (float(g['runnerTp2']), 1 / 3)], 'trail': float(g['runnerTrail']), 'stop': -float(g['runnerStop']),
                       'label': f"⅓ at +{g['runnerTp1']}% · ⅓ at +{g['runnerTp2']}% · trail {g['runnerTrail']} · stop −{g['runnerStop']}%"},
            'hold': {'ladder': [], 'trail': float(g['holdTrail']), 'stop': -float(g['holdStop']), 'label': f"Trail {g['holdTrail']} pts · stop −{g['holdStop']}%"}}


def failed_gates(c, cfg=None):
    return [label for _, label, test in (gates(cfg) if cfg else GATES) if not test(c)]


def score(c):
    """0–100 with the reason for every part (shown on the board)."""
    mom = max(0.0, min(30.0, c['chg1h'] / 10))                                   # +300%/h → 30
    acc = max(0.0, min(15.0, c['chg5m'] / 2))                                    # +30%/5m → 15
    vel = max(0.0, min(20.0, (c['vol1h'] / c['mcap'] * 10) if c['mcap'] else 0))  # turnover 2×/h → 20
    flow = max(0.0, 10 - abs((c['buyShare'] or 0) - 60) / 2)                     # sweet spot ~60% buys
    curve = 10.0 if c['stage'] == 'curve' and 60 <= c['curve'] <= 95 else 5.0 if c['stage'] == 'graduated' else 0.0
    rep_pts = {'clean': 5.0, 'watch': -10.0}.get(c.get('creatorRep'), 0.0)       # reputation: clean creators earn, "watch" pays
    bonus = (8.0 if c['snipersOut'] else 0.0) + min(7.0, c['quality'] / 14) + rep_pts
    pts = round(min(100.0, mom + acc + vel + flow + curve + bonus), 1)
    return pts, [{'part': 'momentum', 'points': round(mom, 1), 'why': f"{c['chg1h']:+.0f}% in 1h"},
                 {'part': 'acceleration', 'points': round(acc, 1), 'why': f"{c['chg5m']:+.0f}% in 5m"},
                 {'part': 'velocity', 'points': round(vel, 1), 'why': f"1h volume = {c['vol1h'] / c['mcap'] if c['mcap'] else 0:.1f}× market cap"},
                 {'part': 'flow', 'points': round(flow, 1), 'why': f"{c['buyShare']}% buys" if c['buyShare'] is not None else 'no flow'},
                 {'part': 'stage', 'points': curve, 'why': f"{c['curve']:.0f}% up the curve" if c['stage'] == 'curve' else 'graduated (own pool)'},
                 {'part': 'bonus', 'points': round(bonus, 1), 'why': ('snipers sold out · ' if c['snipersOut'] else '') + f"quality {c['quality']:.0f}" + (f" · creator {c.get('creatorRep')}" if c.get('creatorRep') else '')}]


def lane_of(c, streak=0, pts=0):
    if streak >= 2 and pts >= 70:
        return 'hold'
    if c['curve'] >= 50:          # pre-bond and racing toward graduation: sell into the rush
        return 'scalp'
    return 'runner'               # earlier on the curve with momentum: ladder out


def board(cands, cfg=None):
    """Every arriving coin, gated + scored: {passing: [...best first], dropped: [...with reasons]}."""
    passing, dropped = [], []
    gs = gates(cfg) if cfg else GATES
    for c in cands:
        if not c.get('mint'):
            continue
        bad = [label for _, label, test in gs if not test(c)]
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


def swap_failing(rnd, passing, failing, paths, now, cfg=None):
    """Keep a round clean: at most ONE pick that now FAILS a gate (it's in `failing` = {mint: [reasons]}) is swapped for the
    best passing runner not already in the round. The swapped-out pick is closed on paper at that moment (its result
    stays in the proof); the new one enters at today's price. Returns (round, swap or None)."""
    picks = list(rnd.get('picks') or [])
    bad = next((p for p in picks if p['mint'] in failing), None)
    inr = {p['mint'] for p in picks}
    sub = next((x for x in passing if x['mint'] not in inr and _f(x.get('price')) > 0), None)
    if not bad or not sub:
        return rnd, None
    since = bad.get('swappedIn') or rnd['at']
    path = [px for t, px in paths.get(bad['mint'], []) if since < t <= now]
    mult = play_exits(bad.get('lane', 'runner'), bad['entry'], path, cfg) if path else 1.0
    new = {**sub, 'streak': 1, 'entry': sub['price'], 'enteredAt': now, 'swappedIn': now, 'lane': lane_of(sub, 1, sub['score'])}
    swap = {'at': now, 'out': {'mint': bad['mint'], 'symbol': bad.get('symbol')}, 'in': {'mint': sub['mint'], 'symbol': sub.get('symbol')},
            'why': list(failing[bad['mint']])[:3], 'mult': mult}
    picks[picks.index(bad)] = new
    return {**rnd, 'picks': picks, 'swaps': (rnd.get('swaps') or []) + [swap]}, swap


def lit_card(rnd, proof_now):
    """Snapshot of a round dealt while the proof was lit — it joins the lit-cards list and is tracked on paper from then."""
    return {'id': rnd['id'], 'at': rnd['at'], 'proof': {k: proof_now.get(k) for k in ('rounds', 'avgPct', 'winRate')},
            'picks': [{k: p.get(k) for k in ('mint', 'symbol', 'lane', 'entry', 'logo', 'pairAddress')} for p in rnd['picks']]}


def _pick_mult(card, p, paths, now, cfg=None):
    since = p.get('swappedIn') or card['at']
    return play_exits(p.get('lane') or 'runner', p['entry'], [px for t, px in paths.get(p['mint'], []) if since < t <= now], cfg)


def card_result(card, paths, now, cfg=None):
    """$5-run result of a lit card since it lit: equal $ per runner slot, each with its lane exits. A swapped-in pick counts
    from its swap; a swapped-out pick keeps the result it closed at (never erased from the record)."""
    mults = [_pick_mult(card, p, paths, now, cfg) for p in card['picks'] if p.get('entry')] + [_f(s['mult']) for s in card.get('swaps') or [] if 'mult' in s]
    return round((sum(mults) / len(mults) - 1) * 100, 2) if mults else 0.0


CARD_WEAK_PCT = -25.0   # a lit-card pick at or below this since it joined the card is weak


def rebuild_lit(card, paths, passing, failing, now, cfg=None):
    """Lit cards stay strong. A pick is WEAK when it fails a gate now or is ≤ −25% since it joined; STRONG when it still
    passes and is ≥ 0. With ≥2 strong and ≥1 weak, the worst weak pick is swapped for the best passing runner not in the
    card (one per check, its result kept). With fewer than 2 strong and a weak one, the card is TAKEN DOWN (kept in history,
    off the stage). Returns (card, 'swap' | 'down' | None)."""
    if card.get('downAt'):
        return card, None
    live = {r['mint'] for r in passing}
    rows = []
    for p in card['picks']:
        since = p.get('swappedIn') or card['at']
        path = [px for t, px in paths.get(p['mint'], []) if since < t <= now]
        mv = (path[-1] / p['entry'] - 1) * 100 if path and _f(p.get('entry')) > 0 else None
        weak = p['mint'] in failing or (mv is not None and mv <= CARD_WEAK_PCT)
        rows.append({'p': p, 'mv': mv, 'weak': weak, 'strong': not weak and p['mint'] in live and (mv or 0) >= 0})
    weak = sorted((r for r in rows if r['weak']), key=lambda r: r['mv'] if r['mv'] is not None else -1e9)
    strong = [r for r in rows if r['strong']]
    if not weak:
        return card, None
    w = weak[0]['p']
    why = (list(failing.get(w['mint']) or [])[:1] or [f"down {weak[0]['mv']:.1f}% since it joined"])[0]
    if len(strong) >= 2:
        have = {p['mint'] for p in card['picks']}
        sub = next((x for x in sorted(passing, key=lambda x: -_f(x.get('score'))) if x['mint'] not in have and _f(x.get('price')) > 0), None)
        if not sub:
            return card, None
        new = {k: sub.get(k) for k in ('mint', 'symbol', 'logo', 'pairAddress')}
        new.update(lane=lane_of(sub, 1, sub.get('score')), entry=sub['price'], swappedIn=now)
        swap = {'at': now, 'out': {'mint': w['mint'], 'symbol': w.get('symbol')}, 'in': {'mint': sub['mint'], 'symbol': sub.get('symbol')}, 'why': why,
                'mult': round(_pick_mult(card, w, paths, now, cfg), 4)}
        return {**card, 'picks': [new if p is w else p for p in card['picks']], 'swaps': (card.get('swaps') or []) + [swap]}, 'swap'
    return {**card, 'downAt': now, 'downWhy': f"{len(strong)} strong of {len(rows)} — ${w.get('symbol')} {why}"}, 'down'


def play_exits(lane, entry, path, cfg=None):
    """Paper-play a lane's exit plan on the prices seen after entry → realized multiple (1.0 = flat).
    Ladder rungs sell their slice when hit; trail sells the rest when it falls `trail` pts below the peak gain;
    stop sells everything left. Whatever is left at the end is marked at the last price."""
    if entry <= 0:
        return 1.0
    plan = (exits(cfg) if cfg else EXITS)[lane]
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


def proof(rounds, paths, now, window=24 * 3600, cfg=None):
    """Each round in the window (at least one later price seen): equal-$ basket of its picks played with their lane exits.
    lights = enough rounds, positive average, ≥50% won."""
    rows = []
    for r in rounds:
        if now - r['at'] > window or not r.get('picks'):
            continue
        mults = []
        for p in r['picks']:
            since = p.get('swappedIn') or r['at']   # a swapped-in runner only counts from when it joined
            path = [px for t, px in paths.get(p['mint'], []) if t > since]
            if path:
                mults.append(play_exits(p['lane'], p['entry'], path, cfg))
        mults += [s['mult'] for s in r.get('swaps') or [] if s.get('mult')]   # swapped-out runners: closed at the swap
        if mults:
            rows.append(sum(mults) / len(mults))
    n = len(rows)
    avg = round((sum(rows) / n - 1) * 100, 2) if n else 0.0
    win = round(sum(1 for m in rows if m > 1) / n * 100) if n else 0
    need_n = clean_cfg(cfg)['lightRounds'] if cfg else LIGHT_MIN_ROUNDS
    return {'rounds': n, 'avgPct': avg, 'winRate': win, 'lights': n >= need_n and avg > 0 and win >= 50,
            'per1': round(1 + avg / 100, 3), 'need': max(0, need_n - n)}


def addon(legs, runners, slice_pct=20.0, n=2):
    """Runner add-on: bolt the top `n` runners onto any Fuse as a small slice (default 20%, split evenly); the basket's
    own legs keep their proportions in the rest."""
    rs = [r for r in runners if r.get('pairAddress')][:n]
    if not rs:
        return [dict(l) for l in legs]
    slice_pct = 100.0 if not legs else max(5.0, min(60.0, _f(slice_pct)))   # runners-only card = 100%
    total = sum(_f(l.get('weight')) for l in legs) or 1
    base = [{**l, 'weight': round(_f(l.get('weight')) / total * (100 - slice_pct), 2)} for l in legs]
    return base + [{'chainId': 'solana', 'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'baseAddress': r.get('mint'), 'logo': r.get('logo'),
                    'weight': round(slice_pct / len(rs), 2), 'runner': True, 'lane': r.get('lane'), 'exits': EXITS[r.get('lane') or 'runner']['label']} for r in rs]


SOURCES = {'arena': '🏟 Arena pick', 'lit': '🔥 Lit card', 'pump': '🚀 Pump scan', 'snipers': '🎯 Snipers out', 'creator': "📣 Creators' pick"}


def discover(passing, tags, limit=40):
    """Runner discovery: only coins that PASS every gate right now (fail closed — a popular coin that fails a gate is not
    shown). tags = {mint: {source: detail}} from the arena round, lit cards, the pump scan, snipers-out radar and creators'
    picks. More independent sources = higher; then score."""
    out = []
    for r in passing:
        t = tags.get(r['mint']) or {}
        if not t:
            continue
        out.append({**r, 'sources': [{'kind': k, 'label': SOURCES[k], 'detail': v} for k, v in t.items() if k in SOURCES]})
    return sorted(out, key=lambda r: (-len(r['sources']), -_f(r.get('score'))))[:limit]
