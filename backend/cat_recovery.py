"""🔑 RECOVERY PIN (owner 2026-10-30: "assure account secure and a recovery pin will show next"). An agent answers to the browser that launched it
(`ownerId` in localStorage): clear that browser and the agent is out of reach. The PIN is the way back: 12 random characters shown ONCE, only a
scrypt hash kept on the agent. It re-binds the agent to a new browser; it never moves money (withdrawals still go only to the linked wallet, signed).
Five wrong tries lock that agent's PIN for an hour. Pure, tested (tests/test_cat_recovery.py)."""
import hashlib
import hmac
import secrets

ALPHABET = '23456789ABCDEFGHJKMNPQRSTVWXYZ'   # no 0/O, 1/I/L, U: it gets copied by hand
MAX_TRIES, LOCK_SEC = 5, 3600.0


def new_pin():
    c = ''.join(secrets.choice(ALPHABET) for _ in range(12))
    return f'{c[:4]}-{c[4:8]}-{c[8:]}'


def _clean(pin):
    return ''.join(ch for ch in str(pin or '').upper() if ch in ALPHABET)


def _hash(pin, salt):
    return hashlib.scrypt(_clean(pin).encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1, dklen=32).hex()


def seal(pin):
    salt = secrets.token_hex(16)
    return {'salt': salt, 'hash': _hash(pin, salt), 'tries': 0, 'lockedUntil': 0.0}


def check(rec, pin, now):
    """→ 'ok' | 'wrong' | 'locked'. Counts a wrong try on `rec`; a right one clears the count."""
    if not rec or now < float(rec.get('lockedUntil') or 0):
        return 'locked' if rec else 'wrong'
    if len(_clean(pin)) == 12 and hmac.compare_digest(_hash(pin, rec['salt']), rec['hash']):
        rec['tries'] = 0
        return 'ok'
    rec['tries'] = int(rec.get('tries') or 0) + 1
    if rec['tries'] >= MAX_TRIES:
        rec['tries'], rec['lockedUntil'] = 0, now + LOCK_SEC
    return 'wrong'
