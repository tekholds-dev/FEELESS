"""🐝 THE COLONY (owner 2026-10-31). An owner COLONIZES an agent (no stake needed — owner 2026-10-31): it files cells (proof of insight) and its
trades are graded (entry = a BUY cell, exit = an AVOID cell, judged an hour on). HONEY is its proof — it ranks the Colony; nobody is paid for being right.

Two OPPORTUNITIES in the Colonize popout (owner: "we earn nothing but FEECAT staking"):
  1 · STAKE — FEECAT or SOL into the colony pool the owner opens with the colony wallet on a pool platform; that pool pays on its own epochs.
      (Assigning the pool is built; depositing through it is not.)
  2 · SHARE WINNINGS — the owner signs once to let its agent send `pct` % of each WINNING trade's profit to the colony wallet; the colony
      airdrops back to the sharers every day / week (the owner picks), in proportion to what each shared. (Accrual is built; sending is not.)

THE POT is ONE Circle wallet. Users' money is never pooled for trading — each agent trades from its own wallet. The pot only pays out its
GROWTH, under guards our server enforces: PRINCIPAL LOCK (only ever raised) · EPOCH CAP · ALLOWLIST (only wallets that signed) · OWNER
APPROVES + TIMELOCK. Pure functions; the services hold the records. Nothing here sends money.
"""

# 🐝 what EVERY agent knows about the Colony (owner 2026-10-31: "agents must know all about how colony and colonizing works, whatever the prompt")
KNOWHOW = ('THE COLONY (FEELESS): agents that are colonized read the Solana trenches on their own, cheaply, one coin at a time, and file a call '
           '(BUY / WATCH / AVOID + the numbers why). An hour later every call, entry and exit is graded on what the coin really did — right calls earn '
           'HONEY (your proof on the Colony board; nobody is paid for being right). Your owner may let you send a share of each WINNING trade to the '
           'colony wallet; the colony airdrops back to the sharers. So: read real numbers, name your sources, never invent, and keep notes your owner can read.')
COLONIZED = 'YOU ARE COLONIZED: every coin you read is filed as a graded call, and your best finds go to your owner\'s cabinet.'

POLICY_DEFAULT = {'epochCapPct': 20, 'timelockH': 24, 'cadence': 'daily'}
POLICY_BOUNDS = {'epochCapPct': (5, 50), 'timelockH': (6, 72)}
CADENCES = {'daily': 86400, 'weekly': 7 * 86400}   # 🪂 how often the airdrop pays (the owner picks)
SHARE_PCTS = (5, 10, 20, 30)                         # 🤝 opportunity 2: the share of each winning trade's profit an owner lets its agent send
FIXED_GUARDS = ('principalLock', 'allowlist', 'ownerSigns')   # always on — the owner can't turn these off


def clean_policy(p):
    out = dict(POLICY_DEFAULT)
    if (p or {}).get('cadence') in CADENCES:
        out['cadence'] = p['cadence']
    for k, (lo, hi) in POLICY_BOUNDS.items():
        try:
            out[k] = int(max(lo, min(hi, float((p or {}).get(k, out[k])))))
        except (TypeError, ValueError):
            pass
    return out


def raise_floor(principal, value):
    """The principal floor only ever goes UP (lock today's value in) — never down."""
    return round(max(float(principal or 0), float(value or 0)), 2)


def growth(value, principal):
    return round(max(0.0, float(value or 0) - float(principal or 0)), 2)


def payable(value, principal, policy):
    """What may leave this epoch: the epoch cap of the growth, never a cent of the principal."""
    return round(growth(value, principal) * clean_policy(policy)['epochCapPct'] / 100, 2)


def share_pct(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return 0
    return v if v in SHARE_PCTS else 0


def share_cut(pnl_sol, pct):
    """🤝 What a sharing agent owes the colony from ONE closed trade: pct % of the profit — nothing on a loss."""
    return round(max(0.0, float(pnl_sol or 0)) * share_pct(pct) / 100, 6)


def period_of(t, cadence):
    """The airdrop period a moment falls in (UTC days / weeks), and when it ends."""
    n = CADENCES.get(cadence, CADENCES['daily'])
    k = int(float(t) // n)
    return k, (k + 1) * n


def airdrop(shares, owners_ok, amount, since):
    """🪂 Opportunity 2: the next airdrop. Every owner whose agent shared since `since` gets `amount` × their share of what was shared —
    proportional to what they put in, never to who was 'right'. Only wallets that signed (owners_ok) are paid. → [{owner, sol, pct, usd}]"""
    tot = {}
    for x in shares or []:
        if float(x.get('at') or 0) >= since and x.get('owner') in (owners_ok or set()):
            tot[x['owner']] = tot.get(x['owner'], 0.0) + float(x.get('sol') or 0)
    s = sum(tot.values())
    return sorted(({'owner': o, 'sol': round(v, 6), 'pct': round(100 * v / s, 1) if s else 0, 'usd': round(float(amount or 0) * v / s, 2) if s else 0}
                   for o, v in tot.items()), key=lambda r: -r['sol'])


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
