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
        raise ValueError('Family names are 3–20 letters, numbers, spaces, dots, dashes or underscores.')
    return s


def clean_tag(s):
    t = str(s or '').strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{2,4}', t):
        raise ValueError('A family tag is 2–4 letters or numbers.')
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
        raise ValueError('You are already in a family — leave it first.')
    name, tag = clean_name(name), clean_tag(tag)
    for c in store['crews'].values():
        if c['name'].lower() == name.lower():
            raise ValueError('That family name is taken.')
        if c['tag'] == tag:
            raise ValueError('That tag is taken.')
    return name, tag


def sig_used(store, sig):
    return sig in (store.get('sigs') or [])


def create(store, owner, name, tag, now, paid=None):
    _norm(store)
    if owner in store['by']:
        raise ValueError('You are already in a family — leave it first.')
    name, tag = clean_name(name), clean_tag(tag)
    for c in store['crews'].values():
        if c['name'].lower() == name.lower():
            raise ValueError('That family name is taken.')
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
        raise ValueError('You are not in a family.')
    if crew['owner'] != wallet:
        raise ValueError('Only the family head can add seats.')
    if crew.get('seats', BASE_SEATS) + PACK_SEATS > MAX_SEATS:
        raise ValueError(f'A family holds at most {MAX_SEATS} seats.')
    crew['seats'] = crew.get('seats', BASE_SEATS) + PACK_SEATS
    if paid:
        crew.setdefault('paid', []).append(paid)
        if paid.get('sig'):
            store['sigs'] = (store.get('sigs') or [])[-500:] + [paid['sig']]
    return crew


def join(store, wallet, code, now=None):
    _norm(store)
    if wallet in store['by']:
        raise ValueError('You are already in a family — leave it first.')
    crew = find_by_code(store, code)
    if not crew:
        raise ValueError('That invite code does not match a family.')
    if len(crew['members']) >= crew.get('seats', BASE_SEATS):
        raise ValueError(f"That family is full ({crew.get('seats', BASE_SEATS)} seats) — its owner can add 5 more for ${PACK_USD:g}.")
    crew['members'].append(wallet); store['by'][wallet] = crew['id']
    if now:
        crew.setdefault('joined', {})[wallet] = now   # 🔴 the live feed says "a new member joined" (never who)
    return crew


def leave(store, wallet):
    """→ the crew it left ({} if it was disbanded with its last member). The owner leaving hands the crew to the longest-standing member."""
    _norm(store)
    cid = store['by'].pop(wallet, None)
    crew = store['crews'].get(cid)
    if not crew:
        raise ValueError('You are not in a family.')
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


def board(store, pieces_by_wallet, now, cfg=None, staff_of=None):
    """→ ranked crews first (best weekly % result), unranked after. `pieces_by_wallet` = {wallet: [closed track_record pieces]}."""
    _norm(store)
    rows = []
    for c in store['crews'].values():
        ps = [p for m in c['members'] for p in pieces_by_wallet.get(m, []) if now - p['at'] <= WEEK]
        active = len({m for m in c['members'] if any(now - p['at'] <= WEEK for p in pieces_by_wallet.get(m, []))})
        s = stats(ps)
        ranked = len(c['members']) >= MIN_MEMBERS and s['trades'] >= MIN_TRADES and s['pct'] is not None
        rows.append({'id': c['id'], 'name': c['name'], 'tag': c['tag'], 'members': len(c['members']), 'seats': c.get('seats', BASE_SEATS), 'active': active, 'ranked': ranked, **s,
                     'launch': (c.get('launch') or {}).get('symbol') or None, 'bounties': sum(1 for b in c.get('bounties') or [] if b.get('state') == 'open'),
                     'badge': badge_view(c, store.get('awards'), cfg, bool(staff_of and staff_of(c.get('owner')))),
                     'warW': int(c.get('warWins') or 0), 'warL': int(c.get('warLosses') or 0), 'chest': int(c['chest']) if c.get('chest') is not None else 500})
    return sorted(rows, key=lambda r: (not r['ranked'], -(r['pct'] if r['pct'] is not None else -999), -r['members']))


