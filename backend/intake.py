"""🕸 ONE DEDUPED LIVE INTAKE — pure, deterministic, tested (`tests/test_intake.py`). No network, no wallet, no order.

Every coin outlet FEELESS already runs feeds ONE registry, per mint: first / last seen, first seen by EACH source, symbol, launchpad,
creation time, and the four stamps of its trip through the office (agent intake · deep review · cleared · seated) plus how its real
seat ended. From that registry come the numbers the owner asked to SEE: new unique mints per cycle (never seen by any source before),
per-source mix, per-source funnel (seen → promoted → deep → cleared → bought → won / lost), and the latencies
source → intake → deep review → clear → seat. Source performance is CONTEXT: nothing here blocks a coin for where it came from.

The outlets (each is an existing FEELESS stream — none is invented here):
  pulse    Pump pulse: the PumpPortal live stream of every Pump launch (on-chain create transactions, pushed as they land)
  migr     Pump migrations: the same stream's graduations / migrations
  open     the launch board (Pump biggest + recently traded, Pump's own trending tab, Jupiter's live rankings + newest, launchpad boards)
  runner   the runner board's candidates (the coins the engine's gates already judged / holder-scanned)
  list:*   the tracked pick lists (Pump trending, movers, volume, live movers, fed runners, narrative leaders, cooling off, proven callers …)
  calls    Pump's own callouts (users calling coins)
  feeders  runners with launches paired to them, and those paired launches
  radar    the FEELESS radar (called coins + users' watchlists) whose pool the board also carries
  held     the coins on the real card
"""

def _f(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    return x if x == x else 0.0

SOURCES = {'pulse': 'Pump pulse (PumpPortal live launches)', 'migr': 'Pump migrations (PumpPortal live)', 'open': 'launch board', 'runner': 'runner board',
           'calls': 'Pump callouts', 'feeders': 'fed runners', 'radar': 'FEELESS radar', 'held': 'the real card'}
FRESH = ('pulse', 'migr')            # the reserved fresh outlets (a newborn never waits behind old volume leaders)
KEEP = 5000                          # registry size (most recently seen kept)
KEEP_SEC = 12 * 3600                 # … and nothing older than this
WINDOW = 6 * 3600                    # the per-source funnel + latency window
STAGES = ('intake', 'deep', 'clear', 'seat')


def label(src):
    return SOURCES.get(src) or (f"list · {src[5:]}" if str(src).startswith('list:') else str(src))


def note(reg, seen, now):
    """Record one pass of every outlet. `seen` = {source: [{mint, symbol?, pad?, born? (unix s)}]}. → (registry, {source: new mints}, new mints)
    A mint is NEW when no source ever saw it before (registry-wide); a mint is new TO A SOURCE when that source first lists it."""
    r = dict(reg or {})
    new_by, new_all = {}, []
    for src, rows in (seen or {}).items():
        for x in rows or []:
            m = (x or {}).get('mint')
            if not m:
                continue
            e = r.get(m)
            if e is None:
                e = {'first': now, 'src': {}}
                new_all.append(m)
            else:
                e = {**e, 'src': dict(e.get('src') or {})}
            if src not in e['src']:
                e['src'][src] = now
                new_by.setdefault(src, []).append(m)
            e['last'] = now
            for k in ('symbol', 'pad'):
                if x.get(k) and not e.get(k):
                    e[k] = x[k]
            if x.get('born') and not e.get('born'):
                e['born'] = _f(x['born'])
            r[m] = e
    if len(r) > KEEP or any(now - _f(v.get('last')) > KEEP_SEC for v in list(r.values())[:50]):
        live = {m: v for m, v in r.items() if now - _f(v.get('last')) <= KEEP_SEC}
        r = dict(sorted(live.items(), key=lambda kv: -_f(kv[1].get('last')))[:KEEP])
    return r, new_by, list(dict.fromkeys(new_all))


def stamp(reg, stage, mints, now):
    """The first time a coin reaches a stage of the office (intake · deep · clear · seat) — set once, never moved."""
    r = dict(reg or {})
    for m in mints or ():
        e = r.get(m)
        if e is not None and not e.get(stage):
            r[m] = {**e, stage: now}
    return r


def outcome(reg, mint, pct, now):
    """How a real seat in this coin ended (% at exit, price result) — the per-source win / loss record."""
    r = dict(reg or {})
    e = r.get(mint)
    if e is not None:
        r[mint] = {**e, 'out': round(_f(pct), 2), 'outAt': now}
    return r


def srcs_of(e):
    """A coin's sources, first finder first."""
    return [k for k, _ in sorted((e or {}).get('src', {}).items(), key=lambda kv: _f(kv[1]))]


def _med(xs):
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    return None if not n else round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 1)


