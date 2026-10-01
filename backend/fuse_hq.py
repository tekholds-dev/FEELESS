"""FUSE HQ: the money side of fusing. Pure functions (no I/O) — the service gathers prices and records.

- position_pnl(): a real Fuse-in (verified FEELESS trades, one per leg) valued at live prices → $ and % P&L per leg.
- book(): many positions → totals, winners/losers, per-Fuse rollup (Cmd Ctr P&L tab).
- arena_*: paper $5 runs for evolution champions, settled after 24h — the evidence a strategy works before real money.
- best_style(): the strategy with the best settled arena record (what "Find my best 3" uses for traders).
- health(): a published Fuse vs the latest champion — flags when it has been beaten.
"""
import math

ARENA_USD = 5.0
ARENA_HOURS = 24
MIN_SETTLED = 3        # a style needs this many settled runs before it can be called "best"
BEATEN_BY = 1.10       # champion fitness ≥ 110% of the published Fuse's → "beaten"


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def position_pnl(pos, prices):
    """pos = {legs: [{pairAddress, symbol, usd, tokens}]}; prices = {pairAddress: priceUsd now}."""
    legs, cost, value = [], 0.0, 0.0
    for leg in pos.get('legs') or []:
        c, t, px = _f(leg.get('usd')), _f(leg.get('tokens')), _f(prices.get(leg.get('pairAddress')))
        v = t * px if px > 0 else c          # no live price → shown at cost, never invented
        cost += c; value += v
        legs.append({**leg, 'valueUsd': round(v, 4), 'pnlUsd': round(v - c, 4), 'pnlPct': round((v / c - 1) * 100, 2) if c > 0 else 0.0, 'priced': px > 0})
    return {**{k: pos.get(k) for k in ('id', 'name', 'fuseId', 'at', 'wallet')}, 'legs': legs, 'costUsd': round(cost, 4), 'valueUsd': round(value, 4),
            'pnlUsd': round(value - cost, 4), 'pnlPct': round((value / cost - 1) * 100, 2) if cost > 0 else 0.0}


def book(rows):
    """Totals across valued positions + a rollup per published Fuse (or 'lab' for custom fuses)."""
    cost = sum(r['costUsd'] for r in rows); value = sum(r['valueUsd'] for r in rows)
    per = {}
    for r in rows:
        k = r.get('fuseId') or 'lab'
        a = per.setdefault(k, {'fuseId': k, 'name': r.get('name') or 'Lab fuse', 'positions': 0, 'costUsd': 0.0, 'valueUsd': 0.0, 'wallets': set()})
        a['positions'] += 1; a['costUsd'] += r['costUsd']; a['valueUsd'] += r['valueUsd']; a['wallets'].add(r.get('wallet'))
    fuses = [{**a, 'wallets': len(a['wallets']), 'costUsd': round(a['costUsd'], 2), 'valueUsd': round(a['valueUsd'], 2), 'pnlUsd': round(a['valueUsd'] - a['costUsd'], 2),
              'pnlPct': round((a['valueUsd'] / a['costUsd'] - 1) * 100, 2) if a['costUsd'] else 0.0} for a in per.values()]
    return {'positions': len(rows), 'costUsd': round(cost, 2), 'valueUsd': round(value, 2), 'pnlUsd': round(value - cost, 2),
            'pnlPct': round((value / cost - 1) * 100, 2) if cost else 0.0, 'winners': sum(1 for r in rows if r['pnlUsd'] > 0),
            'losers': sum(1 for r in rows if r['pnlUsd'] < 0), 'fuses': sorted(fuses, key=lambda x: -x['pnlUsd'])}


def arena_entry(champion, style, prices, now, eid):
    """Paper $5 split by the champion's weights at today's prices."""
    legs = [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'weight': _f(l.get('weight')), 'start': _f(prices.get(l['pairAddress']))} for l in champion['legs']]
    legs = [l for l in legs if l['start'] > 0]
    return {'id': eid, 'style': style, 'at': now, 'usd': ARENA_USD, 'fitness': champion.get('fitness'), 'legs': legs}


def arena_value(entry, prices, now):
    """Live (or settled) paper P&L. After ARENA_HOURS the entry settles at its stored close prices."""
    total_w = sum(l['weight'] for l in entry['legs']) or 1
    end = entry.get('close') or prices
    v = sum(entry['usd'] * l['weight'] / total_w * (_f(end.get(l['pairAddress'])) / l['start'] if _f(end.get(l['pairAddress'])) > 0 else 1.0) for l in entry['legs'])
    return {**entry, 'valueUsd': round(v, 4), 'pnlPct': round((v / entry['usd'] - 1) * 100, 2), 'settled': bool(entry.get('close')),
            'due': not entry.get('close') and now - entry['at'] >= ARENA_HOURS * 3600}


def arena_board(values, sol_change_pct=0.0):
    """Per style: settled runs, average and win rate, and whether it beat just holding SOL (sol_change_pct per 24h)."""
    out = {}
    for v in values:
        if not v['settled']:
            continue
        s = out.setdefault(v['style'], {'style': v['style'], 'runs': 0, 'sum': 0.0, 'wins': 0})
        s['runs'] += 1; s['sum'] += v['pnlPct']; s['wins'] += v['pnlPct'] > 0
    rows = [{'style': s['style'], 'runs': s['runs'], 'avgPct': round(s['sum'] / s['runs'], 2), 'winRate': round(s['wins'] / s['runs'] * 100),
             'beatsSol': s['sum'] / s['runs'] > sol_change_pct} for s in out.values()]
    return sorted(rows, key=lambda r: -r['avgPct'])


def best_style(board, default='yield'):
    proven = [r for r in board if r['runs'] >= MIN_SETTLED and r['avgPct'] > 0]
    return proven[0]['style'] if proven else default


def bloodline_seeds(bloodline, available, legs):
    """Saved champions whose pools are all still live (and the right size) seed the next evolution."""
    return [b['pools'] for b in bloodline if len(b['pools']) == legs and all(p in available for p in b['pools'])]


def health(fuse_fitness, champion_fitness):
    beaten = champion_fitness > 0 and fuse_fitness < champion_fitness / BEATEN_BY
    return {'fitness': round(fuse_fitness, 2), 'champion': round(champion_fitness, 2), 'beaten': beaten,
            'gapPct': round((champion_fitness / fuse_fitness - 1) * 100, 1) if fuse_fitness > 0 else None}
