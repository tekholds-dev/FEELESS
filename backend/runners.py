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
    'bond': {'ladder': [(30.0, 0.5)], 'trail': 20.0, 'stop': -15.0, 'label': '½ at +30% (the bond pop) · trail 20 · stop −15%'},
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


def candidate(pair, intel=None, creator_flagged=False, snipers_out=False, now_ms=0, mayhem=False, creator_rep=None, hist=None, smart=0):
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
            'bundled': len(intel.get('bundledWallets') or []), 'scanned': bool(intel) and intel.get('top10Pct') is not None, 'creatorFlagged': bool(creator_flagged), 'snipersOut': bool(snipers_out),
            'mayhem': bool(mayhem or pair.get('mayhem') or pair.get('is_mayhem_mode')), 'creatorRep': creator_rep,
            # New checks (service keeps ~20 min of history per coin): curve speed, buyer acceleration, kill-switch signals
            'buysAccel': round(_f(((pair.get('txns') or {}).get('m5') or {}).get('buys')) / max(1.0, buys / 12), 2) if buys else 0.0,
            'curveSpeed': (hist or {}).get('curveSpeed'), 'top10Jump': (hist or {}).get('top10Jump'), 'devSold': bool((hist or {}).get('devSold')),
            'flaggedFunders': len(intel.get('flaggedFunders') or []), 'smartBuyers': int(smart or 0),
            'paid': bool((pair.get('info') or {}).get('header') or _f((pair.get('boosts') or {}).get('active')) > 0), 'boosts': int(_f((pair.get('boosts') or {}).get('active'))),
            **_socials(pair)}


def is_dip(c):
    """📉 Buy the dip: a coin that dropped hard on the day (24h ≤ −25%) and is BOUNCING with buyers — 5m green, 1h no longer
    falling (≥ −5%), buys ≥ 55% and buys speeding up. A coin still sliding is never a dip-buy."""
    return (_f(c.get('chg24h')) <= -25 and _f(c.get('chg5m')) >= 2 and _f(c.get('chg1h')) >= -5
            and _f(c.get('buyShare')) >= 55 and _f(c.get('buysAccel')) >= 1.0)


def _socials(pair):
    """Website / X / Telegram set at launch (DexScreener info.* or the launchpad's own fields)."""
    info = pair.get('info') or {}
    kinds = {str(x.get('type') or '').lower() for x in info.get('socials') or [] if isinstance(x, dict)}
    site = bool(info.get('websites') or pair.get('website'))
    x = bool('twitter' in kinds or 'x' in kinds or pair.get('twitter'))
    tg = bool('telegram' in kinds or pair.get('telegram'))
    return {'site': site, 'x': x, 'tg': tg}


# ⚠️ NEW runners: a TIGHT filter for coins only minutes/hours old — website + X set at launch, clean creator first, tight holders.
NEW_RUNNER = {'maxAgeH': 3.0, 'minBuyShare': 55.0, 'maxTop10': 25.0, 'maxDev': 5.0, 'maxBundled': 1, 'minVol1h': 3000.0}


def new_runners(rows, cfg=None, limit=12):
    """Young coins that pass the tight launch checks (all scanned): website AND X at launch, creator not suspect/high (clean
    sorts first), top-10 ≤25%, dev ≤5%, ≤1 bundle, buys ≥55%, 1h vol ≥ $3K. Each carries its reasons. Riskier than runners."""
    c = {**NEW_RUNNER, **(cfg or {})}
    out = []
    for r in rows or []:
        age = r.get('ageH')
        if age is None or age > c['maxAgeH'] or not r.get('scanned') or not (r.get('site') and r.get('x')):
            continue
        if r.get('creatorFlagged') or r.get('creatorRep') in ('suspect', 'high') or r.get('devSold') or r.get('mayhem'):
            continue
        if _f(r.get('top10')) > c['maxTop10'] or _f(r.get('dev')) > c['maxDev'] or int(r.get('bundled') or 0) > c['maxBundled']:
            continue
        if _f(r.get('buyShare')) < c['minBuyShare'] or _f(r.get('vol1h')) < c['minVol1h']:
            continue
        why = [f"{int(age * 60)}m old", 'site + X at launch' + (' + TG' if r.get('tg') else ''), f"top10 {_f(r.get('top10')):.0f}%", f"{_f(r.get('buyShare')):.0f}% buys"]
        if r.get('creatorRep') == 'clean':
            why.insert(1, '🧼 clean creator')
        out.append({**r, 'newRunner': True, 'why': why})
    return sorted(out, key=lambda r: (r.get('creatorRep') != 'clean', -_f(r.get('vol1h'))))[:limit]


# HQ › Runners settings. Every key is range-checked by clean_cfg(); defaults = the tested engine.
DEFAULT_CFG = {'roundSize': 5, 'minMcap': 8000, 'minVol1h': 5000, 'maxTop10': 30, 'maxInsiders': 15, 'maxDev': 10,
               'scalpTp': 50, 'scalpStop': 25, 'runnerTp1': 50, 'runnerTp2': 100, 'runnerTrail': 25, 'runnerStop': 30, 'holdTrail': 30, 'holdStop': 35, 'lightRounds': 8,
               # 🔔 Bond run (right before graduation): every box must tick — stiff on purpose, fun to watch fill up
               'bondCurve': 90, 'bondBuys': 60, 'bondVol1h': 10000, 'bondTop10': 20, 'bondPts': 15,
               # ⚔ Arena: the auto-built card each round (coins + pools) and how long a battle lasts
               'autoCoins': 4, 'autoPools': 3, 'battleMins': 60,
               # flow + bundles (were hard-coded) and the new checks
               'minBuyShare': 40, 'maxBuyShare': 85, 'minTrades1h': 50, 'maxBundled': 2, 'maxTop10Jump': 10,
               'bondWatchCurve': 75, 'bondSpeed10m': 8, 'smartMin': 3}

# ⚡ Stronger engine: what HQ is offered (one click) when its live config is weaker. Each with the reason.
RECOMMENDED = {'minMcap': (12000, 'Under $12K is mostly bots'), 'minVol1h': (10000, 'Real two-sided flow starts here'),
               'maxTop10': (25, 'Rugs cluster above 25% top-10'), 'maxInsiders': (10, 'Snipers/bundlers dump together'),
               'maxDev': (5, 'A dev holding 5%+ can end it in one sell'), 'maxBundled': (1, 'Bundles exit together'),
               'minBuyShare': (52, 'Buyers in control'), 'maxBuyShare': (80, '85% buys is usually wash or bots'),
               'minTrades1h': (80, 'Enough real trades to trust the flow'), 'bondVol1h': (15000, 'Bond runs need real volume'),
               'roundSize': (4, 'Fewer, better picks'), 'lightRounds': (12, 'Prove it over ~3h, not 2h')}
