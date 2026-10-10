"""📈 CHART INTELLIGENCE for the office — pure, deterministic, tested (`tests/test_chart_intel.py`).

ONE shared snapshot per coin per pass (`snapshot`): measured price-action features from 1-minute candles — the candles service's
OHLCV when the service fetched them for that coin, else Tally's own one-reading-a-minute tape (closes only: wicks are then NOT
measured and say so). Every desk reads the SAME snapshot:

  classify   → the market-structure state (named constants + thresholds below — code decides, never prose)
  entry_call → Trigger: is THIS MOMENT a place to take risk (ENTER NOW · WAIT FOR PULLBACK / BREAKOUT / CONFIRMATION · SKIP)
  objections → Devil: evidence-backed attacks on the chart thesis
  risk       → Warden: a size multiplier ≤ 1 from chart risk
  stop_for   → the NORMAL stop for this entry (volatility · support · liquidity · age · execution), inside hard bounds
  thesis     → the entry thesis saved with a real position;  review → Reaper's checkpoint ruling against that thesis

Buy share alone, a green-candle count alone or one big candle never decides a state: structure does (swings, slope + its consistency,
efficiency of the path, where price sits in its range, breakouts that held or failed).
"""
import math

LOOK = 30          # 1-minute candles a snapshot reads
MIN_BARS = 6       # fewer = UNKNOWN (never guessed)
WINDOW_MIN = 5     # the trench stage: one evaluation window
MIN_WINDOWS = 3    # a thesis gets at least 15 minutes before a "no read left" exit (the card's record: exits inside 15 min lose) — an INVALIDATED thesis leaves at once
MAX_WINDOWS = 12   # … and at most an hour of extensions
STOP_FLOOR = 8.0   # the tightest a normal stop may be
CATASTROPHIC_STOP = 45.0   # 🧱 the hard ceiling: a position down this much is closed whatever any learned / promoted setting says. Not a tunable.

STATES = ('STRONG UPTREND', 'UPTREND', 'PULLBACK IN UPTREND', 'BREAKOUT ATTEMPT', 'CONFIRMED BREAKOUT', 'ACCUMULATION', 'COMPRESSION', 'RANGE', 'CHOP',
          'DISTRIBUTION', 'DOWNTREND', 'LIQUIDITY FAILURE', 'PARABOLIC', 'FAILED BREAKOUT', 'UNKNOWN')
GOOD = ('STRONG UPTREND', 'UPTREND', 'PULLBACK IN UPTREND', 'CONFIRMED BREAKOUT')          # the thesis of a long still stands
BAD = ('DOWNTREND', 'LIQUIDITY FAILURE', 'FAILED BREAKOUT', 'DISTRIBUTION', 'CHOP')        # it does not
BULL = GOOD + ('BREAKOUT ATTEMPT', 'ACCUMULATION')
ENTRY_CALLS = ('ENTER NOW', 'WAIT FOR PULLBACK', 'WAIT FOR BREAKOUT', 'WAIT FOR CONFIRMATION', 'SKIP')

# thresholds (each is one measured line)
PARABOLIC_5M, PARABOLIC_EXT = 25.0, 85.0
TREND_STRONG, TREND_MIN, CHOP_MAX_STRONG, CHOP_MIN = 62.0, 38.0, 45.0, 62.0
EXT_WAIT, VOL_WILD, WICK_HEAVY = 70.0, 6.0, 0.55
LIQ_FAIL_DROP, LIQ_FAIL_MIN = -25.0, 10_000.0


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def from_tape(series):
    """Tally's own readings (one a pass, ~1 min apart: {t, px}) as close-only 1-minute candles. → (rows [t, o, h, l, c, v], ohlc False)"""
    out, prev = [], None
    for p in series or []:
        px = _f(p.get('px'))
        if px <= 0:
            continue
        o = prev if prev else px
        out.append([_f(p.get('t')), o, max(o, px), min(o, px), px, None])
        prev = px
    return out


def _pivots(vals, hi=True):
    """3-bar fractal pivots of a series → [(index, value)]"""
    out = []
    for i in range(1, len(vals) - 1):
        if (vals[i] > vals[i - 1] and vals[i] >= vals[i + 1]) if hi else (vals[i] < vals[i - 1] and vals[i] <= vals[i + 1]):
            out.append((i, vals[i]))
    return out


def _ret(c, k):
    return round((c[-1] / c[-1 - k] - 1) * 100, 2) if len(c) > k and c[-1 - k] > 0 else None


