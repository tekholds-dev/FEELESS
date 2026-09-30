"""Fee report: what a wallet paid in FEELESS fees (7d + all time) and the FeeBack it has accrued.

Pure functions over the fee ledger the trading service feeds (one row per confirmed trade, per signature).
FeeBack accrues FEEBACK_PCT of every fee paid; it is paid out in FEECAT once the program goes live.
"""
FEEBACK_PCT = 100.0
DAY = 86400


SOL_MINT = 'So11111111111111111111111111111111111111112'
USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'


def ledger_row(ts: float, sig: str, in_usd: float, fee_bps: int, fee_atoms: int = 0, fee_mint: str = '', sol_usd: float = 0) -> dict:
    """One confirmed trade. The fee actually built into the transaction wins; trade value × fee % is the fallback."""
    usd = max(0.0, float(in_usd or 0))
    row = {'t': float(ts), 'sig': sig, 'inUsd': round(usd, 2), 'feeUsd': round(usd * max(0, int(fee_bps or 0)) / 10000, 4)}
    atoms = max(0, int(fee_atoms or 0))
    if atoms and fee_mint == SOL_MINT:
        row['feeSol'] = atoms / 1e9
        if sol_usd:
            row['feeUsd'] = round(row['feeSol'] * sol_usd, 4)
    elif atoms and fee_mint == USDC_MINT:
        row['feeUsdc'] = atoms / 1e6
        row['feeUsd'] = round(row['feeUsdc'], 4)
    return row


def fee_report(rows: list, now: float, feeback_pct: float = FEEBACK_PCT) -> dict:
    rows = [r for r in rows or [] if isinstance(r, dict)]
    week = [r for r in rows if now - r['t'] < 7 * DAY]
    days = [0.0] * 7   # oldest → today
    for r in week:
        i = 6 - int((now - r['t']) // DAY)
        if 0 <= i < 7:
            days[i] = round(days[i] + r['feeUsd'], 4)
    total = round(sum(r['feeUsd'] for r in rows), 4)
    fee7 = round(sum(r['feeUsd'] for r in week), 4)
    return {'fees7dUsd': fee7, 'trades7d': len(week), 'fees7dSol': round(sum(r.get('feeSol', 0) for r in week), 9), 'volume7dUsd': round(sum(r['inUsd'] for r in week), 2),
            'feesTotalUsd': total, 'tradesTotal': len(rows), 'days': days,
            'feeBackPct': feeback_pct, 'feeBackUsd': round(total * feeback_pct / 100, 4), 'feeBack7dUsd': round(fee7 * feeback_pct / 100, 4),
            'feeBackStatus': 'accruing'}
