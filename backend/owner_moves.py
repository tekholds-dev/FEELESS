"""🧾 The owner's moves on a real card, recorded and scored (pure, tested).

Every hand move the card's own activity shows — a pick, a hand swap, a rebuy, a profit take, the initial taken out, a ✂ cut —
is noted once with the coin's price at that moment (`collect`), and judged `SETTLE_SEC` later against the price then (`settle`):
a coin you BROUGHT IN is good when it is up 10%+ since, a coin you SOLD / trimmed is good when it is down 10%+ since (you were
right to take it). `summary` is what the paper card that copies the owner, and the owner, read; `calls` turns fresh results
and the card's own locks into short chat lines. Coin moves in %, never the card's $ P&L. A record, never a promise."""
import re

SETTLE_SEC, GOOD_PCT, KEEP = 1800, 10.0, 400
IN_KINDS, OUT_KINDS = ('pick', 'swap', 'rebuy'), ('skim', 'house', 'cut')
LABEL = {'pick': '🎯 pick', 'swap': '⇄ hand swap', 'rebuy': '🔄 rebuy', 'skim': '💰 profit take', 'house': '🏠 initial out', 'cut': '✂ cut', 'lock': '❄ lock'}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


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
    if kind == 'ride' and 'frozen' in why:
        return ('lock', e.get('symbol'))
    return None


def collect(log, card, coin_of, now, card_label=None):
    """New events of this card since the log's last look → noted moves. `coin_of(symbol)` → {'mint', 'pair', 'px'} or None (a move
    whose coin can't be priced is skipped). → (new log, [moves added])."""
    log = dict(log or {})
    seen_at, rows, added = _f(log.get('seenAt')), list(log.get('rows') or []), []
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
        c = coin_of(sym) or {}
        if not c.get('mint') or _f(c.get('px')) <= 0:
            continue
        m = {'id': f"{kind}:{c['mint'][:8]}:{int(at)}", 'at': at, 'kind': kind, 'symbol': sym, 'mint': c['mint'], 'pair': c.get('pair'), 'px0': _f(c['px']),
             'card': card_label or (card or {}).get('label') or '', 'engine': kind == 'lock'}
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
    log['rows'] = rows
    return log, done


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
