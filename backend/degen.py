"""🧨 DEGEN EDGES (pure, tested). Owner, 2026-10-08: "do all the degen ideas".

  · 🐳 SMART-WALLET RADAR — every trade tape we read (held coins, Coming up's top coins) notes each wallet's FIRST buy of a coin and its price;
    an hour later the coin's price judges that buy. A wallet with ≥ SMART_MIN settled buys, median ≥ +SMART_MED% and ≥ 60% up is SMART.
    When a smart wallet buys a coin we read, that coin is flagged. The radar earns its keep on its own record (the `smart` key in the edge
    proof): until that is proven the flag is a badge only, never a reason to buy.
  · ⚡ BUY BURST — the last 90s of a coin's tape: buys ≥ 2× sells, ≥ $BURST_USD bought, price up → a burst is happening now.
  · 📣 CALLOUT SPIKE SELL — a coin the card holds that is UP ≥ SPIKE_GAIN% while a rush of Pump callers piles in: sell part of its PROFIT
    into that buying (once an hour per coin). The stake keeps riding.
A read of the tape and the callouts, never a promise.
"""
import statistics

SMART_MIN = 3        # settled buys before a wallet can be called smart
SMART_MED = 20.0     # its typical buy is up this much an hour later
SMART_WON = 60.0     # and at least this share of its buys were up
SETTLE_SEC = 3600
KEEP_BUYS = 6000
BURST_USD = 150.0
BURST_RATIO = 2.0
SPIKE_GAIN = 20.0    # %, a held coin must already be up this much
SPIKE_FRAC = 0.5     # share of its PROFIT sold into the spike
SPIKE_EVERY = 3600


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def note_buys(state, mint, trades, now):
    """Record each wallet's FIRST buy of this coin (price + time) → new state {buys: [...], wallets: {...}}."""
    st = {'buys': list((state or {}).get('buys') or []), 'wallets': dict((state or {}).get('wallets') or {})}
    seen = {(b['w'], b['m']) for b in st['buys']}
    for t in trades or []:
        w, px = t.get('wallet'), _f(t.get('price'))
        if t.get('kind') != 'buy' or not w or px <= 0 or (w, mint) in seen:
            continue
        seen.add((w, mint))
        st['buys'].append({'w': w, 'm': mint, 'px': px, 'at': now, 'usd': round(_f(t.get('usd')), 2)})
    st['buys'] = st['buys'][-KEEP_BUYS:]
    return st


def settle(state, price_of, now):
    """Judge buys at least an hour old (no price = −100%) → new state; each wallet keeps its settled results."""
    st = {'buys': [], 'wallets': {w: dict(v) for w, v in ((state or {}).get('wallets') or {}).items()}}
    for b in (state or {}).get('buys') or []:
        if now - _f(b.get('at')) < SETTLE_SEC:
            st['buys'].append(b)
            continue
        px = _f(price_of(b['m']))
        pct = (px / b['px'] - 1) * 100 if px > 0 else -100.0
        w = st['wallets'].setdefault(b['w'], {'r': []})
        w['r'] = (list(w.get('r') or []) + [round(pct, 1)])[-30:]
    return st


def smart_set(state):
    """{wallet: {n, med, won}} for wallets that proved themselves."""
    out = {}
    for w, v in ((state or {}).get('wallets') or {}).items():
        r = v.get('r') or []
        if len(r) >= SMART_MIN:
            med = statistics.median(r); won = sum(1 for x in r if x > 0) / len(r) * 100
            if med >= SMART_MED and won >= SMART_WON:
                out[w] = {'n': len(r), 'med': round(med, 1), 'won': round(won)}
    return out


def smart_hits(trades, smart):
    """Smart wallets buying in these trades → [(wallet, usd)]."""
    return [(t.get('wallet'), _f(t.get('usd'))) for t in trades or [] if t.get('kind') == 'buy' and t.get('wallet') in (smart or {})]


def burst_why(win):
    """⚡ a buy burst in the last 90s → the reason, else None."""
    if not win or win.get('n', 0) < 5:
        return None
    b, s = _f(win.get('buyUsd')), _f(win.get('sellUsd'))
    if b >= BURST_USD and b >= BURST_RATIO * max(s, 0.01) and _f(win.get('pxChg')) > 0:
        return f"⚡ buy burst: ${b:,.0f} bought vs ${s:,.0f} sold in 90s, price {_f(win['pxChg']):+.1f}%"
    return None


def spike_sells(card, prices, rushing, now):
    """📣 Which held coins to sell PROFIT from into a callout rush → [(pairAddress, why)]. `rushing` = {mint: callers}."""
    out = []
    last = (card or {}).get('spikeAt') or {}
    for l in (card or {}).get('legs') or []:
        m, px, entry = l.get('mint'), _f((prices or {}).get(l.get('pairAddress'))), _f(l.get('entry'))
        if not m or m not in (rushing or {}) or px <= 0 or entry <= 0 or _f(l.get('units')) <= 0 or l.get('buying') or l.get('placeholder') or l.get('house'):
            continue
        gain = (px / entry - 1) * 100
        if gain < SPIKE_GAIN or now - _f(last.get(m)) < SPIKE_EVERY:
            continue
        out.append((l['pairAddress'], f"📣 {rushing[m]} Pump callers piling in while it is up {gain:+.0f}% — {SPIKE_FRAC * 100:.0f}% of its profit sold into the buying"))
    return out
