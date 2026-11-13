"""⚖ LEGAL-1 (owner 2026-11-13: "nothing truly needs a lawyer — research how these sites do it"). Pure, tested; reputation_service feeds it.

What peer sites do (research 2026-11-13: Jupiter terms, Jupiter Lock / Mobile, pump.fun terms, Drift docs):
  • The site is an INTERFACE; the user signs every transaction and keeps their keys.
  • On first use the user STATES: 18+ (age of majority where they live), not a sanctioned / prohibited person, not in a restricted
    territory, and won't use a VPN to get around that. pump.fun asks for an explicit "I'm over 18" click.
  • One list blocked everywhere (comprehensively sanctioned places) + a per-product list (Jupiter Lock / Mobile: the US; pump.fun: the UK
    after the FCA warning). We copy that shape: `everywhere` + `features[feature].blocked`, all switched by the owner in HQ.
  • Privacy: export on request; delete profile/social data on request; KEEP money receipts, security logs and proof of consent
    (the law lets every peer keep those), and on-chain data can never be deleted by anyone.
"""
import re
import time

VERSION = '2026-11-13'          # bump ONLY when the Terms / Risk / Privacy text materially changes → every wallet is asked once again
MIN_AGE = 18

# ISO-3166 alpha-2. Comprehensively sanctioned (US OFAC programs; the list every peer blocks). Crimea / DNR / LNR are regions, not
# countries — a country header can't see them, so the user's own statement covers them (exactly how the peers word it).
SANCTIONED = ['CU', 'IR', 'KP', 'SY']

# Every feature the owner can close per country. Empty lists = open everywhere except SANCTIONED (owner flips them in HQ).
FEATURES = {
    'site':    'The whole site',
    'swap':    'Swaps (Jupiter route, user-signed)',
    'perps':   'Perps + leverage (Jupiter Perps / Lend)',
    'agents':  'Agents that trade on their own (auto wallets)',
    'launch':  'Launching coins',
    'games':   'Points, raffles, prizes and games',
    'brokers': 'Broker links (stocks via SnapTrade)',
}

COUNTRY_RE = re.compile(r'^[A-Z]{2}$')


def default_cfg():
    return {'version': VERSION, 'minAge': MIN_AGE, 'everywhere': list(SANCTIONED),
            'features': {k: {'blocked': [], 'ageGate': True} for k in FEATURES}, 'requireAccept': True}


def _codes(v):
    out = []
    for c in (v or []):
        c = str(c or '').strip().upper()
        if COUNTRY_RE.match(c) and c not in out:
            out.append(c)
    return out[:250]


def clean_cfg(body, prev=None):
    """Owner edits from HQ. Unknown features / bad codes are dropped; the sanctioned list can be added to, never emptied (the law)."""
    base = prev or default_cfg()
    body = body or {}
    every = _codes(body.get('everywhere', base.get('everywhere')))
    for c in SANCTIONED:
        if c not in every:
            every.insert(0, c)
    feats = {}
    for k in FEATURES:
        src = (body.get('features') or {}).get(k) or (base.get('features') or {}).get(k) or {}
        feats[k] = {'blocked': _codes(src.get('blocked')), 'ageGate': bool(src.get('ageGate', True))}
    try:
        age = int(body.get('minAge', base.get('minAge', MIN_AGE)))
    except (TypeError, ValueError):
        age = MIN_AGE
    return {'version': VERSION, 'minAge': max(MIN_AGE, min(age, 25)), 'everywhere': every, 'features': feats,
            'requireAccept': bool(body.get('requireAccept', base.get('requireAccept', True)))}


def country_of(headers):
    """The visitor's country when a CDN in front of us says so (Cloudflare / Vercel / CloudFront). None today on the bare Mac."""
    for h in ('cf-ipcountry', 'x-vercel-ip-country', 'cloudfront-viewer-country'):
        c = str((headers or {}).get(h) or '').strip().upper()
        if COUNTRY_RE.match(c) and c not in ('XX', 'T1'):   # XX = unknown, T1 = Tor (Cloudflare)
            return c
    return None


def gate(cfg, feature, country, accepted=None):
    """→ {'ok': bool, 'why': str}. `country` = the CDN's country, else the one the wallet stated when it accepted."""
    cfg = cfg or default_cfg()
    c = (country or (accepted or {}).get('country') or '').upper() or None
    if c and c in (cfg.get('everywhere') or []):
        return {'ok': False, 'why': f'FEELESS is not available in {c}.'}
    for f in ('site', feature):
        if c and c in ((cfg.get('features') or {}).get(f) or {}).get('blocked', []):
            return {'ok': False, 'why': f"{FEATURES.get(f, f)} {'is' if f == 'site' else 'are'} closed in {c}."}
    feat = (cfg.get('features') or {}).get(feature) or {}
    if feature != 'site' and feat.get('ageGate', True) and cfg.get('requireAccept', True) and not (accepted or {}).get('adult'):
        return {'ok': False, 'why': f"Confirm you're {cfg.get('minAge', MIN_AGE)}+ and accept the terms first."}
    return {'ok': True, 'why': ''}


# 🚪 EXITS ARE NEVER HELD (reduce-only, like the peers): a wallet whose country the owner closes later can always take its money out.
EXIT_MINTS = ('So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')   # a sell back into SOL / USDC
PERPS_EXITS = ('decrease-position', 'create-tpsl', 'cancel-tpsl', 'update-tpsl')   # a TP / SL only ever closes


