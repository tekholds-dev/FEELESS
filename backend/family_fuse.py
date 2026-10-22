"""⚔ FAMILY FUSE (owner, 2026-10-21: "Family Fuse in the Fuse Arena stadium — two families' Fuse cards (same coin count ±1), paper or MP
(2K min), spectator bids, played live on the pitch"). Pure + tested; the service holds the store, prices and I/O.

· A family's Don / Underboss CHALLENGES another family with one of its cards (a Fuse design or a Fuse card its members built in the Fuse
  tab): PAPER (glory + a win on the ladder) or MP (both banks put up the same stake; the challenger's stake is held at once). The bank must
  hold the Family Fuse minimum (owner-set, 2,000 MP) for an MP fight.
· The rival ACCEPTS with its own card: coin counts must match or be one apart (never 4 vs 6). Its stake is held, the BELL rings, both
  cards get a $100 paper book at true fills (pg_battle.paper_book) and the fight runs for 15 / 30 / 60 minutes.
· The game is the Arena's: SIX DUELS, seat by seat (each card's biggest coin vs the other's) — the coin that moved more since the bell takes
  a spark; most sparks wins, level → the whole card's move, still level → a draw (pg_battle.duels / duel_winner).
· SPECTATORS bid their own member points on a side while bids are open (from the challenge until a third of the fight has run): one bid a
  wallet, a pari-mutuel pool — the winners share it pro rata, the house keeps HOUSE of it. Nobody on the winning side, or a draw → refunds.
· At the final bell the MP pot (both stakes) goes to the winner less HOUSE; a draw refunds both. Open challenges expire after OPEN_SEC.
Points only — nothing here moves money.
"""
MINS = (15, 30, 60)
# 🎖 RANKED BRACKETS (owner, 2026-10-21: "ranked brackets … any player can fuse any player"): every family carries a Fuse rating (Elo, from
# ELO0). Its bracket is the rating band below; a fight between families at most ONE bracket apart is RANKED (ratings move at settle, K-factor
# ELO_K), anything wider is an EXHIBITION (glory only — a Don can't farm rating off a family three brackets down). Any member may call or answer
# a PAPER fight; an MP fight spends the family bank, so it stays the Don's / Underboss's.
ELO0, ELO_K = 1000, 32
BRACKETS = (('street', 'Street', 0), ('made', 'Made', 1100), ('capo', 'Capo', 1250), ('don', 'Don', 1400))
OPEN_SEC = 1800
HOUSE = 0.05
BID_MIN, BID_MAX = 10, 5000
MAX_COINS = 12
LOG_KEEP = 30


def card_of(key, name, legs):
    """A card as the fight sees it: its key, name and coins (pair + symbol + mint), never more than MAX_COINS."""
    ls = [{'pairAddress': str(l.get('pairAddress'))[:64], 'symbol': str(l.get('symbol') or '')[:16], 'mint': l.get('mint') or l.get('baseAddress'),
           'usd': float(l.get('usd') or l.get('weight') or 1)} for l in (legs or []) if l.get('pairAddress')][:MAX_COINS]
    return {'key': str(key)[:80], 'name': str(name or 'Fuse card')[:40], 'legs': ls, 'coins': len(ls)}


def coins_ok(a, b):
    a, b = int(a), int(b)
    if a < 1 or b < 1:
        return False, 'Both families need a Fuse card with coins.'
    if abs(a - b) > 1:
        return False, f'{a} coins vs {b}: cards must have the same coin count or one apart.'
    return True, ''


def bracket(rating):
    """A rating → (key, word, index)."""
    r = float(rating if rating is not None else ELO0)
    i = max(k for k, (_, _, lo) in enumerate(BRACKETS) if r >= lo)
    return BRACKETS[i][0], BRACKETS[i][1], i


def ranked(ra, rb):
    """At most one bracket apart → a ranked fight."""
    return abs(bracket(ra)[2] - bracket(rb)[2]) <= 1


def elo(ra, rb, score_a, k=ELO_K):
    """New (ra, rb) after a fight; score_a = 1 win · 0.5 draw · 0 loss for A. Whole numbers, zero-sum."""
    ra, rb = float(ra if ra is not None else ELO0), float(rb if rb is not None else ELO0)
    ea = 1 / (1 + 10 ** ((rb - ra) / 400))
    d = int(round(k * (score_a - ea)))
    return int(round(ra)) + d, int(round(rb)) - d


def may_run(stake, boss):
    """Who may call / answer: anyone in the family for PAPER, the Don or Underboss when the family bank is on the line (MP)."""
    if stake == 'mp' and not boss:
        raise ValueError('An MP Family Fuse spends the family bank — only the Don or the Underboss calls or answers it.')


def busy(store, cid):
    return next((f for f in store.values() if f['status'] in ('open', 'live') and cid in (f['a']['id'], f['b']['id'])), None)


