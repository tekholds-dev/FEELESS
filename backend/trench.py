"""🗑 Trench coins — fresh launches breaking out of the ~$20–30K zone with a real crowd. Pure, tested.

High risk, so the gate is the strictest on the site and FAILS CLOSED (anything unknown = out). Every check is cited:
  • fresh: ≤ maxAgeH old · market cap broke $20K and is still under the cap (the break, not the top)
  • a real crowd: ≥ 400 holders (counted on-chain) · ≥ 250 trades in the last hour · ≥ $10K 1h volume · buyers ≥ 55%
  • momentum: 5-minute AND 1-hour candles green (it is breaking now, not bleeding)
  • clean holders: holder scan done · top-10 < 25% · snipers/bundlers < 8% · ≤ 1 bundled wallet · dev < 5% and NOT selling ·
    no top-10 spike · no flagged funders
  • safe token: mint AND freeze authority revoked (nobody can print more or freeze your coins) · not a mayhem-mode coin
  • reputation: creator not flagged (bot shield / reported rug) and not rated watch / suspect / high — a fresh launch is exactly
    where rugs happen, so here a suspect creator is out even with good numbers
A card holds 1 or 2 of these at most (`arena_prime.TRENCH_COINS`). Ranking only — it never promises a result.
"""
import math

TRENCH = {'maxAgeH': 6.0, 'minMcap': 20_000.0, 'maxMcap': 150_000.0, 'minHolders': 400, 'minTxns1h': 250, 'minVol1h': 10_000.0,
          'minBuyShare': 55.0, 'maxTop10': 25.0, 'maxInsiders': 8.0, 'maxBundled': 1, 'maxDev': 5.0, 'maxTop10Jump': 5.0}
HOLD_TOP10 = 35.0
BAD_REP = ('suspect', 'high')   # 'watch' (a little evidence — most serial pump deployers) passes with a score penalty


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _holding(c):
    import runners
    return runners.holding(c)[0]


def precheck(c, cfg=None):
    """Every check that needs no extra lookup (cheap — runs on the whole feed). → list of failed checks (empty = worth a holder count)."""
    g = {**TRENCH, **(cfg or {})}
    fails = []
    if g.get('needSocials') and not (c.get('site') and c.get('x')):
        fails.append('website + X account set at launch')
    age = c.get('ageH')
    if age is None or _f(age) > g['maxAgeH']:
        fails.append(f"fresh (≤ {g['maxAgeH']:g}h old)")
    if not g['minMcap'] <= _f(c.get('mcap')) <= g['maxMcap']:
        fails.append(f"market cap broke ${g['minMcap'] / 1000:g}K (under ${g['maxMcap'] / 1000:g}K)")
    if int(_f(c.get('txns1h'))) < g['minTxns1h']:
        fails.append(f"≥ {g['minTxns1h']} trades in 1h")
    if _f(c.get('vol1h')) < g['minVol1h']:
        fails.append(f"≥ ${g['minVol1h'] / 1000:g}K 1h volume")
    if c.get('buyShare') is None or _f(c['buyShare']) < g['minBuyShare']:
        fails.append(f"buyers ≥ {g['minBuyShare']:g}%")
    if _f(c.get('chg5m')) <= 0 or _f(c.get('chg1h')) <= 0:
        fails.append('5m and 1h green (breaking out now)')
    if not c.get('scanned') or c.get('top10') is None:
        fails.append('holder scan not done yet')        # ⏳ not a verdict on the coin: the scan is still queued (shown apart in the funnel)
    elif _f(c['top10']) >= g['maxTop10'] and not (_f(c['top10']) < HOLD_TOP10 and _holding(c)):
        # 🤝 above the limit passes up to 35% ONLY while the big holders hold (`runners.holding`: top-10 not growing, dev not
        # sold, no flagged funders, buyers lead, ≥ 1h old, a site or X, clean / watch creator)
        fails.append(f"top-10 < {g['maxTop10']:g}% (to {HOLD_TOP10:g}% while holders hold)")
    if _f(c.get('insiders')) >= g['maxInsiders'] or int(_f(c.get('bundled'))) > g['maxBundled']:
        fails.append(f"snipers/bundlers < {g['maxInsiders']:g}% · ≤ {g['maxBundled']} bundled")
    if _f(c.get('dev')) >= g['maxDev'] or c.get('devSold'):
        fails.append(f"dev < {g['maxDev']:g}% and not selling")
    if _f(c.get('top10Jump')) >= g['maxTop10Jump'] or int(_f(c.get('flaggedFunders'))) > 0:
        fails.append('no top-10 spike · no flagged funders')
    if c.get('mayhem'):
        fails.append('not a mayhem-mode coin')
    if c.get('creatorFlagged') or c.get('creatorRep') in BAD_REP:
        fails.append('creator clean (not flagged · not suspect / high)')
    return fails


