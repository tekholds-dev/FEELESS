"""😴 THE REGRET LEDGER — the agents learn from the coins they DIDN'T take, and tune their own checks (owner, 2026-10-13: "agents / AI need to
learn like you do from missed opportunities and tweaks … last forever untouched"). Pure + tested (`tests/test_regret.py`).

The missed-winner autopsy (`office_edge.missed_winners`) files only the coins that RAN — it can never say a block was wrong, because the
coins the same block rightly kept out are not on it. Here EVERY coin a check blocked is noted at its price with the check that blocked it,
next to every coin the desk actually TOOK, and both are graded the same way JUDGE_SEC later (end %, peak seen, dumped). Per check:
  blocked typical result vs taken typical result, how many ran (peak ≥ RAN_PCT), how many dumped (end ≤ DUMP_PCT).

TWEAKS (only on a check the owner left on AGENTS — the owner's own setting always wins, and money safety checks never move):
  · a buy-gate limit (price gap / sell-back / smallest pool) steps ONE notch looser when, on ≥ MIN_N blocked AND ≥ MIN_N taken coins, the
    blocked ones did ≥ EDGE points better and dumped no more than the taken ones (+ DUMP_SLACK) — at most once per STEP_SEC;
  · a timing wait (Trigger's flow PEAK / SELLERS waits) switches OFF the same way, and back ON when its blocked coins turn worse;
  · every tweak is ROLLED BACK when the coins taken since it typically do ≥ EDGE points worse than the taken coins before it.
Nothing here buys, sizes or sells; it moves a check one notch inside the owner's option list, with its reason on the page.
"""
import re

JUDGE_SEC = 1800.0      # graded 30 minutes after the block (the trench desk's window)
GONE_SEC = 7200.0       # no price for 2h = the coin is gone: −100%
RENOTE_SEC = 1800.0     # one note per coin + check per 30 min
RAN_PCT, DUMP_PCT = 20.0, -30.0
MIN_N, EDGE, DUMP_SLACK = 12, 5.0, 5.0
STEP_SEC = 6 * 3600.0
KEEP_OPEN, KEEP_DONE = 400, 1500
WINDOW_SEC = 48 * 3600.0   # the record a tweak is judged on

# check → how a refusal / wait reads in the desk's own words
CHECKS = (('gate:gap', re.compile(r'above market', re.I)), ('gate:back', re.compile(r'sells back|sell it back', re.I)),
          ('gate:pool', re.compile(r'pool too thin', re.I)), ('gate:route', re.compile(r'route|jupiter|429', re.I)))
# the tunable checks: key → (cfg key, the steps from tightest to loosest, what the step means). 0 = the agents' own default.
GATES = {'gate:gap': ('agentGapPct', (0, 4, 6, 8), 'buy price over market'),
         'gate:back': ('agentBackPct', (0, 5, 7, 10), 'sell-back loss'),
         'gate:pool': ('agentPoolMin', (0, 5000, 3000), 'smallest pool')}
WAITS = {'flow:PEAK': 'peakWait', 'flow:SELLERS': 'sellersWait'}   # Trigger's tape waits that can switch off / on


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def _med(xs):
    s = sorted(xs)
    return None if not s else s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2


def why_class(text):
    """A refusal in the keeper's own words → the check that made it ('gate:…'), else None."""
    for k, rx in CHECKS:
        if rx.search(str(text or '')):
            return k
    return None


def note(book, mint, why, px, now, symbol=None):
    """One blocked (or taken: why='taken') coin at its price — once per coin + check per RENOTE_SEC, only with a live price."""
    b = {'open': list((book or {}).get('open') or []), 'done': list((book or {}).get('done') or []), 'tune': dict((book or {}).get('tune') or {}),
         'log': list((book or {}).get('log') or [])}
    if not mint or not why or _f(px) <= 0:
        return b
    if any(c['mint'] == mint and c['why'] == why and now - _f(c['at']) < RENOTE_SEC for c in b['open'][-200:] + b['done'][-200:]):
        return b
    b['open'] = (b['open'] + [{'mint': mint, 'sym': symbol, 'why': why, 'px': _f(px), 'at': round(now, 1), 'peak': 0.0}])[-KEEP_OPEN:]
    return b


def watch(book, prices, now):
    """Every open note: its peak so far (from today's price) and, once due, its grade. A coin with no price waits until GONE_SEC (−100%)."""
    b = {**(book or {}), 'open': [], 'done': list((book or {}).get('done') or [])}
    for c in (book or {}).get('open') or []:
        c = dict(c)
        px = _f((prices or {}).get(c['mint']))
        if px > 0:
            c['peak'] = max(_f(c.get('peak')), (px / c['px'] - 1) * 100)
            c['seenAt'] = round(now, 1)
        age = now - _f(c['at'])
        if age >= JUDGE_SEC and px > 0:
            b['done'].append({**c, 'end': round((px / c['px'] - 1) * 100, 2), 'doneAt': round(now, 1)})
        elif age >= GONE_SEC:
            b['done'].append({**c, 'end': -100.0, 'gone': True, 'doneAt': round(now, 1)})
        else:
            b['open'].append(c)
    b['done'] = b['done'][-KEEP_DONE:]
    return b