# ---- 🔐 PASSCODE · 🎯 BOUNTIES · 💬 BOARD · 🚀 LAUNCH (owner, 2026-10-19: "create a code or generate a secure encrypted passcode with
# bounty, discussion boards, and crew launch") — all points / words only: a crew still shares no money and nobody signs for anyone. ----
import hashlib
import hmac

CODE_RE = r'[A-Za-z0-9_\-]{6,24}'
POST_MAX, POSTS_KEPT, BOUNTIES_KEPT = 500, 200, 40
BOUNTY_MAX = 1000          # crew points a bounty may pay (points, never money)


def _hash(code, salt):
    return hashlib.sha256((salt + str(code)).encode()).hexdigest()


def set_code(store, wallet, code=None):
    """The OWNER sets the crew's join code: their own (6–24 letters / numbers / - _) or, with none, a generated secure passcode (16 chars). Stored only as a
    salted SHA-256 — the plain code is returned ONCE here and never shown again. → (crew, plain code)."""
    _norm(store)
    crew = crew_of(store, wallet)
    if not crew or crew['owner'] != wallet:
        raise ValueError('Only the family head can set the code.')
    plain = str(code or '').strip() or secrets.token_urlsafe(12)[:16]
    if not re.fullmatch(CODE_RE, plain):
        raise ValueError('A family code is 6–24 letters, numbers, - or _.')
    for c in store['crews'].values():
        if c is not crew and (c.get('code') == plain or (c.get('codeHash') and hmac.compare_digest(c['codeHash'], _hash(plain, c.get('salt', ''))))):
            raise ValueError('That code is taken — pick another or generate one.')
    salt = secrets.token_hex(8)
    crew.update(codeHash=_hash(plain, salt), salt=salt, codeTail=plain[-2:])
    crew.pop('code', None)
    return crew, plain


def code_ok(crew, code):
    code = str(code or '').strip()
    if not code:
        return False
    if crew.get('codeHash'):
        return hmac.compare_digest(crew['codeHash'], _hash(code, crew.get('salt', '')))
    return crew.get('code') == code


def find_by_code(store, code):
    _norm(store)
    return next((c for c in store['crews'].values() if code_ok(c, code)), None)


def _member(store, wallet):
    crew = crew_of(store, wallet)
    if not crew:
        raise ValueError('You are not in a family.')
    return crew


def _clean_text(s, n=POST_MAX):
    t = ' '.join(str(s or '').replace('\x00', '').split())
    if not t:
        raise ValueError('Write something first.')
    return t[:n]


def post(store, wallet, text, now, parent=None):
    """💬 A post on the crew board (members only; ≤ 500 chars; a reply names its parent post). Newest 200 kept."""
    crew = _member(store, wallet)
    posts = crew.setdefault('posts', [])
    if parent and not any(p['id'] == parent for p in posts):
        raise ValueError('That post is gone.')
    p = {'id': secrets.token_hex(4), 'by': wallet, 'text': _clean_text(text), 'at': now, **({'parent': parent} if parent else {})}
    posts.append(p)
    crew['posts'] = posts[-POSTS_KEPT:]
    return p


def bounty_add(store, wallet, title, reward, now, mint=None):
    """🎯 The OWNER posts a bounty: a task + crew points it pays (1–1000). Points only."""
    crew = _member(store, wallet)
    if crew['owner'] != wallet:
        raise ValueError('Only the family head posts bounties.')
    r = int(float(reward or 0))
    if not 1 <= r <= BOUNTY_MAX:
        raise ValueError(f'A bounty pays 1–{BOUNTY_MAX} family points.')
    b = {'id': secrets.token_hex(4), 'title': _clean_text(title, 120), 'reward': r, 'at': now, 'state': 'open', **({'mint': str(mint)[:60]} if mint else {})}
    crew['bounties'] = (crew.get('bounties') or [])[-(BOUNTIES_KEPT - 1):] + [b]
    return b


def bounty_claim(store, wallet, bid, proof, now):
    """A member claims an open bounty with a line of proof (a tx, a link, a word); the owner then pays or reopens it."""
    crew = _member(store, wallet)
    b = next((x for x in crew.get('bounties') or [] if x['id'] == bid), None)
    if not b or b['state'] != 'open':
        raise ValueError('That bounty is not open.')
    b.update(state='claimed', by=wallet, proof=_clean_text(proof, 200), claimedAt=now)
    return b


