"""🩸 DRAIN VITALS (owner, 2026-10-14: "buy/sell bar should be a vital to getting out if holders are gone or big holders are about to drain
the chart … we need to predict the future with 80% accuracy"). Pure + tested (`tests/test_drain.py`).

From readings the desk ALREADY has (no new fetch):
  🐋 EXIT LIQUIDITY  = the top-10 holders' $ bag ÷ the pool (top10 % × cap ÷ liquidity). 3× = the top ten can sell three pools' worth:
                       if they go, the chart goes. It is how much a rug can hurt, read BEFORE it happens.
  👥 HOLDERS LEAVING = Tally's holder change over its window (`nums.holdD`, %).
  💧 POOL DRAINING   = Tally's pool change (`nums.liqD`, %).
  🌊 TAPE            = the buy / sell vital of the last 90s (flow.vital: SELLERS / PEAK …) — the buy/sell bar, as a vital.
  🤖 BOT CROWD       = same-size buys on the tape (flow.trench_meta sameSizePct).
→ ONE drain read: score 0–100 · CLEAR / WATCH / DRAIN · the parts that made it. Reaper's R4d sells an agent seat on DRAIN only when at
least one MOVING part (holders leaving · pool draining · sellers on the tape · a big wallet dumping) agrees — a heavy bag that is not
moving is a WATCH, never an exit by itself.

🔮 ODDS (`odds_table` / `odds`): the measured share of coins with this coin's features that fell 50%+ (or vanished) within the hour, from
the trench brain's judged coins — the bucket that says the MOST about this coin (furthest from the base rate), with its n. A record, never
a promise: 2026-10-14 (2,659 coins) the strongest buckets read 73–79% (under 15 min old · RUG BAIT · +15% in 5 min · +200% in an hour)
and the calmest 1–6% (12h+ · $1M+ · WASH TRADED / DRYING UP · flat 5 min). Unknown readings are left out — never zero."""
XL_WATCH, XL_DRAIN = 1.0, 3.0          # exit liquidity: top-10 bag ≥ 1 pool = heavy · ≥ 3 pools = a drain waiting to happen
HOLD_LEAVE, HOLD_RUN = -2.0, -5.0      # holders % over Tally's window
POOL_LEAK, POOL_DRAIN = -10.0, -25.0   # pool % over Tally's window
BOT_SAME = 50.0                        # same-size buys ≥ this % of the tape = a bot loop
WATCH_AT, DRAIN_AT = 30, 60
ODDS_MIN_N = 40
TABLE = {}                             # the live odds table (set by the service from the trench brain, rebuilt every 10 min)
RUG_LOW = -50.0                        # "rugged" in the brain's record = fell 50%+ (or vanished) within the hour


def _f(v, d=None):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def exit_liq(top10, mcap, liq):
    """The top-10 holders' $ bag ÷ the pool, or None when any reading is missing."""
    t, m, l = _f(top10), _f(mcap), _f(liq)
    if t is None or m is None or l is None or t <= 0 or m <= 0 or l <= 0:
        return None
    return round(t / 100 * m / l, 2)


def read(vitals=None, nums=None, flow=None, meta=None, dump=None):
    """→ {score, state, parts [(label, pts, moving)], xl, hd, lq, bot} — the drain read of one coin. `flow` = flow.vital,
    `meta` = flow.trench_meta, `dump` = a rug-radar reason (a top holder / creator / bundle wallet selling)."""
    v, n = vitals or {}, nums or {}
    xl = exit_liq(v.get('top10'), v.get('mcap'), n.get('liq') or v.get('liq'))
    hd, lq = _f(n.get('holdD')), _f(n.get('liqD'))
    bot = _f((meta or {}).get('sameSizePct'))
    parts = []
    if xl is not None and xl >= XL_WATCH:
        parts.append((f"top-10 hold {xl:g}× the pool", 35 if xl >= XL_DRAIN else 20 if xl >= 2 else 10, False))
    if hd is not None and hd <= HOLD_LEAVE:
        parts.append((f"holders {hd:+.0f}%", 25 if hd <= HOLD_RUN else 12, True))
    if lq is not None and lq <= POOL_LEAK:
        parts.append((f"pool {lq:+.0f}%", 35 if lq <= POOL_DRAIN else 18, True))
    fs = (flow or {}).get('state')
    if fs == 'SELLERS':
        parts.append(('sellers lead the tape', 20, True))
    elif fs == 'PEAK':
        parts.append(('buying climax on the tape', 8, False))
    if bot is not None and bot >= BOT_SAME:
        parts.append((f"{bot:.0f}% same-size buys (bots)", 10, False))
    if dump:
        parts.append((str(dump)[:70], 50, True))
    score = min(100, sum(p[1] for p in parts))
    state = 'DRAIN' if score >= DRAIN_AT else 'WATCH' if score >= WATCH_AT else 'CLEAR'
    return {'score': score, 'state': state, 'parts': parts, 'xl': xl, 'hd': hd, 'lq': lq, 'bot': bot}