def snapshot(rows, now=0.0, ohlc=True, buy=None, liq=None, liq_d=None, flow=None, seat_usd=None):
    """The measured features of one coin from its last LOOK 1-minute candles (`rows` = [t, o, h, l, c, v]). `ohlc` False = built from
    closes only (wick features are None, not zero). `buy` = buy share %, `liq` / `liq_d` = pool $ and its % change on our tape,
    `flow` = the 90s tape window {buyUsd, sellUsd, n} when the service already holds one. → features dict (None = not measured)."""
    rs = [r for r in (rows or []) if r and _f(r[4]) > 0][-LOOK:]
    n = len(rs)
    f = {'n': n, 'ohlc': bool(ohlc), 'at': now, 'buy': buy, 'liq': liq, 'liqD': liq_d}
    if n < MIN_BARS:   # too short to measure structure: the price only, every feature unmeasured
        return {**f, 'px': _f(rs[-1][4]) if rs else None}
    o, h, l, c = [_f(r[1]) for r in rs], [_f(r[2]) for r in rs], [_f(r[3]) for r in rs], [_f(r[4]) for r in rs]
    v = [r[5] for r in rs]
    px = c[-1]
    rets = [(c[i] / c[i - 1] - 1) * 100 for i in range(1, n) if c[i - 1] > 0]
    mean = sum(rets) / len(rets)
    vol = math.sqrt(sum((x - mean) ** 2 for x in rets) / len(rets))
    hi, lo = max(h), min(l)
    rng = [(h[i] - l[i]) / l[i] * 100 for i in range(n) if l[i] > 0]
    atr = sum(rng) / len(rng) if ohlc else sum(abs(x) for x in rets) / len(rets)
    # slope of log price over the window (% a minute) and how well a straight line fits it
    ys = [math.log(x) for x in c]
    xm, ym = (n - 1) / 2, sum(ys) / n
    sxx = sum((i - xm) ** 2 for i in range(n))
    sxy = sum((i - xm) * (ys[i] - ym) for i in range(n))
    syy = sum((y - ym) ** 2 for y in ys)
    slope = sxy / sxx if sxx else 0.0
    r2 = (sxy * sxy / (sxx * syy)) if sxx and syy > 1e-18 else 0.0
    path = sum(abs(x) for x in rets)
    er = abs((c[-1] / c[0] - 1) * 100) / path if path > 1e-9 else 0.0          # efficiency: net move ÷ distance travelled (1 = a straight line)
    flips = sum(1 for i in range(1, len(rets)) if rets[i] * rets[i - 1] < 0) / max(1, len(rets) - 1)
    ph, pl = _pivots(c, True), _pivots(c, False)   # swings on CLOSES (a wick is not a swing; close-only tapes read the same way)
    hh = sum(1 for a, b in zip(ph, ph[1:]) if b[1] > a[1]); lh = sum(1 for a, b in zip(ph, ph[1:]) if b[1] < a[1])
    hl = sum(1 for a, b in zip(pl, pl[1:]) if b[1] > a[1]); ll = sum(1 for a, b in zip(pl, pl[1:]) if b[1] < a[1])
    col = ['G' if c[i] > o[i] else 'R' if c[i] < o[i] else '-' for i in range(n)]
    run = lambda ch: next((k for k in range(n) if col[-1 - k] != ch), n)
    # the last swing: the high before now, the low after it
    ih = max(range(n), key=lambda i: h[i])
    low_after = min(l[ih:]) if ih < n - 1 else l[-1]
    leg_lo = min(l[:ih + 1]) if ih else l[0]
    pull = (hi - low_after) / hi * 100 if hi > 0 else 0.0
    leg = (hi - leg_lo) / leg_lo * 100 if leg_lo > 0 else 0.0
    recov = (px - low_after) / (hi - low_after) if hi - low_after > 1e-12 else 1.0
    up_leg = c[:ih + 1]
    leg_path = sum(abs(up_leg[i] / up_leg[i - 1] - 1) for i in range(1, len(up_leg)) if up_leg[i - 1] > 0)
    leg_eff = (up_leg[-1] / up_leg[0] - 1) / leg_path if len(up_leg) >= 4 and leg_path > 1e-12 else 0.0     # how straight the climb INTO the high was
    # resistance / support = the extremes of the window BEFORE the last 5 candles
    k = min(5, n - 2)
    res, sup = max(h[:-k]), min(l[:-k])
    if pl and pl[-1][1] < c[-1] and slope > 0:
        sup = max(sup, pl[-1][1])   # in a rising chart the support a long stands on is the LAST higher low, not where the trend began
    above = [c[i] > res for i in range(n - k, n)]
    att = sum(1 for i in range(n - k, n) if h[i] > res)
    band = max(atr, 0.2) / 100
    sup_t = sum(1 for i in range(n - k, n) if l[i] <= sup * (1 + band) and c[i] >= sup)
    res_t = sum(1 for i in range(n - k, n) if h[i] >= res * (1 - band) and c[i] <= res)
    r_now = (max(h[-k:]) - min(l[-k:])) / min(l[-k:]) * 100
    r_was = (max(h[:-k]) - min(l[:-k])) / min(l[:-k]) * 100 if min(l[:-k]) > 0 else 0.0
    pre = c[:-k]
    pre_path = sum(abs(pre[i] / pre[i - 1] - 1) for i in range(1, len(pre)) if pre[i - 1] > 0)
    base = len(pre) >= 4 and (abs(pre[-1] / pre[0] - 1) / pre_path if pre_path > 1e-12 else 0.0) < 0.35      # the window BEFORE the last 5 candles went nowhere: a base a breakout can leave
    sma = sum(c[-15:]) / len(c[-15:])
    ext_pct = (px / sma - 1) * 100
    resid = (ys[-1] - (ym + slope * (n - 1 - xm))) * 100                                                      # how far price sits above (+) / below (−) its own trend line, %
    r3 = (c[-1] / c[-4] - 1) * 100 if n >= 4 else None
    r3p = (c[-4] / c[-7] - 1) * 100 if n >= 7 else None
    r5 = _ret(c, 5)
    z = (r5 if r5 is not None else (c[-1] / c[0] - 1) * 100) / (vol * math.sqrt(5) + 0.05)
    vv = [_f(x) for x in v if x is not None]
    f.update(
        px=px, open=o[0], high=hi, low=lo, close=px,
        r1=_ret(c, 1), r5=r5, r10=_ret(c, 10), r15=_ret(c, 15), r30=_ret(c, 30) if n > 30 else _ret(c, n - 1) if n >= 25 else None, r60=None,
        hh=hh, hl=hl, lh=lh, ll=ll, lastHigh='lower' if len(ph) >= 2 and ph[-1][1] < ph[-2][1] else 'higher' if len(ph) >= 2 else None,
        lastLow='lower' if len(pl) >= 2 and pl[-1][1] < pl[-2][1] else 'higher' if len(pl) >= 2 else None,
        slope=round(slope * 100, 3), fit=round(r2, 2), dir='up' if slope > 0 else 'down',
        distHigh=round((hi - px) / hi * 100, 2), distLow=round((px - lo) / lo * 100, 2) if lo > 0 else None, rangePct=round((hi - lo) / lo * 100, 2) if lo > 0 else None,
        pos=round((px - lo) / (hi - lo), 2) if hi > lo else 0.5, vol=round(vol, 2), atr=round(atr, 2),
        body=round(sum(abs(c[i] - o[i]) / o[i] * 100 for i in range(n) if o[i] > 0) / n, 2),
        wick=round(sum(((h[i] - l[i]) - abs(c[i] - o[i])) / o[i] * 100 for i in range(n) if o[i] > 0) / n, 2) if ohlc else None,
        upWick=round(sum((h[i] - max(o[i], c[i])) / (h[i] - l[i]) for i in range(n - 3, n) if h[i] > l[i]) / 3, 2) if ohlc and n >= 3 else None,
        loWick=round(sum((min(o[i], c[i]) - l[i]) / (h[i] - l[i]) for i in range(n - 3, n) if h[i] > l[i]) / 3, 2) if ohlc and n >= 3 else None,
        seq=''.join(col[-8:]), up=run('G'), down=run('R'),
        pullback=round(pull, 2), leg=round(leg, 2), legEff=round(_clamp(leg_eff, -1, 1) * 100), recovery=round(_clamp(recov, 0.0, 1.0), 2), sinceHigh=n - 1 - ih,
        resistance=res, support=sup, base=bool(base), breakTries=att, breakHeld=sum(above), breakFailed=bool(att and not above[-1] and px < res * (1 - band / 2)),
        supTests=sup_t, resTests=res_t, squeeze=round(r_now / r_was, 2) if r_was > 0 else None,
        trend=round(_clamp(100 * er * (0.4 + 0.6 * r2), 0, 100)), chop=round(_clamp(100 * (0.6 * (1 - er) + 0.4 * flips), 0, 100)),
        mom=round(_clamp(50 + 20 * z, 0, 100)), accel=None if r3 is None or r3p is None else round(r3 - r3p, 2),
        ext=round(_clamp(50 + resid / max(atr, 0.3) * 25, 0, 100)), extPct=round(resid, 2), smaGap=round(ext_pct, 2),
        volTrend=round((sum(vv[-5:]) / 5) / (sum(vv[-15:-5]) / 10), 2) if len(vv) >= 15 and sum(vv[-15:-5]) > 0 else None,
        imbalance=None if not flow or _f(flow.get('buyUsd')) + _f(flow.get('sellUsd')) <= 0 else round((_f(flow['buyUsd']) - _f(flow['sellUsd'])) / (_f(flow['buyUsd']) + _f(flow['sellUsd'])) * 100),
        trades=None if not flow else int(_f(flow.get('n'))),
        impact=None if not (seat_usd and liq and _f(liq) > 0) else round(_f(seat_usd) / (_f(liq) / 2) * 100, 3))
    f['decay'] = bool(f['accel'] is not None and f['accel'] < 0 and (r5 or 0) > 0)
    return f