def bounty_settle(store, wallet, bid, pay, now):
    """The OWNER pays a claimed bounty (the claimer's crew points += reward) or reopens it."""
    crew = _member(store, wallet)
    if crew['owner'] != wallet:
        raise ValueError('Only the family head settles bounties.')
    b = next((x for x in crew.get('bounties') or [] if x['id'] == bid), None)
    if not b or b['state'] != 'claimed':
        raise ValueError('That bounty has no claim to settle.')
    if pay:
        pts = crew.setdefault('points', {})
        pts[b['by']] = int(pts.get(b['by'], 0)) + b['reward']
        b.update(state='paid', paidAt=now)
    else:
        b.update(state='open'); [b.pop(k, None) for k in ('by', 'proof', 'claimedAt')]
    return b


def launch(store, wallet, mint, symbol, note, now):
    """🚀 The OWNER pins the crew's launch — the coin the crew is behind (its live numbers are drawn by the page). None clears it."""
    crew = _member(store, wallet)
    if crew['owner'] != wallet:
        raise ValueError('Only the family head pins the launch.')
    if not mint:
        crew.pop('launch', None)
        return None
    if not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,48}', str(mint)):
        raise ValueError('Paste the coin\'s mint address (CA).')
    crew['launch'] = {'mint': mint, 'symbol': str(symbol or '')[:16], 'note': str(note or '')[:160], 'at': now}
    return crew['launch']


def events(store, now, limit=40, since=7 * 86400):
    """🔴 LA FAMILIA LIVE (owner, 2026-10-19: "more live animations, vitals and social events"): what every family DID, newest first — founded,
    member joined, badge forged, bounty posted / claimed / paid, launch pinned, week crowned. Family names + public facts only: never a wallet,
    never a board post (those are the family's own)."""
    _norm(store)
    out = []
    for c in store['crews'].values():
        f = {'fam': c['tag'], 'name': c['name'], 'id': c['id']}
        if c.get('created'):
            out.append({**f, 'kind': 'founded', 'at': c['created'], 'text': f"{c['name']} was founded"})
        for _w, t in (c.get('joined') or {}).items():
            out.append({**f, 'kind': 'joined', 'at': t, 'text': f"a new member joined {c['name']}"})
        if (c.get('badge') or {}).get('at'):
            out.append({**f, 'kind': 'badge', 'at': c['badge']['at'], 'text': f"{c['name']} forged its badge" + (f" — “{c['badge'].get('motto')}”" if c['badge'].get('motto') else '')})
        for b in c.get('bounties') or []:
            out.append({**f, 'kind': 'bounty', 'at': b.get('at'), 'text': f"🎯 {b.get('title')} — {b.get('reward')} pts", 'pts': b.get('reward')})
            if b.get('claimedAt'):
                out.append({**f, 'kind': 'claimed', 'at': b['claimedAt'], 'text': f"a member claimed “{b.get('title')}”"})
            if b.get('paidAt'):
                out.append({**f, 'kind': 'paid', 'at': b['paidAt'], 'text': f"{b.get('reward')} pts paid for “{b.get('title')}”", 'pts': b.get('reward')})
        if (c.get('launch') or {}).get('at'):
            out.append({**f, 'kind': 'launch', 'at': c['launch']['at'], 'text': f"{c['name']} is behind ${c['launch'].get('symbol') or '?'}", 'mint': c['launch'].get('mint')})
    names = {c['id']: c for c in store['crews'].values()}
    for a in store.get('awards') or []:
        top = (a.get('top') or [])[:1]
        c = names.get((top[0] if top else {}).get('id'))
        if c and a.get('at'):
            out.append({'fam': c['tag'], 'name': c['name'], 'id': c['id'], 'kind': 'crown', 'at': a['at'], 'text': f"👑 {c['name']} took the week"})
    for w in store.get('wars') or []:   # ⚔ every war's public moves (call-out, accepted, raises, the bell, the result)
        c = names.get(w.get('a')) or {}
        for t, line in (w.get('log') or [])[-6:]:
            out.append({'fam': c.get('tag', '?'), 'name': c.get('name', ''), 'id': w['id'], 'kind': 'war', 'at': t, 'text': line})
    out = [e for e in out if e.get('at') and now - float(e['at']) <= since]
    return sorted(out, key=lambda e: -float(e['at']))[:limit]


