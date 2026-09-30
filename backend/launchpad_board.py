"""Launchpad board: what Pump.fun, LetsBONK and Raydium LaunchLab would put on their front page.

Candidates come from each launchpad's own index (recently traded, top market cap, newest,
live streams). Each coin is enriched with DexScreener's 5m/1h flow, gated against bots,
dust and dead charts, then scored. Two boards per refresh:
  trending — "bangers": real volume, momentum and community right now
  new      — "good new coins": young coins that already have organic traction
"""
import math
import time

BONK_PLATFORM_ID = 'FfYek5vEz23cMkWsdJwG2oa6EphsvXSHrGpdALN4g6W1'
LAUNCHPAD_LABELS = {'pump': 'Pump.fun', 'bonk': 'LetsBONK', 'raydium': 'LaunchLab'}
NEW_MAX_AGE_HOURS = 12


def _f(value, default=0.0):
    try:
        out = float(value)
        return out if out == out else default
    except (TypeError, ValueError):
        return default


def _clamp(value, lo=0.0, hi=1.0):
    return max(lo, min(hi, value))


def pump_candidate(coin):
    mint = coin.get('mint')
    if not isinstance(mint, str) or not mint.isalnum() or coin.get('is_banned') or coin.get('nsfw'):
        return None
    created = _f(coin.get('created_timestamp'))
    real_sol = _f(coin.get('real_sol_reserves')) / 1e9
    return {
        'mint': mint, 'launchpad': 'pump', 'symbol': coin.get('symbol'), 'name': coin.get('name'),
        'image': coin.get('image_uri'), 'createdAt': created if created > 1e12 else created * 1000,
        'marketCap': _f(coin.get('usd_market_cap')), 'athMarketCap': _f(coin.get('ath_market_cap')),
        'replies': int(_f(coin.get('reply_count'))), 'live': bool(coin.get('is_currently_live')),
        'graduated': bool(coin.get('complete')),
        'curveProgress': None if coin.get('complete') else round(_clamp(real_sol / 85) * 100, 1),
        'socials': sum(1 for k in ('twitter', 'telegram', 'website') if coin.get(k)),
        'url': f'https://pump.fun/coin/{mint}',
    }


def launchlab_candidate(row, platform):
    mint = row.get('mint')
    if not isinstance(mint, str) or not mint.isalnum():
        return None
    finishing = _f(row.get('finishingRate'))
    pad = 'bonk' if platform == 'bonk' else 'raydium'
    return {
        'mint': mint, 'launchpad': pad, 'symbol': row.get('symbol'), 'name': row.get('name'),
        'image': row.get('imgUrl'), 'createdAt': _f(row.get('createAt')), 'marketCap': _f(row.get('marketCap')),
        'athMarketCap': 0.0, 'replies': 0, 'live': False, 'graduated': finishing >= 100,
        'curveProgress': None if finishing >= 100 else round(_clamp(finishing / 100) * 100, 1),
        'socials': sum(1 for k in ('twitter', 'telegram', 'website') if row.get(k)),
        'platformName': (row.get('platformInfo') or {}).get('name'), 'pool': row.get('poolId'),
        'url': f"https://{'letsbonk.fun' if pad == 'bonk' else 'raydium.io/launchpad'}/token/{mint}",
    }


def flow(pair):
    txns, vol, change = pair.get('txns') or {}, pair.get('volume') or {}, pair.get('priceChange') or {}
    h1, m5 = txns.get('h1') or {}, txns.get('m5') or {}
    tx_h1 = int(_f(h1.get('buys')) + _f(h1.get('sells')))
    tx_m5 = int(_f(m5.get('buys')) + _f(m5.get('sells')))
    vol_h1 = _f(vol.get('h1'))
    return {
        'txH1': tx_h1, 'txM5': tx_m5, 'volH1': vol_h1, 'volM5': _f(vol.get('m5')),
        'buyShareH1': _f(h1.get('buys')) / tx_h1 if tx_h1 else 0.0,
        'avgTradeH1': vol_h1 / tx_h1 if tx_h1 else 0.0,
        'chM5': _f(change.get('m5')), 'chH1': _f(change.get('h1')),
        'liq': _f((pair.get('liquidity') or {}).get('usd')), 'mc': _f(pair.get('marketCap') or pair.get('fdv')),
    }