def hold(s, feature, wallet, country=None):
    """⚖ The server's own check before a money route builds or sends (LEGAL-1 d): the same gate the browser runs, on the wallet's stored
    acceptance (its stated country counts here: the server reads its own record). → '' = go on, else the words to refuse with. Pure."""
    st = status(s, wallet) if wallet else {'accepted': False, 'row': None}
    row = st['row'] if st['accepted'] else None
    seen = country if country and country not in ('XX', 'T1') else None
    g = gate(s.get('cfg'), feature, seen, row)
    if g['ok'] and seen and row:   # both count: a header a caller can set never hides the country the wallet itself stated
        g = gate(s.get('cfg'), feature, None, row)
    return '' if g['ok'] else g['why']


def new_state():
    return {'accept': {}, 'cfg': default_cfg(), 'requests': []}


def accept(s, wallet, version, country, adult, not_restricted, ip_country=None, now=None):
    """Record one wallet's acceptance of THIS version. Refuses a stale version, a missing 18+ / not-restricted statement, or a blocked
    country (stated or seen) — the same three statements every peer asks for."""
    if version != VERSION:
        raise ValueError('These terms changed — reload the page and read the new version.')
    if not adult:
        raise ValueError(f"You must be {s['cfg'].get('minAge', MIN_AGE)} or older to use FEELESS.")
    if not not_restricted:
        raise ValueError("You must confirm you're not a sanctioned person and not in a restricted place.")
    c = str(country or '').strip().upper()
    if not COUNTRY_RE.match(c):
        raise ValueError('Pick the country you live in.')
    for where in (c, ip_country):
        if where and where in (s['cfg'].get('everywhere') or []):
            raise ValueError(f'FEELESS is not available in {where}.')
    row = {'v': VERSION, 'at': float(now or time.time()), 'country': c, 'adult': True, 'notRestricted': True,
           **({'seen': ip_country} if ip_country else {})}
    hist = (s['accept'].get(wallet) or {}).get('history') or []
    prev = s['accept'].get(wallet)
    if prev and prev.get('v') != VERSION:
        hist = (hist + [{k: prev.get(k) for k in ('v', 'at', 'country')}])[-10:]
    s['accept'][wallet] = {**row, 'history': hist}
    return s['accept'][wallet]


def status(s, wallet):
    row = (s.get('accept') or {}).get(wallet)
    return {'version': VERSION, 'accepted': bool(row and row.get('v') == VERSION), 'row': row}


# 🗂 The privacy plan per store (reputation_service fills each name with the wallet's rows). DELETE = personal / social, removed on
# request. KEEP = what the law lets (and money needs) us keep, each with the reason shown to the user.
DELETE = {
    'profile': 'your profile (name, bio, picture, links)',
    'follows': 'who you follow',
    'notifications': 'your notification inbox',
    'push': 'your phone push subscriptions',
    'dmPrefs': 'your message settings',
    'identities': 'linked social accounts',
    'dms': 'direct messages you sent',
    'chat': 'chat messages you posted',
    'sessions': 'your signed-in chat sessions (you are signed out)',
}
KEEP = {
    'consent': 'your acceptance of the terms — proof of consent we must keep',
    'receipts': 'trade receipts and fee records — money records we must keep',
    'points': 'points, rounds and rewards ledgers — tied to payouts',
    'security': 'security logs (blocks, reports) — kept to stop abuse',
    'onchain': 'everything on-chain — public, and nobody can delete it',
}
SECRET_KEYS = {'sec', 'secret', 'token', 'key', 'apiKey', 'api_key', 'password', 'seed', 'privateKey', 'endpoint', 'keys', 'auth', 'p256dh', 'session', 'sessions', 'signature', 'sig_'}


def scrub(v, depth=0):
    """A copy with every secret-looking field removed — an export never carries a token, sealed secret or push key."""
    if depth > 8:
        return None
    if isinstance(v, dict):
        return {k: scrub(x, depth + 1) for k, x in v.items() if k not in SECRET_KEYS}
    if isinstance(v, list):
        return [scrub(x, depth + 1) for x in v[:5000]]
    return v


def export_bundle(wallet, parts, now=None):
    """parts = {store name: the wallet's rows}. → one JSON-ready bundle (what we hold, scrubbed) + the plan for a delete."""
    return {'wallet': wallet, 'exportedAt': float(now or time.time()), 'termsVersion': VERSION,
            'data': {k: scrub(v) for k, v in (parts or {}).items() if v not in (None, [], {})},
            'onDelete': {'removed': DELETE, 'kept': KEEP}}


def note_request(s, wallet, kind, counts, now=None):
    """A short audit row per export / delete (counts only — never the data)."""
    s.setdefault('requests', []).append({'wallet': wallet, 'kind': kind, 'at': float(now or time.time()),
                                         'counts': {k: int(v) for k, v in (counts or {}).items()}})
    s['requests'] = s['requests'][-500:]


def view(s):
    acc = s.get('accept') or {}
    cur = [r for r in acc.values() if r.get('v') == VERSION]
    by = {}
    for r in cur:
        by[r.get('country') or '?'] = by.get(r.get('country') or '?', 0) + 1
    return {'version': VERSION, 'cfg': s.get('cfg') or default_cfg(), 'features': FEATURES, 'sanctioned': SANCTIONED,
            'accepted': len(cur), 'stale': len(acc) - len(cur), 'byCountry': sorted(by.items(), key=lambda x: -x[1])[:30],
            'requests': list(reversed((s.get('requests') or [])[-40:]))}
