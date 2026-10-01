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
        sold = leg.get('soldUsd')
        v = _f(sold) if sold is not None else t * px if px > 0 else c   # unfused leg = realized; no live price → at cost, never invented
        cost += c; value += v
        legs.append({**leg, 'valueUsd': round(v, 4), 'pnlUsd': round(v - c, 4), 'pnlPct': round((v / c - 1) * 100, 2) if c > 0 else 0.0, 'priced': px > 0})
    return {**{k: pos.get(k) for k in ('id', 'name', 'fuseId', 'at', 'wallet', 'closedAt')}, 'closed': all(l.get('soldUsd') is not None for l in legs) and bool(legs), 'legs': legs, 'costUsd': round(cost, 4), 'valueUsd': round(value, 4),
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


def outlook(board):
    """The honest daily outlook: the proven style's settled 24h average → what $1 / $100 became. None until proven."""
    best = next((r for r in board if r['runs'] >= MIN_SETTLED), None)
    if not best:
        return {'proven': False, 'note': f'No strategy has {MIN_SETTLED} settled arena runs yet — run the arena before trusting any number.'}
    return {'proven': best['avgPct'] > 0, 'style': best['style'], 'avgPct': best['avgPct'], 'winRate': best['winRate'], 'runs': best['runs'],
            'per1': round(1 + best['avgPct'] / 100, 3), 'per100': round(100 * (1 + best['avgPct'] / 100), 2),
            'note': f"{best['runs']} settled $5 runs, {best['winRate']}% won. Past 24h results, not a promise."}


def receipt(quoted, actual):
    """Before vs after for one Fuse in. quoted = [{sig, symbol, usd, tokens, feeUsd, networkUsd}] from the review screen;
    actual = {sig: FEELESS trade record (usd, tokens, feelessFeeUsd, networkUsd, via)}. Missing fills show as pending."""
    legs, tot = [], {'quotedUsd': 0.0, 'paidUsd': 0.0, 'quotedFeesUsd': 0.0, 'paidFeesUsd': 0.0}
    for q in quoted:
        a = actual.get(q.get('sig')) or {}
        row = {'symbol': q.get('symbol'), 'sig': q.get('sig'), 'quotedUsd': round(_f(q.get('usd')), 4), 'quotedTokens': _f(q.get('tokens')),
               'quotedFeesUsd': round(_f(q.get('feeUsd')) + _f(q.get('networkUsd')), 4), 'pending': not a}
        tot['quotedUsd'] += row['quotedUsd']; tot['quotedFeesUsd'] += row['quotedFeesUsd']
        if a:
            paid, got = _f(a.get('usd')), _f(a.get('tokens'))
            fees = _f(a.get('feelessFeeUsd')) + _f(a.get('networkUsd'))
            row.update(paidUsd=round(paid, 4), gotTokens=got, paidFeesUsd=round(fees, 4), exact=a.get('via') == 'chain',
                       slippagePct=round((row['quotedTokens'] - got) / row['quotedTokens'] * 100, 2) if row['quotedTokens'] > 0 and got > 0 else None)
            tot['paidUsd'] += paid; tot['paidFeesUsd'] += fees
        legs.append(row)
    done = [x for x in legs if not x['pending']]
    return {'legs': legs, **{k: round(v, 4) for k, v in tot.items()}, 'settled': len(done) == len(legs) and bool(legs),
            'feePct': round(tot['paidFeesUsd'] / tot['paidUsd'] * 100, 2) if tot['paidUsd'] else round(tot['quotedFeesUsd'] / tot['quotedUsd'] * 100, 2) if tot['quotedUsd'] else 0.0}


AUTOPILOT_EVERY = 3600


def autopilot_due(arena, style, now, every=AUTOPILOT_EVERY):
    """True when `style` has no autopilot arena entry in the last `every` seconds (one paper run per style per hour)."""
    return not any(e.get('style') == style and e.get('auto') and now - e.get('at', 0) < every for e in arena or [])


def trust_rank(points, buyers, trusted):
    """Published Fuse ordering: grade points + up to 15 for a buyer base that is mostly real (not bots / self-buys).
    Needs ≥5 buyers for the full boost so one friend can't game it."""
    if not buyers:
        return float(points)
    return round(points + 15 * (trusted / buyers) * min(1.0, buyers / 5), 2)


def close_legs(pos, sells):
    """Unfuse: attach realized $ to each leg from the wallet's verified SELL trades of that leg's coin (sig → record).
    A leg can be closed once; returns (updated pos, legs closed now)."""
    n = 0
    for leg in pos.get('legs') or []:
        if leg.get('soldUsd') is not None:
            continue
        hit = next((t for t in sells if t.get('token') == leg.get('mint')), None)
        if hit:
            leg['soldUsd'] = round(_f(hit.get('usd')), 6); leg['sellSig'] = hit.get('tx'); n += 1
    return pos, n


# ---- Fuse cards (NFT): one 1/1 Metaplex Core asset per published Fuse; its HOLDER is paid the creator cut ----------
RARITY = {'A': 'Legendary', 'B': 'Epic', 'C': 'Rare', 'D': 'Common', 'F': 'Common'}


def _esc(t):
    return str(t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def card_meta(fid, view, site):
    """Metaplex JSON for a Fuse card: name, image (our SVG), attributes = the Fuse's real makeup at mint time."""
    g = (view.get('score') or {}).get('grade', 'C')
    return {'name': f"FUSE · {view.get('name', 'Fuse')}"[:32], 'symbol': 'FUSE',
            'description': f"FEELESS Fuse card. Holder earns the creator cut ({(view.get('creatorBps') or 0) / 100:g}% of the FEELESS fee) on every verified buy of this Fuse.",
            'image': f'{site}/api/reputation/fuse-card/{fid}.svg', 'external_url': f'{site}/terminal/trade?tab=fuse',
            'attributes': [{'trait_type': 'Grade', 'value': g}, {'trait_type': 'Rarity', 'value': RARITY.get(g, 'Rare')},
                           {'trait_type': 'Pools', 'value': len(view.get('legs') or [])}, {'trait_type': 'Creator cut', 'value': f"{(view.get('creatorBps') or 0) / 100:g}%"}]
            + [{'trait_type': f"Leg {i + 1}", 'value': f"{l.get('symbol')} {round(_f(l.get('weight')))}%"} for i, l in enumerate((view.get('legs') or [])[:10])],
            'properties': {'category': 'image', 'files': [{'uri': f'{site}/api/reputation/fuse-card/{fid}.svg', 'type': 'image/svg+xml'}]}}


def card_svg(view):
    """A static card image (no scripts, escaped text) in the MetaCard layout: label + pips, grade crest, name, legs, footer."""
    g = (view.get('score') or {}).get('grade', 'C')
    pips = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1}.get(g, 3)
    legs = (view.get('legs') or [])[:5]
    rows = ''.join(f'<text x="40" y="{318 + i * 22}" font-size="15" fill="#eafff3" font-family="monospace">{_esc(l.get("symbol"))}</text>'
                   f'<text x="340" y="{318 + i * 22}" font-size="15" fill="#19f58f" text-anchor="end" font-family="monospace">{round(_f(l.get("weight")))}%</text>' for i, l in enumerate(legs))
    dots = ''.join(f'<rect x="{292 + i * 13}" y="34" width="8" height="8" transform="rotate(45 {296 + i * 13} 38)" fill="{"#19f58f" if i < pips else "none"}" stroke="#19f58f"/>' for i in range(5))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 532" width="380" height="532">'
            f'<defs><radialGradient id="b" cx="50%" cy="0%" r="90%"><stop offset="0" stop-color="#19f58f" stop-opacity=".35"/><stop offset="1" stop-color="#030a06"/></radialGradient></defs>'
            f'<rect x="4" y="4" width="372" height="524" rx="28" fill="url(#b)" stroke="#f5c451" stroke-width="3"/>'
            f'<text x="34" y="44" font-size="16" letter-spacing="3" fill="#19f58f" font-family="monospace">FUSE</text>{dots}'
            f'<circle cx="190" cy="160" r="78" fill="#020805" stroke="#19f58f" stroke-width="4"/><circle cx="190" cy="160" r="92" fill="none" stroke="#f5c451" stroke-dasharray="2 6"/>'
            f'<text x="190" y="185" font-size="72" text-anchor="middle" fill="#eafff3" font-family="sans-serif" font-weight="700">{_esc(g)}</text>'
            f'<text x="190" y="282" font-size="24" text-anchor="middle" fill="#ffffff" font-family="sans-serif" font-weight="700">{_esc(view.get("name"))[:22]}</text>{rows}'
            f'<line x1="34" y1="470" x2="346" y2="470" stroke="#19f58f" stroke-opacity=".3"/>'
            f'<text x="34" y="500" font-size="14" fill="#9fd9b8" font-family="monospace">{RARITY.get(g, "Rare").upper()}</text>'
            f'<text x="346" y="500" font-size="14" fill="#f5c451" text-anchor="end" font-family="monospace">FEELESS</text></svg>')


