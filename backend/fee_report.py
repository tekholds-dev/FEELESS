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


def referral_credit(book: dict, inviter: str, invitee: str, row: dict, pct: float, now: float) -> dict:
    """Credit an inviter pct% of the FEELESS fee their invitee just paid (accrues; paid out by the owner)."""
    pct = max(0.0, min(50.0, float(pct or 0)))
    if not inviter or pct <= 0 or not row.get('feeUsd'):
        return book
    rec = book.setdefault(inviter, {'usd': 0.0, 'sol': 0.0, 'trades': 0, 'invitees': [], 'lastAt': 0})
    rec['usd'] = round(rec['usd'] + row['feeUsd'] * pct / 100, 6)
    rec['sol'] = round(rec['sol'] + row.get('feeSol', 0) * pct / 100, 9)
    rec['trades'] += 1
    if invitee not in rec['invitees']:
        rec['invitees'].append(invitee)
    rec['lastAt'] = now
    return book


def add_total(totals: dict, who: str, row: dict) -> dict:
    """Lifetime fee book per account (never trimmed): the base for any future FeeBack / payback."""
    t = totals.setdefault(who, {'feeUsd': 0.0, 'feeSol': 0.0, 'feeUsdc': 0.0, 'volumeUsd': 0.0, 'trades': 0, 'first': row['t'], 'last': row['t']})
    t['feeUsd'] = round(t['feeUsd'] + row.get('feeUsd', 0), 6)
    t['feeSol'] = round(t['feeSol'] + row.get('feeSol', 0), 9)
    t['feeUsdc'] = round(t['feeUsdc'] + row.get('feeUsdc', 0), 6)
    t['volumeUsd'] = round(t['volumeUsd'] + row.get('inUsd', 0), 2)
    t['trades'] += 1
    t['first'], t['last'] = min(t['first'], row['t']), max(t['last'], row['t'])
    return totals


def fee_book(totals: dict, paid: dict, feeback_pct: float = FEEBACK_PCT) -> list:
    """Every account: lifetime fees, FeeBack earned at feeback_pct, already paid, still owed. Biggest first."""
    rows = []
    for who, t in (totals or {}).items():
        earned = round(t['feeUsd'] * feeback_pct / 100, 6)
        done = round(float((paid or {}).get(who, 0)), 6)
        rows.append({'address': who, **t, 'feeBackUsd': earned, 'paidUsd': done, 'owedUsd': round(max(0.0, earned - done), 6)})
    return sorted(rows, key=lambda r: -r['feeUsd'])