def is_bot(fl):
    """Micro-buy volume bots: one-sided flow or tiny average trades at volume."""
    return fl['txH1'] >= 50 and (fl['buyShareH1'] > 0.96 or fl['buyShareH1'] < 0.15 or fl['avgTradeH1'] < 12)


def score(cand, fl, now_ms):
    reasons, s = [], 0.0
    s += 30 * _clamp(math.log10(1 + fl['volH1'] / 1000) / 3)          # $1M/h = full marks
    s += 15 * _clamp(fl['txH1'] / 600)
    s += 15 * _clamp((fl['chH1'] + 20) / 80)
    s += 10 * _clamp((fl['chM5'] + 5) / 20)
    s += 6 * _clamp(cand['replies'] / 300) + 2 * _clamp(cand['socials'] / 2) + (2 if cand['live'] else 0)
    share = fl['buyShareH1']
    s += 10 * (1 - _clamp(abs(share - 0.62) / 0.3))                   # healthy two-sided, buyer-led flow
    if cand['graduated'] and fl['mc']:
        depth = fl['liq'] / fl['mc']
        s += 10 * (1 - _clamp(abs(depth - 0.2) / 0.25))
    elif cand['curveProgress'] is not None:
        s += 10 * _clamp(cand['curveProgress'] / 100)
    if fl['volH1'] >= 100_000:
        reasons.append(f"${fl['volH1'] / 1000:,.0f}K vol 1h")
    if fl['chH1'] >= 25:
        reasons.append(f"+{fl['chH1']:.0f}% 1h")
    if cand['replies'] >= 100:
        reasons.append(f"{cand['replies']} replies")
    if cand['live']:
        reasons.append('live stream')
    if cand['curveProgress'] is not None and cand['curveProgress'] >= 70:
        reasons.append(f"{cand['curveProgress']:.0f}% to graduation")
    age_h = (now_ms - cand['createdAt']) / 3_600_000 if cand['createdAt'] else None
    return round(s, 1), reasons, age_h


def build_board(candidates, dex_pairs, kind, now_ms=None):
    """candidates: {mint: cand}; dex_pairs: {mint: best DexScreener pair}. Returns ranked pairs."""
    now_ms = now_ms or time.time() * 1000
    out = []
    for mint, cand in candidates.items():
        pair = dex_pairs.get(mint)
        if not pair:
            continue
        fl = flow(pair)
        mc = fl['mc'] or cand['marketCap']
        if is_bot(fl):
            continue
        if cand['athMarketCap'] and mc < 0.15 * cand['athMarketCap'] and cand['athMarketCap'] > 200_000:
            continue                                                     # dead chart: down 85%+ from a real ATH
        sc, reasons, age_h = score(cand, fl, now_ms)
        if kind == 'trending':
            if mc < 25_000 or fl['volH1'] < 15_000 or fl['txH1'] < 60 or fl['chH1'] < -40:
                continue
        else:
            if age_h is None or age_h > NEW_MAX_AGE_HOURS or mc < 7_000 or fl['volH1'] < 2_500 or fl['txH1'] < 20 or fl['chH1'] < -50:
                continue
            sc = round(sc + 10 * _clamp(1 - age_h / NEW_MAX_AGE_HOURS), 1)   # fresher is better among equals
        info = dict(pair.get('info') or {})
        if not info.get('imageUrl') and cand.get('image'):
            info['imageUrl'] = cand['image']
        out.append({
            **pair, 'info': info, 'launchpadId': cand['launchpad'], 'launchpadLabel': LAUNCHPAD_LABELS[cand['launchpad']],
            'platformName': cand.get('platformName'), 'graduated': cand['graduated'], 'curveProgress': cand['curveProgress'],
            'replyCount': cand['replies'], 'athMarketCap': cand['athMarketCap'] or None, 'isLive': cand['live'],
            'marketStage': 'new' if kind == 'new' else pair.get('marketStage'), 'launchpadUrl': cand['url'],
            'quality': {'score': sc, 'reasons': reasons[:3]},
        })
    out.sort(key=lambda p: -p['quality']['score'])
    return out


