"""🌐 COMP's internet learner: real market rows it labels itself, no human and no other company's model in the loop.

Every collect: (1) SNAPSHOT the coins DexScreener is showing right now (latest profiles + boosts, Solana) with what a trader sees at that
second — age, liquidity, FDV, 5m / 1h move, 1h buys vs sells, volume; (2) SETTLE every snapshot older than HOLD_SEC by asking DexScreener
for the same pair again: up ≥ WIN_PCT = won, down ≥ LOSS_PCT or the pool is gone = lost, in between = flat (dropped, like flat proofs).
Settled rows join COMP v2's TRAIN set (never its exam, which stays the owner's held-out proofs), capped so they never outnumber his.
DexScreener only (the sitewide data rule), paced by ds_pace like every other caller.
"""
import json
import time
from pathlib import Path

HOLD_SEC = 3600
WIN_PCT = 20.0
LOSS_PCT = -20.0
MAX_OPEN = 600           # snapshots waiting to settle
PER_COLLECT = 30          # new coins per collect (one /tokens/v1 call)
KIND = 'PoMkt'
API = 'https://api.dexscreener.com'


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def features(pair, now):
    """What a trader sees on one pair at this second → dict (None when it has no price or pool)."""
    price = _num(pair.get('priceUsd')); liq = _num((pair.get('liquidity') or {}).get('usd'))
    if price <= 0 or liq <= 0:
        return None
    tx = (pair.get('txns') or {}).get('h1') or {}; ch = pair.get('priceChange') or {}
    born = _num(pair.get('pairCreatedAt')) / 1000
    return {'pair': pair.get('pairAddress'), 'mint': (pair.get('baseToken') or {}).get('address'), 'symbol': (pair.get('baseToken') or {}).get('symbol') or '?',
            'dex': pair.get('dexId') or '', 'price': price, 'liq': round(liq), 'fdv': round(_num(pair.get('fdv'))),
            'ageMin': round((now - born) / 60) if born else None, 'm5': _num(ch.get('m5')), 'h1': _num(ch.get('h1')),
            'buys': int(_num(tx.get('buys'))), 'sells': int(_num(tx.get('sells'))), 'volH1': round(_num((pair.get('volume') or {}).get('h1'))), 'at': round(now)}


def _cmp(n):
    n = float(n or 0)
    return f'${n / 1e6:.1f}M' if n >= 1e6 else f'${n / 1e3:.0f}K' if n >= 1e3 else f'${n:.0f}'


def row_of(snap, outcome):
    """A settled snapshot as a COMP training row: the same shape as an owner proof, written only from what was known at the snapshot."""
    age = f"{snap['ageMin']} min old" if snap.get('ageMin') is not None else 'age unknown'
    plan = (f"{snap['symbol']} on {snap['dex']}: {age}, liquidity {_cmp(snap['liq'])}, FDV {_cmp(snap['fdv'])}, "
            f"{snap['m5']:+.1f}% in 5m, {snap['h1']:+.1f}% in 1h, {snap['buys']} buys vs {snap['sells']} sells in 1h, volume {_cmp(snap['volH1'])} in 1h")
    return {'kind': KIND, 'title': f"Hold ${snap['symbol']} for 1 hour", 'plan': plan, 'source': 'dexscreener', 'outcome': outcome, 'at': snap['at']}


def settle_one(snap, pair):
    """→ 'won' / 'lost' / 'flat' for one snapshot, given the pair now (None = the pool is gone: a rug counts as lost)."""
    now = features(pair, time.time()) if pair else None
    if not now:
        return 'lost'
    move = (now['price'] / snap['price'] - 1) * 100
    return 'won' if move >= WIN_PCT else 'lost' if move <= LOSS_PCT else 'flat'


def _load(p, d):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return d


async def collect(http, folder, now=None):
    """One snapshot + settle pass. `http` is an httpx.AsyncClient-like object. → the learner's counts."""
    now = now or time.time()
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    open_p, rows_p, st_p = folder / 'market_open.json', folder / 'market_rows.jsonl', folder / 'market.json'
    snaps = _load(open_p, []); st = _load(st_p, {'won': 0, 'lost': 0, 'flat': 0, 'collects': 0})
    # SETTLE: snapshots that have been held long enough, one /pairs call per 30
    due = [s for s in snaps if now - s['at'] >= HOLD_SEC]
    keep = [s for s in snaps if now - s['at'] < HOLD_SEC]
    settled = []
    for i in range(0, len(due), 30):
        part = due[i:i + 30]
        r = await http.get(f"{API}/latest/dex/pairs/solana/{','.join(s['pair'] for s in part)}")
        got = {p.get('pairAddress'): p for p in ((r.json() or {}).get('pairs') or [])} if r.status_code == 200 else None
        if got is None:
            keep += part; continue           # DexScreener down: try again next collect, never guess
        for s in part:
            o = settle_one(s, got.get(s['pair']))
            st[o] = st.get(o, 0) + 1
            if o != 'flat':
                settled.append(row_of(s, o))
    if settled:
        with open(rows_p, 'a', encoding='utf-8') as f:
            for r in settled:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    # SNAPSHOT: coins on DexScreener right now that we are not already holding
    held = {s['mint'] for s in keep}
    mints = []
    for path in ('/token-profiles/latest/v1', '/token-boosts/latest/v1'):
        r = await http.get(API + path)
        if r.status_code == 200:
            for t in r.json() or []:
                m = t.get('tokenAddress')
                if t.get('chainId') == 'solana' and m and m not in held and m not in mints:
                    mints.append(m)
    mints = mints[:PER_COLLECT]
    if mints and len(keep) < MAX_OPEN:
        r = await http.get(f"{API}/tokens/v1/solana/{','.join(mints)}")
        best = {}
        for p in (r.json() or []) if r.status_code == 200 else []:
            m = (p.get('baseToken') or {}).get('address')
            if m and _num((p.get('liquidity') or {}).get('usd')) > _num(((best.get(m) or {}).get('liquidity') or {}).get('usd')):
                best[m] = p
        for p in best.values():
            f = features(p, now)
            if f:
                keep.append(f)
    st['collects'] += 1; st['open'] = len(keep); st['rows'] = st.get('rows', 0) + len(settled); st['at'] = round(now)
    st['nextSettle'] = round(min((s['at'] for s in keep), default=now) + HOLD_SEC)
    open_p.write_text(json.dumps(keep[-MAX_OPEN:])); st_p.write_text(json.dumps(st))
    return st


def rows(folder, cap):
    """The settled market rows (newest first), at most `cap` of them."""
    try:
        lines = Path(folder, 'market_rows.jsonl').read_text().splitlines()
    except OSError:
        return []
    return [json.loads(x) for x in lines[::-1][:max(0, cap)] if x.strip()]
