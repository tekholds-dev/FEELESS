"""🔁 THE PROOF LOOP (owner 2026-11-04): before any new proof an agent quick-studies the proofs it already filed.

PoW: a coin that looks like one it lost on (same source, same pool and cap size, same direction) is dropped, so a new fingerprint never repeats a loss. It can only make it trade less.
PoB and PoP: the same topic or market keeps one running series, "Loop 3 on lakers parlays", and both minds are told what they called before and how it went.
Pure and tested: the service reads the folders and passes the note on. Every line here comes from a filed folder.
"""
import re

KEEP = 5
_GENERIC = {'best', 'top', 'good', 'great', 'pick', 'picks', 'bid', 'bids', 'bidding', 'bet', 'bets', 'betting', 'parlay', 'parlays', 'choice', 'choices', 'odds', 'game', 'games', 'tonight', 'today',
            'tomorrow', 'this', 'next', 'week', 'for', 'the', 'and', 'on', 'of', 'in', 'to', 'a', 'an', 'my', 'me', 'what', 'who', 'which', 'will', 'win', 'wins', 'keep', 'more', 'file', 'pob', 'proof'}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _size(v, steps):
    return next((i for i, s in enumerate(steps) if _f(v) < s), len(steps))


def coin_sig(c):
    """A coin's shape, not its name: where it came from, its pool size, its cap size, which way it is going."""
    c = c or {}
    ch = _f(c.get('ch'))
    return (str(c.get('src') or ''), _size(c.get('liq'), (20_000, 50_000, 100_000, 500_000)), _size(c.get('mc'), (100_000, 500_000, 2_000_000, 10_000_000)), 'up' if ch > 5 else 'down' if ch < -5 else 'flat')


def _lost(f):
    return f.get('status') == 'closed' and not f.get('propose') and (f.get('pnlSol') is not None and _f(f.get('pnlSol')) < 0)


def _picked(f):
    return next((c for c in f.get('coins') or [] if c.get('mint') == f.get('mint')), None)


def losers(folders):
    """{fingerprint: the loss it came from} from its closed PoW folders. The newest loss names it."""
    out = {}
    for f in folders or []:
        c = _picked(f)
        if c and _lost(f):
            out[coin_sig(c)] = {'n': f.get('n'), 'sym': f.get('sym'), 'pct': round(_f(f.get('pnlPct')), 1), 'why': str(f.get('why') or '')[:60]}
    return out


def repeat_of(coin, lost):
    """The past loss this coin looks like, or None. The same coin, or a safe coin of another shape, passes this check."""
    return (lost or {}).get(coin_sig(coin))


def pow_loop(folders, dropped=()):
    done = [f for f in folders or [] if f.get('status') == 'closed' and f.get('pnlSol') is not None]
    wins = sum(1 for f in done if _f(f.get('pnlSol')) > 0)
    rows = [{'n': f.get('n'), 'at': f.get('at'), 'sym': f.get('sym'), 'pct': round(_f(f.get('pnlPct')), 1), 'why': str(f.get('why') or '')[:60]} for f in done[-KEEP:]][::-1]
    return {'n': len(done) + 1, 'wins': wins, 'losses': len(done) - wins, 'past': rows, 'skipped': [{'sym': d.get('sym'), 'like': d.get('like')} for d in dropped if d.get('like')]}


def pow_note(folders):
    rows = pow_loop(folders)['past']
    if not rows:
        return ''
    return ' YOUR LAST PROOFS, study them first: ' + '; '.join(f"${r['sym']} {r['pct']:+.1f}% ({r['why']})" for r in rows) + '.'


def _key_words(text):
    return {w for w in re.findall(r'[a-z0-9]+', str(text or '').lower()) if w not in _GENERIC and len(w) > 1}


def same_topic(a, b):
    """"lakers parlays" and "best lakers picks tonight" are one series: they share a name that is not a generic betting word."""
    return bool(_key_words(a) & _key_words(b))


def _label(f):
    return f.get('topic') or f.get('q') or ''


def bid_loop(folders, topic):
    rows = [f for f in folders or [] if _label(f) and same_topic(_label(f), topic) and not f.get('noTrade')]
    past = [{'n': f.get('n'), 'at': f.get('at'), 'topic': _label(f)[:80], 'picks': [str(p.get('pick') if isinstance(p, dict) else p)[:60] for p in f.get('agreed') or []][:3], 'mark': f.get('graded'), 'net': f.get('net')} for f in rows[-KEEP:]][::-1]
    return {'n': len(rows) + 1, 'topic': str(topic)[:80], 'right': sum(1 for f in rows if f.get('graded') == 'right'), 'wrong': sum(1 for f in rows if f.get('graded') == 'wrong'), 'past': past}


def bid_note(loop):
    past = (loop or {}).get('past') or []
    if not past:
        return ''
    lines = [f"Folder {r.get('n')}: {', '.join(r['picks']) or 'no shared pick'}" + (f", the owner marked it {r['mark']}" if r.get('mark') else ', not marked yet') for r in past]
    return f"\nThis is loop {loop['n']} on this topic. Your past calls: " + '; '.join(lines) + '. A call marked wrong needs new evidence to be made again. Say what is different this time.'


def perp_loop(folders):
    done = [f for f in folders or [] if f.get('status') == 'closed' and not f.get('noTrade') and f.get('roePct') is not None]
    wins = sum(1 for f in done if _f(f.get('roePct')) > 0)
    past = [{'n': f.get('n'), 'at': f.get('at'), 'market': f.get('market'), 'side': f.get('side'), 'roe': round(_f(f.get('roePct')), 1), 'why': str(f.get('exitWhy') or f.get('why') or '')[:60]} for f in done[-KEEP:]][::-1]
    return {'n': len(done) + 1, 'wins': wins, 'losses': len(done) - wins, 'past': past}


def perp_note(loop):
    past = (loop or {}).get('past') or []
    if not past:
        return ''
    return f"\nThis is loop {loop['n']}. Your last proofs: " + '; '.join(f"{r.get('market')} {r.get('side')} {r['roe']:+.1f}%" for r in past) + '. Study them. A call like a recent loss needs a new reason.'
