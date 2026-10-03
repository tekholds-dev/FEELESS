"""🧬 Card DNA — every card (Arena, engine, HQ, user) carries its OWN automation config, so no two cards play alike.
Pure, tested. The same fields are what the FUSE Card program will execute once the owner signs (see docs/GO_LIVE.md):

  cycle     off · classic (anchor→degen→anchor→mixed) · adaptive (losing → majors, winning → runners) · safe · press
  compound  smart (gains go to the strongest coins — momentum-weighted, never into fading ones) · even · off
  payoutPct share of every profit take that goes straight to the owner's wallet (0 · 25 · 50 · 75 · 100); the rest compounds
  clock     reshuffle clock in hours (5m … 24h)
  stop      sell · park (sell to SOL, buy back at entry with buyers) · hold
  trail     lock a +50% run before it turns red

`assign` gives each card a DNA nobody else on the board has (stable per card id). `learn` is the engine's brain: from
battle results it scores every trait value and `best` returns the winning combination — new engine cards are born with it.
"""
import hashlib

CYCLES = ('off', 'classic', 'adaptive', 'safe', 'press', 'rescue', 'auto')
COMPOUNDS = ('smart', 'even', 'off')
PAYOUTS = (0, 25, 50, 75, 100)
CLOCKS = (5 / 60, 0.25, 1, 12, 24)
STOPS = ('sell', 'park', 'hold')
EMOJI = {'off': '➡', 'classic': '⚓🔥', 'adaptive': '🧠', 'safe': '⚓', 'press': '🔥', 'rescue': '🛟', 'auto': '🤖', 'smart': '🧲', 'even': '⚖', 'sell': '✂', 'park': '🅿', 'hold': '❄'}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def clean(d):
    d = d if isinstance(d, dict) else {}
    pick = lambda v, opts, dflt: v if v in opts else dflt
    clock = next((c for c in CLOCKS if abs(c - _f(d.get('clock'))) < 0.005), 24)
    pay = min(PAYOUTS, key=lambda p: abs(p - _f(d.get('payoutPct', 50))))
    return {'cycle': pick(d.get('cycle'), CYCLES, 'off'), 'compound': pick(d.get('compound'), COMPOUNDS, 'smart'), 'payoutPct': pay,
            'clock': clock, 'stop': pick(d.get('stop'), STOPS, 'sell'), 'trail': bool(d.get('trail', True))}


def sig(d):
    d = clean(d)
    return (d['cycle'], d['compound'], d['payoutPct'], round(d['clock'], 3), d['stop'])


def label(d):
    d = clean(d)
    clk = f"{d['clock']:g}h" if d['clock'] >= 1 else f"{round(d['clock'] * 60)}m"
    return f"{EMOJI[d['cycle']]} {d['cycle']} · {EMOJI[d['compound']]} {d['compound']} compound · 💸 {d['payoutPct']}% out · ⟳ {clk} · {EMOJI[d['stop']]} {d['stop']}"


def _all():
    return [(c, m, p, k, s) for c in CYCLES for m in COMPOUNDS for p in PAYOUTS for k in CLOCKS for s in STOPS]


def assign(cards, known=None, lean=None):
    """{card_id: dna} — keeps every card's existing DNA (`known`), gives the rest a combination nobody else holds. A card's
    `lean` (dial: safe / balanced / degen) steers the pick so the DNA fits the card; the order is stable per card id."""
    known = {k: clean(v) for k, v in (known or {}).items()}
    taken = {sig(v) for k, v in known.items() if k in {c['id'] for c in cards}}
    out = {}
    combos = _all()
    fit = {'safe': lambda t: t[0] in ('safe', 'off', 'adaptive') and t[2] >= 50 and t[4] != 'hold',
           'degen': lambda t: t[0] in ('press', 'classic', 'adaptive') and t[2] <= 50 and t[3] <= 1,
           'balanced': lambda t: t[0] in ('adaptive', 'classic', 'safe') and 25 <= t[2] <= 75}
    for c in cards or []:
        if c['id'] in known:
            out[c['id']] = known[c['id']]
            continue
        start = int(hashlib.sha256(str(c['id']).encode()).hexdigest(), 16) % len(combos)
        order = combos[start:] + combos[:start]
        want = fit.get((lean or {}).get(c['id']) or c.get('dial'))
        ts = lambda t: (t[0], t[1], t[2], round(t[3], 3), t[4])
        pickd = next((t for t in order if ts(t) not in taken and (want is None or want(t))), None) or next((t for t in order if ts(t) not in taken), order[0])
        taken.add(ts(pickd))
        out[c['id']] = clean({'cycle': pickd[0], 'compound': pickd[1], 'payoutPct': pickd[2], 'clock': pickd[3], 'stop': pickd[4]})
    return out


def learn(results, dna):
    """🧠 Trait scores from battle results [{winner, loser}] (card ids) × their DNA: wins / fights per trait value."""
    score = {}
    for r in results or []:
        for cid, won in ((r.get('winner'), 1), (r.get('loser'), 0)):
            d = dna.get(cid)
            if not cid or not d:
                continue
            for trait in ('cycle', 'compound', 'payoutPct', 'clock', 'stop'):
                s = score.setdefault(trait, {}).setdefault(str(d[trait]), {'w': 0, 'n': 0})
                s['w'] += won; s['n'] += 1
    return score


def best(score, min_n=3):
    """The winning DNA: for each trait the value with the best win rate over ≥ min_n fights (else the default)."""
    base = clean({})
    out, why = dict(base), []
    for trait, vals in (score or {}).items():
        ok = [(v, s['w'] / s['n'], s['n']) for v, s in vals.items() if s['n'] >= min_n]
        if not ok:
            continue
        v, rate, n = max(ok, key=lambda x: (x[1], x[2]))
        cast = float(v) if trait in ('payoutPct', 'clock') else v
        out[trait] = int(cast) if trait == 'payoutPct' else cast
        why.append(f"{trait} {v} won {round(rate * 100)}% of {n}")
    return {'dna': clean(out), 'why': why}


def split_profit(gain_usd, d):
    """A profit take under this DNA: (to the wallet, compounded back into the card)."""
    d = clean(d)
    out = round(_f(gain_usd) * d['payoutPct'] / 100, 6)
    return out, round(_f(gain_usd) - out, 6) if d['compound'] != 'off' else 0.0


def compound_weights(legs, mom):
    """🧲 smart compound: weight each coin by momentum (1h move + buy share), fading coins get nothing. Returns {pair: weight}."""
    w = {}
    for l in legs or []:
        m = (mom or {}).get(l['pairAddress']) or {}
        fading = _f(m.get('chg1h')) < 0 and _f(m.get('buyShare')) < 50
        if fading:
            continue
        w[l['pairAddress']] = max(0.2, 1 + _f(m.get('chg1h')) / 50 + (_f(m.get('buyShare')) - 50) / 50) if m else 1.0
    tot = sum(w.values())
    return {k: v / tot for k, v in w.items()} if tot else {l['pairAddress']: 1 / len(legs) for l in legs or []}
