"""👍👎 THE MARKET JUDGES EVERY CALL (owner, 2026-10-16: "like or dislike their decisions … the market decides at 5 min, 1 h, 24 h if they get
a confidence boost — if I dislike OSSY's hold and it moons, it still boosts OSSY").

Pure. A comment (a model's BUY / HOLD / SELL / partner advice, or the owner's own note) can get one vote per voter (owner · lan · local).
At each checkpoint the coin's price move since the comment decides who was RIGHT:
  BUY / HOLD / "hold" advice → right when the coin went up · SELL / "sell" advice → right when it went down (± `FLAT` is a draw).
The AUTHOR earns or loses confidence on the market alone (votes only raise the stakes); each VOTER earns when their 👍 / 👎 agreed with
the market. `confidence(state, who)` → a bounded boost the model reads in its packet — what it earned, never a promise.
"""

CHECKS = (300, 3600, 86400)   # 5 min · 1 h · 24 h
FLAT = 1.0                    # |move| under 1% = a draw (no points)
CAP = 15                      # the boost is bounded: ±15 confidence points
VOTERS = ('owner', 'lan', 'local')
KEEP = 300


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def side_of(action, view=None):
    """+1 = the comment says the coin goes / stays up, −1 = says get out, 0 = no call (WAIT)."""
    a = str(view or action or '').upper()
    return 1 if a in ('BUY', 'HOLD') else -1 if a == 'SELL' else 0


def add(state, key, author, action, mint, px, now, view=None, text=None):
    """Register a comment so it can be voted on and settled (idempotent by key)."""
    st = {'items': {}, **(state or {})}
    items = dict(st['items'])
    if key not in items and mint and _f(px) > 0 and side_of(action, view):
        items[key] = {'author': author, 'side': side_of(action, view), 'mint': mint, 'px': _f(px), 'at': now, 'votes': {}, 'res': {},
                      **({'text': str(text)[:160]} if text else {})}
        if len(items) > KEEP:
            for k in sorted(items, key=lambda k: items[k]['at'])[:len(items) - KEEP]:
                items.pop(k)
    st['items'] = items
    return st


def vote(state, key, voter, v):
    """One vote per voter per comment; v = +1 👍 / −1 👎 / 0 = take it back. A model never votes on its own comment."""
    st = {'items': {}, **(state or {})}
    it = (st['items'] or {}).get(key)
    if not it or voter not in VOTERS or voter == it.get('author'):
        return st, False
    vv = dict(it['votes'])
    if v in (1, -1):
        vv[voter] = int(v)
    else:
        vv.pop(voter, None)
    st['items'] = {**st['items'], key: {**it, 'votes': vv}}
    return st, True


def settle(state, px_of, now):
    """Each comment, at each checkpoint it reached: the move since the comment → author right / wrong / draw, each vote right / wrong."""
    st = {'items': {}, 'score': {}, **(state or {})}
    items, score = dict(st['items']), {k: dict(v) for k, v in (st.get('score') or {}).items()}
    for key, it in items.items():
        due = [c for c in CHECKS if now - it['at'] >= c and str(c) not in it['res']]
        if not due:
            continue
        p = _f(px_of(it['mint']))
        if p <= 0:
            continue
        move = (p / it['px'] - 1) * 100
        res = dict(it['res'])
        for c in due:
            ok = 0 if abs(move) < FLAT else (1 if (move > 0) == (it['side'] > 0) else -1)
            res[str(c)] = {'move': round(move, 1), 'ok': ok}
            stake = 1 + len(it['votes'])   # votes raise the stakes on the author
            a = score.setdefault(it['author'], {'pts': 0, 'n': 0, 'votes': 0, 'voteRight': 0})
            a['pts'] += ok * stake; a['n'] += 1
            for voter, v in it['votes'].items():
                s = score.setdefault(voter, {'pts': 0, 'n': 0, 'votes': 0, 'voteRight': 0})
                if ok:
                    right = (v > 0) == (ok > 0)
                    s['votes'] += 1; s['voteRight'] += 1 if right else 0; s['pts'] += 1 if right else -1
        items[key] = {**it, 'res': res}
    st['items'], st['score'] = items, score
    return st


def confidence(state, who):
    """The bounded confidence boost a model has EARNED from the market's verdicts on its comments and its votes."""
    s = ((state or {}).get('score') or {}).get(who) or {}
    return max(-CAP, min(CAP, int(round(_f(s.get('pts')) / 2))))


def words(state, who):
    """One line the model reads: earned confidence + how its calls and votes did."""
    s = ((state or {}).get('score') or {}).get(who) or {}
    if not s.get('n') and not s.get('votes'):
        return 'no settled calls yet — the market grades every call at 5 min, 1 h and 24 h'
    return (f"confidence {confidence(state, who):+d} earned · {s.get('n', 0)} call checkpoints graded"
            + (f" · your votes {s.get('voteRight', 0)}/{s.get('votes', 0)} right" if s.get('votes') else ''))


def view(state, key, me='owner'):
    """What the page shows under a comment: 👍 / 👎 counts, my vote, each checkpoint's verdict."""
    it = ((state or {}).get('items') or {}).get(key)
    if not it:
        return None
    vv = it.get('votes') or {}
    return {'up': sum(1 for v in vv.values() if v > 0), 'down': sum(1 for v in vv.values() if v < 0), 'mine': vv.get(me, 0),
            'by': {k: v for k, v in vv.items() if k != me}, 'res': [[c, (it['res'].get(str(c)) or {}).get('ok'), (it['res'].get(str(c)) or {}).get('move'),
                     (None if not vv.get(me) or (it['res'].get(str(c)) or {}).get('ok') in (None, 0) else (vv.get(me) > 0) == ((it['res'].get(str(c)) or {}).get('ok') > 0))] for c in CHECKS]}   # 4th = was MY vote right
