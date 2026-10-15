"""🎓 YOUR LESSONS AS RULES (owner, 2026-10-13: "I've been teaching AI and agents about fake candles / narratives — I don't think it's wired in
a way it can be used or tweaked"). Pure + tested (`tests/test_taught_rules.py`).

A teaching typed as text only ever reached the MODEL's prompt ("stop buying fake candles" was even split into ticker words: fake, stop,
buying). These are the same lessons as RULES the agents run on every coin, each with a mode the owner picks:
  off · 👀 flag (shown on the coin + graded, changes nothing) · ⬇ rank down (the coin drops in the agents' order) · ✋ skip (the agents never
  buy it; the owner's own picks still can).
Every coin a rule hits is graded 30 min later on the desk's own price (coach.grade_note), so the screen says whether the lesson is right.
A rule is never an order, a size or a sell.
"""
from functools import lru_cache
import re

RULES = {
    'fake candles': {'icon': '🕯', 'label': 'Fake candles', 'what': 'a straight run of green candles with no red — painted / botted, it dumps when the bot stops',
                     'knob': ('run', (5, 6, 8, 10, 12, 15), 8, 'green candles in a row')},
    'same narrative': {'icon': '🔁', 'label': 'Same narrative again', 'what': 'its theme / name is already on the card or was traded in the last few hours',
                       'knob': ('hours', (1, 3, 6, 12, 24), 6, 'hours back')},
    'copycat': {'icon': '🪞', 'label': 'Copycat', 'what': 'a copy of a ticker wave running today, not the original', 'knob': None},
    'clone': {'icon': '🧬', 'label': 'Clone ticker', 'what': 'the SAME ticker as a coin the card traded lately, or a copy of a bigger coin with that ticker on the board (5 different $MrBeast in one day)',
              'knob': ('hours', (168, 336, 720), 720, 'hours back')},
}
MODES = ('off', 'flag', 'rank', 'skip')
MODE_WORDS = {'off': 'off', 'flag': '👀 flag only', 'rank': '⬇ rank down', 'skip': '✋ skip'}
STRENGTH = {'soft': -6.0, 'normal': -12.0, 'hard': -20.0}
DEFAULT = {'fake candles': {'mode': 'rank', 'strength': 'normal', 'run': 8},
           'same narrative': {'mode': 'rank', 'strength': 'normal', 'hours': 6},
           'copycat': {'mode': 'flag', 'strength': 'normal'},
           'clone': {'mode': 'skip', 'strength': 'hard', 'hours': 720}}
LOCKED = {'clone': 'skip', 'copycat': 'skip'}   # 🧬 owner, 2026-10-15: "STOP AGENTS FROM BUYING COPYCATS PERIOD" — these two can't be switched below ✋ skip
STOP = {'the', 'and', 'coin', 'token', 'official', 'sol', 'solana', 'pump', 'fun', 'inu', 'new', 'real', 'meme', 'of', 'on', 'in', 'a', 'to', 'for'}


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def clean(cfg):
    """The owner's settings → every rule with a valid mode / strength / knob (unknown keys dropped, bad values = the default)."""
    src = cfg if isinstance(cfg, dict) else {}
    out = {}
    for k, base in DEFAULT.items():
        x = src.get(k) if isinstance(src.get(k), dict) else {}
        r = dict(base)
        if x.get('mode') in MODES:
            r['mode'] = x['mode']
        if x.get('strength') in STRENGTH:
            r['strength'] = x['strength']
        kn = RULES[k]['knob']
        if kn and x.get(kn[0]) is not None and int(_f(x.get(kn[0]), -1)) in kn[1]:
            r[kn[0]] = int(_f(x[kn[0]]))
        if k in LOCKED:
            r['mode'] = LOCKED[k]
        out[k] = r
    return out


def patch(cfg, key, change):
    """One rule changed by the owner's tap → the whole cleaned set. Raises on an unknown rule."""
    if key not in RULES:
        raise ValueError('unknown rule')
    cur = clean(cfg)
    ch = dict(change) if isinstance(change, dict) else {}
    kn = RULES[key]['knob']
    for k in list(ch):
        if k in ('run', 'hours') and not (kn and k == kn[0] and int(_f(ch[k], -1)) in kn[1]):
            ch.pop(k)   # not one of this rule's options → the old value stays
    return clean({**cur, key: {**cur[key], **ch}})


