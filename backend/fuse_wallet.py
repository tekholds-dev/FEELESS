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
               'dailyUsd': 300.0, 'reserveSol': 0.03, 'slippageBps': 100, 'maxImpactPct': 3.0, 'minOrderUsd': 0.5, 'minLiqUsd': 20000.0, 'arenaMinLiqUsd': 20000.0}
RANGES = {'maxCardUsd': (5, 50000), 'maxSwapUsd': (1, 10000), 'dailyUsd': (5, 100000), 'reserveSol': (0.005, 5),
          'slippageBps': (10, 300), 'maxImpactPct': (0.2, 10), 'minOrderUsd': (0.10, 50), 'minLiqUsd': (0, 10000000), 'arenaMinLiqUsd': (0, 10000000)}
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


def liq_floor(cfg, arena=False):
    """💧 Real-buy pool floor. Arena coins (passed every runner gate + picked by the Arena) have their own floor, so a high general
    floor ($100K) doesn't lock every Arena coin out of the card; the secure-buy checks (price gap + sell-back) still run on them."""
    c = clean_cfg(cfg)
    return min(c['minLiqUsd'], c['arenaMinLiqUsd']) if arena else c['minLiqUsd']


def target(card, prices):
    """What the paper engine says the card holds: {mint: {units, pair, symbol, px}} (SOL anchor = native SOL, kept in the book)."""
    out = {}
    for l in card.get('legs') or []:
        px = _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
        t = out.setdefault(l['mint'], {'units': 0.0, 'pair': l['pairAddress'], 'symbol': l.get('symbol'), 'px': px, 'role': l.get('role'), 'arena': bool(l.get('arena')),
                                       'manualCash': bool(l.get('manualCash'))})
        t['units'] += _f(l.get('units')) or (_f(l.get('wantUnits')) if l.get('buying') else 0.0)   # a coin whose buy hasn't landed is still WANTED
    return out


def anchor_sol(tgt):
    return _f((tgt.get(SOL_MINT) or {}).get('units'))


def mark_off_card_cash(book, card):
    """Mark confirmed book holdings absent from the card for sell-to-card-cash.
    This changes intent only; holdings and card value remain until a confirmed sell fill removes the atoms."""
    visible = {l.get('mint') for l in (card or {}).get('legs') or []}
    legs, marked = {}, []
    for mint, leg in (book.get('legs') or {}).items():
        held = int(_f(leg.get('atoms')))
        if mint not in visible and held > 0:
            leg = {**leg, 'manualCash': True, 'recovered': True}
            marked.append(mint)
        legs[mint] = leg
    return {**book, 'legs': legs}, marked


REBAL_BAND = 0.5   # coins kept through a re-shape: sell / rebuy only when > 50% off target — re-weighing the same coin each round
#                    burnt the daily cap on churn (cbBTC bought 14:20, sold 14:21, bought again) and starved the real new buys


def orders(card_id, card, book, prices, sol_px, cfg, now, count_sells=True):
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
        manual_cash = bool(l.get('manualCash') or (tgt.get(mint) or {}).get('manualCash'))
        if not full and excess * px < want * px * REBAL_BAND:   # 🔁 a coin that STAYS is only trimmed when it's far over target (no churn)
            continue
        # Explicit recovery may clean out a confirmed balance after a dead pool pushes it below the normal dust floor.
        # Jupiter, slippage and impact checks still fail closed; this only ensures the recovery sell is attempted.
        if excess <= 0 or (usd < cfg['minOrderUsd'] and not (full and (manual_cash or usd >= DUST_USD))):
            continue
        frac = 1.0 if full and usd <= cfg['maxSwapUsd'] else min(1.0, min(usd, cfg['maxSwapUsd']) / (have * px)) if have * px > 0 else 0
        atoms = int(l['atoms']) if frac >= 1 else int(int(l['atoms']) * frac)
        if atoms <= 0:
            continue
        sells.append({'id': f"{card_id}:{now:.0f}:s:{mint[:6]}", 'card': card_id, 'side': 'sell', 'mint': mint, 'pair': l.get('pair'), 'symbol': l.get('symbol'),
                      'atoms': atoms, 'decimals': int(l.get('decimals') or 0), 'usd': round(min(usd, cfg['maxSwapUsd']), 4), 'midPx': px, 'at': now,
                      'why': 'sold by owner to card cash' if manual_cash else 'not on the card any more' if full else 'trimmed to the card',
                      **({'manualCash': True} if manual_cash else {})})
    # `count_sells` = plan view only: the keeper's BUY pass runs after its sells landed (or were refused) and must spend only SOL the
    # book really holds — counting a refused sell's proceeds once let a buy spend SOL the card never had (book SOL went negative)
    sol_free = _f(book.get('sol')) - _f(book.get('manualCashSol')) - anchor_sol(tgt) + (sum(o['usd'] for o in sells) / sol_px * 0.97 if count_sells else 0.0) if sol_px > 0 else 0.0   # ✂ owner's cash is never spent
    for mint, t in tgt.items():
        if mint == SOL_MINT or t['px'] <= 0:
            continue
        gap = (t['units'] - held_units(book, mint)) * t['px']
        if held_units(book, mint) > 0 and gap < t['units'] * t['px'] * REBAL_BAND:   # already holds it: top up only when far under target
            continue
        usd = min(gap, cfg['maxSwapUsd'], max(0.0, sol_free * sol_px))
        last = usd >= LEFTOVER_MIN_USD and usd >= sol_free * sol_px * 0.98   # the card's whole leftover SOL → let it in (no stuck cash)
        if (gap < cfg['minOrderUsd'] or usd < cfg['minOrderUsd']) and not last:
            continue
        sol_free -= usd / sol_px
        buys.append({'id': f"{card_id}:{now:.0f}:b:{mint[:6]}", 'card': card_id, 'side': 'buy', 'mint': mint, 'pair': t['pair'], 'symbol': t['symbol'],
                     'lamports': int(usd / sol_px * 1e9), 'usd': round(usd, 4), 'midPx': t['px'], 'at': now, 'why': 'card buys its coin',
                     **({'arena': True} if t.get('arena') else {})})
    return sells + buys


def spent_24h(ledger, now):
    # NEW money only = buys − sells in 24h: a card re-buying with the SOL it just sold recycles, it doesn't spend — counting turnover
    # froze a $5 card in cash for a day ("daily cap reached" on every rebuy after a few rotations)
    day = [o for o in ledger or [] if o.get('status') == 'filled' and now - _f(o.get('at')) < 86400]
    return round(max(0.0, sum(_f(o.get('usd')) for o in day if o.get('side') == 'buy') - sum(_f(o.get('usd')) for o in day if o.get('side') == 'sell')), 4)


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
    if order.get('side') == 'buy' and spent_24h(ledger, now) + _f(order.get('usd')) > cfg['dailyUsd']:   # sells never hit the cap (they take risk OFF)
        return False, f"daily cap ${cfg['dailyUsd']:g} reached"
    floor = liq_floor(cfg, order.get('arena'))
    if order.get('side') == 'buy' and _f(order.get('liq')) < floor:   # 💧 real money never buys a pool this thin (sells always allowed)
        return False, f"pool too thin: ${_f(order.get('liq')):,.0f} liquidity < ${floor:,.0f} (real buys{' · Arena coin' if order.get('arena') else ''})"
    if quote_impact_pct is not None and _f(quote_impact_pct) > cfg['maxImpactPct']:
        return False, f"price impact {_f(quote_impact_pct):.2f}% > {cfg['maxImpactPct']:g}%"
    return True, ''