STRONGER_IS_LOWER = {'maxTop10', 'maxInsiders', 'maxDev', 'maxBundled', 'maxBuyShare', 'roundSize'}
CFG_RANGES = {'roundSize': (2, 10), 'minMcap': (1000, 1_000_000), 'minVol1h': (500, 1_000_000), 'maxTop10': (10, 60), 'maxInsiders': (2, 40), 'maxDev': (1, 30),
              'scalpTp': (10, 300), 'scalpStop': (5, 80), 'runnerTp1': (10, 300), 'runnerTp2': (20, 1000), 'runnerTrail': (5, 80), 'runnerStop': (5, 80),
              'holdTrail': (5, 80), 'holdStop': (5, 80), 'lightRounds': (3, 48),
              'bondCurve': (70, 99), 'bondBuys': (50, 90), 'bondVol1h': (1000, 1_000_000), 'bondTop10': (5, 40), 'bondPts': (0, 30),
              'autoCoins': (2, 6), 'autoPools': (1, 5), 'battleMins': (15, 240),
              'minBuyShare': (30, 70), 'maxBuyShare': (60, 95), 'minTrades1h': (10, 500), 'maxBundled': (0, 5), 'maxTop10Jump': (3, 40),
              'bondWatchCurve': (50, 89), 'bondSpeed10m': (1, 40), 'smartMin': (1, 10)}


def clean_cfg(p):
    out = dict(DEFAULT_CFG)
    for k, (lo, hi) in CFG_RANGES.items():
        if k in (p or {}):
            out[k] = int(min(hi, max(lo, _f(p[k]))))
    out['runnerTp2'] = max(out['runnerTp2'], out['runnerTp1'] + 10)
    return out


# 🔧 Auto-widen: when NOTHING passes, the engine loosens ONLY the soft gates one step at a time, never past these floors.
# Safety gates (pre-bond, mayhem, age, holder scan, insiders/bundles, top-10 spike, dev sold / dev %, creator flag / rep)
# are never touched. Each level = one step per soft gate; level 0 = the configured engine.
WIDEN_STEPS = {'maxTop10': (5, 35), 'minMcap': (-2000, 5000), 'minVol1h': (-2000, 3000),
               'minBuyShare': (-4, 45), 'maxBuyShare': (3, 88), 'minTrades1h': (-20, 40)}
WIDEN_MAX = 3


def widen(cfg, level):
    """The configured cfg with every soft gate moved `level` steps toward its floor (clamped). Pure."""
    c = clean_cfg(cfg)
    lv = max(0, min(WIDEN_MAX, int(level or 0)))
    for k, (step, floor) in WIDEN_STEPS.items():
        if k in c and lv:
            v = c[k] + step * lv
            c[k] = min(v, floor) if step > 0 else max(v, floor)
    return c


def widen_level(level, passing, min_pass=3, fill=8):
    """Next widen level from how many passed: under min_pass → one step wider; ≥ fill → one step back toward the config."""
    if passing < min_pass:
        return min(WIDEN_MAX, level + 1)
    if passing >= fill:
        return max(0, level - 1)
    return level


def gates(cfg=None):
    g = clean_cfg(cfg)
    return (   # key, label, test — ALL must pass (unknown forensics fail closed)
        ('prebond', 'Pre-bond or a fresh graduate (<48h)', lambda c: c['stage'] == 'curve' or (c['ageH'] is not None and c['ageH'] <= MAX_AGE_H)),   # graduates run too (more coins in the round)
        ('mayhem', 'Not a mayhem-mode coin', lambda c: not c.get('mayhem')),
        ('age', 'Under 48h old', lambda c: c['ageH'] is not None and 0 <= c['ageH'] <= MAX_AGE_H),
        ('size', f"Market cap ≥ ${g['minMcap'] / 1000:g}K", lambda c: c['mcap'] >= g['minMcap']),
        ('volume', f"1h volume ≥ ${g['minVol1h'] / 1000:g}K", lambda c: c['vol1h'] >= g['minVol1h']),
        ('flow', f"Two-sided flow ({g['minBuyShare']}–{g['maxBuyShare']}% buys, {g['minTrades1h']}+ trades/h)",
         lambda c: c['buyShare'] is not None and g['minBuyShare'] <= c['buyShare'] <= g['maxBuyShare'] and c['txns1h'] >= g['minTrades1h']),
        ('scan', 'Holder scan done', lambda c: c['scanned']),
        ('top10', f"Top 10 under {g['maxTop10']}%", lambda c: c['top10'] is not None and c['top10'] < g['maxTop10']),
        ('insiders', f"Snipers/bundlers under {g['maxInsiders']}% · ≤{g['maxBundled']} bundled", lambda c: (c['insiders'] or 0) < g['maxInsiders'] and c['bundled'] <= g['maxBundled']),
        # ⛔ kill switch: these flip a coin to failing at once → it's auto-swapped out of rounds and lit cards
        ('spike', f"No top-10 spike (+{g['maxTop10Jump']} pts in 5m)", lambda c: (c.get('top10Jump') or 0) < g['maxTop10Jump']),
        ('devsold', "Dev hasn't sold", lambda c: not c.get('devSold')),
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
            'hold': {'ladder': [], 'trail': float(g['holdTrail']), 'stop': -float(g['holdStop']), 'label': f"Trail {g['holdTrail']} pts · stop −{g['holdStop']}%"},
            'bond': EXITS['bond']}


def failed_gates(c, cfg=None):
    return [label for _, label, test in (gates(cfg) if cfg else GATES) if not test(c)]


