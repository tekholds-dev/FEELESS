"""🐝 THE COLONY (owner 2026-10-31: "the colony pot should be the smartest, next-level, unforeseen way of safe growth — I create/add a Circle
wallet for it and assign it, then pick the ways it is made most secure for users to stake with").

The Hive becomes the Colony. An owner COLONIZES an agent by staking FEECAT (for now: holding ≥ STAKE_MIN_USD of it in the owner's wallet, read
live — on-chain staking through a provider is not built yet). A colonized agent files cells (proof of insight) AND its trades are graded: every
entry is a BUY cell at its fill price, every exit an AVOID cell at its exit price, judged an hour on like any other cell. Honey ranks the epoch.

THE POT is ONE Circle wallet the owner creates and assigns. Users' money is never pooled: each agent trades from its own wallet. The pot only
pays out its GROWTH, under guards our server enforces (it is the only one that can send from a Circle developer wallet):
  · PRINCIPAL LOCK — what was staked / locked in is never paid out; the owner can only RAISE the floor (lock gains in = compounding).
  · EPOCH CAP — at most `epochCapPct` % of the growth leaves in one epoch; the rest keeps compounding.
  · ALLOWLIST — a payout goes only to a wallet that owns a colonized agent with honey this epoch.
  · OWNER SIGNS + TIMELOCK — a batch is proposed, waits `timelockH` hours (anyone can see it), then the owner approves it.
Pure functions; the service holds the record. Nothing here sends money.
"""

STAKE_MIN_USD = 25.0
POLICY_DEFAULT = {'epochCapPct': 20, 'timelockH': 24}
POLICY_BOUNDS = {'epochCapPct': (5, 50), 'timelockH': (6, 72)}
FIXED_GUARDS = ('principalLock', 'allowlist', 'ownerSigns')   # always on — the owner can't turn these off


def clean_policy(p):
    out = dict(POLICY_DEFAULT)
    for k, (lo, hi) in POLICY_BOUNDS.items():
        try:
            out[k] = int(max(lo, min(hi, float((p or {}).get(k, out[k])))))
        except (TypeError, ValueError):
            pass
    return out


def stake_ok(feecat_usd, staff=False):
    return bool(staff) or float(feecat_usd or 0) >= STAKE_MIN_USD


def raise_floor(principal, value):
    """The principal floor only ever goes UP (lock today's value in) — never down."""
    return round(max(float(principal or 0), float(value or 0)), 2)


def growth(value, principal):
    return round(max(0.0, float(value or 0) - float(principal or 0)), 2)


def payable(value, principal, policy):
    """What may leave this epoch: the epoch cap of the growth, never a cent of the principal."""
    return round(growth(value, principal) * clean_policy(policy)['epochCapPct'] / 100, 2)


def split(board, owners, amount):
    """Payouts follow honey: each agent with positive honey AND an owner wallet gets honey / all positive honey of `amount`.
    → [{cat, name, owner, honey, pct, usd}] (best first). Agents without an owner wallet are left out (the allowlist)."""
    rows = [r for r in board or [] if int(r.get('honey') or 0) > 0 and (owners or {}).get(r.get('cat'))]
    total = sum(int(r['honey']) for r in rows)
    out = []
    for r in rows:
        pct = r['honey'] / total if total else 0
        out.append({'cat': r['cat'], 'name': r.get('name'), 'owner': owners[r['cat']], 'honey': int(r['honey']),
                    'pct': round(pct * 100, 1), 'usd': round(float(amount or 0) * pct, 2)})
    return sorted(out, key=lambda x: -x['honey'])


def trade_cell(cat, side, pos, px_usd, now):
    """A colonized agent's trade as a cell the Hive grades: an entry is a BUY call at its fill, an exit an AVOID call at its exit
    (selling right = the coin fell after you left). → None without a price."""
    try:
        px = float(px_usd)
    except (TypeError, ValueError):
        return None
    if px <= 0 or not (pos or {}).get('pairAddress'):
        return None
    word = 'entry' if side == 'buy' else 'exit'
    return {'id': f"{cat['id']}-{word}-{pos['pairAddress'][:10]}-{int(now)}", 'cat': cat['id'], 'name': cat.get('name'), 'pair': pos['pairAddress'],
            'mint': pos.get('mint'), 'sym': str(pos.get('symbol') or '?')[:16], 'call': 'BUY' if side == 'buy' else 'AVOID', 'kind': word,
            'why': f"its {word} at ${px:.6g}", 'price': px, 'at': now, 'honey': None}