def record(book, now=None, since=None):
    """{check: {n, med, ran, dumped}} over the judged notes (last WINDOW_SEC, or since a moment)."""
    by = {}
    for c in (book or {}).get('done') or []:
        if now is not None and now - _f(c.get('doneAt')) > WINDOW_SEC:
            continue
        if since is not None and _f(c.get('at')) < since:
            continue
        by.setdefault(c['why'], []).append(c)
    out = {}
    for k, cs in by.items():
        ends = [max(-100.0, min(300.0, _f(c.get('end')))) for c in cs]
        out[k] = {'n': len(cs), 'med': round(_med(ends), 1), 'ran': round(100 * sum(1 for c in cs if _f(c.get('peak')) >= RAN_PCT) / len(cs)),
                  'dumped': round(100 * sum(1 for c in cs if _f(c.get('end')) <= DUMP_PCT) / len(cs))}
    return out


def _costly(rec, check):
    """The blocked coins beat the taken ones: enough of both, ≥ EDGE better typically, dumping no more (+ slack)."""
    b, t = rec.get(check), rec.get('taken')
    return bool(b and t and b['n'] >= MIN_N and t['n'] >= MIN_N and b['med'] - t['med'] >= EDGE and b['dumped'] <= t['dumped'] + DUMP_SLACK)


def _right(rec, check):
    """The block kept us out of worse coins: blocked typical ≥ EDGE under taken."""
    b, t = rec.get(check), rec.get('taken')
    return bool(b and t and b['n'] >= MIN_N and t['n'] >= MIN_N and t['med'] - b['med'] >= EDGE)


def tune(book, owner_cfg, now):
    """One look at the record → (book with `tune` updated, [changes]). `tune` = {cfg or wait key: {value, at, why, before}}. A key the
    owner set (non-zero / explicitly off) is never touched; a tweak whose taken coins since did ≥ EDGE worse is rolled back first."""
    b = {**(book or {}), 'tune': dict((book or {}).get('tune') or {}), 'log': list((book or {}).get('log') or []), 'hold': dict((book or {}).get('hold') or {})}
    rec = record(b, now)
    oc = owner_cfg or {}
    changes = []
    for key, t in list(b['tune'].items()):   # 1 · roll back a tweak the record no longer backs
        since = record(b, now, since=_f(t.get('at')))
        tk, pre = since.get('taken'), t.get('takenBefore')
        if tk and pre is not None and tk['n'] >= MIN_N and _f(pre) - tk['med'] >= EDGE:
            b['tune'].pop(key)
            b['hold'][key] = round(now, 1)   # a rolled-back tweak rests 2 × STEP_SEC before the record may move it again
            changes.append({'key': key, 'to': t.get('before'), 'why': f"rolled back: coins taken since did {tk['med']:+.1f}% vs {_f(pre):+.1f}% before"})
    for check, (key, steps, word) in GATES.items():   # 2 · a buy-gate limit the owner left on AGENTS, one notch looser when it is costly
        if _f(oc.get(key)) > 0 or key in b['tune'] and now - _f(b['tune'][key].get('at')) < STEP_SEC or (key in b['hold'] and now - _f(b['hold'][key]) < 2 * STEP_SEC):
            continue
        cur = (b['tune'].get(key) or {}).get('value', 0)
        if _costly(rec, check) and cur in steps and steps.index(cur) < len(steps) - 1:
            nxt = steps[steps.index(cur) + 1]
            r, tk = rec[check], rec['taken']
            b['tune'][key] = {'value': nxt, 'at': round(now, 1), 'before': cur, 'takenBefore': tk['med'],
                              'why': f"{word}: {r['n']} blocked coins did {r['med']:+.1f}% vs {tk['med']:+.1f}% taken (dumped {r['dumped']}% vs {tk['dumped']}%)"}
            changes.append({'key': key, 'to': nxt, 'why': b['tune'][key]['why']})
    for check, key in WAITS.items():   # 3 · Trigger's tape waits: OFF when costly, back ON when right again
        if oc.get(key) is False:
            continue
        on = (b['tune'].get(key) or {}).get('value', True)
        if on and _costly(rec, check) and not (key in b['tune'] and now - _f(b['tune'][key].get('at')) < STEP_SEC) and not (key in b['hold'] and now - _f(b['hold'][key]) < 2 * STEP_SEC):
            r, tk = rec[check], rec['taken']
            b['tune'][key] = {'value': False, 'at': round(now, 1), 'before': True, 'takenBefore': tk['med'],
                              'why': f"{check} waits cost: {r['n']} waited coins did {r['med']:+.1f}% vs {tk['med']:+.1f}% taken"}
            changes.append({'key': key, 'to': False, 'why': b['tune'][key]['why']})
        elif not on and _right(rec, check):
            b['tune'].pop(key, None)
            changes.append({'key': key, 'to': True, 'why': f"{check} waits were right again — back on"})
    for c in changes:
        b['log'] = (b['log'] + [{**c, 'at': round(now, 1)}])[-30:]
    return b, changes


def effective(owner_cfg, book):
    """The limits the agents buy by: the owner's own value when set, else the agents' tuned value, else the default (0)."""
    oc, tn = owner_cfg or {}, (book or {}).get('tune') or {}
    out = {}
    for _check, (key, _steps, _w) in GATES.items():
        out[key] = oc.get(key) if _f(oc.get(key)) > 0 else (tn.get(key) or {}).get('value', 0)
    for _check, key in WAITS.items():
        out[key] = False if oc.get(key) is False else (tn.get(key) or {}).get('value', True)
    return out


def view(book, now):
    rec = record(book, now)
    return {'record': rec, 'tune': {k: {kk: v.get(kk) for kk in ('value', 'at', 'why', 'before')} for k, v in ((book or {}).get('tune') or {}).items()},
            'log': ((book or {}).get('log') or [])[-8:], 'open': len((book or {}).get('open') or [])}
