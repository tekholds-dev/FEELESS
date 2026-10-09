"""📣 PUMP CALLOUTS — Pump's OWN callouts, read from the public feeds its site uses (found 2026-10-08 by reading pump.fun's page
scripts; base = the Pump coin index, frontend-api-v3):

  GET /home-feed?pageSize=150&platform=WEB&chain=solana   callouts ranked by Pump (who called, at what cap, the multiple since)
  GET /home-feed/new?pageSize=50&chain=solana&platform=WEB the newest callouts
  GET /pnl-leaderboard/positions?period=daily              today's top callouts by the caller's profit

A callout = a public call a HOLDER makes on a coin (Pump's words). Pure functions, tested with fake rows; the service fetches. These are
other people's calls: shown with the caller, the cap it was called at and the multiple since — a read, never advice, never a promise.
Thesis text is user-written: trimmed, control characters dropped, always rendered as plain text.
"""
import re
from datetime import datetime, timezone

HOME_PATH, HOME_PARAMS = '/home-feed', {'pageSize': 150, 'platform': 'WEB', 'chain': 'solana'}
NEW_PATH, NEW_PARAMS = '/home-feed/new', {'pageSize': 50, 'platform': 'WEB', 'chain': 'solana'}
TOP_PATH, TOP_PARAMS = '/pnl-leaderboard/positions', {'period': 'daily'}
TTL = 60               # the feeds are re-read at most once a minute
THESIS_MAX = 160
COINS_MAX, TOP_MAX, LATEST_MAX = 120, 25, 40
_MINT = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x and abs(x) != float('inf') else d
    except (TypeError, ValueError):
        return d


def _ms(v):
    """An ISO time or a unix number → unix ms (0 = unknown)."""
    if isinstance(v, (int, float)):
        return float(v) * (1000 if v < 1e12 else 1)
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00')).astimezone(timezone.utc).timestamp() * 1000
    except (TypeError, ValueError):
        return 0.0


def _text(v, n=THESIS_MAX):
    s = re.sub(r'[\x00-\x1f\x7f]+', ' ', str(v or '')).strip()
    s = re.sub(r'\s+', ' ', s)
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _img(u):
    u = str(u or '')
    return u if u.startswith('https://') and len(u) < 400 else None


def call_row(pos, mint=None):
    """One callout (a home-feed `position` or a leaderboard entry) → a plain row, or None when it is not a token callout."""
    p = pos if isinstance(pos, dict) else {}
    c = p.get('callout') if isinstance(p.get('callout'), dict) else {}
    mint = mint or p.get('coinMint')
    if not c.get('calloutId') or not _MINT.match(str(mint or '')) or (c.get('assetClass') or 'ASSET_CLASS_TOKEN') != 'ASSET_CLASS_TOKEN':
        return None
    at_mc = _f(c.get('calledOutAtMcap'))
    return {'id': str(c['calloutId']), 'mint': mint, 'user': _text(p.get('userName') or p.get('username') or 'anon', 24), 'x': _text(p.get('xUsername') or '', 24) or None,
            'verified': bool(p.get('isVerified')), 'avatar': _img(p.get('profileImage')), 'calls': int(_f(p.get('totalCallouts'))) or None,
            'atMc': at_mc or None, 'mult': round(_f(c.get('multiple')), 2) or None, 'maxMult': round(_f(c.get('maxMultiplier')), 2) or None,
            'thesis': _text(c.get('thesis')), 'at': _ms(c.get('calloutTimestamp')), 'views': int(_f(c.get('viewCount'))), 'likes': int(_f(c.get('likes'))),
            'replies': int(_f(c.get('replyCount')) + _f(c.get('commentCount'))), 'reposts': int(_f(c.get('repostCount'))),
            'heldUsd': round(_f(p.get('valueUsd')), 2), 'pnlPct': round(_f(p.get('pnlPercentage')), 1) if p.get('pnlPercentage') is not None else None,
            'pnlUsd': round(_f(p.get('pnlUsd')), 2) if p.get('pnlUsd') is not None else None, 'exited': bool(p.get('isExited'))}


