"""🎭 PROMPT STUDIO (owner, 2026-10-22: "context prompts and suggested prompts for all models — 3 auto-generated ELITE SUPREME PERSONAS and
DEGEN TRENCH prompts for each model, so if G4 or OSSY's trading style isn't working we can have prompts auto-tuned to fix the mindset:
quick, but patient when in profit — rush is good and progressive"). Pure + tested; the service reads the records, the router applies.

Every model gets three prompt SETS written from its OWN record (its numbers are in the text) plus an AUTO-TUNED set built from what that record
says is wrong (`diagnose`). A set is an OVERLAY: the owner applies it and the router appends it to the system prompt of EVERY call that model
gets — G4 / OSSY on LM Studio. Only the MINDSET changes: the trading rules, the answer schema and every money check stay.
One active overlay per model; revert = none. `since` grades the overlay on the trades that closed after it was applied.
"""

KEYS = ('lan', 'local')
NAMES = {'lan': 'G4', 'local': 'OSSY'}
SETS = ('elite', 'degen', 'progressive', 'tuned')
LABEL = {'elite': 'ELITE', 'degen': 'DEGEN TRENCH', 'progressive': 'PROGRESSIVE', 'tuned': 'AUTO-TUNED'}
MAX_CHARS = {'lan': 900, 'local': 900}
DIAL_KEYS = ('speed', 'patience', 'risk', 'discipline')
GIVE_PEAK, GIVE_KEEP = 10.0, 2.0    # peaked ≥ +10 % and closed ≤ +2 % = a winner ridden back
QUICK_MIN = 15.0                     # the card's law: holds under 15 min lose
MIN_N = 5                            # fewer closed trades = too few to judge a habit


