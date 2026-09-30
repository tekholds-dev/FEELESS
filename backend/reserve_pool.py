"""Season badge reserve pool: who gets what share of the Fee Reserve wallet.

Season tiers earn weighted shares of `badgeRewardPct`% of the reserve wallet's SOL. Pure functions only:
the service reads the balance and scores, the owner signs the payout from the reserve wallet (no custody).
"""

TIER_WEIGHTS = {'Legend': 12, 'Diamond': 6, 'Gold': 3, 'Silver': 2, 'Bronze': 1, 'Recruit': 0}
KEEP_SOL = 0.01      # left in the reserve wallet for rent + network fees
DUST_SOL = 0.001     # shares below this are not worth a transfer


def payout_plan(pool_sol: float, pct: float, holders: list, excluded=frozenset(), keep_sol: float = KEEP_SOL, dust_sol: float = DUST_SOL) -> dict:
    """holders: [{address, tier, score}]. Returns the pot and each wallet's weighted share (SOL, 6 dp)."""
    pct = max(0.0, min(100.0, float(pct or 0)))
    pot = round(max(0.0, min(float(pool_sol or 0) * pct / 100, float(pool_sol or 0) - keep_sol)), 6)
    rows = [{'address': h['address'], 'tier': h.get('tier') or 'Recruit', 'score': h.get('score') or 0,
             'weight': h['weight'] if h.get('weight') is not None else TIER_WEIGHTS.get(h.get('tier'), 0),
             **({'why': h['why']} if h.get('why') else {})} for h in holders if h.get('address') and h['address'] not in excluded]
    rows = [r for r in rows if r['weight'] > 0]
    dropped = 0
    for _ in range(3):  # drop dust shares and re-split, so the pot goes to wallets that actually get paid
        total = sum(r['weight'] for r in rows)
        for r in rows:
            r['sharePct'] = round(100 * r['weight'] / total, 3) if total else 0
            r['sol'] = int(pot * 1e6 * r['weight'] / total) / 1e6 if total else 0
        dust = [r for r in rows if r['sol'] < dust_sol]
        if not dust:
            break
        dropped += len(dust)
        rows = [r for r in rows if r['sol'] >= dust_sol]
    rows.sort(key=lambda r: (-r['weight'], -r['score']))
    return {'poolSol': round(float(pool_sol or 0), 6), 'pct': pct, 'potSol': pot, 'totalWeight': sum(r['weight'] for r in rows),
            'paidSol': round(sum(r['sol'] for r in rows), 6), 'rows': rows, 'droppedDust': dropped, 'weights': TIER_WEIGHTS}


def wallet_share(plan: dict, address: str):
    return next((r for r in plan['rows'] if r['address'] == address), None)


def pool_holders(weights: dict, tiers: dict, badges: dict) -> list:
    """Badge pools: weights keyed 'tier:<Tier>' (season tier) or 'badge:<id>' (custom award), summed per wallet.
    tiers: {address: tier}, badges: {address: [badge ids]}."""
    out = {}
    for a, t in (tiers or {}).items():
        w = float(weights.get(f'tier:{t}') or 0)
        if w > 0:
            out.setdefault(a, [0, []]); out[a][0] += w; out[a][1].append(t)
    for a, ids in (badges or {}).items():
        for bid in ids:
            w = float(weights.get(f'badge:{bid}') or 0)
            if w > 0:
                out.setdefault(a, [0, []]); out[a][0] += w; out[a][1].append(bid)
    return [{'address': a, 'weight': w, 'tier': tiers.get(a) or 'Recruit', 'why': ' + '.join(why)} for a, (w, why) in out.items()]


def pct_holders(alloc: dict, tiers: dict, badges: dict):
    """Badge pools in % mode: alloc {'badge:<id>' | 'tier:<Tier>': % of the pot}. Each key's slice is split equally
    between the wallets holding it; a wallet holding several keys stacks slices. Unallocated % stays in the wallet.
    Returns (holders with weight = their % of the pot, allocated %)."""
    alloc = {k: float(v) for k, v in (alloc or {}).items() if float(v or 0) > 0}
    holders_of = {}
    for a, t in (tiers or {}).items():
        holders_of.setdefault(f'tier:{t}', []).append(a)
    for a, ids in (badges or {}).items():
        for bid in set(ids):
            holders_of.setdefault(f'badge:{bid}', []).append(a)
    out, used = {}, 0.0
    for key, pct in alloc.items():
        who = holders_of.get(key) or []
        if not who:
            continue  # nobody holds it yet: its slice stays in the wallet
        used += pct
        for a in who:
            rec = out.setdefault(a, [0.0, []]); rec[0] += pct / len(who); rec[1].append(key.split(':', 1)[1])
    rows = [{'address': a, 'weight': round(w, 6), 'tier': (tiers or {}).get(a) or 'Recruit', 'why': ' + '.join(why)} for a, (w, why) in out.items()]
    return rows, round(min(100.0, used), 6)


def route_split(amount: float, routes: list, decimals: int = 9) -> list:
    """Treasury split: amount across routes by % (floored to the asset's precision so it never overspends)."""
    q = 10 ** min(decimals, 9)
    return [{'label': r.get('label') or '', 'address': r['address'], 'pct': float(r['pct']),
             'amount': int(float(amount) * float(r['pct']) / 100 * q + 1e-6) / q} for r in routes if float(r.get('pct') or 0) > 0]


def parsed_transfers(tx: dict, signer: str) -> list:
    """Every SOL / SPL transfer the signer made in a jsonParsed transaction (what actually moved)."""
    out = []
    ixs = list((tx.get('transaction') or {}).get('message', {}).get('instructions') or [])
    for inner in (tx.get('meta') or {}).get('innerInstructions') or []:
        ixs += inner.get('instructions') or []
    for ix in ixs:
        p = ix.get('parsed') or {}
        info = p.get('info') or {}
        if ix.get('program') == 'system' and p.get('type') == 'transfer' and info.get('source') == signer:
            out.append({'asset': 'SOL', 'to': info['destination'], 'amount': info['lamports'] / 1e9})
        elif ix.get('program') in ('spl-token', 'spl-token-2022') and p.get('type') in ('transfer', 'transferChecked') and (info.get('authority') or info.get('multisigAuthority')) == signer:
            amt = (info.get('tokenAmount') or {}).get('uiAmount')
            out.append({'asset': info.get('mint') or 'SPL', 'to': info['destination'], 'amount': float(amt if amt is not None else info.get('amount') or 0)})
    return out


def fixed_rows(fixed: dict, tiers: dict, badges: dict, budget: float):
    """Fixed SOL per holder for a badge / tier ('badge:<id>' | 'tier:<Tier>' -> SOL each). If the total would
    overspend the budget, everyone is scaled down equally. Returns ({address: sol}, total)."""
    holders_of = {}
    for a, t in (tiers or {}).items():
        holders_of.setdefault(f'tier:{t}', set()).add(a)
    for a, ids in (badges or {}).items():
        for bid in set(ids):
            holders_of.setdefault(f'badge:{bid}', set()).add(a)
    want = {}
    for key, each in (fixed or {}).items():
        each = float(each or 0)
        for a in holders_of.get(key, ()):
            if each > 0:
                want[a] = want.get(a, 0) + each
    total = sum(want.values())
    scale = min(1.0, max(0.0, budget) / total) if total else 1.0
    out = {a: int(v * scale * 1e6) / 1e6 for a, v in want.items()}
    return out, round(sum(out.values()), 6)
