"""👛 FUSE WALLET — the owner's Fuse Circle wallet funds FEELESS's own top-tier cards with REAL money. Pure, tested.

How it works (no user money, no user keys — this is FEELESS's own treasury):
  • HQ picks one Circle developer-controlled wallet as the Fuse wallet (Circle holds the key; FEELESS never sees it).
  • HQ tops up a tier card with $ from that wallet → the card RESETS as a new real run (the paper record is kept).
  • Every engine tick the paper engine says what the card should hold (`target`); `orders` turns the gap between that
    target and what the card REALLY holds (`book`) into swaps: sells first (coin → SOL), then buys (SOL → coin).
  • The keeper quotes Jupiter, Circle signs, we broadcast, and the confirmed tx's balance changes are the fill (`fill_from_meta`)
    → the card's coins, entries and fees become the TRUE ones (`sync_card`). Paper learns from those fills (`calibrate`).
Hard limits (owner-set, server-enforced): armed switch, pause, max per card, max per swap, daily cap, SOL kept for network
fees, slippage, max price impact. Every order, top-up and defund is written to the audit trail with its tx.
"""
import math
import statistics

SOL_MINT = 'So11111111111111111111111111111111111111112'
DEFAULT_CFG = {'walletId': '', 'address': '', 'armed': False, 'paused': False, 'maxCardUsd': 100.0, 'maxSwapUsd': 50.0,
               'dailyUsd': 300.0, 'reserveSol': 0.03, 'slippageBps': 100, 'maxImpactPct': 3.0, 'minOrderUsd': 1.0}
RANGES = {'maxCardUsd': (5, 50000), 'maxSwapUsd': (1, 10000), 'dailyUsd': (5, 100000), 'reserveSol': (0.005, 5),
          'slippageBps': (10, 300), 'maxImpactPct': (0.2, 10), 'minOrderUsd': (0.25, 50)}
DUST_USD = 0.05


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def clean_cfg(c):
    c = c if isinstance(c, dict) else {}
    out = dict(DEFAULT_CFG)
    for k, (lo, hi) in RANGES.items():
        if c.get(k) is not None:
            out[k] = round(min(hi, max(lo, _f(c[k]))), 4)
    out['slippageBps'] = int(out['slippageBps'])
    for k in ('armed', 'paused'):
        if k in c:
            out[k] = bool(c[k])
    for k in ('walletId', 'address'):
        if isinstance(c.get(k), str):
            out[k] = c[k].strip()[:80]
    return out


def new_book(usd, sol_px, now):
    """A fresh real book: the topped-up $ sits as SOL until the keeper buys the card's coins."""
    return {'sol': round(_f(usd) / sol_px, 9) if sol_px > 0 else 0.0, 'bankSol': 0.0, 'bankUsd': 0.0, 'legs': {}, 'fundedUsd': round(_f(usd), 4),
            'since': now, 'feesSol': 0.0, 'feesUsd': 0.0, 'pending': None}


def held_units(book, mint):
    l = (book.get('legs') or {}).get(mint) or {}
    return int(l.get('atoms') or 0) / (10 ** int(l.get('decimals') or 0)) if l.get('atoms') else 0.0


def target(card, prices):
    """What the paper engine says the card holds: {mint: {units, pair, symbol, px}} (SOL anchor = native SOL, kept in the book)."""
    out = {}
    for l in card.get('legs') or []:
        px = _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
        t = out.setdefault(l['mint'], {'units': 0.0, 'pair': l['pairAddress'], 'symbol': l.get('symbol'), 'px': px, 'role': l.get('role')})
        t['units'] += _f(l.get('units'))
    return out


def anchor_sol(tgt):
    return _f((tgt.get(SOL_MINT) or {}).get('units'))


