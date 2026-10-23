"""💬 THE STREETS — the Familia city chat (owner, 2026-10-22: "familia chat gotta be LITTY" · P1 #6 robust city chat: presence, mentions, coin
cards, call receipts, mod tools, vital tools). Pure helpers, tested in tests/test_street_chat.py; the service owns the stores.

One room per city (`city-<key>`, the same chat store every room uses). A read returns every line dressed for the street: the poster's family
(tag, colour, crest, whether they are its Don), the coins it called with their receipt (x since the call, peak x), its reactions, and a
`mine` / `atMe` flag — plus who is ON THE BLOCK right now (a memory-only heartbeat per city; invisible wallets never show) and the street's
vitals (lines an hour as a 12-bar spark, families talking, the hottest call). Mod: staff can pull any line and mute; a Don pulls lines of
their OWN family. Nothing here touches money."""
import math
import re

ROOM_RE = re.compile(r'^[a-z0-9-]{2,24}$')
HERE_SEC = 90            # a wallet is on the block for this long after its last heartbeat
HERE_CAP = 400           # wallets remembered per city (memory only)
REACTS = ('🔥', '💀', '🫡', '💰')
PIN_SEC = 3600           # a 📌 pinned call stays on top of the street for an hour
SPARK_BARS, SPARK_SEC = 12, 300   # vitals: 12 bars of 5 minutes = the last hour
SLOW_CHOICES = (0, 10, 30, 60)    # 🐢 slow mode a Don / staff can set on a street (seconds between one wallet's lines)
SLOW_TTL = 1800                   # a slow mode lifts on its own after 30 minutes unless someone sets it again
HIT_MIN, HIT_SEC, HIT_TOP = 1.5, 86400, 8   # 📟 the hits tape: calls on this street that peaked ≥ 1.5x in the last 24 h, best 8
TRAIL_EVERY, TRAIL_CAP = 300, 40  # 📈 a receipt's trail: one x sample per 5 min; past 40 the trail thins to every other point


def room_of(city):
    c = str(city or '').strip().lower()
    return f'city-{c}' if ROOM_RE.match(c) else None


def here_beat(here, city, wallet, now):
    """Note `wallet` on `city`'s block. Prunes stale wallets and keeps each city ≤ HERE_CAP. → the city's map."""
    m = here.setdefault(city, {})
    m[wallet] = now
    for w in [w for w, at in m.items() if now - at > HERE_SEC]:
        m.pop(w, None)
    if len(m) > HERE_CAP:
        for w, _at in sorted(m.items(), key=lambda kv: kv[1])[:len(m) - HERE_CAP]:
            m.pop(w, None)
    return m


def here_list(here, city, now, visible=lambda w: True):
    """Wallets on the block now (newest first), invisible ones left out."""
    return [w for w, at in sorted((here.get(city) or {}).items(), key=lambda kv: -kv[1]) if now - at <= HERE_SEC and visible(w)]


def mentions_me(text, handles):
    """True when the line @-mentions any of the viewer's handles."""
    hs = {str(h).lower().lstrip('@') for h in handles or () if h}
    return bool(hs) and any(m.lower() in hs for m in re.findall(r'@([A-Za-z0-9_.-]{2,32})', str(text or '')))


def trail_add(c, px, now):
    """📈 Note a call's x at `now` (the 60 s refresh calls this): one sample per TRAIL_EVERY, thinned to every other point past TRAIL_CAP so a
    receipt always draws its whole life in ≤ 40 points. → the trail."""
    if not c.get('priceAtCall') or not px:
        return c.get('trail') or []
    t = c.setdefault('trail', [])
    if t and now - t[-1][0] < TRAIL_EVERY:
        return t
    t.append([int(now), round(px / c['priceAtCall'], 4)])
    if len(t) > TRAIL_CAP:
        c['trail'] = t = t[::2]
    return t


def _receipt(c):
    return {'symbol': c.get('symbol'), 'x': round(c['lastPrice'] / c['priceAtCall'], 3), 'peakX': round(c['peakPrice'] / c['priceAtCall'], 3),
            'mcAtCall': c.get('mcAtCall'), 'pairAddress': c.get('pairAddress'), 'chain': c.get('chain'), 'image': c.get('imageUrl'),
            'trail': [[int(c.get('at') or 0), 1.0]] + [p for p in (c.get('trail') or []) if p[0] > (c.get('at') or 0)]}


def receipts(calls, room):
    """The call store → {messageId: [{symbol, x, peakX, mcAtCall, pairAddress, chain, image, trail}]} for this room only. `trail` starts at the
    call (1x) and carries the refresh samples — the coin card draws it as a mini chart."""
    out = {}
    for c in (calls or {}).values():
        if c.get('room') != room or not c.get('messageId') or not c.get('priceAtCall'):
            continue
        out.setdefault(c['messageId'], []).append(_receipt(c))
    return out


def hits(calls, room, now, fam_of=lambda a: None):
    """📟 The street's hits tape: calls made on this street in the last 24 h that peaked ≥ HIT_MIN, best first (≤ HIT_TOP), each with who
    called it and their family tag / colour. Older than a day or never ran = off the tape."""
    out = []
    for c in (calls or {}).values():
        if c.get('room') != room or not c.get('priceAtCall') or now - float(c.get('at') or 0) > HIT_SEC:
            continue
        r = _receipt(c)
        if r['peakX'] < HIT_MIN:
            continue
        f = fam_of(c.get('callerAddress')) if c.get('callerAddress') else None
        out.append({**{k: r[k] for k in ('symbol', 'x', 'peakX', 'pairAddress', 'chain', 'image')}, 'by': c.get('caller') or 'anon', 'ago': int(now - float(c.get('at') or now)),
                    'fam': {'tag': f.get('tag'), 'color': f.get('color')} if f else None})
    return sorted(out, key=lambda h: -h['peakX'])[:HIT_TOP]