def _feed_calls(feed):
    out = []
    for c in ((feed.get('coins') or []) if isinstance(feed, dict) else []):
        if not isinstance(c, dict):
            continue
        r = call_row(c.get('position'), c.get('coinMint'))
        if r and str(c.get('chain') or 'solana') == 'solana':
            r.update(symbol=_text(c.get('symbol'), 16), name=_text(c.get('coinName'), 40), logo=_img(c.get('coinImage')), mcap=_f(c.get('marketCap')) or None)
            out.append(r)
    return out


def heat(n_callers, views, verified, mins):
    """0–100: how loud the room is on this coin — callers, eyes on the calls, verified callers, how recent the last call."""
    fresh = 1.0 if mins <= 10 else 0.7 if mins <= 30 else 0.45 if mins <= 120 else 0.2
    raw = min(1.0, n_callers / 6) * 45 + min(1.0, views / 8000) * 30 + min(1.0, verified / 2) * 10 + fresh * 15
    return int(round(max(0.0, min(100.0, raw))))


def board(home=None, new=None, top=None, now_ms=0.0):
    """→ {'coins': one row per called coin (loudest first), 'top': today's top callouts by profit, 'latest': newest calls, 'n': calls read}."""
    calls, seen = [], set()
    for r in _feed_calls(home) + _feed_calls(new):
        if r['id'] not in seen:
            seen.add(r['id'])
            calls.append(r)
    by = {}
    for r in calls:
        by.setdefault(r['mint'], []).append(r)
    coins = []
    for mint, rs in by.items():
        lead = max(rs, key=lambda r: (r['views'], r['likes'], r['at']))
        callers = {r['user'] for r in rs}
        last = max(r['at'] for r in rs)
        first_mc = min((r['atMc'] for r in rs if r['atMc']), default=None)
        mins = (now_ms - last) / 60000 if now_ms and last else 1e9
        views = sum(r['views'] for r in rs)
        ver = len({r['user'] for r in rs if r['verified']})
        coins.append({'mint': mint, 'symbol': lead.get('symbol'), 'name': lead.get('name'), 'logo': lead.get('logo'), 'mcap': lead.get('mcap'),
                      'calls': len(rs), 'callers': len(callers), 'verified': ver, 'views': views, 'likes': sum(r['likes'] for r in rs),
                      'firstMc': first_mc, 'lastAt': last, 'heldUsd': round(sum(r['heldUsd'] for r in rs), 2),
                      'bestMult': max((r['mult'] for r in rs if r['mult']), default=None), 'heat': heat(len(callers), views, ver, mins),
                      'users': sorted(callers)[:20],
                      'lead': {k: lead.get(k) for k in ('id', 'user', 'x', 'verified', 'avatar', 'calls', 'atMc', 'mult', 'maxMult', 'thesis', 'at', 'views', 'likes', 'heldUsd', 'pnlPct')}})
    coins.sort(key=lambda c: (-c['heat'], -c['callers'], -c['views']))
    tops = []
    ents = top.get('entries') if isinstance(top, dict) else None
    for i, e in enumerate(ents if isinstance(ents, list) else []):
        r = call_row(e)
        if r:
            known = by.get(r['mint'], [{}])[0]
            tops.append({**r, 'rank': int(_f(e.get('rank'))) or i + 1, 'symbol': known.get('symbol'), 'logo': known.get('logo')})
    return {'coins': coins[:COINS_MAX], 'top': tops[:TOP_MAX], 'latest': sorted(calls, key=lambda r: -r['at'])[:LATEST_MAX], 'n': len(calls), 'calls': calls}


def summary(coin):
    """The few numbers a list row / quick look carries for a called coin (row field `pc`)."""
    c = coin or {}
    if not c.get('mint'):
        return None
    lead = c.get('lead') or {}
    return {'pro': c.get('pro') or 0, 'pros': c.get('pros') or [],
            'calls': c.get('calls'), 'callers': c.get('callers'), 'verified': c.get('verified'), 'views': c.get('views'), 'heat': c.get('heat'),
            'firstMc': c.get('firstMc'), 'lastAt': c.get('lastAt'), 'bestMult': c.get('bestMult'), 'heldUsd': c.get('heldUsd'),
            'lead': {k: lead.get(k) for k in ('user', 'x', 'verified', 'atMc', 'mult', 'thesis', 'at', 'views')}}


