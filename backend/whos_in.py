"""👥 WHO'S IN (pure, read-only): the people inside one coin, from records that can be checked — never avatars, never guesses.
• on-chain: the top holders of the coin tagged from FEELESS's own forensics (dev · sniper · bundled · pool · flagged).
• FEELESS traders: wallets whose verified FEELESS swaps touched this coin — early-buyer rank (by first verified buy), still in or out, result.
Names are the wallet's profile name / handle, badges are its featured earned badges (art path only)."""
import track_record as _tr


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def short(a):
    a = str(a or '')
    return f'{a[:4]}…{a[-4:]}' if len(a) > 9 else a


def badge_art(bid):
    """Quest badge id → its poster path (q-trader → /assets/badges/feeless/trader, frsv-x → /assets/badges/frsv/x); other badges have no art."""
    b = str(bid or '')
    if b.startswith('q-'):
        return f'/assets/badges/feeless/{b[2:]}'
    if b.startswith('frsv-'):
        return f'/assets/badges/frsv/{b[5:]}'
    return None


def feeless_traders(trades_by_wallet, mint, limit=8):
    """→ [{address, rank, firstBuyAt, in (still holding), ret, usd, buys}] for wallets with verified swaps in `mint`, earliest first buyer = rank 1."""
    rows = []
    for w, rs in (trades_by_wallet or {}).items():
        mine = [r for r in rs or [] if r.get('token') == mint]
        buys = sorted((r for r in mine if r.get('side') == 'buy'), key=lambda r: _f(r.get('ts')))
        if not buys:
            continue
        closed, open_ = _tr.trade_receipts(mine)
        bought = sum(_f(r.get('tokens')) for r in buys)
        sold = sum(_f(r.get('tokens')) for r in mine if r.get('side') == 'sell')
        cost = sum(c['costUsd'] for c in closed)
        rows.append({'address': w, 'firstBuyAt': _f(buys[0].get('ts')), 'buys': len(buys), 'in': bought - sold > bought * 0.02, 'usd': round(sum(c['usd'] for c in closed), 2),
                     'ret': round(sum(c['usd'] for c in closed) / cost, 4) if cost > 0 else None})
    rows.sort(key=lambda r: r['firstBuyAt'])
    for i, r in enumerate(rows):
        r['rank'] = i + 1
    return rows[:limit]


def tag_holders(top, creator='', snipers=(), bundled=(), flagged=(), names=None, limit=10):
    """→ top-holder rows [{address, name, pct, tags}] — tags from the coin's own forensics. `names` = {address: display name}."""
    sn, bu, fl = set(snipers or []), set(bundled or []), set(flagged or [])
    out = []
    for h in top or []:
        o = h.get('owner')
        if not o:
            continue
        tags = []
        if h.get('kind') == 'program':
            tags.append('pool')
        if o == creator:
            tags.append('dev')
        if o in sn:
            tags.append('sniper')
        if o in bu:
            tags.append('bundled')
        if o in fl:
            tags.append('flagged')
        out.append({'address': o, 'name': (names or {}).get(o) or short(o), 'pct': round(_f(h.get('pct')), 2) if h.get('pct') is not None else None, 'tags': tags})
    return out[:limit]


def verdict(rows):
    """One plain line for the header: how much of the top holder list is risky."""
    risky = sum(1 for r in rows if any(t in r['tags'] for t in ('dev', 'sniper', 'bundled', 'flagged')))
    wallets = [r for r in rows if 'pool' not in r['tags']]
    return {'risky': risky, 'wallets': len(wallets)}
