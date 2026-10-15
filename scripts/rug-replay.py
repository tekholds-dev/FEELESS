#!/usr/bin/env python3
"""☠ RUG REPLAY (read-only): for every real agent trade that ended as a rug (≤ −45%) and a control group of young winners, read the pool's
on-chain swaps around our hold from PUBLIC RPC nodes (never the keeper's keyed lanes), rebuild the pool's SOL depth and the buy / sell
tape second by second, and write the windows to data/rug_replay.json for the signal test (backend/rug_signal.py).

  python3 scripts/rug-replay.py [max_tx_per_pool]

Each window = every swap from our buy to the pull (rug) / our sale (control): [t, wallet, side, sol, poolSol] — the pull itself is the tx
where the pool's SOL falls ≥ 50% in one go. Nothing here signs, sends or writes outside data/rug_replay.json."""
import json
import sqlite3
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent / 'backend'
DATA = ROOT / 'data'
sys.path.insert(0, str(ROOT))
import env_loader  # noqa: E402,F401  (reads backend/.env — the URL is never printed)
import os  # noqa: E402
# the Helius DATA key first (HELIUS_RPC_URL: kept for Helius-only reads), the public mainnet node as fallback (publicnode keeps no history)
NODES = [u for u in (os.environ.get('HELIUS_RPC_URL', '').strip(), 'https://api.mainnet-beta.solana.com') if u]
WSOL = 'So11111111111111111111111111111111111111112'
MAX_TX = int(sys.argv[1]) if len(sys.argv) > 1 else 220
ONLY = sys.argv[2] if len(sys.argv) > 2 else None   # 'rug' | 'win' — one group only (writes data/rug_replay_<kind>.json)
_http = httpx.Client(timeout=20)
_last = [0.0]


def rpc(method, params):
    for attempt in range(8):
        for node in NODES:
            wait = 0.2 - (time.time() - _last[0])
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
            try:
                r = _http.post(node, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
                j = r.json() if r.status_code in (200, 429) else {}
                if 'result' in j:
                    return j['result']
                code = (j.get('error') or {}).get('code')
                if code not in (429, -32005) and r.status_code != 429:
                    return None   # a real error (not a rate limit): no retry
                time.sleep(2.0)
            except Exception:
                pass
        time.sleep(1.5 * (attempt + 1))
    return None


def sigs_between(pool, t0, t1):
    """Signatures touching the pool between t0 and t1 (newest first pages until older than t0)."""
    out, before = [], None
    for _ in range(12):
        page = rpc('getSignaturesForAddress', [pool, {'limit': 1000, **({'before': before} if before else {})}]) or []
        if not page:
            break
        for s in page:
            bt = s.get('blockTime') or 0
            if bt and t0 <= bt <= t1 and not s.get('err'):
                out.append(s)
        before = page[-1]['signature']
        if (page[-1].get('blockTime') or 0) < t0:
            break
    return sorted(out, key=lambda s: (s.get('blockTime') or 0, s.get('slot') or 0))


def read_tx(sig, pool, mint):
    tx = rpc('getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}])
    if not tx or not tx.get('meta'):
        return None
    m = tx['meta']
    keys = [k['pubkey'] if isinstance(k, dict) else k for k in tx['transaction']['message']['accountKeys']]
    signer = keys[0]

    def bal(rows, owner, mt):
        return sum(float((b.get('uiTokenAmount') or {}).get('uiAmount') or 0) for b in rows or [] if b.get('owner') == owner and b.get('mint') == mt)
    pre, post = m.get('preTokenBalances'), m.get('postTokenBalances')
    pool_sol = bal(post, pool, WSOL)
    pool_sol0 = bal(pre, pool, WSOL)
    tok = bal(post, signer, mint) - bal(pre, signer, mint)
    side = 'buy' if tok > 0 else 'sell' if tok < 0 else None
    return {'t': tx.get('blockTime'), 'w': signer, 'side': side, 'sol': round(pool_sol - pool_sol0, 4), 'poolSol': round(pool_sol, 3), 'tok': tok}


def main():
    a = json.loads((DATA / 'agent_archive.json').read_text())
    pos = [p for p in a['positions'] if p.get('confirmed') and p.get('realPct') is not None]
    c = sqlite3.connect(f'file:{DATA / "fuse_wallet.db"}?mode=ro', uri=True)
    buys = {}
    for (r,) in c.execute('select row from ledger'):
        r = json.loads(r)
        if r.get('side') == 'buy' and r.get('status') == 'filled':
            buys.setdefault(r['mint'], []).append(r)
    young = lambda p: ((p.get('li') or {}).get('ageH') if (p.get('li') or {}).get('ageH') is not None else (p.get('launch') or {}).get('ageH') or 99) < 1 / 12
    rugs = [p for p in pos if p['realPct'] <= -45]
    ctrl = sorted([p for p in pos if young(p) and p['realPct'] > 0], key=lambda p: -p['since'])[:20]
    out = []
    for kind, group in (('rug', rugs), ('win', ctrl)):
        if ONLY and kind != ONLY:
            continue
        for p in group:
            b = next((x for x in buys.get(p['mint'], []) if abs(x['at'] - p['since']) < 600), None)
            if not b or not b.get('pair'):
                continue
            t0, t1 = int((b.get('confirmedAt') or p['since'])) - 30, int(p['closedAt']) + 5
            ss = sigs_between(b['pair'], t0, t1)
            if len(ss) > MAX_TX:   # the WHOLE hold, sampled evenly, + the last 20 before the exit (where a pull would be)
                step = (len(ss) - 20) / (MAX_TX - 20)
                ss = [ss[int(i * step)] for i in range(MAX_TX - 20)] + ss[-20:]
            rows = []
            for i, s_ in enumerate(ss):
                r_ = read_tx(s_['signature'], b['pair'], p['mint'])
                if r_:
                    rows.append(r_)
                if i % 40 == 39:
                    print(f"  {p['sym']} {i + 1}/{len(ss)}", flush=True)
            out.append({'kind': kind, 'sym': p['sym'], 'mint': p['mint'], 'pair': b['pair'], 'realPct': p['realPct'], 'buyAt': b.get('confirmedAt') or p['since'],
                        'exitAt': p['closedAt'], 'liqBuy': b.get('liq'), 'nSigs': len(ss), 'rows': rows})
            print(kind, p['sym'], len(ss), 'txs', len(rows), 'read', flush=True)
            (DATA / (f'rug_replay_{ONLY}.json' if ONLY else 'rug_replay.json')).write_text(json.dumps(out))
    print('written', len(out))


if __name__ == '__main__':
    main()
