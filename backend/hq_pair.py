"""📱 SCAN TO SIGN IN TO HQ (owner, 2026-10-21: "create a scan to sign in real quick, like Trust Wallet, so I can connect my Phantom").
The computer asks for a one-time CODE and shows it as a QR; the phone opens the link inside Phantom, signs the normal HQ session message
(`FEELESS HQ\\naddress:…\\nts:…` — a message, never a transaction) and posts it under the code; the computer polls the code and receives
that session ONCE. The service verifies the signature exactly like a normal HQ sign-in before it is stored. Memory only, never on disk.
"""
import secrets

TTL = 180          # a code lives 3 minutes
MAX_OPEN = 20      # at most this many codes waiting at once (oldest dropped)


def new_code(store, now):
    for k in [k for k, v in store.items() if now - v['at'] > TTL]:
        store.pop(k, None)
    while len(store) >= MAX_OPEN:
        store.pop(min(store, key=lambda k: store[k]['at']))
    code = secrets.token_urlsafe(18)
    store[code] = {'at': now, 'session': None}
    return code


def put(store, code, session, now):
    """The phone's signed session lands under its code (already verified by the caller). Raises KeyError for an unknown / expired code."""
    v = store.get(code)
    if not v or now - v['at'] > TTL:
        store.pop(code, None)
        raise KeyError('That QR expired — make a new one on the computer.')
    if v['session']:
        raise KeyError('That QR was already used.')
    v['session'] = session


def take(store, code, now):
    """The computer's poll → 'waiting' | 'expired' | the session (handed over ONCE, then the code is gone)."""
    v = store.get(code)
    if not v or now - v['at'] > TTL:
        store.pop(code, None)
        return {'status': 'expired'}
    if not v['session']:
        return {'status': 'waiting', 'left': int(TTL - (now - v['at']))}
    store.pop(code, None)
    return {'status': 'signed', 'session': v['session']}
