#!/usr/bin/env python3
"""⚡ FAST cash check of a real Fuse card (READ-ONLY — signs nothing, changes nothing, prints no keys / URLs / wallet id).
Seconds, not the hours fuse-audit.py takes (it re-reads every swap since the book opened):
  1. the wallet's SOL covers the card's cash (book sol + bank); what is left is the gas reserve — nothing stranded outside the card
  2. every coin on the book is in the wallet, atom for atom; coins the card never bought (airdrops / dust) are listed apart
  3. the last N swaps re-read from the chain: the wallet's real SOL change = the ledger's (sell proceeds / buy cost + rent, − fee);
     a sell whose route parked rent is matched to the account close that brought that rent back

  .venv/bin/python scripts/cash-check.py [card] [N]        (default: degen, 30)
"""
import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'backend'))
TOKEN_PROGRAMS = ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')
LAMPORT = 2e-9   # rounding slack


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def ledger_delta(row):
    """The wallet's SOL change the ledger promises for one filled swap: + proceeds on a sell, − (swap + new account rent) on a buy, − fee."""
    return (_f(row.get('sol')) if row.get('side') == 'sell' else -_f(row.get('sol'))) - _f(row.get('feeSol'))


def explain(row, chain_delta, closes):
    """'ok' when the chain matches the ledger; 'route rent' when a sell's route parked rent that a later close returned; else 'GAP'."""
    gap = chain_delta - ledger_delta(row)
    if abs(gap) <= LAMPORT:
        return 'ok', gap
    if row.get('side') == 'sell' and gap < 0:
        at = _f(row.get('at'))
        back = sum(_f(c.get('sol')) for c in closes if at <= _f(c.get('at')) <= at + 3600 and c.get('status') == 'credited')
        if back + LAMPORT >= -gap:
            return 'route rent', gap
    return 'GAP', gap


def coverage(wallet_sol, book, reserve_sol):
    """Card cash vs the wallet: covered = the wallet holds at least the card's SOL; outside = SOL above card + reserve (unassigned)."""
    card = _f(book.get('sol')) + _f(book.get('bankSol'))
    return {'cardSol': card, 'covered': wallet_sol + LAMPORT >= card, 'reserveHeld': max(0.0, wallet_sol - card),
            'reserveShort': max(0.0, reserve_sol - max(0.0, wallet_sol - card)), 'outsideSol': max(0.0, wallet_sol - card - reserve_sol)}


async def main(tid='degen', n=30):
    import chain_rpc
    import httpx
    db = sqlite3.connect(f"file:{root / 'backend' / 'data' / 'fuse_wallet.db'}?mode=ro", uri=True)
    doc = json.loads(db.execute("select v from kv where k='doc'").fetchone()[0])
    cfg, book = doc.get('cfg') or {}, (doc.get('books') or {}).get(tid)
    if not book:
        sys.exit(f'no real book named {tid}')
    owner = cfg.get('address')
    recent = [json.loads(r[0]) for r in db.execute('select row from ledger order by id desc limit 600')]
    swaps = [r for r in recent if r.get('card') == tid and r.get('status') == 'filled' and r.get('side') in ('buy', 'sell') and r.get('sig')][:n]
    closes = [r for r in recent if r.get('side') == 'close']
    async with httpx.AsyncClient(timeout=25) as http:
        rpc = lambda m, p: chain_rpc.rpc_priority(http, m, p)
        wallet_sol = ((await rpc('getBalance', [owner])) or {}).get('value', 0) / 1e9
        held, parked, accts = {}, 0.0, 0
        for prog in TOKEN_PROGRAMS:
            for a in ((await rpc('getTokenAccountsByOwner', [owner, {'programId': prog}, {'encoding': 'jsonParsed'}])) or {}).get('value') or []:
                info = a['account']['data']['parsed']['info']
                held[info['mint']] = held.get(info['mint'], 0) + int(info['tokenAmount']['amount'])
                parked += a['account']['lamports'] / 1e9
                accts += 1
        cov = coverage(wallet_sol, book, _f(cfg.get('reserveSol')))
        print(f"== {tid} · {time.strftime('%m-%d %H:%M')} ==")
        print(f"1 CASH   card {cov['cardSol']:.6f} SOL · wallet {wallet_sol:.6f} SOL → {'COVERED ✔' if cov['covered'] else 'SHORT ✖'}"
              f" · gas reserve holds {cov['reserveHeld']:.6f} (target {_f(cfg.get('reserveSol')):.3f}, short {cov['reserveShort']:.6f})"
              f" · unassigned {cov['outsideSol']:.6f} · rent parked {parked:.6f} in {accts} accounts")
        legs = book.get('legs') or {}
        short = [(l.get('symbol'), int(_f(l.get('atoms'))), held.get(m, 0)) for m, l in legs.items() if held.get(m, 0) < int(_f(l.get('atoms')))]
        stray = sorted(m[:6] for m, a in held.items() if a and m not in legs)
        print(f"2 COINS  {len(legs)} on the book · {'all in the wallet atom for atom ✔' if not short else f'SHORT {short}'} · not the card's: {stray or 'none'}")
        bad = 0
        for r in swaps:
            tx = await rpc('getTransaction', [r['sig'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
            if not tx:
                print(f"   {r.get('symbol'):>10} {r['side']:4} not readable yet")
                continue
            keys = [k['pubkey'] if isinstance(k, dict) else k for k in tx['transaction']['message']['accountKeys']]
            i = keys.index(owner)
            delta = (tx['meta']['postBalances'][i] - tx['meta']['preBalances'][i]) / 1e9
            verdict, gap = explain(r, delta, closes)
            bad += verdict == 'GAP'
            if verdict != 'ok':
                print(f"   {r.get('symbol'):>10} {r['side']:4} {time.strftime('%H:%M', time.localtime(_f(r.get('at'))))} chain {delta:+.9f} vs ledger {ledger_delta(r):+.9f} → {verdict} {gap:+.9f}")
            await asyncio.sleep(0.12)
        print(f"3 SWAPS  last {len(swaps)} re-read from the chain: {len(swaps) - bad} match to the lamport (route rent returned by closes) · {bad} GAP")


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else 'degen', int(sys.argv[2]) if len(sys.argv) > 2 else 30))
