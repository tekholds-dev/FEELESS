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
LAUNCHPAD_LABELS = {'pump': 'Pump.fun', 'bonk': 'LetsBONK', 'raydium': 'LaunchLab', 'other': 'Solana movers'}
NEW_MAX_AGE_HOURS = 12
TREND_MIN_MC, TREND_MIN_VOL1H, TREND_MIN_TX1H = 15_000, 5_000, 30   # what a launch coin needs to be listed on the trending board
BOARD_MAX = 660   # most coins looked up per board build (DexScreener: 30 a call → ≤ 22 calls a build)


def pump_pages(kind):
    """Which Pump.fun index pages a board reads → [(sort, offset, cache seconds)]. The first pages are live (20s); deeper pages
    move slowly and are cached longer so the wide pull doesn't burst Pump's rate limit."""
    if kind == 'new':
        return [('created_timestamp', 0, 20), ('created_timestamp', 50, 20), ('created_timestamp', 100, 45), ('created_timestamp', 150, 45),
                ('last_trade_timestamp', 0, 20), ('last_trade_timestamp', 50, 20), ('last_trade_timestamp', 100, 45)]
    return ([('last_trade_timestamp', off, 20 if off < 100 else 45) for off in (0, 50, 100, 150, 200, 250)]
            + [('market_cap', off, 60 if off == 0 else 180) for off in (0, 50, 100, 150, 200)])



def _f(value, default=0.0):
    try:
        out = float(value)
        return out if out == out else default
    except (TypeError, ValueError):
        return default


def _clamp(value, lo=0.0, hi=1.0):
    return max(lo, min(hi, value))


# 🔥 PUMP'S OWN TRENDING BOARD (the Trending tab on pump.fun: FLY, LOOP …). Not in the public coin index — pump.fun's page reads it
# from its board indexer. Refreshed every PUMP_TREND_TTL (owner: "keep pump fun trending updating every 10 min"); its coins join
# the launch feed FIRST and are never cut by the board cap. Found 2026-10-07: the owner had to open pump.fun to find LOOP and FLY.
PUMP_TREND_PATH = '/boards/trending'
PUMP_TREND_PARAMS = {'tier': 'web', 'surface': 'TRENDING', 'platform': 'WEB', 'limit': 150, 'chains': 'solana'}
PUMP_TREND_TTL = 600


def pump_trend_candidate(e, rank, now_ms=None):
    """One row of Pump's trending board → a board candidate (rank 1 = top of Pump's list), or None."""
    mint = str((e or {}).get('m') or '')
    if not mint.isalnum() or not str(e.get('c') or 'solana').startswith('solana'):
        return None
    now_ms = now_ms or time.time() * 1000
    age = _f(e.get('age'))
    pad = 'pump' if (e.get('lp') or e.get('pg')) == 'pump' or mint.endswith('pump') else 'bonk' if mint.endswith('bonk') else 'other'
    return {'mint': mint, 'launchpad': pad, 'symbol': e.get('t'), 'name': e.get('n'), 'image': e.get('i'),
            'createdAt': now_ms - age * 1000 if age > 0 else 0.0, 'marketCap': _f(e.get('mc')), 'athMarketCap': _f(e.get('ath')),
            'replies': 0, 'live': bool(e.get('lv')), 'graduated': bool(e.get('gd')), 'curveProgress': None,
            'socials': sum(1 for k in ('tw', 'ws', 'tg') if e.get(k)), 'mover': True, 'pumpTrend': rank,
            'platformName': 'Pump trending', 'url': f'https://pump.fun/coin/{mint}'}


def pump_trend_rows(data, now_ms=None):
    """The board snapshot → candidates in Pump's own order."""
    out = []
    for e in (data or {}).get('entries') or [] if isinstance(data, dict) else []:
        c = pump_trend_candidate(e, len(out) + 1, now_ms)
        if c and c['mint'] not in {x['mint'] for x in out}:
            out.append(c)
    return out


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
            # 2026-10-07: was cap ≥ $25K · $15K/h · 60 trades — only ~125 launch coins clear that at any moment, so every list
            # read the same whatever was pulled. The BOARD shows more; the engine's own gates (volume, flow, safety) are unchanged.
            if not cand.get('pumpTrend') and (mc < TREND_MIN_MC or fl['volH1'] < TREND_MIN_VOL1H or fl['txH1'] < TREND_MIN_TX1H or fl['chH1'] < -40):
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
            'quality': {'score': sc, 'reasons': reasons[:3]}, **({'pumpTrend': cand['pumpTrend']} if cand.get('pumpTrend') else {}),
        })
    out.sort(key=lambda p: -p['quality']['score'])
    return out