# ---- Basket limits: take-profit / stop-loss / trailing stop on a whole Fuse position ---------------------------------
def clean_guard(g):
    """tp/sl/trail in % (tp 1–1000, sl 1–95, trail 1–90); any may be off (None). At least one must be set."""
    def pct(v, lo, hi):
        x = _f(v)
        return round(min(hi, max(lo, x)), 2) if x > 0 else None
    out = {'tp': pct(g.get('tp'), 1, 1000), 'sl': pct(g.get('sl'), 1, 95), 'trail': pct(g.get('trail'), 1, 90)}
    if not any(out.values()):
        raise ValueError('Set a take-profit, stop-loss or trailing stop.')
    return out


def guard_check(guard, pnl_pct):
    """→ (hit, peak). hit = 'tp' | 'sl' | 'trail' | None. Trailing fires when the basket falls `trail` points below its best."""
    peak = max(_f(guard.get('peak')), pnl_pct)
    if guard.get('tp') and pnl_pct >= guard['tp']:
        return 'tp', peak
    if guard.get('sl') and pnl_pct <= -guard['sl']:
        return 'sl', peak
    if guard.get('trail') and peak > 0 and peak - pnl_pct >= guard['trail']:
        return 'trail', peak
    return None, peak


MIN_BUYERS = 2
APR_CAP = 400.0          # same cap the engine uses: higher "APR" on DexScreener is usually wash volume