def orders(card_id, card, book, prices, sol_px, cfg, now):
    """The swaps that move the REAL book to the paper target. Sells first (they fund the buys), then buys sized by the SOL the
    card really has (never more). Each order ≤ maxSwapUsd (the rest goes next tick); dust is ignored; SOL needs no swap."""
    cfg = clean_cfg(cfg)
    tgt = target(card, prices)
    sells, buys = [], []
    for mint, l in (book.get('legs') or {}).items():
        if mint == SOL_MINT or not l.get('atoms'):
            continue
        px = _f(prices.get(l.get('pair'))) or _f((tgt.get(mint) or {}).get('px')) or _f(l.get('entryPx'))
        have = held_units(book, mint)
        want = _f((tgt.get(mint) or {}).get('units'))
        excess = have - want
        usd = excess * px
        full = want <= 0
        if excess <= 0 or (usd < cfg['minOrderUsd'] and not (full and usd >= DUST_USD)):
            continue
        frac = 1.0 if full and usd <= cfg['maxSwapUsd'] else min(1.0, min(usd, cfg['maxSwapUsd']) / (have * px)) if have * px > 0 else 0
        atoms = int(l['atoms']) if frac >= 1 else int(int(l['atoms']) * frac)
        if atoms <= 0:
            continue
        sells.append({'id': f"{card_id}:{now:.0f}:s:{mint[:6]}", 'card': card_id, 'side': 'sell', 'mint': mint, 'pair': l.get('pair'), 'symbol': l.get('symbol'),
                      'atoms': atoms, 'decimals': int(l.get('decimals') or 0), 'usd': round(min(usd, cfg['maxSwapUsd']), 4), 'midPx': px, 'at': now,
                      'why': 'not on the card any more' if full else 'trimmed to the card'})
    sol_free = _f(book.get('sol')) - anchor_sol(tgt) + sum(o['usd'] for o in sells) / sol_px * 0.97 if sol_px > 0 else 0.0
    for mint, t in tgt.items():
        if mint == SOL_MINT or t['px'] <= 0:
            continue
        gap = (t['units'] - held_units(book, mint)) * t['px']
        usd = min(gap, cfg['maxSwapUsd'], max(0.0, sol_free * sol_px))
        if gap < cfg['minOrderUsd'] or usd < cfg['minOrderUsd']:
            continue
        sol_free -= usd / sol_px
        buys.append({'id': f"{card_id}:{now:.0f}:b:{mint[:6]}", 'card': card_id, 'side': 'buy', 'mint': mint, 'pair': t['pair'], 'symbol': t['symbol'],
                     'lamports': int(usd / sol_px * 1e9), 'usd': round(usd, 4), 'midPx': t['px'], 'at': now, 'why': 'card buys its coin'})
    return sells + buys


def spent_24h(ledger, now):
    return round(sum(_f(o.get('usd')) for o in ledger or [] if o.get('status') == 'filled' and now - _f(o.get('at')) < 86400), 4)


def check(order, cfg, ledger, now, quote_impact_pct=None):
    """(ok, why). Armed + not paused, order ≤ max per swap, today's total ≤ daily cap, quoted impact ≤ max."""
    cfg = clean_cfg(cfg)
    if not cfg['armed']:
        return False, 'Fuse wallet is not armed'
    if cfg['paused']:
        return False, 'Fuse wallet is paused'
    if not cfg['walletId'] or not cfg['address']:
        return False, 'No Fuse wallet picked'
    if _f(order.get('usd')) > cfg['maxSwapUsd'] + 0.01:
        return False, f"${_f(order.get('usd')):.2f} is over the ${cfg['maxSwapUsd']:g} per-swap cap"
    if spent_24h(ledger, now) + _f(order.get('usd')) > cfg['dailyUsd']:
        return False, f"daily cap ${cfg['dailyUsd']:g} reached"
    if quote_impact_pct is not None and _f(quote_impact_pct) > cfg['maxImpactPct']:
        return False, f"price impact {_f(quote_impact_pct):.2f}% > {cfg['maxImpactPct']:g}%"
    return True, ''


def fill_from_meta(tx, owner, mint):
    """The TRUE fill from a confirmed jsonParsed tx: (token atoms Δ, decimals, SOL Δ excl. the network fee, network fee SOL).
    None if the tx failed or the owner didn't sign it."""
    meta = (tx or {}).get('meta') or {}
    if not tx or meta.get('err'):
        return None
    keys = (((tx.get('transaction') or {}).get('message') or {}).get('accountKeys')) or []
    names = [k.get('pubkey') if isinstance(k, dict) else k for k in keys]
    if owner not in [k.get('pubkey') for k in keys if isinstance(k, dict) and k.get('signer')]:
        return None
    def tok(rows):
        hit = [r for r in rows or [] if r.get('owner') == owner and r.get('mint') == mint]
        return sum(int((r.get('uiTokenAmount') or {}).get('amount') or 0) for r in hit), next((int((r.get('uiTokenAmount') or {}).get('decimals') or 0) for r in hit), None)
    pre, dec0 = tok(meta.get('preTokenBalances')); post, dec1 = tok(meta.get('postTokenBalances'))
    i = names.index(owner) if owner in names else -1
    fee = int(meta.get('fee') or 0)
    sol = (int(meta['postBalances'][i]) - int(meta['preBalances'][i]) + fee) / 1e9 if i >= 0 and i < len(meta.get('postBalances') or []) else 0.0
    return {'atoms': post - pre, 'decimals': dec1 if dec1 is not None else dec0 if dec0 is not None else 0, 'sol': round(sol, 9), 'feeSol': fee / 1e9}


