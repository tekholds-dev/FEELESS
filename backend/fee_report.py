"""Fee report: what a wallet paid in FEELESS fees (7d + all time) and the FeeBack it has accrued.

Pure functions over the fee ledger the trading service feeds (one row per confirmed trade, per signature).
FeeBack accrues FEEBACK_PCT of every fee paid; it is paid out in FEECAT once the program goes live.
"""
FEEBACK_PCT = 100.0
DAY = 86400


def ledger_row(ts: float, sig: str, in_usd: float, fee_bps: int) -> dict:
    usd = max(0.0, float(in_usd or 0))
    return {'t': float(ts), 'sig': sig, 'inUsd': round(usd, 2), 'feeUsd': round(usd * max(0, int(fee_bps or 0)) / 10000, 4)}


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
    return {'fees7dUsd': fee7, 'trades7d': len(week), 'volume7dUsd': round(sum(r['inUsd'] for r in week), 2),
            'feesTotalUsd': total, 'tradesTotal': len(rows), 'days': days,
            'feeBackPct': feeback_pct, 'feeBackUsd': round(total * feeback_pct / 100, 4), 'feeBack7dUsd': round(fee7 * feeback_pct / 100, 4),
            'feeBackStatus': 'accruing'}