# 🌊 MOVERS: Jupiter's own live rankings (what is trending / most traded on Solana over 5m · 1h · 6h, 100 each). The Pump index
# pages above are "biggest" and "most recently traded" — a coin running +100% on real volume is in neither unless it is also
# huge or traded this second. 2026-10-06: the launch feed held 111 coins while Pump's trending tab was full of coins it never saw.
JUP_LISTS = (('toptrending', '1h'), ('toptraded', '1h'), ('toptrending', '5m'), ('toptrending', '6h'),
             # 2026-10-07 (owner: "more pump and other platform coins — list looking the same"): the feed held ~125 coins. Five more
             # live rankings (most traded now / over 6h / over a day, organic score, a day of trending) roughly double the movers.
             ('toptraded', '5m'), ('toptraded', '6h'), ('toporganicscore', '1h'), ('toptrending', '24h'), ('toptraded', '24h'))
JUP_RECENT = '/tokens/v2/recent'   # … and Jupiter's newest launches across EVERY launchpad (pump, bonk, LaunchLab, stonk.fun, Meteora DBC …)


JUP_MAX_AGE_D = 30   # a mover from another venue (stonk.fun, Meteora DBC, MetaDAO, a plain Raydium / Meteora pool …) joins while it is this young
JUP_PADS = {'pump.fun': 'pump', 'letsbonk.fun': 'bonk', 'bonk.fun': 'bonk', 'raydium-launchlab': 'raydium'}


def jup_candidate(tok, now_ms=None):
    """A Jupiter token-list row → a board candidate, or None. Pump / LetsBONK coins by their mint suffix or `launchpad` tag; a coin
    from ANY other venue joins as 'other' while it is at most JUP_MAX_AGE_D days old (movers are not only on Pump: on 2026-10-06
    28 of Jupiter's 100 trending coins were young coins from stonk.fun, Meteora DBC, MetaDAO or pools with no launchpad at all).
    Whether it graduated is not in the row — the caller re-reads it from the coin's live pair where it can."""
    mint = str((tok or {}).get('id') or '')
    if not mint:
        return None
    created = 0.0
    try:
        from datetime import datetime
        created = datetime.fromisoformat(str((tok.get('firstPool') or {}).get('createdAt') or '').replace('Z', '+00:00')).timestamp() * 1000
    except (ValueError, TypeError):
        created = 0.0
    pad = 'pump' if mint.endswith('pump') else 'bonk' if mint.endswith('bonk') else JUP_PADS.get(str(tok.get('launchpad') or '').lower())
    if not pad:
        now_ms = now_ms or time.time() * 1000
        if not created or now_ms - created > JUP_MAX_AGE_D * 8.64e7 or mint in ('So11111111111111111111111111111111111111112',):
            return None
        pad = 'other'
    return {'mint': mint, 'launchpad': pad, 'symbol': tok.get('symbol'), 'name': tok.get('name'), 'image': tok.get('icon'), 'createdAt': created,
            'marketCap': _f(tok.get('mcap') or tok.get('fdv')), 'athMarketCap': 0.0, 'replies': 0, 'live': False, 'graduated': True, 'curveProgress': None,
            'socials': sum(1 for k in ('twitter', 'website', 'telegram') if tok.get(k)), 'mover': True, 'platformName': tok.get('launchpad') or None,
            'url': f"https://pump.fun/coin/{mint}" if pad == 'pump' else f"https://letsbonk.fun/token/{mint}" if pad == 'bonk' else f"https://jup.ag/tokens/{mint}"}


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


# 🟢 PUMP PROFILE: what Pump itself says about a coin, shaped for the coin profile + coin drawer. Pump moved its coin record from
# `/coins/{mint}` to `/coins-v2/{mint}` (the old path answers 404), which silently blanked the logo fallback, the graduation read
# and every "pump profile" on the site. Pure: `d` = that record; None when it is not a coin record.
def _http_url(u):
    u = str(u or '').strip()
    return u if u.startswith('https://') or u.startswith('http://') else None


