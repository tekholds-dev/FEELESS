"""🧹 Receipts, airdrops, holder perks, linked identities — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""
import reputation_service as _RSM  # noqa: E402,F401  (body models / annotations; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import reputation_service
    return reputation_service


def _receipt_rows():
    rs = _rs()
    if not rs.RECEIPTS_PATH.exists():
        return []
    rows = []
    for line in rs.RECEIPTS_PATH.read_text().splitlines():
        try:
            rows.append(rs.json.loads(line))
        except Exception:
            continue
    return rows


@router.post('/api/reputation/receipts')
async def store_receipt(payload: _RSM.ReceiptIn, request: Request):
    rs = _rs()
    if not await rs._ip_hit(rs._receipt_hits, request, 20, 60):  # each receipt costs RPC lookups; cap per IP
        raise rs.HTTPException(429, 'Too many receipts — slow down.')
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', payload.sig) or not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', payload.wallet):
        raise rs.HTTPException(400, 'Bad signature or wallet.')
    kind = payload.kind if payload.kind in ('swap', 'buy', 'sell', 'airdrop', 'launch', 'transfer', 'pool', 'claim') else 'swap'
    if rs._receipt_sigs is None:
        rs._receipt_sigs = {r[1]: r[2] for r in rs._receipt_rows()}
    if payload.sig in rs._receipt_sigs:
        if rs._receipt_sigs[payload.sig] != payload.wallet:
            raise rs.HTTPException(400, 'That wallet did not sign this transaction.')
        return {'ok': True, 'duplicate': True}
    tx = None
    async with rs.httpx.AsyncClient(timeout=20) as http:
        for _ in range(6):  # freshly-sent txs can take a few seconds to be queryable
            tx = await rs._rpc(http, 'getTransaction', [payload.sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
            if tx:
                break
            await rs.asyncio.sleep(2)
    if not tx:
        raise rs.HTTPException(404, 'Transaction not found on-chain yet — retry shortly.')
    meta = tx.get('meta') or {}
    if meta.get('err'):
        raise rs.HTTPException(400, 'Transaction failed on-chain; no receipt stored.')
    keys = [k['pubkey'] for k in tx['transaction']['message']['accountKeys']]
    signers = [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]
    if payload.wallet not in signers:
        raise rs.HTTPException(400, 'That wallet did not sign this transaction.')
    deltas = {}
    for side, sign in (('preTokenBalances', -1), ('postTokenBalances', 1)):
        for b in meta.get(side) or []:
            if b.get('owner') == payload.wallet:
                amt = float((b.get('uiTokenAmount') or {}).get('uiAmount') or 0)
                deltas[b['mint']] = deltas.get(b['mint'], 0) + sign * amt
    idx = keys.index(payload.wallet)
    sol = ((meta.get('postBalances') or [0])[idx] - (meta.get('preBalances') or [0])[idx]) / 1e9
    row = [tx.get('blockTime'), payload.sig, payload.wallet, kind,
           [[m, float(f'{d:.9g}')] for m, d in deltas.items() if abs(d) > 0], float(f'{sol:.9g}'), tx.get('slot'), (meta.get('fee') or 0) / 1e9]
    async with rs._receipt_lock:
        if payload.sig not in rs._receipt_sigs:
            with rs.RECEIPTS_PATH.open('a') as f:
                f.write(rs.json.dumps(row, separators=(',', ':')) + '\n')
            rs._receipt_sigs[payload.sig] = payload.wallet
            try:  # confirmed on-chain → a receipt notification (the bell), linking the tx
                label = {'swap': 'Swap', 'buy': 'Buy', 'sell': 'Sell', 'launch': 'Launch', 'pool': 'Pool creation', 'airdrop': 'Airdrop', 'transfer': 'Transfer', 'claim': 'Creator fee claim'}[kind]
                rs.notify(payload.wallet, 'reward', f"✅ {label} confirmed on-chain · {sol:+.4f} SOL", f'https://solscan.io/tx/{payload.sig}', once=f'tx:{payload.sig}')
            except Exception:
                pass
    return {'ok': True, 'receipt': row}


async def _first_active(http, account: str):
    """Oldest on-chain activity of a token account = when this wallet started holding."""
    rs = _rs()
    hit = rs._age_cache.get(account)
    if hit and rs.time.time() - hit[0] < 6 * 3600:
        return hit[1]
    before, oldest = None, None
    for _ in range(8):
        opts = {'limit': 1000}
        if before:
            opts['before'] = before
        try:
            sigs = await rs._rpc(http, 'getSignaturesForAddress', [account, opts])
        except Exception:
            break
        if not sigs:
            break
        oldest = sigs[-1].get('blockTime') or oldest
        before = sigs[-1]['signature']
        if len(sigs) < 1000:
            break
    rs._age_cache[account] = (rs.time.time(), oldest)
    return oldest


def _snaps():
    rs = _rs()
    return rs._json_load(rs.SNAP_PATH, {'snaps': []})


async def _perk_tier(address: str):
    rs = _rs()
    address = rs.primary_of(address)
    hit = rs._perk_cache.get(address)
    if hit and rs.time.time() - hit[0] < 120:
        return hit[1]
    usd = 0.0
    if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address or ''):
        mint = (await rs._ecosystem_mints()).get('fee')
        if mint:
            try:
                usd = await rs._holding_usd(address, mint)
            except Exception:
                usd = 0.0
    tier = max(t['tier'] for t in rs.PERK_TIERS if usd >= t['minUsd'])
    if rs._is_staff(address):
        tier = max(t['tier'] for t in rs.PERK_TIERS)
    rs._perk_cache[address] = (rs.time.time(), (tier, usd))
    return tier, usd


def _ids():
    rs = _rs()
    return rs._json_load(rs.IDENTITY_PATH, {'links': {}})


def primary_of(address: str) -> str:
    """Solana account is the primary identity; a linked 0x account resolves to it."""
    rs = _rs()
    return rs._ids()['links'].get(address, {}).get('primary', address)


def linked_of(address: str):
    rs = _rs()
    p = rs.primary_of(address)
    return sorted({p, *[a for a, v in rs._ids()['links'].items() if v.get('primary') == p]})


async def _asset_owner(asset):
    """Current owner of a Core asset (DAS getAsset), cached 5 min. None if unknown."""
    rs = _rs()
    hit = rs._asset_owner_cache.get(asset)
    if hit and rs.time.time() - hit[0] < 300:
        return hit[1]
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            r = await rs._rpc(http, 'getAsset', {'id': asset})
        owner = ((r or {}).get('ownership') or {}).get('owner')
    except Exception:
        owner = None
    rs._asset_owner_cache[asset] = (rs.time.time(), owner)
    return owner


async def _fuse_pay_to(f):
    """Who the creator cut is paid to: the card's on-chain holder if the Fuse has a card, else the creator."""
    rs = _rs()
    card = f.get('card') or {}
    return (await rs._asset_owner(card['asset']) if card.get('asset') else None) or f.get('creator')


