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
    """pos = {legs: [{pairAddress, symbol, usd, tokens, realizedUsd?, soldUsd?, role?}]}; prices = {pairAddress: priceUsd now}.
    A leg's value = what's still held × live price + what was already taken out (take-profits, switches). Fully sold legs
    use their realized $. No live price → held part at cost, never invented."""
    legs, cost, value = [], 0.0, 0.0
    for leg in pos.get('legs') or []:
        c, t, px = _f(leg.get('usd')), _f(leg.get('tokens')), _f(prices.get(leg.get('pairAddress')))
        realized = _f(leg.get('realizedUsd'))
        if leg.get('soldUsd') is not None:
            held, v = 0.0, _f(leg['soldUsd'])
        else:
            t0 = _f(leg.get('tokens0')) or t
            held = t * px if px > 0 else c * (t / t0 if t0 else 1)
            v = held + realized
        cost += c; value += v
        legs.append({**leg, 'heldUsd': round(held, 4), 'valueUsd': round(v, 4), 'pnlUsd': round(v - c, 4), 'pnlPct': round((v / c - 1) * 100, 2) if c > 0 else 0.0,
                     'priced': px > 0, 'priceNow': px or None, 'priceIn': round(c / (_f(leg.get('tokens0')) or t), 12) if (_f(leg.get('tokens0')) or t) else None})
    return {**{k: pos.get(k) for k in ('id', 'name', 'fuseId', 'at', 'wallet', 'closedAt', 'events')}, 'closed': all(l.get('soldUsd') is not None for l in legs) and bool(legs), 'legs': legs, 'costUsd': round(cost, 4), 'valueUsd': round(value, 4),
            'realizedUsd': round(sum(_f(l.get('soldUsd')) if l.get('soldUsd') is not None else _f(l.get('realizedUsd')) for l in legs), 4),
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


def pool_usd(t):
    """A trade's $ at the pool — fees EXCLUDED (FEELESS + network are paid per trade and shown on the receipt, never mixed
    into a card's entry or P&L). Falls back to cash $ for records without a pool value."""
    return _f(t.get('poolUsd')) if t.get('poolUsd') is not None else _f(t.get('usd'))


def close_legs(pos, sells, now=0):
    """Sell from a card (take-profit, switch-out or full withdraw): each verified SELL of a leg's coin moves its $ into
    realizedUsd and its tokens out of the held amount. A leg whose held tokens hit ~0 is closed (soldUsd = all it
    realized). Sells without a token amount count as selling the whole leg. Returns (pos, legs touched)."""
    n = 0
    for t in sells:
        leg = next((l for l in pos.get('legs') or [] if l.get('mint') == t.get('token') and l.get('soldUsd') is None), None)
        if not leg:
            continue
        leg.setdefault('tokens0', leg.get('tokens'))
        sold = _f(t.get('tokens')) or _f(leg.get('tokens'))
        leg['realizedUsd'] = round(_f(leg.get('realizedUsd')) + pool_usd(t), 6)
        leg['tokens'] = max(0.0, _f(leg.get('tokens')) - sold)
        leg.setdefault('sellSigs', []).append(t.get('tx'))
        if leg['tokens'] <= _f(leg['tokens0']) * 0.001:
            leg['soldUsd'] = leg['realizedUsd']; leg['sellSig'] = t.get('tx'); leg['tokens'] = 0.0
        pos.setdefault('events', []).append({'kind': 'sell', 'symbol': leg.get('symbol'), 'usd': round(pool_usd(t), 4), 'at': now})
        n += 1
    return pos, n


def add_legs(pos, buys, metas, now=0, max_pools=3, max_runners=3):
    """Switch-in / top-up: verified BUY trades become new legs (role pool|runner), within the card's limits."""
    legs = pos.setdefault('legs', [])
    live = lambda role: sum(1 for l in legs if l.get('soldUsd') is None and (l.get('role') or 'pool') == role)
    added = 0
    for t, m in zip(buys, metas):
        role = 'runner' if m.get('role') == 'runner' else 'pool'
        if _f(t.get('tokens')) <= 0:
            continue
        same = next((l for l in legs if l.get('soldUsd') is None and l.get('mint') == t.get('token')), None)
        if same:   # rebalance top-up: the leg grows, it doesn't count as a new leg
            same['usd'] = round(_f(same.get('usd')) + pool_usd(t), 6); same['tokens'] = _f(same.get('tokens')) + _f(t.get('tokens'))
            same['tokens0'] = _f(same.get('tokens0') or same.get('tokens')) + _f(t.get('tokens'))
            pos.setdefault('events', []).append({'kind': 'topup', 'symbol': same.get('symbol'), 'usd': round(pool_usd(t), 4), 'at': now}); added += 1
            continue
        if live(role) >= (max_runners if role == 'runner' else max_pools):
            continue
        legs.append({'pairAddress': str(m.get('pairAddress'))[:64], 'chainId': 'solana', 'symbol': str(m.get('symbol') or '')[:16], 'role': role,
                     'mint': t.get('token'), 'sig': t.get('tx'), 'usd': pool_usd(t), 'tokens': _f(t.get('tokens')), 'tokens0': _f(t.get('tokens')), 'addedAt': now})
        pos.setdefault('events', []).append({'kind': 'buy', 'symbol': m.get('symbol'), 'usd': round(pool_usd(t), 4), 'at': now})
        added += 1
    return pos, added


CARD_POOLS, CARD_RUNNERS = 3, 3
ADMIN_POOLS, ADMIN_RUNNERS = 12, 12   # Cmd Ctr: any mix up to ADMIN_LEGS in total (6 pools + 6 runners, or 12 runners)
ADMIN_LEGS = 12
FEE_FOR_3RD_CARD = 200.0


def legs_ok(pools, runners, admin=False):
    """A card's leg mix: traders 3 pools + 3 runners; Cmd Ctr up to 12 legs in any mix."""
    if admin:
        return pools <= ADMIN_POOLS and runners <= ADMIN_RUNNERS and pools + runners <= ADMIN_LEGS
    return pools <= CARD_POOLS and runners <= CARD_RUNNERS


BUNDLE_DEFAULTS = {'on': True, 'perLegUsd': 0.10, 'maxPct': 5.0, 'maxLegUsd': 50.0}
BUNDLE_RANGES = {'perLegUsd': (0.0, 5.0), 'maxPct': (0.1, 20.0), 'maxLegUsd': (1.0, 10000.0)}


def clean_bundle(b):
    b = b if isinstance(b, dict) else {}
    out = {'on': bool(b.get('on', BUNDLE_DEFAULTS['on']))}
    for k, (lo, hi) in BUNDLE_RANGES.items():
        try:
            out[k] = round(max(lo, min(hi, float(b.get(k, BUNDLE_DEFAULTS[k])))), 4)
        except (TypeError, ValueError):
            out[k] = BUNDLE_DEFAULTS[k]
    return out


def bundle_bps(leg_usd, b):
    """Bundle pricing (a Fuse / runner card bought all at once): a flat $ per coin instead of a %, never more than maxPct
    of the leg. Legs above maxLegUsd (or unknown size) pay the normal % fee → None."""
    b = clean_bundle(b)
    leg_usd = _f(leg_usd)
    if not b['on'] or leg_usd <= 0 or leg_usd > b['maxLegUsd']:
        return None
    return int(min(round(b['perLegUsd'] / leg_usd * 10000), round(b['maxPct'] * 100)))


def fuse_fees(positions, ledger_rows, now):
    """Live FEELESS fees from people fusing: every Fuse card leg (buys + sells) matched by signature to the fee ledger
    (the source of truth). → $ per hour / 24h / 7d / all time, legs and cards counted."""
    by_sig = {r.get('sig'): r for r in ledger_rows if r.get('sig')}
    sigs, cards = set(), set()
    for pos in positions or []:
        for leg in pos.get('legs') or []:
            for sg in [leg.get('sig'), *(leg.get('sellSigs') or [leg.get('sellSig')])]:
                if sg in by_sig:
                    sigs.add(sg); cards.add(pos.get('id'))
    rows = [by_sig[s] for s in sigs]
    win = lambda sec: round(sum(_f(r.get('feeUsd')) for r in rows if now - _f(r.get('t')) <= sec), 6)
    return {'hour': win(3600), 'day': win(86400), 'week': win(7 * 86400), 'all': round(sum(_f(r.get('feeUsd')) for r in rows), 6),
            'legs': len(rows), 'cards': len(cards)}


ACTIVITY_TIERS = ((75, 'blazing'), (50, 'hot'), (25, 'warm'), (0, 'calm'))


def activity(buys24h=0, buyers=0, flow_usd=0.0, move_pct=0.0):
    """A card's live activity 0–100 (drives its Arena effects — hard-coded tiers, never a forecast):
    real FEELESS buys in 24h, distinct buyers, $ flow through its pools, and how far its index moved."""
    s = (min(35.0, _f(buys24h) * 5) + min(25.0, _f(buyers) * 5) + min(25.0, math.log10(1 + max(0.0, _f(flow_usd))) * 4.2)
         + min(15.0, abs(_f(move_pct)) * 0.75))
    s = round(max(0.0, min(100.0, s)))
    return {'score': s, 'tier': next(t for cut, t in ACTIVITY_TIERS if s >= cut)}


def card_limit(fee_usd, admin=False):
    """Open Fuse cards a wallet may hold: 2, or 3 when it holds ≥ $200 of $FEE (admin: 10)."""
    return 10 if admin else 3 if _f(fee_usd) >= FEE_FOR_3RD_CARD else 2


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


def drift(row):
    """Largest gap (percentage points) between a leg's share of what's held now and its share of what was put in."""
    open_ = [l for l in row.get('legs') or [] if l.get('soldUsd') is None]
    cost = sum(_f(l.get('usd')) for l in open_); held = sum(_f(l.get('heldUsd')) for l in open_)
    if cost <= 0 or held <= 0 or len(open_) < 2:
        return 0.0
    return round(max(abs(_f(l.get('heldUsd')) / held - _f(l.get('usd')) / cost) * 100 for l in open_), 2)


# ---- Auto-collect (💸 collect profit at +X%) ---------------------------------------------------------------------
# Non-custodial: FEELESS never signs for a holder. "Auto" = an armed rule: when the card's HELD value reaches
# base × (1 + at%), the holder gets ONE alert with a pre-filled "Collect profit" that sells only the gain (their base
# stays in the card). After they collect, the rule re-arms from the new held value, so it never re-fires on the same gain.
YIELD_DEFAULT_AT = 50.0


def clean_yield_at(v):
    x = _f(v)
    if not 10 <= x <= 1000:
        raise ValueError('Collect-profit trigger must be between +10% and +1000%.')
    return round(x, 1)


def held_value(r):
    """What is still in the card now: total value minus what was already taken out."""
    return max(0.0, _f(r.get('valueUsd')) - _f(r.get('realizedUsd')))


def yield_due(r, y, exit_fee=0.0):
    """Due when what you'd walk away with (held − estimated exit fees) ≥ base × (1 + at%). base = your confirmed buy
    + its FEELESS fee (then the held value after each collect), so the trigger is net of fees both ways."""
    base = _f((y or {}).get('base'))
    return bool(y) and not y.get('firedAt') and not y.get('rebase') and base > 0 and held_value(r) - _f(exit_fee) >= base * (1 + _f(y.get('at')) / 100)


# ---- Card rules (Cmd Ctr › Fuse › Card rules): auto-profit levels, swap mode, Arena top tier, Fuse Fee-Back -----------
CARD_RULES = {'yieldLevels': [25, 50, 100, 200], 'yieldDefault': 50, 'netFeeUsdPerLeg': 0.01, 'swapDropPct': 25, 'topTierPct': 50,
              'fbHolderPct': 20, 'fbHoldHours': 24, 'fbLoyaltyPct': 10, 'fbLoyaltyDays': 7, 'fbArenaPct': 10, 'fbCapPct': 50, 'copyPct': 10, 'seasonBoostPct': 10}
RULE_RANGES = {'netFeeUsdPerLeg': (0, 1), 'swapDropPct': (5, 90), 'topTierPct': (5, 1000), 'fbHolderPct': (0, 100), 'fbHoldHours': (1, 720),
               'fbLoyaltyPct': (0, 100), 'fbLoyaltyDays': (1, 90), 'fbArenaPct': (0, 100), 'fbCapPct': (0, 100), 'copyPct': (0, 50), 'seasonBoostPct': (0, 100)}


def clean_rules(r):
    r = r if isinstance(r, dict) else {}
    out = {}
    for k, (lo, hi) in RULE_RANGES.items():
        try:
            out[k] = round(max(lo, min(hi, float(r.get(k, CARD_RULES[k])))), 4)
        except (TypeError, ValueError):
            out[k] = CARD_RULES[k]
    lv = []
    for v in r.get('yieldLevels') or CARD_RULES['yieldLevels']:
        try:
            lv.append(clean_yield_at(v))
        except (ValueError, TypeError):
            continue
    out['yieldLevels'] = sorted(set(lv))[:6] or CARD_RULES['yieldLevels']
    d = _f(r.get('yieldDefault', CARD_RULES['yieldDefault']))
    out['yieldDefault'] = min(out['yieldLevels'], key=lambda x: abs(x - d))
    return out


def exit_fee_usd(r, bundle, swap_bps, net_per_leg=0.01):
    """Estimated fees to sell what's still held: FEELESS fee per leg (bundle price when 2+ legs go together, else the %)
    + a network fee per leg."""
    open_legs = [l for l in r.get('legs') or [] if l.get('soldUsd') is None and _f(l.get('heldUsd')) > 0]
    fee = 0.0
    for l in open_legs:
        h = _f(l.get('heldUsd'))
        bps = bundle_bps(h, bundle) if len(open_legs) >= 2 else None
        fee += h * (bps if bps is not None else _f(swap_bps)) / 10000 + _f(net_per_leg)
    return round(fee, 6)


def swap_suggest(r, failing, passing, drop_pct):
    """Swap mode: the ONE weakest leg that fails a runner gate now or is down ≥ drop_pct, and the best gated runner to
    replace it (not already in the card). Hold mode never calls this. → {'out', 'in', 'why'} or None."""
    have = {l.get('mint') for l in r.get('legs') or []} | {l.get('pairAddress') for l in r.get('legs') or []}
    weak = []
    for l in r.get('legs') or []:
        if l.get('soldUsd') is not None:
            continue
        if l.get('mint') in failing:
            weak.append((0, l, f"fails a gate: {(failing[l['mint']] or ['gate'])[0]}"))
        elif _f(l.get('pnlPct')) <= -abs(_f(drop_pct)):
            weak.append((1, l, f"down {_f(l.get('pnlPct')):.1f}% (swap at −{_f(drop_pct):g}%)"))
    pick = next((p for p in sorted(passing, key=lambda p: -_f(p.get('score'))) if p.get('mint') not in have and p.get('pairAddress') not in have), None)
    if not weak or not pick:
        return None
    _, leg, why = sorted(weak, key=lambda w: (w[0], _f(w[1].get('pnlPct'))))[0]
    return {'out': {k: leg.get(k) for k in ('pairAddress', 'mint', 'symbol', 'heldUsd')}, 'in': {k: pick.get(k) for k in ('mint', 'symbol', 'pairAddress', 'logo', 'score')}, 'why': why}


STREAK_TIERS = ((5, 'immortal', '👑 Immortal'), (3, 'phoenix', '🔥 Phoenix'), (1, 'survivor', '🛡 Survivor'))


def swap_streak(r):
    """Swap streak: how many weak legs a card swapped out (each switch-in = a 'buy' event) and whether it still wins.
    Survivor ≥1 swap, Phoenix ≥3, Immortal ≥5 — only while the card is up. Bonus activity: +5 per swap (max 15)."""
    swaps = sum(1 for e in r.get('events') or [] if e.get('kind') == 'buy')
    won = _f(r.get('pnlPct')) > 0
    hit = next(((k, lab) for n, k, lab in STREAK_TIERS if swaps >= n), None) if won else None
    return {'swaps': swaps, 'won': won, 'tier': hit[0] if hit else None, 'label': hit[1] if hit else None, 'bonus': min(15, swaps * 5) if hit else 0}


COMPOUND_TIERS = ((5, 'diamond', '💎 Diamond loop'), (3, 'snowball', '❄ Snowball'), (1, 'compounder', '♻ Compounder'))
COMPOUND_GAP = 600   # top-ups within 10 min are one compound


def compound_streak(r):
    """Compound streak: how many times a card rolled its gains back in (bursts of top-up events) and still wins.
    ♻ Compounder ≥1 · ❄ Snowball ≥3 · 💎 Diamond loop ≥5. +5 Arena activity per compound (max 15)."""
    ts = sorted(_f(e.get('at')) for e in r.get('events') or [] if e.get('kind') == 'topup')
    n = sum(1 for i, x in enumerate(ts) if i == 0 or x - ts[i - 1] > COMPOUND_GAP)
    won = _f(r.get('pnlPct')) > 0
    hit = next(((k, lab) for c, k, lab in COMPOUND_TIERS if n >= c), None) if won else None
    return {'compounds': n, 'won': won, 'tier': hit[0] if hit else None, 'label': hit[1] if hit else None, 'bonus': min(15, n * 5) if hit else 0}


MEDAL_PTS = {1: 15, 2: 10, 3: 6}
STREAK_PTS = {'survivor': 4, 'phoenix': 8, 'immortal': 12, 'compounder': 4, 'snowball': 8, 'diamond': 12}


def fuse_score(rows, wins, copies, trust, bot=False, cat_wins=0):
    """Fuse score 0–100 for a wallet, every point cited. perf (≤75) = real verified card P&L + season medals + copies
    received + best streaks + cards held ≥24h; rep (≤25) = trust score × 0.25. Bots score 0. Trust reads `perf` only
    (never the rep half), so the two never feed each other in a loop."""
    if bot:
        return {'score': 0, 'perf': 0, 'rep': 0, 'parts': [{'label': 'Bot shield: flagged — Fuse score withheld', 'points': 0}], 'cards': len(rows)}
    parts = []
    cost = sum(_f(r.get('costUsd')) for r in rows); val = sum(_f(r.get('valueUsd')) for r in rows)
    if cost >= 5:
        pct = (val / cost - 1) * 100
        p = round(max(-15.0, min(30.0, pct * 0.6)), 1)
        parts.append({'label': f"Real card P&L {pct:+.1f}% on ${cost:,.0f} (verified buys)", 'points': p})
    med = sorted((w['rank'] for w in wins), key=int)
    if med:
        parts.append({'label': f"Season medals: {' '.join({1: '🥇', 2: '🥈', 3: '🥉'}[m] for m in med)}", 'points': min(25, sum(MEDAL_PTS[m] for m in med))})
    if copies:
        parts.append({'label': f"Copied {copies}× by other traders", 'points': min(15, 3 * copies)})
    sw = max((STREAK_PTS.get((r.get('streak') or {}).get('tier'), 0) for r in rows), default=0)
    cp = max((STREAK_PTS.get((r.get('compound') or {}).get('tier'), 0) for r in rows), default=0)
    if sw or cp:
        parts.append({'label': 'Best swap / compound streaks', 'points': min(15, sw + cp)})
    if cat_wins:
        parts.append({'label': f"🐱 Beat FeeCat {cat_wins}× (weekly)", 'points': min(2 * CAT_WIN_PTS, CAT_WIN_PTS * cat_wins)})
    held = sum(1 for r in rows if _f(r.get('heldS')) >= 86400)
    if held:
        parts.append({'label': f"{held} card(s) held 24h+", 'points': min(10, 2 * held)})
    perf = round(max(0.0, min(75.0, sum(x['points'] for x in parts))), 1)
    rep = round(max(0.0, min(25.0, _f(trust) * 0.25)), 1) if trust is not None else 0.0
    if trust is not None:
        parts.append({'label': f"Reputation (trust {round(_f(trust))}/100)", 'points': rep})
    return {'score': round(min(100.0, perf + rep)), 'perf': perf, 'rep': rep, 'parts': parts, 'cards': len(rows)}


def trust_from_fuse(perf, cards):
    """The Fuse half that flows back into reputation: −3…+6 trust points, only with 2+ cards of evidence."""
    return 0 if cards < 2 else int(max(-3, min(6, round((_f(perf) - 25) / 8))))


def rank_moves(prev, board):
    """Season race: cards whose rank changed since the last board ({id: rank} → board rows)."""
    out = []
    for b in board:
        was = prev.get(b['id'])
        if was != b['rank']:
            out.append({'id': b['id'], 'name': b.get('name'), 'handle': b.get('handle'), 'from': was, 'to': b['rank'], 'pnlPct': b.get('pnlPct'),
                        'kind': 'new' if was is None else 'up' if b['rank'] < was else 'down'})
    return out


# ---- 💸 Weekly creator payouts (owner-signed, verified on-chain) ------------------------------------------------------
PAYOUT_MIN_USD = 0.05   # dust below this waits for next week (network fees would eat it)


def payout_plan(book_rows, sol_usd, exclude=(), min_usd=PAYOUT_MIN_USD):
    """Who is owed Fuse Fee-Back + copy cuts and how much SOL that is at today's price. Never pays excluded wallets
    (FEELESS / flagged bots); dust waits."""
    if _f(sol_usd) <= 0:
        return {'rows': [], 'totalUsd': 0.0, 'totalSol': 0.0, 'solUsd': 0.0}
    rows = [{'wallet': r['wallet'], 'owedUsd': round(_f(r['owedUsd']), 6), 'sol': round(_f(r['owedUsd']) / _f(sol_usd), 9)}
            for r in book_rows if _f(r.get('owedUsd')) >= min_usd and r['wallet'] not in set(exclude)]
    rows.sort(key=lambda r: -r['owedUsd'])
    return {'rows': rows, 'totalUsd': round(sum(r['owedUsd'] for r in rows), 6), 'totalSol': round(sum(r['sol'] for r in rows), 9), 'solUsd': round(_f(sol_usd), 4)}


def credit_paid(paid_sol, plan):
    """$ credited per wallet = what actually moved on-chain × the plan's SOL price, never more than that wallet was owed."""
    owed = {r['wallet']: r['owedUsd'] for r in plan.get('rows') or []}
    return {w: round(min(owed[w], _f(s) * _f(plan.get('solUsd'))), 6) for w, s in paid_sol.items() if w in owed}


# ---- 🐱 FeeCat challenge: beat her book over the week ---------------------------------------------------------------
CAT_WIN_PTS = 8


def feecat_week_pct(exits, positions, since, until):
    """FeeCat's week: her average trade % — closed trades that exited this week + positions she opened this week."""
    vals = [_f(e.get('changeAtExit')) for e in exits or [] if since <= _f(e.get('exitAt')) < until]
    vals += [_f(p.get('currentChange')) for p in positions or [] if since <= _f(p.get('openedAt')) < until]
    return round(sum(vals) / len(vals), 2) if vals else None


def beats_cat(board, cat_pct):
    """Cards (opened this week, ≥ $1, from the season board) up more than FeeCat's week. No FeeCat week → nobody."""
    return [] if cat_pct is None else [b['id'] for b in board if _f(b.get('pnlPct')) > _f(cat_pct)]


def copy_cut(copier_fees_usd, rules):
    """Copy cards: the original card's owner earns copyPct of the FEELESS fees the copier paid (not an extra cost)."""
    return round(_f(copier_fees_usd) * clean_rules(rules)['copyPct'] / 100, 6)


# ---- Card plan (set in the Lab before Fuse in, editable on My cards): per-coin TP / SL, auto-profit level, collect vs compound,
# hold vs swap. Every trigger is an ALERT with a pre-filled one-approval action — FEELESS never signs.
LEG_TP, LEG_SL = (5.0, 1000.0), (5.0, 95.0)


def clean_plan(plan, rules, pair_addresses, runner_pairs=()):
    plan = plan if isinstance(plan, dict) else {}
    if plan.get('risk') in RISK_DIALS:   # the dial wins: server-side values only, nothing free-typed
        rp = risk_plan(plan['risk'], [{'pairAddress': pa, 'runner': pa in set(runner_pairs)} for pa in pair_addresses])
        lvl = clean_rules(rules)['yieldLevels']
        rp['at'] = rp['at'] if rp['at'] in lvl else min(lvl, key=lambda v: abs(v - rp['at']))
        return {k: rp[k] for k in ('risk', 'at', 'mode', 'onProfit', 'legs')}
    rl = clean_rules(rules)
    at = plan.get('at')
    try:
        at = float(at) if at not in (None, '', 0, '0', 'off') else None
    except (TypeError, ValueError):
        at = None
    if at is not None and at not in rl['yieldLevels']:
        raise ValueError(f"Pick one of the auto-profit levels: {', '.join(f'+{v:g}%' for v in rl['yieldLevels'])}.")
    legs = {}
    for pa, lim in ((plan.get('legs') or {}).items() if isinstance(plan.get('legs'), dict) else []):
        if pa not in set(pair_addresses) or not isinstance(lim, dict):
            continue
        tp, sl = _f(lim.get('tp')) or None, _f(lim.get('sl')) or None
        if tp is not None and not LEG_TP[0] <= tp <= LEG_TP[1]:
            raise ValueError(f'Coin take-profit must be +{LEG_TP[0]:g}% to +{LEG_TP[1]:g}%.')
        if sl is not None and not LEG_SL[0] <= sl <= LEG_SL[1]:
            raise ValueError(f'Coin stop-loss must be −{LEG_SL[0]:g}% to −{LEG_SL[1]:g}%.')
        if tp or sl:
            legs[pa] = {'tp': tp, 'sl': sl}
    return {'risk': 'custom', 'at': at, 'mode': 'swap' if plan.get('mode') == 'swap' else 'hold', 'onProfit': 'compound' if plan.get('onProfit') == 'compound' else 'collect', 'legs': legs}


def leg_limit_hits(r, leg_guard):
    """Per-coin limits: the open legs whose P&L % crossed their take-profit or stop-loss and haven't fired yet."""
    out = []
    for l in r.get('legs') or []:
        g = (leg_guard or {}).get(l.get('pairAddress'))
        if not g or g.get('firedAt') or l.get('soldUsd') is not None:
            continue
        pct = _f(l.get('pnlPct'))
        if g.get('tp') and pct >= _f(g['tp']):
            out.append((l, 'tp', pct))
        elif g.get('sl') and pct <= -abs(_f(g['sl'])):
            out.append((l, 'sl', pct))
    return out


WEEK = 7 * 86400
SEASON_MIN_COST = 1.0


def season_start(now):
    """Fuse season week start: Monday 00:00 UTC."""
    now = int(_f(now))
    day = now - now % 86400
    return day - ((day // 86400 + 3) % 7) * 86400   # 1970-01-01 was a Thursday


def season_board(rows, since, until, bots=()):
    """Weekly Fuse season: cards OPENED this week (cost ≥ $1, owner not a flagged bot), ranked by real P&L % (live for
    open cards, realized for closed ones), then by $ P&L. One row per card."""
    ok = [r for r in rows if since <= _f(r.get('at')) < until and _f(r.get('costUsd')) >= SEASON_MIN_COST and r.get('wallet') not in set(bots)]
    ranked = sorted(ok, key=lambda r: (-_f(r.get('pnlPct')), -_f(r.get('pnlUsd'))))
    return [{'rank': i + 1, **{k: r.get(k) for k in ('id', 'wallet', 'name', 'pnlPct', 'pnlUsd', 'costUsd', 'closed', 'streak')}} for i, r in enumerate(ranked)]


def card_feeback(fees_usd, held_s, on_arena, rules, season_win=False):
    """Fuse Fee-Back: a share of the FEELESS fees you paid on a card comes back once you've held it fbHoldHours;
    +fbLoyaltyPct after fbLoyaltyDays; +fbArenaPct while it burns hot/blazing on the Arena. Capped at fbCapPct."""
    rl = clean_rules(rules)
    h = max(0.0, _f(held_s)) / 3600
    unlocked = h >= rl['fbHoldHours']
    loyal = h >= rl['fbLoyaltyDays'] * 24
    pct = 0.0 if not unlocked else min(rl['fbCapPct'], rl['fbHolderPct'] + (rl['fbLoyaltyPct'] if loyal else 0) + (rl['fbArenaPct'] if on_arena else 0)
                                       + (rl['seasonBoostPct'] if season_win else 0))
    nxt = (f"{rl['fbHolderPct']:g}% unlocks in {max(0.0, rl['fbHoldHours'] - h):.0f}h" if not unlocked
           else f"+{rl['fbLoyaltyPct']:g}% at {rl['fbLoyaltyDays']:g}d held" if not loyal and rl['fbLoyaltyPct'] else '')
    return {'feesUsd': round(_f(fees_usd), 6), 'pct': round(pct, 2), 'usd': round(_f(fees_usd) * pct / 100, 6), 'unlocked': unlocked, 'loyal': loyal, 'arena': bool(on_arena),
            'season': bool(season_win), 'next': nxt}


def collect_pct(r, y):
    """% of each leg to sell so only the gain comes out (e.g. +50% → sell 33.3%, the base stays in)."""
    held, base = held_value(r), _f((y or {}).get('base'))
    return round(min(100.0, max(0.0, (held - base) / held * 100)), 1) if held > 0 and held > base else 0.0


ROTATE_EVERY = 24 * 3600   # a trader card may switch ONE pool/coin per 24h (top-ups / rebalances don't count); staff exempt


def next_switch_at(pos, staff=False):
    """When this card may switch again (0 = now). Hard-coded rotation: one switch-in per 24h."""
    last = _f(pos.get('lastSwitchAt'))
    return 0.0 if staff or not last else last + ROTATE_EVERY


# ---- 🎚 Risk dial: ONE choice sets the whole card plan (hard-coded here; the Lab / My cards / contract mirror it) ---------
RISK_DIALS = {
    'safe':     {'label': '🛡 Safe',     'pool': (30, 15),  'runner': (30, 15), 'at': 25,  'onProfit': 'collect',  'mode': 'hold', 'runners': 1,
                 'why': 'Small, quick wins: every coin +30% / −15%, collect at +25%, holds together, 1 runner max'},
    'balanced': {'label': '⚖ Balanced', 'pool': (50, 25),  'runner': (50, 30), 'at': 50,  'onProfit': 'collect',  'mode': 'hold', 'runners': 2,
                 'why': 'Pools +50% / −25%, runners on lane-style +50% / −30%, collect at +50%, up to 2 runners'},
    'degen':    {'label': '🚀 Degen',    'pool': (100, 40), 'runner': (100, 40), 'at': 100, 'onProfit': 'compound', 'mode': 'swap', 'runners': 3,
                 'why': 'Let it run: +100% / −40%, compound at +100%, auto-rotate the weakest coin daily, 3 runners'},
}


def risk_plan(risk, legs):
    """Expand a dial into the full card plan for these legs ([{pairAddress, runner?}]). Unknown dial → ValueError."""
    if risk not in RISK_DIALS:
        raise ValueError('Pick Safe, Balanced or Degen.')
    d = RISK_DIALS[risk]
    lim = {l['pairAddress']: dict(zip(('tp', 'sl'), d['runner' if l.get('runner') or l.get('role') == 'runner' else 'pool'])) for l in legs if l.get('pairAddress')}
    return {'risk': risk, 'at': d['at'], 'mode': d['mode'], 'onProfit': d['onProfit'], 'legs': lim, 'maxRunners': d['runners']}
