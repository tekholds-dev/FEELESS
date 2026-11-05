"""🔑 RECOVERY KEY + 12 WORDS (owner 2026-11-04): if an owner loses their wallet they sign in with a new one and enter either. We only ever keep a slow one-way hash, so nobody here can read them, and either can be rotated at any time.
The words use the standard BIP39 list and checksum but are not a wallet seed: they control this agent's ownership, never hold or move money. Pure, tested."""
import hashlib
import hmac
import secrets
from pathlib import Path

WORDS = (Path(__file__).parent / 'bip39_english.txt').read_text().split()
ALPHABET = '23456789ABCDEFGHJKMNPQRSTVWXYZ'
MAX_TRIES, LOCK_S = 5, 3600.0
HOLD_S = 72 * 3600   # after a recovery its wallet cannot pay out for 3 days: a stolen phrase cannot empty it at once, and the real owner has time to act
KINDS = ('key', 'phrase')


def new_key():
    c = ''.join(secrets.choice(ALPHABET) for _ in range(32))
    return '-'.join(c[i:i + 4] for i in range(0, 32, 4))


def new_phrase():
    """12 words from 128 random bits, BIP39 checksum included, so a typo is caught before a try is spent."""
    ent = secrets.token_bytes(16)
    bits = int.from_bytes(ent, 'big') << 4 | hashlib.sha256(ent).digest()[0] >> 4
    return ' '.join(WORDS[(bits >> (11 * (11 - i))) & 2047] for i in range(12))


def phrase_ok(text):
    w = clean('phrase', text).split()
    if len(w) != 12 or any(x not in WORDS for x in w):
        return False
    bits = 0
    for x in w:
        bits = bits << 11 | WORDS.index(x)
    return hashlib.sha256((bits >> 4).to_bytes(16, 'big')).digest()[0] >> 4 == bits & 15


def clean(kind, text):
    if kind == 'phrase':
        return ' '.join(str(text or '').lower().split())
    return ''.join(ch for ch in str(text or '').upper() if ch in ALPHABET)


def kind_of(text):
    return 'phrase' if len(str(text or '').split()) >= 12 else 'key'


def _hash(kind, text, salt):
    return hashlib.scrypt(clean(kind, text).encode(), salt=bytes.fromhex(salt), n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32).hex()


def seal(kind, text, now):
    salt = secrets.token_hex(16)
    return {'salt': salt, 'hash': _hash(kind, text, salt), 'at': round(now)}


def locked(kit, now):
    return now < float((kit or {}).get('lockedUntil') or 0)


def check(kit, text, now):
    """'ok', 'wrong' or 'locked'. Five wrong tries lock both for an hour; a mistyped phrase does not count."""
    if not kit:
        return 'wrong'
    if locked(kit, now):
        return 'locked'
    kind = kind_of(text)
    if kind == 'phrase' and not phrase_ok(text):
        return 'typo'
    rec = kit.get(kind)
    if rec and hmac.compare_digest(_hash(kind, text, rec['salt']), rec['hash']):
        kit['tries'] = 0
        return 'ok'
    kit['tries'] = int(kit.get('tries') or 0) + 1
    if kit['tries'] >= MAX_TRIES:
        kit['tries'], kit['lockedUntil'] = 0, now + LOCK_S
    return 'wrong'


def view(kit, now=0):
    """What the owner sees: that each exists and when it was made. Never the hash."""
    k = kit or {}
    return {x: {'set': bool(k.get(x)), 'at': (k.get(x) or {}).get('at')} for x in KINDS}


def on_hold(cat, now):
    return now < float((cat or {}).get('recoveredAt') or 0) + HOLD_S