def live_buy_market(order, pair, cfg):
    """Fail-closed final market gate for a REAL buy using a freshly fetched pair snapshot.
    Candidate/radar data may be cached; the keeper must re-check the exact pair immediately before signing."""
    if order.get('side') != 'buy':
        return True, '', {}
    p = pair if isinstance(pair, dict) else {}
    base = (p.get('baseToken') or {}).get('address')
    if not p or not base or base != order.get('mint'):
        return False, 'live market unavailable or pair/mint mismatch', {}
    px = _f(p.get('priceUsd'))
    liq = _f((p.get('liquidity') or {}).get('usd'))
    floor = liq_floor(cfg, order.get('arena'))
    if px <= 0:
        return False, 'live market price unavailable', {'liq': liq}
    if liq < floor:
        return False, f"live pool too thin: ${liq:,.0f} liquidity < ${floor:,.0f}", {'liq': liq, 'midPx': px}
    return True, '', {'liq': liq, 'midPx': px}


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


def deposit_from_tx(tx, owner):
    """💰 A real deposit INTO the Fuse wallet: a confirmed tx the wallet did NOT sign that raised its SOL. → {'sol', 'from'} or None.
    (Keeper swaps, account closes and failed sends are all signed by the wallet, so they can never be counted as deposits.)"""
    meta = (tx or {}).get('meta') or {}
    if not tx or meta.get('err'):
        return None
    keys = (((tx.get('transaction') or {}).get('message') or {}).get('accountKeys')) or []
    names = [k.get('pubkey') if isinstance(k, dict) else k for k in keys]
    if owner not in names or any(isinstance(k, dict) and k.get('pubkey') == owner and k.get('signer') for k in keys):
        return None
    i = names.index(owner)
    post, pre = meta.get('postBalances') or [], meta.get('preBalances') or []
    if i >= len(post) or i >= len(pre) or int(post[i]) <= int(pre[i]):
        return None
    return {'sol': round((int(post[i]) - int(pre[i])) / 1e9, 9), 'from': names[0] if names else ''}


def sol_story(deposits, books, reserve_sol, wallet_sol, coins_sol=0.0):
    """Where every deposited SOL is now, in one line of maths the owner can check:
    DEPOSITED = in cards (their SOL + coins) + fee reserve + unassigned + spent (trading result + network fees + open-account rent)."""
    dep = round(sum(_f(r.get('sol')) for r in deposits or []), 9)
    card_sol = sum(_f(b.get('sol')) + _f(b.get('bankSol')) for b in (books or {}).values())
    unassigned = free_sol(wallet_sol, books, reserve_sol)
    spent = round(dep - _f(wallet_sol) - _f(coins_sol), 9)
    return {'depositedSol': dep, 'n': len(deposits or []), 'cardSol': round(card_sol, 9), 'coinsSol': round(_f(coins_sol), 9),
            'reserveSol': round(min(_f(reserve_sol), max(0.0, _f(wallet_sol) - card_sol)), 9), 'unassignedSol': unassigned, 'spentSol': spent}


def fill_error(order, fill, book=None):
    """Return why a confirmed transaction is not the order we sent. Never let a successful but unrelated/partial balance change
    mutate a card: the caller halts it for reconciliation instead of guessing or submitting the same leg again."""
    if not fill:
        return 'confirmed transaction has no fill'
    atoms, sol = int(fill.get('atoms') or 0), _f(fill.get('sol'))
    booked_leg = (((book or {}).get('legs') or {}).get(order.get('mint')) or {})
    booked = int(booked_leg.get('atoms') or 0)
    if booked and int(fill.get('decimals') or 0) != int(booked_leg.get('decimals') or 0):
        return 'confirmed fill decimals do not match the held token'
    if order.get('side') == 'buy':
        if atoms <= 0 or sol >= 0:
            return 'confirmed buy balance changes have the wrong direction'
        if int(order.get('lamports') or 0) <= 0 or abs(sol) * 1e9 + 1 < int(order['lamports']):
            return 'confirmed buy did not spend the exact-input amount'
    elif order.get('side') == 'sell':
        requested = int(order.get('atoms') or 0)
        if atoms >= 0 or sol <= 0:
            return 'confirmed sell balance changes have the wrong direction'
        if requested <= 0 or abs(atoms) != requested or (booked and abs(atoms) > booked):
            return 'confirmed sell token amount does not match the exact-input order/book'
    else:
        return 'unknown order side'
    return ''


def apply_fill(book, order, fill, sol_px):
    """Book the confirmed fill: atoms + average entry for buys, SOL back for sells; network fees counted apart (never P&L)."""
    b = {**book, 'legs': {k: dict(v) for k, v in (book.get('legs') or {}).items()}}
    m = order['mint']
    l = b['legs'].setdefault(m, {'atoms': 0, 'decimals': fill['decimals'], 'pair': order.get('pair'), 'symbol': order.get('symbol'), 'costUsd': 0.0, 'entryPx': 0.0})
    l['decimals'] = fill['decimals'] or l.get('decimals') or 0
    units = abs(fill['atoms']) / (10 ** l['decimals']) if l['decimals'] is not None else 0
    usd = (min(abs(fill['sol']), int(order['lamports']) / 1e9) if order['side'] == 'buy' and order.get('lamports') else abs(fill['sol'])) * sol_px
    if order['side'] == 'buy' and fill['atoms'] > 0:
        old = int(l['atoms']) / (10 ** l['decimals'])
        l['atoms'] = int(l['atoms']) + fill['atoms']
        l['costUsd'] = round(_f(l.get('costUsd')) + usd, 6)
        l['entryPx'] = (old * _f(l.get('entryPx')) + usd) / (old + units) if old + units > 0 else 0.0
    elif order['side'] == 'sell' and fill['atoms'] < 0:
        left = max(0, int(l['atoms']) + fill['atoms'])
        l['costUsd'] = round(_f(l.get('costUsd')) * (left / int(l['atoms'])) if int(l['atoms']) else 0.0, 6)
        l['atoms'] = left
    sol_move = fill['sol']
    if order['side'] == 'buy' and order.get('lamports') and fill['sol'] < 0:
        # the card pays only what went INTO the swap; anything more (new token-account rent) comes out of the wallet's fee reserve
        swap_sol = int(order['lamports']) / 1e9
        if -fill['sol'] > swap_sol:
            b['rentSol'] = round(_f(b.get('rentSol')) + (-fill['sol'] - swap_sol), 9)
            sol_move = -swap_sol
    if order.get('cardPays'):   # after its first 5 rounds the card pays its own network FEES; rent is a refundable deposit → always the reserve
        sol_move -= fill['feeSol']
    if order['side'] == 'sell' and order.get('manualCash') and sol_move > 0:
        b['manualCashSol'] = round(_f(b.get('manualCashSol')) + sol_move, 9)
    elif order['side'] == 'buy' and sol_move < 0 and _f(b.get('manualCashSol')) > 0:
        b['manualCashSol'] = round(max(0.0, _f(b.get('manualCashSol')) - abs(sol_move)), 9)
    b['sol'] = round(_f(b.get('sol')) + sol_move, 9)
    if b['sol'] < 0:   # a fee can't take card cash below zero (it read "−0.0001 card cash"): the shortfall is the reserve's, booked with rent
        b['rentSol'] = round(_f(b.get('rentSol')) - b['sol'], 9); b['sol'] = 0.0
    if _f(b.get('manualCashSol')) > _f(b.get('sol')):
        b['manualCashSol'] = max(0.0, _f(b.get('sol')))
    b['feesSol'] = round(_f(b.get('feesSol')) + fill['feeSol'], 9)
    b['feesUsd'] = round(_f(b.get('feesUsd')) + fill['feeSol'] * sol_px, 6)
    if not l['atoms']:
        b['legs'].pop(m, None)
    return b, {'units': round(units, 9), 'px': usd / units if units else 0.0, 'usd': round(usd, 6), 'sol': round(abs(fill['sol']), 9)}