def gate(c, holders, auth, cfg=None):
    """Full trench gate: precheck + the on-chain crowd and token-safety checks. → (ok, failed checks)."""
    g = {**TRENCH, **(cfg or {})}
    fails = precheck(c, cfg)
    if holders is None or int(_f(holders)) < g['minHolders']:
        fails.append(f"≥ {g['minHolders']} holders")
    if not auth or auth.get('mintAuthority') or auth.get('freezeAuthority'):
        fails.append('mint + freeze authority revoked')
    return not fails, fails


def score(c, holders):
    """0–100 with cited parts: crowd (holders + trades), flow (buyers + volume), momentum, holder spread, creator."""
    parts = []
    def add(part, pts, why):
        parts.append({'part': part, 'points': round(pts, 1), 'why': why})
    add('crowd', min(25.0, int(_f(holders)) / 40 + int(_f(c.get('txns1h'))) / 60), f"{int(_f(holders))} holders · {int(_f(c.get('txns1h')))} trades/1h")
    add('flow', min(20.0, (_f(c.get('buyShare')) - 50) * 1.2 + math.log10(max(1.0, _f(c.get('vol1h')) / 1000)) * 4), f"{_f(c.get('buyShare')):.0f}% buys · ${_f(c.get('vol1h')) / 1000:.0f}K 1h")
    add('momentum', min(20.0, _f(c.get('chg5m')) * 0.8 + _f(c.get('chg1h')) * 0.2), f"5m {_f(c.get('chg5m')):+.0f}% · 1h {_f(c.get('chg1h')):+.0f}%")
    add('spread', max(0.0, 20.0 - _f(c.get('top10')) * 0.6 - _f(c.get('insiders'))), f"top-10 {_f(c.get('top10')):.0f}% · insiders {_f(c.get('insiders')):.0f}%")
    rep = c.get('creatorRep')
    add('creator', 10.0 if rep == 'clean' else 0.0 if rep == 'watch' else 4.0, 'clean creator' if rep == 'clean' else '👀 creator on watch' if rep == 'watch' else 'new creator (no record)')
    add('snipers', 5.0 if c.get('snipersOut') else 0.0, 'snipers sold out' if c.get('snipersOut') else 'snipers still in')
    return round(max(0.0, min(100.0, sum(p['points'] for p in parts))), 1), parts


def market_pair(p, now_ms, cfg=None):
    """Cheap first look at a RAW DexScreener pair (before any holder scan): fresh, in the $20K–cap band, busy, buyers ahead, green.
    The runner board only scans the 40 busiest coins — trench finalists are added to that scan so their holder checks can run."""
    g = {**TRENCH, **(cfg or {})}
    age_h = (now_ms - _f(p.get('pairCreatedAt'))) / 3.6e6 if _f(p.get('pairCreatedAt')) else None
    tx = (p.get('txns') or {}).get('h1') or {}
    b, s_ = int(_f(tx.get('buys'))), int(_f(tx.get('sells')))
    pc = p.get('priceChange') or {}
    mcap = _f(p.get('marketCap') or p.get('fdv'))
    return (age_h is not None and age_h <= g['maxAgeH'] and g['minMcap'] <= mcap <= g['maxMcap'] and b + s_ >= g['minTxns1h']
            and _f((p.get('volume') or {}).get('h1')) >= g['minVol1h'] and b / (b + s_) * 100 >= g['minBuyShare'] and _f(pc.get('m5')) > 0 and _f(pc.get('h1')) > 0)