def classify(f):
    """→ (state, evidence [words with the measurement], contradictions [same], confidence 0–1). The first rule that holds decides."""
    n = int(_f((f or {}).get('n')))
    if n < MIN_BARS or f.get('trend') is None:
        return 'UNKNOWN', [f'{n} one-minute candles — {MIN_BARS} are needed'], [], 0.0
    ev, con = [], []
    r5, r15 = _f(f.get('r5')), _f(f.get('r15') if f.get('r15') is not None else f.get('r10'))
    up, tr, ch = f['dir'] == 'up', _f(f['trend']), _f(f['chop'])
    if f.get('hh'): ev.append(f"{f['hh']} higher highs")
    if f.get('hl'): ev.append(f"{f['hl']} higher lows")
    if f.get('lh'): con.append(f"{f['lh']} lower highs")
    if f.get('ll'): con.append(f"{f['ll']} lower lows")
    (ev if up else con).append(f"slope {f['slope']:+.2f}% a minute (fit {f['fit']:.2f})")
    (ev if tr >= TREND_MIN else con).append(f'trend {tr:.0f}/100 · chop {ch:.0f}/100')
    if f.get('pullback'): ev.append(f"last pullback {f['pullback']:.1f}%, {round(_f(f['recovery']) * 100)}% recovered")
    if f.get('upWick') is not None and f['upWick'] >= 0.4: con.append(f"upper wicks {round(f['upWick'] * 100)}% of the last 3 candles")
    if f.get('buy') is not None: (ev if _f(f['buy']) >= 55 else con).append(f"buy flow {_f(f['buy']):.0f}%")
    if f.get('decay'): con.append(f"momentum decaying ({f['accel']:+.1f} pts over the last 3 candles)")
    if f.get('liqD') is not None and _f(f['liqD']) <= -10: con.append(f"pool {_f(f['liqD']):+.0f}% on our tape")
    if not f.get('ohlc'): con.append('closes only — wicks not measured')
    conf = lambda s: round(_clamp(min(1.0, n / 20) * (0.5 + 0.5 * s) * (1.0 if f.get('ohlc') else 0.8), 0.05, 0.99), 2)
    if (f.get('liqD') is not None and _f(f['liqD']) <= LIQ_FAIL_DROP) or (f.get('liq') and 0 < _f(f['liq']) < LIQ_FAIL_MIN):
        return 'LIQUIDITY FAILURE', ev, [f"pool {_f(f.get('liqD')):+.0f}% on our tape, ${_f(f.get('liq')) / 1000:.1f}K left"] + con, conf(0.9)
    if r5 >= PARABOLIC_5M or (_f(f['ext']) >= PARABOLIC_EXT and r5 >= 12) or (f['up'] >= 5 and r5 >= 15):
        return 'PARABOLIC', ev + [f"{r5:+.0f}% in 5 min, extension {f['ext']:.0f}/100, {f['up']} green in a row"], con, conf(0.9)
    if f['base'] and f['breakFailed'] and f['seq'][-1:] == 'R':
        return 'FAILED BREAKOUT', ev, [f"{f['breakTries']} candle(s) broke the prior high and price is back under it"] + con, conf(0.8)
    if f['base'] and f['breakHeld'] >= 2 and f['seq'][-1:] != 'R' and up:
        return 'CONFIRMED BREAKOUT', ev + [f"{f['breakHeld']} closes above the prior high"], con, conf(0.8)
    if f['base'] and f['breakTries'] and f['breakHeld'] >= 1 and not f['breakFailed']:
        return 'BREAKOUT ATTEMPT', ev + ['broke the prior high, one close above it so far'], con, conf(0.6)
    if up and _f(f['legEff']) >= 50 and _f(f['leg']) >= 3.0 and 2.0 <= _f(f['distHigh']) <= 15.0 and _f(f['pullback']) <= 0.62 * _f(f['leg']) and f['sinceHigh'] >= 2:
        return 'PULLBACK IN UPTREND', ev + [f"climbed {f['leg']:.1f}% into the high ({f['legEff']:.0f}/100 straight), gave back {f['pullback']:.1f}%"], con, conf(_f(f['legEff']) / 100)
    if not up and tr >= TREND_MIN:
        return 'DOWNTREND', ev, con, conf(tr / 100)
    if up and tr >= TREND_STRONG and ch <= CHOP_MAX_STRONG and f['hh'] >= 2 and f['hl'] >= 2:
        return 'STRONG UPTREND', ev, con, conf(tr / 100)
    if up and tr >= TREND_MIN:
        return 'UPTREND', ev, con, conf(tr / 100)
    if r15 >= 10 and _f(f['distHigh']) <= 6 and f.get('lastHigh') == 'lower' and (f.get('decay') or (f.get('upWick') or 0) >= WICK_HEAVY):
        return 'DISTRIBUTION', ev, ['after a run: a lower high near the top with fading momentum'] + con, conf(0.6)
    if ch >= CHOP_MIN and _f(f['vol']) >= 1.0:
        return 'CHOP', ev, [f"path efficiency low: {ch:.0f}/100 chop at {f['vol']:.1f}% a candle"] + con, conf(ch / 100)
    if f.get('squeeze') is not None and f['squeeze'] <= 0.5:
        return 'COMPRESSION', ev + [f"the last 5 candles span {round(f['squeeze'] * 100)}% of the range before them"], con, conf(0.5)
    if abs(r15) < 4 and f['hl'] >= 2 and f['ll'] == 0:
        return 'ACCUMULATION', ev + ['flat price on rising lows'], con, conf(0.5)
    return 'RANGE', ev, con, conf(0.4)


