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


async def wallet(http_timeout=25):
    """WHOLE-WALLET check: every transaction the Fuse wallet ever appeared in, read from the chain. Proves where every lamport of
    the deposits is: still in the wallet, parked as rent in coin accounts, in coins, paid as network fees, or lost / won trading.
    Any SOL that left the wallet to ANOTHER address is listed — there should be none."""
    d = store.KV(root / 'backend' / 'data' / 'fuse_wallet.json').get({}) or {}
    owner = (d.get('cfg') or {}).get('address')
    async with httpx.AsyncClient(timeout=http_timeout) as http:
        rpc = lambda m, p: chain_rpc.rpc_priority(http, m, p)
        sigs, before = [], None
        while True:
            page = await rpc('getSignaturesForAddress', [owner, {'limit': 1000, **({'before': before} if before else {})}]) or []
            sigs += page
            if len(page) < 1000:
                break
            before = page[-1]['signature']
        ok = [x for x in sigs if not x.get('err')]
        dep = buys = sells = fees = closes = 0.0
        out_other, unread, n_swap, n_close, n_dep, failed_fees = [], 0, 0, 0, 0, 0.0
        for x in sigs[::-1]:
            tx = None
            for _ in range(3):
                try:
                    tx = await rpc('getTransaction', [x['signature'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
                except Exception:
                    tx = None
                if tx:
                    break
                await asyncio.sleep(1.0)
            if not tx:
                unread += 1
                continue
            meta = tx['meta']; keys = tx['transaction']['message']['accountKeys']
            names = [k['pubkey'] for k in keys]
            if owner not in names:
                continue
            i = names.index(owner)
            signer = any(k['pubkey'] == owner and k.get('signer') for k in keys)
            payer = i == 0
            delta = (meta['postBalances'][i] - meta['preBalances'][i]) / 1e9
            fee = meta['fee'] / 1e9 if payer else 0.0
            if meta.get('err'):
                failed_fees += fee
                continue
            pre = {(b['mint'], b.get('owner')): int(b['uiTokenAmount']['amount']) for b in meta.get('preTokenBalances') or []}
            post = {(b['mint'], b.get('owner')): int(b['uiTokenAmount']['amount']) for b in meta.get('postTokenBalances') or []}
            tok = sum(1 for k in set(pre) | set(post) if k[1] == owner and post.get(k, 0) != pre.get(k, 0))
            gross = delta + fee
            fees += fee
            if not signer:
                dep += delta; n_dep += 1
            elif tok:
                n_swap += 1
                if gross < 0:
                    buys += -gross
                else:
                    sells += gross
            elif gross >= 0:
                closes += gross; n_close += 1
            else:
                out_other.append((x['signature'][:10], round(gross, 6), time.strftime('%m-%d %H:%M', time.localtime(x.get('blockTime') or 0))))
            await asyncio.sleep(0.1)
        wallet_sol = ((await rpc('getBalance', [owner])) or {}).get('value', 0) / 1e9
        parked, coins = 0.0, 0
        for prog in TOKEN_PROGRAMS:
            res = await rpc('getTokenAccountsByOwner', [owner, {'programId': prog}, {'encoding': 'jsonParsed'}])
            for a in (res or {}).get('value') or []:
                parked += a['account']['lamports'] / 1e9
                coins += 1 if int(a['account']['data']['parsed']['info']['tokenAmount']['amount']) else 0
        calc = dep - buys + sells + closes - fees - failed_fees + sum(g for _, g, _ in out_other)
        print(f"WHOLE WALLET — {len(sigs)} transactions on-chain ({len(ok)} confirmed, {unread} could not be read)")
        print(f"  deposited by you        {dep:+.6f} SOL  ({n_dep} transfers in)")
        print(f"  into coin buys          {-buys:+.6f} SOL  (includes rent parked in new coin accounts)")
        print(f"  out of coin sells       {sells:+.6f} SOL")
        print(f"  rent back from closes   {closes:+.6f} SOL  ({n_close} closes)")
        print(f"  network fees            {-(fees + failed_fees):+.6f} SOL  ({n_swap} swaps; failed txs cost {failed_fees:.6f})")
        print(f"  sent to another address {sum(g for _, g, _ in out_other):+.6f} SOL  {out_other if out_other else '— none'}")
        print(f"  = should be in wallet   {calc:.6f} SOL · wallet really holds {wallet_sol:.6f} SOL · difference {wallet_sol - calc:+.6f}")
        print(f"  also yours: {parked:.6f} SOL parked as rent in {coins} coin accounts (comes back when they close) + the coins themselves")
        print(f"  trading result so far (sells + closes + parked rent − buys): {sells + closes + parked - buys:+.6f} SOL before the coins still held")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'wallet':
        asyncio.run(wallet())
    else:
        asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