# 🔧 Auto-widen: when NOTHING passes, the SOFT checks (crowd size, trades, volume, market-cap band, age) step looser one level at a
# time (max 3). The SAFETY checks never move: top-10, snipers/bundlers, dev, creator rep, mint + freeze revoked, buyers ≥ 55%, green.
WIDEN = [{},
         {'minHolders': 300, 'minTxns1h': 180, 'minVol1h': 7_500.0, 'maxMcap': 250_000.0},
         {'minHolders': 200, 'minTxns1h': 120, 'minVol1h': 5_000.0, 'minMcap': 15_000.0, 'maxMcap': 400_000.0, 'maxAgeH': 12.0},
         {'minHolders': 150, 'minTxns1h': 90, 'minVol1h': 4_000.0, 'minMcap': 12_000.0, 'maxMcap': 600_000.0, 'maxAgeH': 24.0}]


def widen(level):
    """The trench config at widen `level` (0 = strict … 3 = loosest soft checks)."""
    return {**TRENCH, **WIDEN[max(0, min(len(WIDEN) - 1, int(level or 0)))]}


def best_level(finalists, gate_at):
    """The strictest level at which at least one finalist passes. gate_at(row, cfg) → (ok, fails). → (level, results) or (None, results@0)."""
    for lvl in range(len(WIDEN)):
        res = [(r, *gate_at(r, widen(lvl))) for r in finalists]
        if any(ok for _, ok, _ in res):
            return lvl, res
    return None, [(r, *gate_at(r, widen(0))) for r in finalists]


def funnel(cands, cfg=None):
    """Why nothing passed: how many candidates failed EACH cheap check (a coin counts once per check it fails). → [{why, n}] most first."""
    out = {}
    for c in cands or []:
        for f in precheck(c, cfg):
            out[f] = out.get(f, 0) + 1
    return sorted(({'why': k, 'n': n} for k, n in out.items()), key=lambda x: -x['n'])


# 🎛 The owner's own trench settings. ONLY the soft checks can be set, each from a fixed list (nothing free-typed); the safety checks
# (top-10, snipers/bundlers, dev, creator, mint + freeze revoked, buyers ≥ 55%, green candles) are not options — they never move.
OWN_OPTIONS = {'minHolders': [100, 150, 200, 300, 400, 600, 1000], 'minTxns1h': [60, 90, 120, 180, 250, 400], 'minVol1h': [3_000, 5_000, 7_500, 10_000, 20_000, 50_000],
               'minMcap': [10_000, 15_000, 20_000, 30_000, 50_000], 'maxMcap': [100_000, 150_000, 250_000, 400_000, 600_000, 1_000_000], 'maxAgeH': [1, 3, 6, 12, 24, 48]}