def vitals(store, now):
    """The live numbers on top of the families page."""
    _norm(store)
    cs = list(store['crews'].values())
    wk = now - 7 * 86400
    return {'families': len(cs), 'members': sum(len(c.get('members') or []) for c in cs),
            'openBounties': sum(1 for c in cs for b in c.get('bounties') or [] if b.get('state') == 'open'),
            'ptsWeek': sum(int(b.get('reward') or 0) for c in cs for b in c.get('bounties') or [] if b.get('state') == 'paid' and float(b.get('paidAt') or 0) >= wk),
            'joinedWeek': sum(1 for c in cs for t in (c.get('joined') or {}).values() if t >= wk), 'launches': sum(1 for c in cs if c.get('launch'))}


# ---- 🌹 LA FAMILIA BADGE (owner, 2026-10-19: "users build 1 Family badge that represents their crew / family; rank unlocks things to show on the
# badge — true wiring + tracking + configs for the creator wallet"). Each part of the badge is free OR unlocked by a TRACKED family number,
# recomputed every read (never stored as "unlocked"): members, podium weeks + crowns from the weekly awards, the best place ever, bounty points
# paid. The creator tunes every unlock line and the restyle cost in HQ (fees.crews.unlocks / badgeUsd). One badge per family; the first build
# is free, every restyle after costs `badgeUsd` in SOL (verified on-chain by the service, like the family itself). ----
METRICS = {'members': 'members', 'podiums': 'weeks in the top 3', 'crowns': 'weeks at #1', 'best': 'best weekly place (1 = #1)', 'points': 'bounty points paid', 'wars': 'family wars won'}
PARTS = {   # part → {option: (label, unlock metric or None, min)} — min for 'best' means "place ≤ min"
    'emblem': {'rose': ('🌹 Rose', None, 0), 'skull': ('💀 Skull', None, 0), 'snake': ('🐍 Viper', None, 0), 'dice': ('🎲 Dice', None, 0),
               'gun': ('🔫 Piece', 'members', 3), 'hat': ('🎩 Don\'s hat', 'members', 5), 'scorp': ('🦂 Scorpion', 'podiums', 1),
               'dragon': ('🐉 Dragon', 'podiums', 3), 'crown': ('👑 Crown', 'crowns', 1), 'diamond': ('💎 Diamond', 'points', 1000),
               'sword': ('⚔ Crossed blades', 'wars', 1), 'wolf': ('🐺 Wolf', 'wars', 3), 'lion': ('🦁 Lion', 'wars', 10)},
    'frame': {'iron': ('Iron', None, 0), 'silver': ('Silver', 'members', 5), 'gold': ('Gold', 'podiums', 1), 'blood': ('Blood oath', 'crowns', 1),
              'holo': ('Holo', 'points', 500), 'black': ('Black card', 'best', 1), 'warlord': ('Warlord', 'wars', 5)},
    'fx': {'none': ('None', None, 0), 'smoke': ('Cigar smoke', 'members', 3), 'embers': ('Embers', 'podiums', 1), 'lightning': ('Lightning', 'crowns', 1),
           'rain': ('Money rain', 'points', 2000), 'gunsmoke': ('Gunsmoke', 'wars', 2)},
}
COLORS = ('#15d16a', '#ffd36b', '#ff4d6d', '#9b5cff', '#6fd3ff', '#ffffff', '#ff9f45', '#111111')
BADGE_USD = 2.0
MOTTO_MAX = 24


def family_metrics(crew, awards, staff=False):
    """The tracked numbers every unlock reads. `awards` = crews.json awards [{week, top: [{id}]}] written by the weekly season tick."""
    pod = [i for a in awards or [] for i, r in enumerate((a.get('top') or [])[:3]) if r.get('id') == crew.get('id')]
    return {'members': len(crew.get('members') or []), 'podiums': len(pod), 'crowns': sum(1 for i in pod if i == 0),
            'best': (min(pod) + 1) if pod else None, 'points': int(sum(int(v) for v in (crew.get('points') or {}).values())), 'wars': int(crew.get('warWins') or 0),
            **({'staff': True} if staff else {})}   # a creator / HQ wallet heads it → every part is open (the creator never waits on its own unlock lines)