def challenge(store, fid, a, b, card, stake, mp, mins, now, bank_a, min_mp):
    """→ the new fight (status 'open') and the MP to hold from the challenger's bank. Raises ValueError."""
    if a['id'] == b['id']:
        raise ValueError('A family cannot fight itself.')
    if stake not in ('paper', 'mp'):
        raise ValueError('Pick paper or MP.')
    if int(mins) not in MINS:
        raise ValueError(f'A Family Fuse runs {" / ".join(map(str, MINS))} minutes.')
    if card['coins'] < 1:
        raise ValueError('That card has no coins.')
    if busy(store, a['id']) or busy(store, b['id']):
        raise ValueError('One of the families is already in a Family Fuse.')
    mp = int(mp) if stake == 'mp' else 0
    if stake == 'mp':
        if mp < 100:
            raise ValueError('Put up at least 100 MP.')
        if bank_a < max(min_mp, mp):
            raise ValueError(f'An MP Family Fuse needs {int(max(min_mp, mp)):,} MP in the bank.')
    f = {'id': fid, 'status': 'open', 'stake': stake, 'mp': mp, 'mins': int(mins), 'at': now, 'expires': now + OPEN_SEC,
         'a': {**a, 'card': card}, 'b': {**b, 'card': None}, 'bids': {}, 'books': {}, 'bell': {}}
    store[fid] = f
    return f, mp


def accept(f, card, now, bank_b, min_mp):
    """→ the MP to hold from the rival's bank. The service rings the bell (books) right after. Raises ValueError."""
    if f['status'] != 'open':
        raise ValueError('That challenge is no longer open.')
    if now > f['expires']:
        raise ValueError('That challenge expired.')
    ok, why = coins_ok(f['a']['card']['coins'], card['coins'])
    if not ok:
        raise ValueError(why)
    if f['stake'] == 'mp' and bank_b < max(min_mp, f['mp']):
        raise ValueError(f'Your bank needs {int(max(min_mp, f["mp"])):,} MP to take this fight.')
    f['b']['card'] = card
    f.update(status='live', bell_at=now, ends=now + f['mins'] * 60)
    return f['mp']


def lock_at(f):
    """Bids close a third of the way into the fight (or never opened → at the bell + a third of the clock)."""
    return float(f.get('bell_at') or f['expires']) + f['mins'] * 20


def bid(f, wallet, side, amount, pts, now, family_of=None):
    """→ the points to take from the bidder. One bid a wallet; a family's own members may only back their own side."""
    if f['status'] not in ('open', 'live') or now > lock_at(f):
        raise ValueError('Bids are closed for this fight.')
    if side not in ('a', 'b'):
        raise ValueError('Back one side.')
    if wallet in f['bids']:
        raise ValueError('One bid a fight.')
    if family_of in (f['a']['id'], f['b']['id']) and f[side]['id'] != family_of:
        raise ValueError('You can only back your own family in its fight.')
    amt = int(amount)
    if not BID_MIN <= amt <= BID_MAX:
        raise ValueError(f'Bid {BID_MIN}–{BID_MAX:,} points.')
    if amt > pts:
        raise ValueError(f'You have {int(pts):,} points.')
    f['bids'][wallet] = {'side': side, 'pts': amt, 'at': now}
    return amt


def odds(f):
    """The crowd: points on each side and what 1 point pays if that side wins (after the house cut)."""
    pool = {'a': 0, 'b': 0}
    for b in f['bids'].values():
        pool[b['side']] += b['pts']
    tot = pool['a'] + pool['b']
    pay = {s: round(tot * (1 - HOUSE) / pool[s], 2) if pool[s] else None for s in ('a', 'b')}
    return {'pool': pool, 'total': tot, 'pays': pay, 'bidders': len(f['bids'])}


def settle(f, winner, now, score=None):
    """→ {'fam': {cid: mp back}, 'bids': {wallet: pts back}, 'house': mp + pts kept}. Marks the fight done."""
    pot = 2 * f['mp']; fam = {}; house = 0
    if winner in ('a', 'b'):
        cut = int(round(pot * HOUSE)); house += cut
        if pot:
            fam[f[winner]['id']] = pot - cut
    elif f['mp']:
        fam = {f['a']['id']: f['mp'], f['b']['id']: f['mp']}
    o = odds(f); back = {}
    if winner in ('a', 'b') and o['pool'][winner]:
        share = o['total'] * (1 - HOUSE); house += int(o['total'] - share)
        for w, b in f['bids'].items():
            if b['side'] == winner:
                back[w] = int(share * b['pts'] / o['pool'][winner])
    else:
        back = {w: b['pts'] for w, b in f['bids'].items()}
    f.update(status='done', winner=winner, endAt=now, score=score, paid={'fam': fam, 'bids': back, 'house': house})
    return f['paid']


def expire(f, now):
    """An open challenge nobody took → back to the challenger (its stake refunded by the service)."""
    if f['status'] == 'open' and now > f['expires']:
        f.update(status='expired', endAt=now)
        return True
    return False


def view(f, now, duel=None):
    """The fight as the stadium draws it (never the raw books)."""
    side = lambda s: {k: f[s].get(k) for k in ('id', 'tag', 'name', 'color', 'rating', 'bracket')} | {'card': {k: (f[s]['card'] or {}).get(k) for k in ('name', 'coins')} if f[s].get('card') else None,
                                                                                 'pct': (f['books'].get(s) or {}).get('pct')}
    left = max(0, int((f.get('ends') or f['expires']) - now)) if f['status'] in ('open', 'live') else 0
    return {'id': f['id'], 'status': f['status'], 'stake': f['stake'], 'mp': f['mp'], 'mins': f['mins'], 'a': side('a'), 'b': side('b'), 'left': left,
            'ranked': bool(f.get('ranked')), 'by': f.get('byName'), 'elo': f.get('elo'),
            'bidsOpen': f['status'] in ('open', 'live') and now <= lock_at(f), 'lockIn': max(0, int(lock_at(f) - now)), 'crowd': odds(f),
            'duel': duel if duel is not None else f.get('score'), 'winner': f.get('winner'), 'paid': f.get('paid'), 'at': f['at']}