# 🧪 TRENCH METAS: named styles of trench hunting. Each one sets ONLY the soft checks (crowd, trades, volume, cap band, age), every
# value from OWN_OPTIONS; the safety checks are the same in every meta. HQ picks one for the cards; anyone can VIEW what each finds.
METAS = {
    # 🎯 LAUNCH: in as soon as a coin drops — but only one that came out with a WEBSITE and an X account already set (a team that
    # prepared), its first real crowd in, and every safety check passed. `needSocials` is part of this meta's gate, never widened.
    'launch':   ('🎯 Launch', 'In as it drops: under an hour old, website + X set at launch, first real crowd — highest risk, smallest stake',
                 {'maxAgeH': 1, 'minMcap': 10_000, 'maxMcap': 250_000, 'minHolders': 150, 'minTxns1h': 120, 'minVol1h': 10_000, 'needSocials': 1}),
    'sprout':   ('🌱 Sprout', 'Minutes old, tiny cap, first real crowd — earliest and riskiest',
                 {'maxAgeH': 1, 'minMcap': 10_000, 'maxMcap': 100_000, 'minHolders': 150, 'minTxns1h': 120, 'minVol1h': 5_000}),
    'breakout': ('🚀 Breakout', 'Broke $20K with a real crowd in its first 6 hours — the classic trench',
                 {'maxAgeH': 6, 'minMcap': 20_000, 'maxMcap': 150_000, 'minHolders': 400, 'minTxns1h': 250, 'minVol1h': 10_000}),
    'flood':    ('🌊 Flood', 'Volume first: $50K+ an hour and 400+ trades, any cap up to $600K',
                 {'maxAgeH': 12, 'minMcap': 20_000, 'maxMcap': 600_000, 'minHolders': 300, 'minTxns1h': 400, 'minVol1h': 50_000}),
    'crowd':    ('🏟 Crowd', '1,000+ holders — the crowd is already in, cap $50K to $1M',
                 {'maxAgeH': 24, 'minMcap': 50_000, 'maxMcap': 1_000_000, 'minHolders': 1000, 'minTxns1h': 180, 'minVol1h': 20_000}),
    'survivor': ('🕰 Survivor', 'Still alive and trading after a day or two — past the rug window',
                 {'maxAgeH': 48, 'minMcap': 30_000, 'maxMcap': 1_000_000, 'minHolders': 600, 'minTxns1h': 180, 'minVol1h': 10_000}),
}


def meta_gate(key):
    """The full gate for a named meta (its soft checks on top of the fixed safety checks), or None."""
    m = METAS.get(key)
    return {**TRENCH, **{k: (int(v) if k in ('minHolders', 'minTxns1h') else float(v)) for k, v in m[2].items()}} if m else None


def loosest(extra=None):
    """The widest soft checks of every meta, every widen level and `extra` (the owner's own) — used ONLY to choose which coins get
    the costly holder count, so every meta has finalists to judge. Never a pass rule."""
    gs = [meta_gate(k) for k in METAS] + [widen(i) for i in range(len(WIDEN))] + ([extra] if extra else [])
    out = dict(TRENCH)
    for k in ('minMcap', 'minHolders', 'minTxns1h', 'minVol1h'):
        out[k] = min(g[k] for g in gs)
    for k in ('maxMcap', 'maxAgeH'):
        out[k] = max(g[k] for g in gs)
    return out


def meta_board(finalists, gate_at):
    """What each meta finds RIGHT NOW among the scanned finalists. gate_at(row, cfg) → (ok, fails). → [{key, label, blurb, pass, coins}]"""
    out = []
    for key, (label, blurb, _c) in METAS.items():
        g = meta_gate(key)
        ok = [r for r in finalists if gate_at(r, g)[0]]
        out.append({'key': key, 'label': label, 'blurb': blurb, 'pass': len(ok), 'cfg': {k: g[k] for k in OWN_OPTIONS}})
    return out


def closest(cands, cfg=None, n=5):
    """👀 The list is never empty: the busiest fresh coins that pass EVERY safety check on the cheap pass (scan done, top-10, snipers,
    dev, creator, no spike …) and miss only soft ones (not green this minute, crowd, volume, cap band, age). → [(coin, soft fails)]
    busiest first. For the owner to pick by hand — never seated by the engine."""
    out = []
    for c in cands or []:
        fails = precheck(c, cfg)
        if c.get('mint') and c.get('pairAddress') and (not fails or soft_only(fails)):
            out.append((c, fails or ['holder count pending']))
    return sorted(out, key=lambda x: -_f(x[0].get('vol1h')))[:n]