def entry_call(f, state):
    """⏱ Is THIS MOMENT a place to take risk? → (call, rule id, why). A good chart at a bad spot is a WAIT; a vertical candle is never chased."""
    if state == 'UNKNOWN':
        return 'WAIT FOR CONFIRMATION', 'E0 no chart', f"only {int(_f((f or {}).get('n')))} candles — structure cannot be read yet"
    if state in ('LIQUIDITY FAILURE', 'DOWNTREND', 'CHOP', 'DISTRIBUTION', 'FAILED BREAKOUT'):
        return 'SKIP', 'E1 bad structure', f'{state}: no long thesis here'
    if state == 'PARABOLIC':
        return 'WAIT FOR PULLBACK', 'E2 no chasing', f"{_f(f.get('r5')):+.0f}% in 5 min, extension {f['ext']:.0f}/100 — vertical candles are not chased"
    if _f(f.get('vol')) >= VOL_WILD:
        return 'WAIT FOR CONFIRMATION', 'E3 too violent', f"{f['vol']:.1f}% a candle — no stop fits this"
    if state in ('ACCUMULATION', 'COMPRESSION', 'RANGE'):
        return 'WAIT FOR BREAKOUT', 'E4 no direction yet', f"{state}: waits for a close above {f['resistance']:.6g}"
    if state == 'BREAKOUT ATTEMPT':
        return 'WAIT FOR CONFIRMATION', 'E5 unconfirmed breakout', f"{f['breakHeld']} close above the prior high — needs it to hold"
    if state == 'CONFIRMED BREAKOUT':   # leaving a base always sits above the old trend line: judged on the hold + buyers, not on extension
        if f.get('buy') is not None and _f(f['buy']) < 50:
            return 'WAIT FOR CONFIRMATION', 'E10 breakout without buyers', f"held above the prior high but buy flow is {_f(f['buy']):.0f}%"
        if f.get('liqD') is not None and _f(f['liqD']) <= -10:
            return 'WAIT FOR CONFIRMATION', 'E8 pool leaving', f"pool {_f(f['liqD']):+.0f}% while price breaks out"
        if _f(f.get('r5')) >= 15:
            return 'WAIT FOR PULLBACK', 'E6 extended', f"{_f(f['r5']):+.0f}% in 5 min out of the base — waits for the retest"
        return 'ENTER NOW', 'E10 breakout held', f"{f['breakHeld']} closes above the prior high, {_f(f.get('r5')):+.1f}% in 5 min"
    if _f(f['ext']) >= EXT_WAIT or (_f(f['distHigh']) < 1.0 and _f(f.get('r5')) >= 8):
        return 'WAIT FOR PULLBACK', 'E6 extended', f"extension {f['ext']:.0f}/100, {f['distHigh']:.1f}% under the high after {_f(f.get('r5')):+.0f}% in 5 min"
    if f.get('upWick') is not None and f['upWick'] >= WICK_HEAVY:
        return 'WAIT FOR CONFIRMATION', 'E7 rejection wicks', f"upper wicks are {round(f['upWick'] * 100)}% of the last 3 candles"
    if f.get('liqD') is not None and _f(f['liqD']) <= -10:
        return 'WAIT FOR CONFIRMATION', 'E8 pool leaving', f"pool {_f(f['liqD']):+.0f}% while price holds"
    if state == 'PULLBACK IN UPTREND':
        if _f(f['recovery']) >= 0.25 and f['seq'][-1:] == 'G':
            return 'ENTER NOW', 'E9 pullback recovered', f"pulled back {f['pullback']:.1f}%, {round(f['recovery'] * 100)}% recovered, last candle green"
        return 'WAIT FOR CONFIRMATION', 'E9 pullback not turned', f"pulled back {f['pullback']:.1f}%, only {round(_f(f['recovery']) * 100)}% recovered"
    if f.get('decay') and _f(f['mom']) < 45:
        return 'WAIT FOR CONFIRMATION', 'E11 momentum fading', f"momentum {f['mom']:.0f}/100 and slowing ({f['accel']:+.1f})"
    return 'ENTER NOW', 'E12 trend in hand', f"{state}: trend {f['trend']:.0f}/100, chop {f['chop']:.0f}/100, {f['distHigh']:.1f}% under the high"