def _site(request):
    rs = _rs()
    return rs.os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/') or str(request.base_url).rstrip('/')


async def _sol_usd_live():
    """SOL in $: Jupiter's price (what real swaps route at) → DexScreener's SOL/USDC pool → the last good price (≤ 10 min) → 0.
    NEVER a made-up number: it used to fall back to a hard-coded $150 when DexScreener answered empty (2026-10-07, SOL was $116) —
    every real buy then read "~30% above market" and was refused, and card values were priced at $150 SOL. 0 = callers wait."""
    rs = _rs()
    px = 0.0
    try:
        px = rs._fuse._f(((await rs._jup_prices([rs._fw.SOL_MINT])) or {}).get(rs._fw.SOL_MINT))
    except Exception:
        px = 0.0
    if px <= 0:
        try:
            p = await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': '58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2', 'mint': rs._fw.SOL_MINT}])   # Raydium SOL/USDC
            px = rs._fuse._f(next(iter(p.values())).get('priceUsd')) if p else 0.0
        except Exception:
            px = 0.0
    px = rs._fw.sol_price_pick(px, rs._SOL_LAST, rs.time.time())
    return px


async def _vault_view(vid, v, deposit_sol=10.0):
    rs = _rs()
    pools = rs._vault.clean_pools(v.get('pools'))
    pairs = await rs._fuse_pairs(pools)
    meta = {k: rs._fuse.leg_meta(p) for k, p in pairs.items()}
    sol_usd = await rs._sol_usd_live()
    sim = rs._vault.simulate(pools, meta, sol_usd, deposit_sol, v.get('mgmtBps', 0), v.get('perfBps', 0))
    return {'id': vid, **{k: v.get(k) for k in ('name', 'emoji', 'tagline', 'mgmtBps', 'perfBps', 'status', 'programId', 'createdAt')},
            'pools': [{**p, **meta.get(p['pairAddress'], {}), 'liveWeight': sim['weights'].get(p['pairAddress'])} for p in pools],
            'solUsd': sol_usd, 'sim': sim, 'feeWallet': rs._fee_cfg().get('vaultFeeWallet') or ''}


