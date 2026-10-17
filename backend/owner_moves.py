"""🧾 The owner's moves on a real card, recorded and scored (pure, tested).

Every hand move the card's own activity shows — a pick, a hand swap, a rebuy, a profit take, the initial taken out, a ✂ cut —
is noted once with the coin's price at that moment (`collect`), and judged `SETTLE_SEC` later against the price then (`settle`):
a coin you BROUGHT IN is good when it is up 10%+ since, a coin you SOLD / trimmed is good when it is down 10%+ since (you were
right to take it). `summary` is what the paper card that copies the owner, and the owner, read; `calls` turns fresh results
and the card's own locks into short chat lines. Coin moves in %, never the card's $ P&L. A record, never a promise."""
import re

SETTLE_SEC, GOOD_PCT, KEEP = 1800, 10.0, 400
IN_KINDS, OUT_KINDS = ('pick', 'swap', 'rebuy', 'room'), ('skim', 'house', 'cut', 'tight', 'stopped')
LATE_SEC = 7200   # 🕰 a second look 2h after the move: a stop that was 'right' at 30 min can be a shake-out by then ($STREAM ran after the owner's stop)
CTX_KEYS = ('chg5m', 'chg1h', 'buyShare', 'vol5m', 'vol1h', 'liq', 'mcap', 'ageH', 'holders', 'top10', 'call')
LABEL = {'pick': '🎯 pick', 'swap': '⇄ hand swap', 'rebuy': '🔄 rebuy', 'skim': '💰 profit take', 'house': '🏠 initial out', 'cut': '✂ cut', 'lock': '❄ lock', 'room': '✋ gave it room (SL/TP)', 'tight': '✋ tightened (SL/TP)', 'stopped': '🛑 your stop hit'}


from fnum import plain as _f


def classify(e):
    """A card event → (kind, coin symbol the move is ABOUT) for an owner move or an engine lock, else None."""
    why, kind = str((e or {}).get('why') or ''), (e or {}).get('kind')
    to = ((e or {}).get('to') or [None])[0]
    if kind in ('rotate', 'seat') and 'your pick' in why and 'failed verification' not in why:
        return ('pick', to or e.get('symbol'))
    if kind == 'rotate' and 'swapped by hand' in why:
        return ('swap', to)
    if kind == 'seat' and re.search(r'rebuy|bought back', why):
        return ('rebuy', e.get('symbol'))
    if kind == 'skim' and 'auto:' not in why and not e.get('stack'):
        return ('house' if e.get('house') or '🏠' in why else 'skim', e.get('symbol'))
    if kind in ('cut', 'manual') or (kind == 'rotate' and why.startswith('✂')):
        return ('cut', e.get('symbol'))
    if kind == 'level':   # ✋ the owner dragged a coin's SL / TP: more room is judged like a buy (up = right), tighter like a sale (down = right)
        return ('room' if e.get('room') else 'tight', e.get('symbol'))
    if kind == 'sl':   # 🛑 a stop on the card — on a coin the owner picked / lined it is the OWNER's stop (collect checks whose coin it is)
        return ('stopped', e.get('symbol'))
    if kind == 'agent' and 'R5 stop' in why:
        return ('stopped', e.get('symbol'))
    if kind == 'ride' and 'frozen' in why:
        return ('lock', e.get('symbol'))
    return None


def collect(log, card, coin_of, now, card_label=None, mine=None):
    """New events of this card since the log's last look → noted moves. `coin_of(symbol)` → {'mint', 'pair', 'px'} or None (a move
    whose coin can't be priced is skipped). → (new log, [moves added])."""
    log = dict(log or {})
    seen_at, rows, added = _f(log.get('seenAt')), list(log.get('rows') or []), []
    mine_ = set(mine or ()) | {r.get('symbol') for r in rows if r.get('kind') in IN_KINDS and now - _f(r.get('at')) < 12 * 3600}
    newest = seen_at
    for e in (card or {}).get('events') or []:
        at = _f(e.get('at'))
        if at <= seen_at or now - at > 6 * 3600:
            continue
        newest = max(newest, at)
        hit = classify(e)
        if not hit or not hit[1]:
            continue
        kind, sym = hit
        if kind == 'stopped' and sym not in mine_:   # only the OWNER's coins: an agent coin's stop is the agents' lesson, not yours
            continue
        c = coin_of(sym) or {}
        if not c.get('mint') or _f(c.get('px')) <= 0:
            continue
        m = {'id': f"{kind}:{c['mint'][:8]}:{int(at)}", 'at': at, 'kind': kind, 'symbol': sym, 'mint': c['mint'], 'pair': c.get('pair'), 'px0': _f(c['px']),
             'card': card_label or (card or {}).get('label') or '', 'engine': kind == 'lock',
             'ctx': {k: c['ctx'][k] for k in CTX_KEYS if (c.get('ctx') or {}).get(k) is not None} or None}   # 📸 the market AT the move: why you did it, read later
        if not any(r.get('id') == m['id'] for r in rows):
            rows.append(m); added.append(m)
    log['seenAt'] = newest
    log['rows'] = rows[-KEEP:]
    return log, added