def latency(reg, now, window=WINDOW):
    """Medians (seconds) over coins first seen inside the window: source → intake, intake → deep review, deep → clear, clear → seat,
    and a launch's own birth → our first sight (when the outlet carries the creation time). Counts beside each."""
    es = [e for e in (reg or {}).values() if now - _f(e.get('first')) <= window]
    pair = lambda a, b: [(_f(e[b]) - _f(e[a])) for e in es if e.get(a) and e.get(b) and _f(e[b]) >= _f(e[a])]
    born = [(_f(e['first']) - _f(e['born'])) for e in es if e.get('born') and _f(e['first']) >= _f(e['born'])]
    out = {}
    for k, xs in (('sourceToIntake', pair('first', 'intake')), ('intakeToDeep', pair('intake', 'deep')), ('deepToClear', pair('deep', 'clear')),
                  ('clearToSeat', pair('clear', 'seat')), ('birthToSeen', born)):
        out[k] = {'med': _med(xs), 'n': len(xs)}
    return out


def per_source(reg, now, window=WINDOW):
    """Each outlet's funnel over the window: seen → promoted (reached the agents' desk) → deep reviewed → cleared → bought → won / lost.
    A coin counts for EVERY source that listed it (sources overlap); `firstFinder` = how often this source saw it first."""
    out = {}
    for e in (reg or {}).values():
        if now - _f(e.get('last')) > window:
            continue
        ss = srcs_of(e)
        for i, s in enumerate(ss):
            a = out.setdefault(s, {'seen': 0, 'firstFinder': 0, 'promoted': 0, 'deep': 0, 'cleared': 0, 'bought': 0, 'won': 0, 'lost': 0})
            a['seen'] += 1
            a['firstFinder'] += 1 if i == 0 else 0
            a['promoted'] += 1 if e.get('intake') else 0
            a['deep'] += 1 if e.get('deep') else 0
            a['cleared'] += 1 if e.get('clear') else 0
            a['bought'] += 1 if e.get('seat') else 0
            if e.get('out') is not None:
                a['won' if _f(e['out']) > 0 else 'lost'] += 1
                a.setdefault('_outs', []).append(_f(e['out']))
            if e.get('seat') and _f(e['seat']) >= _f(e.get('first')):
                a.setdefault('_tte', []).append(_f(e['seat']) - _f(e.get('first')))
    for a in out.values():   # 🕵 which outlet deserves priority: win rate · median P/L · rug rate (≤ −50% exits) · time from first seen to our entry
        outs, tte = a.pop('_outs', []), a.pop('_tte', [])
        a['winRate'] = round(100 * a['won'] / (a['won'] + a['lost'])) if a['won'] + a['lost'] else None
        a['medPct'] = _med(outs)
        a['rugRate'] = round(100 * sum(x <= -50 for x in outs) / len(outs)) if outs else None
        a['timeToEntry'] = _med(tte)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]['seen']))


def cycle(reg, seen_now, new_by, new_all, table_mints, prev_table, now):
    """This pass, in counts: unique seen (any outlet), new unique mints (first ever), new per outlet, unique on the desk, desk turnover
    (on the desk now but not last pass) and the desk's source mix (first finder per coin)."""
    t = set(table_mints or ())
    mix = {}
    for m in t:
        s = (srcs_of((reg or {}).get(m)) or ['?'])[0]
        mix[s] = mix.get(s, 0) + 1
    return {'uniqueSeen': len({x.get('mint') for rows in (seen_now or {}).values() for x in rows or () if x.get('mint')}), 'newUnique': len(new_all or ()),
            'newBy': {k: len(v) for k, v in (new_by or {}).items()}, 'desk': len(t), 'deskNew': len(t - set(prev_table or ())),
            'mix': dict(sorted(mix.items(), key=lambda kv: -kv[1]))}