def pump_profile(d, now_ms=0):
    if not isinstance(d, dict) or not d.get('mint') or not d.get('symbol'):
        return None
    f = lambda v: float(v or 0) if isinstance(v, (int, float, str)) and str(v).replace('.', '', 1).replace('-', '', 1).isdigit() else 0.0
    mc, ath, made = f(d.get('usd_market_cap') or d.get('market_cap_usd')), f(d.get('ath_market_cap')), f(d.get('created_timestamp'))
    ath_usd = max(ath, mc) if ath > 0 else 0.0     # Pump's ATH is already in $ (checked live: SK ath 257,626 beside usd_market_cap 210,549); never under today's cap
    links = [(k, _http_url(d.get(k))) for k in ('twitter', 'telegram', 'website')]
    return {'mint': d['mint'], 'name': str(d.get('name') or '')[:60], 'symbol': str(d.get('symbol'))[:20], 'image': _http_url(d.get('image_uri')),
            'banner': None if d.get('hide_banner') else _http_url(d.get('banner_uri')), 'description': str(d.get('description') or '')[:600],
            'links': [{'type': 'x' if k == 'twitter' else k, 'url': u} for k, u in links if u],
            'creator': d.get('creator'), 'createdAt': made or None, 'ageH': round((now_ms - made) / 3.6e6, 1) if made and now_ms else None,
            'graduated': d.get('complete') is True, 'pool': d.get('pump_swap_pool') or d.get('pool_address'),
            'mcapUsd': round(mc, 2), 'athUsd': round(ath_usd, 2), 'offAthPct': round((mc / ath_usd - 1) * 100, 1) if ath_usd > 0 and mc > 0 else None,
            'vol1hUsd': round(f(d.get('volume_1h_usd')), 2), 'liqUsd': round(f(d.get('canonical_pool_liquidity_usd')), 2),
            'replies': int(f(d.get('reply_count'))), 'live': bool(d.get('is_currently_live')), 'banned': bool(d.get('is_banned')), 'nsfw': bool(d.get('nsfw')),
            'verified': bool(d.get('verified')), 'cashback': bool(d.get('is_cashback_enabled')),
            'lastTradeAt': f(d.get('last_trade_timestamp')) or None, 'url': f"https://pump.fun/coin/{d['mint']}"}


def keep_last_board(hit, ranked, failed, now):
    """📡 True = serve the previous board: this build lost DexScreener batches AND came out empty or under a third of the last one,
    while that one is < 10 min old. 2026-10-07: a 429 burst built an EMPTY board, it was cached as fresh, and every list went blank.
    `hit` = (built_at, rows, meta) or None."""
    if not hit or not failed or now - hit[0] > 600:
        return False
    return len(ranked) < max(1, len(hit[1]) // 3)


def _iso_ms(v):
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(v or '').replace('Z', '+00:00')).timestamp() * 1000
    except (ValueError, TypeError):
        return 0.0


def jup_pair(tok):
    """📡 A Jupiter token row → a DexScreener-SHAPED pair (the same fields every reader uses), or None. The fallback when DexScreener's
    API answers empty: 2026-10-07 it returned `pairs: null` even for SOL/USDC (from any IP) while its website worked — the launch feed,
    every picker list and Coming up went blank. Pair = the graduated pool, else the first pool (the launch curve). `source: 'jupiter'`."""
    t = tok or {}
    mint, px = str(t.get('id') or ''), _f(t.get('usdPrice'))
    pool = t.get('graduatedPool') or (t.get('firstPool') or {}).get('id')
    if not mint or not pool or px <= 0:
        return None
    st = {k: t.get(f'stats{k}') or {} for k in ('5m', '1h', '6h', '24h')}
    vol = {k: _f(s.get('buyVolume')) + _f(s.get('sellVolume')) for k, s in st.items()}
    created = _iso_ms((t.get('firstPool') or {}).get('createdAt'))
    socials = [{'type': k, 'url': t[k]} for k in ('twitter', 'telegram') if t.get(k)]
    return {'chainId': 'solana', 'dexId': 'pumpswap' if t.get('graduatedPool') and mint.endswith('pump') else 'pumpfun' if mint.endswith('pump') else 'jupiter',
            'pairAddress': pool, 'url': f'https://jup.ag/tokens/{mint}', 'source': 'jupiter',
            'baseToken': {'address': mint, 'name': t.get('name'), 'symbol': t.get('symbol')},
            'quoteToken': {'address': 'So11111111111111111111111111111111111111112', 'name': 'Wrapped SOL', 'symbol': 'SOL'},
            'priceUsd': str(px), 'liquidity': {'usd': _f(t.get('liquidity'))}, 'marketCap': _f(t.get('mcap')), 'fdv': _f(t.get('fdv') or t.get('mcap')),
            'volume': {'m5': vol['5m'], 'h1': vol['1h'], 'h6': vol['6h'], 'h24': vol['24h']},
            'priceChange': {'m5': _f(st['5m'].get('priceChange')), 'h1': _f(st['1h'].get('priceChange')), 'h6': _f(st['6h'].get('priceChange')), 'h24': _f(st['24h'].get('priceChange'))},
            'txns': {k2: {'buys': int(_f(st[k].get('numBuys'))), 'sells': int(_f(st[k].get('numSells')))} for k, k2 in (('5m', 'm5'), ('1h', 'h1'), ('6h', 'h6'), ('24h', 'h24'))},
            **({'pairCreatedAt': created} if created else {}),
            'info': {'imageUrl': t.get('icon'), 'socials': socials, **({'websites': [{'url': t['website']}]} if t.get('website') else {})},
            'holders': t.get('holderCount')}