def fake_candles(chart, run=8):
    """'N green candles in a row, no red' from the chart read the desk already holds (real candles only; a tape is closes and is
    never judged). Short newborn charts: every candle so far green (≥ 5). → reason or None."""
    ch = chart or {}
    f = ch.get('f') if isinstance(ch.get('f'), dict) else ch
    if not f or f.get('ohlc') is False:
        return None
    up, n = int(_f(f.get('up'))), int(_f(f.get('n')))
    seq = str(f.get('seq') or '')
    if up >= run and 'R' not in seq[-min(len(seq), run):]:
        wick = f.get('loWick')
        return f"{up} green candles in a row, no red{' · no lower wicks' if wick is not None and _f(wick) < 0.08 else ''}"
    e = f.get('early') or {}
    en, eg = int(_f(e.get('n'))), int(_f(e.get('green')))
    if en >= 5 and eg >= en:
        return f"all {en} candles since launch green"
    if 0 < n <= run + 2 and n >= 5 and up >= n:
        return f"all {n} candles since launch green"
    return None


@lru_cache(maxsize=65536)   # 🧈 pure + hot: the clone rule compares every candidate with 30 days of trades each pass (41% of the loop, 2026-10-15)
def themes(symbol, name=None):
    """What a coin is 'about': its narrative class (🤖 AI, 🐕 dog …), its name words (≥ 4 letters) and its ticker stem (first 4)."""
    out = set()
    try:
        import trench_mind as _tm
        k, _l = _tm.narrative({'symbol': symbol, 'name': name})
        if k:
            out.add(f'narr:{k}')
    except Exception:
        pass
    sym = re.sub(r'[^a-z0-9]', '', str(symbol or '').lower())
    if len(sym) >= 4:
        out.add(sym[:4])
    for w in re.findall(r'[a-z]{4,}', f"{name or ''} {symbol or ''}".lower()):
        if w not in STOP:
            out.add(w)
    return frozenset(out)


def recent(held, closed, now, hours):
    """[(symbol, name, where)] the card holds now + coins that left it in the last `hours` (archive positions: sym + closedAt)."""
    out = [(h.get('symbol') or h.get('sym'), h.get('name'), 'on the card') for h in held or []]
    for p in closed or []:
        if now - _f(p.get('closedAt')) <= hours * 3600:
            out.append((p.get('sym'), None, 'traded'))
    return out


def same_narrative(row, seen, mint_self=None):
    t = themes(row.get('symbol'), row.get('name'))
    if not t:
        return None
    for sym, name, where in seen or []:
        if not sym or str(sym).lower() == str(row.get('symbol') or '').lower():
            continue
        both = t & themes(sym, name)
        if both:
            w = sorted(both, key=lambda x: (x.startswith('narr:'), -len(x)))[0]
            w = w.replace('narr:', '') + ' narrative' if w.startswith('narr:') else f'"{w}"'
            return f"same {w} as ${sym} ({where})"
    return None


@lru_cache(maxsize=65536)   # 🧈 pure + hot: the clone rule compares every candidate with 30 days of trades each pass (41% of the loop, 2026-10-15)
def tick(sym):
    return re.sub(r'[^a-z0-9]', '', str(sym or '').lower())


ROMAN = {'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'}


@lru_cache(maxsize=65536)   # 🧈 pure + hot: the clone rule compares every candidate with 30 days of trades each pass (41% of the loop, 2026-10-15)
def sequel(sym):
    """A ticker that is letters + a number / roman numeral ("GTA 6", "GT IV", "PEPE2") → (letters, number) else None."""
    raw = re.sub(r'[^a-z0-9 ]', '', str(sym or '').lower()).strip()
    m = re.match(r'^([a-z]{2,})\s+([ivx]{1,4})$', raw) or re.match(r'^([a-z]{2,}?)\s*(\d{1,3})$', raw)   # a roman numeral needs a space ("GT IV"): "AIX" is not "AI 10"
    if not m:
        return None
    n = ROMAN.get(m.group(2), m.group(2))
    return (m.group(1), n) if n.isdigit() else None


@lru_cache(maxsize=65536)   # 🧈 pure + hot: the clone rule compares every candidate with 30 days of trades each pass (41% of the loop, 2026-10-15)
def family(a, b):
    """Two tickers of one family: the same, one the start of the other (≥ 4 letters: SPACEXAI ↔ SPACEX), or two SEQUELS whose letters start
    alike (GTA 6 ↔ GT IV ↔ GTA5: 'gt' / 'gta'). Plain 2–3 letter tickers never match each other by prefix."""
    ta, tb = tick(a), tick(b)
    if not ta or not tb:
        return False
    if ta == tb or (min(len(ta), len(tb)) >= 4 and (ta.startswith(tb) or tb.startswith(ta))):
        return True
    sa, sb = sequel(a), sequel(b)
    if sa and sb:
        return sa[0].startswith(sb[0]) or sb[0].startswith(sa[0])
    base = lambda t: re.sub(r'[^a-z]', '', t)
    s_, plain = (sa, tb) if sa else (sb, ta) if sb else (None, None)   # "GTA" ↔ "GTA6": a plain ticker vs its numbered sequel (it bought $GTA after $GTA6)
    return bool(s_ and len(base(plain)) >= 2 and plain == base(plain) and (s_[0].startswith(plain) or plain.startswith(s_[0])))