def unlock_rule(part, opt, cfg=None):
    """(metric, min) for one option — the creator's HQ override first (fees.crews.unlocks['part.opt'] = {metric, min}), else the default."""
    ov = ((cfg or {}).get('unlocks') or {}).get(f'{part}.{opt}')
    if isinstance(ov, dict) and (ov.get('metric') in METRICS or ov.get('metric') in (None, '')):
        return (ov.get('metric') or None), float(ov.get('min') or 0)
    _, m, n = PARTS[part][opt]
    return m, float(n)


def is_unlocked(metric, need, met):
    if not metric or (met or {}).get('staff'):
        return True
    v = (met or {}).get(metric)
    if v is None:
        return False
    return v <= need if metric == 'best' else v >= need


def catalog(met, cfg=None):
    """Every part's options with locked / unlocked + what's missing in words (the builder draws this; the server enforces it)."""
    out = {}
    for part, opts in PARTS.items():
        rows = []
        for opt, (label, _m, _n) in opts.items():
            m, n = unlock_rule(part, opt, cfg)
            ok = is_unlocked(m, n, met)
            have = (met or {}).get(m) if m else None
            rows.append({'key': opt, 'label': label, 'ok': ok, 'metric': m, 'min': n,
                         'need': None if ok or not m else (f"reach #{int(n)} in a week" if m == 'best' else f"{int(n)} {METRICS[m]} (now {int(have or 0)})")})
        out[part] = rows
    return out


def clean_badge(raw, met, cfg=None):
    """A badge as saved: every part must be a known option the family has UNLOCKED, colors from the palette, a short clean motto."""
    raw = raw or {}
    b = {}
    for part, opts in PARTS.items():
        v = str(raw.get(part) or next(iter(opts)))
        if v not in opts:
            raise ValueError(f'Unknown {part}.')
        m, n = unlock_rule(part, v, cfg)
        if not is_unlocked(m, n, met):
            raise ValueError(f"{opts[v][0]} is locked — needs {int(n)} {METRICS[m]}." if m != 'best' else f"{opts[v][0]} is locked — reach #{int(n)} in a week.")
        b[part] = v
    for k in ('c1', 'c2'):
        c = str(raw.get(k) or COLORS[0 if k == 'c1' else 1]).lower()
        if c not in COLORS:
            raise ValueError('Pick colors from the palette.')
        b[k] = c
    motto = ' '.join(str(raw.get('motto') or '').split())[:MOTTO_MAX]
    if motto and not re.fullmatch(r"[\w .,'!?&\-]+", motto):
        raise ValueError('The motto takes letters, numbers and simple punctuation.')
    b['motto'] = motto
    return b


def set_badge(store, wallet, raw, awards, now, cfg=None, paid=None, staff=False):
    """The family OWNER builds / restyles its ONE badge. → crew. A restyle after the first build needs `paid` (the service verifies the SOL)."""
    crew = _member(store, wallet)
    if crew['owner'] != wallet:
        raise ValueError('Only the family head builds the badge.')
    b = clean_badge(raw, family_metrics(crew, awards, staff), cfg)
    if crew.get('badge') and paid is None:
        raise ValueError('Restyling the badge needs its payment.')
    crew['badge'] = {**b, 'at': now, 'v': int((crew.get('badge') or {}).get('v', 0)) + 1}
    if paid and paid.get('sig'):
        crew.setdefault('paid', []).append({**paid, 'kind': 'badge'})
        store['sigs'] = (store.get('sigs') or [])[-500:] + [paid['sig']]
    return crew


def badge_view(crew, awards, cfg=None, staff=False):
    """What every page draws: the badge (re-checked: a part whose unlock was raised later falls back to the default) + the rank chips."""
    met = family_metrics(crew, awards, staff)
    raw = dict(crew.get('badge') or {})
    for part, opts in PARTS.items():
        v = raw.get(part)
        if v not in opts or not is_unlocked(*unlock_rule(part, v, cfg), met):
            raw[part] = next(iter(opts))
    return {**raw, 'tag': crew.get('tag'), 'name': crew.get('name'), 'set': bool(crew.get('badge')), 'ranks': met}