def enforce_principal_floor(book, equity_usd, sol_px):
    """Keep PAID OUT NOW within whole-card profit.

    If an older rule banked principal while the card was below fundedUsd, move the
    excess bankSol back into active card SOL. Lifetime payout history is untouched.
    """
    b = dict(book)
    if sol_px <= 0:
        return b, 0.0
    funded = max(0.0, _f(b.get('fundedUsd')))
    max_bank_usd = max(0.0, _f(equity_usd) - funded)
    max_bank_sol = max_bank_usd / sol_px
    bank = max(0.0, _f(b.get('bankSol')))
    if bank <= max_bank_sol + 1e-12:
        return b, 0.0
    move = bank - max_bank_sol
    b['bankSol'] = round(max_bank_sol, 9)
    b['sol'] = round(_f(b.get('sol')) + move, 9)
    b['bankUsd'] = round(max_bank_usd, 6)
    return b, round(move, 9)

def profit_available(book, equity_usd, sol_px):
    """Additional profit that may leave active capital without touching funded principal.

    Equity includes active holdings + card cash + already-segregated payout SOL.
    Anything at/below fundedUsd is principal and is never eligible for payout.
    """
    funded = max(0.0, _f((book or {}).get('fundedUsd')))
    banked = max(0.0, _f((book or {}).get('bankSol'))) * max(0.0, _f(sol_px))
    return round(max(0.0, _f(equity_usd) - funded - banked), 6)


def bank(book, wallet_usd, sol_px, equity_usd=None):
    """Segregate only eligible PROFIT requested by the paper engine.

    The card's funded principal is a hard floor. Even if an individual coin realizes
    a gain, no SOL is moved to paid-out balance until the WHOLE real card is above
    fundedUsd. Once above it, payouts can happen piece-by-piece as equity grows.
    """
    b = dict(book)
    target = max(0.0, _f(wallet_usd))
    seen = max(0.0, _f(b.get('payoutSeenUsd')))
    if 'payoutSeenUsd' not in b:
        seen = min(target, max(0.0, _f(b.get('bankUsd'))))
    raw = max(0.0, target - seen)
    if raw <= 0 or sol_px <= 0:
        b['payoutSeenUsd'] = max(seen, target)
        return b
    d = raw
    if equity_usd is not None:
        d = min(d, profit_available(b, equity_usd, sol_px))
        if d <= 0:
            return b   # principal protected; leave the payout target pending for later growth
    protected = min(_f(b.get('sol')), max(0.0, _f(b.get('manualCashSol'))))
    sol = min(max(0.0, _f(b.get('sol')) - protected), d / sol_px)
    if sol <= 0:
        return b
    b['sol'] = round(_f(b['sol']) - sol, 9)
    b['bankSol'] = round(_f(b.get('bankSol')) + sol, 9)
    b['bankUsd'] = round(_f(b.get('bankUsd')) + sol * sol_px, 6)
    b['payoutSeenUsd'] = round(seen + sol * sol_px, 6)
    return b


def payout_profit_cash(book, equity_usd, sol_px, usd=None):
    """Owner payout button: move only available PROFIT that already exists as card SOL.

    Never sells a coin and never touches funded principal or manual-recovery cash.
    Returns (updated_book, paid_usd).
    """
    b = dict(book)
    if sol_px <= 0:
        return b, 0.0
    avail = profit_available(b, equity_usd, sol_px)
    protected = min(_f(b.get('sol')), max(0.0, _f(b.get('manualCashSol'))))
    cash_usd = max(0.0, _f(b.get('sol')) - protected) * sol_px
    want = avail if usd is None else min(avail, max(0.0, _f(usd)))
    pay = min(want, cash_usd)
    if pay <= 0:
        return b, 0.0
    sol = pay / sol_px
    b['sol'] = round(_f(b.get('sol')) - sol, 9)
    b['bankSol'] = round(_f(b.get('bankSol')) + sol, 9)
    b['bankUsd'] = round(_f(b.get('bankUsd')) + pay, 6)
    b['manualProfitPaidUsd'] = round(_f(b.get('manualProfitPaidUsd')) + pay, 6)
    return b, round(pay, 6)


DUST_USD = 0.05   # a holding worth less than this can't be sold (under every route's minimum) — it must not hold a card open


def write_off_dust(book, prices, min_usd=DUST_USD):
    """A card that is SELLING OUT finishes even when a dead coin is left: a holding with a LIVE price that is worth under `min_usd`
    (a rugged coin: 25 units at $0.000002) is written off the book — the coins stay in the wallet, the loss was already in the card's
    value. No live price = unknown = kept (never written off blind). → (book, [{mint, symbol, usd, costUsd}])."""
    b = {**book, 'legs': {k: dict(v) for k, v in (book.get('legs') or {}).items()}}
    gone = []
    for m, l in list(b['legs'].items()):
        px = _f((prices or {}).get(l.get('pair')))
        if px <= 0:
            continue
        usd = held_units(b, m) * px
        if usd < min_usd:
            gone.append({'mint': m, 'symbol': l.get('symbol') or m[:6], 'usd': round(usd, 6), 'costUsd': round(_f(l.get('costUsd')), 4), 'pair': l.get('pair')})
            b['legs'].pop(m)
    return b, gone


def withdraw_cash(book, sol_px, usd=None):
    """💵 The OWNER takes money out of the card: card cash (SOL the card already holds — a manual sell lands here) leaves the card and
    the principal drops by the same amount. Put in $5, take $2 out → the card's principal is $3, and profit is whatever it is worth
    above $3 from then on. No coin is sold and nothing moves on-chain: the SOL becomes unassigned wallet SOL. → (book, usd taken)."""
    b = dict(book)
    if sol_px <= 0:
        return b, 0.0
    have = max(0.0, _f(b.get('sol')))
    sol = have if usd is None else min(have, max(0.0, _f(usd)) / sol_px)
    if sol <= 0:
        return b, 0.0
    took = sol * sol_px
    b['sol'] = round(have - sol, 9)
    b['manualCashSol'] = round(max(0.0, _f(b.get('manualCashSol')) - sol), 9)
    b['fundedUsd'] = round(max(0.0, _f(b.get('fundedUsd')) - took), 4)
    b['withdrawnUsd'] = round(_f(b.get('withdrawnUsd')) + took, 4)
    return b, round(took, 6)


def reinvest_bank(book):
    """Move the card's currently segregated paid-out SOL back into active card SOL.
    This is NOT new funding: fundedUsd and bankUsd (historical payouts) stay unchanged."""
    b = dict(book)
    amt = max(0.0, _f(b.get('bankSol')))
    if amt <= 0:
        return b, 0.0
    b['sol'] = round(_f(b.get('sol')) + amt, 9)
    b['bankSol'] = 0.0
    # bankUsd is the CURRENT segregated paid-out balance. Lifetime payout history lives in the append-only ledger.
    # Clearing it prevents the normal payout synchronizer from treating an already-reinvested balance as still paid out.
    b['bankUsd'] = 0.0
    # payoutSeenUsd intentionally stays put: reinvest consumes the current bank, not the historical payout event.
    return b, round(amt, 9)


MIN_REBUY_USD = 0.5
LEFTOVER_MIN_USD = 0.15   # a coin waiting on the card's last SOL may buy down to this


