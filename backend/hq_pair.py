"""📱 SCAN TO SIGN IN TO HQ (owner, 2026-10-21: "create a scan to sign in real quick, like Trust Wallet, so I can connect my Phantom").
The computer asks for a one-time CODE and shows a QR. It uses PHANTOM'S DEEPLINK PROTOCOL (the in-app browser froze on a plain-http
page): the QR opens the Phantom app on CONNECT; Phantom answers to our page on the phone's browser (encrypted to this code's own X25519
key); the service then hands back a SIGN-MESSAGE deeplink for the normal HQ message (`FEELESS HQ\\naddress:…\\nts:…` — a message, never a
transaction); Phantom answers with the signature; the service verifies it exactly like a normal HQ sign-in and the computer receives that
session ONCE. Memory only, never on disk; every code has its own key pair and lives 3 minutes.
"""
import json
import secrets
from urllib.parse import quote

import base58
from nacl.public import Box, PrivateKey, PublicKey

TTL = 180          # a code lives 3 minutes
MAX_OPEN = 20      # at most this many codes waiting at once (oldest dropped)


def new_code(store, now):
    for k in [k for k, v in store.items() if now - v['at'] > TTL]:
        store.pop(k, None)
    while len(store) >= MAX_OPEN:
        store.pop(min(store, key=lambda k: store[k]['at']))
    code = secrets.token_urlsafe(18)
    store[code] = {'at': now, 'session': None, 'sk': bytes(PrivateKey.generate())}
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


# ── Phantom deeplinks (https://docs.phantom.com/phantom-deeplinks) ──────────────────────────────────────────────────────────────────────
PHANTOM = 'https://phantom.app/ul/v1'


def _live(store, code, now):
    v = store.get(code)
    if not v or now - v['at'] > TTL:
        store.pop(code, None)
        raise KeyError('That QR expired — make a new one on the computer.')
    return v


def _pub(v):
    return base58.b58encode(bytes(PrivateKey(v['sk']).public_key)).decode()


def connect_link(store, code, site, now):
    """The QR: Phantom CONNECT, answering to our page on the phone (`site` = this computer on the Wi-Fi)."""
    v = _live(store, code, now)
    back = f"{site}/hq-link?c={code}&s=connect"
    return (f"{PHANTOM}/connect?app_url={quote(site, safe='')}&dapp_encryption_public_key={_pub(v)}&cluster=mainnet-beta"
            f"&redirect_link={quote(back, safe='')}")


def _box(v, phantom_pub):
    return Box(PrivateKey(v['sk']), PublicKey(base58.b58decode(phantom_pub)))


def on_connect(store, code, site, phantom_pub, nonce, data, now, ts=None):
    """Phantom's CONNECT answer → the wallet + the SIGN-MESSAGE deeplink for the HQ message."""
    v = _live(store, code, now)
    box = _box(v, phantom_pub)
    got = json.loads(box.decrypt(base58.b58decode(data), base58.b58decode(nonce)))
    address = str(got['public_key']); ts = int(ts if ts is not None else now)
    msg = f'FEELESS HQ\naddress:{address}\nts:{ts}'
    v.update(phantom=phantom_pub, address=address, ts=ts)
    n2 = secrets.token_bytes(24)
    payload = box.encrypt(json.dumps({'message': base58.b58encode(msg.encode()).decode(), 'session': got['session'], 'display': 'utf8'}).encode(), n2).ciphertext
    back = f"{site}/hq-link?c={code}&s=sign"
    return {'address': address, 'link': (f"{PHANTOM}/signMessage?dapp_encryption_public_key={_pub(v)}&nonce={base58.b58encode(n2).decode()}"
                                         f"&redirect_link={quote(back, safe='')}&payload={base58.b58encode(payload).decode()}")}


def on_signed(store, code, nonce, data, now):
    """Phantom's SIGN-MESSAGE answer → (address, ts, signature) for the caller to verify before `put`."""
    v = _live(store, code, now)
    if not v.get('phantom'):
        raise KeyError('Connect first — scan the QR again.')
    got = json.loads(_box(v, v['phantom']).decrypt(base58.b58decode(data), base58.b58decode(nonce)))
    return v['address'], v['ts'], str(got['signature'])