def label(coin):
    """One line under the ticker: '📣 3 callers · called at $6.7K → 1.9×'."""
    c = coin or {}
    lead = c.get('lead') or {}
    mc = _f(c.get('firstMc'))
    cap = f"${mc / 1e6:.1f}M" if mc >= 1e6 else f"${mc / 1e3:.1f}K" if mc >= 1e3 else f"${mc:.0f}" if mc else None
    parts = [f"📣 {c.get('callers') or 1} caller{'' if (c.get('callers') or 1) == 1 else 's'}"]
    if cap:
        parts.append(f"called at {cap}" + (f" → {lead['mult']}×" if lead.get('mult') else ''))
    return ' · '.join(parts)


def candidate(coin, now_ms=0.0):
    """A called coin → a launch-board candidate (the feed's own filters still decide whether it is listed)."""
    c = coin or {}
    mint = str(c.get('mint') or '')
    if not _MINT.match(mint):
        return None
    pad = 'pump' if mint.endswith('pump') else 'bonk' if mint.endswith('bonk') else 'other'
    return {'mint': mint, 'launchpad': pad, 'symbol': c.get('symbol'), 'name': c.get('name'), 'image': c.get('logo'), 'createdAt': 0.0,
            'marketCap': _f(c.get('mcap')), 'athMarketCap': 0.0, 'replies': 0, 'live': False, 'graduated': False, 'curveProgress': None,
            'socials': 0, 'mover': True, 'pumpCalls': int(_f(c.get('callers'))) or 1, 'platformName': 'Pump callouts', 'url': f'https://pump.fun/coin/{mint}'}


# 🎯 CALLER SCOREBOARD — not every caller is worth the same. Each callout is noted once (who, which coin, the cap it was called at) and
# judged by the multiple Pump itself reports about an hour later (`res`; a call that left the feed before that keeps its last reading).
# A caller is PROVEN with >= PRO_MIN judged calls, a typical (median) result >= PRO_MED× and at least half of them up.
JUDGE_MIN = 60          # minutes after the call before it is judged
PRO_MIN, PRO_MED = 3, 1.2
CALLER_KEEP = 30        # judged calls kept per caller
CALLER_DAYS = 7         # a caller not seen for a week is dropped


def caller_track(state, calls, now_ms):
    """One pass over the calls just read → the updated record {caller: {'seen': ms, 'calls': {id: {mint, at, atMc, mult, res}}}}. Pure."""
    st = {u: {'seen': v.get('seen', 0), 'calls': dict(v.get('calls') or {})} for u, v in (state or {}).items() if isinstance(v, dict)}
    live = set()
    for r in calls or []:
        u, cid = r.get('user'), r.get('id')
        if not u or not cid or not r.get('at') or r.get('mult') is None:
            continue
        live.add(cid)
        rec = st.setdefault(u, {'seen': 0, 'calls': {}})
        rec['seen'] = now_ms
        c = rec['calls'].setdefault(cid, {'mint': r.get('mint'), 'at': r['at'], 'atMc': r.get('atMc')})
        c['mult'] = r['mult']
        if c.get('res') is None and now_ms - r['at'] >= JUDGE_MIN * 60000:
            c['res'] = r['mult']
    for u in list(st):
        rec = st[u]
        for cid, c in rec['calls'].items():   # left the feed before it could be judged: its last reading stands
            if c.get('res') is None and cid not in live and now_ms - _f(c.get('at')) >= JUDGE_MIN * 60000:
                c['res'] = c.get('mult')
        done = sorted((kv for kv in rec['calls'].items() if kv[1].get('res') is not None), key=lambda kv: -_f(kv[1].get('at')))[:CALLER_KEEP]
        rec['calls'] = {**dict(done), **{k: v for k, v in rec['calls'].items() if v.get('res') is None}}
        if now_ms - _f(rec.get('seen')) > CALLER_DAYS * 86400000 or not rec['calls']:
            st.pop(u)
    return st


