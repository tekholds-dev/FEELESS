"""🤝 ALLIANCES (C12): start one from a reply in chat, at most 10 members, one per wallet. After the days the owner sets, its founder can found a FEELESS Union. Pure: the service stores it."""
import re
import uuid

MAX_MEMBERS = 10
DEFAULT_DAYS = 30
MAX_ALLIANCES = 2000


def _name(text):
    name = re.sub(r'[^\w .\-&\']', '', str(text or ''), flags=re.UNICODE).strip()[:32]
    if len(name) < 3:
        raise ValueError('Give it a name of at least 3 characters.')
    return name


def mine(rows, wallet):
    return next((a for a in rows if wallet in a['members']), None)


def create(rows, wallet, name, now, reply=None):
    if mine(rows, wallet):
        raise ValueError('You are already in an alliance. Leave it first.')
    if len(rows) >= MAX_ALLIANCES:
        raise ValueError('No room for new alliances right now.')
    clean = _name(name)
    if any(a['name'].lower() == clean.lower() for a in rows):
        raise ValueError('That name is taken.')
    row = {'id': uuid.uuid4().hex[:12], 'name': clean, 'founder': wallet, 'members': [wallet], 'at': round(now), 'from': str(reply or '')[:64] or None, 'union': None}
    rows.append(row)
    return row


def join(rows, wallet, aid):
    if mine(rows, wallet):
        raise ValueError('You are already in an alliance. Leave it first.')
    a = next((x for x in rows if x['id'] == aid), None)
    if not a:
        raise ValueError('That alliance is gone.')
    if len(a['members']) >= MAX_MEMBERS:
        raise ValueError(f'It is full: {MAX_MEMBERS} members.')
    a['members'].append(wallet)
    return a


def leave(rows, wallet):
    """Leaving hands the alliance to the longest-standing member. The last one out closes it, unless it became a Union, which stays on the record."""
    a = mine(rows, wallet)
    if not a:
        raise ValueError('You are not in an alliance.')
    a['members'].remove(wallet)
    if a['founder'] == wallet and a['members']:
        a['founder'] = a['members'][0]
    if not a['members'] and not a['union']:
        rows.remove(a)
    return a


def union_at(a, days):
    return a['at'] + max(0, days) * 86400


def found_union(rows, wallet, name, days, now):
    a = mine(rows, wallet)
    if not a or a['founder'] != wallet:
        raise ValueError('Only its founder can found a Union.')
    if a['union']:
        raise ValueError('It is already a Union.')
    if now < union_at(a, days):
        raise ValueError(f'It can found a Union after {days} days together.')
    a['union'] = {'name': _name(name), 'at': round(now)}
    return a


def public(a, days, now, wallet=''):
    short = lambda w: f'{w[:4]}…{w[-4:]}'
    return {'id': a['id'], 'name': a['name'], 'n': len(a['members']), 'max': MAX_MEMBERS, 'members': [short(w) for w in a['members']], 'at': a['at'], 'union': a['union'], 'unionAt': union_at(a, days), 'ready': now >= union_at(a, days), 'mine': wallet in a['members'], 'founder': a['founder'] == wallet}