def heat(v, reacts=0):
    """🌡 The street's heat 0–3 (calm · warm · hot · on fire) from its own pulse: lines this hour, reactions on the last lines, and a call that
    has run ≥ 2x. The drawn street reads it (rain, neon, lit windows), so a busy street LOOKS busy."""
    n = (v or {}).get('hour', 0) + reacts // 3
    lvl = 0 if n < 3 else 1 if n < 12 else 2 if n < 40 else 3
    return min(3, lvl + (1 if ((v or {}).get('hot') or {}).get('peakX', 0) >= 2 else 0))


def slow_view(slow, now):
    """🐢 The street's slow mode → {sec, by, left} while it holds (it lifts after SLOW_TTL), else None."""
    if not slow or not slow.get('sec') or now - float(slow.get('at') or 0) > SLOW_TTL:
        return None
    return {'sec': int(slow['sec']), 'by': slow.get('by'), 'left': int(SLOW_TTL - (now - float(slow['at'])))}


def slow_wait(slow, last_at, now, exempt=False):
    """Seconds a wallet still has to wait before its next line on a slowed street (0 = post now). Staff and Dons are exempt."""
    v = slow_view(slow, now)
    if exempt or not v or not last_at:
        return 0
    return max(0, math.ceil(v['sec'] - (now - last_at)))


def dress(msgs, fam_of, calls_by_msg, reacts, viewer=None, handles=(), linked=()):
    """Raw room lines → the street view. `fam_of(address)` → {id, tag, color, badge, don} | None (the service caches it per family)."""
    mine = set(linked or ()) | ({viewer} if viewer else set())
    out = []
    for m in msgs or []:
        r = (reacts or {}).get(m.get('id')) or {}
        out.append({'id': m.get('id'), 'ts': m.get('ts'), 'text': m.get('text'), 'name': m.get('username') or m.get('handle') or 'anon', 'handle': m.get('handle'),
                    'address': m.get('identity') or m.get('address'), 'tier': m.get('tier', 0), 'official': bool(m.get('official')), 'system': bool(m.get('system')),
                    'parentId': m.get('parentId'), 'fam': fam_of(m.get('address')) if m.get('address') else None, 'calls': calls_by_msg.get(m.get('id')) or [],
                    'coins': [{'symbol': t.get('symbol'), 'pairAddress': t.get('pairAddress'), 'chain': t.get('chainId'), 'image': ((t.get('pair') or {}).get('info') or {}).get('imageUrl'),
                               'mc': (t.get('pair') or {}).get('marketCap') or (t.get('pair') or {}).get('fdv')} for t in (m.get('tokens') or [])[:3] if t.get('pairAddress')],
                    'reacts': {e: {'n': len(v), 'mine': bool(mine & set(v))} for e, v in r.items() if v and e in REACTS},
                    'mine': bool(m.get('address') in mine or m.get('identity') in mine), 'atMe': mentions_me(m.get('text'), handles)})
    return out


def vitals(lines, now_ms):
    """The street's pulse from its own lines: a 12-bar spark of the last hour, lines in the hour, families talking, the hottest receipt."""
    bars = [0] * SPARK_BARS
    fams, hour = set(), 0
    for l in lines:
        age = (now_ms - (l.get('ts') or 0)) / 1000
        if 0 <= age < SPARK_BARS * SPARK_SEC:
            bars[SPARK_BARS - 1 - int(age // SPARK_SEC)] += 1
            hour += 1
            if l.get('fam'):
                fams.add(l['fam'].get('tag'))
    hot = max(((c, l) for l in lines for c in l.get('calls') or []), key=lambda cl: cl[0].get('peakX') or 0, default=None)
    return {'spark': bars, 'hour': hour, 'families': sorted(f for f in fams if f), 'hot': {'symbol': hot[0]['symbol'], 'peakX': hot[0]['peakX'], 'x': hot[0]['x'], 'by': hot[1]['name'],
                                                                                          'fam': (hot[1].get('fam') or {}).get('tag')} if hot and (hot[0].get('peakX') or 0) > 1 else None}


def can_pull(viewer_staff, viewer_crew_id, viewer_is_don, line_crew_id):
    """Who may pull a line off the street: staff any line; a Don the lines of their own family."""
    return bool(viewer_staff or (viewer_is_don and viewer_crew_id and viewer_crew_id == line_crew_id))


def pin_view(pin, lines, now):
    """The street's 📌 pin → the pinned line (dressed) + who pinned it + seconds left, or None (expired / the line is gone)."""
    if not pin or now - float(pin.get('at') or 0) > PIN_SEC:
        return None
    line = next((l for l in lines or [] if l.get('id') == pin.get('id')), None)
    return {**line, 'pinnedBy': pin.get('by'), 'left': int(PIN_SEC - (now - float(pin['at'])))} if line else None


def can_pin(viewer_staff, viewer_is_don):
    """Who may pin a line on a street: staff, or any family's Don (the last pin wins; it lasts an hour)."""
    return bool(viewer_staff or viewer_is_don)