def band_miss(c, cfg=None):
    """🎛 Is this coin INSIDE the filter's age + market-cap band? → [] or the exact misses in numbers ("6.3h old — filter ≤ 1h").
    Age and cap band are what the owner's dropdowns promise: a coin outside them is never shown as a near-miss."""
    g = {**TRENCH, **(cfg or {})}
    k = lambda v: f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v / 1000:.0f}K"
    out, age, mc = [], c.get('ageH'), _f(c.get('mcap'))
    if age is None:
        out.append('age unknown')
    elif _f(age) > g['maxAgeH']:
        out.append(f"{_f(age):.1f}h old — filter ≤ {g['maxAgeH']:g}h")
    if mc < g['minMcap']:
        out.append(f"cap {k(mc)} — filter from {k(g['minMcap'])}")
    elif mc > g['maxMcap']:
        out.append(f"cap {k(mc)} — filter up to {k(g['maxMcap'])}")
    return out


PROOF_SEC, PROOF_KEEP, PROOF_MIN = 3600.0, 60, 5


def meta_track(state, passing, price_of, now, keys=None):
    """📈 Paper proof per meta. `passing` = {meta: [(mint, price)]} right now; a coin a meta passes is noted ONCE at that price and
    settled an hour later at `price_of(mint)` (no price then = −100%: a coin that vanished is a loss, never dropped from the count).
    A coin is not noted again while open or for 6h after. → new state {meta: {open: {mint: {px, at}}, done: [{pct, at, mint}]}}"""
    out = {}
    for key in (keys or METAS):   # `keys` = any other set of named reads judged the same way (entry setups)
        s = (state or {}).get(key) or {}
        opened, done = dict(s.get('open') or {}), list(s.get('done') or [])
        for mint, o in list(opened.items()):
            if now - _f(o.get('at')) >= PROOF_SEC:
                px = _f(price_of(mint))
                done.append({'mint': mint, 'at': now, 'pct': round((px / _f(o['px']) - 1) * 100, 2) if px > 0 and _f(o.get('px')) > 0 else -100.0})
                opened.pop(mint)
        recent = {d['mint'] for d in done if now - _f(d.get('at')) < 6 * 3600}
        for mint, px in (passing or {}).get(key) or []:
            if mint and _f(px) > 0 and mint not in opened and mint not in recent:
                opened[mint] = {'px': _f(px), 'at': now}
        out[key] = {'open': opened, 'done': done[-PROOF_KEEP:]}
    return out


