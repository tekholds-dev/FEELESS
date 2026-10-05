#!/usr/bin/env python3
"""🔎 Chain audit of a real Fuse card (READ-ONLY — signs nothing, changes nothing, prints no keys / URLs / wallet id).

Re-reads EVERY confirmed swap of the card's current book from the chain and rebuilds what the card's SOL cash must be:
  funded SOL − SOL into each buy + SOL out of each sell (+ rent the sell's route parked) − network fees the card paid − cash taken out
then compares it with the book, and compares every coin the book holds with the wallet's real token balance.

  backend/.venv/bin/python scripts/fuse-audit.py [card]      (default: every real card)
"""
import asyncio
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'backend'))
import chain_rpc  # noqa: E402
import fuse_wallet as fw  # noqa: E402
import httpx  # noqa: E402
import store  # noqa: E402

TOKEN_PROGRAMS = ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')


async def main(only=None):
    d = store.KV(root / 'backend' / 'data' / 'fuse_wallet.json').get({}) or {}
    owner = (d.get('cfg') or {}).get('address')
    rows_all = store.Ledger(root / 'backend' / 'data' / 'fuse_wallet.json').rows(limit=100000)
    async with httpx.AsyncClient(timeout=25) as http:
        rpc = lambda m, p: chain_rpc.rpc_priority(http, m, p)
        wallet_sol = ((await rpc('getBalance', [owner])) or {}).get('value', 0) / 1e9
        held = {}
        for prog in TOKEN_PROGRAMS:
            res = await rpc('getTokenAccountsByOwner', [owner, {'programId': prog}, {'encoding': 'jsonParsed'}])
            for a in (res or {}).get('value') or []:
                info = a['account']['data']['parsed']['info']
                held[info['mint']] = held.get(info['mint'], 0) + int(info['tokenAmount']['amount'])
        print(f"WALLET: {wallet_sol:.6f} SOL · {sum(1 for v in held.values() if v)} coins held · fee reserve {(d.get('cfg') or {}).get('reserveSol')} SOL")
        book_sol = sum(fw._f(b.get('sol')) + fw._f(b.get('bankSol')) for b in d['books'].values())
        print(f"  card books hold {book_sol:.6f} SOL → wallet covers them: {'YES' if wallet_sol + 1e-9 >= book_sol else 'NO — SHORT'} (unassigned + reserve {wallet_sol - book_sol:.6f} SOL)")
        for tid, b in d['books'].items():
            if only and tid != only:
                continue
            since = fw._f(b.get('since'))
            rows = sorted((r for r in rows_all if r.get('card') == tid and fw._f(r.get('at')) >= since - 5), key=lambda r: fw._f(r.get('at')))
            print(f"\n== {tid} · book since {time.strftime('%m-%d %H:%M', time.localtime(since))} · put in ${fw._f(b.get('fundedUsd')):.2f} ==")
            bad = [(l.get('symbol'), int(l.get('atoms') or 0), held.get(m, 0)) for m, l in (b.get('legs') or {}).items() if held.get(m, 0) < int(l.get('atoms') or 0)]
            print('  coins: every coin on the book is in the wallet ✔' if not bad else f'  coins: SHORT IN WALLET {bad}')
            seen, sol, fees_card, fees_all, opened_sells, opened_missed, n, unread = set(), 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0
            for r in rows:
                side, st = r.get('side'), r.get('status')
                if side == 'topup' and st in ('done', None) and r.get('sol') is not None:
                    sol += fw._f(r.get('sol'))
                elif side == 'topup' and st in ('done', None):
                    sol += fw._f(r.get('usd')) / (fw._f(r.get('solPx')) or 1)
                elif side in ('withdraw', 'payout') and st in ('done', None):
                    sol -= fw._f(r.get('sol'))
                if side not in ('buy', 'sell') or st != 'filled' or not r.get('sig') or (r['sig'], side) in seen:
                    continue
                seen.add((r['sig'], side))
                tx = None
                for _ in range(3):
                    try:
                        tx = await rpc('getTransaction', [r['sig'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
                    except Exception:
                        tx = None
                    if tx:
                        break
                    await asyncio.sleep(1.0)
                if not tx:
                    unread += 1
                    continue
                n += 1
                meta = tx['meta']
                keys = [k['pubkey'] for k in tx['transaction']['message']['accountKeys']]
                i = keys.index(owner)
                fee = meta['fee'] / 1e9
                delta = (meta['postBalances'][i] - meta['preBalances'][i]) / 1e9 + fee      # excl. the network fee
                opened = fw.opened_sol(tx, owner)
                fees_all += fee
                if r.get('cardPays'):
                    sol -= fee; fees_card += fee
                if side == 'buy':
                    sol -= min(-delta, int(r.get('lamports') or 0) / 1e9) if r.get('lamports') else 0.0   # only what went INTO the swap
                elif fw._f(r.get('sol')) == 0 and str(r.get('why') or '').startswith('🔀'):
                    pass                                                                    # one-transaction swap: no SOL changes hands
                else:
                    sol += delta + opened
                    opened_sells += opened
                    if opened > 0 and not fw._f(r.get('openedSol')):
                        opened_missed += opened                                             # booked before the route-rent rule
                await asyncio.sleep(0.12)
            credited = sum(fw._f(r.get('sol')) for r in rows if str(r.get('id') or '').startswith('routefix'))
            have = fw._f(b.get('sol')) + fw._f(b.get('bankSol')) + fw._f(b.get('rentHeldSol'))
            print(f"  {n} swaps re-read from the chain ({unread} could not be read) · network fees {fees_all:.6f} SOL (card paid {fees_card:.6f})")
            print(f"  card SOL cash — chain says {sol:.6f} · book says {have:.6f} · difference {have - sol:+.6f} SOL")
            print(f"  route rent parked by sells: {opened_sells:.6f} SOL · booked before the rule {opened_missed:.6f} · already put back {credited:.6f} · STILL OWED TO THE CARD {max(0.0, opened_missed - credited):.6f} SOL")


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