def bond_check(c, cfg=None):
    """🔔 Bond checklist for a pre-bond coin. Two tiers, every box must tick:
    🔔 Bond run (≥ bondCurve, default 90%): curve, buys, 5m green, volume, holders, clean creator, curve SPEED, buyers ACCELERATING.
    👀 Bond watch (bondWatchCurve–bondCurve, default 75–89%): the same + REP-CONFIRMED — smart FEELESS buyers (trust ≥ 75 / elite),
       no flagged funder clusters, dev hasn't sold. Earlier entry pays more, so it has to prove more."""
    k = clean_cfg(cfg)
    cur = _f(c.get('curve'))
    if c.get('stage') != 'curve' or cur < k['bondWatchCurve'] or cur >= 100:
        return []
    run = cur >= k['bondCurve']
    checks = [{'id': 'curve', 'label': f"⚡ {k['bondCurve'] if run else k['bondWatchCurve']}%+ up the curve", 'ok': True},
              {'id': 'buys', 'label': f"🟢 {k['bondBuys']}%+ buys", 'ok': _f(c.get('buyShare')) >= k['bondBuys']},
              {'id': 'green', 'label': '📈 5m green', 'ok': _f(c.get('chg5m')) > 0},
              {'id': 'vol', 'label': f"🌊 ${k['bondVol1h'] / 1000:g}K+ 1h volume", 'ok': _f(c.get('vol1h')) >= k['bondVol1h']},
              {'id': 'holders', 'label': f"🎯 snipers out or top-10 < {k['bondTop10']}%", 'ok': bool(c.get('snipersOut')) or (c.get('top10') is not None and _f(c.get('top10')) < k['bondTop10'])},
              {'id': 'creator', 'label': '🧼 clean creator', 'ok': c.get('creatorRep') == 'clean'},
              {'id': 'speed', 'label': f"🏎 curve +{k['bondSpeed10m']} pts in 10m", 'ok': c.get('curveSpeed') is not None and _f(c.get('curveSpeed')) >= k['bondSpeed10m']},
              {'id': 'accel', 'label': '🔥 buyers accelerating (5m vs 1h pace)', 'ok': _f(c.get('buysAccel')) >= 1.2}]
    if not run:
        checks += [{'id': 'smart', 'label': f"🧠 {k['smartMin']}+ smart FEELESS buyers", 'ok': int(c.get('smartBuyers') or 0) >= k['smartMin']},
                   {'id': 'funders', 'label': '🕸 no flagged funder clusters', 'ok': int(c.get('flaggedFunders') or 0) == 0},
                   {'id': 'devhold', 'label': "🔒 dev hasn't sold", 'ok': not c.get('devSold')}]
    return checks


def bond_tier(c, cfg=None):
    """'run' | 'watch' | None — only when EVERY box of that tier ticks."""
    ch = bond_check(c, cfg)
    if not ch or not all(x['ok'] for x in ch):
        return None
    return 'run' if _f(c.get('curve')) >= clean_cfg(cfg)['bondCurve'] else 'watch'


def near_bond(c, cfg=None):
    """Right before it bonds: every 🔔 Bond run box ticks."""
    return bond_tier(c, cfg) == 'run'


BOND_PTS = DEFAULT_CFG['bondPts']


def score(c, cfg=None):
    """0–100 with the reason for every part (shown on the board)."""
    mom = max(0.0, min(30.0, c['chg1h'] / 10))                                   # +300%/h → 30
    acc = max(0.0, min(15.0, c['chg5m'] / 2))                                    # +30%/5m → 15
    vel = max(0.0, min(20.0, (c['vol1h'] / c['mcap'] * 10) if c['mcap'] else 0))  # turnover 2×/h → 20
    flow = max(0.0, 10 - abs((c['buyShare'] or 0) - 60) / 2)                     # sweet spot ~60% buys
    curve = 10.0 if c['stage'] == 'curve' and 60 <= c['curve'] <= 95 else 5.0 if c['stage'] == 'graduated' else 0.0
    # Pre-bond lives on volume: real $ traded in the last hour (log scale, $5K → 0 · $50K → 7.5 · $500K → 15). A pre-bond
    # coin with thin volume (< $20K/h) only gets half the curve points — a curve climbing on dust isn't a runner.
    pre = c['stage'] == 'curve'
    vol = max(0.0, min(15.0, 7.5 * math.log10(c['vol1h'] / 5000))) if c['vol1h'] > 5000 else 0.0
    vol = vol if pre else vol / 2
    if pre and c['vol1h'] < 20000:
        curve /= 2
    rep_pts = {'clean': 5.0, 'watch': -10.0}.get(c.get('creatorRep'), 0.0)       # reputation: clean creators earn, "watch" pays
    bonus = (8.0 if c['snipersOut'] else 0.0) + min(7.0, c['quality'] / 14) + rep_pts
    tier = bond_tier(c, cfg)
    bond = float(clean_cfg(cfg)['bondPts']) * (1.0 if tier == 'run' else 0.5 if tier == 'watch' else 0.0)
    dip = min(10.0, -_f(c.get('chg24h')) / 6) if is_dip(c) else 0.0              # 📉 bounce off a big drop, buyers back
    paid = 4.0 if c.get('paid') else 0.0                                          # 💳 DEX paid profile / boosted
    pts = round(min(100.0, mom + acc + vel + vol + flow + curve + bonus + bond + dip + paid), 1)
    return pts, [{'part': 'momentum', 'points': round(mom, 1), 'why': f"{c['chg1h']:+.0f}% in 1h"},
                 {'part': 'acceleration', 'points': round(acc, 1), 'why': f"{c['chg5m']:+.0f}% in 5m"},
                 {'part': 'velocity', 'points': round(vel, 1), 'why': f"1h volume = {c['vol1h'] / c['mcap'] if c['mcap'] else 0:.1f}× market cap"},
                 {'part': 'volume', 'points': round(vol, 1), 'why': f"${c['vol1h'] / 1000:,.0f}K traded in 1h" + (' (pre-bond: volume counts double)' if pre else '')},
                 {'part': 'flow', 'points': round(flow, 1), 'why': f"{c['buyShare']}% buys" if c['buyShare'] is not None else 'no flow'},
                 {'part': 'stage', 'points': curve, 'why': f"{c['curve']:.0f}% up the curve" if c['stage'] == 'curve' else 'graduated (own pool)'},
                 *([{'part': 'bond run' if tier == 'run' else 'bond watch', 'points': bond, 'why': f"{c['curve']:.0f}% up the curve, every {'bond run' if tier == 'run' else 'rep-confirmed bond watch'} box ticked"}] if bond else []),
                 *([{'part': 'dip buy', 'points': round(dip, 1), 'why': f"{_f(c.get('chg24h')):+.0f}% on the day, bouncing {_f(c.get('chg5m')):+.0f}% in 5m with {c['buyShare']}% buys"}] if dip else []),
                 *([{'part': 'dex paid', 'points': paid, 'why': 'DexScreener profile paid' + (f" · {c.get('boosts')} boosts" if c.get('boosts') else '')}] if paid else []),
                 {'part': 'bonus', 'points': round(bonus, 1), 'why': ('snipers sold out · ' if c['snipersOut'] else '') + f"quality {c['quality']:.0f}" + (f" · creator {c.get('creatorRep')}" if c.get('creatorRep') else '')}]