# ⚖ Devil's chart rules: (hard?, what). A soft one stands only while its own objection record does not show it blocking winners.
CHART_RULES = {'chart_parabolic': (True, 'parabolic extension'), 'chart_fake_breakout': (True, 'the breakout failed'), 'chart_liq_div': (True, 'liquidity falling while price rises'),
               'chart_chop': (True, 'chop disguised as a trend'), 'chart_top': (False, 'buying the top'), 'chart_lower_high': (False, 'a lower high is forming'),
               'chart_divergence': (False, 'flow is not confirming price'), 'chart_wick': (False, 'heavy wick rejection'), 'chart_thin': (False, 'the rise rests on very few trades'),
               'chart_young': (False, 'the trend is too young'), 'chart_late': (False, 'late: most of the move already happened')}


def objections(f, state):
    """⚖ Every chart objection that the measurements support → [(rule id, evidence)]. Nothing here fires on how a chart "looks"."""
    out = []
    if not f or f.get('trend') is None:
        return out
    r5 = _f(f.get('r5'))
    if state == 'PARABOLIC':
        out.append(('chart_parabolic', f"parabolic: {r5:+.0f}% in 5 min, extension {f['ext']:.0f}/100"))
    if state == 'FAILED BREAKOUT':
        out.append(('chart_fake_breakout', f"fake breakout: {f['breakTries']} candle(s) above the prior high, price back under it"))
    if r5 > 3 and f.get('liqD') is not None and _f(f['liqD']) <= -10:
        out.append(('chart_liq_div', f"price {r5:+.1f}% in 5 min while the pool is {_f(f['liqD']):+.0f}%"))
    if state == 'CHOP' or (_f(f['chop']) >= 70 and _f(f['vol']) >= 1.0):
        out.append(('chart_chop', f"chop {f['chop']:.0f}/100 at {f['vol']:.1f}% a candle — no trend to stand on"))
    if _f(f['distHigh']) < 1.0 and _f(f['ext']) >= EXT_WAIT:
        out.append(('chart_top', f"{f['distHigh']:.1f}% under the high at extension {f['ext']:.0f}/100"))
    if f.get('lastHigh') == 'lower' and f.get('decay'):
        out.append(('chart_lower_high', f"last swing high is lower and momentum is slowing ({f['accel']:+.1f})"))
    if r5 > 3 and ((f.get('buy') is not None and _f(f['buy']) < 45) or (f.get('imbalance') is not None and _f(f['imbalance']) < -20)):
        out.append(('chart_divergence', f"price {r5:+.1f}% in 5 min on {'buy flow ' + format(_f(f['buy']), '.0f') + '%' if f.get('buy') is not None else 'a ' + str(f['imbalance']) + '% flow imbalance'}"))
    if f.get('upWick') is not None and f['upWick'] >= WICK_HEAVY + 0.1:
        out.append(('chart_wick', f"upper wicks are {round(f['upWick'] * 100)}% of the last 3 candles"))
    if f.get('trades') is not None and f['trades'] < 6 and r5 > 5:
        out.append(('chart_thin', f"{r5:+.1f}% in 5 min on {f['trades']} trades in the last 90s"))
    if state in GOOD and int(f['n']) < 8:
        out.append(('chart_young', f"only {f['n']} candles of this trend"))
    if _f(f.get('r15')) >= 40 and _f(f['distHigh']) < 3:
        out.append(('chart_late', f"already {_f(f['r15']):+.0f}% in 15 min and {f['distHigh']:.1f}% under the high"))
    return out


