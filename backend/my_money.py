"""💵 YOUR MONEY (owner, 2026-10-22 ELITE 1e: "one YOUR MONEY tower in the capital — every proved position, live"). Pure + tested.

Every position FEELESS can PROVE for a wallet, priced live:
  · coins it holds from its verified FEELESS trades (/pnl receipts) × the coin's live price — with the coin's own 24 h move, never a P&L here:
    the receipts' SOL flow includes fees and P&L never includes fees (CLAUDE.md › Money rules)
  · its family block's real market positions (block_markets: LST / JLP balances, position NFTs, Kamino shares) — $ value + live APY
→ the total, each position's share of it (the tower's floors), sorted biggest first; dust under a cent and unpriced coins are counted apart."""

DUST = 0.01
MAX = 24


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def best_prices(pairs):
    """DexScreener token pairs → {mint: {priceUsd, symbol, pairAddress, ch24, image}} from each mint's deepest pool."""
    out, depth = {}, {}
    for p in pairs or []:
        m = (p.get('baseToken') or {}).get('address')
        liq = _f((p.get('liquidity') or {}).get('usd')) or 0
        if not m or not _f(p.get('priceUsd')) or liq < depth.get(m, -1):
            continue
        depth[m] = liq
        out[m] = {'priceUsd': _f(p['priceUsd']), 'symbol': (p.get('baseToken') or {}).get('symbol'), 'pairAddress': p.get('pairAddress'),
                  'ch24': _f((p.get('priceChange') or {}).get('h24')), 'image': (p.get('info') or {}).get('imageUrl'), 'liq': liq}
    return out


def assemble(held, prices, buildings=()):
    """held = [{mint, holding}] · prices = best_prices(...) · buildings = the family block's own view → {total, positions, coins, markets, dust, unpriced}."""
    pos, dust, unpriced = [], 0, 0
    for t in held or []:
        units = _f(t.get('holding')) or 0
        if units <= 0:
            continue
        p = (prices or {}).get(t.get('mint')) or {}
        if not p.get('priceUsd'):
            unpriced += 1
            continue
        usd = units * p['priceUsd']
        if usd < DUST:
            dust += 1
            continue
        pos.append({'kind': 'coin', 'key': t['mint'], 'sym': p.get('symbol') or t['mint'][:4], 'usd': round(usd, 2), 'ch24': p.get('ch24'),
                    'pair': p.get('pairAddress'), 'image': p.get('image'), 'units': units})
    for b in buildings or []:
        usd = _f(b.get('usd')) or 0
        if b.get('state') == 'built' and usd >= DUST:
            pos.append({'kind': 'market', 'key': b.get('key'), 'sym': b.get('sym') or b.get('name'), 'name': b.get('name'), 'usd': round(usd, 2), 'apy': _f(b.get('apy'))})
    pos.sort(key=lambda x: -x['usd'])
    total = sum(x['usd'] for x in pos)
    for x in pos:
        x['share'] = round(x['usd'] / total, 4) if total else 0
    return {'total': round(total, 2), 'positions': pos[:MAX], 'coins': sum(1 for x in pos if x['kind'] == 'coin'),
            'markets': sum(1 for x in pos if x['kind'] == 'market'), 'dust': dust, 'unpriced': unpriced}
