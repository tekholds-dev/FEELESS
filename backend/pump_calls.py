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
                      'lead': {k: lead.get(k) for k in ('id', 'user', 'x', 'verified', 'avatar', 'calls', 'atMc', 'mult', 'maxMult', 'thesis', 'at', 'views', 'likes', 'heldUsd', 'pnlPct')}})
    coins.sort(key=lambda c: (-c['heat'], -c['callers'], -c['views']))
    tops = []
    ents = top.get('entries') if isinstance(top, dict) else None
    for i, e in enumerate(ents if isinstance(ents, list) else []):
        r = call_row(e)
        if r:
            known = by.get(r['mint'], [{}])[0]
            tops.append({**r, 'rank': int(_f(e.get('rank'))) or i + 1, 'symbol': known.get('symbol'), 'logo': known.get('logo')})
    return {'coins': coins[:COINS_MAX], 'top': tops[:TOP_MAX], 'latest': sorted(calls, key=lambda r: -r['at'])[:LATEST_MAX], 'n': len(calls)}


def summary(coin):
    """The few numbers a list row / quick look carries for a called coin (row field `pc`)."""
    c = coin or {}
    if not c.get('mint'):
        return None
    lead = c.get('lead') or {}
    return {'calls': c.get('calls'), 'callers': c.get('callers'), 'verified': c.get('verified'), 'views': c.get('views'), 'heat': c.get('heat'),
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