def risk(f, state):
    """🛡 Chart risk as a size multiplier ≤ 1 → (mult, why). It never returns more than 1."""
    if not f or state == 'UNKNOWN':
        return 0.5, 'structure unknown — half size'
    if state in ('CHOP', 'DOWNTREND', 'LIQUIDITY FAILURE', 'FAILED BREAKOUT', 'DISTRIBUTION'):
        return 0.0, f'{state} — no size'
    if state == 'PARABOLIC':
        return 0.25, f"parabolic ({_f(f.get('r5')):+.0f}% in 5 min) — quarter size at most"
    hits = []
    if state in ('BREAKOUT ATTEMPT', 'CONFIRMED BREAKOUT'):
        hits.append((0.5, 'a young breakout'))
    if _f(f.get('vol')) >= 4.0:
        hits.append((0.5, f"{f['vol']:.1f}% a candle"))
    if f.get('distLow') is not None and support_gap(f) >= 12:
        hits.append((0.5, f'{support_gap(f):.0f}% above support'))
    if state in ('ACCUMULATION', 'COMPRESSION', 'RANGE'):
        hits.append((0.75, f'{state}: no trend yet'))
    if not hits:
        return 1.0, f"{state}: trend {f['trend']:.0f}/100, pullbacks {f['pullback']:.1f}%"
    m, why = min(hits, key=lambda x: x[0])
    return m, why