def apply_fill(book, order, fill, sol_px):
    """Book the confirmed fill: atoms + average entry for buys, SOL back for sells; network fees counted apart (never P&L)."""
    b = {**book, 'legs': {k: dict(v) for k, v in (book.get('legs') or {}).items()}}
    m = order['mint']
    l = b['legs'].setdefault(m, {'atoms': 0, 'decimals': fill['decimals'], 'pair': order.get('pair'), 'symbol': order.get('symbol'), 'costUsd': 0.0, 'entryPx': 0.0})
    l['decimals'] = fill['decimals'] or l.get('decimals') or 0
    units = abs(fill['atoms']) / (10 ** l['decimals']) if l['decimals'] is not None else 0
    usd = abs(fill['sol']) * sol_px
    if order['side'] == 'buy' and fill['atoms'] > 0:
        old = int(l['atoms']) / (10 ** l['decimals'])
        l['atoms'] = int(l['atoms']) + fill['atoms']
        l['costUsd'] = round(_f(l.get('costUsd')) + usd, 6)
        l['entryPx'] = (old * _f(l.get('entryPx')) + usd) / (old + units) if old + units > 0 else 0.0
    elif order['side'] == 'sell' and fill['atoms'] < 0:
        left = max(0, int(l['atoms']) + fill['atoms'])
        l['costUsd'] = round(_f(l.get('costUsd')) * (left / int(l['atoms'])) if int(l['atoms']) else 0.0, 6)
        l['atoms'] = left
    b['sol'] = round(_f(b.get('sol')) + fill['sol'], 9)
    b['feesSol'] = round(_f(b.get('feesSol')) + fill['feeSol'], 9)
    b['feesUsd'] = round(_f(b.get('feesUsd')) + fill['feeSol'] * sol_px, 6)
    if not l['atoms']:
        b['legs'].pop(m, None)
    return b, {'units': round(units, 9), 'px': usd / units if units else 0.0, 'usd': round(usd, 6)}


def bank(book, wallet_usd, sol_px):
    """The paper card paid part of a take to the owner → move that $ of the card's SOL to the bank (still the owner's, never redeployed)."""
    b = dict(book)
    d = _f(wallet_usd) - _f(b.get('bankUsd'))
    if d <= 0 or sol_px <= 0:
        return b
    sol = min(_f(b.get('sol')), d / sol_px)
    b['sol'] = round(_f(b['sol']) - sol, 9); b['bankSol'] = round(_f(b.get('bankSol')) + sol, 9); b['bankUsd'] = round(_f(wallet_usd), 6)
    return b


def sync_card(card, book, prices, sol_px):
    """The tier card now shows what it REALLY holds: coin units + true entries from the book, SOL anchor + cash from its SOL,
    network fees as its fees. P&L keeps the money rule (fees apart)."""
    c = {**card, 'legs': [dict(l) for l in card.get('legs') or []]}
    sol_left = _f(book.get('sol'))
    for l in c['legs']:
        if l['mint'] == SOL_MINT:
            u = min(_f(l.get('units')), max(0.0, sol_left)); sol_left -= u; l['units'] = u
            continue
        bl = (book.get('legs') or {}).get(l['mint'])
        if bl:
            l['units'] = held_units(book, l['mint'])
            if _f(bl.get('entryPx')) > 0:
                l['entry'] = bl['entryPx']; l.setdefault('firstEntry', bl['entryPx'])
            l['costUsd'] = _f(bl.get('costUsd'))
            l['real'] = True
        else:
            l['units'] = 0.0; l['real'] = False
    c['cash'] = round(max(0.0, sol_left) * sol_px, 6)
    c['feesUsd'] = round(_f(book.get('feesUsd')), 6)
    c['real'] = True
    return c


def book_value(book, prices, sol_px):
    return round((_f(book.get('sol')) + _f(book.get('bankSol'))) * sol_px + sum(held_units(book, m) * (_f(prices.get(l.get('pair'))) or _f(l.get('entryPx')))
                                                                                  for m, l in (book.get('legs') or {}).items()), 6)


def free_sol(wallet_sol, books, reserve_sol):
    """SOL in the Fuse wallet not owned by any card's book and not kept back for network fees."""
    return round(max(0.0, _f(wallet_sol) - _f(reserve_sol) - sum(_f(b.get('sol')) + _f(b.get('bankSol')) for b in (books or {}).values())), 9)