def verdict(kind, pct):
    """good · bad · flat for a move, from the coin's move since: brought in → up is good; sold → down is good."""
    if kind in OUT_KINDS:
        return 'good' if pct <= -GOOD_PCT else 'bad' if pct >= GOOD_PCT else 'flat'
    return 'good' if pct >= GOOD_PCT else 'bad' if pct <= -GOOD_PCT else 'flat'


def settle(log, price_of, now):
    """Judge every move older than SETTLE_SEC that has a price now (no price after 2h = the coin is gone: −100%). → (log, [settled])."""
    log = dict(log or {}); rows, done = [dict(r) for r in log.get('rows') or []], []
    for r in rows:
        if r.get('pct') is not None or now - _f(r.get('at')) < SETTLE_SEC:
            continue
        px = _f(price_of(r.get('mint')))
        if px <= 0 and now - _f(r.get('at')) < 7200:
            continue
        r['pct'] = round((px / _f(r['px0']) - 1) * 100, 1) if px > 0 and _f(r.get('px0')) > 0 else -100.0
        r['result'] = verdict(r['kind'], r['pct']); r['settledAt'] = now
        done.append(r)
    for r in rows:   # 🕰 the 2h second look (a stop / sale that looked right at 30 min may have been a shake-out)
        if r.get('pct') is not None and r.get('pct2h') is None and now - _f(r.get('at')) >= LATE_SEC:
            px = _f(price_of(r.get('mint')))
            if px > 0 and _f(r.get('px0')) > 0:
                r['pct2h'] = round((px / _f(r['px0']) - 1) * 100, 1)
                r['result2h'] = verdict(r['kind'], r['pct2h'])
    log['rows'] = rows
    return log, done


def shakeouts(log, run=20.0):
    """🛑 Your stops that sold a coin which then ran ≥ `run`% within 2h — the owner's own lesson ("STREAM mooned after my stop")."""
    rows = [r for r in (log or {}).get('rows') or [] if r.get('kind') == 'stopped' and r.get('pct2h') is not None]
    hit = [r for r in rows if r['pct2h'] >= run]
    return {'n': len(rows), 'shaken': len(hit), 'coins': [f"${r.get('symbol')} +{r['pct2h']:.0f}%" for r in hit[-5:]]}


def why_line(r):
    """One line: what the owner did, the market at that moment, and how it turned out."""
    c = r.get('ctx') or {}
    mk = ' · '.join(x for x in (f"5m {c['chg5m']:+.0f}%" if c.get('chg5m') is not None else None, f"buyers {c['buyShare']:.0f}%" if c.get('buyShare') is not None else None,
                               f"1h vol ${c['vol1h'] / 1e3:.0f}K" if c.get('vol1h') else None, f"{c['ageH']:.1f}h old" if c.get('ageH') is not None else None) if x)
    res = f"{r['pct']:+.0f}% at 30m" + (f", {r['pct2h']:+.0f}% at 2h" if r.get('pct2h') is not None else '') if r.get('pct') is not None else 'not judged yet'
    return f"{LABEL.get(r.get('kind'), r.get('kind'))} ${r.get('symbol')}" + (f" when {mk}" if mk else '') + f" → {res}"



def summary(log):
    """The owner's record by kind of move (engine locks left out): n settled, how many good / bad, the typical coin move since."""
    out = {}
    for k in IN_KINDS + OUT_KINDS:
        xs = [r for r in (log or {}).get('rows') or [] if r.get('kind') == k and r.get('pct') is not None and not r.get('engine')]
        if xs:
            ps = sorted(r['pct'] for r in xs)
            out[k] = {'label': LABEL[k], 'n': len(xs), 'good': sum(1 for r in xs if r['result'] == 'good'), 'bad': sum(1 for r in xs if r['result'] == 'bad'), 'medPct': ps[len(ps) // 2]}
    return out


def calls(added, settled):
    """Chat lines worth posting → [(key, text)]: a lock the moment it happens, and every move that turned out GOOD."""
    out = []
    for m in added or []:
        if m.get('kind') == 'lock':
            out.append((f"lock:{m['id']}", f"❄ ${m['symbol']} just locked on {m.get('card') or 'a Fuse card'} — it is riding; the card sells it only off its peak."))
    for r in settled or []:
        if r.get('result') != 'good' or r.get('engine'):
            continue
        mins = max(1, round((_f(r.get('settledAt')) - _f(r.get('at'))) / 60))
        if r['kind'] in OUT_KINDS:
            out.append((f"move:{r['id']}", f"✅ Good exit: {LABEL[r['kind']]} on ${r['symbol']} {mins}m ago ({r.get('card') or 'Fuse card'}) — the coin is {r['pct']:+.0f}% since."))
        else:
            out.append((f"move:{r['id']}", f"✅ Good call: {LABEL[r['kind']]} ${r['symbol']} onto {r.get('card') or 'a Fuse card'} {mins}m ago — {r['pct']:+.0f}% since."))
    return out