def support_gap(f):
    """How far price sits above the nearest support it has (the prior window's low, else the window low), %."""
    s = _f((f or {}).get('support')) or _f((f or {}).get('low'))
    return round((_f(f['px']) / s - 1) * 100, 2) if s > 0 and _f(f.get('px')) > 0 else 0.0


def stop_for(f, state, ctx=None, ceiling=30.0):
    """🛑 The NORMAL stop for an entry here, % → (stop, parts). Room = the gap to support + 2 average candles, then cut by a fifth for each
    of: a thin pool (< $50K), a coin under 6h old, degraded execution, a breakout / unknown structure. Always inside
    [STOP_FLOOR, min(ceiling, CATASTROPHIC_STOP − 5)] — it cannot be learned wider than that, and the catastrophic stop sits above it."""
    c = ctx or {}
    top = min(_clamp(_f(ceiling), STOP_FLOOR, CATASTROPHIC_STOP - 5), CATASTROPHIC_STOP - 5)
    if not f or f.get('atr') is None:
        return round(_clamp(top * 0.5, STOP_FLOOR, top), 1), ['no chart: half the ceiling']
    room = min(support_gap(f), 12.0) + 2 * _f(f['atr'])
    parts = [f"support {min(support_gap(f), 12.0):.1f}% away + 2 candles of {f['atr']:.1f}%"]
    for cond, word in ((0 < _f(c.get('liq')) < 50_000, 'thin pool'), (c.get('ageH') is not None and _f(c['ageH']) < 6, 'under 6h old'),
                       (c.get('courier') in ('DEGRADED', 'BAD'), 'execution degraded'), (state in ('CONFIRMED BREAKOUT', 'BREAKOUT ATTEMPT', 'UNKNOWN'), 'unproven structure')):
        if cond:
            room *= 0.8; parts.append(f'−20% {word}')
    stop = round(_clamp(room, STOP_FLOOR, top), 1)
    parts.append(f'bounds {STOP_FLOOR:g} … {top:g}%')
    return stop, parts


EXPECT = {'STRONG UPTREND': 4, 'UPTREND': 3, 'PULLBACK IN UPTREND': 3, 'CONFIRMED BREAKOUT': 3}


