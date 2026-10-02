"""Money pulse: one owner-side snapshot of every FEELESS wallet + a preflight of everything money depends on.

Pure functions. The service does ONE batched chain read (getMultipleAccounts) and the Circle listing in parallel,
then every HQ card (reserve, pools, Circle, treasury) reads from this snapshot.
"""

def parse_accounts(addrs: list, values: list) -> dict:
    """getMultipleAccounts(jsonParsed) → {address: {sol, token?: {mint, owner, amount}}}; missing accounts → sol 0."""
    out = {}
    for a, v in zip(addrs, values or []):
        if not v:
            out[a] = {'sol': 0.0, 'exists': False}
            continue
        row = {'sol': round((v.get('lamports') or 0) / 1e9, 9), 'exists': True}
        data = v.get('data')
        info = ((data or {}).get('parsed') or {}).get('info') if isinstance(data, dict) else None
        if info and info.get('mint'):
            row['token'] = {'mint': info['mint'], 'owner': info.get('owner'), 'amount': float((info.get('tokenAmount') or {}).get('uiAmount') or 0)}
        out[a] = row
    return out


def preflight(env: dict, cfg: dict, fee_accounts: list, trading: dict, ledger_last: float, now: float, circle: dict) -> list:
    """Everything a real-money trade depends on, each with a plain fix."""
    fa = {f['asset']: f for f in fee_accounts}
    engine = cfg.get('engine') or 'swap'
    checks = [
        ('rpc', 'Solana RPC key set', bool(env.get('SOLANA_RPC_URL')), 'Add SOLANA_RPC_URL (Helius) to backend/.env and restart.'),
        ('jup', 'Jupiter API key set', bool(env.get('JUPITER_API_KEY')), 'Add JUPITER_API_KEY to backend/.env and restart.'),
        ('trading', 'Swap engine online', bool(trading.get('configured')), 'Start the backend: bash scripts/start-backend.sh'),
        ('feeSol', 'SOL fee account live', bool((fa.get('wSOL') or {}).get('ok')), 'HQ › Trading & fees › create fee accounts.'),
        ('feeUsdc', 'USDC fee account live', bool((fa.get('USDC') or {}).get('ok')), 'HQ › Trading & fees › create fee accounts.'),
        ('fee', 'Trade fee above 0%', int(cfg.get('platformFeeBps') or 0) > 0, 'HQ › Trading & fees › set the fee.'),
        ('engine', 'Engine: Jupiter Swap API' + (' (Ultra fallback on)' if cfg.get('ultraFallback') else ''), engine == 'swap', 'Swap API puts the fee in your own accounts. Switch in Trading & fees.'),
        ('internal', 'Fee ledger linked to trading', bool(env.get('_internal_key')), 'Restart the backend so both services share data/internal.key.'),
    ]
    out = [{'key': k, 'label': l, 'ok': ok, 'fix': '' if ok else fix} for k, l, ok, fix in checks]
    out.append({'key': 'ledger', 'label': 'Last fee recorded', 'ok': True, 'info': True,
                'detail': 'no trades yet' if not ledger_last else _ago(now - ledger_last)})
    if circle.get('configured'):
        out.append({'key': 'circle', 'label': 'Circle service up', 'ok': bool(circle.get('up')), 'fix': '' if circle.get('up') else (circle.get('error') or 'Circle did not answer.')})
    return out


def alerts(reserves: list, pools: list, circle_wallets: list) -> list:
    """Nudges: money that's ready to go out, wallets that need funding."""
    out = []
    circle = {w.get('address') for w in circle_wallets or []}
    for r in reserves:
        name = (r.get('season') or {}).get('name') or 'Season'
        if r.get('payout') and not (r['payout'].get('failed')):
            continue
        if r.get('rows') and r.get('paidSol', 0) > 0:
            out.append({'tone': 'ok', 'text': f"{name}: {r['paidSol']} SOL ready for {len(r['rows'])} holders" + (' · pays via Circle' if (r.get('season') or {}).get('reserveWallet') in circle else ''), 'tab': 'reserve'})
        elif r.get('assigned') and not r.get('potSol'):
            out.append({'tone': 'warn', 'text': f"{name}: reserve wallet is empty — fund it to pay badge holders", 'tab': 'reserve'})
        if (r.get('payout') or {}).get('failed'):
            out.append({'tone': 'bad', 'text': f"{name}: {len(r['payout']['failed'])} Circle payouts failed — retry", 'tab': 'reserve'})
    for p in pools:
        nm = (p.get('pool') or {}).get('name') or 'Pool'
        if p.get('rows') and not p.get('cooldownLeft') and p.get('paidSol', 0) > 0:
            out.append({'tone': 'ok', 'text': f"Pool {nm}: {p['paidSol']} SOL ready for {len(p['rows'])} wallets", 'tab': 'reserve'})
    return out


def _ago(s: float) -> str:
    s = max(0, int(s))
    return f'{s // 60}m ago' if s < 3600 else f'{s // 3600}h ago' if s < 86400 else f'{s // 86400}d ago'


def known_destinations(owners, admins, fee_owners, reserves, pools, routes, circle_wallets, saved) -> list:
    """Every wallet a Circle wallet may send to: HQ wallets + ones the owner saved by hand.
    [{address, label, kind}] deduplicated, first label wins."""
    out, seen = [], set()

    def add(addr, label, kind):
        if addr and addr not in seen:
            seen.add(addr); out.append({'address': addr, 'label': label, 'kind': kind})
    for a in owners:
        add(a, 'Owner wallet', 'owner')
    for a in admins:
        add(a, 'Admin wallet', 'admin')
    for a in fee_owners:
        add(a, 'Fee account owner', 'fees')
    for label, a in reserves:
        add(a, label, 'reserve')
    for label, a in pools:
        add(a, label, 'pool')
    for r in routes:
        add(r.get('address'), r.get('label') or 'Treasury route', 'route')
    for w in circle_wallets:
        add(w.get('address'), f"Circle · {w.get('name') or 'wallet'}", 'circle')
    for s in saved:
        add(s.get('address'), s.get('label') or 'Saved wallet', 'saved')
    return out


def same_network(from_chain: str, address: str) -> bool:
    evm = address.startswith('0x')
    return evm != (from_chain or '').upper().startswith('SOL')


def check_flips(prev: dict, checks: list):
    """(newly failing, recovered, new state) between two preflight runs. The first run only records the state."""
    state = {c['key']: bool(c['ok']) for c in checks if not c.get('info')}
    if not prev:
        return [], [], state
    bad = [c for c in checks if not c.get('info') and not c['ok'] and prev.get(c['key'], True)]
    fixed = [c for c in checks if not c.get('info') and c['ok'] and prev.get(c['key']) is False]
    return bad, fixed, state