def _f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _med(xs):
    s = sorted(x for x in xs if x is not None)
    return s[len(s) // 2] if s else None


def stats(trades=None, calls=None, bench=None, grades=None):
    """A model's record → the numbers every set is written from. trades = closed real trades [{pct, peak, heldMin}]; calls = its call log
    [{action, ms}]; bench = ai_seat.bench(); Unknown stays None, never 0."""
    tr = [t for t in trades or [] if _f((t or {}).get('pct')) is not None]
    pct = [_f(t['pct']) for t in tr]
    wins, losses = [p for p in pct if p > 0], [p for p in pct if p <= 0]
    held = [_f(t.get('heldMin')) for t in tr]
    win_held = [_f(t.get('heldMin')) for t in tr if _f(t['pct']) > 0 and _f(t.get('heldMin')) is not None]
    loss_held = [_f(t.get('heldMin')) for t in tr if _f(t['pct']) <= 0 and _f(t.get('heldMin')) is not None]
    quick = [t for t in tr if _f(t.get('heldMin')) is not None and _f(t['heldMin']) < QUICK_MIN]
    gave = [t for t in tr if (_f(t.get('peak')) or 0) >= GIVE_PEAK and _f(t['pct']) <= GIVE_KEEP]
    cl = [c for c in calls or [] if isinstance(c, dict)]
    ok = [c for c in cl if c.get('action') and c.get('action') != 'NO ANSWER']
    fv = (grades or {}).get('favor') or {}
    return {'n': len(tr), 'wonPct': round(100 * len(wins) / len(tr)) if tr else None, 'avgPct': round(sum(pct) / len(pct), 1) if pct else None,
            'avgWin': round(sum(wins) / len(wins), 1) if wins else None, 'avgLoss': round(sum(losses) / len(losses), 1) if losses else None,
            'medHeld': _med(held), 'winHeld': _med(win_held), 'lossHeld': _med(loss_held), 'quickN': len(quick), 'quickWonPct': round(100 * sum(1 for t in quick if _f(t['pct']) > 0) / len(quick)) if quick else None,
            'gaveN': len(gave), 'calls': len(cl), 'answerPct': round(100 * len(ok) / len(cl)) if cl else None,
            'medMs': _med([_f(c.get('ms')) for c in ok if _f(c.get('ms'))]),
            'favorN': (bench or {}).get('n') or 0, 'favorMed': (bench or {}).get('median'), 'favorUp': (bench or {}).get('upPct'),
            'yesN': fv.get('n') or 0, 'yesRight': fv.get('rightPct'), 'yesTypical': fv.get('typical')}


def _fix(key, title, evidence, rule, dial):
    return {'key': key, 'title': title, 'evidence': evidence, 'rule': rule, 'dial': dial}


def diagnose(st):
    """What the record says is wrong with this model's mindset → [fix] (worst first). Each fix: the habit, the evidence (its numbers), the
    rule that fixes it, and how it moves the dials. A healthy or too-short record → []."""
    s, out = st or {}, []
    n = s.get('n') or 0
    if n >= MIN_N and s.get('gaveN', 0) >= max(2, 0.3 * n):
        out.append(_fix('giveback', 'rides winners back to red', f"{s['gaveN']} of {n} trades peaked +{GIVE_PEAK:g} % and closed under +{GIVE_KEEP:g} %",
                        f"Once a trade is +{GIVE_PEAK:g} %, your stop goes to break-even; past +25 % give back at most a third of the peak.", {'patience': -10, 'discipline': 15}))
    if n >= MIN_N and s.get('avgLoss') is not None and s.get('avgWin') is not None and abs(s['avgLoss']) >= 2 * max(0.5, s['avgWin']):
        out.append(_fix('bleed', 'lets losers run', f"average loss {s['avgLoss']:+.1f} % vs average win {s['avgWin']:+.1f} %",
                        'Cut a loser at the line you set BEFORE the buy. Never widen a stop; a red trade gets no hope minutes.', {'risk': -15, 'discipline': 15}))
    if s.get('quickN', 0) >= max(3, 0.5 * n) and (s.get('quickWonPct') is not None and s['quickWonPct'] < 35):
        out.append(_fix('jumpy', 'bails inside 15 min', f"{s['quickN']} of {n} trades closed under {QUICK_MIN:g} min, {s['quickWonPct']} % of those won",
                        f"A clean trade gets at least {QUICK_MIN:g} minutes. Only the chart breaking (a lower low, the germ floor lost) or your own stop ends it sooner.", {'patience': 20, 'speed': -10}))
    if n >= 8 and s.get('wonPct') is not None and s['wonPct'] < 30:
        out.append(_fix('cold', 'entries lose', f"{s['wonPct']} % won over {n} real trades",
                        'Buy only the proven setup: graduated, cap under $30K, buyers leading, a higher low above the germ floor. Anything else is WAIT.', {'risk': -15, 'speed': -10, 'discipline': 10}))
    if s.get('favorN', 0) >= 30 and s.get('favorMed') is not None and s['favorMed'] <= 0 and (s.get('favorUp') or 0) < 50:
        out.append(_fix('favor', 'its FAVOR calls lose', f"last {s['favorN']} FAVOR calls: median {s['favorMed']:+.1f} %, {s['favorUp']} % up",
                        'Say FAVOR only when three facts agree (trend, buyers, pool depth). One or two = NEUTRAL.', {'risk': -10, 'discipline': 10}))
    if s.get('yesN', 0) >= 10 and s.get('yesRight') is not None and s['yesRight'] < 50:
        out.append(_fix('yes', 'its YES calls lose', f"{s['yesN']} YES calls graded: {s['yesRight']} % right, typical {s.get('yesTypical') if s.get('yesTypical') is not None else '—'} %",
                        'YES only when graduated, cap under $30K, buyers over 55 % and the pool over $10K. Everything else is NO.', {'risk': -15, 'discipline': 10}))
    if s.get('medMs') is not None and s['medMs'] > 45000:
        out.append(_fix('slow', 'answers slowly', f"median answer {s['medMs'] / 1000:.0f} s",
                        'Decide in one pass: read NOW and the theory line, then answer. No essays, no second thoughts.', {'speed': 15}))
    if s.get('calls', 0) >= 10 and s.get('answerPct') is not None and s['answerPct'] < 70:
        out.append(_fix('mute', 'misses calls', f"answered {s['answerPct']} % of {s['calls']} calls",
                        'Always answer in the schema, even when unsure: WAIT is an answer, silence is not.', {'discipline': 10}))
    return out


def _line(s):
    """The record as one sentence the model reads about itself."""
    if s.get('n'):
        return f"your real record: {s['n']} trades, {s['wonPct']} % won, average {s['avgPct']:+.1f} % a trade"
    if s.get('yesN'):
        return f"your graded YES calls: {s['yesN']}, {s['yesRight']} % right"
    return 'no closed record yet — earn one'


def _clip(t, key):
    m = MAX_CHARS.get(key, 900)
    return t if len(t) <= m else t[:m - 1].rsplit(' ', 1)[0] + '…'


def _dials(base, fixes=()):
    d = dict(base)
    for fx in fixes:
        for k, v in (fx.get('dial') or {}).items():
            d[k] = d.get(k, 50) + v
    return {k: max(5, min(100, int(d.get(k, 50)))) for k in DIAL_KEYS}


def best_rung(ladder_rows):
    """The mindset that PROVED best for this model (≥ MIN_N trades opened under it, the best average) — None until one is proven and green."""
    return next((x for x in ladder_rows or [] if (x.get('n') or 0) >= MIN_N and x.get('set') in SETS and (x.get('avgPct') or 0) > 0), None)


def sets(key, st, fixes=None, best=None):
    """The four prompt sets for one model, each {set, label, tag, dials, text, why}. Text = the overlay the router appends, ≤ MAX_CHARS.
    `best` = the ladder's proven-best mindset: AUTO-TUNED keeps its core (owner, 2026-10-23: "G4 was losing — better auto-updated prompts")."""
    nm, s, fx = NAMES.get(key, key), st or {}, list(fixes or [])
    rec = _line(s)
    body = {'elite': (f"ELITE MINDSET — {nm}, the family's sniper. Few trades, all clean: if fewer than three facts agree (trend, buyers, pool), WAIT. "
                      "Set TP / SL before the buy and size only what the pool can take back. Once set, only the chart breaks your lines. "
                      f"Pick the setups that paid and nothing else — {rec}. Calm, exact, numbers in every line."),
            'degen': (f"DEGEN TRENCH MINDSET — {nm}, born in the trenches, ruled by the laws: a coin under 15 min old loses, the bonding curve is the worst bucket, "
                      "graduated under $30K is the one setup that pays, exits are set before entry (+50 / −30). The germ floor is the base before the pump: "
                      "above it with buyers over 55 % and a higher low, you send it. A fresh pump with sellers leading is exit liquidity — never yours. "
                      f"Jeets dump the first green; you hold the germ, not the candle. {rec[0].upper() + rec[1:]}."),
            'progressive': (f"PROGRESSIVE MINDSET — {nm}: quick in, patient in profit. RUSH the entry once the move is confirmed (buyers leading, a higher low, "
                            "volume rising): hesitation costs the best fill. Once green, SLOW DOWN: trail the peak, let +10 % become +30 %, trim a third at +25 % "
                            "and ride the rest. Red early = cut at your line, no hope holds. Speed on the way in, patience on the way up, zero patience on the way down. "
                            f"{rec[0].upper() + rec[1:]}."),
            'tuned': (f"AUTO-TUNED for {nm} from {rec}. Fix these habits first: " + ' '.join(f"({i + 1}) {f['rule']}" for i, f in enumerate(fx))
                      + (f" Your winners held a median {s['winHeld']:.0f} min, your losers {s['lossHeld']:.0f} min — hold like your winners."
                         if s.get('winHeld') is not None and s.get('lossHeld') is not None and abs(s['winHeld'] - s['lossHeld']) >= 5 else '')
                      + (f" Your best proven mindset is {LABEL[best['set']]} ({best['avgPct']:+.1f} % avg over {best['n']} trades): keep its core."
                         if best else '')
                      + " Everything else: your own style.") if fx else (f"AUTO-TUNED for {nm}: the record shows no losing habit yet ({rec}). Keep your style; "
                                                                         f"one upgrade — once a trade is +{GIVE_PEAK:g} %, the stop goes to break-even.")}
    base = {'elite': {'speed': 35, 'patience': 80, 'risk': 25, 'discipline': 95}, 'degen': {'speed': 75, 'patience': 55, 'risk': 70, 'discipline': 60},
            'progressive': {'speed': 85, 'patience': 85, 'risk': 55, 'discipline': 80}, 'tuned': {'speed': 60, 'patience': 60, 'risk': 50, 'discipline': 70}}
    tag = {'elite': 'few trades · all clean', 'degen': 'germ floor · trench laws', 'progressive': 'rush in · ride green · cut red',
           'tuned': f"{len(fx)} habit{'s' if len(fx) != 1 else ''} fixed from the record" if fx else 'record is healthy'}
    why = {'elite': 'Quality over count: the card pays on the few setups that work.', 'degen': 'Argues from the measured trench theory, in trench slang.',
           'progressive': 'Your words: quick, but patient when in profit — rush is good.', 'tuned': '; '.join(f"{f['title']}: {f['evidence']}" for f in fx) or 'Nothing in the record needs fixing yet.'}
    return [{'set': k, 'label': LABEL[k], 'tag': tag[k], 'dials': _dials(base[k], fx if k == 'tuned' else ()), 'text': _clip(body[k], key), 'why': why[k]} for k in SETS]


def clean_active(raw):
    """The stored overlays → {key: {set, text, at, by}} — unknown models / sets dropped, text clipped to the model's budget."""
    out = {}
    for k, v in (raw or {}).items() if isinstance(raw, dict) else ():
        if k not in KEYS or not isinstance(v, dict) or v.get('set') not in SETS:
            continue
        t = ' '.join(str(v.get('text') or '').split())
        if t:
            out[k] = {'set': v['set'], 'text': _clip(t, k), 'at': _f(v.get('at')) or 0.0, 'by': str(v.get('by') or '')[:44], 'edited': bool(v.get('edited'))}
    return out


def overlay_block(text):
    """How an applied set reads inside the system prompt (the router appends it to the FIRST system message)."""
    return f"\n\n🎭 MINDSET (the owner's applied prompt — it changes how you think, never your answer format or the desk's rules):\n{text}" if text else ''


def since(trades, at):
    """The applied overlay's own record: the trades that OPENED after it was applied → {n, wonPct, avgPct}."""
    a = _f(at) or 0.0
    s = stats([t for t in trades or [] if (_f((t or {}).get('at')) or 0.0) >= a]) if a else stats([])
    return {'n': s['n'], 'wonPct': s['wonPct'], 'avgPct': s['avgPct']}


# ── 🤖 AUTO-TUNE + 🏆 the MINDSET LADDER (owner, 2026-10-22: "apply the AUTO-TUNED set automatically when a model's record turns red, plus a
# ladder of which mindset paid most per model") ──────────────────────────────────────────────────────────────────────────────────────────
RECENT_N = 10                 # "turned red" is read on the last 10 closed trades
RED_WON = 40                  # red = losing on average AND under 40 % won
AUTO_COOLDOWN = 6 * 3600.0    # any applied set (yours or the auto one) gets 6 h to prove itself before the switch moves it
HIST_KEEP = 200
AUTO_DEFAULT = ('lan', 'local')   # 🤖 owner, 2026-10-23: "G4 was losing so I asked for auto-updated prompts" — the seat models' switch is ON until the owner turns it off


def auto_on(raw, key):
    """Is the auto-tune switch on for this model? The owner's own choice wins; never set = ON for the seat models (G4, OSSY)."""
    a = (raw or {}).get('auto') if isinstance(raw, dict) else None
    return bool(a[key]) if isinstance(a, dict) and key in a else key in AUTO_DEFAULT
PLAIN = 'plain'


def recent(trades, n=RECENT_N):
    """The record of the last `n` closed trades (oldest → newest by open time)."""
    tr = sorted([t for t in trades or [] if _f((t or {}).get('pct')) is not None], key=lambda t: _f(t.get('at')) or 0.0)
    return stats(tr[-n:])


def is_red(st):
    """Is this window of the record red? Too few trades = never red (nothing proved yet)."""
    s = st or {}
    if (s.get('n') or 0) >= MIN_N:
        return (s.get('avgPct') or 0) < 0 and (s.get('wonPct') or 0) < RED_WON
    return False


def red_word(st):
    s = st or {}
    return f"last {s['n']} trades: {s['wonPct']} % won, {s['avgPct']:+.1f} % avg" if s.get('n') else 'not enough trades yet'


def auto_pick(on, active, rec_st, tuned, now, cooldown=AUTO_COOLDOWN):
    """The switch's decision for one model → None or {'set': 'tuned', 'text', 'why'}. Only when the switch is ON, the recent record is RED,
    the model is not already on this exact tune, and whatever is applied has had its cooldown."""
    if not on or not tuned or not tuned.get('text') or not is_red(rec_st):
        return None
    if active and active.get('set') == 'tuned' and active.get('text') == tuned['text']:
        return None
    if active and (_f(now) or 0) - (_f(active.get('at')) or 0) < cooldown:
        return None
    return {'set': 'tuned', 'text': tuned['text'], 'why': f"record turned red ({red_word(rec_st)}) → AUTO-TUNED applied"}


def hist_add(history, key, set_, now, by):
    """One apply / revert on the history the ladder is cut from (set None = back to the plain prompt)."""
    return (list(history or []) + [{'key': key, 'set': set_ if set_ in SETS else None, 'at': round(_f(now) or 0.0, 1), 'by': str(by or '')[:44]}])[-HIST_KEEP:]


def periods(history, key, now, active=None):
    """[(set or 'plain', start, end)] — which mindset ran when. No history but a set applied = it ran from its apply time."""
    hs = sorted([h for h in history or [] if isinstance(h, dict) and h.get('key') == key], key=lambda h: _f(h.get('at')) or 0.0)
    if not hs and active:
        hs = [{'set': active.get('set'), 'at': active.get('at')}]
    out, cur, start = [], PLAIN, 0.0
    for h in hs:
        at = _f(h.get('at')) or 0.0
        out.append((cur, start, at))
        cur, start = (h.get('set') if h.get('set') in SETS else PLAIN), at
    out.append((cur, start, (_f(now) or 0.0) + 1))
    return [p for p in out if p[2] > p[1]]


def ladder(trades, history, key, now, active=None):
    """🏆 Which mindset paid most for this model: every closed trade goes to the mindset that was active when it OPENED. Proven rows
    (≥ MIN_N trades) rank by average % first, then the ones still proving, then the ones never tried."""
    per = periods(history, key, now, active)
    rows = {s: [] for s in (PLAIN,) + SETS}
    for t in trades or []:
        at = _f((t or {}).get('at'))
        if at is None or _f(t.get('pct')) is None:
            continue
        hit = next((s for s, a, b in per if a <= at < b), PLAIN)
        rows[hit].append(t)
    out = []
    for s, ts in rows.items():
        st = stats(ts)
        usd = [_f(t.get('usd')) for t in ts if _f(t.get('usd')) is not None]
        out.append({'set': s, 'label': LABEL.get(s, 'PLAIN PROMPT'), 'n': st['n'], 'wonPct': st['wonPct'], 'avgPct': st['avgPct'],
                    'usd': round(sum(usd), 3) if usd else None, 'proving': 0 < st['n'] < MIN_N, 'active': (active or {}).get('set', PLAIN) == s if active else s == PLAIN})
    rank = lambda r: -(r['avgPct'] if r['avgPct'] is not None else -1e9)
    return (sorted([r for r in out if r['n'] >= MIN_N], key=rank) + sorted([r for r in out if r['proving']], key=rank) + [r for r in out if not r['n']])