def sync_card(card, book, prices, sol_px):
    """The tier card now shows what it REALLY holds: coin units + true entries from the book, SOL anchor + cash from its SOL,
    network fees as its fees. P&L keeps the money rule (fees apart)."""
    c = {**card, 'legs': [dict(l) for l in card.get('legs') or []]}
    if not c.get('realBaselineAt') and _f(book.get('fundedUsd')) > 0:
        # 🩹 legacy real cards: a run baseline taken from a drifted paper value ($1.39 while $6 was really in) showed +310% and kept the
        # floor / rescue / payout math blind. Re-base once on the confirmed money put in (the UI already shows that number).
        start = round(_f(book['fundedUsd']), 4)
        c.update(startUsd=start, roundStartUsd=start, dayStartUsd=start, lowPct=0.0, realBaselineAt=_f(book.get('since')) or 1.0)
    sol_left = _f(book.get('sol'))
    for l in c['legs']:
        if l['mint'] == SOL_MINT:
            desired = _f(l.get('wantUnits')) or _f(l.get('units'))
            # A prior real sync could reduce the SOL anchor to zero while its funds sat in card cash. SOL is native—there is no
            # Jupiter buy to retry—so restore its configured equal slot directly from confirmed card SOL on the next sync.
            if desired <= 0 and sol_left > 0 and c['legs']:
                desired = sol_left / len(c['legs'])
            u = min(desired, max(0.0, sol_left)); sol_left -= u
            l['units'] = u
            if u + 1e-12 < desired:
                l['wantUnits'] = desired
            else:
                l.pop('wantUnits', None); l.pop('buying', None)
            if _f(l.get('entry')) > 0:
                l['costUsd'] = round(u * _f(l['entry']), 6)   # SOL anchor cost = SOL really left × its entry (trimmed SOL isn't a loss)
            continue
        bl = (book.get('legs') or {}).get(l['mint'])
        if bl:
            l['units'] = held_units(book, l['mint'])
            if _f(bl.get('entryPx')) > 0:
                l['entry'] = bl['entryPx']; l.setdefault('firstEntry', bl['entryPx'])
            l['costUsd'] = _f(bl.get('costUsd'))
            l['real'] = True; l.pop('buying', None); l.pop('wantUnits', None)
        else:   # its buy hasn't landed yet (failed / route busy): hold nothing, keep wanting it so the keeper retries, never show −100%
            if _f(l.get('units')) > 0:
                l['wantUnits'] = _f(l['units'])
            l.update(units=0.0, costUsd=0.0, real=False, buying=_f(l.get('wantUnits')) > 0)
    # 🔁 each NEW round: a coin that holds nothing (buy never landed / rotated in) gets an equal share again and the SOL anchor is
    # trimmed to its share, so the keeper re-tries the buy — within every wallet limit (per swap, daily, impact), never more SOL than the card has
    empty = [l for l in c['legs'] if l['mint'] != SOL_MINT and _f(l.get('units')) <= 0 and not l.get('buying') and not l.get('manualCash')]
    import time as _t
    if empty and (int(card.get('rounds') or 0) != int(card.get('rebuyRound') or -1) or _t.time() - _f(card.get('rebuyAt')) >= 60):   # new round, or 60s (no whole-round 'empty' wait)
        px = lambda l: _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
        total = _f(book.get('sol')) * sol_px + sum(_f(l.get('units')) * px(l) for l in c['legs'] if l['mint'] != SOL_MINT)
        share = total / max(1, len(c['legs']))
        for l in c['legs']:
            if l['mint'] == SOL_MINT and sol_px > 0 and _f(l.get('units')) * sol_px > share:
                sol_left += _f(l['units']) - share / sol_px
                l['costUsd'] = _f(l.get('costUsd')) * (share / sol_px) / _f(l['units']); l['units'] = share / sol_px
        free = max(0.0, sol_left - _f(book.get('manualCashSol'))) * sol_px   # ✂ cash the OWNER sold out by hand is never re-spent by a rebuy
        # If the empty slot has no free SOL, do not strand it forever. On a card with a non-SOL anchor (e.g. cbBTC),
        # trim ONLY that unprotected anchor down toward one equal slot and reserve the released slice for the empty coin.
        # The keeper still sells first and the BUY pass spends only SOL that the confirmed sell actually returned.
        # Frozen/riding coins, paid-out bankSol and wallet/free-top-up SOL are never touched by this repair.
        need = max(0.0, min(share * len(empty), total) - free)
        donors = [l for l in c['legs'] if l['mint'] != SOL_MINT and l.get('role') == 'anchor' and _f(l.get('units')) > 0
                  and not l.get('frozen') and not l.get('ride') and px(l) > 0 and _f(l.get('units')) * px(l) > share + LEFTOVER_MIN_USD]
        released = 0.0
        for d in sorted(donors, key=lambda x: _f(x.get('units')) * px(x), reverse=True):
            if need - released < LEFTOVER_MIN_USD:
                break
            val = _f(d.get('units')) * px(d)
            cut = min(val - share, need - released)
            if cut < LEFTOVER_MIN_USD:
                continue
            old_units = _f(d['units'])
            d['units'] = max(0.0, old_units - cut / px(d))
            d['costUsd'] = round(_f(d.get('costUsd')) * (d['units'] / old_units), 6) if old_units > 0 else 0.0
            released += cut
        alloc = free + released
        for l in empty:
            if px(l) > 0 and alloc >= LEFTOVER_MIN_USD:
                usd = min(share, alloc / len(empty))
                l.update(wantUnits=usd / px(l), buying=True)
        c['rebuyRound'] = int(card.get('rounds') or 0); c['rebuyAt'] = _t.time()
    c['cash'] = round(max(0.0, sol_left) * sol_px, 6)
    c['fundedUsd'] = round(_f(book.get('fundedUsd')), 6)
    c['paidNowUsd'] = round(_f(book.get('bankSol')) * sol_px, 6)
    c['feesUsd'] = round(_f(book.get('feesUsd')), 6)
    c['real'] = True
    return c


def book_value(book, prices, sol_px):
    return round((_f(book.get('sol')) + _f(book.get('bankSol'))) * sol_px + sum(held_units(book, m) * (_f(prices.get(l.get('pair'))) or _f(l.get('entryPx')))
                                                                                  for m, l in (book.get('legs') or {}).items()), 6)


def free_sol(wallet_sol, books, reserve_sol):
    """SOL in the Fuse wallet not owned by any card's book and not kept back for network fees."""
    return round(max(0.0, _f(wallet_sol) - _f(reserve_sol) - sum(_f(b.get('sol')) + _f(b.get('bankSol')) for b in (books or {}).values())), 9)


GAS_RENT_SOL = 0.00204   # rent for one new coin account — a buy of a coin the wallet never held needs this much free SOL