def _qs():
    """🗄 SITE-8: quest state as one row per wallet in SQLite: any number of workers check in at once without wiping each other (sql_store)."""
    rs = _rs()
    import sql_store as _sqls
    k_ = str(rs.QUEST_STATE_PATH)
    if k_ not in rs._qs_docs:
        rs._qs_docs[k_] = _sqls.Docs(rs.QUEST_STATE_PATH)
    return rs._qs_docs[k_]


def _quest_defs():
    rs = _rs()
    return rs._quests.merge(rs._quests.DEFAULTS, rs._json_load(rs.QUESTS_PATH, {}))


def _streak(days):
    rs = _rs()
    have, n, d = set(days), 0, rs.time.time()
    if rs.time.strftime('%Y-%m-%d', rs.time.gmtime(d)) not in have:
        d -= 86400   # today not checked in yet: the streak is still alive from yesterday
    while rs.time.strftime('%Y-%m-%d', rs.time.gmtime(d)) in have:
        n += 1; d -= 86400
    return n


def _fuse_quest_stats(mine):
    """⚛️ Fuse → the ONE season: cards opened, survivors (swapped a weak coin and closed in profit), battles won, weeks
    that beat FeeCat, season medals — counts for badges + timestamps so weekly quests and season XP see them."""
    rs = _rs()
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    pos = [x for x in d.get('positions') or [] if x['wallet'] in mine]
    ids = {x['id'] for x in pos}
    surv = [x for x in pos if x.get('closedAt') and any(e.get('kind') == 'buy' for e in x.get('events') or []) and rs._hq.position_pnl(x, {})['pnlUsd'] > 0]
    wins = [b['at'] for b in d.get('battleLog') or [] if (b.get('winnerKey') or '').startswith('user:') and b['winnerKey'][5:] in ids]
    beats = [w['week'] + rs._hq.WEEK for w in d.get('catChallenge') or [] for cid in w.get('ids') or [] if cid in ids]
    medals = [s['week'] + rs._hq.WEEK for s in d.get('seasons') or [] for t_ in s.get('top') or [] if t_['id'] in ids]
    return {'counts': {'fuse_cards': len(pos), 'fuse_survivors': len(surv), 'battle_wins': len(wins), 'feecat_beats': len(beats), 'season_medals': len(medals)},
            'events': {'fuse_card': [rs._fuse._f(x.get('at')) for x in pos], 'battle_win': wins, 'feecat_beat': beats, 'season_medal': medals,
                       # ⚔ backing feeds the season too: every back + every winning back is XP (daily + weekly quests) → rank
                       'battle_back': [t for w in mine for t in ((d.get('backLog') or {}).get(w) or [])],
                       'back_win': [t for w in mine for t in ((d.get('backWins') or {}).get(w) or [])],
                       'bracket_win': [t for w in mine for t in ((d.get('bracketWins') or {}).get(w) or [])]}}