# ✉ INVITES (owner, 2026-10-20: "creator wallet can add members, users invite their members and members accept"): any member invites a wallet
# that is not in a family; the invited wallet sees it and accepts (a seat must be free then) or declines. The creator / HQ wallet may add a wallet
# straight into ITS OWN family (no accept step). Invites expire after a week; ≤ INVITES_MAX pending per family; a wallet holds ≤ 10 invites.
INVITE_SEC = 7 * 86400
INVITES_MAX = 25


def _live_invites(store, now):
    inv = store.setdefault('invites', {})
    for w in list(inv):
        inv[w] = [x for x in inv[w] if now - x.get('at', 0) < INVITE_SEC and x.get('cid') in store.get('crews', {})]
        if not inv[w]:
            inv.pop(w)
    return inv


def invite(store, by, to, now):
    _norm(store)
    crew = crew_of(store, by)
    if not crew:
        raise ValueError('Join or start a family before inviting.')
    to = (to or '').strip()
    if not (32 <= len(to) <= 44) or to == by:
        raise ValueError('Paste the wallet address you want to invite.')
    if to in store['by']:
        raise ValueError('That wallet is already in a family.')
    inv = _live_invites(store, now)
    if sum(1 for xs in inv.values() for x in xs if x['cid'] == crew['id']) >= INVITES_MAX:
        raise ValueError(f'Your family has {INVITES_MAX} invites waiting — let some answer first.')
    mine = inv.setdefault(to, [])
    if any(x['cid'] == crew['id'] for x in mine):
        raise ValueError('That wallet already has an invite from your family.')
    if len(mine) >= 10:
        raise ValueError('That wallet has too many invites waiting.')
    mine.append({'cid': crew['id'], 'by': by, 'at': now})
    return crew


def accept(store, wallet, cid, now):
    _norm(store)
    inv = _live_invites(store, now)
    if not any(x['cid'] == cid for x in inv.get(wallet, [])):
        raise ValueError('No invite from that family is waiting for you.')
    if wallet in store['by']:
        raise ValueError('You are already in a family — leave it first.')
    crew = store['crews'][cid]
    if len(crew['members']) >= crew.get('seats', BASE_SEATS):
        raise ValueError('That family is full right now — ask its head to add seats.')
    crew['members'].append(wallet); store['by'][wallet] = cid
    crew.setdefault('joined', {})[wallet] = now
    inv.pop(wallet, None)
    return crew


def decline(store, wallet, cid, now):
    inv = _live_invites(store, now)
    inv[wallet] = [x for x in inv.get(wallet, []) if x['cid'] != cid]
    if not inv[wallet]:
        inv.pop(wallet)


def add_direct(store, by, to, now):
    """The creator / HQ wallet adds a wallet straight into its own family (the caller checks staff)."""
    _norm(store)
    crew = crew_of(store, by)
    if not crew:
        raise ValueError('Start a family first.')
    to = (to or '').strip()
    if not (32 <= len(to) <= 44):
        raise ValueError('Paste the wallet address to add.')
    if to in store['by']:
        raise ValueError('That wallet is already in a family.')
    if len(crew['members']) >= crew.get('seats', BASE_SEATS):
        crew['seats'] = min(MAX_SEATS, crew.get('seats', BASE_SEATS) + PACK_SEATS)
    crew['members'].append(to); store['by'][to] = crew['id']
    crew.setdefault('joined', {})[to] = now
    _live_invites(store, now).pop(to, None)
    return crew


def invites_for(store, wallet, now):
    out = []
    for x in _live_invites(store, now).get(wallet, []):
        c = store['crews'][x['cid']]
        out.append({'cid': c['id'], 'name': c['name'], 'tag': c['tag'], 'members': len(c['members']), 'seats': c.get('seats', BASE_SEATS),
                    'by': x['by'][:4] + '…' + x['by'][-4:], 'at': x['at'], 'expires': x['at'] + INVITE_SEC})
    return out


def sent_by(store, crew, now):
    return [{'to': w[:4] + '…' + w[-4:], 'at': x['at']} for w, xs in _live_invites(store, now).items() for x in xs if x['cid'] == crew['id']]