def creator_board(rows, fuses, since=0):
    """Weekly Fuse creator season: creators ranked by their BUYERS' combined real P&L on Fuses opened since `since`.
    rows = valued positions (position_pnl + wallet + fuseId); fuses = {fid: {creator, name}}. The creator's own buys don't
    count; a creator needs MIN_BUYERS outside buyers to rank (no farming with one friend)."""
    by = {}
    for r in rows:
        f = fuses.get(r.get('fuseId') or '')
        if not f or (r.get('at') or 0) < since or r.get('wallet') == f.get('creator'):
            continue
        c = by.setdefault(f['creator'], {'creator': f['creator'], 'fuses': set(), 'buyers': set(), 'costUsd': 0.0, 'valueUsd': 0.0, 'wins': 0, 'n': 0})
        c['fuses'].add(f.get('name')); c['buyers'].add(r['wallet']); c['costUsd'] += r['costUsd']; c['valueUsd'] += r['valueUsd']; c['n'] += 1; c['wins'] += r['pnlUsd'] > 0
    out = [{'creator': c['creator'], 'fuses': sorted(x for x in c['fuses'] if x)[:3], 'buyers': len(c['buyers']), 'costUsd': round(c['costUsd'], 2),
            'pnlPct': round((c['valueUsd'] / c['costUsd'] - 1) * 100, 2) if c['costUsd'] else 0.0, 'winRate': round(c['wins'] / c['n'] * 100), 'ranked': len(c['buyers']) >= MIN_BUYERS}
           for c in by.values()]
    return sorted(out, key=lambda x: (not x['ranked'], -x['pnlPct'], -x['buyers']))


def yield_math(metas, min_liq=100_000):
    """Where $1/day can come from, on live pools (no promises):
    - Vault (LP fees): deep pools' fee APR → $ per day per $1/$20/$100, and the APR it would take for +20c/+50c a day on $1.
    - Fuse (price moves): what the same pools' 24h moves did to $1 — best, median, worst."""
    deep = [m for m in metas.values() if _f(m.get('liquidityUsd')) >= min_liq]
    aprs = sorted((min(APR_CAP, _f(m.get("aprEst"))) for m in deep), reverse=True)
    top = aprs[:3]
    apr = sum(top) / len(top) if top else 0.0
    per_day = lambda usd: round(usd * apr / 100 / 365, 4)
    moves = sorted(_f(m.get('change24h')) for m in deep)
    med = moves[len(moves) // 2] if moves else 0.0
    return {'pools': len(deep), 'vaultAprPct': round(apr, 1), 'vaultPerDay': {'1': per_day(1), '20': per_day(20), '100': per_day(100)},
            'aprFor20c': 7300.0, 'aprFor50c': 18250.0,
            'fuse1': {'best': round(1 + (moves[-1] if moves else 0) / 100, 3), 'median': round(1 + med / 100, 3), 'worst': round(1 + (moves[0] if moves else 0) / 100, 3)}}