async def _quest_raw(me, board=None):
    """Everything the engine measures, read from FEELESS's own records (nothing self-reported)."""
    rs = _rs()
    mine = set(rs.linked_of(me)) | {me}
    trades = [{'side': x.get('side'), 'usd': x.get('usd') or x.get('poolUsd') or 0, 'token': x.get('token'), 'ts': x.get('ts')}
              for w, rows in rs._json_load(rs.FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or []]
    chat = [{'room': m.get('room'), 'chain': m.get('chain'), 'ts': m.get('ts')} for ms in rs._chat_load()['rooms'].values() for m in ms
            if isinstance(m, dict) and not m.get('system') and (m.get('identity') or m.get('address')) in mine]
    calls = [c for c in (rs._json_load(rs.CALLS_PATH, {}).get('calls') or {}).values() if c.get('callerAddress') in mine]
    board = board or await rs.caller_board(days=90)
    hits = sum(r.get('hits', 0) for r in board['rows'] if r.get('callerAddress') in mine)
    pts = rs._pts().get(me) or {}
    st = rs._qs().get(me) or {}
    days = set(st.get('days') or []) | ({pts['claims']['daily']} if (pts.get('claims') or {}).get('daily') else set())
    creator = rs._load()['creators'].get(rs._creator_key('solana', me))
    return {'trades': trades, 'chat': chat, 'call_ts': [c.get('at') or 0 for c in calls], 'call_hits': hits,
            'invited': len(rs._json_load(rs.REF_PATH, {'by': {}})['by'].get(me, [])),
            'followers': sum(1 for lst in (rs._json_load(rs.FOLLOW_PATH, {}).get('following') or {}).values() if me in lst),
            'launches': rs.score_creator(creator)['tokenCount'] if creator else 0, 'points': int(pts.get('total') or 0),
            'signin_days': sorted(days), 'streak': max(rs._streak(days), int(pts.get('streak') or 0)),
            'fee_usd': await rs._fee_usd(me), 'fee_mints': [m for m in (await rs._ecosystem_mints()).values() if m], 'first_seen': st.get('first'),
            'events': {**(st.get('events') or {}), **(fz := rs._fuse_quest_stats(mine))['events'], 'rug_found': __import__('bounty').find_events(rs._block_load()['wallets'], mine),
                       'predict_pick': [t for w in mine for t in (((rs._json_load(rs.PREDICT_PATH, {}).get('players') or {}).get(w) or {}).get('pickAt') or [])],
                       'predict_win': [t for w in mine for t in (((rs._json_load(rs.PREDICT_PATH, {}).get('players') or {}).get(w) or {}).get('winAt') or [])]}, 'fuse': fz['counts'],
            'alerts_set': sum(len(e.get('watch') or []) for e in rs._push_load()['subs'].values() if (e.get('prefs') or {}).get('address') in mine)}


def _quest_season():
    rs = _rs()
    return {**rs.QUEST_SEASON_DEFAULT, **(rs._json_load(rs.QUESTS_PATH, {}).get('season') or {})}


async def _quest_summary(address):
    rs = _rs()
    me = rs.primary_of(address)
    hit = rs._quest_cache.get(me)
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    manual = (rs._json_load(rs.QUESTS_PATH, {}).get('manual') or {}).get(me)
    if rs._is_staff(me):   # FEELESS HQ: every badge (and so every perk) unlocked
        manual = {**(manual or {}), 'grant': [b['id'] for b in rs._quest_defs()], 'revoke': []}
    raw = await rs._quest_raw(me)
    out = {'address': me, **rs._quests.summary(rs._quest_defs(), raw, manual)}
    # First time each badge shows as earned is its earn date (season scoring + "new" flags). Written only on change.
    st = rs._qs().get(me) or {}
    earned_at = dict(st.get('earned') or {})
    new = [b['id'] for b in out['badges'] if b['earned'] and b['id'] not in earned_at]
    if new:
        # Editions: the first EDITION_CAP wallets to EARN a badge (not granted) are numbered forever: #007 / 100.
        eds = rs._json_load(rs.EDITIONS_PATH, {})
        for bid in new:
            earned_at[bid] = rs.time.time()
            real = next((b for b in out['badges'] if b['id'] == bid and not b.get('granted')), None)
            lst = eds.setdefault(bid, [])
            if real and me not in lst and len(lst) < rs.EDITION_CAP:
                lst.append(me)
        rs._json_save(rs.EDITIONS_PATH, eds)
        rs._qs().update(me, lambda cur: {**(cur or {}), 'earned': {**earned_at, **((cur or {}).get('earned') or {})}, 'first': (cur or {}).get('first') or rs.time.time(), 'days': (cur or {}).get('days') or []})
    season = rs._quest_season()
    eds = rs._json_load(rs.EDITIONS_PATH, {})
    out['editions'] = {bid: lst.index(me) + 1 for bid, lst in eds.items() if me in lst}
    out['editionCap'] = rs.EDITION_CAP
    out.update(earnedAt=earned_at, season={**season, 'score': rs._quests.season_score(out['badges'], raw, earned_at, season)},
               trophies=[it for it in rs._json_load(rs.COLLECTION_PATH, {}).get(me, []) if it.get('kind') == 'quest'])
    rs._quest_cache[me] = (rs.time.time(), out)
    return out


async def _quest_rarity():
    """Share of active wallets holding each badge, recomputed at most every 10 minutes (one caller-board read)."""
    rs = _rs()
    if rs._rarity_cache.get('at', 0) > rs.time.time() - 600:
        return rs._rarity_cache['data']
    wallets = set(rs._json_load(rs.FEELESS_TRADES_PATH, {})) | set(rs._pts()) | set(rs._qs().all())
    board = await rs.caller_board(days=90); defs = rs._quest_defs(); held = {}
    for w in list(wallets)[:2000]:
        try:
            s = rs._quests.summary(defs, await rs._quest_raw(rs.primary_of(w), board), (rs._json_load(rs.QUESTS_PATH, {}).get('manual') or {}).get(rs.primary_of(w)))
        except Exception:
            continue
        for b in s['badges']:
            if b['earned']:
                held[b['id']] = held.get(b['id'], 0) + 1
    data = {'pct': rs._quests.rarity(held, len(wallets)), 'holders': held, 'wallets': len(wallets)}
    rs._rarity_cache.update(at=rs.time.time(), data=data)
    return data