def gecko_pool_to_pair(pool, mint, cand):
    """GeckoTerminal pool (LaunchLab curves DexScreener hasn't indexed) → shared pair contract."""
    a = pool.get('attributes') or {}
    tx, vol, ch = a.get('transactions') or {}, a.get('volume_usd') or {}, a.get('price_change_percentage') or {}
    created = a.get('pool_created_at')
    try:
        from datetime import datetime
        created_ms = int(datetime.fromisoformat(created.replace('Z', '+00:00')).timestamp() * 1000) if created else None
    except ValueError:
        created_ms = None
    window = lambda w: {'buys': int(_f((tx.get(w) or {}).get('buys'))), 'sells': int(_f((tx.get(w) or {}).get('sells')))}
    dex = ((pool.get('relationships') or {}).get('dex') or {}).get('data', {}).get('id')
    return {
        'chainId': 'solana', 'dexId': dex or cand['launchpad'], 'pairAddress': a.get('address'),
        'url': f"https://www.geckoterminal.com/solana/pools/{a.get('address')}",
        'baseToken': {'address': mint, 'symbol': cand.get('symbol'), 'name': cand.get('name')},
        'quoteToken': {'address': 'So11111111111111111111111111111111111111112', 'symbol': 'SOL', 'name': 'Wrapped SOL'},
        'priceUsd': a.get('base_token_price_usd'),
        'marketCap': _f(a.get('market_cap_usd')) or _f(a.get('fdv_usd')) or None, 'fdv': _f(a.get('fdv_usd')) or None,
        'liquidity': {'usd': _f(a.get('reserve_in_usd'))},
        'volume': {w: _f(vol.get(w)) for w in ('m5', 'h1', 'h6', 'h24')},
        'txns': {w: window(w) for w in ('m5', 'h1', 'h6', 'h24')},
        'priceChange': {w: _f(ch.get(w)) for w in ('m5', 'h1', 'h6', 'h24')},
        'pairCreatedAt': created_ms, 'info': {'imageUrl': cand.get('image')}, 'source': 'GeckoTerminal',
    }


def dex_candidate(pair):
    """Migrated launchpad coins found in DexScreener discovery. Pump/LetsBONK mints carry their suffix."""
    mint = (pair.get('baseToken') or {}).get('address') or ''
    pad = 'pump' if mint.endswith('pump') else 'bonk' if mint.endswith('bonk') else None
    if not pad or pair.get('chainId') != 'solana':
        return None
    info = pair.get('info') or {}
    on_curve = str(pair.get('dexId') or '').lower() in ('pumpfun', 'pump.fun', 'launchlab', 'raydium-launchlab')
    return {
        'mint': mint, 'launchpad': pad, 'symbol': (pair.get('baseToken') or {}).get('symbol'), 'name': (pair.get('baseToken') or {}).get('name'),
        'image': info.get('imageUrl'), 'createdAt': _f(pair.get('pairCreatedAt')), 'marketCap': _f(pair.get('marketCap') or pair.get('fdv')),
        'athMarketCap': 0.0, 'replies': 0, 'live': False, 'graduated': not on_curve, 'curveProgress': None,
        'socials': len(info.get('socials') or []) + len(info.get('websites') or []),
        'url': f"https://{'pump.fun/coin' if pad == 'pump' else 'letsbonk.fun/token'}/{mint}",
    }


def gecko_network_pairs(payload, chain):
    """GeckoTerminal /networks/{net}/(trending|new)_pools?include=base_token,quote_token → shared pair contract.
    Covers every chain's own DEXes, so small networks (Cronos, zkSync, Zora…) never load empty."""
    tokens = {t.get('id'): (t.get('attributes') or {}) for t in payload.get('included') or []}
    out = []
    for pool in payload.get('data') or []:
        rel = pool.get('relationships') or {}
        base = tokens.get(((rel.get('base_token') or {}).get('data') or {}).get('id')) or {}
        quote = tokens.get(((rel.get('quote_token') or {}).get('data') or {}).get('id')) or {}
        if not base.get('address'):
            continue
        pair = gecko_pool_to_pair(pool, base['address'], {'launchpad': 'dex', 'symbol': base.get('symbol'), 'name': base.get('name'),
                                                          'image': base.get('image_url') if str(base.get('image_url') or '').startswith('http') else None})
        addr = pair['pairAddress']
        pair.update({'chainId': chain, 'url': f"https://dexscreener.com/{chain}/{addr}",
                     'quoteToken': {'address': quote.get('address'), 'symbol': quote.get('symbol'), 'name': quote.get('name')}})
        out.append(pair)
    return out