def exit_why(d):
    """Reaper R4d: the reason to sell a held seat, or None. DRAIN + at least one MOVING part, and either a heavy bag (≥ 1 pool) behind
    it or two moving parts — a heavy bag that is not moving never sells by itself."""
    d = d or {}
    moving = [p for p in d.get('parts') or [] if p[2]]
    if d.get('state') != 'DRAIN' or not moving:
        return None
    if not ((_f(d.get('xl')) or 0) >= XL_WATCH or len(moving) >= 2):
        return None
    return 'drain: ' + ' · '.join(p[0] for p in sorted(d['parts'], key=lambda p: -p[1])[:3])


def odds_table(done, since=0):
    """{feature: [n, rug %, typical end %]} from the trench brain's judged coins (`done` rows: f, low, end, gone)."""
    import statistics
    g = {}
    for x in done or []:
        if _f(x.get('at'), 0) < since or not x.get('f'):
            continue
        rug = bool(x.get('gone')) or (_f(x.get('low')) is not None and _f(x['low']) <= RUG_LOW)
        for t in x['f']:
            g.setdefault(t, []).append((rug, _f(x.get('end'), 0)))
    out = {}
    for t, xs in g.items():
        if len(xs) >= ODDS_MIN_N:
            out[t] = [len(xs), round(sum(1 for r, _e in xs if r) / len(xs) * 100), round(statistics.median(e for _r, e in xs), 1)]
    n_all = len([x for x in done or [] if x.get('f') and _f(x.get('at'), 0) >= since])
    rugs = sum(1 for x in done or [] if x.get('f') and _f(x.get('at'), 0) >= since and (x.get('gone') or (_f(x.get('low')) is not None and _f(x['low']) <= RUG_LOW)))
    out['_base'] = [n_all, round(rugs / n_all * 100) if n_all else None, None]
    return out


WORDS = {'age': 'old', 'cap': 'cap', 'read': 'read', '5m': 'in 5 min', '1h': 'in 1h', 'live': 'traded', 'pace': 'pace', 'stage': '', 'buy': '% buyers',
         'bund': 'bundled', 'snipe': 'snipers', 'ins': '% insiders', 'dev': 'dev', 'top10': '% top-10', 'safe': 'scan safe', 'soc': 'socials', 'xl': '× pool top-10'}


def odds(features, table):
    """The bucket that says the most about THIS coin → {rug, n, end, why, base} or None (no bucket with enough coins)."""
    base = ((table or {}).get('_base') or [0, None])[1]
    best = None
    for t in features or []:
        r = (table or {}).get(t)
        if not r or base is None:
            continue
        if best is None or abs(r[1] - base) > abs(best[1][1] - base):
            best = (t, r)
    if not best:
        return None
    k, _, v = best[0].partition(':')
    return {'rug': best[1][1], 'n': best[1][0], 'end': best[1][2], 'base': base, 'feature': best[0],
            'why': f"{best[1][1]}% of {best[1][0]:,} coins with {v} {WORDS.get(k, k)} fell 50%+ within the hour (all coins: {base}%)".replace('  ', ' ')}


def set_table(t):
    TABLE.clear()
    TABLE.update(t or {})