def reconcile(wallet_tokens, books):
    """Coins the books say the wallet holds but it doesn't (> 0.1% short) → [{mint, booked, held}]: that card pauses."""
    want = {}
    for b in (books or {}).values():
        for m, l in (b.get('legs') or {}).items():
            want[m] = want.get(m, 0) + int(l.get('atoms') or 0)
    return [{'mint': m, 'booked': a, 'held': int((wallet_tokens or {}).get(m) or 0)} for m, a in want.items() if int((wallet_tokens or {}).get(m) or 0) < a * 0.999]


def calibrate(ledger, min_n=3):
    """🎯 Paper learns from real fills: how much worse (or better) the real price impact was than the paper model
    (usd ÷ half the pool liquidity) → `impactMult`, and the typical network fee per swap → `feeUsd`."""
    ratios, fees = [], []
    for o in ledger or []:
        if o.get('status') != 'filled':
            continue
        if _f(o.get('feeUsd')) > 0:
            fees.append(_f(o['feeUsd']))
        mid, px, liq, usd = _f(o.get('midPx')), _f(o.get('px')), _f(o.get('liq')), _f(o.get('usd'))
        if mid <= 0 or px <= 0 or liq <= 0 or usd <= 0:
            continue
        model = usd / (liq / 2)
        real = (px / mid - 1) if o.get('side') == 'buy' else (1 - px / mid)
        if model > 1e-5:
            ratios.append(max(0.0, real) / model)
    n = len(ratios)
    return {'n': n, 'impactMult': round(min(6.0, max(0.5, statistics.median(ratios))), 3) if n >= min_n else 1.0,
            'feeUsd': round(statistics.median(fees), 5) if len(fees) >= min_n else None, 'fees': len(fees)}


def totals(ledger, card=None):
    """Audit totals: bought / sold $, network fees $, swaps, failures (optionally one card)."""
    rows = [o for o in ledger or [] if card is None or o.get('card') == card]
    ok = [o for o in rows if o.get('status') == 'filled']
    return {'bought': round(sum(_f(o.get('usd')) for o in ok if o.get('side') == 'buy'), 4),
            'sold': round(sum(_f(o.get('usd')) for o in ok if o.get('side') == 'sell'), 4),
            'feesUsd': round(sum(_f(o.get('feeUsd')) for o in ok), 6), 'swaps': len(ok),
            'failed': sum(1 for o in rows if o.get('status') in ('failed', 'skipped')),
            'topups': round(sum(_f(o.get('usd')) for o in rows if o.get('side') == 'topup'), 4)}


def topup_card(card, usd, prices, now, first=False):
    """A top-up RESETS the card as a new run: the old run is kept on the record; the new $ is spread over the card's coins by
    their current weight (first funding = the whole card starts fresh from this $)."""
    c = {**card, 'legs': [dict(l) for l in card.get('legs') or []], 'events': list(card.get('events') or [])}
    val = sum(_f(l.get('units')) * (_f(prices.get(l['pairAddress'])) or _f(l.get('entry'))) for l in c['legs']) + _f(c.get('cash'))
    if not first and val > 0:
        for l in c['legs']:
            px = _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
            share = _f(l.get('units')) * px / val
            if px > 0:
                l['units'] = _f(l['units']) + usd * share / px; l['costUsd'] = _f(l.get('costUsd')) + usd * share
    start = round((0 if first else val + _f(c.get('walletUsd'))) + usd, 4)
    c['runs'] = (list(c.get('runs') or []) + ([{'at': now, 'startUsd': c.get('startUsd'), 'endUsd': round(val + _f(c.get('walletUsd')), 4),
                                                'pct': round(((val + _f(c.get('walletUsd'))) / (_f(c.get('startUsd')) or 1) - 1) * 100, 2), 'paper': not card.get('real')}]))[-10:]
    if first:
        c.update(walletUsd=0.0, takenUsd=0.0, compoundedUsd=0.0, feesUsd=0.0, rounds=0, roundWins=0, days=[], lowPct=0.0)
    c.update(startUsd=start, roundStartUsd=start, dayStartUsd=start, dayAt=now, real=True, realSince=c.get('realSince') if not first else now)
    c['events'].append({'at': now, 'kind': 'topup', 'usd': round(usd, 4), 'why': ('💵 funded with real money — new run' if first else f'💵 topped up +${usd:.2f} — new run'), 'to': ['card']})
    return c