def clone(row, traded=None, board=None):
    """Same ticker FAMILY as a coin the card traded (different mint), or another coin on the board of this family with a bigger cap."""
    t = tick(row.get('symbol'))
    if len(t) < 2:
        return None
    same = lambda a: family(a, row.get('symbol'))   # "SPACEXAI" is a clone of "SPACEX", "COCACOLA" of "COCA COLA", "GT IV" of "GTA 6"
    for sym, mint in traded or []:
        if tick(sym)[:2] != t[:2]:   # 🧈 every family match shares its first two letters — skip the rest cheaply
            continue
        if same(sym) and mint != row.get('mint'):
            return f"same ticker as a ${sym} the card already traded (a different coin)"
    cap = _f(row.get('cap') or (row.get('vitals') or {}).get('mcap'))
    for o in board or []:
        if o.get('mint') != row.get('mint') and tick(o.get('symbol'))[:2] == t[:2] and same(o.get('symbol')) and _f(o.get('cap') or (o.get('vitals') or {}).get('mcap')) > cap:
            return f"a copy — a bigger ${o.get('symbol')} with this ticker is on the board"
    return None


def hits(row, rules, seen=None, traded=None, board=None):
    """{rule: reason} for every rule that is NOT off and matches this coin."""
    r = row or {}
    out = {}
    for k, cfg in clean(rules).items():
        if cfg['mode'] == 'off':
            continue
        why = None
        if k == 'fake candles':
            why = fake_candles(r.get('chart'), cfg.get('run', 8))
        elif k == 'same narrative':
            why = same_narrative(r, seen)
        elif k == 'copycat' and r.get('waveRole') == 'copy':
            why = 'copy of a ticker wave running today'
        elif k == 'clone':
            why = clone(r, traded, board)
        if why:
            out[k] = why
    return out


WIRE = {'fake candles': r'fake\s*candle|painted|green candles|all green|no red|botted chart',
        'same narrative': r'same\s*(name|narr|narrative|theme|meta)|keep buying the same',
        'clone': r'(\d+(st|nd|rd|th)?\s*time|again and again|same (coin|ticker)|clone)',
        'copycat': r'(stop|avoid|no|skip|never)\b[\w\s]{0,12}(copy\s*cats?|clones?|knock\s*offs?)'}   # "copycats are in-and-out trades" is not an avoid


def from_text(text):
    """The rules a lesson's words name ('stop buying fake candles' → fake candles) — so a teaching switches its rule on."""
    t = str(text or '').lower()
    return [k for k, rx in WIRE.items() if re.search(rx, t)]


def pens(rules):
    """{rule: points} the kernel ranks a matching coin down by (rank AND skip — a skipped coin also sorts last)."""
    return {k: STRENGTH[c['strength']] for k, c in clean(rules).items() if c['mode'] in ('rank', 'skip')}


def flagged(rules):
    """Every rule that is graded (anything not off)."""
    return [k for k, c in clean(rules).items() if c['mode'] != 'off']


def skips(rules, taught_by_mint):
    """Mints the agents must not buy: they hit a rule in ✋ skip mode."""
    sk = {k for k, c in clean(rules).items() if c['mode'] == 'skip'}
    return {m for m, h in (taught_by_mint or {}).items() if sk & set(h or {})}


def view(rules, grades=None, counts=None, examples=None):
    """One row per rule for the page: what it catches (plain words), its mode, strength, knob, how many coins it hits NOW and its record."""
    out = []
    for k, c in clean(rules).items():
        meta = RULES[k]
        kn = meta['knob']
        g = (grades or {}).get(k) or {}
        out.append({'key': k, 'icon': meta['icon'], 'label': meta['label'], 'what': meta['what'], 'mode': c['mode'], 'strength': c['strength'],
                    'knob': {'key': kn[0], 'options': list(kn[1]), 'value': c.get(kn[0], kn[2]), 'word': kn[3]} if kn else None,
                    **({'now': int(counts[k])} if (counts or {}).get(k) else {}), **({'examples': list(examples[k])[:3]} if (examples or {}).get(k) else {}),
                    **({'record': {'n': g['n'], 'med': g.get('med'), 'up': g.get('up', 0), 'verdict': g.get('verdict') or 'open'}} if g.get('n') else {})})
    return {'rules': out}   # mode / strength words live on the page (VitalBoard.RuleCard)