def lane_of(c, streak=0, pts=0):
    if c.get('bondTier'):         # 🔔/👀 right before bonding: take half at the pop, trail the rest
        return 'bond'
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
        pts, parts = score(c, cfg)
        row = {**c, 'score': pts, 'parts': parts, 'gates': bad, 'bond': bond_check(c, cfg), 'bondTier': bond_tier(c, cfg)}
        (dropped if bad else passing).append(row)
    passing.sort(key=lambda r: -r['score'])
    return {'passing': passing, 'dropped': sorted(dropped, key=lambda r: -r['score'])[:30]}


def next_round(prev, passing, now, size=ROUND_SIZE, rid='', weights=None):
    """Best runners STAY for another round (streak + 1, may graduate to the hold lane); the rest of the slots go to the
    best newcomers. prev = last round or None. `weights` = self-tuned lane weights: newcomers are ranked by score × the
    weight of the lane they'd join (a lane that keeps losing gets fewer seats)."""
    if weights:
        passing = sorted(passing, key=lambda r: -_f(r.get('score')) * _f(weights.get(lane_of(r, 1, r.get('score')), 1.0)))
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


SOURCES = {'grad': '🎓 Fresh grad', 'bond': '🔔 About to bond', 'watch': '👀 Bond watch', 'arena': '🏟 Arena pick', 'lit': '🔥 Lit card', 'pump': '🚀 Pump scan', 'snipers': '🎯 Snipers out', 'creator': "📣 Creators' pick",
           'dip': '📉 Dip buy', 'paid': '💳 Dex paid'}


def fresh_grads(dropped):
    """🎓 Fresh grads: coins that graduated in the last 48h and pass EVERY other gate (holders, insiders, dev, creator, flow,
    volume, size). The pre-bond gate is the only one they miss — so the board never sits empty while clean young coins run."""
    return [r for r in dropped or [] if r.get('stage') == 'graduated' and r.get('gates') == ['Pre-bond (still on the curve)']]


def discover(passing, tags, limit=40):
    """Runner discovery: only coins that PASS every gate right now (fail closed — a popular coin that fails a gate is not
    shown). tags = {mint: {source: detail}} from the arena round, lit cards, the pump scan, snipers-out radar and creators'
    picks. More independent sources = higher; then score."""
    out = []
    for r in passing:
        t = dict(tags.get(r['mint']) or {})
        if is_dip(r):          # 📉 / 💳 come from the coin itself — every gated coin can earn them, no outside list needed
            t.setdefault('dip', f"{_f(r.get('chg24h')):+.0f}% day, {_f(r.get('chg5m')):+.0f}% 5m bounce")
        if r.get('paid'):
            t.setdefault('paid', 'DexScreener profile paid' + (f" · {r.get('boosts')} boosts" if r.get('boosts') else ''))
        if not t:
            continue
        out.append({**r, 'sources': [{'kind': k, 'label': SOURCES[k], 'detail': v} for k, v in t.items() if k in SOURCES]})
    return sorted(out, key=lambda r: (-len(r['sources']), -_f(r.get('score'))))[:limit]



def auto_card(passing, pools, now, cfg=None):
    """⚔ Arena build: each round the arena fuses its own card — the best `autoCoins` gated runners (bond runs first, then
    score) + the best `autoPools` live pools (deep, busy, not falling). Coins 40% / pools 60% of the weight. Entry = the
    price at build time, so its live % is honest from the moment it's dealt. Traders loading it still get 3 + 3."""
    k = {**DEFAULT_CFG, **(cfg or {})}
    coins = sorted([r for r in passing if _f(r.get('price')) > 0], key=lambda r: (-near_bond(r, cfg), -_f(r.get('score'))))[:int(k['autoCoins'])]
    good = [p for p in pools if _f(p.get('liquidityUsd')) >= 100_000 and _f(p.get('priceUsd')) > 0 and _f(p.get('change24h')) > -15]
    pls = sorted(good, key=lambda p: -(min(400.0, _f(p.get('aprEst'))) + min(50.0, _f(p.get('change24h')))))[:int(k['autoPools'])]
    if not coins and not pls:
        return None
    cw = 40.0 if pls else 100.0
    legs = [{'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'baseAddress': r['mint'], 'logo': r.get('logo'), 'entry': _f(r['price']), 'runner': True,
             'lane': r.get('lane') or 'runner', 'weight': round(cw / len(coins), 2)} for r in coins if r.get('pairAddress')]
    legs += [{'pairAddress': p['pairAddress'], 'symbol': p.get('symbol'), 'baseAddress': p.get('baseAddress'), 'logo': p.get('logo'), 'entry': _f(p['priceUsd']),
              'weight': round((100 - cw if coins else 100) / len(pls), 2)} for p in pls]
    return {'id': f"auto{int(now)}", 'at': now, 'legs': legs}


def pair_battles(cards):
    """⚔ Battles: stage cards paired by activity (1 v 2, 3 v 4…) — hot fights hot, calm fights calm. Odd one out sits."""
    s = sorted(cards, key=lambda c: -_f((c.get('activity') or {}).get('score')))
    return [(s[i], s[i + 1]) for i in range(0, len(s) - 1, 2)]


def settle_battle(a_start, a_now, b_start, b_now):
    """The card whose % moved more since the bell wins; a dead heat (< 0.05 pts) is a draw."""
    da, db = _f(a_now) - _f(a_start), _f(b_now) - _f(b_start)
    return 'draw' if abs(da - db) < 0.05 else 'a' if da > db else 'b'



def suggest_cfg(cfg):
    """⚡ Stronger engine: every setting where the live config is weaker than RECOMMENDED, with the reason. HQ is asked to
    click to apply — nothing changes by itself."""
    cur = clean_cfg(cfg)
    out = []
    for k, (to, why) in RECOMMENDED.items():
        now = cur[k]
        weaker = now > to if k in STRONGER_IS_LOWER else now < to
        if weaker:
            out.append({'key': k, 'now': now, 'to': to, 'why': why})
    return out


LANE_DAYS = 3


