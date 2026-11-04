"""🪪 NAMES (owner 2026-11-04): a profile, agent or any other name made on FEELESS can change once every 7 days. Staff any time.
A name shows publicly, so its current text stays readable and searchable. What is sealed: every change is stamped with a keyed signature nobody can forge without the server's key, and past names are kept encrypted."""
import hashlib
import hmac
import json
import time

import cat_keys as _ck

LOCK_S = 7 * 86400
SCOPE = 'names'


def left_s(rec, now=None):
    """Seconds until this record may change again. 0 = it may."""
    at = float((rec or {}).get('at') or 0)
    return max(0, int(at + LOCK_S - (now if now is not None else time.time()))) if at else 0


def wait_line(rec, now=None):
    s = left_s(rec, now); d = s // 86400; h = (s % 86400) // 3600
    return f'Names change once every 7 days. Try again in {d}d {h}h.' if d else f'Names change once every 7 days. Try again in {max(1, h)}h.'


def _key():
    return hashlib.sha256(f'name-stamp:{_ck._master()}'.encode()).digest()


def _sig(owner, name, at):
    return hmac.new(_key(), f'{owner}|{name}|{float(at)}'.encode(), hashlib.sha256).hexdigest()


def stamp(rec, owner, name, now=None):
    """The record after a change: when, a keyed signature, and the past names, sealed."""
    at = now if now is not None else time.time(); rec = rec or {}
    old = []
    if rec.get('past'):
        try:
            old = json.loads(_ck.unseal(rec['past'], SCOPE))
        except Exception:   # noqa: BLE001 — a past list it can't read starts over; the current name still counts
            old = []
    if rec.get('name') is not None:
        old = (old + [{'name': rec.get('name'), 'at': rec.get('at')}])[-20:]
    return {'name': name, 'at': at, 'sig': _sig(owner, name, at), 'past': _ck.seal(json.dumps(old), SCOPE)}


def genuine(rec, owner, name):
    """True when this name is the one the record signed."""
    return bool(rec) and rec.get('name') == name and hmac.compare_digest(str(rec.get('sig') or ''), _sig(owner, name, rec.get('at') or 0))


def past_names(rec):
    if not (rec or {}).get('past'):
        return []
    return json.loads(_ck.unseal(rec['past'], SCOPE))


def check(rec, owner, new, is_staff=False, now=None):
    """(allowed, new record or None, why). The first name ever set is free. No change is no change."""
    new = str(new or '')
    if rec is None and not new:
        return True, None, ''
    if (rec or {}).get('name') == new:
        return True, rec, ''
    if not is_staff and left_s(rec, now) > 0:
        return False, rec, wait_line(rec, now)
    return True, stamp(rec, owner, new, now), ''