def caller_board(state):
    """→ {caller: {n, medMult, wonPct, best, proven}} from judged calls only."""
    out = {}
    for u, rec in (state or {}).items():
        rs = sorted(_f(c.get('res')) for c in (rec.get('calls') or {}).values() if c.get('res') is not None)
        if not rs:
            continue
        n = len(rs)
        med = rs[n // 2] if n % 2 else (rs[n // 2 - 1] + rs[n // 2]) / 2
        won = sum(1 for x in rs if x > 1) / n * 100
        out[u] = {'n': n, 'medMult': round(med, 2), 'wonPct': round(won), 'best': round(rs[-1], 2), 'proven': n >= PRO_MIN and med >= PRO_MED and won >= 50}
    return out


def mark_pros(b, callers):
    """Each called coin gets `pro` (how many PROVEN callers are on it) + their names. In place; returns the board."""
    pros = {u for u, v in (callers or {}).items() if v.get('proven')}
    for c in (b or {}).get('coins') or []:
        on = [u for u in c.get('users') or [] if u in pros]
        c['pro'], c['pros'] = len(on), on[:3]
    return b


def leaders(callers, n=15):
    """The scoreboard: proven callers first, then best typical result (>= 2 judged calls)."""
    rows = [{'user': u, **v} for u, v in (callers or {}).items() if v.get('n', 0) >= 2]
    return sorted(rows, key=lambda r: (not r['proven'], -r['medMult'], -r['n']))[:n]


# 🔔 CALL RUSH — several different callers on one coin inside a few minutes, while it is still small
RUSH_N, RUSH_MIN = 3, 10
RUSH_CAPS_K = (0, 50, 100, 250, 1000)   # the owner's alert: off · under $50K · $100K · $250K · $1M


def rush(calls, now_ms, cap_usd=0.0, n=RUSH_N, window_min=RUSH_MIN):
    """→ [{mint, symbol, callers, mcap, firstMc}] for coins with >= n DIFFERENT callers in the last `window_min` minutes and a cap under `cap_usd`."""
    by = {}
    for r in calls or []:
        if r.get('at') and 0 <= now_ms - r['at'] <= window_min * 60000:
            by.setdefault(r['mint'], []).append(r)
    out = []
    for m, rs in by.items():
        who = {r['user'] for r in rs}
        mc = max((_f(r.get('mcap')) for r in rs), default=0.0)
        if len(who) >= n and cap_usd > 0 and 0 < mc <= cap_usd:
            out.append({'mint': m, 'symbol': rs[0].get('symbol'), 'callers': len(who), 'mcap': mc, 'firstMc': min((r['atMc'] for r in rs if r.get('atMc')), default=None)})
    return sorted(out, key=lambda x: -x['callers'])


# 🎯 PRO-CALL ENTRY — get in early on the best new coins by following the callers who have been RIGHT (owner, 2026-10-09: "get in early on
# the best possible new trenches"). Walk-forward on 32K judged calls: callers proven on the first half → their next calls 50% up vs 42%
# for everyone else (median 1.01× vs 1.0×). A small edge, so it rides as a trench TICKET with the card's scalp-the-stake exits.
PRO_ENTRY_MIN = 15      # the call is at most this many minutes old …
PRO_ENTRY_LATE = 1.15   # … and the coin is still within 15% of the cap it was called at (their price, not the pump after)


def pro_entries(calls, callers, open_rows, now_ms, max_min=PRO_ENTRY_MIN, late=PRO_ENTRY_LATE):
    """Fresh calls by PROVEN callers on coins the open trench list marks SAFE, still near the called cap → open rows, best caller first,
    each with `proCall` (who, their record, minutes since the call, cap then vs now). Pure."""
    pros = {u: v for u, v in (callers or {}).items() if v.get('proven')}
    rows = {r.get('mint'): r for r in open_rows or [] if r.get('mint')}
    out, seen = [], set()
    for c in sorted((c for c in calls or [] if c.get('user') in pros), key=lambda c: -_f(c.get('at'))):
        r, m = rows.get(c.get('mint')), c.get('mint')
        mins = (now_ms - _f(c.get('at'))) / 60000
        if m in seen or not r or not r.get('safe') or not r.get('pairAddress') or _f(r.get('price')) <= 0 or not 0 <= mins <= max_min:
            continue
        at_mc, mc = _f(c.get('atMc')), _f(r.get('mcap'))
        if at_mc > 0 and mc > at_mc * late:
            continue   # it already ran past the caller's price
        seen.add(m)
        v = pros[c['user']]
        out.append({**r, 'trenchScore': 200 + _f(v.get('medMult')) * 10, 'proCall': {'user': c['user'], 'medMult': v.get('medMult'), 'wonPct': v.get('wonPct'),
                                                                                      'n': v.get('n'), 'mins': round(mins, 1), 'atMc': at_mc or None, 'mcap': mc or None}})
    return sorted(out, key=lambda r: -_f(r['trenchScore']))
