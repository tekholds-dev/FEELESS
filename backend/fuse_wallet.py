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
               'dailyUsd': 300.0, 'reserveSol': 0.03, 'slippageBps': 100, 'maxImpactPct': 3.0, 'minOrderUsd': 0.5, 'minLiqUsd': 20000.0, 'arenaMinLiqUsd': 20000.0, 'trenchMinLiqUsd': 8000.0, 'pickMinLiqUsd': 10000.0, 'pickSellBackPct': 6.0,
               'coinToCoin': False}   # 🔀 one-transaction swaps (old coin → new coin). OFF until the owner switches it on
RANGES = {'maxCardUsd': (5, 50000), 'maxSwapUsd': (1, 10000), 'dailyUsd': (5, 100000), 'reserveSol': (0.005, 5),
          'slippageBps': (10, 300), 'maxImpactPct': (0.2, 10), 'minOrderUsd': (0.10, 50), 'minLiqUsd': (0, 10000000), 'arenaMinLiqUsd': (0, 10000000), 'trenchMinLiqUsd': (3000, 10000000), 'pickMinLiqUsd': (5000, 10000000), 'pickSellBackPct': (6, 10)}
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
    for k in ('armed', 'paused', 'coinToCoin'):
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


def liq_floor(cfg, arena=False, trench=False, picked=False):
    """💧 Real-buy pool floor. Arena coins (passed every runner gate + picked by the Arena) have their own floor, so a high general
    floor ($100K) doesn't lock every Arena coin out of the card; the secure-buy checks (price gap + sell-back) still run on them.
    🗑 Trench coins (fresh breakouts, strict trench gate) have their own lower floor (never under $3K)."""
    c = clean_cfg(cfg)
    if trench:
        return c['trenchMinLiqUsd']
    # 🎯 the owner's own PICK is held to the same floor the picker promised it (the Arena floor) — it used to be accepted at $25K,
    # then refused by the keeper at the general $80K AFTER the old coin was already sold
    # 🎯 …and that floor is the OWNER'S OWN setting (`pickMinLiqUsd`, never under $5K): a coin they chose by hand on a small card
    # moves a $10K pool by a fraction of a percent, and every buy still passes the impact + price-gap + sell-back checks
    if picked:
        return min(c['minLiqUsd'], c['arenaMinLiqUsd'], c['pickMinLiqUsd'])
    return min(c['minLiqUsd'], c['arenaMinLiqUsd']) if arena else c['minLiqUsd']


def target(card, prices):
    """What the paper engine says the card holds: {mint: {units, pair, symbol, px}} (SOL anchor = native SOL, kept in the book)."""
    out = {}
    for l in card.get('legs') or []:
        px = _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
        t = out.setdefault(l['mint'], {'units': 0.0, 'pair': l['pairAddress'], 'symbol': l.get('symbol'), 'px': px, 'role': l.get('role'), 'arena': bool(l.get('arena')), 'trench': bool(l.get('trench')), 'picked': bool(l.get('picked')),
                                       'trim': bool(l.get('trimAt')) and _f(l.get('trimAt')) > 0, 'trimAt': _f(l.get('trimAt')),
                                       'manualCash': bool(l.get('manualCash')), 'locked': bool(l.get('ride') or l.get('frozen'))})
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


TRIM_SEC = 600     # how long an engine cut (`trimAt`) stays wanted before the card goes back to what the wallet holds
REBAL_BAND = 0.5   # coins kept through a re-shape: sell / rebuy only when > 50% off target — re-weighing the same coin each round
#                    burnt the daily cap on churn (cbBTC bought 14:20, sold 14:21, bought again) and starved the real new buys


MIN_ORDER_FLOOR = 0.10


SEAT_ROOM = 1.25   # a seat must be worth at least the smallest sendable order × this, or its buy can never be sent


