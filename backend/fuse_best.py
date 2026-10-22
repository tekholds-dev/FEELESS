"""🏆 BEST SETTINGS FOR THE FUSE ARENA (owner, 2026-10-22: "we need to see the best settings for Fuse Arena"). Pure + tested.

From the Arena's own scored cards (fuse_hq.json `arena`: style, fitness = the Arena's score, legs with weights): which STYLES score best (median,
with how many cards back it), and what the TOP QUARTER of cards share vs the rest — how many coins, how concentrated the biggest leg is, how much
sits in majors (SOL / ETH / BTC and their wrapped forms) — plus the three best cards to copy. Evidence, never a promise.
"""
import statistics as _st

MAJORS = {'SOL', 'WSOL', 'ETH', 'WETH', 'BTC', 'WBTC', 'CBBTC', 'JITOSOL', 'MSOL', 'JUPSOL'}
MIN_STYLE = 8


def _shape(card):
    legs = card.get('legs') or []
    w = [float(l.get('weight') or 0) for l in legs]; tot = sum(w) or 1.0
    return {'legs': len(legs), 'maxW': round(max(w) / tot * 100, 1) if w else 0.0,
            'majorW': round(sum(x for x, l in zip(w, legs) if str(l.get('symbol') or '').upper() in MAJORS) / tot * 100, 1)}


def best(arena):
    cards = [c for c in (arena or []) if isinstance(c, dict) and isinstance(c.get('fitness'), (int, float))]
    if not cards:
        return {'n': 0, 'styles': [], 'top': None, 'rest': None, 'cards': []}
    by = {}
    for c in cards:
        by.setdefault(str(c.get('style') or '?'), []).append(c['fitness'])
    styles = sorted(({'style': k, 'n': len(v), 'medFit': round(_st.median(v), 1)} for k, v in by.items() if len(v) >= MIN_STYLE), key=lambda s: -s['medFit'])
    srt = sorted(cards, key=lambda c: -c['fitness']); q = max(1, len(srt) // 4)
    avg = lambda xs, k: round(sum(_shape(c)[k] for c in xs) / len(xs), 1) if xs else None
    top, rest = srt[:q], srt[q:]
    return {'n': len(cards), 'styles': styles[:6],
            'top': {'fit': round(_st.median(c['fitness'] for c in top), 1), 'legs': avg(top, 'legs'), 'maxW': avg(top, 'maxW'), 'majorW': avg(top, 'majorW')},
            'rest': {'fit': round(_st.median(c['fitness'] for c in rest), 1), 'legs': avg(rest, 'legs'), 'maxW': avg(rest, 'maxW'), 'majorW': avg(rest, 'majorW')} if rest else None,
            'cards': [{'id': c.get('id'), 'style': c.get('style'), 'fitness': c['fitness'], 'legs': [{'symbol': l.get('symbol'), 'weight': l.get('weight')} for l in c.get('legs') or []]} for c in srt[:3]]}
