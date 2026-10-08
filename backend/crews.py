"""🛡 CREWS (pure): a crew costs $25 in SOL paid to the FEELESS fee wallet and has 5 seats including its owner; +5 seats cost $5 each time. One crew each, an invite code, a members-only-post chat room. The weekly board ranks crews by what their members'
VERIFIED FEELESS trades did over the last 7 days (price result, fees apart; track_record pieces) — never self-reported. A crew ranks once it has ≥ 2
members and ≥ 5 closed trades that week; below that it is listed, unranked. Everyone still signs their own trades: a crew shares nothing financial."""
import re
import secrets

BASE_SEATS, PACK_SEATS, MAX_SEATS = 5, 5, 100      # 5 seats incl. the owner; +5 per pack; a sanity ceiling
CREATE_USD, PACK_USD = 25.0, 5.0                   # paid in SOL to the fee wallet (verified on-chain by the service)
MIN_MEMBERS, MIN_TRADES = 2, 5
WEEK = 7 * 86400


def clean_name(s):
    s = ' '.join(str(s or '').split())
    if not 3 <= len(s) <= 20 or not re.fullmatch(r'[A-Za-z0-9 _.\-]+', s):
        raise ValueError('Crew names are 3–20 letters, numbers, spaces, dots, dashes or underscores.')
    return s


def clean_tag(s):
    t = str(s or '').strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{2,4}', t):
        raise ValueError('A crew tag is 2–4 letters or numbers.')
    return t


def _norm(store):
    store.setdefault('crews', {}); store.setdefault('by', {})
    return store


def crew_of(store, wallet):
    _norm(store)
    return store['crews'].get(store['by'].get(wallet))


def price(kind, cfg=None):
    """USD a crew action costs: 'create' ($25, 5 seats incl. the owner) or 'seats' ($5 for +5). `cfg` = optional {createUsd, packUsd} override."""
    c = cfg or {}
    return float(c.get('createUsd', CREATE_USD)) if kind == 'create' else float(c.get('packUsd', PACK_USD))


def check_new(store, owner, name, tag):
    """Everything create() would refuse, checked BEFORE anyone pays. → (name, tag) cleaned; raises ValueError."""
    _norm(store)
    if owner in store['by']:
        raise ValueError('You are already in a crew — leave it first.')
    name, tag = clean_name(name), clean_tag(tag)
    for c in store['crews'].values():
        if c['name'].lower() == name.lower():
            raise ValueError('That crew name is taken.')
        if c['tag'] == tag:
            raise ValueError('That tag is taken.')
    return name, tag


def sig_used(store, sig):
    return sig in (store.get('sigs') or [])


def create(store, owner, name, tag, now, paid=None):
    _norm(store)
    if owner in store['by']:
        raise ValueError('You are already in a crew — leave it first.')
    name, tag = clean_name(name), clean_tag(tag)
    for c in store['crews'].values():
        if c['name'].lower() == name.lower():
            raise ValueError('That crew name is taken.')
        if c['tag'] == tag:
            raise ValueError('That tag is taken.')
    cid = secrets.token_hex(3)
    crew = {'id': cid, 'name': name, 'tag': tag, 'owner': owner, 'members': [owner], 'seats': BASE_SEATS, 'code': secrets.token_urlsafe(6)[:8], 'created': now, 'paid': [paid] if paid else []}
    store['crews'][cid] = crew; store['by'][owner] = cid
    if paid and paid.get('sig'):
        store['sigs'] = (store.get('sigs') or [])[-500:] + [paid['sig']]            # a payment is never reused
    return crew


def add_seats(store, wallet, paid=None):
    """The OWNER buys +5 seats ($5). → the crew. A payment (`paid` = {sig, usd, at}) is recorded and never reused."""
    _norm(store)
    crew = crew_of(store, wallet)
    if not crew:
        raise ValueError('You are not in a crew.')
    if crew['owner'] != wallet:
        raise ValueError('Only the crew owner can add seats.')
    if crew.get('seats', BASE_SEATS) + PACK_SEATS > MAX_SEATS:
        raise ValueError(f'A crew holds at most {MAX_SEATS} seats.')
    crew['seats'] = crew.get('seats', BASE_SEATS) + PACK_SEATS
    if paid:
        crew.setdefault('paid', []).append(paid)
        if paid.get('sig'):
            store['sigs'] = (store.get('sigs') or [])[-500:] + [paid['sig']]
    return crew


def join(store, wallet, code):
    _norm(store)
    if wallet in store['by']:
        raise ValueError('You are already in a crew — leave it first.')
    crew = next((c for c in store['crews'].values() if c['code'] == str(code or '').strip()), None)
    if not crew:
        raise ValueError('That invite code does not match a crew.')
    if len(crew['members']) >= crew.get('seats', BASE_SEATS):
        raise ValueError(f"That crew is full ({crew.get('seats', BASE_SEATS)} seats) — its owner can add 5 more for ${PACK_USD:g}.")
    crew['members'].append(wallet); store['by'][wallet] = crew['id']
    return crew


def leave(store, wallet):
    """→ the crew it left ({} if it was disbanded with its last member). The owner leaving hands the crew to the longest-standing member."""
    _norm(store)
    cid = store['by'].pop(wallet, None)
    crew = store['crews'].get(cid)
    if not crew:
        raise ValueError('You are not in a crew.')
    crew['members'] = [m for m in crew['members'] if m != wallet]
    if not crew['members']:
        store['crews'].pop(cid, None)
        return {}
    if crew['owner'] == wallet:
        crew['owner'] = crew['members'][0]
    return crew


def stats(pieces):
    n = len(pieces)
    usd, cost = sum(p['usd'] for p in pieces), sum(p['costUsd'] for p in pieces)
    return {'trades': n, 'wonPct': round(100 * sum(1 for p in pieces if p['usd'] > 0) / n) if n else None, 'usd': round(usd, 2),
            'pct': round(100 * usd / cost, 1) if cost > 0 else None}


def board(store, pieces_by_wallet, now):
    """→ ranked crews first (best weekly % result), unranked after. `pieces_by_wallet` = {wallet: [closed track_record pieces]}."""
    _norm(store)
    rows = []
    for c in store['crews'].values():
        ps = [p for m in c['members'] for p in pieces_by_wallet.get(m, []) if now - p['at'] <= WEEK]
        active = len({m for m in c['members'] if any(now - p['at'] <= WEEK for p in pieces_by_wallet.get(m, []))})
        s = stats(ps)
        ranked = len(c['members']) >= MIN_MEMBERS and s['trades'] >= MIN_TRADES and s['pct'] is not None
        rows.append({'id': c['id'], 'name': c['name'], 'tag': c['tag'], 'members': len(c['members']), 'seats': c.get('seats', BASE_SEATS), 'active': active, 'ranked': ranked, **s})
    return sorted(rows, key=lambda r: (not r['ranked'], -(r['pct'] if r['pct'] is not None else -999), -r['members']))