def lane_proofs(rounds, paths, now, cfg=None, days=LANE_DAYS):
    """Self-tuning lanes: each lane's $5 run over the last `days` days (every pick played with its lane's exits), and how
    many of those days IN A ROW (most recent first) it lost."""
    out = {}
    for r in rounds:
        if now - r['at'] > days * 86400:
            continue
        day = int((now - r['at']) // 86400)
        for p in r.get('picks') or []:
            since = p.get('swappedIn') or r['at']
            path = [px for t, px in paths.get(p['mint'], []) if t > since]
            if not path or not _f(p.get('entry')):
                continue
            m = play_exits(p.get('lane') or 'runner', p['entry'], path, cfg)
            a = out.setdefault(p.get('lane') or 'runner', {'n': 0, 'sum': 0.0, 'wins': 0, 'days': {}})
            a['n'] += 1; a['sum'] += m; a['wins'] += m > 1
            d = a['days'].setdefault(day, [0.0, 0]); d[0] += m; d[1] += 1
    res = {}
    for lane, a in out.items():
        streak = 0
        for day in range(days):
            if day not in a['days']:
                break
            s, n = a['days'][day]
            if s / n < 1:
                streak += 1
            else:
                break
        res[lane] = {'n': a['n'], 'avgPct': round((a['sum'] / a['n'] - 1) * 100, 2), 'winRate': round(a['wins'] / a['n'] * 100), 'losingDays': streak}
    return res


def lane_weights(proofs):
    """Lane seats: a lane that lost 3 days running gets half weight; the best proven lane (≥10 picks, average > 0) gets 1.25×."""
    w = {lane: 0.5 if pr['losingDays'] >= LANE_DAYS else 1.0 for lane, pr in proofs.items()}
    good = [(l, pr) for l, pr in proofs.items() if pr['n'] >= 10 and pr['avgPct'] > 0 and w[l] == 1.0]
    if good:
        w[max(good, key=lambda x: x[1]['avgPct'])[0]] = 1.25
    return w


# ---- 🎚 Engine dial (HQ): one choice sets the runner engine (gates + lanes), on top of the tested defaults ----------
ENGINE_DIALS = {
    'safe': {'label': '🛡 Safe', 'cfg': {'minMcap': 15000, 'minVol1h': 12000, 'maxTop10': 22, 'maxInsiders': 8, 'maxDev': 4, 'maxBundled': 1, 'roundSize': 3,
                                        'scalpTp': 35, 'scalpStop': 15, 'runnerTp1': 35, 'runnerTp2': 80, 'runnerTrail': 15, 'runnerStop': 20, 'lightRounds': 16},
             'why': 'Strictest gates, 3 picks, quick exits, needs 16 proven rounds'},
    'balanced': {'label': '⚖ Balanced', 'cfg': {k: v for k, (v, _) in RECOMMENDED.items()}, 'why': 'The recommended engine (⚡ Stronger engine values)'},
    'degen': {'label': '🚀 Degen', 'cfg': {'minMcap': 8000, 'minVol1h': 6000, 'maxTop10': 30, 'maxInsiders': 15, 'maxDev': 8, 'roundSize': 6,
                                          'scalpTp': 80, 'scalpStop': 30, 'runnerTp1': 60, 'runnerTp2': 150, 'runnerTrail': 30, 'runnerStop': 35, 'lightRounds': 8},
              'why': 'Looser gates, 6 picks, let winners run longer'},
}


def engine_dial(dial, cfg=None):
    """HQ dial → a full engine cfg (clean_cfg-validated). Unknown dial → ValueError."""
    if dial not in ENGINE_DIALS:
        raise ValueError('Pick Safe, Balanced or Degen.')
    return {**clean_cfg({**(cfg or {}), **ENGINE_DIALS[dial]['cfg']}), 'dial': dial}


def dial_proof(rounds, paths, now, dials, window=24 * 3600):
    """Auto paper cards per RISK dial: every round's picks played with that dial's take-profit / stop-loss on the prices seen
    after the round. dials = {id: {'runner': (tp, sl)}}. → {id: {rounds, avgPct, winRate, per1}} (a dial lights like proof())."""
    out = {}
    for did, d in dials.items():
        tp, sl = d['runner']
        rows = []
        for r in rounds:
            if now - r['at'] > window or not r.get('picks'):
                continue
            mults = []
            for p in r['picks']:
                path = [px for t, px in paths.get(p['mint'], []) if t > r['at']]
                if path and p.get('entry', 0) > 0:
                    mults.append(_dial_play(p['entry'], path, tp, sl))
            if mults:
                rows.append(sum(mults) / len(mults))
        n = len(rows)
        avg = round((sum(rows) / n - 1) * 100, 2) if n else 0.0
        out[did] = {'rounds': n, 'avgPct': avg, 'winRate': round(sum(1 for m in rows if m > 1) / n * 100) if n else 0, 'per1': round(1 + avg / 100, 3),
                    'lit': n >= LIGHT_MIN_ROUNDS and avg > 0 and (sum(1 for m in rows if m > 1) / n) >= 0.5}
    return out


def _dial_play(entry, path, tp, sl):
    for px in path:
        g = (px / entry - 1) * 100
        if g >= tp:
            return round(px / entry, 4)
        if g <= -sl:
            return round(px / entry, 4)
    return round(path[-1] / entry, 4)


def auto_pick(proof, current, min_rounds=8, margin=2.0):
    """🔧 Auto-strength: the engine dial to run next. Switch only to a dial PROVEN better (≥ min_rounds, avg > 0, ahead of the
    current dial by ≥ margin pts of avg round). Never switches on noise; returns (dial, why) or (None, None)."""
    cur = (proof or {}).get(current) or {}
    ok = [(d, p) for d, p in (proof or {}).items() if p.get('rounds', 0) >= min_rounds and p.get('avgPct', 0) > 0]
    if not ok:
        return None, None
    d, p = max(ok, key=lambda x: x[1]['avgPct'])
    if d == current or p['avgPct'] - (cur.get('avgPct') or 0) < margin:
        return None, None
    return d, f"{d} dial avg {p['avgPct']:+.1f}% over {p['rounds']} rounds vs {current or 'custom'} {cur.get('avgPct', 0):+.1f}%"


PROOF_WINDOWS = {'6h': 6 * 3600, '24h': 24 * 3600, '72h': 72 * 3600}


def auto_pick_multi(proofs, current, margin=2.0):
    """Robust auto-strength: the engine tests every dial over SEVERAL windows (6h · 24h · 72h). Switch only when the SAME
    dial wins (proven: rounds ≥ 4/8/16, avg > 0, ≥ margin ahead of the current) in every window that has enough rounds —
    and at least two windows agree. Noise in one window never flips the engine."""
    need = {'6h': 4, '24h': 8, '72h': 16}
    winners, whys = [], []
    for w, proof in (proofs or {}).items():
        d, why = auto_pick(proof, current, min_rounds=need.get(w, 8), margin=margin)
        if d:
            winners.append(d); whys.append(f'{w}: {why}')
        elif any(p.get('rounds', 0) >= need.get(w, 8) for p in (proof or {}).values()):
            winners.append(None)   # a window with enough data that does NOT agree vetoes the switch
    picks = [d for d in winners if d]
    if len(picks) >= 2 and len(set(winners)) == 1:
        return picks[0], ' · '.join(whys)
    return None, None


SCENARIO_TP = (30, 50, 100, 200)
SCENARIO_SL = (15, 25, 40)


def scenarios(rounds, paths, now, dials):
    """🧪 Engine-cycled scenario cards: every runner round replayed under 12 TP × SL exit combos (24h) + each dial over 6h / 24h /
    72h — 21 cards, best first, each with its rounds, average, win rate and $1 → result. Real prices, no money."""
    out = []
    grid = {f'tp{tp}_sl{sl}': {'runner': (tp, sl)} for tp in SCENARIO_TP for sl in SCENARIO_SL}
    for sid, p in dial_proof(rounds, paths, now, grid).items():
        tp, sl = grid[sid]['runner']
        out.append({'id': sid, 'kind': 'exits', 'label': f'TP +{tp}% · stop −{sl}%', 'window': '24h', 'tp': tp, 'sl': sl, **p})
    for w, sec in PROOF_WINDOWS.items():
        for did, p in dial_proof(rounds, paths, now, dials, window=sec).items():
            out.append({'id': f'{did}_{w}', 'kind': 'dial', 'label': f'{did} dial · {w}', 'window': w, 'tp': dials[did]['runner'][0], 'sl': dials[did]['runner'][1], **p})
    for fid, v in filter_proof(rounds, paths, now).items():   # 🔬 pick-filter scenarios: WHICH picks to take (the doctor's view)
        if fid != '_all' and v.get('ready') and v.get('avgPct') is not None:
            out.append({'id': f'f_{fid}', 'kind': 'filter', 'filter': fid, 'label': v['label'], 'window': '24h', 'tp': 100, 'sl': 30,
                        'rounds': v['picks'], 'avgPct': v['avgPct'], 'winRate': v['winRate'], 'per1': round(1 + v['avgPct'] / 100, 2)})
    return sorted(out, key=lambda s: (not (s.get('rounds') or 0), -(s.get('avgPct') or 0)))


def exits_pick(grids, current, min_rounds=8, margin=2.0):
    """💡 Scenario winner → runner exits. grids = {window: dial_proof over the TP×SL grid}. Apply a combo only when the SAME
    combo is best in every window with enough rounds (≥2 windows), avg > 0, and ≥ margin ahead of the current exits' combo.
    current = (tp, sl). Returns ((tp, sl), why) or (None, None)."""
    bests = []
    for w, g in (grids or {}).items():
        ok = {k: p for k, p in (g or {}).items() if p.get('rounds', 0) >= min_rounds}
        if not ok:
            continue
        k, p = max(ok.items(), key=lambda kv: kv[1].get('avgPct', 0))
        cur = ok.get(f'tp{current[0]}_sl{current[1]}', {}).get('avgPct', 0)
        bests.append((k, p, cur, w))
    if len(bests) < 2 or len({b[0] for b in bests}) != 1:
        return None, None
    k = bests[0][0]
    if any(p.get('avgPct', 0) <= 0 or p['avgPct'] - cur < margin for _, p, cur, _ in bests):
        return None, None
    tp, sl = (int(x[2:]) for x in k.split('_'))
    if (tp, sl) == tuple(current):
        return None, None
    return (tp, sl), ' · '.join(f"{w}: TP +{tp}% / stop −{sl}% avg {p['avgPct']:+.1f}% vs current {cur:+.1f}%" for _, p, cur, w in bests)


def scenario_grid(rounds, paths, now, window):
    return dial_proof(rounds, paths, now, {f'tp{tp}_sl{sl}': {'runner': (tp, sl)} for tp in SCENARIO_TP for sl in SCENARIO_SL}, window=window)


def scenario_cards(scen, picks, anchor=None, top=3, losers_ok=False):
    """🃏 The best scenarios become REAL cards: this round's gated runner picks (≤3) + a SOL anchor (35%), with that scenario's
    TP / SL on every runner. Only scenarios with rounds and avg > 0 qualify. Pure."""
    out, used = [], set()
    runners = [p for p in picks or [] if p.get('pairAddress')][:3]
    if not runners:
        return out
    for sc in [s for s in scen or [] if (s.get('rounds') or 0) > 0 and (losers_ok or (s.get('avgPct') or 0) > 0)][:top]:   # battles may field losers (experiments)
        runners = [p for p in picks or [] if p.get('pairAddress')][:3]
        if sc.get('kind') == 'filter':   # a filter card only takes this round's picks that match its rule
            test = (PICK_FILTERS.get(sc.get('filter')) or (None, lambda p: True))[1]
            runners = [p for p in runners if test(p)] or runners[:1]
        legs = ([{**anchor, 'role': 'anchor', 'weight': 35}] if anchor else [])
        each = round((100 - (35 if anchor else 0)) / len(runners), 2)
        legs += [{'chainId': 'solana', 'pairAddress': p['pairAddress'], 'mint': p.get('mint'), 'symbol': p.get('symbol'), 'logo': p.get('logo'),
                  'role': 'runner', 'weight': each, 'tp': sc['tp'], 'sl': sc['sl']} for p in runners]
        dial = dial_of(sc['tp'], sc['sl'], sc['id'].split('_')[0] if sc.get('kind') == 'dial' else None)
        out.append({'id': sc['id'], 'label': sc['label'], 'window': sc['window'], 'tp': sc['tp'], 'sl': sc['sl'], 'avgPct': sc['avgPct'],
                    'winRate': sc.get('winRate'), 'rounds': sc['rounds'], 'per1': sc.get('per1'), 'legs': legs,
                    'dial': dial, 'name': card_name(dial, sc['id'], used), 'cfg': card_cfg(dial, sc)})
    return out


# 🃏 Card names: simple, degen, 1–2 emojis — picked by the card's dial (safe / balanced / degen), stable per scenario id.
CARD_NAMES = {
    'safe': ['🛡 Comfy Bag', '🧊 Cold Hands', '🏦 Bag Secured', '🐢 Slow Cook', '⚓ Anchor Gang', '🧘 Zen Hold'],
    'balanced': ['⚖️ Mid Curve', '🎯 Sniper Mode', '🧠 Big Brain', '🌊 Wave Rider', '🥷 Silent Ape', '🦊 Sly Fox'],
    'degen': ['🚀 Moon Mission', '🔥 Full Send', '🦍 Ape Season', '💎🙌 Diamond Hands', '🎰 Casino Night', '⚡ Send It'],
}
DIAL_CFG = {'safe': {'rotateHours': 24, 'slMode': 'park'}, 'balanced': {'rotateHours': 6, 'slMode': 'sell'}, 'degen': {'rotateHours': 1, 'slMode': 'sell'}}


def dial_of(tp, sl, dial=None):
    """Which look a card wears: a dial scenario keeps its dial; exits cards: big TP or wide stop = degen, tight = safe."""
    if dial in CARD_NAMES:
        return dial
    tp, sl = _f(tp), _f(sl)
    return 'degen' if tp >= 200 or sl >= 35 else 'safe' if tp <= 50 and sl <= 20 else 'balanced'


def card_name(dial, seed, used=None):
    """Stable per seed; skips names already `used` this round so two cards never share one."""
    names = CARD_NAMES.get(dial) or CARD_NAMES['balanced']
    i = sum(ord(ch) for ch in str(seed)) % len(names)
    for k in range(len(names)):
        n = names[(i + k) % len(names)]
        if not used or n not in used:
            if used is not None:
                used.add(n)
            return n
    return names[i]


def card_cfg(dial, sc):
    """The configs a card plays with (shown as chips): TP / stop per runner, rotate clock, stop mode, proof window."""
    return {'tp': int(_f(sc.get('tp'))), 'sl': int(_f(sc.get('sl'))), 'window': sc.get('window'), **DIAL_CFG.get(dial, DIAL_CFG['balanced'])}


def tag_versions(cards, versions, listed):
    """Playground cards from the same scenario are one bloodline: v.01, v.02 … (bumped each round it's dealt). Each card gets
    `vName`, its scenario `combo` (hover) and where it's listed on the Fuse terminal: 'stage' (published) / 'bench' / None."""
    out = []
    for c in cards or []:
        v = max(1, int((versions or {}).get(c['id']) or 1))
        out.append({**c, 'version': v, 'vName': f"{c.get('name') or c.get('label')} v.{v:02d}",
                    'combo': f"{c.get('label')} · proof {c.get('window')} · {c.get('dial') or '—'} dial · {c.get('rounds') or 0} rounds",
                    'listed': (listed or {}).get(c['id'])})
    return out


BATTLE_MAX = 2   # 2 Arena battles at once (4 cards going PvP) — the rest wait in the 'up next' queue


def card_sig(c):
    """A card's config fingerprint: same coins + same exits + same dial = the same card (only one may fight)."""
    cfg = c.get('cfg') or {}
    legs = tuple(sorted(l.get('pairAddress') or '' for l in c.get('legs') or []))
    return (legs, cfg.get('tp'), cfg.get('sl'), c.get('dial') or '') if legs else ('card', f"{c.get('kind')}:{c.get('id')}")


def unique_cards(cards):
    """Drop duplicate configs — the hottest copy stays."""
    seen, out = set(), []
    for c in sorted(cards or [], key=lambda c: -_f((c.get('activity') or {}).get('score'))):
        sg = card_sig(c)
        if sg not in seen:
            seen.add(sg); out.append(c)
    return out


# 🏆 Bracket (double elimination, rolling): every card that made it starts 0–0 in the WINNERS bracket; a loss drops it to the
# LOSERS bracket; a second loss knocks it out. Winners fight winners, losers fight losers (odd ones cross over). When fewer than
# two cards are left standing, the last one is crowned champion and a fresh bracket starts.
def bracket_pairs(cards, bracket, battles=3):
    key = lambda c: f"{c['kind']}:{c['id']}"
    loss = lambda c: int(((bracket or {}).get(key(c)) or {}).get('l') or 0)
    heat = lambda c: -_f((c.get('activity') or {}).get('score'))
    alive = [c for c in unique_cards(cards) if loss(c) < 2]
    wb = sorted([c for c in alive if loss(c) == 0], key=heat)
    lb = sorted([c for c in alive if loss(c) == 1], key=heat)
    pairs = []
    for grp in (wb, lb):
        while len(grp) >= 2 and len(pairs) < battles:
            pairs.append((grp.pop(0), grp.pop(0)))
    if wb and lb and len(pairs) < battles:   # odd ones out cross brackets
        pairs.append((wb.pop(0), lb.pop(0)))
    return pairs


def bracket_update(bracket, results):
    """W/L in the current bracket from settled battles ({aKey, bKey, winnerKey, draw}). Draws change nothing."""
    b = {k: dict(v) for k, v in (bracket or {}).items()}
    for r in results or []:
        if r.get('draw') or not r.get('winnerKey'):
            continue
        lose = r['bKey'] if r['winnerKey'] == r['aKey'] else r['aKey']
        b.setdefault(r['winnerKey'], {'w': 0, 'l': 0})['w'] += 1
        b.setdefault(lose, {'w': 0, 'l': 0})['l'] += 1
    return b


def bracket_done(cards, bracket):
    """Champion key when fewer than 2 unique cards are still standing (and someone has fought), else None."""
    alive = [c for c in unique_cards(cards) if int(((bracket or {}).get(f"{c['kind']}:{c['id']}") or {}).get('l') or 0) < 2]
    fought = any((v or {}).get('w') or (v or {}).get('l') for v in (bracket or {}).values())
    if fought and len(alive) < 2:
        return f"{alive[0]['kind']}:{alive[0]['id']}" if alive else ''
    return None


def battle_seats(stage, bench, battles=2):
    """⚔ Who fights: stage cards first (hottest), runners-up from the bench fill empty seats — max `battles` fights
    (4 cards → 2 battles, both visible). Pure."""
    s = sorted(stage or [], key=lambda c: -_f((c.get('activity') or {}).get('score')))[:battles * 2]
    s += sorted(bench or [], key=lambda c: -_f((c.get('activity') or {}).get('score')))[:max(0, battles * 2 - len(s))]
    return pair_battles(s)


def log_drops(log, dropped, now, cap=400):
    """Remember each rejected PRE-BOND coin once a day with the gate that stopped it + its price then (for gate_regret)."""
    seen = {(e['mint'], int(e['at'] // 86400)) for e in log or []}
    out = list(log or [])
    for r in dropped or []:
        if r.get('stage') != 'curve' or not r.get('gates') or not _f(r.get('price')):
            continue
        k = (r['mint'], int(now // 86400))
        if k not in seen:
            out.append({'mint': r['mint'], 'pairAddress': r.get('pairAddress'), 'symbol': r.get('symbol'), 'gate': r['gates'][0], 'price': _f(r['price']), 'at': now}); seen.add(k)
    return out[-cap:]


def gate_regret(log, prices, now, min_age=6 * 3600, ran=3.0):
    """💡 Which gates block winners: of the coins a gate stopped (≥ min_age ago), how many later ran ≥ `ran`×. A gate that
    keeps stopping 3× coins is a candidate to loosen — only that gate, never the safety gates as a group."""
    by = {}
    for e in log or []:
        if now - e['at'] < min_age:
            continue
        px = _f((prices or {}).get(e.get('pairAddress')))
        if px <= 0:
            continue
        g = by.setdefault(e['gate'], {'gate': e['gate'], 'stopped': 0, 'ran': 0, 'examples': []})
        g['stopped'] += 1
        if px / e['price'] >= ran:
            g['ran'] += 1; g['examples'] = (g['examples'] + [f"${e.get('symbol')} {px / e['price']:.1f}×"])[-3:]
    return sorted(({**g, 'rate': round(g['ran'] / g['stopped'] * 100, 1)} for g in by.values()), key=lambda g: -g['rate'])


# 🔬 PICK FILTERS — the engine learns WHICH picks win, not only which exits. Every past pick kept its entry snapshot (score, flow,
# stage, socials, holders…); each filter replays only the picks that match it, with their lane exits, on the prices seen after.
PICK_FILTERS = {
    'score70': ('🏅 Score ≥ 70', lambda p: _f(p.get('score')) >= 70),
    'green5m': ('🟢 5m green at entry', lambda p: _f(p.get('chg5m')) > 0),
    'buyers60': ('🛒 Buyers ≥ 60%', lambda p: _f(p.get('buyShare')) >= 60),
    'accel': ('⚡ Buyers accelerating', lambda p: _f(p.get('buysAccel')) >= 1.5),
    'grad': ('🎓 Graduated only', lambda p: p.get('stage') == 'graduated'),
    'curve': ('📈 Pre-bond only', lambda p: p.get('stage') == 'curve'),
    'clean': ('🧼 Clean creator', lambda p: p.get('creatorRep') == 'clean'),
    'socials': ('🌐 Site + X', lambda p: bool(p.get('site') and p.get('x'))),
    'deep': ('🌊 Liquidity ≥ $30K', lambda p: _f(p.get('liq')) >= 30_000),
    'small': ('🐣 Mcap < $100K', lambda p: 0 < _f(p.get('mcap')) < 100_000),
    'big': ('🐋 Mcap ≥ $300K', lambda p: _f(p.get('mcap')) >= 300_000),
    'tight': ('🔒 Top-10 < 20%', lambda p: p.get('top10') is not None and _f(p.get('top10')) < 20),
    'snipers': ('🎯 Snipers out', lambda p: bool(p.get('snipersOut'))),
    'cool': ('🧊 Not chased (1h < +50%)', lambda p: _f(p.get('chg1h')) < 50),
}


def filter_proof(rounds, paths, now, cfg=None, window=24 * 3600, min_picks=6):
    """{filter: {label, picks, avgPct, winRate}} — every matching pick in the window played with its lane exits (equal $ each)."""
    out = {}
    base = []
    for fid, (label, test) in PICK_FILTERS.items():
        mults = []
        for r in rounds or []:
            if now - _f(r.get('at')) > window:
                continue
            for p in r.get('picks') or []:
                path = [px for t, px in (paths or {}).get(p['mint'], []) if t > r['at']]
                if not path or _f(p.get('entry')) <= 0:
                    continue
                m = play_exits(p.get('lane') or 'runner', p['entry'], path, cfg)
                if fid == 'score70':
                    base.append(m)
                if test(p):
                    mults.append(m)
        n = len(mults)
        out[fid] = {'label': label, 'picks': n, 'avgPct': round((sum(mults) / n - 1) * 100, 2) if n else None,
                    'winRate': round(sum(1 for m in mults if m > 1) / n * 100) if n else None, 'ready': n >= min_picks}
    allm = base
    out['_all'] = {'label': 'All picks', 'picks': len(allm), 'avgPct': round((sum(allm) / len(allm) - 1) * 100, 2) if allm else None}
    return out


def doctor(f24, f72, min_edge=3.0):
    """🩺 Engine doctor: the pick filter that is POSITIVE in both 24h and 72h (enough picks) and beats taking every pick by
    ≥ min_edge pts → apply it. Nothing positive anywhere → 'sit out' (runners stay paper, cards lean on pools / majors).
    Returns {'filter': id|None, 'sitOut': bool, 'why': str}."""
    all24 = _f((f24.get('_all') or {}).get('avgPct'))
    good = [(fid, v, f72.get(fid) or {}) for fid, v in f24.items() if fid != '_all' and v.get('ready') and (f72.get(fid) or {}).get('ready')
            and _f(v['avgPct']) > 0 and _f((f72.get(fid) or {}).get('avgPct')) > 0 and _f(v['avgPct']) - all24 >= min_edge]
    if good:
        fid, v, v72 = max(good, key=lambda g: _f(g[1]['avgPct']) + _f(g[2]['avgPct']))
        return {'filter': fid, 'sitOut': False, 'why': f"{v['label']}: {v['avgPct']:+.1f}% (24h, {v['picks']} picks) · {v72['avgPct']:+.1f}% (72h) vs every pick {all24:+.1f}%"}
    any_pos = any(_f(v.get('avgPct')) > 0 and v.get('ready') for fid, v in f24.items() if fid != '_all') or all24 > 0
    return {'filter': None, 'sitOut': not any_pos, 'why': 'nothing wins yet in 24h + 72h — sitting out runners (sitting out is a position)' if not any_pos else 'no filter beats every pick by enough yet'}


def apply_filter(passing, fid, size):
    """Prefer picks that match the doctor's filter; fall back to everything when too few match (never an empty round)."""
    test = (PICK_FILTERS.get(fid) or (None, None))[1]
    if not test:
        return passing
    hit = [r for r in passing or [] if test(r)]
    return hit + [r for r in passing or [] if r not in hit] if len(hit) >= max(1, size) else passing
