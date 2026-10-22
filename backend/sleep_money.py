"""💤 THE NIGHT VAULT — money while you sleep (owner, 2026-10-22, P1 #2: "auto-compound vaults, lend loops / multiply, LST stacking, JLP, yield
stables … live APY + 24h earned + calculator + deposit here; show liquidation / IL / depeg risk"). Pure, tested (tests/test_sleep_money.py).

Built ONLY from live reads: the Pool Hub's rows (DefiLlama yields + our pair feed, fee_pools.py) and Kamino's public reserve metrics
(api.kamino.finance … /reserves/metrics: supply / borrow APY + max LTV per token). Nothing is guessed: a strategy with no live row is left out,
a loop is only offered where Kamino lends SOL against that LST. Deposits stay where they are safe today — our engine swaps (wallet signs),
the verified Jupiter Lend deposit-here, or the protocol's own page (Kamino vaults / Multiply need their SDK: the owner's call)."""

KAMINO_MAIN = '7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF'
JLP_MINT = '27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4'
LOOPS = (1.5, 2.0, 3.0)
LOOP_SAFETY = 0.9                 # never offer a loop past 90% of the market's max LTV
# risk 0 (none) … 3 (high), per strategy — the WHY is on the card, the numbers come from the live rows
RISK = {
    'lst': {'contract': 1, 'depeg': 1, 'il': 0, 'liq': 0, 'note': 'LSTs track SOL + staking rewards; a depeg vs SOL is the risk, rare and small for the big ones.'},
    'stable': {'contract': 1, 'depeg': 1, 'il': 0, 'liq': 0, 'note': 'Lending USDC / USDT: borrowers pay you interest. Risk = the protocol and the stablecoin itself.'},
    'jlp': {'contract': 1, 'depeg': 2, 'il': 2, 'liq': 0, 'note': 'JLP = the house of Jupiter perps: you earn the fees, you eat traders\' wins, and you hold its SOL / ETH / BTC / USDC basket.'},
    'vault': {'contract': 2, 'depeg': 1, 'il': 2, 'liq': 0, 'note': 'Auto-compound vaults rebalance a DEX position for you — fees compound, impermanent loss is still yours.'},
    'loop': {'contract': 2, 'depeg': 2, 'il': 0, 'liq': 3, 'note': 'Loop = stake, borrow SOL against it, stake again. More yield, but a depeg past the cushion gets you liquidated.'},
}


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def kamino_rates(rows):
    """Kamino reserves → {mint: {sym, supply %, borrow %, maxLtv, tvl}} — the deepest reserve per mint (main market dupes are tiny)."""
    out = {}
    for r in rows or []:
        if not isinstance(r, dict) or not r.get('liquidityTokenMint'):
            continue
        m, tvl = r['liquidityTokenMint'], _f(r.get('totalSupplyUsd'))
        if m in out and out[m]['tvl'] >= tvl:
            continue
        out[m] = {'sym': r.get('liquidityToken'), 'supply': round(_f(r.get('supplyApy')) * 100, 3), 'borrow': round(_f(r.get('borrowApy')) * 100, 3),
                  'maxLtv': round(_f(r.get('maxLtv')), 3), 'tvl': round(tvl)}
    return out


def loop_plays(lst_apy, sol_borrow, max_ltv):
    """Net APY of looping an LST: y·L − b·(L−1); LTV = (L−1)/L; cushion = how far the LST can fall vs SOL before the LTV hits the market's max.
    Only leverages under LOOP_SAFETY × the max LTV."""
    out = []
    for L in LOOPS:
        ltv = (L - 1) / L
        if max_ltv <= 0 or ltv > max_ltv * LOOP_SAFETY:
            continue
        out.append({'x': L, 'apy': round(lst_apy * L - sol_borrow * (L - 1), 2), 'ltv': round(ltv, 3), 'cushion': round(1 - ltv / max_ltv, 3)})
    return out


def earn(apy, usd=1000.0):
    """What `usd` earns at `apy` % over a day / a month / a year (simple, before compounding)."""
    a = _f(apy) / 100
    return {'day': round(usd * a / 365, 4), 'month': round(usd * a / 12, 2), 'year': round(usd * a, 2)}


def strategies(pools, kamino=None, sol_mint='So11111111111111111111111111111111111111112'):
    """Pool Hub rows (+ Kamino rates) → the Night Vault's strategy cards, best first inside each. A strategy with no live row is left out."""
    rows = [r for r in pools or [] if isinstance(r, dict) and _f(r.get('apy')) > 0]   # an APY of 0 / None = not published (DefiLlama's JLP row) — never shown as 0%
    best = lambda rs, n: sorted(rs, key=lambda r: (-_f(r.get('apy')), -_f(r.get('tvl'))))[:n]
    lst = best([r for r in rows if r.get('kind') == 'stake'], 6)
    stable = best([r for r in rows if r.get('kind') == 'lend' and r.get('stable')], 6)
    jlp = best([r for r in rows if 'JLP' in str(r.get('sym') or '').upper() or r.get('hold') == JLP_MINT], 2)
    vault = best([r for r in rows if r.get('kind') == 'vault'], 6)
    out = []
    for key, name, sub, picked in (('lst', '🥩 STAKE STACK', 'SOL → a liquid staking token: staking yield, still liquid', lst),
                                   ('stable', '💵 STABLE SLEEP', 'lend USDC / USDT — interest from borrowers', stable),
                                   ('jlp', '🎰 BE THE HOUSE · JLP', 'earn Jupiter perps\' fees as the counterparty', jlp),
                                   ('vault', '🌀 AUTO-COMPOUND', 'vaults that rebalance + compound a DEX position', vault)):
        if picked:
            out.append({'key': key, 'name': name, 'sub': sub, 'risk': RISK[key], 'rows': [r['id'] for r in picked], 'apy': _f(picked[0]['apy']),
                        'earn': earn(picked[0]['apy']), 'top': picked[0]['sym']})
    km = kamino or {}
    sol = km.get(sol_mint) or {}
    loops = []
    if sol.get('borrow'):
        for r in lst:
            res = km.get(r.get('hold'))
            if not res or not res.get('maxLtv'):
                continue
            plays = loop_plays(_f(r['apy']), sol['borrow'], res['maxLtv'])
            if plays:
                loops.append({'id': r['id'], 'sym': r['sym'], 'proto': r.get('proto'), 'lstApy': _f(r['apy']), 'borrow': sol['borrow'], 'maxLtv': res['maxLtv'], 'plays': plays,
                              'app': 'https://app.kamino.finance/multiply'})
    if loops:
        loops.sort(key=lambda x: -max(p['apy'] for p in x['plays']))
        top = max(loops[0]['plays'], key=lambda p: p['apy'])
        out.append({'key': 'loop', 'name': '🔁 LOOP IT · MULTIPLY', 'sub': f"stake → borrow SOL at {sol['borrow']:.1f}% on Kamino → stake again", 'risk': RISK['loop'],
                    'rows': [], 'loops': loops[:4], 'apy': top['apy'], 'earn': earn(top['apy']), 'top': f"{loops[0]['sym']} ×{top['x']:g}"})
    return out