def fit_seats(equity_usd, seats):
    """🪑 How many of the owner's seats a card of this size can really FILL: each needs ≥ MIN_ORDER_FLOOR × SEAT_ROOM ($0.125).
    A $0.39 card set to 4 coins has $0.0975 a seat — under the $0.10 the keeper can send — so three seats sat on "buying…" for
    good while the card bought, trimmed and re-bought the one coin it could. Never under 2 (1 for a card under $0.25)."""
    seats = int(seats or 0)
    if seats <= 0 or _f(equity_usd) <= 0:
        return seats
    return max(1 if _f(equity_usd) < 2 * MIN_ORDER_FLOOR * SEAT_ROOM else 2, min(seats, int(_f(equity_usd) // (MIN_ORDER_FLOOR * SEAT_ROOM))))


def min_order(cfg, equity_usd=0.0, seats=0):
    """💵 The smallest order THIS card sends = the owner's `minOrderUsd`, but never more than 40% of one seat's equal share
    (and never under $0.10). Found live: a $0.99 card with 4 seats has $0.25 seats; at a flat $0.25 minimum it could not buy its
    4th coin or trim the others to fund it, so that seat sat on "buying…" and was swapped for another coin every 2 minutes,
    for good. Cards with seats of $0.63 or more are not affected."""
    mo = _f(clean_cfg(cfg)['minOrderUsd'])
    if _f(equity_usd) > 0 and int(seats or 0) > 0:
        mo = min(mo, max(MIN_ORDER_FLOOR, _f(equity_usd) / int(seats) * 0.4))
    return round(mo, 4)


def orders(card_id, card, book, prices, sol_px, cfg, now, count_sells=True):
    """The swaps that move the REAL book to the paper target. Sells first (they fund the buys), then buys sized by the SOL the
    card really has (never more). Each order ≤ maxSwapUsd (the rest goes next tick); dust is ignored; SOL needs no swap."""
    cfg = clean_cfg(cfg)
    tgt = target(card, prices)
    seats_ = max(int(_f(card.get('seats'))), len([l for l in card.get('legs') or [] if not l.get('placeholder')]))
    cfg = {**cfg, 'minOrderUsd': min_order(cfg, book_value(book, prices, sol_px) if sol_px > 0 else 0.0, seats_)}   # sized to the card's seats
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
        # ♻ a RECOVERY sell (dead / off-card coin) puts its SOL back to work in the card; only the owner's own ✂ cash is held apart
        recovered = bool(l.get('recovered'))
        manual_cash = bool((l.get('manualCash') and not recovered) or (tgt.get(mint) or {}).get('manualCash'))
        # 🔁 a coin that STAYS is only trimmed when it's far over target (no churn) — unless the ENGINE cut it on purpose
        # (🏦 banking part of a winner as it locks: `trimAt` on the leg, for 10 minutes)
        banked = bool((tgt.get(mint) or {}).get('trim')) and now - _f((tgt.get(mint) or {}).get('trimAt')) < TRIM_SEC
        if not full and not banked and excess * px < want * px * REBAL_BAND:
            continue
        # Explicit recovery may clean out a confirmed balance after a dead pool pushes it below the normal dust floor.
        # Jupiter, slippage and impact checks still fail closed; this only ensures the recovery sell is attempted.
        if excess <= 0 or (usd < cfg['minOrderUsd'] and not (full and (manual_cash or recovered or usd >= DUST_USD))):
            continue
        frac = 1.0 if full and usd <= cfg['maxSwapUsd'] else min(1.0, min(usd, cfg['maxSwapUsd']) / (have * px)) if have * px > 0 else 0
        atoms = int(l['atoms']) if frac >= 1 else int(int(l['atoms']) * frac)
        if atoms <= 0:
            continue
        sells.append({'id': f"{card_id}:{now:.0f}:s:{mint[:6]}", 'card': card_id, 'side': 'sell', 'mint': mint, 'pair': l.get('pair'), 'symbol': l.get('symbol'),
                      'atoms': atoms, 'decimals': int(l.get('decimals') or 0), 'usd': round(min(usd, cfg['maxSwapUsd']), 4), 'midPx': px, 'at': now,
                      'why': 'sold by owner to card cash' if manual_cash else 'recovered coin sold back into the card' if recovered else 'not on the card any more' if full else 'trimmed to the card',
                      **({'manualCash': True} if manual_cash else {})})
    # `count_sells` = plan view only: the keeper's BUY pass runs after its sells landed (or were refused) and must spend only SOL the
    # book really holds — counting a refused sell's proceeds once let a buy spend SOL the card never had (book SOL went negative)
    sol_free = _f(book.get('sol')) - _f(book.get('owedOutSol')) - _f(book.get('manualCashSol')) - anchor_sol(tgt) + (sum(o['usd'] for o in sells) / sol_px * 0.97 if count_sells else 0.0) if sol_px > 0 else 0.0   # ✂ owner's cash is never spent
    for mint, t in tgt.items():
        if mint == SOL_MINT or t['px'] <= 0:
            continue
        if refused_now(book, mint, now):
            continue   # 🛑 a SAFETY refusal stands for 2 minutes: the same coin is not quoted again and again until one quote slips through
        gap = (t['units'] - held_units(book, mint)) * t['px']
        if held_units(book, mint) > 0 and gap < t['units'] * t['px'] * REBAL_BAND:   # already holds it: top up only when far under target
            continue
        # ♻ a coin the wallet doesn't hold yet opens an account: its rent deposit comes out of the card's SOL too, so set it aside
        # first (when the card can't also afford it, the reserve fronts it — see apply_fill)
        # 🏦 RENT IS THE RESERVE'S, ALWAYS. A new coin's account needs ~0.002 SOL parked in it; the card used to pay that as a
        # "deposit" (counted in its value, back on close) — on a $5 card with 4 coins that was ~$1 of the card not working and a P&L
        # nobody could read. Now the card's money is ONLY its coins + its cash; the wallet reserve carries every account's rent and
        # gets it back when the account closes (`apply_fill` → `rentSol`).
        rent = 0.0
        usd = min(gap, cfg['maxSwapUsd'], max(0.0, (sol_free - rent) * sol_px))
        last = usd >= LEFTOVER_MIN_USD and usd >= (sol_free - rent) * sol_px * 0.98   # the card's whole leftover SOL → let it in (no stuck cash)
        if (gap < cfg['minOrderUsd'] or usd < cfg['minOrderUsd']) and not last:
            continue
        sol_free -= usd / sol_px + rent
        buys.append({'id': f"{card_id}:{now:.0f}:b:{mint[:6]}", 'card': card_id, 'side': 'buy', 'mint': mint, 'pair': t['pair'], 'symbol': t['symbol'],
                     'lamports': int(usd / sol_px * 1e9), 'usd': round(usd, 4), 'midPx': t['px'], 'at': now, 'why': 'card buys its coin',
                     **({'rentDeposit': rent} if rent else {}),
                     **({'arena': True} if t.get('arena') else {}), **({'trench': True} if t.get('trench') else {}), **({'picked': True} if t.get('picked') else {})})
    sweep = idle_sweep(card_id, card, book, tgt, sol_free, sol_px, cfg, now) if not sells and not buys else None
    return sells + buys + ([sweep] if sweep else [])


SAFETY_WORDS = ('sells back', 'above market', 'price impact', 'too thin', "can't sell")
REFUSED_SEC = 120.0


def refused_now(book, mint, now):
    """True while a buy of this coin was refused by a SAFETY check in the last 2 minutes (sell-back loss, price gap, impact, thin
    pool, no way back to SOL). Transient misses (route busy, slippage at send, a 429) are retried as before."""
    m = (book.get('misses') or {}).get(mint) or {}
    return bool(m) and now - _f(m.get('last')) < REFUSED_SEC and any(w in str(m.get('why') or '') for w in SAFETY_WORDS)


SWEEP_WAIT_SEC = 300   # idle cash waits this long after a failed / refused buy (the engine is re-picking that seat)


def idle_sweep(card_id, card, book, tgt, sol_free, sol_px, cfg, now):
    """💤 IDLE CARD CASH GOES BACK INTO THE CARD'S COINS. The engine tops coins up on paper in small pieces; a top-up inside the
    50% re-weigh band (or under the min order) is never sent, the next sync copies the wallet back, and the cash sat in the book
    for good — the engine logged "idle cash back into the card" every tick while $0.75 of a $2.60 card did nothing. When a tick has
    NO other order and the card holds spare SOL (beyond a SOL seat, the owner's ✂ cash, a reserved seat's money), ONE buy puts it
    into the held coin furthest under an equal share (one min-size order at least) — never a locked rider or a coin cut in the
    last 10 min; the rest follows on the next ticks. → order or None"""
    if sol_px <= 0 or card.get('flooredAt') or card.get('sellingOut'):
        return None
    reserved = sum(_f(l.get('reserveUsd')) for l in card.get('legs') or [] if l.get('placeholder')) + _f(card.get('holdCashUsd'))
    idle = sol_free * sol_px - reserved
    floor = max(_f(cfg['minOrderUsd']), LEFTOVER_MIN_USD)
    if idle < floor:
        return None
    val = lambda m, t: held_units(book, m) * t['px']
    seats = [(m, t) for m, t in tgt.items() if m != SOL_MINT and t['px'] > 0 and held_units(book, m) > 0 and not t.get('manualCash')]
    # … nor a coin whose buy was just refused (benched / a miss on record): the sweep must not hammer a coin the checks turned down
    bad = {m for m, b in (book.get('benched') or {}).items() if _f(b.get('until')) > now} | set(book.get('misses') or {})
    ok = [(m, t) for m, t in seats if not t.get('locked') and m not in bad and not (t.get('trim') and now - _f(t.get('trimAt')) < TRIM_SEC)]
    # 🔁 NO BUY-THEN-TRIM LOOP (found live: a failed buy's cash was swept into two coins, and 2 min later both were trimmed again
    # to seat the replacement; a coin trimmed for a new seat was bought back 16s later when that seat's buy was refused):
    # after any failed / refused buy the cash waits SWEEP_WAIT_SEC for the engine's re-pick, and a coin SOLD in the last 10 min
    # (whatever the reason) is not topped up.
    if any(now - _f(m.get('last')) < SWEEP_WAIT_SEC for m in (book.get('misses') or {}).values()):
        return None
    sold = book.get('soldAt') or {}
    ok = [(m, t) for m, t in ok if not (0 <= now - _f(sold.get(m, -1e12)) < TRIM_SEC)]
    if not ok:
        return None
    # an equal share among every UNLOCKED coin (a coin skipped only for minutes still counts — else the one coin left takes it all:
    # the first live sweep put $0.75 into a $0.60 coin on a four-coin card)
    free = [(m, t) for m, t in seats if not t.get('locked')]
    share = (sum(val(m, t) for m, t in free) + idle) / len(free)
    mint, t = min(ok, key=lambda x: val(*x))
    if val(mint, t) >= share:
        return None                                   # the coins under their share are resting: the cash waits for them
    usd = min(idle, cfg['maxSwapUsd'], max(share - val(mint, t), floor))
    if usd < floor:
        return None
    return {'id': f"{card_id}:{now:.0f}:b:{mint[:6]}", 'card': card_id, 'side': 'buy', 'mint': mint, 'pair': t['pair'], 'symbol': t['symbol'],
            'lamports': int(usd / sol_px * 1e9), 'usd': round(usd, 4), 'midPx': t['px'], 'at': now, 'why': 'idle card cash back into its coin',
            **({'arena': True} if t.get('arena') else {}), **({'trench': True} if t.get('trench') else {}), **({'picked': True} if t.get('picked') else {})}


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
    floor = liq_floor(cfg, order.get('arena'), order.get('trench'), order.get('picked'))
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
    if liq <= 0 and order.get('picked') and p.get('dexId') == 'pumpfun':
        # 🎯 the OWNER picked a coin still on Pump's launch curve: no pool figure exists, the curve's own depth is used
        # (= fuse.curve_liq at a conservative $100 SOL). The engine never buys a curve coin by itself.
        liq = round(2 * (32.19 * _f(p.get('marketCap') or p.get('fdv')) * 100.0) ** 0.5, 2)
    floor = liq_floor(cfg, order.get('arena'), order.get('trench'), order.get('picked'))
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
    return {'atoms': post - pre, 'decimals': dec1 if dec1 is not None else dec0 if dec0 is not None else 0, 'sol': round(sol, 9), 'feeSol': fee / 1e9,
            'openedSol': opened_sol(tx, owner)}


OPENED_MAX_SOL = 0.02   # sanity cap: ~10 accounts' rent — anything bigger is not rent


def opened_sol(tx, owner):
    """SOL this transaction put into accounts it OPENED (balance 0 before, > 0 after — never the owner itself). A multi-hop swap
    opens accounts for the coins it passes through; that rent comes back when they close, so it is a DEPOSIT, never a trading result.
    A sell of baton once booked −87% and one of ORCA −50% because $0.36 / $0.18 of such rent was counted as the price."""
    meta = (tx or {}).get('meta') or {}
    keys = (((tx or {}).get('transaction') or {}).get('message') or {}).get('accountKeys') or []
    names = [k.get('pubkey') if isinstance(k, dict) else k for k in keys]
    pre, post = meta.get('preBalances') or [], meta.get('postBalances') or []
    lam = sum(int(post[j]) for j in range(min(len(names), len(pre), len(post))) if names[j] != owner and int(pre[j]) == 0 and int(post[j]) > 0)
    return round(min(OPENED_MAX_SOL, lam / 1e9), 9)


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
        if atoms >= 0 or sol + _f(fill.get('openedSol')) <= 0:
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
    # a SELL's proceeds = what the swap paid: the SOL that reached the wallet + the rent it parked in accounts the route opened
    opened = _f(fill.get('openedSol')) if order['side'] == 'sell' else 0.0
    usd = (min(abs(fill['sol']), int(order['lamports']) / 1e9) if order['side'] == 'buy' and order.get('lamports') else abs(fill['sol'] + opened)) * sol_px
    if order['side'] == 'buy' and fill['atoms'] > 0:
        old = int(l['atoms']) / (10 ** l['decimals'])
        l['atoms'] = int(l['atoms']) + fill['atoms']
        l['costUsd'] = round(_f(l.get('costUsd')) + usd, 6)
        l['entryPx'] = (old * _f(l.get('entryPx')) + usd) / (old + units) if old + units > 0 else 0.0
    elif order['side'] == 'sell' and fill['atoms'] < 0:
        left = max(0, int(l['atoms']) + fill['atoms'])
        l['costUsd'] = round(_f(l.get('costUsd')) * (left / int(l['atoms'])) if int(l['atoms']) else 0.0, 6)
        l['atoms'] = left
        # 💤 when this coin was last SOLD (any cut, trim or exit): the idle sweep never buys back a coin sold minutes ago
        at = _f(order.get('at')) or __import__('time').time()
        b['soldAt'] = {**{m: t for m, t in (b.get('soldAt') or {}).items() if at - _f(t) < 3600}, order['mint']: at}
    sol_move = fill['sol'] + opened
    if opened > 0:   # the reserve fronts that rent (it is refunded to the wallet when the accounts close) — the card gets its full price
        b['rentSol'] = round(_f(b.get('rentSol')) + opened, 9)
    if order['side'] == 'buy' and order.get('lamports') and fill['sol'] < 0:
        # the card pays only what went INTO the swap; anything more (new token-account rent) comes out of the wallet's fee reserve
        swap_sol = int(order['lamports']) / 1e9
        if -fill['sol'] > swap_sol:
            # ♻ new-coin rent = a DEPOSIT the card pays from its own SOL and gets back when the empty account closes (`rent_back`).
            # It stays the card's money (`rentHeldSol`, counted in `book_value`), so P&L never moves. Only what the card's SOL can't
            # cover is fronted by the reserve (`rentSol`, refunded to the reserve).
            rent = -fill['sol'] - swap_sol
            # only when `orders` set the deposit aside for this buy (`rentDeposit`) — else a later order planned in the same pass
            # would find less SOL than it was sized for
            card_part = max(0.0, min(rent, _f(order.get('rentDeposit')), _f(b.get('sol')) - swap_sol))
            if card_part > 0:
                b['rentHeldSol'] = round(_f(b.get('rentHeldSol')) + card_part, 9)
                b['rentDeposits'] = {**(b.get('rentDeposits') or {}), m: round(_f((b.get('rentDeposits') or {}).get(m)) + card_part, 9)}
            if rent - card_part > 0:
                b['rentSol'] = round(_f(b.get('rentSol')) + rent - card_part, 9)
            sol_move = -swap_sol - card_part
    if order.get('cardPays'):   # after its first 5 rounds the card pays its own network FEES; rent is a refundable deposit → always the reserve
        sol_move -= fill['feeSol']
        b['cardFeesSol'] = round(_f(b.get('cardFeesSol')) + fill['feeSol'], 9)   # 🧾 P&L adds these back (fees never count in P&L)
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
    return b, {'units': round(units, 9), 'px': usd / units if units else 0.0, 'usd': round(usd, 6), 'sol': round(abs(fill['sol'] + opened), 9),
               **({'openedSol': opened} if opened else {})}


ROUTE_FIX_LOSS = 0.25   # a sell that paid ≥ 25% under its cost is worth one look at its transaction


def route_fix_rows(ledger, since=0.0):
    """🩹 Sells that may have had route rent booked as a loss (filled, with a tx, never checked, paid ≥ 25% under cost)."""
    return [r for r in ledger or [] if r.get('side') == 'sell' and r.get('status') == 'filled' and r.get('sig') and 'openedSol' not in r
            and _f(r.get('at')) >= since and _f(r.get('costUsd')) > 0 and _f(r.get('usd')) < _f(r.get('costUsd')) * (1 - ROUTE_FIX_LOSS)]


def route_fix(books, found, free, sol_px):
    """Give each card back the route rent its sells were short by (`found` = {card: SOL}), never more than the wallet's free SOL.
    → (books, {card: SOL credited})"""
    out, credits, left = dict(books or {}), {}, max(0.0, _f(free))
    for card, sol in (found or {}).items():
        back = round(min(_f(sol), left), 9)
        if back <= 0 or card not in out:
            continue
        out[card] = {**out[card], 'sol': round(_f(out[card].get('sol')) + back, 9)}
        credits[card] = back; left -= back
    return out, credits


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
    sol_left = max(0.0, _f(book.get('sol')) - _f(book.get('owedOutSol')))   # ↗ SOL owed out of the card is not the card's cash
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
                l.pop('wantUnits', None); l.pop('buying', None); l.pop('buyingSince', None)
            if _f(l.get('entry')) > 0:
                l['costUsd'] = round(u * _f(l['entry']), 6)   # SOL anchor cost = SOL really left × its entry (trimmed SOL isn't a loss)
            continue
        bl = (book.get('legs') or {}).get(l['mint'])
        if bl:
            held, want = held_units(book, l['mint']), _f(l.get('units'))
            # 🏦 AN ENGINE CUT IS DURABLE: when the engine sold part of a coin on purpose (bank at the lock, 💰 skim, ✂ part-sell →
            # `trimAt`) and that sell has not landed yet, the card keeps the CUT amount for 10 min so the keeper keeps trying. This
            # line used to copy the wallet's full balance back every tick, so one skipped sell erased the cut for good
            # ($SpaceXSI locked at +101% and its 33% bank never sold; the coin then ran to +430% with nothing banked).
            cut = bool(l.get('trimAt')) and __import__('time').time() - _f(l.get('trimAt')) < TRIM_SEC and 0 < want < held * 0.999
            l['units'] = want if cut else held
            if _f(bl.get('entryPx')) > 0:
                l['entry'] = bl['entryPx']; l.setdefault('firstEntry', bl['entryPx'])
            l['costUsd'] = round(_f(bl.get('costUsd')) * (want / held), 6) if cut else _f(bl.get('costUsd'))
            l['real'] = True; l.pop('buying', None); l.pop('wantUnits', None); l.pop('buyingSince', None)
        else:   # its buy hasn't landed yet (failed / route busy): hold nothing, keep wanting it so the keeper retries, never show −100%
            if _f(l.get('units')) > 0:
                l['wantUnits'] = _f(l['units'])
            l.update(units=0.0, costUsd=0.0, real=False, buying=_f(l.get('wantUnits')) > 0)
            if l['buying']:
                l.setdefault('buyingSince', __import__('time').time())   # ⏳ how long it has waited (a buy stuck > STUCK_BUY_SEC is swapped)
            else:
                l.pop('buyingSince', None)
    # 🔁 each NEW round: a coin that holds nothing (buy never landed / rotated in) gets an equal share again and the SOL anchor is
    # trimmed to its share, so the keeper re-tries the buy — within every wallet limit (per swap, daily, impact), never more SOL than the card has
    empty = [l for l in c['legs'] if l['mint'] != SOL_MINT and _f(l.get('units')) <= 0 and not l.get('buying') and not l.get('manualCash')]
    # ⏳ coins already WAITING on a buy need SOL too: the SOL anchor used to keep it all (sync gives SOL first), so their orders were
    # never even sent — "buying… keeper retries" for hours. They now trigger the same repair: SOL trimmed to an equal share.
    waiting = [l for l in c['legs'] if l['mint'] != SOL_MINT and _f(l.get('units')) <= 0 and l.get('buying') and not l.get('manualCash')]
    _wpx = lambda l: _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
    if waiting and max(0.0, sol_left - _f(book.get('manualCashSol'))) * sol_px + LEFTOVER_MIN_USD >= sum(_f(l.get('wantUnits')) * _wpx(l) for l in waiting):
        waiting = []   # the free SOL already covers every waiting buy → nothing to repair
    import time as _t
    if (empty or waiting) and (int(card.get('rounds') or 0) != int(card.get('rebuyRound') or -1) or _t.time() - _f(card.get('rebuyAt')) >= 60):   # new round, or 60s (no whole-round 'empty' wait)
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
        need = max(0.0, min(share * len(empty), total) - free)   # coin donors are trimmed only for EMPTY slots; a waiting buy takes SOL only
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
        for l in empty + waiting:   # waiting coins keep what they asked for, capped to what the card can really fund
            if px(l) > 0 and alloc >= LEFTOVER_MIN_USD:
                usd = min(share, alloc / len(empty + waiting))
                if l in waiting and _f(l.get('wantUnits')) > 0:
                    usd = min(_f(l['wantUnits']) * px(l), max(usd, alloc / len(empty + waiting)))
                if not held_units(book, l['mint']) and usd - GAS_RENT_SOL * sol_px >= LEFTOVER_MIN_USD:
                    usd -= GAS_RENT_SOL * sol_px   # ♻ leave room for the new coin's rent deposit (the card pays it, gets it back on close)
                l.update(wantUnits=usd / px(l), buying=True); l.setdefault('buyingSince', _t.time())
        c['rebuyRound'] = int(card.get('rounds') or 0); c['rebuyAt'] = _t.time()
    c['cash'] = round(max(0.0, sol_left) * sol_px, 6)
    c['rentUsd'] = round(_f(book.get('rentHeldSol')) * sol_px, 6)   # ♻ coin-account deposits: the card's money, back on close
    c['fundedUsd'] = round(_f(book.get('fundedUsd')), 6)
    c['paidNowUsd'] = round(_f(book.get('bankSol')) * sol_px, 6)
    c['feesUsd'] = round(_f(book.get('feesUsd')), 6)
    c['real'] = True
    return c


def settle_owed(book):
    """↗ MONEY THAT IS NOT THE CARD'S LEAVES IT (`owedOutSol`): SOL that got into a card's book without being put in by the owner
    (2026-10-05: a second keeper process paid duplicate buys from unassigned wallet SOL). The amount is taken off the card's VALUE
    at once (`book_value`), is never spent by the keeper (`orders`, `sync_card`), and moves out of the book as card cash appears —
    it simply becomes unassigned wallet SOL again (nothing on-chain). PUT IN does not change. → (book, SOL moved now)."""
    b = dict(book)
    owed = _f(b.get('owedOutSol'))
    x = min(owed, max(0.0, _f(b.get('sol')) - _f(b.get('manualCashSol'))))
    if x <= 0:
        return b, 0.0
    b['sol'] = round(_f(b.get('sol')) - x, 9); b['owedOutSol'] = round(owed - x, 9)
    return b, round(x, 9)


def book_value(book, prices, sol_px):
    return round((_f(book.get('sol')) + _f(book.get('bankSol')) + _f(book.get('rentHeldSol')) - _f(book.get('owedOutSol'))) * sol_px + sum(held_units(book, m) * (_f(prices.get(l.get('pair'))) or _f(l.get('entryPx')))
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
    """Coins the books say the wallet holds but it doesn't (> 0.1% short) → [{mint, booked, held}]: that card pauses.
    A coin with an order IN FLIGHT is never called missing: its sale can confirm on-chain seconds before the keeper books it
    (the wallet read 0 BP while the book still held it → "coins missing" for half a minute, and a needless halt)."""
    want, flying = {}, set()
    for b in (books or {}).values():
        p = b.get('pending') or {}
        flying |= {p.get('mint'), p.get('toMint')}
        for m, l in (b.get('legs') or {}).items():
            want[m] = want.get(m, 0) + int(l.get('atoms') or 0)
    want = {m: a for m, a in want.items() if m not in flying}
    return [{'mint': m, 'booked': a, 'held': int((wallet_tokens or {}).get(m) or 0)} for m, a in want.items() if int((wallet_tokens or {}).get(m) or 0) < a * 0.999]


FIT_MAX_PCT = 2.0


def fit_small_shortage(books, missing, max_pct=FIT_MAX_PCT):
    """📏 The wallet is the truth. A coin the wallet holds a LITTLE less of than ONE card's book says (≤ 2%: rounding, a transfer
    tax, a fill booked from a quote) can never be sold at the booked amount — every sell fails its simulation and the coin is
    stuck. The book is lowered to the wallet's amount (cost kept: the money really went in). Bigger shortages, a coin the wallet
    has none of, or a coin two cards hold are left to the halt. → (books, [{card, mint, symbol, pct}])"""
    out, fits = {t: b for t, b in (books or {}).items()}, []
    for m in missing or []:
        held, booked = int(m.get('held') or 0), int(m.get('booked') or 0)
        owners = [t for t, b in out.items() if int(((b.get('legs') or {}).get(m['mint']) or {}).get('atoms') or 0) > 0]
        if held <= 0 or booked <= 0 or len(owners) != 1 or (1 - held / booked) * 100 > max_pct:
            continue
        t = owners[0]; leg = out[t]['legs'][m['mint']]
        out[t] = {**out[t], 'legs': {**out[t]['legs'], m['mint']: {**leg, 'atoms': held}}}
        fits.append({'card': t, 'mint': m['mint'], 'symbol': leg.get('symbol') or m['mint'][:4], 'pct': (1 - held / booked) * 100})
    return out, fits


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
    # one row per tx AND side: a one-transaction swap books a sell row and a buy row on the same signature
    ok = list({(o.get('sig') or o.get('id'), o.get('side')): o for o in rows if o.get('status') == 'filled'}.values())
    return {'bought': round(sum(_f(o.get('usd')) for o in ok if o.get('side') == 'buy'), 4),
            'sold': round(sum(_f(o.get('usd')) for o in ok if o.get('side') == 'sell'), 4),
            'feesUsd': round(sum(_f(o.get('feeUsd')) for o in ok), 6), 'swaps': len({o.get('sig') or o.get('id') for o in ok}),
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
    # 🎯 the owner's own pick may use their own limit (6–10%, cfg `pickSellBackPct`); the engine's coins always use 6%
    cap = max(MAX_ROUNDTRIP_PCT, min(10.0, _f(order.get('maxRoundtripPct')))) if order.get('picked') else MAX_ROUNDTRIP_PCT
    if loss > cap:
        return False, f"sells back for {loss:.1f}% less (> {cap:g}%) — tax / thin / one-way"
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


PENNY_USD = 0.005      # the most ANY keeper swap may pay the network (base fee + priority) — a retry included: half a cent
FIRST_USD = 0.001      # a first try with no landing trouble: a tenth of a cent (owner: "way less than a penny", on every clock)
BASE_LAMPORTS = 5_000  # Solana's signature fee
MIN_PRIORITY = 1_000


def priority_cap(attempt, boost, sol_usd=0.0):
    """Max priority fee (lamports) so base + priority stays WAY under a penny: first try ≤ $0.001; each retry / recent miss adds
    $0.001; never over $0.005 whatever happens (it used to climb to 300K lamports ≈ $0.04 on a retry). Landing comes from the
    one-hop route + re-sending the same signed tx to every node, not from paying more. No SOL price → 10K lamports a step, ≤ 70K."""
    level = max(0, int(attempt)) + max(0, int(boost))
    if _f(sol_usd) <= 0:
        return min(70_000, 10_000 * (level + 1))
    usd = min(PENNY_USD, FIRST_USD * (level + 1))
    # the signature fee alone is 5,000 lamports: when SOL is dear the $ cap leaves no room, so a retry still steps up by a little
    return max(MIN_PRIORITY * (min(level, 4) + 1), int(round(usd / _f(sol_usd) * 1e9)) - BASE_LAMPORTS)


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


STUCK_BUY_SEC = 120     # ⏳ a coin still 'buying' after 2 min with NO refusal on record (no order could be sent) is swapped out
RETRY_SEC = 15          # … and a coin whose buy WAS refused / failed is swapped for the next best coin 15s later (owner: "15 sec, try a new one")
MISS_LIMIT = 2          # a coin that fails the buy checks this many times …
MISS_WINDOW = 1800      # … within 30 minutes is benched for this card (≥ 2× QUIET_SEC: a quietly re-logged skip must still add up)
QUIET_SEC = 900        # a skip that no quote can fix (cap / pause / thin pool) is booked once per 15 min, not every tick


def logged_recently(ledger, row, now, secs=QUIET_SEC):
    """True when the same card · coin · side was already skipped for the same reason inside `secs` (keeps the trail + Jupiter quiet)."""
    why = str(row.get('err') or '').split(' (')[0][:40]
    return any(r.get('card') == row.get('card') and r.get('mint') == row.get('mint') and r.get('side') == row.get('side')
               and r.get('status') == 'skipped' and str(r.get('err') or '').startswith(why) and now - _f(r.get('at')) < secs
               for r in (ledger or [])[-80:])


THIN_POOL = 'pool too thin'   # the keeper's thin-pool refusal (check + live_buy_market both say it)
BENCH_SEC = 900         # 15 min (doubling ≤ 2h), so the engine swaps in a coin that CAN be bought — and the coin can come back the same hour
BENCH_MAX = 7200


def note_miss(book, mint, now, reason=''):
    """Count a failed / skipped real buy. Returns (book, benched?)."""
    b = {**book, 'misses': dict(book.get('misses') or {}), 'benched': dict(book.get('benched') or {})}
    m = b['misses'].get(mint) or {'n': 0, 'first': now}
    if now - _f(m.get('first')) > MISS_WINDOW:
        m = {'n': 0, 'first': now}
    m = {**m, 'n': int(m['n']) + 1, 'why': reason[:80], 'last': now}
    b['misses'][mint] = m
    if m['n'] >= MISS_LIMIT or THIN_POOL in reason:   # 💧 a thin pool won't deepen in minutes: bench at once so the engine swaps it NOW   # each repeat bench doubles (1h → 2h → … ≤ 24h): a coin that keeps failing stops coming back
        times = int((book.get('benched') or {}).get(mint, {}).get('times') or 0) + 1
        b['benched'][mint] = {'until': now + min(BENCH_MAX, BENCH_SEC * 2 ** (times - 1)), 'why': reason[:80], 'times': times}
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
    fills = list({(r.get('sig') or r.get('id'), r.get('side')): r for r in rows if r.get('status') == 'filled' and r.get('side') in ('buy', 'sell')}.values())
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


def money_trail(rows, book, since, now, sol_px, prices=None):
    """🧾 Where a real card's money went over a window (read-only, from the audit ledger + the card's book):
    money in / out by hand · per coin bought / sold / realized result · still held (cost → now) · card cash · network fees · rent on the
    reserve · failed sends + skip reasons · benched coins. The `check` line proves the books add up: funded − taken out = held now +
    cash + realized + unrealized − card-paid fees (anything left is labelled `unexplained`, never hidden)."""
    prices = prices or {}
    rows = sorted((r for r in rows or []), key=lambda r: _f(r.get('at')))
    rows = list({(r.get('id') or r.get('sig') or id(r), r.get('status')): r for r in rows}.values())   # one row per order outcome
    win = [r for r in rows if _f(r.get('at')) >= since]
    fills = [r for r in win if r.get('status') == 'filled' and r.get('side') in ('buy', 'sell')]
    coins = {}
    for r in fills:
        c = coins.setdefault(r.get('mint'), {'symbol': r.get('symbol') or str(r.get('mint'))[:6], 'buys': 0, 'sells': 0, 'boughtUsd': 0.0, 'soldUsd': 0.0, 'realizedUsd': 0.0})
        if r['side'] == 'buy':
            c['buys'] += 1; c['boughtUsd'] += _f(r.get('usd'))
        else:
            c['sells'] += 1; c['soldUsd'] += _f(r.get('usd')); c['realizedUsd'] += _f(r.get('realizedPnlUsd'))
    held = []
    for m, l in (book.get('legs') or {}).items():
        units = int(l.get('atoms') or 0) / (10 ** int(l.get('decimals') or 0))
        px = _f(prices.get(m))
        held.append({'mint': m, 'symbol': l.get('symbol') or str(m)[:6], 'units': units, 'costUsd': round(_f(l.get('costUsd')), 4),
                     'nowUsd': round(units * px, 4) if px else None})
    by_hand = lambda *sides: round(sum(_f(r.get('usd')) for r in rows if r.get('side') in sides and r.get('status') in ('done', None)), 4)
    funded_in = by_hand('topup', 'reinvest')
    taken_out = by_hand('withdraw', 'payout', 'defund')
    cash = round((_f(book.get('sol')) + _f(book.get('rentHeldSol'))) * sol_px, 4)   # card SOL + its coin-account rent deposits
    held_cost = round(sum(h['costUsd'] for h in held), 4)
    held_now = round(sum(h['nowUsd'] if h['nowUsd'] is not None else h['costUsd'] for h in held), 4)
    realized_all = round(sum(_f(r.get('realizedPnlUsd')) for r in rows if r.get('status') == 'filled' and r.get('side') == 'sell'), 4)
    # 🩹 route rent once booked as sale losses and since put back into the card (`routefix` rows) is not a loss — the permanent
    # audit table keeps the original sell rows, so the repair is added back here
    route_back = round(sum(_f(r.get('usd')) for r in rows if r.get('side') == 'fix' and str(r.get('id') or '').startswith('routefix')), 4)
    realized_all = round(realized_all + route_back, 4)
    writeoff = round(sum(_f(r.get('costUsd')) for r in rows if r.get('side') == 'writeoff'), 4)
    card_fees = round(_f(book.get('cardFeesSol')) * sol_px, 4)
    funded = round(_f(book.get('fundedUsd')) or (funded_in - taken_out), 4)
    now_total = round(held_now + cash, 4)
    unexplained = round(funded - now_total + (held_now - held_cost) + realized_all - writeoff - card_fees, 4)   # cost-basis view
    why = {}
    for r in win:
        if r.get('status') in ('skipped', 'failed') and r.get('side') in ('buy', 'sell'):
            k = f"{r['status']}: " + str(r.get('err') or '?').split(' (')[0].split(':')[0][:60]
            why[k] = why.get(k, 0) + 1
    return {'hours': round((now - since) / 3600, 1), 'fundedUsd': funded, 'inByHandUsd': funded_in, 'outByHandUsd': taken_out,
            'nowUsd': now_total, 'heldNowUsd': held_now, 'heldCostUsd': held_cost, 'cashUsd': cash, 'resultUsd': round(now_total - funded + card_fees, 4),
            'realizedWindowUsd': round(sum(c['realizedUsd'] for c in coins.values()), 4), 'realizedAllUsd': realized_all, 'writeoffUsd': writeoff,
            'unrealizedUsd': round(held_now - held_cost, 4), 'cardFeesUsd': card_fees,
            'netFeesWindowUsd': round(sum(_f(r.get('feeUsd')) for r in fills), 4), 'rentOnReserveSol': round(_f(book.get('rentSol')), 6),
            'swaps': len(fills), 'coins': sorted(({**c, 'boughtUsd': round(c['boughtUsd'], 4), 'soldUsd': round(c['soldUsd'], 4), 'realizedUsd': round(c['realizedUsd'], 4)}
                                                  for c in coins.values()), key=lambda c: c['realizedUsd']),
            'held': held, 'problems': sorted(({'why': k, 'n': n} for k, n in why.items()), key=lambda x: -x['n']),
            'benched': {m: v.get('why') for m, v in (book.get('benched') or {}).items() if _f(v.get('until')) > now},
            'routeRentBackUsd': route_back, 'unexplainedUsd': unexplained}


def stuck_buys(card, now, benched_mints=(), secs=STUCK_BUY_SEC, missed=None, pending_mint=None):
    """⏳ Legs of a real card waiting on a buy that won't land → [pairAddress]. Benched coins at once · a coin whose buy was refused or
    failed (`missed` = the book's {mint: {first, …}}) `RETRY_SEC` after that miss · any other after `secs`. A coin with a transaction
    in flight (`pending_mint`) is NEVER swapped — it may still land."""
    bench, missed, out = set(benched_mints), missed or {}, []
    for l in (card or {}).get('legs') or []:
        m = l.get('mint')
        if not l.get('buying') or m == SOL_MINT or m == pending_mint:
            continue
        since = now if l.get('buyingSince') is None else _f(l['buyingSince'])
        miss_at = _f((missed.get(m) or {}).get('last') or (missed.get(m) or {}).get('first'))
        if m in bench or now - since >= secs or (miss_at and now - miss_at >= RETRY_SEC):
            out.append(l['pairAddress'])
    return out


HOLD_SELL_SEC = 45      # a swap's sell waits at most this long for a replacement that can be bought
URGENT_KINDS = ('sl', 'rug', 'floor', 'fix')


def hold_sells(book, card, bad_mints, now, secs=HOLD_SELL_SEC):
    """🔒 CHECK THE BUY BEFORE THE SELL. A swap = sell the old coin, then buy the new one. When the new coin can't be bought (thin pool,
    price gap, no way back out) the old coin used to be sold anyway and its money sat in cash until another coin was found — a wasted
    sell. Now the sell WAITS (≤ `secs`) while the engine swaps the unbuyable coin for the next best one. Never waits on a protective
    exit (stop / rug / floor in the card's last events), a sell-all, a halt, or the owner's own ✂. → (book, hold?)"""
    if not bad_mints or book.get('defund') or book.get('halt'):
        return ({k: v for k, v in book.items() if k != 'sellHoldAt'} if book.get('sellHoldAt') else book), False
    if any(e.get('kind') in URGENT_KINDS and now - _f(e.get('at')) < 120 for e in ((card or {}).get('events') or [])[-8:]):
        return book, False
    since = _f(book.get('sellHoldAt')) or now
    if now - since >= secs:
        return book, False
    return {**book, 'sellHoldAt': since}, True


def swap_flow(book, ledger, card_id, plan, now, window=120):
    """👁 The swap as STEPS, in the order they really happen (one transaction at a time): what just confirmed, what is in flight,
    what is next. Only confirmed rows say done — nothing is shown as bought before the chain says so.
    → [{side, symbol, state: done | failed | sending | next, usd, at}]"""
    steps, seen = [], set()
    for r in [x for x in (ledger or [])[-40:] if x.get('card') == card_id and x.get('side') in ('buy', 'sell') and now - _f(x.get('at')) <= window
              and x.get('status') in ('filled', 'failed', 'skipped')][-4:]:
        steps.append({'side': r['side'], 'symbol': r.get('symbol'), 'state': 'done' if r['status'] == 'filled' else 'failed', 'usd': round(_f(r.get('usd')), 2),
                      'at': r.get('at'), **({'err': str(r.get('err') or '').split(' (')[0][:60]} if r['status'] != 'filled' else {})})
    p = book.get('pending') or {}
    if p.get('mint'):
        seen.add((p.get('side'), p.get('mint')))
        if p.get('side') == 'swap':   # 🔀 one transaction: both coins move together
            seen.update({('sell', p.get('mint')), ('buy', p.get('toMint'))})
        steps.append({'side': p.get('side'), 'symbol': f"{p.get('symbol')} → ${p.get('toSymbol')}" if p.get('side') == 'swap' else p.get('symbol'), 'state': 'sending',
                      'usd': round(_f(p.get('usd')), 2), 'at': p.get('sentAt')})
    for o in plan or []:
        if (o.get('side'), o.get('mint')) not in seen:
            steps.append({'side': o['side'], 'symbol': o.get('symbol'), 'state': 'next', 'usd': round(_f(o.get('usd')), 2)})
    live = any(x['state'] in ('sending', 'next') for x in steps)
    return steps[-6:] if live else []


def rent_back(books, closed, sol_px=0.0):
    """♻ A closed empty coin account returns its rent to the card that PAID it (`rentDeposits[mint]`): back into card cash, out of
    `rentHeldSol`. Value and P&L don't move (the deposit was already counted as the card's). Rent the reserve fronted, or that no card
    paid, stays on the reserve. → (books, {card: sol}). Never credits more than the card deposited for that coin."""
    out = {k: {**v, 'rentDeposits': dict(v.get('rentDeposits') or {})} for k, v in (books or {}).items()}
    credits = {}
    for a in closed or []:
        sol = _f(a.get('lamports')) / 1e9
        card = next((k for k, v in out.items() if _f(v['rentDeposits'].get(a.get('mint'))) > 0), None)
        if sol <= 0 or not card:
            continue
        b = out[card]
        back = min(sol, _f(b['rentDeposits'].pop(a.get('mint'))), _f(b.get('rentHeldSol')))
        b['sol'] = round(_f(b.get('sol')) + back, 9)
        b['rentHeldSol'] = round(max(0.0, _f(b.get('rentHeldSol')) - back), 9)
        credits[card] = round(credits.get(card, 0.0) + back, 9)
    return out, credits


def undo_rent_credits(books, ledger, sol_px):
    """🩹 One-time repair: the first rent rule credited EVERY historical refund (the reserve had re-used that SOL many times) into the
    card as cash + money put in. Take each 'credited' row's SOL back out of that card's book. → (books, {card: sol removed})."""
    out = {k: dict(v) for k, v in (books or {}).items()}
    gone = {}
    for r in ledger or []:
        if r.get('side') == 'close' and r.get('status') == 'credited':
            for card, sol in (r.get('credits') or {}).items():
                if card in out:
                    gone[card] = round(gone.get(card, 0.0) + _f(sol), 9)
    for card, sol in gone.items():
        b = out[card]
        b['sol'] = round(max(0.0, _f(b.get('sol')) - sol), 9)
        b['fundedUsd'] = round(max(0.0, _f(b.get('fundedUsd')) - sol * sol_px), 4)
        b.pop('rentMints', None); b.pop('rentBackSol', None)
    return out, gone


def funded_from_ledger(book, ledger, card):
    """💵 PUT IN rebuilt from the audit trail: every top-up of this book (since it was funded) minus cash the owner withdrew."""
    since = _f(book.get('since')) - 1
    rows = [r for r in ledger or [] if r.get('card') == card and _f(r.get('at')) >= since and r.get('status') == 'done']
    return round(sum(_f(r.get('usd')) for r in rows if r.get('side') == 'topup') - sum(_f(r.get('usd')) for r in rows if r.get('side') == 'withdraw'), 4)


def halt_cleared(book, sol_short, missing_mints):
    """An automatic halt lifts by itself once the wallet shows the condition is gone (a SOL shortage the books no longer have, a
    token shortage no longer missing). The owner's own ⏸ Pause (no reason) and fill mismatches never auto-lift."""
    why = str(book.get('haltWhy') or '')
    if not book.get('halt'):
        return False
    if 'wallet SOL is below card books' in why:
        return not sol_short
    if 'token balance is below card books' in why:
        return not set(missing_mints or ()).intersection(book.get('legs') or {})
    return False


def halt_allows_sells(book):
    """A halted card still SELLS (it only adds SOL, which is what a SOL-shortage halt needs) — the owner's queued ✂ / recovery sells
    used to sit 'queued' forever. A token-shortage halt sells nothing (the wallet may not hold what the book says)."""
    return bool(book.get('halt')) and 'token balance' not in str(book.get('haltWhy') or '')


# 🔀 ONE-TRANSACTION SWAP (coin → coin). A rotation is "sell the old coin, then buy the new one": two transactions, two fees, and a
# moment in cash between them. When a single route from the old coin straight into the new one is at least as good, the keeper sends
# ONE transaction instead — the old coin leaves and the new coin arrives together, or nothing happens at all.
C2C_MAX_IMPACT = 4.0    # never when the route's own price impact is worse than this
C2C_MAX_SOL = 0.012     # the wallet's SOL may only drop by fees + new-account rent in a swap tx — more than this is not a swap


def swap_pairs(plan, book):
    """Which planned orders are one swap: a coin leaving the card for good ('not on the card any more', never the owner's ✂ cash)
    matched, in order, with a coin the card doesn't hold yet. → [(sell, buy)]"""
    sells = [o for o in plan or [] if o.get('side') == 'sell' and not o.get('manualCash') and o.get('why') == 'not on the card any more'
             and int(o.get('atoms') or 0) == int(((book.get('legs') or {}).get(o.get('mint')) or {}).get('atoms') or -1)]
    buys = [o for o in plan or [] if o.get('side') == 'buy' and not held_units(book, o.get('mint'))]
    return list(zip(sells, buys))


def c2c_ok(direct_out, two_leg_out, impact_pct, max_impact=C2C_MAX_IMPACT):
    """(ok, why). The one-transaction route is used only when it delivers AT LEAST as many coins as selling to SOL and buying back
    would, and its own impact is no worse than `max_impact`%. Otherwise the keeper does the two swaps as before."""
    d, t = _f(direct_out), _f(two_leg_out)
    if d <= 0:
        return False, 'no one-transaction route'
    if _f(impact_pct) > max_impact:
        return False, f'one-transaction route impact {_f(impact_pct):.2f}% > {max_impact:g}%'
    if t > 0 and d < t:
        return False, f'two swaps pay {(t / d - 1) * 100:.2f}% more coins than one'
    return True, f'one transaction gives {((d / t - 1) * 100 if t > 0 else 0):+.2f}% more coins than two swaps (impact {_f(impact_pct):.2f}%)'


def swap_fill_from_meta(tx, owner, mint_out, mint_in):
    """The TRUE result of a coin → coin tx: atoms out (negative), atoms in, SOL change excl. the fee, fee, rent parked in opened
    accounts. None if it failed or the owner didn't sign it."""
    a, b = fill_from_meta(tx, owner, mint_out), fill_from_meta(tx, owner, mint_in)
    if not a or not b:
        return None
    return {'outAtoms': a['atoms'], 'outDecimals': a['decimals'], 'inAtoms': b['atoms'], 'inDecimals': b['decimals'], 'sol': a['sol'], 'feeSol': a['feeSol'],
            'openedSol': a.get('openedSol') or 0.0}


def swap_fill_error(order, fill, book):
    """Why a confirmed tx is NOT the swap we sent ('' = it is). Exact coins out, some coins in (≥ the quoted minimum), and the
    wallet's SOL moved by no more than fees + rent."""
    if not fill:
        return 'confirmed transaction has no fill'
    held = int((((book or {}).get('legs') or {}).get(order.get('mint')) or {}).get('atoms') or 0)
    if fill['outAtoms'] >= 0 or abs(fill['outAtoms']) != int(order.get('atoms') or 0) or abs(fill['outAtoms']) > held:
        return 'confirmed swap did not sell the exact coins of the order/book'
    if fill['inAtoms'] <= 0 or fill['inAtoms'] < int(_f(order.get('minIn'))):
        return 'confirmed swap delivered fewer coins than the quoted minimum'
    if fill['sol'] > 0.000001 or -fill['sol'] > C2C_MAX_SOL:
        return 'confirmed swap moved SOL it should not have'
    return ''


def apply_swap(book, order, fill, sol_px, px_in):
    """Book a confirmed coin → coin swap. The money moved = what the new coins are worth at the market price right now (`px_in`):
    that is the old coin's sale price (its realized result = that − its cost) and the new coin's cost. No SOL changes hands; the SOL
    the tx used beyond its fee is new-account rent the reserve fronts (refunded to it on close). Fees stay apart, as always."""
    b = {**book, 'legs': {k: dict(v) for k, v in (book.get('legs') or {}).items()}}
    old = b['legs'].get(order['mint']) or {}
    units_in = fill['inAtoms'] / (10 ** int(fill['inDecimals'] or 0))
    usd = round(units_in * _f(px_in), 6)
    cost_out = round(_f(old.get('costUsd')), 6)
    b['legs'].pop(order['mint'], None)
    to = order['toMint']
    l = b['legs'].setdefault(to, {'atoms': 0, 'decimals': fill['inDecimals'], 'pair': order.get('toPair'), 'symbol': order.get('toSymbol'), 'costUsd': 0.0, 'entryPx': 0.0})
    was = int(l['atoms']) / (10 ** int(fill['inDecimals'] or 0))
    l.update(atoms=int(l['atoms']) + fill['inAtoms'], decimals=fill['inDecimals'], costUsd=round(_f(l.get('costUsd')) + usd, 6),
             entryPx=(was * _f(l.get('entryPx')) + usd) / (was + units_in) if was + units_in > 0 else 0.0)
    rent = max(0.0, -fill['sol'])
    if rent > 0:
        b['rentSol'] = round(_f(b.get('rentSol')) + rent, 9)
    if order.get('cardPays'):
        take = min(fill['feeSol'], max(0.0, _f(b.get('sol'))))
        b['sol'] = round(_f(b.get('sol')) - take, 9); b['cardFeesSol'] = round(_f(b.get('cardFeesSol')) + take, 9)
        if fill['feeSol'] > take:
            b['rentSol'] = round(_f(b.get('rentSol')) + fill['feeSol'] - take, 9)
    b['feesSol'] = round(_f(b.get('feesSol')) + fill['feeSol'], 9)
    b['feesUsd'] = round(_f(b.get('feesUsd')) + fill['feeSol'] * sol_px, 6)
    return b, {'usd': usd, 'costUsd': cost_out, 'realizedPnlUsd': round(usd - cost_out, 6), 'unitsIn': round(units_in, 9), 'px': _f(px_in),
               'unitsOut': abs(fill['outAtoms']) / (10 ** int(fill['outDecimals'] or 0)), 'rentSol': round(rent, 9)}


def release_rent_deposits(books, free):
    """🏦 One rule for rent (the reserve carries it): deposits a card paid under the old rule (`rentHeldSol`) go back into that card's
    cash and onto the reserve's tab (`rentSol`) — as far as the wallet has free SOL to cover them (`free`). Value doesn't change
    (the deposit was already counted as the card's); the money just starts working again. → (books, {card: SOL released})"""
    out, done, left = dict(books or {}), {}, max(0.0, _f(free))
    for k, b in out.items():
        held = _f(b.get('rentHeldSol'))
        back = round(min(held, left), 9)
        if back <= 0:
            continue
        nb = {**b, 'sol': round(_f(b.get('sol')) + back, 9), 'rentHeldSol': round(held - back, 9), 'rentSol': round(_f(b.get('rentSol')) + back, 9)}
        if nb['rentHeldSol'] <= 1e-9:
            nb['rentHeldSol'] = 0.0; nb['rentDeposits'] = {}
        out[k] = nb; done[k] = back; left -= back
    return out, done


def lookalike(symbol, mint, majors):
    """A coin wearing a major's ticker that is NOT that major (a "SOL" at $0.0004) → True. `majors` = {mint: (symbol, name)}.
    Real money once bought one: −28% in 78 seconds."""
    sym = str(symbol or '').strip().upper()
    real = {str(v[0]).upper(): m for m, v in (majors or {}).items()}
    return bool(sym) and sym in real and real[sym] != mint and mint not in (majors or {})
