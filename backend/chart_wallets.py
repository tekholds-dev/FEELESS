"""🐋 WHO TRADED THIS CHART (pure, tested `tests/test_chart_wallets.py`). Owner, 2026-10-18: "I want to see snipers, bundles, whales and top
trader bubbles on each chart in the Agents tab". Every swap the trade tape saw is tagged from records FEELESS already holds — the coin's
launch read (sniper / bundle wallets, the creator) and its holder scan (top holders) — plus the tape itself (whales, top traders).
Nothing is fetched here; an unread launch means no sniper / bundle tags (never a guess)."""
import statistics
from datetime import datetime

WHALE_USD = 500.0      # a whale trade = at least this …
WHALE_X = 5.0          # … and this many times the typical trade on this coin
TOP_N = 3              # the top traders = the wallets that moved the most $ in the window
KEEP = 40              # bubbles per chart (newest)
TAGS = ('dev', 'sniper', 'bundle', 'holder', 'whale', 'top')


def _ts(v):
    if isinstance(v, (int, float)):
        return float(v) / (1000.0 if v > 1e12 else 1.0)
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00')).timestamp()
    except ValueError:
        return None


def tag_trades(trades, intel=None, keep=KEEP):
    """trades = the tape's rows {ts, kind, usd, price, wallet, tx}; intel = the holder scan {sniperWallets, bundledWallets, creator,
    topHolders}. → {'trades': [{at, side, usd, px, w, tags}] (only tagged ones, newest first), 'counts': {tag: n}, 'top': [{w, usd}]}."""
    it = intel or {}
    snipers, bundles = set(it.get('sniperWallets') or ()), set(it.get('bundledWallets') or ())
    dev = it.get('creator')
    holders = {h.get('owner') or h.get('address') for h in (it.get('topHolders') or [])[:10] if isinstance(h, dict) and h.get('kind', 'wallet') == 'wallet'} - {None}   # pools / programs are not holders
    rows = []
    for t in trades or []:
        at, w = _ts(t.get('ts') or t.get('at')), t.get('wallet') or t.get('w')
        usd = float(t.get('usd') or 0)
        if at is None or not w or usd <= 0:
            continue
        rows.append({'at': round(at), 'side': 'buy' if str(t.get('kind') or t.get('side')).lower().startswith('b') else 'sell', 'usd': round(usd, 2),
                     'px': t.get('price') or t.get('px'), 'w': w, 'tx': t.get('tx')})
    if not rows:
        return {'trades': [], 'counts': {}, 'top': []}
    med = statistics.median(r['usd'] for r in rows)
    vol = {}
    for r in rows:
        vol[r['w']] = vol.get(r['w'], 0.0) + r['usd']
    top = sorted(vol.items(), key=lambda kv: -kv[1])[:TOP_N]
    top_w = {w for w, _ in top}
    out, counts = [], {}
    for r in rows:
        tags = [k for k, ok in (('dev', r['w'] == dev), ('sniper', r['w'] in snipers), ('bundle', r['w'] in bundles), ('holder', r['w'] in holders),
                                 ('whale', r['usd'] >= WHALE_USD and r['usd'] >= WHALE_X * med), ('top', r['w'] in top_w)) if ok]
        if tags:
            for k in tags:
                counts[k] = counts.get(k, 0) + 1
            out.append({**r, 'tags': tags})
    out.sort(key=lambda r: -r['at'])
    return {'trades': out[:keep], 'counts': counts, 'top': [{'w': w, 'usd': round(u, 2)} for w, u in top]}