def thesis(chart, now, ctx=None, ceiling=30.0, take=None):
    """🧾 The entry thesis saved with a REAL position (never rewritten): what the structure was, the rule Trigger entered on, the support
    it stands on, the price that invalidates it, the stop, how many 5-minute windows it is expected / allowed to take, the reasons
    and the risks known at that moment."""
    f, state = (chart or {}).get('f') or {}, (chart or {}).get('state') or 'UNKNOWN'
    stop, parts = stop_for(f, state, ctx, ceiling)
    sup = _f(f.get('support')) or _f(f.get('low'))
    exp = max(MIN_WINDOWS, EXPECT.get(state, MIN_WINDOWS))
    ent = (chart or {}).get('entry') or ['', '', '']
    return {'structure': state, 'at': now, 'px': f.get('px'), 'call': ent[0], 'triggerRule': ent[1], 'why': ent[2], 'support': sup or None,
            'invalidation': round(sup * (1 - max(_f(f.get('atr')), 0.3) / 100), 12) if sup else None, 'stopPct': stop, 'stopParts': parts,
            'expectedHoldWindows': exp, 'maxHoldWindows': MAX_WINDOWS, 'trend': f.get('trend'), 'chop': f.get('chop'), 'mom': f.get('mom'),
            'reasons': list((chart or {}).get('ev') or [])[:6], 'risks': list((chart or {}).get('con') or [])[:6], 'src': (chart or {}).get('src'), 'take': take}


def review(th, chart, pct, held_min, granted=None):
    """☠ Reaper's checkpoint against the SAVED thesis → {verdict: valid | weak | invalid | unknown, why [..], window, granted, next}.
    valid   = the structure is still one a long stands on and price is above the invalidation level
    invalid = support broke into a bad structure, the pool is failing, a breakout failed, or a downtrend printed lower lows
    weak    = neither (range / compression / unknown): it uses up its windows instead of earning more"""
    f, state = (chart or {}).get('f') or {}, (chart or {}).get('state') or 'UNKNOWN'
    win = int(held_min // WINDOW_MIN)
    g = int(granted if granted is not None else (th or {}).get('expectedHoldWindows') or MIN_WINDOWS)
    out = {'window': win, 'granted': g, 'next': round((win + 1) * WINDOW_MIN * 60 - held_min * 60), 'state': state}
    if not f or state == 'UNKNOWN':
        return {**out, 'verdict': 'unknown', 'why': ['no chart this pass — the thesis cannot be checked']}
    inv, px = _f((th or {}).get('invalidation')), _f(f.get('px'))
    why = []
    if state == 'LIQUIDITY FAILURE':
        return {**out, 'verdict': 'invalid', 'why': [f'{state} — the thesis ({(th or {}).get("structure")}) is gone']}
    # a FAILED BREAKOUT label alone is one candle back under the old high — it invalidates only once price is under the thesis's own
    # invalidation level (2026-10-10, first hour live: $FPES and $USWR were bought and sold flat inside 4 minutes on the label alone)
    if inv and px and px < inv and state in BAD:
        return {**out, 'verdict': 'invalid', 'why': [f'price under the invalidation level ({px:.6g} < {inv:.6g}) in a {state}']}
    if state == 'DOWNTREND' and _f(f.get('ll')) >= 1 and f.get('lastHigh') == 'lower':
        return {**out, 'verdict': 'invalid', 'why': [f"DOWNTREND with a lower high and {f['ll']} lower low(s)"]}
    if state in GOOD:
        why.append(f'{state} still valid')
        if f.get('lastHigh') != 'lower' and f.get('lastLow') != 'lower': why.append('HH/HL intact')
        if not f.get('decay'): why.append(f"momentum {f['mom']:.0f}/100")
        if f.get('liqD') is None or _f(f['liqD']) > -10: why.append('liquidity stable')
        turning = f.get('lastHigh') == 'lower' and f.get('decay')
        return {**out, 'verdict': 'weak' if turning else 'valid', 'why': ['a lower high with fading momentum'] if turning else why}
    return {**out, 'verdict': 'weak', 'why': [f'{state}: no structure a long stands on' + (' (lower high)' if f.get('lastHigh') == 'lower' else '')]}


def read(rows, now=0.0, ohlc=True, src='candles', **k):
    """snapshot + classify + entry call + objections + risk in ONE object — what the desks share. `f` = the full features."""
    f = snapshot(rows, now, ohlc, **k)
    state, ev, con, conf = classify(f)
    call = entry_call(f, state)
    m, why = risk(f, state)
    return {'state': state, 'src': src, 'n': f.get('n'), 'conf': conf, 'ev': ev, 'con': con, 'entry': list(call), 'objs': [list(o) for o in objections(f, state)],
            'risk': [m, why], 'trend': f.get('trend'), 'chop': f.get('chop'), 'mom': f.get('mom'), 'ext': f.get('ext'), 'dir': f.get('dir'), 'f': f}


def compact(chart):
    """The few fields a table row carries (the full features stay in the office's shared snapshot)."""
    return None if not chart else {k: chart.get(k) for k in ('state', 'src', 'n', 'conf', 'entry', 'trend', 'chop', 'mom', 'ext', 'risk')}
