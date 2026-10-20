"""🛟 SUPPORT HUB (owner, 2026-10-20: "a visual live grid of bugs / reports auto-sorted by importance, community polls where enough votes climb
the ladder of approval, a support button in vital areas, its own huge section"). Pure.
Bugs come from the existing report store (bugs.json); the PUBLIC board shows only a cleaned title, the area, the count, the status and an
importance score — never stack traces, addresses or a security report's text. People +1 a report ("me too") to raise it.
Polls: anyone signed in proposes one (2–5 options); votes climb the LADDER by their own count; only the owner moves one onto the roadmap."""
import re
import time

SEV = {'security': 50, 'bug': 20, 'idea': 10}
STATUS_W = {'open': 1.0, 'fixing': 1.15, 'fixed': 0.15, 'wontfix': 0.1}
LADDER = [(0, 'idea', '💡 IDEA'), (10, 'hot', '🔥 HOT'), (25, 'pick', '🗳 COMMUNITY PICK'), (50, 'review', '🛠 TEAM REVIEW')]
OWNER_STATES = ('roadmap', 'building', 'shipped', 'declined')
POLL_DAY_MAX = 3
Q_LEN, OPT_LEN, OPTS_MAX = 140, 60, 5


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def title_of(b):
    """A report's public title: first line, stack frames / urls / hashes / addresses removed, ≤ 90 chars. Security reports stay hidden."""
    if b.get('kind') == 'security':
        return '🔒 Security report (details kept private)'
    t = str(b.get('text') or '').split('\n')[0]
    t = re.sub(r'\s+·\s+at .*$', '', t)
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'[1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{20,}|[0-9a-f]{12,}', '…', t)
    t = re.sub(r'^\[auto crash\]\s*', '💥 ', t)
    return ' '.join(t.split())[:90] or 'report'


def area_of(b):
    p = str(b.get('page') or '').split('?')[0].strip('/').split('/')
    return (p[1] if len(p) > 1 and p[0] == 'terminal' else p[0]) or 'site'


def importance(b, plus=0, now=None):
    """0–100: severity × how many hit it (log) × how recent × its status, + people saying 'me too'."""
    now = time.time() if now is None else now
    n = max(1, int(_f(b.get('count'), 1)))
    base = SEV.get(b.get('kind'), 20) + (10 if str(b.get('text') or '').startswith('[auto crash]') else 0)
    age = (now - _f(b.get('lastAt') or b.get('at'), now)) / 86400
    rec = 1.0 if age <= 1 else 0.6 if age <= 7 else 0.3
    import math
    v = (base * (1 + math.log2(n)) + 5 * plus) * rec * STATUS_W.get(b.get('status', 'open'), 1.0)
    return round(min(100, v))


def board(bugs, plus, now=None, limit=60):
    """The public grid: one row per report, most important first."""
    out = []
    for b in bugs or []:
        p = len((plus or {}).get(b.get('id'), []))
        out.append({'id': b.get('id'), 'title': title_of(b), 'area': area_of(b), 'kind': b.get('kind') or 'bug', 'count': int(_f(b.get('count'), 1)),
                    'status': b.get('status', 'open'), 'plus': p, 'importance': importance(b, p, now), 'at': b.get('at'), 'lastAt': b.get('lastAt') or b.get('at')})
    return sorted(out, key=lambda r: (r['status'] in ('fixed', 'wontfix'), -r['importance']))[:limit]


def clean_poll(q, options):
    q = ' '.join(str(q or '').split())[:Q_LEN]
    opts = [' '.join(str(o or '').split())[:OPT_LEN] for o in (options or [])]
    opts = [o for i, o in enumerate(opts) if o and o.lower() not in [x.lower() for x in opts[:i]]][:OPTS_MAX]
    if len(q) < 8:
        raise ValueError('Ask a real question (8+ characters).')
    if len(opts) < 2:
        raise ValueError('Give at least 2 different options.')
    return q, opts


def stage(poll):
    """Where a poll stands: the owner's word first, else the ladder rung its own vote count reached."""
    if poll.get('status') in OWNER_STATES:
        return {'key': poll['status'], 'label': {'roadmap': '🗺 ON THE ROADMAP', 'building': '🔨 BUILDING', 'shipped': '✅ SHIPPED', 'declined': '✕ DECLINED'}[poll['status']], 'next': None}
    n = len(poll.get('votes') or {})
    cur = [r for r in LADDER if n >= r[0]][-1]
    nxt = next((r for r in LADDER if r[0] > n), None)
    return {'key': cur[1], 'label': cur[2], 'next': {'at': nxt[0], 'label': nxt[2], 'need': nxt[0] - n} if nxt else None}


def vote(poll, wallet, opt):
    """One wallet, one vote; the same option again takes it back; another option moves it."""
    if not (0 <= int(opt) < len(poll.get('options') or [])):
        raise ValueError('No such option.')
    v = poll.setdefault('votes', {})
    if v.get(wallet) == int(opt):
        v.pop(wallet, None)
    else:
        v[wallet] = int(opt)
    return poll


def poll_view(poll, me=None):
    v = poll.get('votes') or {}
    tally = [sum(1 for x in v.values() if x == i) for i in range(len(poll.get('options') or []))]
    return {'id': poll['id'], 'q': poll['q'], 'options': poll['options'], 'tally': tally, 'votes': len(v), 'mine': v.get(me) if me else None,
            'by': (poll.get('by') or '')[:4] + '…' if poll.get('by') else None, 'at': poll.get('at'), 'stage': stage(poll), 'note': poll.get('note')}


def polls_board(polls, me=None):
    rank = {'review': 3, 'pick': 2, 'hot': 1, 'idea': 0, 'roadmap': 4, 'building': 5, 'shipped': 1, 'declined': -1}
    rows = [poll_view(p, me) for p in polls or []]
    return sorted(rows, key=lambda r: (-rank.get(r['stage']['key'], 0), -r['votes'], -_f(r['at'])))


def can_post(polls, wallet, now=None):
    now = time.time() if now is None else now
    return sum(1 for p in polls or [] if p.get('by') == wallet and now - _f(p.get('at')) < 86400) < POLL_DAY_MAX