def meta_proof(state, keys=None):
    """{meta: {n, medPct, wonPct, proven}} from settled coins. Median, not average (one 10× must not carry a meta); `proven` needs
    ≥ 5 settled, median > 0 and half or more up. A record of the last hour-holds — never a promise."""
    out = {}
    for key in (keys or METAS):
        ps = sorted(_f(d.get('pct')) for d in ((state or {}).get(key) or {}).get('done') or [])
        n = len(ps)
        med = (ps[n // 2] if n % 2 else (ps[n // 2 - 1] + ps[n // 2]) / 2) if n else None
        won = round(sum(1 for x in ps if x > 0) / n * 100) if n else None
        out[key] = {'n': n, 'medPct': None if med is None else round(med, 1), 'wonPct': won, 'open': len(((state or {}).get(key) or {}).get('open') or {}),
                    'proven': bool(n >= PROOF_MIN and med > 0 and won >= 50)}
    return out


def clean_own(c):
    """{'mode': 'auto' | 'own', + one allowed value per soft check}. Anything else snaps to the nearest allowed value / the default."""
    c = c if isinstance(c, dict) else {}
    out = {'mode': c.get('mode') if c.get('mode') in ('own', 'meta') else 'auto', 'meta': c.get('meta') if c.get('meta') in METAS else 'breakout'}
    for k, opts in OWN_OPTIONS.items():
        v = _f(c.get(k)) if c.get(k) is not None else _f(TRENCH[k])
        out[k] = min(opts, key=lambda o: abs(o - v))
    if out['minMcap'] >= out['maxMcap']:
        out['maxMcap'] = next((o for o in OWN_OPTIONS['maxMcap'] if o > out['minMcap']), OWN_OPTIONS['maxMcap'][-1])
    return out


def own_gate(own):
    """The full gate config for the owner's settings: their soft checks on top of the fixed safety checks."""
    o = clean_own(own)
    if o['mode'] == 'meta':
        return meta_gate(o['meta'])
    return {**TRENCH, **{k: (float(o[k]) if k not in ('minHolders', 'minTxns1h') else int(o[k])) for k in OWN_OPTIONS}}


SAFETY_FAILS = ('top-10', 'holder scan', 'snipers', 'dev <', 'spike', 'flagged funders', 'mayhem', 'creator', 'mint + freeze')


def soft_only(fails):
    """True when a finalist missed ONLY soft checks (crowd size, trades, volume, market-cap band, age, green candles, buyers) — every
    safety check passed. Such a coin is shown in the 🗑 list as a near-miss the owner may pick (never auto-seated as a trench coin)."""
    return bool(fails) and not any(any(w in str(f) for w in SAFETY_FAILS) for f in fails)


# 🚪 OPEN GATES: the trench list with NO filter — every launch coin the feed sees (Pump's biggest + most recently traded, the
# launch boards, Jupiter's live trending), ranked as FRONT-RUNNERS by what is happening right now. Nothing is hidden; each row says
# what it has NOT passed (`fails`) or that it was never scanned. View + the owner's hand pick only: never auto-seated.
OPEN_MAX = 60


def open_row(pair, now_ms):
    """A raw feed pair → the flat row the open list shows (None when it has no mint / price)."""
    base = pair.get('baseToken') or {}
    px = _f(pair.get('priceUsd'))
    if not base.get('address') or px <= 0:
        return None
    tx = (pair.get('txns') or {}).get('h1') or {}
    buys, sells = _f(tx.get('buys')), _f(tx.get('sells'))
    pc, vol = pair.get('priceChange') or {}, pair.get('volume') or {}
    made = _f(pair.get('pairCreatedAt'))
    return {'mint': base['address'], 'symbol': base.get('symbol') or '', 'pairAddress': pair.get('pairAddress'), 'price': px,
            'mcap': _f(pair.get('marketCap') or pair.get('fdv')), 'liq': _f((pair.get('liquidity') or {}).get('usd')),
            'ageH': round((now_ms - made) / 3.6e6, 2) if made > 0 else None, 'vol1h': _f(vol.get('h1')), 'vol5m': _f(vol.get('m5')),
            'chg5m': None if pc.get('m5') is None else _f(pc.get('m5')), 'chg1h': None if pc.get('h1') is None else _f(pc.get('h1')),
            'txns1h': int(buys + sells), 'buyShare': round(buys / (buys + sells) * 100, 1) if buys + sells else None,
            'curve': not pair.get('graduated') and str(pair.get('marketStage') or '') not in ('graduated', 'amm'), 'logo': (pair.get('info') or {}).get('imageUrl') or ''}


def front_score(r):
    """How much of a front-runner a coin is RIGHT NOW (0–100): 1h volume (log), trades, the 5-min volume pace, buyers, a green hour.
    Activity only — it says nothing about safety."""
    import math
    v = min(40.0, max(0.0, (math.log10(max(_f(r.get('vol1h')), 1.0)) - 3.0) * 16.0))            # $1K → 0 · $300K+ → 40
    t = min(15.0, _f(r.get('txns1h')) / 40.0)
    pace = min(15.0, (_f(r.get('vol5m')) * 12.0 / _f(r.get('vol1h')) if _f(r.get('vol1h')) > 0 else 0.0) * 7.5)   # 5m pace vs the hour
    b = min(15.0, max(0.0, (_f(r.get('buyShare')) - 45.0) * 0.75)) if r.get('buyShare') is not None else 0.0
    g = min(15.0, max(0.0, _f(r.get('chg1h')) / 4.0)) if r.get('chg1h') is not None else 0.0
    return round(v + t + pace + b + g, 1)


def open_board(pairs, scanned=None, now_ms=0, n=OPEN_MAX):
    """Every launch coin in the feed, best front-runner first. `scanned` = {mint: (safe: bool, fails: [..])} from the runner board;
    a coin it never scanned says so. Rows are `soft` (the engine never seats one) and `open`."""
    out, seen = [], set()
    for p in pairs or []:
        r = open_row(p, now_ms)
        if not r or r['mint'] in seen:
            continue
        seen.add(r['mint'])
        sc = (scanned or {}).get(r['mint'])
        fails = ['not scanned yet — holders unknown'] if sc is None else list(sc[1] or [])
        out.append({**r, 'front': front_score(r), 'safe': None if sc is None else bool(sc[0]), 'fails': fails, 'soft': True, 'open': True})
    out.sort(key=lambda r: -r['front'])
    for i, r in enumerate(out):
        r['rank'] = i + 1
    return out[:n]


# 📣 CALLOUTS: every few minutes the open list calls out its leaders — 🔥 volume leader · 🚀 mover · 🆕 fresh launch. A coin is
# noted ONCE when it first makes a callout, at that price, and settled an hour later (`meta_track` / `meta_proof`: no price = −100%).
CALLOUT_SEC = 210          # 3.5 minutes
CALLOUTS = {'leader': ('🔥', 'Volume leader', 'top 5 by 1h volume'),
            'mover': ('🚀', 'Mover', 'top 5 by 5-min move with ≥ $5K traded in those 5 min'),
            'fresh': ('🆕', 'Fresh launch', '≤ 1h old, top 5 by 1h volume (≥ $10K)')}


def callouts(board, n=5):
    """{kind: [row …]} — who the open list is calling out right now."""
    rows = list(board or [])
    return {'leader': sorted(rows, key=lambda r: -_f(r.get('vol1h')))[:n],
            'mover': sorted((r for r in rows if r.get('chg5m') is not None and _f(r.get('chg5m')) > 0 and _f(r.get('vol5m')) >= 5000), key=lambda r: -_f(r.get('chg5m')))[:n],
            'fresh': sorted((r for r in rows if r.get('ageH') is not None and _f(r.get('ageH')) <= 1 and _f(r.get('vol1h')) >= 10000), key=lambda r: -_f(r.get('vol1h')))[:n]}


def callout_feed(state, names, price_now, now, n=24):
    """The callouts as a feed, newest first: open ones with their move since the call (live), settled ones with their 1h result."""
    out = []
    for kind in CALLOUTS:
        s = (state or {}).get(kind) or {}
        for mint, o in (s.get('open') or {}).items():
            px = _f((price_now or {}).get(mint))
            out.append({'kind': kind, 'mint': mint, 'at': _f(o.get('at')), 'px': _f(o.get('px')), 'live': True,
                        'pct': round((px / _f(o['px']) - 1) * 100, 1) if px > 0 and _f(o.get('px')) > 0 else None})
        for d in (s.get('done') or [])[-n:]:
            out.append({'kind': kind, 'mint': d.get('mint'), 'at': _f(d.get('at')) - PROOF_SEC, 'live': False, 'pct': d.get('pct')})
    for x in out:
        nm = (names or {}).get(x['mint']) or {}
        x.update(symbol=nm.get('symbol') or '', pairAddress=nm.get('pairAddress'), mins=max(0, int((now - x['at']) / 60)))
    return sorted(out, key=lambda x: -x['at'])[:n]