def gas_tank(wallet_sol, books, reserve_sol):
    """⛽ SOL the Fuse wallet has OUTSIDE the cards' books = what pays network fees + new-coin rent. ok / low / empty."""
    gas = round(max(0.0, _f(wallet_sol) - sum(_f(b.get('sol')) + _f(b.get('bankSol')) for b in (books or {}).values())), 9)
    state = 'empty' if gas < GAS_RENT_SOL else 'low' if gas < _f(reserve_sol) else 'ok'
    return {'sol': gas, 'reserve': _f(reserve_sol), 'state': state, 'newCoins': int(gas // GAS_RENT_SOL)}


def landing(ledger, card, now, window=86400, broadcast_only=False):
    """📶 Real-swap health for one card over the last 24h.

    The legacy/default view keeps the historical contract used by diagnostics/tests:
    filled transactions plus failed/skipped attempts. The live card asks for
    broadcast_only=True so its LANDED gauge measures only transactions that actually
    reached Solana and therefore answers the literal question "did it land?".
    """
    rows = [r for r in ledger or [] if r.get('card') == card and r.get('side') in ('buy', 'sell') and now - _f(r.get('at')) < window]
    if broadcast_only:
        sent = [r for r in rows if r.get('sig') and r.get('status') in ('filled', 'failed')]
        filled = len({r.get('sig') for r in sent if r.get('status') == 'filled'})
        failed = [r for r in sent if r.get('status') == 'failed']
        miss = [str(r.get('err') or '').split(' (')[0].split(':')[0][:40] for r in failed]
        top = max(set(miss), key=miss.count) if miss else None
        tried = len({r.get('sig') for r in sent})
        return {'tried': tried, 'filled': filled, 'pct': round(filled / tried * 100) if tried else None,
                'top': top, 'topN': miss.count(top) if top else 0}

    filled = len({r.get('sig') or r.get('id') for r in rows if r.get('status') == 'filled'})
    miss = [str(r.get('err') or '').split(' (')[0].split(':')[0][:40]
            for r in rows if r.get('status') in ('failed', 'skipped')]
    top = max(set(miss), key=miss.count) if miss else None
    tried = filled + len(miss)
    return {'tried': tried, 'filled': filled, 'pct': round(filled / tried * 100) if tried else None,
            'top': top, 'topN': miss.count(top) if top else 0}


def strays(wallet_tokens, decimals, books, ledger, now, settle=300):
    """🧹 Coins in the Fuse wallet that NO card books but the KEEPER traded (its ledger has them) — left by a tx marked 'not confirmed'
    that landed later, or an old double-run. → [{card, mint, atoms, decimals, pair, symbol}] to adopt back into that card (it then sells
    them to SOL). Coins the keeper never touched (the owner's own) are never returned. Skips while any order is in flight."""
    if any((b or {}).get('pending') for b in (books or {}).values()):
        return []
    booked = {m for b in (books or {}).values() for m in ((b or {}).get('legs') or {})}
    out = []
    for mint, atoms in (wallet_tokens or {}).items():
        if mint == SOL_MINT or int(_f(atoms)) <= 0 or mint in booked:
            continue
        rows = [r for r in ledger or [] if r.get('mint') == mint and r.get('card') in (books or {}) and r.get('pair')]
        if not rows or now - _f(rows[-1].get('at')) < settle:   # never traded by the keeper, or still settling
            continue
        last = rows[-1]
        out.append({'card': last['card'], 'mint': mint, 'atoms': int(_f(atoms)), 'decimals': int((decimals or {}).get(mint) or last.get('decimals') or 0),
                    'pair': last['pair'], 'symbol': last.get('symbol')})
    return out


def adopt(book, s):
    """Book a stray into its card at $0 cost (recovered — the spend was already counted); the keeper sells it next tick."""
    legs = dict(book.get('legs') or {})
    legs[s['mint']] = {'atoms': s['atoms'], 'decimals': s['decimals'], 'pair': s['pair'], 'symbol': s['symbol'], 'costUsd': 0.0, 'entryPx': 0.0, 'recovered': True}
    return {**book, 'legs': legs}


def circle_balances(wallets, address):
    """Fallback balance from Circle's own wallet list (when our RPC is rate-limited): SOL + coins by symbol. No mints → display only."""
    w = next((x for x in wallets or [] if x.get('address') == address), None)
    if not w:
        return None
    rows = w.get('balances') or []
    sol = sum(_f(r.get('amount')) for r in rows if r.get('symbol') == 'SOL')
    return {'sol': sol, 'tokens': {r.get('symbol'): _f(r.get('amount')) for r in rows if r.get('symbol') != 'SOL' and _f(r.get('amount')) > 0}, 'decimals': {}, 'source': 'circle'}


def reconcile(wallet_tokens, books):
    """Coins the books say the wallet holds but it doesn't (> 0.1% short) → [{mint, booked, held}]: that card pauses."""
    want = {}
    for b in (books or {}).values():
        for m, l in (b.get('legs') or {}).items():
            want[m] = want.get(m, 0) + int(l.get('atoms') or 0)
    return [{'mint': m, 'booked': a, 'held': int((wallet_tokens or {}).get(m) or 0)} for m, a in want.items() if int((wallet_tokens or {}).get(m) or 0) < a * 0.999]


def reconcile_sol(wallet_sol, books):
    """Card SOL is a liability of the shared wallet. A shortage must stop trading instead of letting another card spend it."""
    booked = sum(_f(b.get('sol')) + _f(b.get('bankSol')) for b in (books or {}).values())
    held = _f(wallet_sol)
    return {'booked': round(booked, 9), 'held': round(held, 9)} if held + 0.000001 < booked else None


def calibrate(ledger, min_n=3):
    """🎯 Paper learns from real fills: how much worse (or better) the real price impact was than the paper model
    (usd ÷ half the pool liquidity) → `impactMult`, and the typical network fee per swap → `feeUsd`."""
    ratios, fees, flats = [], [], []
    for o in ledger or []:
        if o.get('status') != 'filled':
            continue
        if o.get('source') == 'quote' and o.get('devPct') is not None and abs(_f(o['devPct'])) > 10:
            continue   # a price-SOURCE gap (stale / other pool), not price impact — never teaches the impact model
        if _f(o.get('feeUsd')) > 0:
            fees.append(_f(o['feeUsd']))
        mid, px, liq, usd = _f(o.get('midPx')), _f(o.get('px')), _f(o.get('liq')), _f(o.get('usd'))
        if mid <= 0 or px <= 0 or liq <= 0 or usd <= 0:
            continue
        model = usd / (liq / 2)
        real = (px / mid - 1) if o.get('side') == 'buy' else (1 - px / mid)
        # two different costs: a swap too small to move the pool (model < 0.05%) shows the FLAT cost of swapping (pool fee + spread);
        # only swaps big enough to move it teach the impact model. Mixing them pinned impactMult at ×6 from $1 swaps.
        if model < 0.0005:
            flats.append(max(0.0, real))
        elif model > 1e-5:
            ratios.append(max(0.0, real) / model)
    n = len(ratios)
    spread = round(min(0.02, statistics.median(flats)), 5) if len(flats) >= min_n else 0.0
    return {'n': n + len(flats), 'spreadPct': round(spread * 100, 3), 'spread': spread,
            'impactMult': round(min(6.0, max(0.5, statistics.median(ratios))), 3) if n >= min_n else 1.0,
            'feeUsd': round(statistics.median(fees), 5) if len(fees) >= min_n else None, 'fees': len(fees)}


def totals(ledger, card=None):
    """Audit totals: bought / sold $, network fees $, swaps, failures (optionally one card)."""
    rows = [o for o in ledger or [] if card is None or o.get('card') == card]
    ok = list({(o.get('sig') or o.get('id')): o for o in rows if o.get('status') == 'filled'}.values())   # one row per tx
    return {'bought': round(sum(_f(o.get('usd')) for o in ok if o.get('side') == 'buy'), 4),
            'sold': round(sum(_f(o.get('usd')) for o in ok if o.get('side') == 'sell'), 4),
            'feesUsd': round(sum(_f(o.get('feeUsd')) for o in ok), 6), 'swaps': len(ok),
            'failed': sum(1 for o in rows if o.get('status') in ('failed', 'skipped')),
            'topups': round(sum(_f(o.get('usd')) for o in rows if o.get('side') == 'topup'), 4)}


def topup_card(card, usd, prices, now, first=False, current_usd=None):
    """💵 Real money joins the SAME card. First funding: every coin, the cycle phase, the clock and the config stay exactly as
    they are on paper — the card is scaled to the funded $ and its time / P&L start over (the paper run is kept on the record).
    A later top-up: the new $ is spread over the coins by their current weight and a new run starts at the new total."""
    c = {**card, 'legs': [dict(l) for l in card.get('legs') or []], 'events': list(card.get('events') or []), 'parked': {k: dict(v) for k, v in (card.get('parked') or {}).items()}}
    px = lambda l: _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
    coins = sum(_f(l.get('units')) * px(l) for l in c['legs'])
    held = coins + _f(c.get('cash')) + sum(_f(p.get('usd')) for p in c['parked'].values())
    total_before = _f(current_usd) if current_usd is not None else held + _f(c.get('walletUsd'))
    c['runs'] = (list(c.get('runs') or []) + [{'at': now, 'startUsd': c.get('startUsd'), 'endUsd': round(total_before, 4),
                                                 'pct': round((total_before / (_f(c.get('startUsd')) or 1) - 1) * 100, 2), 'paper': not card.get('real')}])[-10:]
    if first:
        c['paperBefore'] = {k2: v for k2, v in card.items() if k2 not in ('events', 'runs', 'paperBefore')}   # ↩ restored when the money comes out
        k = usd / held if held > 0 else 0.0
        for l in c['legs']:
            l['units'] = _f(l.get('units')) * k; l['costUsd'] = round(_f(l.get('units')) * px(l), 6); l['entry'] = px(l); l['firstEntry'] = px(l); l['at'] = now; l.pop('peak', None)
        c['cash'] = round(_f(c.get('cash')) * k, 6)
        for p in c['parked'].values():
            p['usd'] = round(_f(p.get('usd')) * k, 6)
        c.update(walletUsd=0.0, takenUsd=0.0, compoundedUsd=0.0, feesUsd=0.0, rounds=0, roundWins=0, days=[], lowPct=0.0, realSince=now, lastRoundPct=None)
        start = round(usd, 4)
    else:
        if coins > 0:
            for l in c['legs']:
                share = _f(l.get('units')) * px(l) / coins
                if px(l) > 0:
                    l['units'] = _f(l['units']) + usd * share / px(l); l['costUsd'] = _f(l.get('costUsd')) + usd * share
        else:
            c['cash'] = _f(c.get('cash')) + usd
        start = round(total_before + usd, 4)
    c.update(startUsd=start, roundStartUsd=start, dayStartUsd=start, dayAt=now, real=True, realBaselineAt=now)
    c['events'].append({'at': now, 'kind': 'topup', 'usd': round(usd, 4), 'why': ('💵 funded with real money — same coins, same mechanics, time + P&L start over' if first else f'💵 topped up +${usd:.2f} — new run'), 'to': ['card']})
    return c


def real_run_start(card, book):
    """Use a confirmed funding baseline for legacy real cards whose pre-funding paper start leaked into the live UI."""
    start, funded = _f((card or {}).get('startUsd')), _f((book or {}).get('fundedUsd'))
    return start if (card or {}).get('realBaselineAt') or funded <= 0 else funded


def paper_status(card, prices, usd):
    """🔍 What funding $usd would make of the card RIGHT NOW: its paper status + every coin's slice at that amount."""
    px = lambda l: _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
    vals = [(l, _f(l.get('units')) * px(l)) for l in card.get('legs') or []]
    held = sum(v for _, v in vals) + _f(card.get('cash'))
    v_all = held + _f(card.get('walletUsd')) + sum(_f(p.get('usd')) for p in (card.get('parked') or {}).values())
    return {'label': card.get('label'), 'phase': card.get('phase'), 'rounds': int(card.get('rounds') or 0), 'paperUsd': round(v_all, 4),
            'paperPct': round((v_all / (_f(card.get('startUsd')) or 1) - 1) * 100, 2), 'cashPct': round(_f(card.get('cash')) / held * 100, 2) if held else 0.0,
            'coins': [{'symbol': l.get('symbol'), 'role': l.get('role'), 'pairAddress': l['pairAddress'], 'weightPct': round(v / held * 100, 2) if held else 0.0,
                       'usd': round(usd * v / held, 4) if held else 0.0, 'pricePct': round((px(l) / _f(l.get('entry')) - 1) * 100, 2) if _f(l.get('entry')) else 0.0,
                       'frozen': bool(l.get('frozen'))} for l, v in vals]}


def quote_row(symbol, usd, mid, liq, paper_px, real_units, now):
    """📏 One paper-vs-real check: what paper said $usd buys (at its modelled fill `paper_px`) vs what a REAL Jupiter quote returns.
    Shaped like a ledger fill so `calibrate` can learn the impact model from it before any real money moves."""
    real_units = _f(real_units)
    paper_units = _f(usd) / paper_px if paper_px > 0 else 0.0
    return {'at': now, 'symbol': symbol, 'usd': round(_f(usd), 4), 'midPx': _f(mid), 'liq': _f(liq), 'side': 'buy', 'status': 'filled', 'source': 'quote',
            'px': _f(usd) / real_units if real_units > 0 else 0.0, 'paperUnits': paper_units, 'realUnits': real_units,
            'devPct': round((real_units / paper_units - 1) * 100, 3) if paper_units > 0 and real_units > 0 else None}


def paper_match(rows, window=40):
    """How close paper is to real quotes: average / worst deviation of coins received (+ = real gives MORE than paper)."""
    devs = [_f(r['devPct']) for r in (rows or [])[-window:] if r.get('devPct') is not None]
    if not devs:
        return {'n': 0, 'avgDevPct': None, 'worstDevPct': None, 'within2Pct': None}
    return {'n': len(devs), 'avgDevPct': round(sum(devs) / len(devs), 3), 'worstDevPct': round(min(devs, key=lambda x: -abs(x)), 3),
            'within2Pct': round(sum(1 for x in devs if abs(x) <= 2) / len(devs) * 100, 1)}


def paper_snapshot(card):
    """The paper card from before real money. Cards funded before snapshots existed: the current coins scaled back up to the paper
    value at funding (last run record), with the paper start restored."""
    if card.get('paperBefore'):
        return card['paperBefore']
    run = next((r for r in reversed(card.get('runs') or []) if r.get('paper')), None)
    start = _f(card.get('startUsd'))
    if not run or start <= 0:
        return None
    k = _f(run.get('endUsd')) / start
    snap = {k2: v for k2, v in card.items() if k2 not in ('events', 'runs', 'paperBefore')}
    snap['legs'] = [{**{x: y for x, y in l.items() if x not in ('buying', 'wantUnits', 'real')}, 'units': _f(l.get('units')) * k, 'costUsd': _f(l.get('costUsd')) * k} for l in card.get('legs') or []]
    snap.update(cash=_f(card.get('cash')) * k, startUsd=run.get('startUsd'), roundStartUsd=run.get('endUsd'), dayStartUsd=run.get('endUsd'))
    return snap


def back_to_paper(card, real_end_usd, now):
    """↩ Every coin sold: the card goes back to the paper card it was before real money (the real run stays on its record)."""
    snap = card.get('paperBefore') or paper_snapshot(card)
    runs = list(card.get('runs') or []) + [{'at': now, 'startUsd': card.get('startUsd'), 'endUsd': round(_f(real_end_usd), 4),
                                            'pct': round((_f(real_end_usd) / (_f(card.get('startUsd')) or 1) - 1) * 100, 2), 'paper': False}]
    ev = list(card.get('events') or []) + [{'at': now, 'kind': 'defund', 'why': 'back to paper — every coin sold to SOL, the paper card from before real money is back'}]
    base = {k: v for k, v in (snap or card).items() if k != 'paperBefore'}
    base['legs'] = [{x: y for x, y in l.items() if x not in ('buying', 'wantUnits', 'real')} for l in base.get('legs') or []]
    return {**base, 'real': False, 'runs': runs[-10:], 'events': ev}


MAX_PRICE_GAP_PCT = 5.0     # the quote's price may be at most this much worse than the market price
MAX_SELL_GAP_PCT = 8.0      # a SELL may pay at most this much under the market price (a 43%-under route once sold HOTBOT for $0.49 of $0.83)
MAX_ROUNDTRIP_PCT = 6.0     # buying then selling straight back may lose at most this (fees + impact both ways)


def buy_safety(order, quote_out_atoms, decimals, sell_back_lamports):
    """(ok, why) for a REAL buy, from two read-only quotes: the buy price must be near the market price (no stale / manipulated
    route) and the coin must SELL straight back for SOL without a big loss (no honeypot, transfer tax or one-way pool)."""
    out = _f(quote_out_atoms) / (10 ** int(decimals or 0))
    if out <= 0:
        return False, 'quote returned no coins'
    px = _f(order.get('usd')) / out
    mid = _f(order.get('midPx'))
    if decimals is not None and mid > 0 and (px / mid - 1) * 100 > MAX_PRICE_GAP_PCT:   # unknown decimals → only the sell-back check
        return False, f"buy price {((px / mid - 1) * 100):.1f}% above market (> {MAX_PRICE_GAP_PCT:g}%)"
    if sell_back_lamports is None:
        return False, "can't sell it back to SOL (no route) — skipped"
    loss = (1 - _f(sell_back_lamports) / max(1, _f(order.get('lamports')))) * 100
    if loss > MAX_ROUNDTRIP_PCT:
        return False, f"sells back for {loss:.1f}% less (> {MAX_ROUNDTRIP_PCT:g}%) — tax / thin / one-way"
    return True, ''


def sell_safety(order, quote_out_lamports, sol_px, market_px):
    """(ok, why) for a REAL sell: what the route pays (SOL × SOL price) vs the coin's market value (Jupiter price). A coin that really
    dumped still sells (the market price fell with it); a broken / thin route that pays far under market is skipped and retried."""
    got = _f(quote_out_lamports) / 1e9 * _f(sol_px)
    worth = _f(order.get('atoms')) / (10 ** int(order.get('decimals') or 0)) * _f(market_px)
    if got <= 0 or worth <= 0:
        return True, ''   # no market price → the per-swap limits still apply; never strand a coin
    gap = (1 - got / worth) * 100
    if gap > MAX_SELL_GAP_PCT:
        return False, f"sell route pays {gap:.1f}% under market (> {MAX_SELL_GAP_PCT:g}%) — retried next tick"
    return True, ''


def cost_of(book, mint, atoms):
    """Cost basis ($ that reached the pool) of `atoms` of a coin in the real book — for the sell's 'in $X → out $Y' trail line."""
    l = (book.get('legs') or {}).get(mint) or {}
    have = int(_f(l.get('atoms')))
    return round(_f(l.get('costUsd')) * min(1.0, _f(atoms) / have), 6) if have > 0 else 0.0


def landing_boost(ledger, card, now, window=600):
    """Recent confirmation failures raise the next tx's priority fee.

    Keep recognising legacy timeout rows (older ledgers did not stamp side/status/sig)
    while also recognising today's explicit signed on-chain failures.
    """
    def missed(r):
        err = str(r.get('err') or '').lower()
        legacy_timeout = 'not confirmed' in err
        signed_failure = r.get('status') == 'failed' and r.get('sig') and ('expired' in err or 'failed on-chain' in err)
        return r.get('card') == card and (legacy_timeout or signed_failure) and now - _f(r.get('at')) < window
    return min(4, sum(1 for r in (ledger or [])[-60:] if missed(r)))


PENNY_USD = 0.009      # a first-try swap (base fee + priority) stays under a penny
BASE_LAMPORTS = 5_000  # Solana's signature fee


def priority_cap(attempt, boost, sol_usd=0.0):
    """Max priority fee (lamports). First try with no landing trouble: whatever keeps base + priority under a penny at today's SOL
    price (10K–50K). A retry or a card whose txs lately didn't land: 50K ×(attempt+1+boost), capped at 300K (≈ $0.02–0.06) —
    landing beats saving a fraction of a cent; it never burns the card."""
    if not int(attempt) and not int(boost) and _f(sol_usd) > 0:
        return max(10_000, min(50_000, int(round(PENNY_USD / _f(sol_usd) * 1e9)) - BASE_LAMPORTS))
    return min(300_000, 50_000 * (int(attempt) + 1 + int(boost)))


CLOSE_MAX = 8   # accounts per close transaction (well inside the size limit)


def close_every(rotate_hours):
    """Seconds between empty-account sweeps: every 2 rounds of the real card's clock, kept between 10 and 30 minutes."""
    return max(600.0, min(1800.0, 2 * _f(rotate_hours) * 3600)) if _f(rotate_hours) > 0 else 1800.0


def empty_accounts(token_accounts, keep_mints=()):
    """[{pubkey, program}] of the wallet's EMPTY token accounts (0 balance) whose coin no card holds — closing them returns the rent."""
    out = []
    for a in token_accounts or []:
        info = a.get('info') or {}
        if int((info.get('tokenAmount') or {}).get('amount') or 0) == 0 and info.get('mint') not in set(keep_mints) and a.get('pubkey') and a.get('program'):
            out.append({'pubkey': a['pubkey'], 'program': a['program'], 'mint': info.get('mint')})
    return out[:CLOSE_MAX]


def close_tx(owner, accounts, blockhash):
    """Unsigned legacy tx (base64): SPL CloseAccount for each empty account → its rent goes back to the owner wallet. Nothing else."""
    import base64
    from solders.pubkey import Pubkey
    from solders.instruction import Instruction, AccountMeta
    from solders.message import Message
    from solders.transaction import Transaction
    from solders.hash import Hash
    me = Pubkey.from_string(owner)
    ixs = [Instruction(Pubkey.from_string(a['program']), bytes([9]),   # 9 = CloseAccount (same in Token + Token-2022)
                       [AccountMeta(Pubkey.from_string(a['pubkey']), False, True), AccountMeta(me, False, True), AccountMeta(me, True, False)]) for a in accounts]
    msg = Message.new_with_blockhash(ixs, me, Hash.from_string(blockhash))
    return base64.b64encode(bytes(Transaction.new_unsigned(msg))).decode()


MISS_LIMIT = 2          # a coin that fails the buy checks this many times …
MISS_WINDOW = 600       # … within 10 minutes is benched for this card
QUIET_SEC = 900        # a skip that no quote can fix (cap / pause / thin pool) is booked once per 15 min, not every tick


def logged_recently(ledger, row, now, secs=QUIET_SEC):
    """True when the same card · coin · side was already skipped for the same reason inside `secs` (keeps the trail + Jupiter quiet)."""
    why = str(row.get('err') or '').split(' (')[0][:40]
    return any(r.get('card') == row.get('card') and r.get('mint') == row.get('mint') and r.get('side') == row.get('side')
               and r.get('status') == 'skipped' and str(r.get('err') or '').startswith(why) and now - _f(r.get('at')) < secs
               for r in (ledger or [])[-80:])


BENCH_SEC = 3600        # for an hour, so the engine swaps in a coin that CAN be bought


def note_miss(book, mint, now, reason=''):
    """Count a failed / skipped real buy. Returns (book, benched?)."""
    b = {**book, 'misses': dict(book.get('misses') or {}), 'benched': dict(book.get('benched') or {})}
    m = b['misses'].get(mint) or {'n': 0, 'first': now}
    if now - _f(m.get('first')) > MISS_WINDOW:
        m = {'n': 0, 'first': now}
    m = {**m, 'n': int(m['n']) + 1, 'why': reason[:80]}
    b['misses'][mint] = m
    if m['n'] >= MISS_LIMIT:   # each repeat bench doubles (1h → 2h → … ≤ 24h): a coin that keeps failing stops coming back
        times = int((book.get('benched') or {}).get(mint, {}).get('times') or 0) + 1
        b['benched'][mint] = {'until': now + min(86400, BENCH_SEC * 2 ** (times - 1)), 'why': reason[:80], 'times': times}
        b['misses'].pop(mint, None)
        return b, True
    return b, False


def benched(book, now):
    return {m for m, v in (book.get('benched') or {}).items() if _f(v.get('until')) > now}


CHURN_SEC = 1800   # a coin sold within 30 min of being bought = a round trip that paid fees both ways for nothing


def run_report(ledger, card, now, funded_usd=0.0, equity_usd=None, hold_sol_pct=None):
    """🩺 What a REAL run actually did, from the audit ledger only (no guesses): swaps / hour, network fees as % of the money in,
    round trips (bought then sold < 30 min), per-coin realized result, failures + top skip reasons, average fill vs market — and the
    FLAWS those numbers show, each with the setting that fixes it. Read-only: it never changes a card."""
    rows = sorted((r for r in ledger or [] if r.get('card') == card), key=lambda r: _f(r.get('at')))
    fills = list({(r.get('sig') or r.get('id')): r for r in rows if r.get('status') == 'filled' and r.get('side') in ('buy', 'sell')}.values())
    fills.sort(key=lambda r: _f(r.get('at')))
    start = next((_f(r.get('at')) for r in rows), now)
    hours = max(0.25, (now - start) / 3600)
    funded = _f(funded_usd) or sum(_f(r.get('usd')) for r in rows if r.get('side') == 'topup') or 1.0
    fees = sum(_f(r.get('feeUsd')) for r in fills)
    coins, trips, last_buy = {}, [], {}
    for r in fills:
        m = r.get('mint'); c = coins.setdefault(m, {'symbol': r.get('symbol') or str(m)[:6], 'bought': 0.0, 'sold': 0.0, 'buys': 0, 'sells': 0})
        if r['side'] == 'buy':
            c['bought'] += _f(r.get('usd')); c['buys'] += 1; last_buy[m] = r
        else:
            c['sold'] += _f(r.get('usd')); c['sells'] += 1
            b = last_buy.pop(m, None)
            if b and _f(r.get('at')) - _f(b.get('at')) < CHURN_SEC:
                trips.append({'symbol': c['symbol'], 'mins': round((_f(r.get('at')) - _f(b.get('at'))) / 60, 1), 'inUsd': round(_f(b.get('usd')), 4),
                              'outUsd': round(_f(r.get('usd')), 4), 'lossUsd': round(_f(b.get('usd')) - _f(r.get('usd')) + _f(b.get('feeUsd')) + _f(r.get('feeUsd')), 4)})
    slips = [(_f(r['px']) / _f(r['midPx']) - 1) * 100 * (1 if r['side'] == 'buy' else -1) for r in fills if _f(r.get('px')) > 0 and _f(r.get('midPx')) > 0]
    slip = round(statistics.median(slips), 3) if slips else None
    failed = [r for r in rows if r.get('status') == 'failed' and r.get('side') in ('buy', 'sell')]
    skipped = [r for r in rows if r.get('status') == 'skipped' and r.get('side') in ('buy', 'sell')]
    why = {}
    for r in skipped + failed:
        k = str(r.get('err') or '?').split(' (')[0].split(':')[0][:48]
        why[k] = why.get(k, 0) + 1
    sent = len(fills) + len(failed)
    per = sorted(({**c, 'netUsd': round(c['sold'] - c['bought'], 4), 'bought': round(c['bought'], 4), 'sold': round(c['sold'], 4)} for c in coins.values()), key=lambda c: c['netUsd'])
    out = {'card': card, 'hours': round(hours, 2), 'fundedUsd': round(funded, 4), 'swaps': len(fills), 'perHour': round(len(fills) / hours, 2),
           'feesUsd': round(fees, 4), 'feesPct': round(fees / funded * 100, 2), 'roundTrips': trips[-12:], 'tripLossUsd': round(sum(t['lossUsd'] for t in trips), 4),
           'trips': len(trips), 'failed': len(failed), 'failPct': round(len(failed) / sent * 100, 1) if sent else None, 'skipped': len(skipped),
           'skipWhy': sorted(({'why': k, 'n': n} for k, n in why.items()), key=lambda x: -x['n'])[:6], 'slipPct': slip, 'coins': per[:20],
           'equityUsd': None if equity_usd is None else round(_f(equity_usd), 4),
           'pnlPct': None if equity_usd is None else round((_f(equity_usd) / funded - 1) * 100, 2), 'holdSolPct': hold_sol_pct}
    flaws = []
    def flaw(level, what, fix):
        flaws.append({'level': level, 'what': what, 'fix': fix})
    if out['feesPct'] >= 3:
        flaw('high', f"Network fees ate {out['feesPct']:.1f}% of the money in ({len(fills)} swaps, ${fees:.2f}).", 'Slow the round clock or raise patience / min hold so coins change less often.')
    if out['perHour'] >= 6 and funded < 50:
        flaw('high', f"{out['perHour']:.1f} swaps an hour on a ${funded:.0f} card — overtrading.", 'Rotate only losers (rotateMinDrop) and keep patience ≥ 3 rounds.')
    if len(trips) >= 3:
        flaw('high', f"{len(trips)} coins were sold within 30 min of buying (round trips lost ${out['tripLossUsd']:.2f}).", 'Raise min hold (REAL_MIN_HOLD) and the instant-swap trigger so noise can’t flip a coin.')
    if out['failPct'] is not None and out['failPct'] >= 20 and sent >= 5:
        flaw('mid', f"{out['failPct']:.0f}% of sent transactions failed ({len(failed)}/{sent}).", 'Check the keeper RPC (SOLANA_RPC_URL) and priority fee; failures cost fees and miss rounds.')
    if slip is not None and slip >= 1:
        flaw('mid', f"Typical fill was {slip:.2f}% worse than the market price.", 'Raise the real-buy pool floor (minLiqUsd) — thin pools cost the most.')
    top = (out['skipWhy'] or [{}])[0]
    if top.get('n', 0) >= 10:
        flaw('mid', f"“{top['why']}” blocked {top['n']} orders.", 'This limit decided the run more than the engine did — review it in Hard limits.')
    worst = per[0] if per else None
    if worst and worst['netUsd'] < -0.25 * funded and worst['sells']:
        flaw('mid', f"${worst['symbol']} alone lost ${-worst['netUsd']:.2f} realized.", 'Tighten that coin’s stop or bench runners younger than REAL_RUNNER_AGE_H.')
    if out['pnlPct'] is not None and hold_sol_pct is not None and out['pnlPct'] < _f(hold_sol_pct) - 2:
        flaw('mid', f"The card ({out['pnlPct']:+.1f}%) trailed just holding SOL ({_f(hold_sol_pct):+.1f}%).", 'Compare clocks in the Engine pick; run the proven clock only.')
    out['flaws'] = flaws
    out['verdict'] = 'clean' if not flaws else 'fix' if any(f['level'] == 'high' for f in flaws) else 'watch'
    return out
