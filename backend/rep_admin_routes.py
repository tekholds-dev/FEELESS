"""🧩 SITE-5 slice 11 (2026-11-14): ADMIN routes (staff / admin, no money words), moved out of
reputation_service by scripts/move-routes.py --kind admin: byte-for-byte the same bodies (every auth / staff / signed = quoted check kept), helpers
looked up on reputation_service when a route runs, body models read off the loaded service (imported at the END of it)."""
import reputation_service as _RSM  # noqa: E402
from fastapi import APIRouter, Query, Request

router = APIRouter()


def _rs():
    import reputation_service
    return reputation_service


@router.post('/api/reputation/uploads')
async def upload_image(payload: _RSM.UploadPayload, request: Request):
    """Images for profiles, launches and seasons. Everyone: 15 MB (animated GIFs: 40 MB). A signed-in creator/admin
    (HQ session) may upload big GIFs/art up to 25 MB; the creator wallet's GIFs are not size-limited (250 MB memory guard)."""
    rs = _rs()
    import base64
    import re
    head = (payload.dataUrl or '')[:40]
    mt = re.match(r'^data:(image/(?:png|jpeg|webp|gif));base64,', head)
    if not mt:
        raise rs.HTTPException(400, 'Only PNG, JPG, WEBP or GIF images are supported.')
    role = 'user'
    try:
        role = 'owner' if rs._require_admin(request) in rs._owner_wallets() else 'admin'
    except rs.HTTPException:
        pass
    cap = rs.upload_cap(mt.group(1), role)
    if role == 'user':
        # No sign-in needed to upload, so cap it: 20 images per hour per IP (stops anyone filling the disk).
        if not await rs._ip_hit(rs._upload_ip, request, 20, 3600):
            raise rs.HTTPException(429, 'Upload limit reached — try again in an hour.')
    if len(payload.dataUrl) > cap * 4 // 3 + 64:   # 🔒 audit #8: refuse an oversized body BEFORE the regex and the base64 decode
        raise rs.HTTPException(413, f'Image must be under {cap // 1_000_000} MB.')
    m = re.match(r'^data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)$', payload.dataUrl)
    if not m:
        raise rs.HTTPException(400, 'Only PNG, JPG, WEBP or GIF images are supported.')
    raw = base64.b64decode(m.group(2))
    if len(raw) > cap:
        raise rs.HTTPException(413, f'Image must be under {cap // 1_000_000} MB.')
    sig = raw[:12]
    if not (sig.startswith(b'\x89PNG') or sig.startswith(b'\xff\xd8') or sig[:4] == b'RIFF' or sig[:3] == b'GIF'):
        raise rs.HTTPException(400, 'File is not a valid image.')
    name = f"{rs.uuid.uuid4().hex}.{rs.UPLOAD_TYPES[m.group(1)]}"
    (rs.UPLOAD_DIR / name).write_bytes(raw)
    return {'url': f'/api/reputation/uploads/{name}'}


@router.post('/api/reputation/profile')
async def save_profile(payload: _RSM.ProfileSave):
    rs = _rs()
    if payload.session:
        who = rs.session_address(payload.session)
        if not who or rs.primary_of(who) != rs.primary_of(payload.address):
            raise rs.HTTPException(401, 'Session expired — sign once to continue.')
        ts = rs.time.time()
    else:
        expected_prefix = f'FEELESS profile update\naddress:{payload.address}\nts:'
        if not payload.message.startswith(expected_prefix):
            raise rs.HTTPException(400, 'Unexpected message.')
        try:
            ts = int(payload.message[len(expected_prefix):])
        except ValueError:
            raise rs.HTTPException(400, 'Bad timestamp.')
        if abs(rs.time.time() - ts) > 300:
            raise rs.HTTPException(401, 'Signature expired — sign again.')
        if not rs._verify_wallet(payload.address, payload.message, payload.signature):
            raise rs.HTTPException(401, 'Signature does not match this wallet.')
    tier = (await rs._perk_tier(payload.address))[0]
    owner = rs.primary_of(payload.address)
    if payload.target and rs.primary_of(payload.target) != owner:
        raise rs.HTTPException(403, 'This wallet is not linked to that profile.')
    async with rs._profile_lock:
        d = rs._profiles_load()
        prev = d['profiles'].get(owner, {})
        if prev.get('lastTs', 0) >= ts:
            raise rs.HTTPException(409, 'Replay rejected — sign a fresh update.')
        clean = rs._clean_profile(payload.profile)
        if clean['handle'] and any(a != owner and (v or {}).get('handle') == clean['handle'] for a, v in d['profiles'].items()):
            raise rs.HTTPException(409, f"@{clean['handle']} is taken.")
        if clean['featuredBadges']:
            earned = {b['id'] for b in (await rs.wallet_badges(owner))['badges']}
            clean['featuredBadges'] = [b for b in clean['featuredBadges'] if b in earned]
        locks_ = dict(prev.get('nameLock') or {})   # 🪪 a name changes once every 7 days, staff any time; each change is stamped and past names are sealed
        for k_ in ('displayName', 'handle'):
            if not locks_.get(k_) and prev.get(k_) == clean[k_]:   # a name from before the rule stays, unstamped, until it changes
                continue
            ok_, rec_, why_ = rs._name_lock.check(locks_.get(k_), owner, clean[k_], rs._is_staff(owner))
            if not ok_:
                raise rs.HTTPException(429, why_)
            if rec_:
                locks_[k_] = rec_
        un, _r = rs._unlocks(owner)
        if (rs.RING_TIERS[clean['ring']] > tier and f"ring:{clean['ring']}" not in un) or (rs.NAMEFX_TIERS[clean['nameFx']] > tier and f"nameFx:{clean['nameFx']}" not in un):
            raise rs.HTTPException(403, 'That style is a $FEE holder perk — hold more $FEE to unlock it.')
        if rs.TIER_THEMES.get(clean['theme'], 0) > tier:
            raise rs.HTTPException(403, {1: 'That backdrop is a $FEE holder perk: hold $10+ of $FEE.', 2: 'That backdrop is an Alpha perk: reach Fee Insider tier.',
                                      3: 'That backdrop is a Whale perk: reach Fee Whale tier.'}[rs.TIER_THEMES[clean['theme']]])
        # Pictures never disappear by accident: an empty avatar/cover keeps the previous one unless
        # the owner explicitly removed it; every image ever set is kept in mediaHistory.
        cleared = set((payload.profile or {}).get('cleared') or [])
        hist = list(prev.get('mediaHistory') or [])
        for k in ('avatarUrl', 'bannerUrl'):
            if not clean.get(k) and prev.get(k) and k not in cleared:
                clean[k] = prev[k]
            if prev.get(k) and prev[k] != clean.get(k):
                hist.append({'field': k, 'url': prev[k], 'at': rs.time.time()})
        row_ = {**clean, 'mediaHistory': hist[-20:], 'lastTs': ts, 'updatedAt': rs.time.time(), 'nameLock': locks_}

        def put_(cur):   # one transaction for this wallet: a newer save from another worker in between wins, this replay is refused
            if (cur or {}).get('lastTs', 0) >= ts:
                raise rs.HTTPException(409, 'Replay rejected — sign a fresh update.')
            return row_
        rs._prof().update(owner, put_)
    return {'ok': True, 'profile': {k: v for k, v in row_.items() if k != 'nameLock'}}


@router.post('/api/reputation/chat')
async def chat_post(payload: _RSM.ChatPost):
    rs = _rs()
    text = payload.text.strip()
    if not text or len(text) > 500:
        raise rs.HTTPException(400, 'Messages must be 1–500 characters.')
    if not rs._re.match(r'^[a-z0-9-]{3,120}$', payload.room) and not payload.room.startswith('coin-') and not rs._re.match(r'^wall-([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', payload.room):
        raise rs.HTTPException(400, 'Unknown room.')
    if abs(rs.time.time() - payload.ts) > 120:
        raise rs.HTTPException(401, 'Signature expired — try again.')
    if payload.session:
        if rs.primary_of(rs.session_address(payload.session) or "") != rs.primary_of(payload.address) or not rs.session_address(payload.session):
            raise rs.HTTPException(401, 'Chat session expired — sign in to chat again.')
    elif not rs._verify_wallet(payload.address, rs._chat_message_to_sign(payload.room, payload.address, payload.ts, text), payload.signature):
        raise rs.HTTPException(401, 'Signature does not match this wallet.')
    is_admin = rs._is_staff(payload.address)  # admins / the creator's linked wallets post anywhere, unthrottled (0c: staff unlock everything)
    _is_crew, _crew_ok = rs._crew_room_ok(payload.room, payload.address)
    if _is_crew and not _crew_ok and not is_admin:
        raise rs.HTTPException(403, 'Only family members can post in a family room.')
    if payload.room == 'feeless-updates' and not is_admin:
        raise rs.HTTPException(403, 'Updates is read-only — only FEELESS admins post here.')
    if not is_admin and payload.room in rs._ALPHA and not await rs._alpha_allowed(payload.room, payload.address):
        raise rs.HTTPException(403, f"{rs._ALPHA[payload.room]['name']} unlocks at ${rs._ALPHA[payload.room]['minUsd']:,} held in $FEE.")
    eg = None if is_admin else await rs.evm_gate(payload.room, payload.address)
    if eg and not eg['allowed']:
        raise rs.HTTPException(403, f"{eg['symbol']} is an EVM coin — link or switch to your 0x account." if eg.get('needsChain') else f"Hold at least ${rs.MIN_HOLD_USD:.0f} of {eg['symbol']} to chat here (you hold ${eg['holdingUsd'] or 0:.2f}).")
    coin = None if is_admin else await rs._room_mint(payload.room)
    if coin and payload.address.startswith('0x'):
        raise rs.HTTPException(403, f'{coin[1]} lives on Solana — switch your wallet to its Solana account to chat here.')
    if coin:
        value = await rs._holding_usd(payload.address, coin[0])
        if value < rs.MIN_HOLD_USD:
            raise rs.HTTPException(403, f'Hold at least ${rs.MIN_HOLD_USD:.0f} of {coin[1]} to chat here (you hold ${value:.2f}).')
    tokens = []
    for ca in rs.CA_RE.findall(text)[:2]:
        try:
            async with rs.httpx.AsyncClient(timeout=8) as http:
                r = await http.get(f'https://api.dexscreener.com/latest/dex/search?q={ca}')
                pairs = sorted((r.json() or {}).get('pairs') or [], key=lambda p: -(((p.get('liquidity') or {}).get('usd')) or 0))
            if pairs:
                tokens.append({'address': ca, 'chainId': pairs[0].get('chainId'), 'pairAddress': pairs[0].get('pairAddress'),
                               'symbol': (pairs[0].get('baseToken') or {}).get('symbol'), 'pair': pairs[0], 'fetched_at': rs.time.time()})
        except Exception:
            pass
    if rs.is_muted(payload.address):
        raise rs.HTTPException(403, 'You are muted by FEELESS moderators for now.')
    tier = (await rs._perk_tier(payload.address))[0]
    boosted = False
    if payload.boost:
        credits = (rs._pts().get(rs.primary_of(payload.address)) or {}).get('boostCredits', 0)
        if tier < 2 and credits <= 0:
            raise rs.HTTPException(403, 'Boosting is a Fee Insider perk — hold $100+ of $FEE or buy boosts with points.')
        if tier < 2:
            d_ = rs._pts(); d_[rs.primary_of(payload.address)]['boostCredits'] = credits - 1; rs._json_save(rs.POINTS_PATH, d_)
        if rs.time.time() - rs._boost_last.get(payload.address, 0) < 600:
            raise rs.HTTPException(429, 'One boost every 10 minutes.')
        boosted = True
    async with rs._chat_lock:
        d = rs._chat_load()
        last = d['lastTs'].get(payload.address, 0)
        if payload.ts <= last:
            raise rs.HTTPException(409, 'Replay rejected — sign a fresh message.')
        if not is_admin and rs.time.time() - d.get('lastAt', {}).get(payload.address, 0) < 3:
            raise rs.HTTPException(429, 'Slow down — one message every 3 seconds.')
        if payload.room.startswith('city-') and not is_admin and (d.get('streetSlow') or {}).get(payload.room):   # 🐢 a Don / staff slowed this street
            _fam_ = rs._street_fams()(payload.address) or {}
            wait_ = rs._stc.slow_wait(d['streetSlow'][payload.room], ((d.get('streetLastAt') or {}).get(payload.room) or {}).get(rs.primary_of(payload.address)), rs.time.time(),
                                   rs._is_staff(payload.address) or bool(_fam_.get('don')))
            if wait_:
                raise rs.HTTPException(429, f"🐢 Slow mode on this street — your next line in {wait_}s.")
        verdict = None if is_admin else rs._spam_check(d, payload.room, payload.address, text, tier)
        if verdict:
            rs.CHAT_PATH.write_text(rs.json.dumps(d))
            raise rs.HTTPException(429 if verdict.startswith('Slow') else 403, verdict)
        d['lastTs'][payload.address] = payload.ts
        d.setdefault('lastAt', {})[payload.address] = rs.time.time()
        if payload.room.startswith('city-'):   # 🐢 per-street last line (slow mode reads it); ≤ 400 wallets per street
            sla_ = d.setdefault('streetLastAt', {}).setdefault(payload.room, {})
            sla_[rs.primary_of(payload.address)] = rs.time.time()
            if len(sla_) > 400:
                for w_, _t in sorted(sla_.items(), key=lambda kv: kv[1])[:len(sla_) - 400]:
                    sla_.pop(w_, None)
        if boosted:
            rs._boost_last[payload.address] = rs.time.time()
        msg = {'id': rs.uuid.uuid4().hex[:16], 'handle': rs.handle_of(rs.primary_of(payload.address)), 'room': payload.room, 'address': payload.address, 'chain': 'evm' if payload.address.startswith('0x') else 'solana',
               'tier': tier, 'boosted': boosted,
               'username': rs._display_name(rs.primary_of(payload.address)), 'identity': rs.primary_of(payload.address), 'text': text, 'ts': int(rs.time.time() * 1000),
               'parentId': payload.parentId, 'mentions': sorted(set(rs.MENTION_RE.findall(text)))[:10], 'tokens': tokens,
               'profile': {'address': rs.primary_of(payload.address), 'chain': 'solana' if not rs.primary_of(payload.address).startswith('0x') else 'evm'}}
        if payload.room.startswith('city-'):   # 👑 the Familia city chats: every line wears the poster's family tag + colour
            import crews as _cr
            c_ = _cr.crew_of(rs._json_load(rs.CREWS_PATH, {}), payload.address)
            if c_:
                msg['fam'] = {'tag': c_.get('tag'), 'color': ((c_.get('badge') or {}).get('colors') or [None])[0]}
        room = d['rooms'].setdefault(payload.room, [])
        room.append(msg)
        rs._track_pin(d, payload.room, room, payload.parentId)
        try:
            if payload.room.startswith('wall-'):
                rs.notify(payload.room[5:], 'wall', f"@{rs.handle_of(rs.primary_of(payload.address))} wrote on your wall: {text[:80]}", f"/terminal/profile/{rs.primary_of(payload.room[5:])}", payload.address)
            for h in msg['mentions']:
                who = next((a for a, v in rs._profiles_load()['profiles'].items() if (v or {}).get('handle') == h.lower()), None)
                if who:
                    rs.notify(who, 'mention', f"@{rs.handle_of(rs.primary_of(payload.address))} mentioned you: {text[:80]}", '/terminal/chat', payload.address)
        except Exception:
            pass
        d['rooms'][payload.room] = room[-300:]
        rs.CHAT_PATH.write_text(rs.json.dumps(d))
    if payload.room.startswith(('feed-', 'city-')) and tokens:   # 📞 a coin pasted on a Familia street gets a receipt too (points stay FEEd-only)
        rs._record_feed_calls(msg)
    return {'ok': True, 'message': msg}


@router.get('/api/reputation/alpha-rooms')
async def alpha_rooms(address: str = ''):
    rs = _rs()
    held = await rs._fee_usd(rs.primary_of(address)) if address else 0.0
    admin = rs._is_staff(address) if address else False
    d = rs._chat_load()
    return {'holdingUsd': held, 'rooms': [{**r, 'unlocked': admin or held >= r['minUsd'], 'messages': len(d['rooms'].get(r['id'], []))} for r in rs.ALPHA_ROOMS]}


@router.get('/api/reputation/admin/chat-guard')
async def admin_chat_guard(request: Request):
    rs = _rs()
    rs._require_admin(request)
    g = rs._chat_load().get('guard') or {}
    now = rs.time.time()
    return {'log': g.get('log', [])[:100], 'cooling': sorted(({'address': a, 'secondsLeft': int(t - now)} for a, t in (g.get('cool') or {}).items() if t > now), key=lambda x: -x['secondsLeft'])}


@router.post('/api/reputation/admin/fuses/evolve')
async def fuses_evolve(request: Request, p: _RSM.FuseEvolveIn):
    """🧬 HQ: breed Fuse baskets from the chain's live pools (best 40 across popular/yield/deep/new) over generations.
    Read-only ranking — the champion is loaded into the Lab, where Fuse in still needs your wallet."""
    rs = _rs()
    rs._require_admin(request)
    raw = await rs._fuse_discover_pairs(p.chain)
    cands = {}
    for lens in rs._fuse.LENSES:
        for r in rs._fuse.discover(raw, lens, p.chain, now_ms=rs.time.time() * 1000, limit=12):
            cands.setdefault(r['pairAddress'], r)
    metas = dict(list(cands.items())[:40])
    sol_usd = await rs._sol_usd_live()
    seeds = rs._hq.bloodline_seeds(rs._json_load(rs.FUSE_HQ_PATH, {}).get('bloodline') or [], set(metas), p.legs) if p.bloodline else []
    out = await rs.asyncio.to_thread(rs._fuse.evolve, metas, p.legs, p.generations, p.population, p.style if p.style in rs._fuse.STYLES else 'yield',
                                  p.sol, sol_usd, p.seed or int(rs.time.time()), seeds)
    out['seeded'] = len(seeds)
    out['champions'] = [rs._champ_view(c, metas, p.chain) for c in out['champions']]
    return {**out, 'solUsd': sol_usd, 'styles': list(rs._fuse.STYLES)}


@router.post('/api/reputation/admin/fuses/auto-yield')
async def admin_auto_yield_set(request: Request):
    """HQ default for NEW Fuse cards (users can still turn it off per card)."""
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    try:
        at = rs._hq.clean_yield_at(body.get('at') or rs._hq.YIELD_DEFAULT_AT)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        d['autoYieldDefault'] = {'on': bool(body.get('on')), 'at': at}
        rs._json_save(rs.FUSE_HQ_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'fuse-auto-yield', rs.json.dumps(d['autoYieldDefault'])); rs._admin_save(ad)
    return d['autoYieldDefault']


@router.post('/api/reputation/fuses/position/switch')
async def fuse_position_switch(p: _RSM.FuseSwitchIn):
    """Switch-in / top-up: new legs join YOUR card only from your verified FEELESS buys, within 3 pools + 3 runners."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    metas = [x for x in (p.legs or [])[:6] if isinstance(x, dict)]
    trades = {x.get('tx'): x for w, rows in rs._json_load(rs.FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or []}
    pairs = [(trades[str(m.get('signature'))], m) for m in metas if str(m.get('signature')) in trades and trades[str(m.get('signature'))].get('side', 'buy') == 'buy']
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise rs.HTTPException(404, 'No open Fuse card with that id for this wallet.')
        used = {leg.get('sig') for x in d.get('positions') or [] for leg in x['legs']}
        pairs = [(t, m) for t, m in pairs if t['tx'] not in used]
        buys_before = sum(1 for e in pos.get('events') or [] if e.get('kind') == 'buy')
        pos, n = rs._hq.add_legs(pos, [t for t, _ in pairs], [m for _, m in pairs], now=rs.time.time())
        filled = [m.get('pairAddress') for _, m in pairs if m.get('pairAddress') in (pos.get('missing') or [])]
        if filled:   # ↻ a retry completed the original buy — not a switch, the 24h clock is untouched
            pos['missing'] = [x for x in pos.get('missing') or [] if x not in filled]
        switched = not filled and sum(1 for e in pos.get('events') or [] if e.get('kind') == 'buy') > buys_before
        if switched:   # a real switch-in (not a top-up)
            pos['lastSwitchAt'] = rs.time.time()
            pos['switchTimes'] = (pos.get('switchTimes') or [])[-9:] + [pos['lastSwitchAt']]
        if n and not filled:
            rs._hq.use_prepaid(pos, n)   # 💳 prepaid swaps cover these buys first
        rs._json_save(rs.FUSE_HQ_PATH, d)
    if n:
        rs.notify(me, 'fuse-card', f"{'⇄ Switched in' if switched else '⚖ Topped up'}: {', '.join('$' + (m.get('symbol') or '?') for _, m in pairs[:3])} on {pos.get('name') or 'your Fuse card'}.{' Next switch in 24h.' if switched and not rs._is_staff(me) else ''}",
               url=f"/terminal/fuse?tab=cards&card={pos['id']}", once=f"card-in-{pos['id']}-{pairs[0][0]['tx'] if pairs else ''}", meta={'claim': 'Confirmed FEELESS buys from your wallet', 'source': 'Fuse cards'})
    return {'ok': True, 'added': n, 'nextSwitchAt': rs._hq.next_switch_at(pos, rs._is_staff(me))}


@router.get('/api/reputation/fuses/limits/{address}')
async def fuse_limits(address: str):
    """How many Fuse cards this wallet may hold open: 2, or 3 with ≥ $200 of $FEE. Each card: 3 pools + 3 runners."""
    rs = _rs()
    me = rs.primary_of(address)
    mine = set(rs.linked_of(me)) | {me}
    open_n = sum(1 for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [] if x['wallet'] in mine and not x.get('closedAt'))
    try:
        fee = await rs._fee_usd(me)
    except Exception:
        fee = 0.0
    mx = rs._hq.card_limit(fee, rs._is_staff(me))
    return {'open': open_n, 'max': mx, 'canOpen': open_n < mx, 'feeUsd': round(fee, 2), 'feeFor3rd': rs._hq.FEE_FOR_3RD_CARD,
            'pools': rs._hq.CARD_POOLS, 'runners': rs._hq.CARD_RUNNERS}


@router.get('/api/reputation/admin/fuses/hq')
async def fuse_hq_admin(request: Request):
    """HQ › Fuse HQ: everyone's Fuse P&L, the paper arena (settles at 24h), bloodlines, published-Fuse health."""
    rs = _rs()
    rs._require_admin(request)
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    now = rs.time.time()
    pos, arena = d.get('positions') or [], d.get('arena') or []
    px = await rs._hq_prices([leg for x in pos for leg in x['legs']] + [leg for e in arena if not e.get('close') for leg in e['legs']])
    vals = [rs._hq.arena_value(e, px, now) for e in arena]
    if any(v['due'] for v in vals):
        d = await rs._arena_settle(px, now)
        vals = [rs._hq.arena_value(e, px, now) for e in d.get('arena') or []]
    rows = [rs._hq.position_pnl(x, px) for x in pos]
    board = rs._hq.arena_board(vals)
    return {'book': rs._hq.book(rows), 'rows': sorted(rows, key=lambda r: -r['pnlUsd'])[:50], 'arena': sorted(vals, key=lambda v: -v['at'])[:40],
            'board': board, 'bestStyle': rs._hq.best_style(board), 'bloodline': d.get('bloodline') or [], 'minSettled': rs._hq.MIN_SETTLED,
            'outlook': rs._hq.outlook(board), 'published': len(rs._json_load(rs.FUSES_PATH, {'fuses': {}})['fuses']),
            'blockedCuts': sum(1 for b in rs._json_load(rs.FUSES_PATH, {}).get('buys') or [] if b.get('selfDeal') or b.get('bot'))}


@router.post('/api/reputation/admin/fuses/hq')
async def fuse_hq_admin_save(request: Request):
    """Enter a champion in the paper arena, save / drop it from the bloodline."""
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    champ = body.get('champion') or {}
    legs = [leg for leg in champ.get('legs') or [] if leg.get('pairAddress')][:rs._fuse.MAX_LEGS]
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        if body.get('action') == 'arena' and len(legs) >= 2:
            e = rs._hq.arena_entry({**champ, 'legs': legs}, str(body.get('style') or 'yield')[:12], await rs._hq_prices(legs), rs.time.time(), rs.uuid.uuid4().hex[:10])
            d['arena'] = ((d.get('arena') or []) + [e])[-rs.ARENA_KEEP:]
        elif body.get('action') == 'bloodline' and len(legs) >= 2:
            pools = sorted(leg['pairAddress'] for leg in legs)
            if not any(b['pools'] == pools for b in d.get('bloodline') or []):
                d['bloodline'] = ((d.get('bloodline') or []) + [{'pools': pools, 'symbols': [leg.get('symbol') for leg in legs], 'fitness': champ.get('fitness'),
                                                                 'style': body.get('style'), 'at': rs.time.time()}])[-30:]
        elif body.get('action') == 'unbloodline':
            d['bloodline'] = [b for b in d.get('bloodline') or [] if b['pools'] != sorted(body.get('pools') or [])]
        else:
            raise rs.HTTPException(400, 'arena | bloodline | unbloodline with a champion.')
        rs._json_save(rs.FUSE_HQ_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, f"fuse-{body.get('action')}", ','.join(leg.get('symbol') or '' for leg in legs)[:120]); rs._admin_save(ad)
    return {'ok': True}


@router.post('/api/reputation/social-feed/x')
async def social_feed_x(p: _RSM.FeedXShare):
    """𝕏 INTO FEEd (owner, 2026-10-19: "should be a way to get X in, or have users do it"): reading X needs a paid API app, so people bring it in —
    paste an X post link, FEELESS reads X's PUBLIC oEmbed (publish.twitter.com, no key, no login) and the post joins the timeline with who
    shared it. ≤ 20 shares a wallet a day; one copy of each post."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    if rs._is_blocked(rs._block_load()['wallets'].get(me)):
        raise rs.HTTPException(403, 'This wallet cannot post here.')
    st_ = rs._sfeed.x_status(p.url)
    if not st_:
        raise rs.HTTPException(400, 'Paste an X post link (x.com/<name>/status/<id>).')
    try:
        r_ = await rs._sf_client().get('https://publish.twitter.com/oembed', params={'url': f'https://twitter.com/{st_[0]}/status/{st_[1]}', 'omit_script': '1', 'dnt': 'true'}, timeout=8)
    except Exception:
        raise rs.HTTPException(502, 'X did not answer — try again.')
    if r_.status_code != 200:
        raise rs.HTTPException(404, 'X has no public post at that link (deleted, private or age-gated).')
    post_ = rs._sfeed.from_x_oembed(r_.json(), p.url, rs._crew_name(me) or (me[:4] + '…' + me[-4:]), rs.time.time())
    if not post_:
        raise rs.HTTPException(404, 'That post has no text to show.')
    async with rs._fsoc_lock:
        d_ = rs._json_load(rs.FEED_X_PATH, {}) or {}
        posts_ = [x for x in d_.get('posts') or [] if x.get('id') != post_['id']]
        day_ = rs.time.time() - 86400
        if sum(1 for x in posts_ if x.get('by') == me and rs._fuse._f(x.get('at')) > day_) >= rs.X_SHARE_DAY and not rs._is_staff(me):
            raise rs.HTTPException(429, f'{rs.X_SHARE_DAY} X shares a day.')
        d_['posts'] = ([{**post_, 'by': me}] + posts_)[:rs._sfeed.X_MAX]
        rs._json_save(rs.FEED_X_PATH, d_)
    rs._SF_CACHE.pop('x', None)
    return {'post': {k: v for k, v in post_.items()}}


@router.get('/api/reputation/crews')
async def crews_board():
    """🛡 Public: the weekly crew board — crews ranked by their members' VERIFIED FEELESS trade results over 7 days (needs ≥ 2 members and ≥ 5 closed trades to rank). 60s cache."""
    rs = _rs()
    import crews as _cr
    now = rs.time.time()
    if rs._crew_cache['data'] and now - rs._crew_cache['at'] < 60:
        return rs._crew_cache['data']
    st = rs._json_load(rs.CREWS_PATH, {})
    members = [m for c in (st.get('crews') or {}).values() for m in c['members']]
    out = {'board': _cr.board(st, rs._crew_pieces(members, now), now, rs._crew_cfg(), rs._is_staff)[:40], 'total': len(st.get('crews') or {}), 'rule': f'Ranked by what members\' verified FEELESS trades did in the last 7 days (price result, fees apart). A family ranks with ≥ {_cr.MIN_MEMBERS} members and ≥ {_cr.MIN_TRADES} closed trades. Everyone signs their own trades — a crew shares no money.', 'at': now}
    rs._crew_cache.update(at=now, data=out)
    return out


@router.get('/api/reputation/crews/of/{address}')
async def crew_of_wallet(address: str):
    """🛡 Public: the crew a wallet is in (tag + name) — for the chip beside names. Nothing else."""
    rs = _rs()
    import crews as _cr
    c = _cr.crew_of(rs._json_load(rs.CREWS_PATH, {}), rs.primary_of(address))
    st_ = rs._json_load(rs.CREWS_PATH, {})
    return {'crew': {'id': c['id'], 'tag': c['tag'], 'name': c['name'], 'badge': _cr.badge_view(c, st_.get('awards'), rs._crew_cfg(), rs._is_staff(c.get('owner')))} if c else None}


@router.get('/api/reputation/admin/crews/revenue')
async def admin_crews_revenue(request: Request):
    """💳 Owner only: what crews have paid the fee wallet — total, count and the last payments (every one links to its on-chain tx)."""
    rs = _rs()
    rs._require_owner(request)
    st = rs._json_load(rs.CREWS_PATH, {}); rows = []
    for c in (st.get('crews') or {}).values():
        for x in c.get('paid') or []:
            rows.append({'crew': c['name'], 'tag': c['tag'], 'kind': x.get('kind'), 'usd': x.get('usd'), 'at': x.get('at'), 'sig': x.get('sig'), 'by': x.get('by'), 'staff': bool(x.get('staff'))})
    rows.sort(key=lambda r: -(r['at'] or 0))
    return {'totalUsd': round(sum(r['usd'] or 0 for r in rows), 2), 'payments': len([r for r in rows if r['usd']]), 'crews': len(st.get('crews') or {}), 'recent': rows[:25]}


@router.post('/api/reputation/admin/fees/crews')
async def admin_fees_crews(request: Request, body: dict):
    """Core › Fees: what a crew costs ($ to start, 5 seats incl. the owner) and what +5 seats cost (owner only; 0–500)."""
    rs = _rs()
    import crews as _cr
    admin = rs._require_owner(request)
    def num(v, d):
        try:
            return max(0.0, min(500.0, round(float(v), 2)))
        except (TypeError, ValueError):
            return d
    prev = rs._crew_cfg()
    unl = {}
    for k, v in ((body.get('unlocks') if isinstance(body.get('unlocks'), dict) else prev.get('unlocks')) or {}).items():   # 🌹 the creator's unlock lines
        part, _, opt = str(k).partition('.')
        if part in _cr.PARTS and opt in _cr.PARTS[part] and isinstance(v, dict) and (v.get('metric') in _cr.METRICS or v.get('metric') in (None, '')):
            unl[k] = {'metric': v.get('metric') or None, 'min': max(0.0, min(100000.0, float(v.get('min') or 0)))}
    cfg = {'createUsd': num(body.get('createUsd'), _cr.CREATE_USD), 'packUsd': num(body.get('packUsd'), _cr.PACK_USD),
           'badgeUsd': num(body.get('badgeUsd', prev.get('badgeUsd', _cr.BADGE_USD)), _cr.BADGE_USD), 'unlocks': unl,
           'houseTaxPct': max(0.0, min(20.0, float(body.get('houseTaxPct', prev.get('houseTaxPct', 5)) or 0)))}   # 🏦 the city's house tax
    async with rs._admin_lock:
        d = rs._admin_load(); d.setdefault('fees', {})['crews'] = cfg
        rs._audit(d, admin, 'fees', f"familia · ${cfg['createUsd']:g} to start · ${cfg['packUsd']:g} per +{_cr.PACK_SEATS} seats · ${cfg['badgeUsd']:g} badge restyle · {len(unl)} unlock lines")
        rs._admin_save(d)
    return {'crews': cfg}


@router.get('/api/reputation/familia-city')
async def familia_city(address: str, session: str):
    """🏙 My family's block (members): lots, MP, stash, goons, the catalog with locks, the log, and rival stashes to rob."""
    rs = _rs()
    import crews as _cr
    me = rs._session_or_401(address, session); now = rs.time.time()
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {}); me = rs._seat_of(st, me); c = _cr.crew_of(st, me)
        if not c:
            raise rs.HTTPException(404, 'Join a family to build a block.')
        boost_, rk_ = rs._city_ctx(c, me, now)
        v_ = rs._fcity.view(c, now, staff=rs._is_staff(me), boost=boost_, mine=True, tax=rs._city_tax())
        v_['rivals'] = rs._city_rivals(st, c, now)
        v_['canBuild'] = rs._is_staff(me) or me == c.get('owner') or rk_.get(me) == 'underboss'
        v_['house'] = int(st.get('house') or 0)
        rs._json_save(rs.CREWS_PATH, st)
    return v_


@router.get('/api/reputation/familia-city/{cid}')
async def familia_city_visit(cid: str):
    """🏙 Visit any family's block (public): its stores, levels, rate, goons and power — never its log."""
    rs = _rs()
    import crews as _cr
    st = rs._json_load(rs.CREWS_PATH, {}); _cr._norm(st); c = (st.get('crews') or {}).get(cid)
    if not c:
        raise rs.HTTPException(404, 'No such family.')
    return rs._fcity.view(c, rs.time.time(), staff=rs._is_staff(c.get('owner')))


@router.get('/api/reputation/familia-block')
async def familia_block(address: str, session: str):
    """🏙 My family's block of REAL market buildings: built (a real position, its $ value, APY, errands) or under construction, + the catalog."""
    rs = _rs()
    import crews as _cr
    me = rs._session_or_401(address, session); now = rs.time.time()
    st = rs._json_load(rs.CREWS_PATH, {}); me = rs._seat_of(st, me); c = _cr.crew_of(st, me)
    if not c:
        raise rs.HTTPException(404, 'Join a family to build a block.')
    _b, rk_ = rs._city_ctx(c, me, now)
    return await rs._fblock_view(c, me, rs._is_staff(me), rk_)


@router.get('/api/reputation/admin/familia/overwatch')
async def admin_familia_overwatch(request: Request):
    """👑 OVERWATCH — the creator's eye on EVERY family (owner, 2026-10-22: "every family's wallet, bank, trades, pools, members, plus Familia
    pricing / limits / fees"). Owner only, read-only: each family's members (wallets + their verified FEELESS trades this week), MP bank, war
    chest + record, turf + home, buildings set to real pools (live APY), the fees it paid, its pinned launch; totals; the prices and limits HQ
    sets. Family wallets with real money wait on the custody pick (P5) — this shows what exists today."""
    rs = _rs()
    rs._require_owner(request)
    import crews as _cr
    now = rs.time.time(); st = rs._json_load(rs.CREWS_PATH, {}); _cr._norm(st); w = st.get('world') or rs._fworld.blank()
    crews_ = list((st.get('crews') or {}).values())
    pieces_ = await rs.asyncio.to_thread(rs._crew_pieces, sorted({m for c in crews_ for m in c.get('members') or []}), now)
    links_ = w.get('links') or {}
    live_p = {r['id']: r for r in ((rs._fpl_cache.get('v') or {}).get('pools') or [])}
    fams = []
    for c in crews_:
        city_ = rs._fcity.city_of(c, now)
        mem_ = []
        for m in c.get('members') or []:
            s_ = _cr.stats(pieces_.get(m, []))
            mem_.append({'address': m, 'name': rs._crew_name(m), 'don': m == c.get('owner'), 'staff': rs._is_staff(m), **s_})
        wk_ = _cr.stats([p_ for m in c.get('members') or [] for p_ in pieces_.get(m, [])])
        turf_ = rs._fworld.turf_of(w, c['id'])
        pools_ = [{'block': b_, 'name': ln_.get('name') or ln_.get('pool'), 'apy': (live_p.get(ln_.get('pool')) or {}).get('apy'), 'tvl': (live_p.get(ln_.get('pool')) or {}).get('tvl')}
                  for b_, ln_ in links_.items() if (w.get('own') or {}).get(b_) == c['id']]
        paid_ = [x for x in c.get('paid') or [] if isinstance(x, dict)]
        fams.append({'id': c['id'], 'tag': c.get('tag'), 'name': c.get('name'), 'badge': _cr.badge_view(c, st.get('awards'), rs._crew_cfg(), rs._is_staff(c.get('owner'))),
                     'owner': {'address': c.get('owner'), 'name': rs._crew_name(c.get('owner') or '')}, 'creator': rs._is_staff(c.get('owner')),
                     'seats': c.get('seats'), 'members': mem_, 'bankMp': int(city_['bank']), 'power': rs._fcity.power(city_), 'chest': rs._fwar.chest(c),
                     'record': rs._fwar.record(c), 'home': (w.get('home') or {}).get(c['id']), 'turf': turf_, 'pools': pools_, 'week': wk_,
                     'paidUsd': round(sum(float(x.get('usd') or 0) for x in paid_), 2), 'payments': len([x for x in paid_ if x.get('usd')]),
                     'launch': {'symbol': (c.get('launch') or {}).get('symbol'), 'mint': (c.get('launch') or {}).get('mint')} if (c.get('launch') or {}).get('mint') else None,
                     'created': c.get('created'), 'code': bool(c.get('codeHash') or c.get('code'))})
    fams.sort(key=lambda f: (-f['creator'], -f['power']))
    cfg_ = rs._crew_cfg()
    return {'families': fams, 'at': round(now, 1),
            'totals': {'families': len(fams), 'members': sum(len(f['members']) for f in fams), 'bankMp': sum(f['bankMp'] for f in fams),
                       'trades7d': sum(f['week']['trades'] for f in fams), 'usd7d': round(sum(f['week']['usd'] for f in fams), 2), 'paidUsd': round(sum(f['paidUsd'] for f in fams), 2),
                       'turf': sum(len(f['turf']) for f in fams), 'pools': sum(len(f['pools']) for f in fams), 'houseMp': int(st.get('house') or 0)},
            'pricing': {'createUsd': _cr.price('create', cfg_), 'packUsd': _cr.price('seats', cfg_), 'badgeUsd': rs._crew_badge_usd(), 'baseSeats': _cr.BASE_SEATS},
            'limits': {k_: v_ for k_, v_ in rs._familia_rules().items() if k_ in ('familiesPerWallet', 'upkeepMp', 'fuseMinMp', 'hitCapPct', 'raidCooldownH', 'maxTurf')},
            'custody': 'Family wallets that hold real money wait on the custody pick (CLAUDE.md P5) — every member trades from their own wallet today.'}


@router.post('/api/reputation/admin/familia/rules')
async def admin_familia_rules_set(request: Request, body: dict):
    """🏙 Owner only: save the Familia rules (clamped). Live ones change the engine at once; planned ones wait for the real-money custody pick."""
    rs = _rs()
    admin = rs._require_owner(request)
    async with rs._admin_lock:
        d = rs._admin_load(); d['familiaRules'] = rs._fworld.clean_rules(body if isinstance(body, dict) else {}, d.get('familiaRules'))
        if isinstance(body, dict) and 'prices' in body:
            d['familiaPrices'] = rs._fcity.clean_prices(body.get('prices') if isinstance(body.get('prices'), dict) else {}, rs._bmk.ISLAND_MP)
            rs._fcity.set_prices(d['familiaPrices'])
        rs._audit(d, admin, 'familia', f"rules · block {d['familiaRules']['blockMp']:g} MP · Fee City ×{d['familiaRules']['feeTier']:g} · Family Fuse {d['familiaRules']['fuseMinMp']:g} MP")
        rs._admin_save(d)
    rs._fworld.set_rules(d['familiaRules'])
    return await rs.admin_familia_rules(request)


@router.get('/api/reputation/familia/broker')
async def familia_broker(address: str = Query('', max_length=64), session: str = Query('', max_length=400)):
    """🏦 Your linked broker accounts, live: cash, buying power, value, positions with P&L (one read / 20 s). `ready` = SnapTrade is set up."""
    rs = _rs()
    import brokers as _bk
    snap_ = bool(_bk.keys(rs.os.environ)[0])
    if not address or not session:
        return {'ready': True, 'snaptrade': snap_, 'linked': False, 'signup': _bk.ALPACA_SIGNUP}
    me_ = rs._session_or_401(address, session)
    rs._brk_seal()
    snap_ = snap_ and (not _bk.personal(_bk.keys(rs.os.environ)[0]) or rs._is_staff(me_))   # a PERSONAL key = the owner's own accounts only
    q_ = rs._brk_q(me_) if snap_ else None
    ak_ = rs._brk_alpaca(me_)
    ck_ = rs._brk_cdc(me_)
    if q_ is None and not ak_ and not ck_:
        return {'ready': True, 'snaptrade': snap_, 'linked': False, 'signup': _bk.ALPACA_SIGNUP}
    hit_ = rs._brk_cache.get(me_)
    if hit_ and rs.time.time() - hit_[0] < 20:
        return hit_[1]
    accts_, pos_, bal_ = [], {}, {}
    if q_ is not None:
        accts_ = await rs._brk_call('GET', '/accounts', q_) or []
        if not accts_ and not ak_ and not ck_:   # set up, nothing linked yet → the LINK MY BROKER door
            return {'ready': True, 'snaptrade': True, 'linked': False, 'signup': _bk.ALPACA_SIGNUP}
        ids_ = [a_.get('id') for a_ in accts_ if a_.get('id')]
        got_ = await rs.asyncio.gather(*[rs.asyncio.gather(rs._brk_call('GET', f'/accounts/{i_}/positions', q_), rs._brk_call('GET', f'/accounts/{i_}/balances', q_), return_exceptions=True) for i_ in ids_])
        pos_ = {i_: (g_[0] if isinstance(g_[0], list) else []) for i_, g_ in zip(ids_, got_)}
        bal_ = {i_: (g_[1] if isinstance(g_[1], list) else []) for i_, g_ in zip(ids_, got_)}
    v_ = _bk.view(accts_, pos_, bal_)
    if ak_:
        try:
            a_, p_ = await rs.asyncio.gather(rs._alpaca_call(ak_, 'GET', '/v2/account'), rs._alpaca_call(ak_, 'GET', '/v2/positions'))
            av_ = _bk.alpaca_view(a_, p_ if isinstance(p_, list) else [], ak_['paper'])
            v_['accounts'] = [av_] + v_['accounts']; v_['value'] = round(v_['value'] + av_['value'], 2); v_['pnl'] = round(v_['pnl'] + sum(x['pnl'] for x in av_['positions']), 2)
        except rs.HTTPException as e:
            v_['alpacaError'] = e.detail
    if ck_:
        try:
            cv_ = _bk.cdc_view(await rs._cdc_call(ck_, 'private/user-balance'))
            v_['accounts'] = v_['accounts'] + [cv_]; v_['value'] = round(v_['value'] + cv_['value'], 2)
        except rs.HTTPException as e:
            v_['cdcError'] = e.detail
    out_ = {'ready': True, 'snaptrade': snap_, 'linked': True, **v_, 'at': round(rs.time.time())}
    rs._brk_cache[me_] = (rs.time.time(), out_)
    return out_


@router.post('/api/reputation/familia/broker/link')
async def familia_broker_link(request: Request):
    """🔗 Link a broker: one SnapTrade user per wallet (its secret sealed at rest) → SnapTrade's Connection Portal URL (5 min) where the user
    logs in to THEIR broker — FEELESS never sees a broker password. Trading is asked for (`trade-if-available`; read-only where a broker can't)."""
    rs = _rs()
    import brokers as _bk
    b_ = await request.json()
    me_ = rs._session_or_401(str((b_ or {}).get('address') or ''), str((b_ or {}).get('session') or ''))
    rs._brk_need()
    if _bk.personal(_bk.keys(rs.os.environ)[0]):   # 🔑 PERSONAL key: the owner links THEIR broker in SnapTrade's portal (no SnapTrade user to make)
        if not rs._is_staff(me_):
            raise rs.HTTPException(403, 'Linking any broker is the owner\'s own for now — add your free Alpaca keys instead.')
        d_ = await rs._brk_call('POST', '/snapTrade/login', None, {'connectionType': 'trade-if-available', 'darkMode': True})
        if not d_.get('redirectURI'):
            raise rs.HTTPException(502, 'SnapTrade gave no portal link.')
        rs._brk_cache.pop(me_, None)
        return {'url': d_['redirectURI']}
    async with rs._brk_lock:
        u_ = rs._brk_user(me_)
        if not u_:
            d_ = await rs._brk_call('POST', '/snapTrade/registerUser', None, {'userId': _bk.user_id(me_)})
            if not d_.get('userSecret'):
                raise rs.HTTPException(502, 'SnapTrade did not register the user.')
            st_ = rs._json_load(rs.BROKERS_PATH, {}) or {}
            st_[me_] = {'uid': d_.get('userId') or _bk.user_id(me_), 'sec': _bk.seal(d_['userSecret'], rs.os.environ), 'at': rs.time.time()}
            rs._json_save(rs.BROKERS_PATH, st_)
            u_ = (st_[me_]['uid'], d_['userSecret'])
    back_ = str((b_ or {}).get('back') or '')
    body_ = {'connectionType': 'trade-if-available', 'darkMode': True, **({'broker': str(b_['broker'])[:40]} if (b_ or {}).get('broker') else {}),
             **({'customRedirect': back_, 'immediateRedirect': True} if rs._re.match(r'^https?://(localhost(:\d+)?|127\.0\.0\.1(:\d+)?|[a-z0-9.-]*feeless[a-z0-9.-]*)(/|$)', back_) else {})}
    d_ = await rs._brk_call('POST', '/snapTrade/login', {'userId': u_[0], 'userSecret': u_[1]}, body_)
    if not d_.get('redirectURI'):
        raise rs.HTTPException(502, 'SnapTrade gave no portal link.')
    rs._brk_cache.pop(me_, None)
    return {'url': d_['redirectURI']}


@router.get('/api/reputation/familia/trade-center')
async def familia_trade_center(address: str = '', session: str = ''):
    """📈 The Trade Center building: the agents' real card live — the aggregate for everyone, every seat (coin · model · live %) for staff."""
    rs = _rs()
    import trade_center as _tcn
    me = rs._session_or_401(address, session) if address and session else None
    return {**_tcn.summary(rs._agents.get('card') or (rs._agents.get('view') or {}).get('card'), staff=bool(me and rs._is_staff(address))),
            'closed': _tcn.closed_view((rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [])}


@router.post('/api/reputation/familia-world/act')
async def familia_world_act(p: _RSM.WorldAct):
    """🗺 buy · sell · move · raid · attack · defend · errand · challenge · reward · redeem — points only. Don / Underboss buy, sell, move, raid
    and spend on rewards; any member runs errands; the raid's sender makes the attack moves, any member of the target answers."""
    rs = _rs()
    import crews as _cr
    me = rs._session_or_401(p.address, p.session); now = rs.time.time(); res_ = None
    cartels_ = await rs.asyncio.to_thread(rs._cartels_now, now)
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {}); _cr._norm(st)
        me = rs._seat_of(st, me); c = _cr.crew_of(st, me)
        if not c:
            raise rs.HTTPException(404, 'Join a family first.')
        w = st.setdefault('world', rs._fworld.blank())
        rs._world_tick(st, w, now)
        rs._fworld.ensure_home(w, c['id'])
        staff_ = rs._is_staff(me)
        boost_, rk_ = rs._city_ctx(c, me, now)
        city = rs._fcity.accrue(rs._fcity.city_of(c, now), now, boost_)
        boss = staff_ or me == c.get('owner') or rk_.get(me) == 'underboss'
        m = c.setdefault('world', {})
        lv = {}
        for l in city['lots'].values():
            lv[l['b']] = max(lv.get(l['b'], 0), l['lvl'])
        try:
            if p.act in ('buy', 'sell', 'move', 'raid', 'reward', 'redeem', 'link', 'unlink', 'billboard') and not boss:
                raise ValueError('Only the Don or the Underboss does that.')
            if p.act == 'fund':   # 💡 keep a turf block ACTIVE: any member from their own points, the Don / Underboss from the bank
                up_ = int(rs._familia_rules().get('upkeepMp') or rs._fworld.UPKEEP_MP) or rs._fworld.UPKEEP_MP
                if p.source == 'bank':
                    if not boss:
                        raise ValueError('Only the Don or the Underboss spends the bank.')
                    take_, hrs_ = rs._fworld.fund_block(w, c['id'], p.block, min(p.mp, int(city['bank'])), now, up_)
                    city['bank'] -= take_
                else:
                    pm_ = m.setdefault('pts', {}); have_ = int(pm_.get(me) or 0)
                    take_, hrs_ = rs._fworld.fund_block(w, c['id'], p.block, min(p.mp, have_), now, up_)
                    pm_[me] = have_ - take_
                res_ = {'fund': {'block': p.block, 'mp': take_, 'hours': hrs_, 'state': 'active'}}
            elif p.act in ('link', 'unlink'):   # 🏦 set a held building to a real pool from the Pool Hub (display only, no funds)
                row_ = None
                if p.act == 'link':
                    hub_ = (rs._fpl_cache.get('v') or {}).get('pools') or []
                    row_ = next((r for r in hub_ if r['id'] == p.pool), None)
                    if not row_:
                        raise ValueError('That pool is not in the hub right now — refresh the Pool Hub.')
                    row_ = rs._fpl.link_row(row_)
                res_ = {'link': rs._fworld.link_block(w, c['id'], p.block, row_)}
            elif p.act == 'billboard':   # 📺 a 24 h billboard slot from the family bank (Don / Underboss)
                city['bank'] -= rs._fworld.billboard(w, {'id': c['id'], 'tag': c.get('tag')}, city['bank'], p.text, p.mint, now)
                res_ = {'billboard': True}
            elif p.act == 'buy':
                city['bank'] -= rs._fworld.buy_block(w, c['id'], city['bank'], p.block, staff_)
            elif p.act == 'sell':
                city['bank'] += rs._fworld.sell_block(w, c['id'], p.block)
            elif p.act == 'move':
                city['bank'] -= rs._fworld.relocate(w, c['id'], city['bank'], p.block, 0.05 * lv.get('gas', 0), staff_)
            elif p.act == 'raid':
                if float(m.get('shieldUntil') or 0) > now:
                    m['shieldUntil'] = 0      # raiding drops your own truce flag
                t, bor, kind, stash = rs._world_target(st, w, p.vs, now, cartels_)
                if kind == 'family' and float(((st['crews'].get(p.vs) or {}).get('world') or {}).get('shieldUntil') or 0) > now:
                    raise ValueError('They are under a truce flag right now.')
                if kind == 'family' and rs._fworld.newcomer_shielded(st['crews'].get(p.vs), now):
                    raise ValueError('That family is new: it cannot be raided for its first 24 hours.')
                if not staff_ and not rs._fworld.can_raid(w, c['id'], bor, kind, lv.get('docks', 0)):   # ⚖ cartels: from any city
                    raise ValueError('Out of reach — hold a block in that borough or one bridge away (docks add reach).')
                hit = [r['lvl'] for r in rs._fcity.ready(city, now, 'hitter')]
                rank = 'don' if (staff_ or me == c.get('owner')) else rk_.get(me, 'soldier')
                rounds = 2 + lv.get('tower', 0) // 3
                res_ = rs._fworld.raid_view(rs._fworld.start(w, {'id': c['id'], 'tag': c.get('tag'), 'name': c.get('name')}, t, me, rank, hit, stash, now,
                                                       rounds, kind), 'a')
            elif p.act in ('attack', 'defend'):
                r = w['raids'].get(p.raid)
                if not r:
                    raise ValueError('No such raid.')
                if p.act == 'attack':
                    if r['a']['id'] != c['id'] or (r['sender'] != me and not boss):
                        raise ValueError('Only the member who led the raid moves.')
                    rs._fworld.attack(r, p.kind, p.lot, now)
                    if r['kind'] in ('cpu', 'cartel'):
                        rs._fworld.tick(r, now)
                else:
                    if r['b']['id'] != c['id']:
                        raise ValueError('That raid is not on your block.')
                    rs._fworld.defend(r, p.kind, p.lot, now)
                rs._world_settle(st, w, r, now)
                res_ = rs._fworld.raid_view(r, 'a' if p.act == 'attack' else 'b')
            elif p.act == 'errand':
                cd = m.setdefault('errandAt', {}).setdefault(me, {})
                mp, pts, _n = rs._fworld.errand(lv, cd, p.kind, now, rs._fcity.rate(city, boost_, now))
                city['bank'] += mp
                city['mpEver'] = city.get('mpEver', 0) + mp
                m['errands'] = int(m.get('errands') or 0) + 1
                pm_ = m.setdefault('pts', {}); pm_[me] = int(pm_.get(me) or 0) + pts   # setdefault FIRST: the right side ran before it and raised KeyError on a family's first errand
                res_ = {'mp': mp, 'pts': pts}
            elif p.act == 'challenge':
                done = m.setdefault('done', [])
                row = rs._fworld.claim_challenge(p.kind, rs._world_metrics(st, c, now), done)
                done.append(row['key'])
                city['crew'].append({'id': city['nextId'], 'k': row['recruit']['k'], 'lvl': row['recruit']['lvl'], 'xp': 0.0, 'hurt': 0, 'special': row['key']})
                city['nextId'] += 1
                city['bank'] += row['mp']
                res_ = {'recruit': row['recruit'], 'mp': row['mp']}
            elif p.act == 'reward':
                cost = 0 if staff_ else rs._fworld.reward(p.kind, city['bank'])
                if p.kind not in rs._fworld.REWARDS:
                    raise ValueError('No such reward.')
                city['bank'] -= cost
                if p.kind == 'rush':
                    m['rushUntil'] = max(now, float(m.get('rushUntil') or 0)) + 3600
                elif p.kind == 'shield':
                    m['shieldUntil'] = max(now, float(m.get('shieldUntil') or 0)) + 7200
                elif p.kind.startswith('title-'):
                    m.setdefault('titles', {})[me] = rs._fworld.REWARDS[p.kind][0].split(': ', 1)[-1]
                elif p.kind == 'badge-boost':
                    m['glowUntil'] = now + 86400
                elif p.kind == 'season':
                    m.setdefault('pts', {})[me] = int(m.setdefault('pts', {}).get(me) or 0) + 500
                res_ = {'reward': p.kind, 'cost': cost}
            elif p.act == 'redeem':
                if me != c.get('owner') and not staff_:
                    raise ValueError('Only the Don files a redeem.')
                spend, fc = rs._fworld.redeem_feecat(int(city['bank']), rs._world_feecat_rate())
                city['bank'] -= spend
                rq = {'id': f"rd{int(now)}", 'cid': c['id'], 'tag': c.get('tag'), 'by': me, 'mp': spend, 'feecat': fc, 'at': now, 'status': 'pending'}
                st['redeems'] = ([rq] + (st.get('redeems') or []))[:200]
                for ow_ in rs._owner_wallets():
                    try:
                        rs.notify(ow_, 'familia', f"🎁 {c.get('tag')} filed a redeem: {spend:,} MP → {fc:,} FEECAT — pay it by hand", push=False)
                    except Exception:
                        pass
                res_ = rq
            else:
                raise ValueError('Unknown city action.')
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        v = rs._world_view(st, c, me, now, cartels_)
        rs._json_save(rs.CREWS_PATH, st)
    rs._crew_cache['data'] = None
    return {**v, 'result': res_}


@router.post('/api/reputation/cats/model-limit')
async def cat_model_limit(p: _RSM.CatModelLimitIn):
    rs = _rs()
    me = rs.session_address(p.session)
    maximum = max(1, min(8, int(rs._fee_cfg().get('catMaxModels', 3))))
    staff = bool(me and rs._is_staff(me))
    usd = (await rs._perk_tier(me))[1] if me and not staff else 0
    return {'maxModels': 8 if staff else min(maximum, 3 if usd >= 100 else 2), 'staff': staff}


@router.post('/api/reputation/familia-fuse/act')
async def familia_fuse_act(p: _RSM.FamFuseAct):
    """⚔ challenge · accept · decline · cancel · bid. Don / Underboss challenge, accept, decline and cancel; any family member bids their
    own points. Points only."""
    rs = _rs()
    import crews as _cr
    me = rs._session_or_401(p.address, p.session); now = rs.time.time()
    st0 = rs._json_load(rs.CREWS_PATH, {}); c0 = _cr.crew_of(st0, me)
    if not c0:
        raise rs.HTTPException(404, 'Join a family first.')
    pre = {}
    if p.act == 'accept':   # 🔔 the bell needs live prices for both cards — fetched before the lock
        f0 = (((st0.get('world') or {}).get('ffuse') or {}).get(p.fight)) or {}
        mine_ = next((x for x in rs._ffuse_cards(st0, c0) if x['key'] == p.card), None)
        if f0 and mine_:
            pre['card'] = mine_
            pre['px'] = await rs._ffuse_prices([f0['a']['card'], mine_])
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {}); _cr._norm(st); me = rs._seat_of(st, me); c = _cr.crew_of(st, me)
        if not c:
            raise rs.HTTPException(404, 'Join a family first.')
        w = st.setdefault('world', rs._fworld.blank()); store = w.setdefault('ffuse', {})
        staff_ = rs._is_staff(me); boost_, rk_ = rs._city_ctx(c, me, now)
        boss = staff_ or me == c.get('owner') or rk_.get(me) == 'underboss'
        city = rs._fcity.city_of(c, now); min_mp = rs._familia_rules()['fuseMinMp']
        def me_(o):
            r_ = int(((o.get('world') or {}).get('fuseElo')) or rs._ffuse.ELO0)
            b_ = o.get('badge') or {}
            lum_ = lambda h_: sum(int(str(h_)[i_:i_ + 2], 16) * w_ for i_, w_ in ((1, .299), (3, .587), (5, .114))) if isinstance(h_, str) and len(h_) == 7 else -1
            col_ = max((b_.get(k_) for k_ in ('c1', 'c2', 'c3')), key=lum_, default=None) if b_ else None   # the family's brightest colour (a black c1 vanishes on the board)
            return {'id': o['id'], 'tag': o.get('tag'), 'name': o.get('name'), 'color': col_ if lum_(col_) > 60 else None, 'rating': r_, 'bracket': rs._ffuse.bracket(r_)[1]}
        try:
            if p.act == 'challenge':
                rs._ffuse.may_run(p.stake, boss)   # 🎖 any member calls a PAPER fight; the bank (MP) stays the Don's / Underboss's
                o = (st.get('crews') or {}).get(p.vs)
                if not o:
                    raise ValueError('No such family.')
                card = next((x for x in rs._ffuse_cards(st, c) if x['key'] == p.card), None)
                if not card:
                    raise ValueError('Pick one of your family\'s Fuse cards (build one in the Fuse tab).')
                f, hold = rs._ffuse.challenge(store, f"ff{int(now * 1000) % 10**10}", me_(c), me_(o), card, p.stake, p.mp, p.mins, now, city['bank'], min_mp)
                f.update(ranked=rs._ffuse.ranked(f['a']['rating'], f['b']['rating']), by=me, byName=rs._display_name(me))
                city['bank'] -= hold
                for m_ in o.get('members') or []:
                    a_ = m_.get('address') if isinstance(m_, dict) else m_
                    try:
                        rs.notify(a_, 'familia', f"⚔ [{c.get('tag')}] called your family out to a Family Fuse ({p.stake.upper()}{f' · {hold:,} MP' if hold else ''}) — answer in Fee City", push=False)
                    except Exception:
                        pass
                res_ = rs._ffuse.view(f, now)
            elif p.act == 'accept':
                f = store.get(p.fight)
                if not f or f['b']['id'] != c['id']:
                    raise ValueError('No such challenge for your family.')
                if not pre.get('card'):
                    raise ValueError('Pick one of your family\'s Fuse cards.')
                rs._ffuse.may_run(f['stake'], boss)
                hold = rs._ffuse.accept(f, pre['card'], now, city['bank'], min_mp)
                prices, liqs = pre['px']
                books = {s_: rs._ffuse_book(f, s_, prices, liqs, now) for s_ in ('a', 'b')}
                if not all(books.values()):
                    f.update(status='open', bell_at=None, ends=None); f['b']['card'] = None
                    raise ValueError('Live prices for one of the cards are not answering — try again in a minute.')
                city['bank'] -= hold
                f['books'] = books; f['bell'] = {s_: rs._pgb.seat_prices(books[s_], prices) for s_ in ('a', 'b')}
                res_ = rs._ffuse.view(f, now)
            elif p.act in ('decline', 'cancel'):
                f = store.get(p.fight)
                if not f or f['status'] != 'open' or (p.act == 'decline' and f['b']['id'] != c['id']) or (p.act == 'cancel' and f['a']['id'] != c['id']):
                    raise ValueError('No such open challenge.')
                if not boss and not (p.act == 'cancel' and f.get('by') == me) and f['stake'] == 'mp':
                    raise ValueError('Only the Don, the Underboss or whoever called it can cancel it.')
                f.update(status='expired', endAt=now); rs._ffuse_pay(st, f, now); res_ = rs._ffuse.view(f, now)
            elif p.act == 'bid':
                f = store.get(p.fight)
                if not f:
                    raise ValueError('No such fight.')
                pm = c.setdefault('world', {}).setdefault('pts', {})
                take = rs._ffuse.bid(f, me, p.side, p.amount, int(pm.get(me) or 0), now, c['id'])
                pm[me] = int(pm.get(me) or 0) - take
                res_ = rs._ffuse.view(f, now)
            else:
                raise ValueError('Unknown Family Fuse action.')
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._json_save(rs.CREWS_PATH, st)
    return {'result': res_, **rs._ffuse_view(st, c, now)}


@router.get('/api/reputation/crews/badge/catalog')
async def crew_badge_catalog(address: str, session: str):
    """🌹 The badge builder for MY family: every part with locked / unlocked from the family's TRACKED numbers + what the restyle costs."""
    rs = _rs()
    import crews as _cr
    me = rs._session_or_401(address, session); st = rs._json_load(rs.CREWS_PATH, {}); me = rs._seat_of(st, me); c = _cr.crew_of(st, me)
    if not c:
        raise rs.HTTPException(404, 'You are not in a family.')
    met = _cr.family_metrics(c, st.get('awards'), rs._is_staff(c.get('owner')))
    return {'metrics': met, 'metricWords': _cr.METRICS, 'parts': _cr.catalog(met, rs._crew_cfg()), 'colors': list(_cr.COLORS), 'mottoMax': _cr.MOTTO_MAX,
            'adjust': {k: {'min': lo, 'max': hi, 'default': d} for k, (lo, hi, d) in _cr.ADJUST.items()},
            'owner': c['owner'] == me, 'built': bool(c.get('badge')), 'restyleUsd': rs._crew_badge_usd(), 'free': rs._is_staff(me), 'badge': _cr.badge_view(c, st.get('awards'), rs._crew_cfg(), rs._is_staff(c.get('owner')))}


@router.post('/api/reputation/admin/fuse-wallet/recover-sell')
async def fuse_wallet_recover_sell(request: Request):
    """Owner rescue: sell an old keeper token still physically in the Fuse wallet but no longer booked on a card.
    Only excess atoms with matching keeper history are adopted; unrelated wallet tokens are refused.
    Confirmed proceeds stay inside the original card as active cash/SOL."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    return await rs._fw_recover_sell(me, body.get('tpl'), str(body.get('mint') or '').strip())


@router.post('/api/reputation/admin/fuse-wallet/coin-sell')
async def fuse_wallet_coin_sell(request: Request):
    """↩ One coin chip on the Fuse wallet → sell it (owner, 2026-10-18: "should be able to sell / burn"): the card that last traded this coin
    is found from the ledger, then the same recover-sell path runs (the keeper sells it back to SOL into that card's cash)."""
    rs = _rs()
    me = rs._require_owner(request)
    mint = str((await request.json() or {}).get('mint') or '').strip()
    tid = next((r.get('card') for r in reversed(rs._fw_full_ledger()) if r.get('mint') == mint and r.get('pair') and r.get('card') in rs._prime.TEMPLATES), None)
    if not tid:
        raise rs.HTTPException(400, 'No card ever traded this coin — sell it from your own wallet (Trade › 🧹 Dust).')
    return await rs._fw_recover_sell(me, tid, mint)


@router.post('/api/reputation/admin/fuse-wallet/recover-sell-all')
async def fuse_wallet_recover_sell_all(request: Request):
    """Queue every confirmed dead/off-card keeper holding for sale into its card cash.
    Failed buys have no confirmed atoms and are deliberately ignored. Nothing is removed or credited until its sell confirms."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    tid = body.get('tpl')
    if tid not in rs._prime.TEMPLATES:
        raise rs.HTTPException(400, 'Pick a funded real tier card.')
    cfg = rs._fw_cfg()
    if not cfg.get('address') or not cfg.get('armed') or cfg.get('paused'):
        raise rs.HTTPException(400, 'Fuse wallet must be armed and running.')
    cards = rs._prime_cards()
    card = cards.get(tid)
    if not card or not card.get('real'):
        raise rs.HTTPException(400, 'That tier is not a real card.')
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        # 👻 the wallet is read INSIDE the lock: read before it, a sale the keeper confirmed while we waited still showed as held
        # and was booked back as a leftover (2026-10-09, $UP: $0.48 of phantom value + a halt)
        bal = await rs._fw_balances(cfg['address'])
        d = rs._fw_load(); book = d['books'].get(tid)
        if not book:
            raise rs.HTTPException(400, 'That tier is not funded.')
        if book.get('pending'):
            raise rs.HTTPException(409, 'Wait for the current transaction to settle first.')
        book, marked = rs._fw.mark_off_card_cash(book, card)
        just_sold = {r.get('mint') for r in d['ledger'][-200:] if r.get('side') == 'sell' and r.get('status') == 'filled' and rs.time.time() - rs._fuse._f(r.get('at')) < 120}
        booked = {}
        for bb in d['books'].values():
            for mint, leg in (bb.get('legs') or {}).items():
                booked[mint] = booked.get(mint, 0) + int(rs._fuse._f(leg.get('atoms')))
        adopted = []
        for mint, held_raw in (bal.get('tokens') or {}).items():
            excess = int(rs._fuse._f(held_raw)) - int(booked.get(mint, 0))
            if excess <= 0 or mint in just_sold:   # a coin sold in the last 2 min may still show in a lagging balance read
                continue
            hist = [r for r in d['ledger'] if r.get('card') == tid and r.get('mint') == mint and r.get('pair')]
            if not hist:
                continue
            last = hist[-1]
            if last.get('side') == 'writeoff':   # 🩸 a written-off drained / dead coin is never re-booked (it jammed every buy behind a refused sell)
                continue
            st = {'card': tid, 'mint': mint, 'atoms': excess,
                  'decimals': int((bal.get('decimals') or {}).get(mint) or last.get('decimals') or 0),
                  'pair': last.get('pair'), 'symbol': last.get('symbol') or mint[:6]}
            book = rs._fw.adopt(book, st)
            book['legs'][mint] = {**book['legs'][mint], 'manualCash': True, 'recovered': True}
            adopted.append(mint)
        queued = list(dict.fromkeys(marked + adopted))
        if not queued:
            raise rs.HTTPException(400, 'No confirmed dead/off-card holdings need selling.')
        d['books'][tid] = book
        rs._fw_record(d, {'card': tid, 'side': 'repair-sell-all', 'mints': queued, 'n': len(queued), 'at': rs.time.time(), 'status': 'done',
                       'why': 'owner queued every confirmed dead/off-card holding -> proceeds stay in card cash'})
        rs._fw_save(d)
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-wallet-recover-sell-all', f'{tid} {len(queued)} confirmed holdings'); rs._admin_save(ad)
    rs._fw_kick_now()
    return {'ok': True, 'tpl': tid, 'queued': len(queued), 'mints': queued, 'status': 'confirmed holdings queued/running'}


@router.post('/api/reputation/admin/fuse-wallet/cfg')
async def fuse_wallet_cfg(request: Request):
    """Owner only: pick the Fuse Circle wallet and set the hard limits. Arming needs signing enabled + a picked wallet."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        d = rs._fw_load()
        cfg = rs._fw.clean_cfg({**(d.get('cfg') or {}), **{k: v for k, v in body.items() if k in rs._fw.DEFAULT_CFG}})
        if cfg['armed'] and (not cfg['address'] or not rs._fw_signer_ready()):
            raise rs.HTTPException(400, 'Pick the Fuse wallet first (and the Circle service must be running) before arming real money.')
        d['cfg'] = cfg; rs._fw_save(d)
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-wallet-cfg', rs.json.dumps({k: cfg[k] for k in cfg if k != 'walletId'})[:160]); rs._admin_save(ad)
    return {'cfg': cfg}


@router.post('/api/reputation/admin/rpc')
async def admin_rpc_set(request: Request):
    """Owner only: put a new keyed RPC URL on lane 1 or 2. It is TESTED first (answers + holder lookup), saved to backend/.env as
    the one active line of its key, and used by the keeper at once — no restart. The URL is never returned, logged or audited."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    slot = int(rs._fuse._f(body.get('slot'))) if int(rs._fuse._f(body.get('slot'))) in rs._chain.LANE_KEYS else 1
    try:
        url = rs._chain.clean_rpc_url(body.get('url'))
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    async with rs.httpx.AsyncClient(timeout=10) as http:
        res = await rs._chain.probe(http, url)
    if not res.get('ok'):
        raise rs.HTTPException(400, f"Not saved — {res.get('err')}.")
    env = rs.Path(__file__).parent / '.env'
    if not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        env.write_text(rs._chain.env_with_key(env.read_text() if env.exists() else '', rs._chain.LANE_KEYS[slot], url))
    rs._chain.set_lane(slot, url)
    ad = rs._admin_load(); rs._audit(ad, me, 'rpc-lane', f"lane {slot} → {rs._chain.provider_of(url)}"); rs._admin_save(ad)
    return {'ok': True, 'slot': slot, 'provider': rs._chain.provider_of(url), 'holders': bool(res.get('holders')), 'ms': res.get('ms'), 'lanes': rs._rpc_quota_state()}


@router.post('/api/reputation/admin/alliance-days')
async def admin_alliance_days(request: Request):
    """🤝 Owner only: how many days an alliance waits before it can found a Union."""
    rs = _rs()
    me = rs._require_owner(request); b = await request.json()
    try:
        days = int(b.get('days'))
    except (TypeError, ValueError):
        raise rs.HTTPException(400, 'Give a number of days.')
    if not 0 <= days <= 3650:
        raise rs.HTTPException(400, '0 to 3,650 days.')
    async with rs._alliance_lock:
        st = rs._json_load(rs.ALLIANCES_PATH, {}) or {}; st['days'] = days; rs._json_save(rs.ALLIANCES_PATH, st)
    ad = rs._admin_load(); rs._audit(ad, me, 'alliance-days', str(days)); rs._admin_save(ad)
    return rs._alliance_view()


@router.post('/api/reputation/admin/collective-look')
async def admin_collective_look(request: Request):
    """🎨 Owner only: the Collective's colors and glow, for everyone who opens it."""
    rs = _rs()
    me = rs._require_owner(request); b = await request.json()
    if b.get('theme') not in rs.COLLECTIVE_THEMES:
        raise rs.HTTPException(400, 'Pick one of the themes.')
    look = {'theme': b['theme'], 'glow': max(0, min(100, int(b.get('glow') if isinstance(b.get('glow'), (int, float)) else 70)))}
    rs._json_save(rs.DATA_DIR / 'collective_look.json', look)
    ad = rs._admin_load(); rs._audit(ad, me, 'collective-look', look['theme']); rs._admin_save(ad)
    return look


@router.post('/api/reputation/admin/provider-key')
async def admin_provider_key(request: Request):
    """🔑 Owner only: save one provider key to backend/.env and this process. The value is never returned, logged or audited: only its name."""
    rs = _rs()
    me = rs._require_owner(request)
    import provider_ready as _pr
    body = await request.json()
    try:
        name, value = _pr.clean_key(body.get('name'), body.get('value'))
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    env = rs.Path(__file__).parent / '.env'
    if not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        env.write_text(rs._chain.env_with_key(env.read_text() if env.exists() else '', name, value))
    rs.os.environ[name] = value
    ad = rs._admin_load(); rs._audit(ad, me, 'provider-key', name); rs._admin_save(ad)
    return _pr.status(rs.os.environ)


@router.post('/api/reputation/admin/ai-key')
async def admin_ai_key_set(request: Request):
    """🔑 Owner only: save an AI API key (OpenAI · Anthropic · Gemini · OpenRouter · Groq · xAI · any OpenAI-compatible https base).
    It is TESTED first (one read-only list-models request — no tokens spent), saved to backend/.env as the one active line of its
    variable and set in this process. `{provider, clear: true}` removes it. The key is never returned, logged, audited or echoed in
    an error. Storing a key does not make any agent call a model (ai_keys.py)."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    env = rs.Path(__file__).parent / '.env'
    prov = str(body.get('provider') or '')
    if body.get('clear'):
        if prov not in rs._aik.PROVIDERS:
            raise rs.HTTPException(400, 'Pick a provider.')
        var = rs._aik.PROVIDERS[prov][1]
        if not rs.os.environ.get('PYTEST_CURRENT_TEST') and env.exists():
            txt = rs._aik.env_without(env.read_text(), var)
            if rs.os.environ.get(rs._aik.ACTIVE_VAR) == prov:
                txt = rs._aik.env_without(txt, rs._aik.ACTIVE_VAR)
            env.write_text(txt)
        rs.os.environ.pop(var, None)
        if rs.os.environ.get(rs._aik.ACTIVE_VAR) == prov:
            rs.os.environ.pop(rs._aik.ACTIVE_VAR, None)
        ad = rs._admin_load(); rs._audit(ad, me, 'ai-key', f'{prov} cleared'); rs._admin_save(ad)
        return {'ok': True, **rs._aik.status(rs.os.environ)}
    try:
        c = rs._aik.clean(prov, body.get('key'), body.get('base'), body.get('model'))
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    async with rs.httpx.AsyncClient(timeout=10) as http:
        res = await rs._aik.probe(http, c)
    if not res.get('ok'):
        raise rs.HTTPException(400, f"Not saved — {res.get('err')}.")
    lines = rs._aik.env_lines(c)
    if not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        txt = env.read_text() if env.exists() else ''
        for var, val in lines:
            txt = rs._chain.env_with_key(txt, var, val)
        env.write_text(txt)
    for var, val in lines:
        rs.os.environ[var] = val
    ad = rs._admin_load(); rs._audit(ad, me, 'ai-key', f"{c['provider']} saved"); rs._admin_save(ad)   # the provider only — never the key
    return {'ok': True, 'ms': res.get('ms'), 'models': res.get('models') or [], **rs._aik.status(rs.os.environ)}


@router.post('/api/reputation/admin/ai/seat')
async def admin_ai_seat_post(request: Request):
    """👍👎 / 💬 Owner on the duo's trade room: vote on a call ({vote: {key, v: 1 | -1 | 0}}) or chime in ({comment: text}) — the holder reads it
    next minute. A comment that says buy / hold / sell is graded by the market like theirs."""
    rs = _rs()
    admin = rs._require_owner(request)
    body = await request.json()
    now = rs.time.time()
    if 'guards' in body:   # 🔁 strict turns (off) · or the streak brake + proof bench may skip a losing model's turn (on)
        rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'guards': bool(body.get('guards'))}, rs.time.time())
        rs._duo_push()
        return {'ok': True, 'guards': bool(body.get('guards')), **rs._duo_view()}
    if body.get('vote'):
        vt_ = body['vote'] or {}
        st_, ok_ = rs._dv.vote(rs._dv_mem.get() or {}, str(vt_.get('key') or ''), 'owner', int(rs._fuse._f(vt_.get('v'))))
        if not ok_:
            raise rs.HTTPException(400, 'That call can\'t be voted on (too old, no coin, or it is your own).')
        rs._dv_mem.put(st_, now)
    txt_ = rs._re.sub(r'\s+', ' ', str(body.get('comment') or '')).strip()[:800]
    if txt_:
        st_ = rs._g4_state()
        legs_ = [l for c_ in (((rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}).get('cards') or {}).values() if (c_ or {}).get('real') for l in c_.get('legs') or [] if l.get('aiSeat') and not l.get('placeholder')]
        m_ = str(body.get('mint') or '') or (legs_[0].get('mint') if legs_ else None) or None   # 💬 a coin room's chime-in is about THAT coin
        lc_ = next((l_ for l_ in rs._duo_card_legs() if l_.get('mint') == m_), None) if body.get('mint') else None
        od_ = rs._seat.owner_order(txt_)   # 🫡 "sell it / get out / should've been sold" = an ORDER on the seat's coin, not a suggestion
        act_ = 'SELL' if od_ else 'HOLD' if rs._re.search(r"\b(hold|moon|send|buy|ride)\b|\b(?:don'?t|do not|never)\s+sell\b", txt_, rs._re.I) else 'NOTE'
        row_ = {'at': round(now), 'mode': 'real', 'model': 'YOU', 'by': 'owner', 'talk': True, 'action': 'TALK', 'view': act_ if act_ != 'NOTE' else None, 'why': txt_, 'mint': m_,
                'symbol': (lc_ or {}).get('symbol') or (legs_[0].get('symbol') if legs_ else None), **({'coinTalk': True} if lc_ and not (legs_ and legs_[0].get('mint') == m_) else {})}
        sl_ = next((l_ for l_ in legs_ if l_.get('mint') == m_), None) if (od_ and m_) else None
        if sl_:   # 🫡 owner, 2026-10-23: "I told him to sell … he won't do what I want" — the seat's coin is sold (or trimmed) on the next tier tick, no model vote
            rs._g4['want'] = {'action': od_['action'], **({'trim': od_['pct']} if od_['action'] == 'TRIM' else {}), 'pair': sl_.get('pairAddress'), 'mint': m_, 'symbol': sl_.get('symbol'),
                           'by': 'owner', 'model': 'YOU', 'why': f"your order in the trade room — “{txt_[:80]}”", 'thinkAt': now, 'at': rs.time.time()}
            row_['why'] = f"{txt_} · 🫡 " + ('selling it now' if od_['action'] == 'SELL' else f"trimming {od_['pct']}% now") + ' — your order, the seat acts on the next tick'
        ln_ = rs._seat.owner_lines(txt_)
        if ln_ and m_:   # ✋ "tp 80 · sl 20 · trail 35" in the chat = YOUR line on that coin, set now (the same path as a drag on the chart)
            async with rs._admin_lock:
                d_ = rs._json_load(rs.FUSE_HQ_PATH, {}); cs_ = (d_.get('prime') or {}).get('cards') or {}
                tp_ = next((k_ for k_, c_ in cs_.items() if (c_ or {}).get('real')), None)
                lg_ = next((l_ for l_ in (cs_.get(tp_) or {}).get('legs') or [] if l_.get('mint') == m_ and not l_.get('placeholder')), None) if tp_ else None
                if lg_:
                    try:
                        cs_[tp_] = rs._prime.set_leg(cs_[tp_], lg_['pairAddress'], tp=ln_.get('tp'), sl=ln_.get('sl'), trail=ln_.get('trail'), now=now)
                        rs._json_save(rs.FUSE_HQ_PATH, d_)
                        row_['why'] = f"{txt_} · ✅ set " + ' · '.join(f"{ {'tp': 'TP +', 'sl': 'SL −', 'trail': 'trail ↩'}[k_]}{v_:g}%" for k_, v_ in ln_.items())
                        row_['lineView'] = rs._seat.lines_view(ln_, lg_)   # 📏 your line move is graded too
                    except ValueError as e_:
                        row_['why'] = f"{txt_} · ⚠ not set: {e_}"
            row_['view'] = row_.pop('lineView', None) or 'LINES'
        rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'log': rs._seat.note(st_['log'], row_)}, now)
        if m_ and ((act_ != 'NOTE' and not ln_) or (ln_ and row_['view'] in ('HOLD', 'SELL'))):
            pm_ = await rs._live_px([m_])
            rs._dv_note(row_, rs._fuse._f(pm_.get(m_)), now)
    _audit_ad = rs._admin_load(); rs._audit(_audit_ad, admin, 'duo-room', rs.json.dumps({k_: body.get(k_) for k_ in ('vote',)} | ({'comment': txt_[:60]} if txt_ else {}))[:160]); rs._admin_save(_audit_ad)
    rs._duo_push()
    return rs._duo_view()


@router.post('/api/reputation/admin/ai/providers')
async def admin_ai_providers_set(request: Request):
    """🧠 Owner only: the provider ORDER and ON / OFF (`{order: [...], enabled: {key: bool}}`). Keys are never sent here."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    cfg = rs._air.clean_cfg(body if isinstance(body, dict) else {}, rs._ai_cfg())
    rs._json_save(rs.AI_CFG_PATH, cfg)
    ad = rs._admin_load(); rs._audit(ad, me, 'ai-providers', f"order {','.join(cfg['order']) or 'default'}"); rs._admin_save(ad)
    if rs._office.get('payload') is not None:
        rs._office['payload']['ai'] = rs._ai_view(light=True)
    return rs._ai_view()


@router.post('/api/reputation/admin/ai/ask')
async def admin_ai_ask(request: Request):
    """🧠 Owner only: ASK THE MODEL about one coin now (`{input: CA | link | mint, role: sherlock | devil | owner}`). The case is the
    kernel's own row for that coin (nothing typed by hand reaches the model except the address). The answer is DISPLAYED — in the
    decision log and beside the coin; it never places, sizes, blocks or sells anything; a stance moves the ranking (±10% at most) only once it is proven on its own judged record."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json()
    ref = rs._owr.parse(str((body or {}).get('input') or ''))
    if not ref:   # 🧭 not a coin: a GENERAL question — a normal answer in normal language, with a few desk facts as context (never the trench schema)
        q_ = str((body or {}).get('question') or (body or {}).get('input') or '').strip()
        if len(q_) < 3:
            raise rs.HTTPException(400, 'Paste a coin (CA / pump.fun · dexscreener link) or type a question.')
        res = await rs._air.ROUTER.ask(rs._ai_http(), rs.os.environ, rs._ai_cfg(), q_[:2000], context=rs._ai_general_context(), role='owner')
        return {'ok': bool(res.get('text')), 'mode': 'general', 'answer': {k_: res.get(k_) for k_ in ('source', 'label', 'text', 'ms', 'why')}, 'ai': rs._ai_view(light=True)}
    role = str((body or {}).get('role') or 'owner').lower()
    if role not in ('sherlock', 'devil', 'owner'):
        raise rs.HTTPException(400, 'Pick sherlock, devil or owner.')
    mint = ref['address']
    p = rs._office.get('payload') or {}
    c = next((c_ for c_ in ((p.get('kernel') or {}).get('candidates') or []) if c_.get('mint') == mint or c_.get('pair') == mint), None)
    if not c:   # held coins and the owner's own list are cases too
        pos_ = next((x_ for x_ in (p.get('positions') or []) if x_.get('mint') == mint), None)
        own_ = next((x_ for x_ in (p.get('ownerReview') or []) if x_.get('mint') == mint), None)
        if pos_:
            c = {'mint': mint, 'symbol': pos_.get('symbol'), 'status': 'HELD', 'state': pos_.get('decision') or pos_.get('state'), 'why': pos_.get('evidence'), 'cap': pos_.get('mc'),
                 'liq': pos_.get('liq'), 'structure': pos_.get('structure'), 'phase': pos_.get('phase'), 'result': pos_.get('pct'), 'heldMin': pos_.get('heldMin'), 'rule': pos_.get('rule')}
        elif own_:
            c = {'mint': mint, 'symbol': own_.get('symbol'), 'state': own_.get('state'), 'why': own_.get('why'), 'cap': own_.get('mc'), 'trigger': (own_.get('trigger') or {}).get('state'),
                 'devil': (own_.get('devil') or {}).get('severity'), 'pending': own_.get('pending')}
    if not c:
        raise rs.HTTPException(400, 'That coin is not on the desk yet — 🔎 Review it first, the agents read it on their next pass and the model can then be asked.')
    case = rs._ai_case(c)
    res = await rs._air.ROUTER.reason(rs._ai_http(), rs.os.environ, rs._ai_cfg(), case, role, 'force', mode='case')
    if res.get('advice'):
        rs._ai['notes'].setdefault(c['mint'], {})[role] = {k_: res.get(k_) for k_ in ('source', 'label', 'advice', 'ms', 'at', 'tried', 'why', 'cached')} | {'symbol': c.get('symbol')}
    rs._ai_log(role, case, res, asked=True)
    rs._ai_learn_note(role, c, res, rs.time.time())
    if rs._office.get('payload') is not None:
        rs._office['payload']['ai'] = rs._ai_view(light=True)
        try:
            rs._tke.HUB.publish('ai_update', 'ai', rs._office['payload']['ai'], rs.time.time())
        except Exception:
            pass
    return {'ok': bool(res.get('advice')), 'mint': c['mint'], 'symbol': c.get('symbol'), 'role': role, 'answer': {k_: res.get(k_) for k_ in ('source', 'label', 'advice', 'ms', 'why')},
            'ai': rs._ai_view(light=True)}


@router.post('/api/reputation/admin/ai/test')
async def admin_ai_test(request: Request):
    """🧠 Owner only: one tiny request to ONE provider (≈ 10 tokens) → online / offline / rate limited + its latency. Never a key."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json()
    key = str((body or {}).get('provider') or '')
    if key not in rs._air.PROVIDERS:
        raise rs.HTTPException(400, 'Pick a provider.')
    res = await rs._air.ROUTER.test(rs._ai_http(), rs.os.environ, rs._ai_cfg(), key)
    return {**res, **rs._ai_view()}


@router.post('/api/reputation/admin/ai/load')
async def admin_ai_load(request: Request):
    """⚡ Owner only: load G4 / OSSY's configured model in its LM Studio (the desktop dropped G4's model → "not connected", 2026-10-22).
    One tap = the owner's approval; nothing loads a model on its own."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json()
    key = str((body or {}).get('provider') or '')
    res = await rs._air.ROUTER.load_model(rs._ai_http(), rs.os.environ, rs._ai_cfg(), key)
    return {**res, **rs._ai_view()}


@router.post('/api/reputation/admin/agent-slots')
async def admin_agent_slots_set(request: Request):
    """🎟 Owner: open more agent slots for new buyers (never past 1,000, never below what is taken)."""
    rs = _rs()
    me_ = rs._require_owner(request)
    body = await request.json()
    try:
        r_ = await rs._ai_http().post('http://127.0.0.1:5088/api/cats/internal/supply', headers={'x-feeless-internal': rs._internal_key()}, json={'open': (body or {}).get('open'), 'by': str(me_)[:44]}, timeout=8)
    except Exception:
        raise rs.HTTPException(503, 'Fee service did not answer.')
    if r_.status_code != 200:
        raise rs.HTTPException(r_.status_code, (r_.json() or {}).get('detail') or 'Fee service rejected the change.')
    return r_.json()


@router.post('/api/reputation/admin/ai/prompts')
async def admin_ai_prompts_set(request: Request):
    """🎭 Owner: apply a set to a model ({key, set, text?} — text = the owner's edit of that set) or revert it ({key, revert: true})."""
    rs = _rs()
    me_ = rs._require_owner(request)
    body = await request.json()
    body = body if isinstance(body, dict) else {}
    k_ = body.get('key')
    if k_ == 'fee':   # 🐱 her versions live with her (feecat_service) — the owner approves each, no auto switch
        await rs._studio_fee({**{x_: body[x_] for x_ in ('set', 'text', 'revert', 'general') if x_ in body}, 'by': str(me_)[:44]})
        return {**(await rs._studio_view()), 'applied': None if body.get('revert') else k_}
    if k_ not in rs._pstu.KEYS:
        raise rs.HTTPException(400, 'unknown model')
    raw_ = dict(rs._json_load(rs.PROMPT_STUDIO_PATH, {}) or {})
    if 'auto' in body:   # 🤖 the auto-tune switch for this model
        raw_['auto'] = {**(raw_.get('auto') or {}), k_: bool(body.get('auto'))}
        rs._json_save(rs.PROMPT_STUDIO_PATH, raw_)
        rs._studio_auto_at['t'] = 0.0   # judged on the next AI round, not in 5 min
        return {**(await rs._studio_view()), 'applied': None}
    if body.get('revert'):
        raw_.pop(k_, None)
        raw_['history'] = rs._pstu.hist_add(raw_.get('history'), k_, None, rs.time.time(), me_)
    else:
        set_ = body.get('set')
        if set_ not in rs._pstu.SETS:
            raise rs.HTTPException(400, 'unknown prompt set')
        gen_ = next((x_ for m_ in (await rs._studio_view())['models'] if m_['key'] == k_ for x_ in m_['sets'] if x_['set'] == set_), None) or {}
        txt_ = ' '.join(str(body.get('text') or '').split()) or gen_.get('text') or ''
        if not txt_:
            raise rs.HTTPException(400, 'empty prompt')
        raw_[k_] = {'set': set_, 'text': txt_, 'at': rs.time.time(), 'by': str(me_)[:44], 'edited': txt_ != gen_.get('text')}
        raw_['history'] = rs._pstu.hist_add(raw_.get('history'), k_, set_, rs.time.time(), me_)
    rs._json_save(rs.PROMPT_STUDIO_PATH, raw_)
    return {**(await rs._studio_view()), 'applied': None if body.get('revert') else k_}


@router.post('/api/reputation/admin/ai/rig/preset')
async def admin_ai_rig_preset(request: Request):
    """🔖 Owner: a model's presets — `save` (snapshot its rig now under a name), `apply` (that snapshot → the rig, listed values only; G4 / OSSY
    reload only on the ⚡ tap), `drop`."""
    rs = _rs()
    admin = rs._require_owner(request)
    import ai_rig as _rg
    body = await request.json(); body = body if isinstance(body, dict) else {}
    key_, name_, act_ = body.get('key'), body.get('name'), body.get('act')
    store_ = rs._json_load(rs.AI_PRESETS_PATH, {}); rig_ = _rg.clean({}, rs._json_load(rs.AI_RIG_PATH, {}))
    try:
        if act_ == 'save':
            _rg.preset_save(store_, key_, name_, rig_.get(key_) or {}, rs.time.time())
        elif act_ == 'drop':
            _rg.preset_drop(store_, key_, name_)
        elif act_ == 'apply':
            row_ = _rg.preset_get(store_, key_, name_)
            if row_ is None:
                raise ValueError('No such preset.')
            rs._json_save(rs.AI_RIG_PATH, _rg.clean({key_: row_}, rig_)); rs._rig_apply()
        else:
            raise ValueError('save, apply or drop.')
    except ValueError as e_:
        raise rs.HTTPException(400, str(e_))
    rs._json_save(rs.AI_PRESETS_PATH, store_)
    ad_ = rs._admin_load(); rs._audit(ad_, admin, 'ai-preset', f'{act_} {key_} {str(name_)[:32]}'); rs._admin_save(ad_)
    return await rs.admin_ai_rig(request)


@router.post('/api/reputation/admin/ai/rig')
async def admin_ai_rig_set(request: Request):
    """🎛 Owner: save the rig (listed values only) — live at once for what FEELESS sends. G4 / OSSY are never reloaded."""
    rs = _rs()
    admin = rs._require_owner(request)
    import ai_rig as _rg
    body = await request.json()
    body = body if isinstance(body, dict) else {}
    new_ = _rg.clean(body, rs._json_load(rs.AI_RIG_PATH, {}))
    rs._json_save(rs.AI_RIG_PATH, new_)
    rs._rig_apply()
    ad_ = rs._admin_load(); rs._audit(ad_, admin, 'ai-rig', str({k_: new_[k_] for k_ in _rg.KEYS})[:300]); rs._admin_save(ad_)
    rl_ = body.get('reload')
    if rl_ in _rg.LM_KEYS:   # ⚡ the owner's tap = the approval: reload THAT model with its wanted load (never automatic)
        if rl_ in rs._lms_reloading:
            raise rs.HTTPException(429, f'{_rg.NAMES[rl_]} is already reloading.')
        rs._lms_reloading.add(rl_)
        try:
            res_ = await rs._lms_reload(rl_, new_[rl_]['load'])
        finally:
            rs._lms_reloading.discard(rl_)
        rs._lms_seen.pop(rl_, None)
        ad_ = rs._admin_load(); rs._audit(ad_, admin, 'lms-reload', f"{rl_} {_rg.load_value(new_[rl_]['load'])} → {'ok' if res_.get('ok') else res_.get('err')}"[:200]); rs._admin_save(ad_)
        out_ = await rs.admin_ai_rig(request)
        return {**out_, 'reload': res_}
    return await rs.admin_ai_rig(request)


@router.get('/api/reputation/admin/ai/calls')
async def admin_ai_calls(request: Request):
    """🧠 Owner: the models' calls LIVE — each one in flight with its % (elapsed ÷ that model's own average) + the last 30 prompts / answers."""
    rs = _rs()
    rs._require_owner(request)
    by_ = {}
    for _t, ms_, k_ in list(getattr(rs._air.ROUTER, 'recent', []) or []):
        by_.setdefault(k_, []).append(ms_)
    avg_ = {k_: sum(v_) / len(v_) for k_, v_ in by_.items() if v_}
    names_ = {k_: rs._air.NAME_DEFAULT.get(k_) for k_ in ('lan', 'local')} if isinstance(getattr(rs._air, 'NAME_DEFAULT', None), dict) else {}
    lim_ = {k_: rs._air.rig(k_, 'timeout', (rs._air.PROVIDERS.get(k_) or (0,) * 7)[6] or 90) for k_ in ('lan', 'local')}   # ⏱ the real deadline per model
    return {**rs._air.calls_view(rs.time.time(), avg_), 'names': names_, 'avgMs': {k_: round(v_) for k_, v_ in avg_.items()}, 'limits': lim_}


@router.get('/api/reputation/admin/ai/learned')
async def admin_ai_learned(request: Request):
    """🎓 Owner: what the desk has LEARNED, in one read — your standing words from the chat log, hold lessons + taught notes, live rules /
    repeat causes, the germ entry's own real record (agents) + your entries vs the germ, and the fixes waiting for your ✅. Read only."""
    rs = _rs()
    rs._require_owner(request)
    now = rs.time.time(); mem_ = rs._aim.prune(rs._aim_mem.get() or {}, now)
    pick_ = lambda d_, n_: [{'t': x.get('t'), 'at': x.get('at')} for x in reversed(mem_.get(d_) or [])][:n_]
    pos_ = (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or []
    try:
        yours_ = rs._co.germ_record(pos_)
    except Exception:
        yours_ = {}
    pend_ = [{k_: x.get(k_) for k_ in ('id', 'agent', 'kind', 'key', 'new', 'reason')} for x in (rs._chat_props().get('items') or []) if x.get('status') == 'pending'][:8]
    return {'owner': pick_('owner', 12), 'lessons': pick_('lessons', 12), 'rules': pick_('rules', 10), 'germAgents': rs._aic.germ_record(rs._real_trades()),
            'germYours': yours_, 'pending': pend_, 'size': rs._aim.size(mem_), 'at': round(now, 1)}


@router.post('/api/reputation/admin/ai/playground')
async def admin_ai_playground_make(request: Request):
    """🧩 Owner: a model proposes ONE code change for a real part of FEELESS (it is shown that file's real outline). Nothing is written to
    the repo: ✅ files it to the build queue, Claude Code applies it with tests. `from` = an earlier proposal to change."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json() or {}
    ask = rs._aic.clean(body.get('prompt'), 900)
    target = str(body.get('target') or 'agents')
    if len(ask) < 3:
        raise rs.HTTPException(400, 'Say what to change.')
    if target not in rs._play.TARGETS:
        raise rs.HTTPException(400, 'Pick a part of FEELESS.')
    if rs._chat['busy']:
        raise rs.HTTPException(429, 'The model is still answering.')
    d_ = rs._json_load(rs.AI_PLAY_PATH, {}) or {}
    prev = next((x for x in (d_.get('items') or []) if x.get('id') == body.get('from')), None)
    try:
        src_ = (rs.Path(__file__).resolve().parent.parent / rs._play.TARGETS[target][0]).read_text()
    except OSError:
        src_ = ''
    prov_ = str(body.get('provider') or 'auto')
    only_ = (prov_,) if prov_ in rs._air.PROVIDERS else (rs._duet.LEAD,) if prov_ == 'duet' else None
    rs._chat['busy'] = True
    raw_ = rs._air.RAW.set(True)
    q_ = rs._play.prompt(ask, target, rs._play.outline(src_, rs._play.TARGETS[target][0]), prev)
    tried_ = []
    try:
        prop, res = None, {}
        for o_ in ([only_] if only_ and prov_ != 'duet' else [only_, (rs._duet.SECOND,)]):   # 🧩 no code from the first model → the other one gets a try
            res = await rs._air.ROUTER.ask(rs._ai_http(), rs.os.environ, rs._ai_cfg(), q_, role='owner', system=rs._play.ASK, only=o_, tune={'temp': 0.3, 'maxTok': 4000}, only_system=True)
            prop = rs._play.parse(res.get('raw') or res.get('text'))
            tried_.append(f"{res.get('label') or res.get('source')}: {'code' if prop else (str(res.get('text') or res.get('why') or 'no answer')[:60])}")
            if prop:
                break
        if prop and not prop.get('preview'):   # 🖼 no mock-up in the answer -> one more call that only builds the live, clickable preview
            pq_ = f"THE CHANGE: {prop['title']} — {prop['why'][:400]}\nWHAT THE OWNER ASKED: {ask[:400]}\nTHE CODE:\n{prop['code'][:3500]}"
            pr_ = await rs._air.ROUTER.ask(rs._ai_http(), rs.os.environ, rs._ai_cfg(), pq_, role='owner', system=rs._play.PREVIEW_ASK, only=only_ if only_ and prov_ != 'duet' else None, tune={'temp': 0.4, 'maxTok': 3500}, only_system=True)
            pv_ = rs._play.html_of(pr_.get('raw') or pr_.get('text'))
            if pv_:
                prop['preview'] = pv_
    finally:
        rs._air.RAW.reset(raw_)
        rs._chat['busy'] = False
    if not prop:
        raise rs.HTTPException(502, "No model returned a code proposal — " + ' · '.join(tried_ or ['no provider answered']))
    prop = {**prop, **rs._play.preview_diff(src_, prop['code'], rs._play.TARGETS[target][0])}   # 🔍 before → after against the real file
    if rs._play.TARGETS[target][0].endswith('.py') and prop.get('examples'):   # ▶ the proposal WORKING: its own examples, run in a locked-down sandbox
        prop['run'] = await rs.asyncio.to_thread(rs._play.test_run, prop['code'], prop['examples'])
    d_['items'], it = rs._play.add(d_.get('items'), ask, prop, target, res.get('label'))
    rs._json_save(rs.AI_PLAY_PATH, d_)
    return {'item': it, 'items': d_['items'], 'ms': res.get('ms')}


@router.post('/api/reputation/admin/ai/playground/decide')
async def admin_ai_playground_decide(request: Request):
    """🧩 Owner: ✅ approve (→ the build queue, pointing back at the proposal's code) or ✕ drop a code proposal. Writes no code."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json() or {}
    now = rs.time.time()
    d_ = rs._json_load(rs.AI_PLAY_PATH, {}) or {}
    d_['items'], it = rs._play.decide(d_.get('items'), str(body.get('id') or ''), bool(body.get('approve')), now)
    if not it:
        raise rs.HTTPException(404, 'No open proposal with that id.')
    if it['status'] == 'approved':
        try:
            rs._chat['build'], b_ = rs._aic.build_add(rs._build_state(), it['title'], f"code lab {it['id']} → {it['file']}: {it['why']} (code in data/ai_playground.json)", 'code lab · approved', now)
            rs._json_save(rs.BUILD_QUEUE_PATH, rs._chat['build']); it['build'] = b_['id']
        except ValueError as e:
            it['build'] = str(e)
    rs._json_save(rs.AI_PLAY_PATH, d_)
    ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'code-lab', f"{it['status']} {it['id']} {it['file']}"[:200]); rs._admin_save(ad_)
    return {'item': it, 'items': d_['items']}


@router.post('/api/reputation/admin/ai/chat')
async def admin_ai_chat(request: Request):
    """💬 Owner only: talk to the current model. `mode` chat (normal language) · case (the structured coin read of `focus`) · improve (the model
    may PROPOSE agent changes — nothing is applied here). One chat inference at a time; the history is short and in memory."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json()
    text = rs._aic.clean((body or {}).get('text'), 2000)
    mode = str((body or {}).get('mode') or 'chat').lower()
    focus = str((body or {}).get('focus') or '')[:60] or None
    if mode not in rs._aic.MODES:
        raise rs.HTTPException(400, 'Pick chat, case, improve or build.')
    asked, mode = mode, rs._aic.route_mode(mode, text)   # a chat message that asks for a change becomes proposals the owner approves
    if len(text) < 2 and mode != 'case':
        raise rs.HTTPException(400, 'Type a message.')
    if asked in ('chat', 'improve') and not (body or {}).get('image'):   # 🎛 "ossy context 16k, temp 0.6" = a SETTINGS LINE: read straight from your words
        rig_items_ = rs._aic.rig_items(text)                              # → proposals at once (no model call); nothing applies before ✅
        if rig_items_:
            now = rs.time.time(); rs._brain_load()
            if any(x_['key'].endswith('.load') for x_ in rig_items_):
                await rs._lms_states(fresh=True)
            rs._chat['props'], new = rs._aic.propose(rs._chat_props(), rig_items_, rs._chat_olds(), now, '👤 your line')
            rs._json_save(rs.AI_PROPOSALS_PATH, rs._chat['props'])
            reply = ('🎛 ' + (f"{len(new)} model change{'s' if len(new) != 1 else ''} waiting for your ✅: " if new else 'Already waiting for your ✅: ')
                     + ' · '.join(p_['effect'].split(' — ')[0] for p_ in (new or rig_items_))
                     + ('. A load change reloads that model once you approve it.' if any(x_['key'].endswith('.load') for x_ in rig_items_) else '. Live the moment you approve.'))
            rs._chat['th'] = rs._aic.push_thread(rs._aic.push_thread(rs._chat['th'], asked, 'user', text), asked, 'assistant', reply, {'mode': asked, 'provider': '🎛 rig'})
            rs._chat_persist()
            ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'ai-proposals', f"{len(new)} rig change(s) from your line: " + ' · '.join(f"{p_['key']}={p_['new']}" for p_ in new)[:200]); rs._admin_save(ad_)
            return {'ok': True, 'mode': asked, 'routed': False, 'reply': reply, 'provider': '🎛 rig', 'model': None, 'ms': 0, 'history': rs._chat['th'].get(asked) or [], **rs._chat_extra(),
                    'new': [p_['id'] for p_ in new], 'refused': [], 'proposals': rs._aic.view(rs._chat_props()), 'rig': True}
    if rs._chat['busy']:
        raise rs.HTTPException(429, 'The model is still answering your last message.')
    rs._chat['busy'] = True
    now = rs.time.time()
    rs._brain_load()
    try:
        env, cfg = rs.os.environ, rs._ai_cfg()
        try:
            await rs._air.ROUTER.heartbeat(rs._ai_http(), env, cfg, now, every=0)   # 💓 a chat never waits on a stale OFFLINE: LM Studio is re-checked first (one cheap read)
        except Exception:
            pass
        if mode == 'case':   # 🔎 CASE REVIEW: the kernel's own case for the selected coin → the validated structured answer
            c = next((c_ for c_ in (((rs._office.get('payload') or {}).get('kernel') or {}).get('candidates') or []) if focus and focus in (c_.get('mint'), c_.get('pair'), c_.get('symbol'))), None)
            if not c:
                raise rs.HTTPException(400, 'Pick a coin that is on the desk (the one on the chart) for a case review.')
            res = await rs._air.ROUTER.reason(rs._ai_http(), env, cfg, rs._ai_case(c), 'owner', 'force', mode='case')
            ad = res.get('advice') or {}
            if ad:
                rs._ai_keep('owner', c, res, now)
            reply = (f"{ad.get('call') or ad.get('stance')} · {ad.get('summary')}" + (f" · risks: {'; '.join(ad.get('risk_flags') or [])}" if ad.get('risk_flags') else '')) if ad else None
            rs._chat['th'] = rs._aic.push_thread(rs._aic.push_thread(rs._chat['th'], 'case', 'user', f"[case review] ${c.get('symbol')} {text}".strip()), 'case', 'assistant', reply or 'no provider answered', {'mode': 'case'})
            return {'ok': bool(ad), 'mode': 'case', 'reply': reply, 'advice': ad or None, 'symbol': c.get('symbol'), 'provider': res.get('label'), 'model': rs._air.provider(env, res['source'], cfg)['model'] if res.get('source') in rs._air.PROVIDERS else None,
                    'ms': res.get('ms'), 'tokens': rs._air.ROUTER.lastUsage.get(res.get('source')), 'history': rs._chat['th'].get('case') or [], 'threads': rs._aic.threads_view(rs._chat['th']), 'proposals': rs._aic.view(rs._chat_props()), 'why': res.get('why')}
        ctx, data_ = rs._chat_context(focus, now), None
        if mode == 'chat' and rs._cev.wants(text):   # 📚 a question about what HAPPENED: the model reads FEELESS's own records for the window, not a guess
            try:
                pk_, st_ = await rs.asyncio.to_thread(rs._chat_evidence, text, now)
                ctx = {'evidence': pk_, 'rules': rs._cev.RULES, 'live': (ctx or {}).get('live'), 'germRecord': (ctx or {}).get('germRecord')}   # 🧠 what is live keeps riding along
                data_ = {'state': st_, 'window': (pk_.get('time_window') or {}).get('label'), 'exits': (pk_.get('summary') or {}).get('exits', 0), 'gaps': pk_.get('known_gaps') or []}
            except Exception as e_:
                print('chat evidence:', str(e_)[:120])
                data_ = {'state': 'NO HISTORY', 'window': None, 'exits': 0, 'gaps': ['the evidence reader failed — answered without records']}
        set_ = rs._chat.get('settings') or {}
        try:   # 👤 THE OWNER'S OWN RECORD rides on EVERY chat answer (owner, 2026-10-15: "they aren't learning from my moves, they think it's all the agents")
            ob_ = rs._owner_brief() if set_.get('memory', 'on') == 'on' else None
            if ob_:
                ctx = {**(ctx or {}), 'owner': ob_, 'ownerRule': rs._aic.OWNER_RULE}
        except Exception as e_:
            print('chat owner brief:', str(e_)[:80])
        try:   # 🗄 the filed memory that fits this question (owner notes first, then lessons / rules / coins / site) — never the whole store
            mm_ = rs._aim.recall(rs._aim.seed_site(rs._aim_mem.get() or {}, now), text, 8) if set_.get('memory', 'on') == 'on' else None
            if mm_:
                ctx = {**(ctx or {}), 'memory': mm_}
        except Exception as e_:
            print('chat memory:', str(e_)[:80])
        try:   # 🪙 a coin the owner NAMES ("ELON", "$BUBBLE"): its own trade record — seat, what the agents would have done, his moves, past exits
            cr_ = rs._chat_coin(text)
            if cr_:
                ctx = {**(ctx or {}), 'coin': cr_, 'coinRule': 'The owner named this coin: answer from `coin` FIRST, with its numbers — entry, now, peak, '
                       'every moment the agents would have sold and what the coin did after, his own moves on it. No web, no generic lessons.'}
        except Exception as e_:
            print('chat coin:', str(e_)[:80])
        prov_ = str((body or {}).get('provider') or 'auto')   # resolve model before optional web research
        web_ = None
        if mode == 'chat' and (body or {}).get('web', True) is not False and set_.get('search', 'deep') != 'off' and rs._aic.should_search(text, rs._chat_syms()) and (prov_ != 'win' or rs._aic.FORCE_WEB.search(text)):   # (records AND the web — owner: "always research before responding")   # 🌐 a quick search before EVERY real question (model memory may be out of date)
            try:
                import feeless_mcp as _mcp
                rows_ = await rs.asyncio.wait_for(rs.asyncio.to_thread(_mcp._search_rows, rs._aic.web_query(text), 5), timeout=8)
                web_ = [{'title': str(x_.get('title') or '')[:120], 'url': str(x_.get('url') or '')[:300], 'snippet': str(x_.get('snippet') or '')[:240]} for x_ in rows_ or [] if x_.get('url')][:5]
                if web_:
                    ctx = {**(ctx or {}), 'web': web_, 'webRule': rs._aic.WEB_RULE}
                    try:   # 📚 READ the 2 most solid results (owner: "back every answer — Google + 2 prominent sources"), in parallel, ≤ 8s — research setting 'deep'
                        if set_.get('search', 'deep') != 'deep':
                            raise StopIteration
                        import fee_voice as _fv_
                        pick_ = _fv_.pick_sources(web_, 2)
                        txt_ = await rs.asyncio.wait_for(rs.asyncio.gather(*[rs.asyncio.to_thread(_mcp.t_web_fetch, {'url': x_['url'], 'max_chars': 1800}) for x_ in pick_], return_exceptions=True), timeout=8)
                        src_ = [{'title': x_.get('title'), 'url': x_['url'], 'text': str(t_)[:1800]} for x_, t_ in zip(pick_, txt_) if isinstance(t_, str) and not t_.startswith('Could not read')]
                        if src_:
                            ctx['sources'] = src_
                    except StopIteration:
                        pass
                    except Exception as e2_:
                        print('chat sources:', str(e2_)[:80])
            except Exception as e_:
                print('chat web:', str(e_)[:100])
        only_ = (prov_,) if prov_ in rs._air.PROVIDERS else (rs._duet.LEAD,) if prov_ == 'duet' else None
        if prov_ == 'auto':   # 💬 your chat asks the STRONGER local model first (OSSY = gpt-oss-20b; G4 is a 2B model on the desktop today) — CHAT_FIRST overrides
            only_ = tuple(dict.fromkeys([str(env.get('CHAT_FIRST') or 'local')] + list(rs._air.order_of(env, cfg))))
        img_ = rs._chat_image((body or {}).get('image'))
        hist_ = rs._aic.as_messages(rs._chat['th'].get(mode))
        vl_ = rs._aic.VOICE_LINE.get(set_.get('voice', 'degen')) or ''
        res = await rs._air.ROUTER.ask(rs._ai_http(), env, cfg, text, context=ctx, role='owner', history=hist_, system=((rs._aic.system_for(mode) or '') + ('\n' + vl_ if vl_ else '')) or None,
                                    only=only_, images=[img_[1]] if img_ else None, tune=rs._aic.tune_of(rs._chat['settings']))
        if prov_ == 'duet' and not img_:   # 🤝 THE DUET IN CHAT: Gemma answers, Qwen reads Gemma's answer and agrees or pushes back — both shown
            lead_t = res.get('text')
            r2 = await rs._air.ROUTER.ask(rs._ai_http(), env, cfg, rs._duet.second_prompt(text, lead_t) if lead_t else text, context=ctx, role='owner', history=hist_,
                                       system=rs._aic.system_for(mode), only=(rs._duet.SECOND,), tune=rs._aic.tune_of(rs._chat['settings']))
            both_ = rs._duet.combine(lead_t, r2.get('text'), {k_: rs._air.model_name(env, k_) for k_ in (rs._duet.LEAD, rs._duet.SECOND)})
            res = {**res, 'text': both_, 'label': ' + '.join(x for x in (res.get('label') if lead_t else None, r2.get('label') if r2.get('text') else None) if x) or res.get('label'),
                   'ms': (res.get('ms') or 0) + (r2.get('ms') or 0), 'model': ' + '.join(x for x in (res.get('model'), r2.get('model')) if x)}
        reply, new, refused = res.get('text'), [], []
        if reply and mode in ('improve', 'build'):   # 🛠 the model's suggestions become PENDING records — nothing is applied until the owner approves each one
            reply, items, refused = rs._aic.parse_improve(reply, tuple(rs._co.CAUSES), only=('idea',) if mode == 'build' else None)
            if items:
                rs._chat['props'], new = rs._aic.propose(rs._chat_props(), items, rs._chat_olds(), now, res.get('label'))
                if rs._chat['settings'].get('allowSmall'):   # 🤝 the owner's allowance: lessons + build ideas apply at once (marked auto); everything else still waits for ✅
                    for p_ in [x for x in new if x['kind'] in rs._aic.SMALL_KINDS]:
                        try:
                            rs._chat['props'], d_, er_ = rs._aic.decide(rs._chat['props'], p_['id'], True, now)
                            if er_ or not d_:
                                continue
                            rs._chat['props'] = rs._aic.applied(rs._chat['props'], p_['id'], '🤝 auto (small thing allowed) · ' + await rs._ai_proposal_apply(d_, now))
                        except Exception as e_:
                            print('ai auto-small:', str(e_)[:80])
                rs._json_save(rs.AI_PROPOSALS_PATH, rs._chat['props'])
                ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'ai-proposals', f"{len(new)} proposed by {res.get('label')}: " + ' · '.join(f"{p_['kind']} {p_['key']}" for p_ in new)[:200]); rs._admin_save(ad_)
        if not reply and data_ and data_['state'] == 'NO HISTORY':
            reply = f"Insufficient evidence: FEELESS has no records for {data_.get('window') or 'that window'} — " + '; '.join(data_['gaps'][:3])
        try:   # 💬 what you STATE in chat (how you trade, what you want) becomes a standing owner note every later answer recalls
            mem_c = rs._aim_mem.get() or {}
            for n_ in rs._aim.chat_notes(text):
                mem_c = rs._aim.file(mem_c, 'owner', 'chat:' + rs.hashlib.sha1(n_.lower().encode()).hexdigest()[:10], '💬 owner said: ' + n_, now)
            rs._aim_mem.put(mem_c, now)
        except Exception as e_:
            print('chat memory note:', str(e_)[:80])
        rs._chat['th'] = rs._aic.push_thread(rs._aic.push_thread(rs._chat['th'], mode, 'user', text, {'img': img_[0]} if img_ else None), mode, 'assistant', reply or 'no provider answered', {'mode': mode, 'ms': res.get('ms'), 'provider': res.get('label'), **({'data': data_} if data_ else {}), **({'web': [{'title': x_['title'], 'url': x_['url']} for x_ in web_]} if web_ else {})})
        rs._chat_persist()
        return {'ok': bool(reply), 'mode': mode, 'routed': mode != asked, 'reply': reply, 'data': data_, 'web': web_, 'provider': res.get('label'), 'model': res.get('model'), 'ms': res.get('ms'), 'tokens': res.get('usage'), 'history': rs._chat['th'].get(mode) or [], **rs._chat_extra(),
                'new': [p_['id'] for p_ in new], 'refused': refused, 'proposals': rs._aic.view(rs._chat_props()), 'why': res.get('why'), 'learned': rs._chat_learned()}
    finally:
        rs._chat['busy'] = False


@router.post('/api/reputation/admin/ai/chat/clear')
async def admin_ai_chat_clear(request: Request):
    """💬 Owner only: forget the conversation — or ONE message of it (`{index}`). The proposals stay: they are the audit record."""
    rs = _rs()
    rs._require_owner(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    rs._brain_load()
    i = (body or {}).get('index'); m_ = str((body or {}).get('mode') or 'chat')
    if m_ not in rs._aic.MODES:
        raise rs.HTTPException(400, 'Unknown mode.')
    h_ = list(rs._chat['th'].get(m_) or [])
    if i is None and (body or {}).get('from') is None and h_:   # ＋ New chat: the current thread is SAVED first (🗂 reopens it)
        rs._chat['saved'] = rs._aic.save_convo(rs._chat['saved'], m_, h_, rs.time.time())
    f_ = (body or {}).get('from')   # ✏ edit = rewind the thread to this message (it and everything after it go; the page puts the text back in the box)
    if isinstance(f_, int) and not isinstance(f_, bool) and 0 <= f_ < len(h_):
        rs._chat['th'] = {**rs._chat['th'], m_: h_[:f_]}
    else:
        rs._chat['th'] = {**rs._chat['th'], m_: (h_[:i] + h_[i + 1:]) if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(h_) else []}
    rs._chat_persist()
    return {'ok': True, 'mode': m_, 'history': rs._chat['th'][m_], **rs._chat_extra(), 'proposals': rs._aic.view(rs._chat_props()), 'learned': rs._chat_learned()}


@router.post('/api/reputation/admin/ai/image')
async def admin_ai_image(request: Request):
    """🎨 Owner only: the Brain GENERATES a picture from {prompt} (OpenRouter image model, inside its daily spend cap). The picture is saved in
    our upload store and lands in the {mode} thread as the Brain's answer. Never posted anywhere by itself."""
    rs = _rs()
    rs._require_owner(request); rs._brain_load()
    body = await request.json() or {}
    prompt = rs._aic.clean(body.get('prompt'), 1200); m_ = str(body.get('mode') or 'chat')
    if len(prompt) < 3 or m_ not in rs._aic.MODES:
        raise rs.HTTPException(400, 'Describe the picture.')
    if rs._chat['busy']:
        raise rs.HTTPException(429, 'The model is still answering.')
    rs._chat['busy'] = True
    try:
        res = await rs._air.ROUTER.gen_image(rs._ai_http(), rs.os.environ, rs._ai_cfg(), prompt)
    finally:
        rs._chat['busy'] = False
    if not res.get('ok'):
        raise rs.HTTPException(402 if res.get('status') == 402 else 502, f"🎨 {res.get('why')}")
    m2 = rs._re.match(r'^data:image/(png|jpeg|webp);base64,(.+)$', res['url'], rs._re.S)
    if not m2:
        raise rs.HTTPException(502, 'The picture came back in a format we do not keep.')
    raw = rs.base64.b64decode(m2.group(2))
    if len(raw) > 8_000_000:
        raise rs.HTTPException(502, 'The picture is too big to keep.')
    name = f"{rs.uuid.uuid4().hex}.{'jpg' if m2.group(1) == 'jpeg' else m2.group(1)}"
    (rs.UPLOAD_DIR / name).write_bytes(raw)
    url = f'/api/reputation/uploads/{name}'
    rs._chat['th'] = rs._aic.push_thread(rs._aic.push_thread(rs._chat['th'], m_, 'user', f"🎨 {prompt}"), m_, 'assistant', res.get('text') or '🎨 here it is', {'img': url, 'provider': 'OPENROUTER', 'ms': res.get('ms')})
    rs._chat_persist()
    ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'ai-image', f"{res.get('model')} · ${res.get('usd') or 0:.3f} · {prompt[:80]}"); rs._admin_save(ad_)
    return {'ok': True, 'url': url, 'mode': m_, 'model': res.get('model'), 'usd': res.get('usd'), 'ms': res.get('ms'), 'history': rs._chat['th'][m_], **rs._chat_extra()}


@router.post('/api/reputation/admin/ai/chat/open')
async def admin_ai_chat_open(request: Request):
    """🗂 Owner only: reopen a saved conversation into its mode's thread (the thread there now is saved first)."""
    rs = _rs()
    rs._require_owner(request); rs._brain_load()
    cid = str((await request.json() or {}).get('id') or '')
    hit = next((x for x in rs._chat['saved'] if x['id'] == cid), None)
    if not hit:
        raise rs.HTTPException(404, 'No such conversation.')
    now_ = rs.time.time(); m_ = hit['mode'] if hit['mode'] in rs._aic.MODES else 'chat'
    rest = [x for x in rs._chat['saved'] if x['id'] != cid]
    rs._chat['saved'] = rs._aic.save_convo(rest, m_, rs._chat['th'].get(m_), now_)
    rs._chat['th'] = {**rs._chat['th'], m_: list(hit.get('msgs') or [])}
    rs._chat_persist()
    return {'ok': True, 'mode': m_, 'history': rs._chat['th'][m_], **rs._chat_extra()}


@router.post('/api/reputation/admin/ai/chat/saved')
async def admin_ai_chat_saved(request: Request):
    """🗂 Owner only: rename a saved conversation ({id, title}), delete one ({id, delete: true}) or clear them all ({clearAll: true})."""
    rs = _rs()
    rs._require_owner(request); rs._brain_load()
    b = await request.json() or {}
    if b.get('clearAll'):
        rs._chat['saved'] = []
    else:
        cid = str(b.get('id') or '')
        if not any(x['id'] == cid for x in rs._chat['saved']):
            raise rs.HTTPException(404, 'No such conversation.')
        if b.get('delete'):
            rs._chat['saved'] = [x for x in rs._chat['saved'] if x['id'] != cid]
        else:
            t_ = rs._aic.clean(str(b.get('title') or ''), 60)
            if not t_:
                raise rs.HTTPException(400, 'Give it a name.')
            rs._chat['saved'] = [({**x, 'title': t_} if x['id'] == cid else x) for x in rs._chat['saved']]
    rs._chat_persist()
    return {'ok': True, **rs._chat_extra()}


@router.post('/api/reputation/admin/ai/chat/settings')
async def admin_ai_chat_settings(request: Request):
    """⚙ Owner only: the Brain's chat tuning (temperature · answer length) + the small-things allowance. Listed values only; audited."""
    rs = _rs()
    rs._require_owner(request); rs._brain_load()
    body_ = {k_: v_ for k_, v_ in (await request.json() or {}).items() if k_ != 'localBoostUntil'}   # the boost's end is set by the server only (now + 24h)
    rs._chat['settings'] = rs._aic.clean_settings({**body_, 'now': rs.time.time()}, rs._chat['settings'])
    rs._chat_persist()
    ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'ai-chat-settings', rs.json.dumps(rs._chat['settings'])[:160]); rs._admin_save(ad_)
    return {'ok': True, **rs._chat_extra()}


@router.post('/api/reputation/admin/ai/build')
async def admin_ai_build(request: Request):
    """📋 Owner only: {text, title?} → QUEUE it for the build (the owner's tap is the permission) · {id, status} → move it (queued / building /
    shipped / dropped). The model never writes code in the app: the next engineering session reads data/build_queue.json first."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json() or {}
    now = rs.time.time()
    try:
        if body.get('id'):
            rs._chat['build'] = rs._aic.build_set(rs._build_state(), str(body['id']), str(body.get('status') or ''), now); what = f"{body['id']} → {body.get('status')}"
        else:
            rs._chat['build'], it_ = rs._aic.build_add(rs._build_state(), body.get('title'), body.get('text'), body.get('src') or 'chat', now); what = f"queued {it_['id']}: {it_['title']}"
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    rs._json_save(rs.BUILD_QUEUE_PATH, rs._chat['build'])
    ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'ai-build', what[:160]); rs._admin_save(ad_)
    return {'ok': True, 'build': rs._aic.build_view(rs._chat['build'])}


@router.post('/api/reputation/admin/ai/chat/remember')
async def admin_ai_chat_remember(request: Request):
    """🧠 Owner only: REMEMBER THIS — the owner taps a line of the chat and it becomes a lesson (teach.py `note`) that every fitting model
    case reads from now on. The owner's own tap is the approval; a lesson is advice for the model, never an order, a size or a setting."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json()
    text = rs._aic.clean((body or {}).get('text'), 400)
    if len(text) < 8:
        raise rs.HTTPException(400, 'Nothing to remember.')
    try:
        rs._teach['st'] = rs._tch.add(rs._teach_state(), {'kind': 'note', 'text': text}, rs.time.time())
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    rs._json_save(rs.TEACH_PATH, rs._teach['st'])
    if rs._office.get('payload') is not None:
        rs._office['payload']['teach'] = {**rs._tch.view(rs._teach['st']), 'rules': rs._taught_view()}
    ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'ai-remember', text[:160]); rs._admin_save(ad_)
    return {'ok': True, 'learned': rs._chat_learned()}


@router.post('/api/reputation/admin/ai/proposals/decide')
async def admin_ai_proposal_decide(request: Request):
    """✅ / ✕ Owner only: APPROVE or REJECT one pending proposal. Approve is the ONLY call that applies anything (`_ai_proposal_apply`,
    safe kinds only); reject changes nothing. Decided once, audited."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json()
    now = rs.time.time()
    st, todo, err = rs._aic.decide(rs._chat_props(), str((body or {}).get('id') or ''), bool((body or {}).get('approve')), now)
    if err:
        rs._chat['props'] = st; rs._json_save(rs.AI_PROPOSALS_PATH, st)
        raise rs.HTTPException(400, err)
    note = None
    if todo:
        try:
            note = await rs._ai_proposal_apply(todo, now)
        except (ValueError, KeyError) as e:
            note = f'not applied: {str(e)[:120]}'
        st = rs._aic.applied(st, todo['id'], note)
        rs._tk.KERNEL.note('owner', 'AI PROPOSAL ✅', f"{todo['agent']} · {todo['kind']} {todo['key']} — {note}", now, key=f"aiprop:{todo['id']}")
    rs._chat['props'] = st; rs._json_save(rs.AI_PROPOSALS_PATH, st)
    ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'ai-proposal-decide', f"{'approved' if todo else 'rejected'} {(body or {}).get('id')}" + (f": {note}" if note else '')); rs._admin_save(ad_)
    return {'ok': True, 'applied': note, 'proposals': rs._aic.view(st)}


@router.post('/api/reputation/admin/fuse-wallet/retry-dead')
async def fuse_wallet_retry_dead(request: Request):
    """Owner repair for a failed/skipped keeper order.
    Sell repairs are prioritized and return confirmed SOL to the card.
    Buy repairs simply clear the bench/miss state and wake the keeper to spend only existing card cash."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    tid, side, mint = body.get('tpl'), body.get('side'), str(body.get('mint') or '').strip()
    if tid not in rs._prime.TEMPLATES or side not in ('buy', 'sell') or not mint:
        raise rs.HTTPException(400, 'Pick a failed buy/sell on a funded card.')
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        d = rs._fw_load(); b = d['books'].get(tid)
        if not b:
            raise rs.HTTPException(400, 'That tier is not funded.')
        if b.get('pending'):
            raise rs.HTTPException(409, 'Wait for the current transaction to settle first.')
        if side == 'buy':
            misses = dict(b.get('misses') or {}); misses.pop(mint, None)
            bench = dict(b.get('benched') or {}); bench.pop(mint, None)
            b = {**b, 'misses': misses, 'benched': bench}
            d['books'][tid] = b
            rs._fw_record(d, {'card': tid, 'side': 'repair-buy', 'mint': mint, 'at': rs.time.time(), 'status': 'done',
                           'why': 'owner retried dead buy from available card cash'})
        else:
            leg = (b.get('legs') or {}).get(mint)
            if not leg or int(rs._fuse._f(leg.get('atoms'))) <= 0:
                raise rs.HTTPException(400, 'No held balance remains for that failed sell.')
            b = {**b, 'legs': {**(b.get('legs') or {}), mint: {**leg, 'manualCash': True, 'recovered': True}}}
            d['books'][tid] = b
            rs._fw_record(d, {'card': tid, 'side': 'repair-sell', 'mint': mint, 'symbol': leg.get('symbol'), 'at': rs.time.time(), 'status': 'done',
                           'why': 'owner retried dead sell -> proceeds stay in card cash'})
        rs._fw_save(d)
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-wallet-retry-dead', f'{tid} {side} {mint[:8]}'); rs._admin_save(ad)
    rs._fw_kick_now()
    return {'ok': True, 'tpl': tid, 'side': side, 'mint': mint}


@router.post('/api/reputation/admin/fuse-wallet/reinvest-paid')
async def fuse_wallet_reinvest_paid(request: Request):
    """Owner only: move this card's currently segregated paid-out SOL back into active card capital.
    This is an internal reallocation, not new funding: fundedUsd never changes and the historical bankUsd trail is preserved."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    tid = body.get('tpl')
    if tid not in rs._prime.TEMPLATES:
        raise rs.HTTPException(400, 'Pick a funded tier.')
    now = rs.time.time()
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        d = rs._fw_load(); b = d['books'].get(tid)
        if not b:
            raise rs.HTTPException(400, 'That tier is not funded.')
        if b.get('pending'):
            raise rs.HTTPException(409, 'Wait for the current Fuse transaction to settle, then reinvest paid out.')
        if b.get('defund'):
            raise rs.HTTPException(409, 'This card is selling out right now.')
        nb, sol = rs._fw.reinvest_bank(b)
        if sol <= 0:
            raise rs.HTTPException(400, 'This card has no paid-out SOL available to reinvest.')
        d['books'][tid] = nb
        rs._fw_record(d, {'card': tid, 'side': 'reinvest', 'sol': sol, 'usd': round(sol * (await rs._sol_usd_live()), 4), 'at': now, 'by': me, 'status': 'done',
                       'why': 'paid-out SOL moved back into active card capital — not new funding'})
        rs._fw_save(d)
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-wallet-reinvest-paid', f'{tid} {sol:.9f} SOL'); rs._admin_save(ad)
    rs.asyncio.create_task(rs._fw_tick(rs.time.time()))
    return {'ok': True, 'tpl': tid, 'sol': sol, 'fundedUsd': nb.get('fundedUsd'), 'bankUsd': nb.get('bankUsd')}


@router.post('/api/reputation/admin/fuse-wallet/card')
async def fuse_wallet_card(request: Request):
    """Owner only: ↩ defund a tier (every coin sold back to SOL, the card returns to paper) or ▶ resume a halted card."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    tid, act = body.get('tpl'), body.get('action')
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        d = rs._fw_load(); b = d['books'].get(tid)
        if not b or act not in ('defund', 'resume', 'halt'):
            raise rs.HTTPException(400, 'Pick a funded tier and defund / halt / resume.')
        d['books'][tid] = {**b, 'defund': True} if act == 'defund' else {**b, 'halt': act == 'halt'}
        if act == 'defund':   # freeze the paper card to come back to BEFORE the selling changes the coins
            async with rs._admin_lock:
                h = rs._json_load(rs.FUSE_HQ_PATH, {}); cs = (h.get('prime') or {}).get('cards') or {}
                if cs.get(tid) and not cs[tid].get('paperBefore'):
                    cs[tid]['paperBefore'] = rs._fw.paper_snapshot(cs[tid]); rs._json_save(rs.FUSE_HQ_PATH, h)
        rs._fw_save(d)
    ad = rs._admin_load(); rs._audit(ad, me, f'fuse-wallet-{act}', tid); rs._admin_save(ad)
    if act in ('defund', 'resume'):
        rs._fw_kick_now()   # ↩ sell all / ▶ resume start NOW (they waited for the keeper's next scheduled pass)
    return {'ok': True}


@router.get('/api/reputation/admin/data-cleaner')
async def admin_data_cleaner(request: Request):
    """HQ: what the cleaner freed on its last run."""
    rs = _rs()
    rs._require_admin(request)
    return {'last': rs._data_clean_last, 'rules': ['Chat: coin snapshots older than 1h lose their stale signal blocks (text, author and the coin stay)',
                                                f'Logo cache ≤ {rs._strim.LOGO_MAX_BYTES // 2**20} MB (oldest first, nothing under a day old); a logo over {rs._strim.LOGO_FILE_MAX // 2**20:.1f} MB is not cached',
                                                f'Service logs in /tmp over {rs._strim.LOG_MAX_BYTES // 2**20} MB keep their newest {rs._strim.LOG_KEEP_BYTES // 2**20} MB',
                                                'Blocklist: a wallet never blocked and idle 2 weeks is forgotten; a blocked wallet keeps 40 strikes',
                                                'Meme terms: a word out of every kept day drops its refs / sources',
                                                'Pump callers: ≤ 8,000 callers, one number per judged call',
                                                'Never touched: ledgers, .db files, records, archives, agent lineage']}


@router.post('/api/reputation/admin/evolution/{role}/rollback')
async def evolution_rollback(role: str, request: Request):
    rs = _rs()
    rs._require_admin(request)
    book_ = rs._json_load(rs.EVO_PATH, {}); led = book_.get(role) or []
    row = rs._evo.rollback(led, rs.time.time())
    if not row:
        raise rs.HTTPException(400, 'Generation 1 has nothing to roll back to.')
    book_[role] = led; rs._json_save(rs.EVO_PATH, book_); rs._evo_memo.clear()
    return {'rolledBack': row, 'history': rs._evo.history(led)}


@router.post('/api/reputation/admin/fuses/scenario-pick')
async def scenario_pick(request: Request, body: dict):
    """🎨 Creator's pick: HQ puts an engine runner-up on the Arena (or takes it off). Dealt right away. Audited."""
    rs = _rs()
    admin = rs._require_admin(request)
    sid = str(body.get('id') or '')[:40]
    if not sid:
        raise rs.HTTPException(400, 'Pick a scenario card.')
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
        if body.get('on', True) and sid not in (d.get('creatorPicks') or []) and not rs._pg_pick_ok(d, sid):
            raise rs.HTTPException(400, f"Only the playground's top {rs._pgb.SHOWN} big cards can be picked — this one is still competing in the background.")
        cur = [x for x in d.get('creatorPicks') or [] if x != sid] + ([sid] if body.get('on', True) else [])
        d['creatorPicks'] = cur[-4:]; rs._json_save(rs.RUNNERS_PATH, d)   # max 4 big engine cards on the Arena
        ad = rs._admin_load(); rs._audit(ad, admin, 'creator-pick', f"{sid} {'on' if body.get('on', True) else 'off'}"); rs._admin_save(ad)
    await rs._scenario_stage(rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}), rs.time.time())
    return {'creatorPicks': rs._json_load(rs.RUNNERS_PATH, {}).get('creatorPicks') or []}


@router.post('/api/reputation/admin/runners/autotune')
async def runners_autotune(request: Request):
    rs = _rs()
    admin = rs._require_admin(request); on = bool((await request.json()).get('on'))
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['autoTune'] = on; rs._json_save(rs.RUNNERS_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, admin, 'runners-autotune', 'on' if on else 'off'); rs._admin_save(ad)
    return {'autoTune': on}


@router.get('/api/reputation/admin/fuses/playground')
async def fuse_playground(request: Request):
    """🧪 Engine playground: every scenario the engines are testing — strategy runs, bloodline, dial proofs over 6h/24h/72h,
    top-tier cards, runner rounds + lit cards, auto-tune log — and what's proven + ready for the Arena."""
    rs = _rs()
    rs._require_admin(request)
    now = rs.time.time()
    d = rs._json_load(rs.FUSE_HQ_PATH, {}); rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    vals = [rs._hq.arena_value(e, {}, now) for e in d.get('arena') or []]
    board = rs._hq.arena_board(vals)
    dials = {w: rs._rn.dial_proof(rd.get('rounds') or [], rd.get('paths') or {}, now, rs._hq.RISK_DIALS, window=sec) for w, sec in rs._rn.PROOF_WINDOWS.items()}
    prime = await rs._prime_view()
    auto = [a for a in (rs._admin_load().get('audit') or []) if a.get('action') in ('runners-config', 'runners-autotune', 'arena-prime')][-12:][::-1]
    return {'counts': {'arenaRuns': len(vals), 'settled': sum(1 for v in vals if v.get('settled')), 'open': sum(1 for v in vals if not v.get('settled')),
                       'bloodline': len(d.get('bloodline') or []), 'runnerRounds': len(rd.get('rounds') or []), 'litCards': len(rd.get('litCards') or []),
                       'dialScenarios': sum(p.get('rounds', 0) for proof in dials.values() for p in proof.values()), 'tierCards': len(prime),
                       'published': len(rs._json_load(rs.FUSES_PATH, {'fuses': {}})['fuses'])},
            'board': board, 'dials': dials, 'bloodline': (d.get('bloodline') or [])[-12:][::-1], 'prime': [{k: c.get(k) for k in ('label', 'tier', 'pnlPct', 'lowPct', 'goodDays', 'loggedDays')} for c in prime],
            'autoLog': auto, 'engineDial': rd.get('cfgDial') or 'custom', 'autoTune': rd.get('autoTune') is not False,
            'gateRegret': rs._rn.gate_regret(rd.get('dropLog') or [], await rs._hq_prices([{'chainId': 'solana', 'pairAddress': e['pairAddress']} for e in (rd.get('dropLog') or [])[-120:] if e.get('pairAddress')]), now),
            'scenarios': (scen := rs._rn.scenarios(rd.get('rounds') or [], rd.get('paths') or {}, now, rs._hq.RISK_DIALS)),
            'scenarioCards': await rs._pg_scenario_cards(rd, scen, now, coins=rs._pgb.REGULAR_COINS),
            'shownIds': rs._pgb.shown((rd.get('pgBattle') or {}).get('record'), (rd.get('pgBattle') or {}).get('pcts'), list(((rd.get('pgBattle') or {}).get('cards') or {}))),
            'filters': {'24h': rs._rn.filter_proof(rd.get('rounds') or [], rd.get('paths') or {}, now, rs._rn.clean_cfg(rd.get('cfg') or {}), 24 * 3600),
                        '72h': rs._rn.filter_proof(rd.get('rounds') or [], rd.get('paths') or {}, now, rs._rn.clean_cfg(rd.get('cfg') or {}), 72 * 3600)},
            'doctor': {'filter': rd.get('pickFilter'), 'sitOut': bool(rd.get('sitOut')), 'why': rd.get('doctorWhy'), 'at': rd.get('doctorAt')},
            'pgBattle': rs._pg_battle_view(rd),
            **rs._hq.playground_ready(board, dials, prime, battle_rows=rs._pgb.ready_rows((rd.get('pgBattle') or {}).get('record'), {k: c.get('name') for k, c in ((rd.get('pgBattle') or {}).get('cards') or {}).items()}))}


@router.post('/api/reputation/admin/fuses/sim/apply')
async def pg_sim_apply(request: Request):
    """Apply the brain's pick (round clock + rotate-only-losers threshold) to the tier engine. Audited."""
    rs = _rs()
    me = rs._require_admin(request)
    b = (rs._json_load(rs.PG_SIM_PATH, {}).get('best') or {})
    patch = {}
    if b.get('clock'):
        patch['rotateHours'] = int(b['clock']['value']) / 60
    if b.get('minDrop'):
        patch['rotateMinDrop'] = float(b['minDrop']['value'])
    if not patch:
        raise rs.HTTPException(400, 'The brain needs more sims first.')
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {}); pr['cfg'] = rs._prime.clean_cfg({**(pr.get('cfg') or {}), **patch}); rs._json_save(rs.FUSE_HQ_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'sim-apply', rs.json.dumps(patch)); rs._admin_save(ad)
    return {'ok': True, 'applied': patch, 'cfg': pr['cfg']}


@router.post('/api/reputation/admin/runners/pick-filter')
async def runners_pick_filter(request: Request, body: dict):
    """HQ overrides the doctor: set a pick filter ('' = none) and/or sit out. Audited; the doctor may change it next round."""
    rs = _rs()
    admin = rs._require_admin(request)
    fid = body.get('filter') or None
    if fid and fid not in rs._rn.PICK_FILTERS:
        raise rs.HTTPException(400, 'Unknown pick filter.')
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['pickFilter'] = fid
        if 'sitOut' in body:
            d['sitOut'] = bool(body['sitOut'])
        d['doctorWhy'] = 'set from HQ'; d['doctorAt'] = rs.time.time(); rs._json_save(rs.RUNNERS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'runners-config', f"pick filter {fid or 'none'} · sit out {d.get('sitOut')}"); rs._admin_save(ad)
    return {'filter': fid, 'sitOut': bool(rs._json_load(rs.RUNNERS_PATH, {}).get('sitOut'))}


@router.post('/api/reputation/admin/fuses/pg-battles')
async def pg_battles_set(request: Request, body: dict):
    """HQ controls for playground battles: on/off, round length (5/15/30/60 min), cards (2/4/6), $ size, swap rules, or
    `reset` (fresh cards + records). Audited."""
    rs = _rs()
    admin = rs._require_admin(request)
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); b = d.get('pgBattle') or {}
        b['cfg'] = rs._pgb.clean_cfg({**(b.get('cfg') or {}), **(body.get('cfg') or {})})
        if body.get('lock'):   # 🔒 lock / unlock one playground card's configs (coins + DNA survive a loss, the brain never re-breeds it)
            lk = set(b.get('locked') or [])
            (lk.add if body.get('on', True) else lk.discard)(str(body['lock'])[:60])
            b['locked'] = sorted(lk)
        if body.get('reset'):
            b = {'cfg': b['cfg'], 'locked': b.get('locked') or []}
        elif body.get('bell'):
            b['endsAt'] = 0
        d['pgBattle'] = b; rs._json_save(rs.RUNNERS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'pg-battles', rs.json.dumps({**b['cfg'], 'reset': bool(body.get('reset')), 'bell': bool(body.get('bell'))})[:160]); rs._admin_save(ad)
    await rs._pg_battle_tick(rs.time.time())
    return rs._pg_battle_view(rs._json_load(rs.RUNNERS_PATH, {}))


@router.post('/api/reputation/admin/runners/config')
async def runners_cfg_set(request: Request):
    """HQ › Runners settings: gates, round size, each lane's exits, rounds needed to light up. Range-checked; reset = defaults."""
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    if body.get('dial'):   # 🎚 Engine dial: Safe / Balanced / Degen sets gates + lanes together
        try:
            dialed = rs._rn.engine_dial(str(body['dial']), rs._runner_cfg())
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        dial, cfg = dialed.pop('dial'), rs._rn.clean_cfg(dialed)
    else:
        dial, cfg = 'custom', (rs._rn.DEFAULT_CFG if body.get('reset') else rs._rn.clean_cfg({**rs._runner_cfg(), **(body.get('cfg') or {})}))
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['cfg'] = cfg; d['cfgDial'] = dial; rs._json_save(rs.RUNNERS_PATH, d)
    rs._runner_live_cache.update(at=0, data=None)
    ad = rs._admin_load(); rs._audit(ad, admin, 'runners-config', rs.json.dumps(cfg)[:160]); rs._admin_save(ad)
    return {'cfg': cfg, 'dial': dial}


@router.post('/api/reputation/admin/runners/round')
async def runners_force_round(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'round': await rs._runner_tick(force=True)}


@router.post('/api/reputation/admin/fuses/card-collection')
async def fuse_card_collection(request: Request, p: _RSM.FuseCardIn):
    """Record the Fuse Cards collection the owner's wallet created (verified on-chain)."""
    rs = _rs()
    me = rs._require_owner(request)
    if not rs._re.match(rs._B58, p.collection):
        raise rs.HTTPException(400, 'Bad collection address.')
    await rs._nft_verify(p.signature, me, [p.collection])
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSES_PATH, {'fuses': {}}); d['cardCollection'] = {'address': p.collection, 'sig': p.signature, 'at': rs.time.time()}; rs._json_save(rs.FUSES_PATH, d)
    return {'ok': True}


@router.post('/api/reputation/admin/fuses/{fid}/card')
async def fuse_card_minted(request: Request, fid: str, p: _RSM.FuseCardIn):
    """Record a minted Fuse card (verified on-chain). From now on the card's holder is paid the creator cut."""
    rs = _rs()
    me = rs._require_owner(request)
    if not rs._re.match(rs._B58, p.asset):
        raise rs.HTTPException(400, 'Bad asset address.')
    d = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    col = (d.get('cardCollection') or {}).get('address')
    if not col or fid not in d['fuses']:
        raise rs.HTTPException(404, 'Create the Fuse Cards collection and publish this Fuse first.')
    if (d['fuses'][fid].get('card') or {}).get('asset'):
        raise rs.HTTPException(400, 'This Fuse already has its card (1 of 1).')
    await rs._nft_verify(p.signature, me, [p.asset, col])
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
        d['fuses'][fid]['card'] = {'asset': p.asset, 'sig': p.signature, 'at': rs.time.time()}
        rs._json_save(rs.FUSES_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-card', f'{fid} → {p.asset[:8]}…'); rs._admin_save(ad)
    return {'ok': True}


@router.post('/api/reputation/admin/fuses/{fid}/aura')
async def fuse_aura(request: Request, fid: str):
    """Pick the live aura (outside-the-card effect) a Fuse's card shows everywhere."""
    rs = _rs()
    admin = rs._require_admin(request)
    aura = str((await request.json()).get('aura') or '')
    if aura not in ('', *rs.badge_cards.AURAS):
        raise rs.HTTPException(400, 'Unknown aura.')
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
        if fid not in d['fuses']:
            raise rs.HTTPException(404, 'No such Fuse.')
        d['fuses'][fid]['aura'] = aura; rs._json_save(rs.FUSES_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, admin, 'fuse-aura', f'{fid} {aura or "none"}'); rs._admin_save(ad)
    return {'ok': True, 'aura': aura}


@router.post('/api/reputation/admin/vaults')
async def admin_vaults_save(request: Request):
    """Design a vault: up to 3 pools (v2/v3), base weights, per-pool caps (% of pool TVL), v3 range widths, fees.
    Status stays 'design' until the on-chain program is deployed and audited — nothing here moves funds."""
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    body = await request.json()
    async with rs._admin_lock:
        d = rs._json_load(rs.VAULTS_PATH, {'vaults': {}})
        vid = body.get('id') or rs.uuid.uuid4().hex[:10]
        if body.get('delete'):
            d['vaults'].pop(vid, None)
        else:
            pools = rs._vault.clean_pools(body.get('pools'))
            name = str(body.get('name') or '').strip()[:40]
            if not name or not 1 <= len(pools) <= rs._vault.MAX_POOLS:
                raise rs.HTTPException(400, f'A vault needs a name and 1–{rs._vault.MAX_POOLS} pools.')
            prev = d['vaults'].get(vid) or {}
            d['vaults'][vid] = {'name': name, 'emoji': str(body.get('emoji') or '🏦')[:4], 'tagline': str(body.get('tagline') or '')[:120], 'pools': pools,
                                'mgmtBps': max(0, min(rs.VAULT_MAX_MGMT_BPS, int(body.get('mgmtBps') or 0))), 'perfBps': max(0, min(rs.VAULT_MAX_PERF_BPS, int(body.get('perfBps') or 0))),
                                'status': prev.get('status', 'design') if body.get('status') not in ('design', 'off') else body['status'],
                                'programId': prev.get('programId'), 'createdAt': prev.get('createdAt') or rs.time.time()}
        rs._json_save(rs.VAULTS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'vault', rs.json.dumps({'id': vid, 'name': body.get('name'), 'delete': body.get('delete')})[:160]); rs._admin_save(ad)
    return {'ok': True, 'id': vid}


@router.post('/api/reputation/admin/quests/season')
async def admin_quest_season(request: Request):
    """Name the season, set its start, pause/unpause (paused until launch), or award the week's top 3 a trophy."""
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    async with rs._admin_lock:
        d = rs._json_load(rs.QUESTS_PATH, {})
        s = {**rs.QUEST_SEASON_DEFAULT, **(d.get('season') or {})}
        for k in ('name', 'paused', 'start'):
            if k in body:
                s[k] = body[k]
        if body.get('paused') is False and not s.get('start'):
            s['start'] = rs.time.time()
        d['season'] = s
        awarded = []
        if body.get('awardWeek'):
            if s.get('paused') or not s.get('start'):
                raise rs.HTTPException(400, 'Season is paused — unpause it (at launch) before awarding weeks.')
            rs._quest_board_cache.clear()
            top = (await rs.quest_leaderboard())['rows'][:3]
            week = int((rs.time.time() - float(s['start'])) // (7 * 86400)) + 1
            col = rs._json_load(rs.COLLECTION_PATH, {})
            for rank, row in enumerate(top, 1):
                iid = f"quest:{s['id']}:w{week}:{rank}"
                items = col.setdefault(row['address'], [])
                if not any(it.get('id') == iid for it in items):
                    items.append({'id': iid, 'kind': 'quest', 'season': s['id'], 'week': week, 'rank': rank, 'name': f"{s['name']} · Week {week} #{rank}",
                                  'glyph': ['🥇', '🥈', '🥉'][rank - 1], 'rarity': ['mythic', 'legendary', 'epic'][rank - 1], 'xp': row['xp'], 'at': rs.time.time()})
                    awarded.append(row['address'])
            rs._json_save(rs.COLLECTION_PATH, col)
        rs._json_save(rs.QUESTS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'quest-season', rs.json.dumps({k: s.get(k) for k in ('name', 'paused')} | {'awarded': len(awarded)})[:160]); rs._admin_save(ad)
    rs._quest_cache.clear(); rs._quest_board_cache.clear()
    return {'ok': True, 'season': s, 'awarded': awarded}


@router.post('/api/reputation/admin/quests')
async def admin_quests_save(request: Request):
    """Edit any badge (name, tier, tasks/targets, on/off) or add one. Invalid task lists are refused."""
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    edits = body.get('badges') or {}
    for bid, o in edits.items():
        if not rs._re.match(r'^[a-z0-9-]{2,40}$', bid) or (o.get('tasks') is not None and not rs._quests.is_valid_def({'name': o.get('name') or bid, 'tasks': o['tasks']})):
            raise rs.HTTPException(400, f'Badge {bid}: every task needs a known metric and a positive target.')
        if o.get('tier') and o['tier'] not in rs._quests.TIER_XP:
            raise rs.HTTPException(400, f'Badge {bid}: unknown tier.')
        if 'aura' in o and o['aura'] not in ('', *rs.badge_cards.AURAS):
            raise rs.HTTPException(400, f'Badge {bid}: unknown aura.')
    async with rs._admin_lock:
        d = rs._json_load(rs.QUESTS_PATH, {})
        for bid, o in edits.items():
            if o.get('reset'):
                (d.get('badges') or {}).pop(bid, None)
            else:
                d.setdefault('badges', {})[bid] = {**(d.get('badges') or {}).get(bid, {}), **{k: v for k, v in o.items() if k in ('name', 'tier', 'enabled', 'tasks', 'art', 'set', 'perks', 'aura')}}
        rs._json_save(rs.QUESTS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'quests', ','.join(edits)[:160]); rs._admin_save(ad)
    rs._quest_cache.clear(); rs._badge_cache.clear(); rs._rarity_cache.clear()
    return {'ok': True, 'badges': rs._quest_defs()}


@router.post('/api/reputation/admin/quests/grant')
async def admin_quests_grant(request: Request):
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    who, bid, action = rs.primary_of(body.get('address', '')), body.get('badge', ''), body.get('action', 'grant')
    if not who or not any(b['id'] == bid for b in rs._quest_defs()) or action not in ('grant', 'revoke', 'clear'):
        raise rs.HTTPException(400, 'Pick a wallet, a badge and grant / revoke / clear.')
    async with rs._admin_lock:
        d = rs._json_load(rs.QUESTS_PATH, {})
        m = d.setdefault('manual', {}).setdefault(who, {'grant': [], 'revoke': []})
        m['grant'] = [x for x in m.get('grant', []) if x != bid]; m['revoke'] = [x for x in m.get('revoke', []) if x != bid]
        if action != 'clear':
            m[action].append(bid)
        rs._json_save(rs.QUESTS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, f'quest-{action}', f'{bid} {who[:8]}'); rs._admin_save(ad)
    rs._quest_cache.pop(who, None); rs._badge_cache.pop(who, None)
    return {'ok': True, 'manual': m}


@router.get('/api/reputation/badges/{address}')
async def wallet_badges(address: str):
    """Automatic, data-backed badges. Every badge states the evidence behind it."""
    rs = _rs()
    hit = rs._badge_cache.get(address)
    if hit and rs.time.time() - hit[0] < 300:
        return hit[1]
    badges = []
    mints = await rs._ecosystem_mints()
    labels = {'fee': '$FEE', 'feecat': 'FEECAT', 'rfee': 'rFEE'}
    fee_usd = 0.0
    for aid, mint in mints.items():
        try:
            value = await rs._holding_usd(address, mint)
        except Exception:
            continue
        if aid == 'fee':
            fee_usd = value
        if value >= 1:
            label = labels.get(aid, aid.upper())
            if aid == 'fee' and value >= 1000:
                badges.append({'id': 'fee-whale', 'label': '$FEE Whale', 'icon': '🐋', 'tone': 'gold', 'why': f'Holds ${value:,.0f} of $FEE'})
            badges.append({'id': f'{aid}-holder', 'label': f'{label} Holder', 'icon': '🌿' if aid == 'fee' else '🐱' if aid == 'feecat' else '💠', 'tone': 'mint', 'why': f'Holds ${value:,.2f} of {label}'})
    try:
        async with rs.httpx.AsyncClient(timeout=6) as http:
            leader = (await http.get('http://127.0.0.1:5088/api/cats/leader')).json().get('cat') or {}
        for pos in leader.get('positions', []):
            if pos.get('mint') and await rs._holding_usd(address, pos['mint']) >= 1:
                badges.append({'id': 'rides-with-fee', 'label': 'Rides with Fee', 'icon': '🐾', 'tone': 'mint', 'why': f"Holds {pos['symbol']}, which Fee is in right now"})
                break
    except Exception:
        pass
    board = await rs.caller_board(days=30)
    me = next((r for r in board['rows'] if r.get('callerAddress') == address), None)
    if me:
        sharp = me['calls'] >= 5 and me['hitRate'] >= 0.5
        badges.append({'id': 'sharp-caller' if sharp else 'caller', 'label': 'Sharp Caller' if sharp else 'Caller', 'icon': '🏹' if sharp else '🎯', 'tone': 'gold' if sharp else 'plain',
                       'why': f"{me['calls']} calls, {round(me['hitRate'] * 100)}% hit 2× (30d)"})
    creator = rs._load()['creators'].get(rs._creator_key('solana', address))
    if creator:
        sc = rs.score_creator(creator)
        if sc['badge'] == 'trusted':
            badges.append({'id': 'trusted-creator', 'label': 'Trusted Creator', 'icon': '🛡️', 'tone': 'mint', 'why': f"{sc['tokenCount']} launches, none dumped"})
        elif sc['badge'] == 'flagged':
            badges.append({'id': 'flagged-creator', 'label': 'Flagged Creator', 'icon': '⚠️', 'tone': 'bad', 'why': f"{sc['dumpedCount'] + sc['ruggedCount']} launches dumped or rugged"})
    if any(l['wallet'] == address for l in (rs._load().get('feelessLaunches') or {}).values()):
        badges.append({'id': 'feeless-launcher', 'label': 'FEELESS Launcher', 'icon': '🚀', 'tone': 'mint', 'why': 'Launched a token on FEELESS (verified on-chain)'})
    rec = rs._block_load()['wallets'].get(address)
    if rs._is_blocked(rec):
        badges.append({'id': 'blocklisted', 'label': 'Blocklisted', 'icon': '⛔', 'tone': 'bad', 'why': f"Caught bundling/sniping {len(rec['mints'])} launch(es)"})
    invited = len(rs._json_load(rs.REF_PATH, {'by': {}})['by'].get(address, []))
    if invited >= 3:
        badges.append({'id': 'recruiter', 'label': 'Recruiter' if invited < 10 else 'Legendary Recruiter', 'icon': '📣', 'tone': 'gold' if invited >= 10 else 'mint', 'why': f'Invited {invited} wallets to FEELESS'})
    if 'badge:points-og' in rs._unlocks(address)[0]:
        badges.append({'id': 'points-og', 'label': 'Points OG', 'icon': '🏅', 'tone': 'gold', 'why': 'Spent 2,000 earned points on it'})
    badges.extend(rs._admin_load()['badges'].get(address, {}).values())
    try:   # earned quest badges (animated art) join chat + profile badges, rarest first
        rank_q = {'mythic': 5, 'legendary': 4, 'epic': 3, 'rare': 2, 'common': 1}
        qs = [b for b in (await rs._quest_summary(address))['badges'] if b['earned']]
        for b in sorted(qs, key=lambda b: -rank_q.get(b['tier'], 0)):
            badges.append({'id': b['id'], 'label': b['name'], 'icon': '', 'art': b['art'], 'rarity': b['tier'], 'tone': 'gold' if rank_q.get(b['tier'], 0) >= 4 else 'mint',
                           'why': ' · '.join(t['label'] for t in b['tasks']) + (' (granted by FEELESS HQ)' if b.get('granted') else '')})
    except Exception:
        pass
    if address and rs._is_staff(address):
        badges.insert(0, {'id': 'feeless-hq', 'label': 'FEELESS HQ', 'icon': '👑', 'tone': 'gold', 'why': 'Created $FEE — runs the FEELESS HQ'})
    # Season cards count as badges too (best rarity first), so chat + profiles show them.
    rank = {'mythic': 5, 'legendary': 4, 'epic': 3, 'rare': 2, 'common': 1}
    seasonal = sorted((it for it in rs._json_load(rs.COLLECTION_PATH, {}).get(rs.primary_of(address), []) if it.get('kind') in ('season', 'weekly')),
                      key=lambda it: (-rank.get(it.get('rarity'), 0), -(it.get('at') or 0)))
    for it in seasonal[:2]:
        key = f"season:{it['season']}" if it['kind'] == 'season' else f"week:{it['season']}:w{it.get('week')}"
        badges.append({'id': key.replace(':', '-'), 'card': key, 'label': it.get('name') or 'Season card', 'icon': it.get('glyph') or '🏅',
                       'tone': 'gold' if rank.get(it.get('rarity'), 0) >= 3 else 'mint', 'rarity': it.get('rarity'), 'why': it.get('how') or 'Season card'})
    # Card edits (HQ › Badges › Cards) change the name + glyph everywhere, chat included.
    edits = rs._json_load(rs.CARDS_PATH, {})
    for b in badges:
        e = edits.get(b.get('card') or f"badge:{b['id']}") or {}
        if e.get('title'):
            b['label'] = e['title']
        if e.get('glyph'):
            b['icon'] = e['glyph']
        if e.get('rarity'):
            b['rarity'] = e['rarity']
    progress = {'feeUsd': round(fee_usd, 2), 'calls': me['calls'] if me else 0, 'hitRate': me['hitRate'] if me else 0}
    out = {'address': address, 'badges': badges, 'progress': progress, 'at': rs.time.time()}
    rs._badge_cache[address] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/admin/whoami')
async def admin_whoami(address: str = ''):
    rs = _rs()
    return {'isAdmin': bool(address) and rs._is_staff(address), 'isOwner': address in rs._owner_wallets()}   # two yes/no only (isOwner = show the creator's HQ pop-out button) — every HQ action still needs a signed admin session


@router.get('/api/reputation/admin/badges')
async def badge_awards_admin_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    d = rs._admin_load()
    rows = [{'address': address, 'badges': list(items.values())} for address, items in d['badges'].items() if items]
    rows.sort(key=lambda row: -max((b.get('at', 0) for b in row['badges']), default=0))
    seen = {}
    for a, (at, rec) in list(rs._badge_cache.items()):
        if rs.time.time() - at < 86400:
            for b in (rec or {}).get('badges', []):
                x = seen.setdefault(b['id'], {'id': b['id'], 'label': b.get('label'), 'icon': b.get('icon'), 'tone': b.get('tone'), 'why': b.get('why'), 'holders': 0, 'builtin': True})
                x['holders'] += 1
    custom = {b['id'] for row in rows for b in row['badges']}
    builtin = sorted((v for k, v in seen.items() if k not in custom), key=lambda v: -v['holders'])
    return {'rows': rows[:500], 'limits': rs._badge_limits(), 'wallets': len(rows), 'awards': sum(len(row['badges']) for row in rows), 'builtin': builtin}


@router.post('/api/reputation/admin/badges')
async def admin_award(request: Request, payload: _RSM.AdminBadge):
    rs = _rs()
    admin = rs._require_admin(request)
    addrs = [a for a in payload.addresses[:500] if rs._re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', str(a))]
    if not addrs:
        raise rs.HTTPException(400, 'No valid addresses.')
    bid = 'custom-' + rs._re.sub(r'[^a-z0-9]+', '-', payload.label.lower()).strip('-')[:28]
    tone = payload.tone if payload.tone in ('mint', 'gold', 'plain', 'bad') else 'gold'
    async with rs._admin_lock:
        d = rs._admin_load()
        for a in addrs:
            d['badges'].setdefault(a, {})[bid] = {'id': bid, 'label': payload.label, 'icon': payload.icon, 'tone': tone,
                                                  'why': payload.why or 'Awarded by FEELESS', 'awardedBy': 'FEELESS', 'at': rs.time.time()}
            rs._badge_cache.pop(a, None)
        rs._audit(d, admin, 'award-badge', f'{payload.label} → {len(addrs)} wallet(s)')
        rs._admin_save(d)
    return {'ok': True, 'awarded': len(addrs), 'id': bid}


@router.delete('/api/reputation/admin/badges/{address}/{bid}')
async def admin_revoke(request: Request, address: str, bid: str):
    rs = _rs()
    admin = rs._require_admin(request)
    async with rs._admin_lock:
        d = rs._admin_load()
        removed = d['badges'].get(address, {}).pop(bid, None)
        rs._badge_cache.pop(address, None)
        rs._audit(d, admin, 'revoke-badge', f'{bid} ✕ {address[:6]}…')
        rs._admin_save(d)
    return {'ok': bool(removed)}


@router.get('/api/reputation/admin/airdrops')
async def admin_airdrops(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'airdrops': sorted(rs._admin_load()['airdrops'], key=lambda a: -a['scheduledAt'])}


@router.post('/api/reputation/admin/airdrops')
async def admin_schedule(request: Request, payload: _RSM.Airdrop):
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    recips = []
    for r in payload.recipients[:1000]:
        a = str((r or {}).get('address', ''))
        try:
            amt = float((r or {}).get('amount'))
        except (TypeError, ValueError):
            continue
        if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a) and amt > 0:
            recips.append({'address': a, 'amount': amt})
    if not recips:
        raise rs.HTTPException(400, 'Add at least one valid Solana recipient with an amount.')
    drop = {'id': rs.uuid.uuid4().hex[:12], 'name': payload.name, 'asset': payload.asset, 'recipients': recips,
            'total': sum(r['amount'] for r in recips), 'scheduledAt': payload.scheduledAt, 'note': payload.note,
            'status': 'scheduled', 'createdAt': rs.time.time(), 'createdBy': admin, 'txs': []}
    async with rs._admin_lock:
        d = rs._admin_load(); d['airdrops'].append(drop)
        rs._audit(d, admin, 'schedule-airdrop', f"{payload.name}: {len(recips)} wallets, {drop['total']:,.2f} {payload.asset.upper()}")
        rs._admin_save(d)
    return {'ok': True, 'airdrop': drop}


@router.post('/api/reputation/admin/airdrops/{drop_id}')
async def admin_airdrop_status(request: Request, drop_id: str, payload: _RSM.AirdropStatus):
    rs = _rs()
    admin = rs._require_admin(request)
    if payload.status not in ('sent', 'cancelled', 'scheduled'):
        raise rs.HTTPException(400, 'Bad status.')
    verified = None
    if payload.status == 'sent':
        if not payload.txSig or not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', payload.txSig):
            raise rs.HTTPException(400, 'Paste the on-chain transaction signature to mark an airdrop sent.')
        async with rs.httpx.AsyncClient(timeout=20) as http:
            tx = await rs._rpc(http, 'getTransaction', [payload.txSig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}])
        if not tx:
            raise rs.HTTPException(404, 'That transaction is not on-chain (yet).')
        if (tx.get('meta') or {}).get('err'):
            raise rs.HTTPException(400, 'That transaction failed on-chain.')
        signers = [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]
        if admin not in signers:
            raise rs.HTTPException(400, 'That transaction was not signed by your HQ wallet.')
        verified = {'sig': payload.txSig, 'slot': tx.get('slot'), 'blockTime': tx.get('blockTime')}
    async with rs._admin_lock:
        d = rs._admin_load()
        drop = next((x for x in d['airdrops'] if x['id'] == drop_id), None)
        if not drop:
            raise rs.HTTPException(404, 'Airdrop not found.')
        drop['status'] = payload.status
        if verified:
            drop['txs'].append(verified)
            for r in drop['recipients']:
                d['badges'].setdefault(r['address'], {})['airdrop-recipient'] = {
                    'id': 'airdrop-recipient', 'label': 'Airdropped', 'icon': '🪂', 'tone': 'gold',
                    'why': f"Received the {drop['name']} airdrop", 'awardedBy': 'FEELESS', 'at': rs.time.time()}
                rs._badge_cache.pop(r['address'], None)
        rs._audit(d, admin, f'airdrop-{payload.status}', drop['name'])
        rs._admin_save(d)
    return {'ok': True, 'airdrop': drop}


@router.post('/api/reputation/admin/bugs/{bug_id}')
async def admin_bug_status(request: Request, bug_id: str, status: str = Query(...)):
    rs = _rs()
    admin = rs._require_admin(request)
    if status not in ('open', 'fixing', 'fixed', 'wontfix'):
        raise rs.HTTPException(400, 'Bad status.')
    async with rs._admin_lock:
        d = rs._json_load(rs.BUGS_PATH, {'bugs': []})
        for b in d['bugs']:
            if b['id'] == bug_id:
                b['status'] = status; b['updatedAt'] = rs.time.time()
        rs._json_save(rs.BUGS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'bug-status', f'{bug_id} → {status}'); rs._admin_save(ad)
    return {'ok': True}


@router.post('/api/reputation/admin/support/poll')
async def admin_support_poll(request: Request):
    """🛟 Owner: move a poll onto the roadmap / building / shipped / declined (or back to the ladder with status ''), with a note. Audited."""
    rs = _rs()
    admin = rs._require_owner(request)
    import support as _sp
    body = await request.json()
    st_k = str(body.get('status') or '')
    if st_k and st_k not in _sp.OWNER_STATES:
        raise rs.HTTPException(400, 'Bad status.')
    async with rs._admin_lock:
        st_ = rs._json_load(rs.SUPPORT_PATH, {'polls': [], 'plus': {}})
        pl_ = next((x_ for x_ in st_.get('polls') or [] if x_.get('id') == body.get('id')), None)
        if not pl_:
            raise rs.HTTPException(404, 'No such poll.')
        pl_['status'] = st_k or None
        pl_['note'] = str(body.get('note') or '')[:200] or None
        rs._json_save(rs.SUPPORT_PATH, st_)
        ad_ = rs._admin_load(); rs._audit(ad_, admin, 'support-poll', f"{pl_['id']} → {st_k or 'ladder'}"); rs._admin_save(ad_)
    return {'ok': True}


@router.get('/api/reputation/admin/security')
async def admin_security(request: Request):
    rs = _rs()
    rs._require_admin(request)
    root = rs.Path(__file__).parent
    checks = []

    def check(name, ok, detail, sev='high'):
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail, 'severity': 'ok' if ok else sev})

    for f, label in ((root / 'data' / 'internal.key', 'Internal service key'), (root / '.env', 'Backend .env secrets')):
        if f.exists():
            mode = oct(f.stat().st_mode & 0o777)
            check(f'{label} permissions', (f.stat().st_mode & 0o077) == 0, f'{f.name} is {mode} (should be 0o600)', 'high')
    gi = (root.parent / '.gitignore')
    gtxt = gi.read_text() if gi.exists() else ''
    check('Secrets kept out of git', all(x in gtxt for x in ('.env', 'data/')), '.gitignore covers .env and backend/data/' if gtxt else 'No .gitignore found')
    fe_env = root.parent / 'frontend' / '.env'
    leak = fe_env.exists() and rs._re.search(r'REACT_APP_[A-Z_]*=.*(api-key|apikey|secret)', fe_env.read_text(), rs._re.I)
    check('No API keys shipped to the browser', not leak, 'A REACT_APP_ variable contains a key — it is public in the bundle.' if leak else 'No REACT_APP_ secrets found')
    check('RPC key stays server-side', bool(rs.os.environ.get('SOLANA_RPC_URL')), 'Helius RPC is read from backend/.env only', 'medium')
    check('CORS scope', False, "Services allow any origin ('*'). Lock to your domain before launch.", 'medium')
    services = []
    async with rs.httpx.AsyncClient(timeout=4) as http:
        for name, url in (('Market API', 'http://127.0.0.1:5001/api/market/assets'), ('Reputation', 'http://127.0.0.1:5077/api/reputation/health'),
                          ('FeeCats', 'http://127.0.0.1:5088/api/cats/leader'), ('Candles', 'http://127.0.0.1:5099/api/candles/health')):
            t0 = rs.time.time()
            try:
                r = await http.get(url); up = r.status_code < 500
            except Exception:
                up = False
            services.append({'name': name, 'up': up, 'ms': round((rs.time.time() - t0) * 1000)})
    now = rs.time.time()
    recent = [s for s in rs._status_log if now - s[0] < 3600]
    by = {}
    for _, m, p, st in recent:
        if st == 404 and m == 'GET' and p.startswith(rs.EXPECTED_404_PREFIXES):
            continue  # 'not observed yet' answers, not failures
        k = f'{st} {m} {rs._re.sub(r"/[1-9A-HJ-NP-Za-km-z]{32,}|/0x[0-9a-fA-F]{40}", "/:addr", p)}'
        by[k] = by.get(k, 0) + 1
    signals = {'forgedSignatures': sum(1 for s in recent if s[3] == 401), 'replays': sum(1 for s in recent if s[3] == 409),
               'rateLimited': sum(1 for s in recent if s[3] == 429), 'forbidden': sum(1 for s in recent if s[3] == 403),
               'serverErrors': sum(1 for s in recent if s[3] >= 500)}
    chat = rs._json_load(rs.CHAT_PATH, {})
    rooms = chat.get('rooms', chat) if isinstance(chat, dict) else {}
    msgs24 = sum(1 for msgs in rooms.values() if isinstance(msgs, list) for m in msgs if isinstance(m, dict) and now - (m.get('ts', 0) / (1000 if m.get('ts', 0) > 1e12 else 1)) < 86400)
    bl = rs._block_load()['wallets']
    bugs = rs._json_load(rs.BUGS_PATH, {'bugs': []})['bugs']
    score = max(0, 100 - sum(25 if c['severity'] == 'high' else 8 for c in checks if not c['ok']) - (10 if signals['serverErrors'] else 0) - 10 * sum(1 for s in services if not s['up']))
    return {'score': score, 'checks': checks, 'services': services, 'signals': signals,
            'topErrors': sorted(({'key': k, 'count': v} for k, v in by.items()), key=lambda x: -x['count'])[:12],
            'stats': {'chat24h': msgs24, 'chatRooms': len(rooms), 'blocklisted': sum(1 for r in bl.values() if rs._is_blocked(r)),
                      'openBugs': sum(1 for b in bugs if b['status'] in ('open', 'fixing') and rs.time.time() - rs._bug_seen(b) < rs.BUG_FRESH_S), 'customBadges': sum(len(v) for v in rs._admin_load()['badges'].values())},
            'audit': rs._admin_load()['audit'][-25:][::-1], 'at': now}


@router.get('/api/reputation/familia/street/{city}')
async def familia_street(city: str, viewer: str = Query('', max_length=64), session: str = Query('', max_length=400)):
    """💬 One street read: the last 60 lines dressed (family crest · Don · receipts · reactions · @you), who is on the block, the street's vitals,
    and whether the viewer may pull lines. A signed-in viewer's read also counts as their heartbeat on this block."""
    rs = _rs()
    room_ = rs._stc.room_of(city)
    if not room_:
        raise rs.HTTPException(400, 'No such city.')
    now = rs.time.time()
    me_ = rs.primary_of(rs.session_address(session) or '') if session else ''
    me_ = me_ if me_ and viewer and rs.primary_of(viewer) == me_ else ''
    seen_ = lambda w: (rs._presence.get(w) or ('online', 0))[0] != 'invisible'   # 🟢 invisible (profile › online status) never shows on the block
    if me_ and seen_(me_):
        rs._stc.here_beat(rs._street_here, city, me_, now)
    d_ = rs._chat_load()
    fam = rs._street_fams()
    reacts_ = (rs._react_load().get('rooms') or {}).get(room_) or {}
    handles_ = [rs.handle_of(me_)] if me_ else []
    lines_ = rs._stc.dress(d_['rooms'].get(room_, [])[-60:], fam, rs._stc.receipts(rs._calls_load().get('calls'), room_), reacts_, me_ or None, handles_, rs.linked_of(me_) if me_ else ())
    here_ = rs._stc.here_list(rs._street_here, city, now, seen_)
    vf_ = fam(me_) if me_ else None
    staff_ = bool(me_) and rs._is_staff(me_)
    pin_ = rs._stc.pin_view(((d_.get('streetPins') or {}).get(room_)), lines_, now)
    v_ = rs._stc.vitals(lines_, now * 1000)
    v_['heat'] = rs._stc.heat(v_, sum(r_.get('n', 0) for l_ in lines_[-20:] for r_ in (l_.get('reacts') or {}).values()))
    slow_ = rs._stc.slow_view((d_.get('streetSlow') or {}).get(room_), now)
    wait_ = rs._stc.slow_wait((d_.get('streetSlow') or {}).get(room_), ((d_.get('streetLastAt') or {}).get(room_) or {}).get(me_), now,
                           staff_ or bool(vf_ and vf_.get('don'))) if me_ else 0
    return {'room': room_, 'lines': lines_, 'vitals': v_, 'reacts': list(rs._stc.REACTS), 'pinned': pin_,
            'hits': rs._stc.hits(rs._calls_load().get('calls'), room_, now, fam), 'slow': slow_ and {**slow_, 'wait': wait_}, 'slowChoices': list(rs._stc.SLOW_CHOICES),
            'here': [{'address': w_, 'name': rs._display_name(w_), 'fam': fam(w_)} for w_ in here_[:40]], 'hereN': len(here_),
            'typing': [rs._display_name(w_) for w_ in rs._stc.typing_list(rs._street_typing, city, now, me_ or None, seen_)[:4]],
            'mod': {'staff': staff_, 'don': bool(vf_ and vf_.get('don')), 'famId': (vf_ or {}).get('id')}, 'me': {'fam': vf_, 'handle': handles_[0] if handles_ else None} if me_ else None}


@router.post('/api/reputation/familia/street/{city}/mod')
async def familia_street_mod(city: str, p: _RSM.StreetMod):
    """🛡 Pull a line off the street (staff: any line · a Don: their own family's lines) or mute its poster for an hour (staff only). Audited."""
    rs = _rs()
    room_ = rs._stc.room_of(city)
    if not room_ or p.act not in ('pull', 'mute', 'pin', 'unpin', 'slow'):
        raise rs.HTTPException(400, 'Pull, mute or pin a line on a real street.')
    me_ = rs._session_or_401(p.address, p.session)
    fam = rs._street_fams()
    vf_ = fam(me_) or {}
    staff_ = rs._is_staff(me_)
    async with rs._chat_lock:
        d_ = rs._chat_load()
        if p.act == 'slow':   # 🐢 staff or a Don slows the street (one line per wallet every N s, lifts after 30 min; staff + Dons exempt)
            if not rs._stc.can_pin(staff_, vf_.get('don')):
                raise rs.HTTPException(403, 'Only a Don (or FEELESS staff) sets slow mode on the street.')
            if p.sec not in rs._stc.SLOW_CHOICES:
                raise rs.HTTPException(400, f'Slow mode is one of {", ".join(map(str, rs._stc.SLOW_CHOICES))} seconds.')
            sl_ = d_.setdefault('streetSlow', {})
            if p.sec:
                sl_[room_] = {'sec': p.sec, 'by': f"[{vf_.get('tag')}] {rs._display_name(me_)}" if vf_.get('tag') else rs._display_name(me_), 'at': rs.time.time()}
            else:
                sl_.pop(room_, None)
            rs.CHAT_PATH.write_text(rs.json.dumps(d_))
            ad_ = rs._admin_load(); rs._audit(ad_, me_, 'street-slow', f'{room_} {p.sec}s'); rs._admin_save(ad_)
            return {'ok': True, 'slow': rs._stc.slow_view(sl_.get(room_), rs.time.time())}
        msgs_ = d_['rooms'].get(room_, [])
        m_ = next((x for x in msgs_ if x.get('id') == p.id), None)
        if not m_:
            raise rs.HTTPException(404, 'That line is gone already.')
        lf_ = fam(m_.get('address')) or {}
        if p.act in ('pin', 'unpin'):   # 📌 staff or a Don pins one call on top of the street for an hour (the last pin wins)
            if not rs._stc.can_pin(staff_, vf_.get('don')):
                raise rs.HTTPException(403, 'Only a Don (or FEELESS staff) pins a line on the street.')
            pins_ = d_.setdefault('streetPins', {})
            if p.act == 'pin':
                pins_[room_] = {'id': p.id, 'by': f"[{vf_.get('tag')}] {rs._display_name(me_)}" if vf_.get('tag') else rs._display_name(me_), 'at': rs.time.time()}
            else:
                pins_.pop(room_, None)
            rs.CHAT_PATH.write_text(rs.json.dumps(d_))
            return {'ok': True}
        if p.act == 'mute' and not staff_:
            raise rs.HTTPException(403, 'Only FEELESS staff can mute.')
        if not rs._stc.can_pull(staff_, vf_.get('id'), vf_.get('don'), lf_.get('id')):
            raise rs.HTTPException(403, "A Don can only pull their own family's lines.")
        d_['rooms'][room_] = [x for x in msgs_ if x.get('id') != p.id]
        rs.CHAT_PATH.write_text(rs.json.dumps(d_))
    if p.act == 'mute' and staff_ and rs.primary_of(m_.get('address') or '') not in rs._admin_wallets():
        async with rs._admin_lock:
            mu_ = rs._json_load(rs.MUTES_PATH, {}); mu_[rs.primary_of(m_['address'])] = rs.time.time() + 3600; rs._json_save(rs.MUTES_PATH, mu_)
    ad_ = rs._admin_load(); rs._audit(ad_, me_, f'street-{p.act}', f"{room_} {p.id} @{rs.handle_of(rs.primary_of(m_.get('address') or ''))}: {str(m_.get('text') or '')[:80]}"); rs._admin_save(ad_)
    return {'ok': True}


@router.post('/api/reputation/admin/security/defence/lift')
async def admin_defence_lift(p: _RSM.DefenceLift, request: Request):
    rs = _rs()
    admin = rs._require_admin(request)
    rs._def.lift(rs._def_s(), p.fp or None, p.ua or None); rs._def_save(force=True)
    async with rs._admin_lock:
        d = rs._admin_load(); rs._audit(d, admin, 'defence-lift', p.fp or p.ua); rs._admin_save(d)
    return rs._def.view(rs._def_s())


@router.get('/api/reputation/admin/security/war-room')
async def admin_war_room(request: Request):
    """The live War Room: feed, timeline, decoy captures, canaries + openers, banned subnets, harden moves, bounty inbox, hardening list."""
    rs = _rs()
    rs._require_owner(request)
    v = rs._war.view(rs._war_s())
    v['hardening'] = rs._war_hard.view()
    v['encyclopedia'] = rs._war_hard.encyclopedia()
    v['bounty'] = rs._BOUNTY_SCOPE
    return v


@router.post('/api/reputation/admin/security/war-room/evidence')
async def admin_war_evidence(request: Request):
    """The evidence pack as it stands (no wallet) for an abuse / IC3 report."""
    rs = _rs()
    rs._require_owner(request)
    return {'pack': rs._war.evidence_pack(rs._war_s())}


@router.get('/api/reputation/admin/legal')
async def legal_admin(request: Request):
    """Owner: the gate switches, how many wallets accepted this version (by stated country), and the export / delete log (counts only)."""
    rs = _rs()
    rs._require_owner(request)
    return rs._legal.view(rs._legal_s())


@router.post('/api/reputation/admin/legal')
async def legal_admin_save(p: _RSM.LegalCfg, request: Request):
    rs = _rs()
    rs._require_owner(request)
    s = rs._legal_s(); s['cfg'] = rs._legal.clean_cfg(p.cfg, s['cfg']); rs._legal_save()
    return rs._legal.view(s)


@router.post('/api/reputation/admin/security/guard')
async def admin_guard_decide(payload: _RSM.GuardDecision, request: Request):
    """Every block is an admin approval (audited). The guard itself only slows floods and flags suspects."""
    rs = _rs()
    admin = rs._require_admin(request)
    try:
        rs._guard.decide(rs._guard_s(), payload.ip.strip(), payload.action, admin, note=payload.note)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    rs._guard_save()
    async with rs._admin_lock:
        d = rs._admin_load(); rs._audit(d, admin, f'guard-{payload.action}', payload.ip.strip()); rs._admin_save(d)
    return rs._guard.view(rs._guard_s())


@router.post('/api/reputation/admin/contract/golive')
async def contract_golive_set(request: Request):
    rs = _rs()
    admin = rs._require_owner(request)   # only the creator wallet can mark a real-money gate passed
    body = await request.json()
    step = str(body.get('step') or '')
    if step not in rs.GOLIVE_STEPS:
        raise rs.HTTPException(400, 'Unknown step.')
    proof = str(body.get('proof') or '')[:200]
    done = bool(body.get('done'))
    if done and step in ('devnet', 'audit', 'multisig') and not proof:
        raise rs.HTTPException(400, 'Add the proof (tx / report link / Circle authority address) before marking this passed.')
    async with rs._admin_lock:
        d = rs._admin_load(); d.setdefault('golive', {})[step] = {'done': done, 'proof': proof, 'at': rs.time.time(), 'by': admin}
        rs._audit(d, admin, 'contract-golive', f'{step} → {"passed" if done else "open"} {proof[:60]}'); rs._admin_save(d)
    return await rs.contract_golive(request)


@router.get('/api/reputation/admin/holders/ages')
async def admin_holder_ages(request: Request, asset: str = 'fee', limit: int = 150):
    rs = _rs()
    rs._require_admin(request)
    mints = await rs._ecosystem_mints()
    mint = mints.get(asset)
    if not mint:
        raise rs.HTTPException(404, 'Unknown asset.')
    data = await rs._token_holders(mint)
    rows = [r for r in data['rows'] if r.get('tokenAccount')][:max(1, min(limit, 300))]
    sem = rs.asyncio.Semaphore(6)
    out = {}
    async with rs.httpx.AsyncClient(timeout=30) as http:
        async def one(r):
            async with sem:
                out[r['owner']] = await rs._first_active(http, r['tokenAccount'])
        await rs.asyncio.gather(*(one(r) for r in rows))
    return {'asset': asset, 'since': out, 'note': 'Earliest on-chain activity of each holder\'s token account.'}


@router.post('/api/reputation/admin/snapshots')
async def admin_snapshot(request: Request, asset: str = 'fee', label: str = ''):
    rs = _rs()
    admin = rs._require_admin(request)
    mints = await rs._ecosystem_mints()
    mint = mints.get(asset)
    if not mint:
        raise rs.HTTPException(404, 'Unknown asset.')
    rs._holder_cache.pop(mint, None)
    data = await rs._token_holders(mint)
    snap = {'id': rs.uuid.uuid4().hex[:10], 'asset': asset, 'label': label[:60], 'at': rs.time.time(), 'price': data['price'],
            'rows': [[r['owner'], float(f"{r['amount']:.9g}")] for r in data['rows']]}
    async with rs._admin_lock:
        d = rs._snaps(); d['snaps'].append(snap); d['snaps'] = d['snaps'][-60:]; rs._json_save(rs.SNAP_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'snapshot', f"{asset.upper()} · {len(snap['rows'])} holders"); rs._admin_save(ad)
    return {'ok': True, 'id': snap['id'], 'holders': len(snap['rows'])}


@router.get('/api/reputation/admin/snapshots/{snap_id}/diff')
async def admin_snapshot_diff(request: Request, snap_id: str):
    rs = _rs()
    rs._require_admin(request)
    snap = next((s for s in rs._snaps()['snaps'] if s['id'] == snap_id), None)
    if not snap:
        raise rs.HTTPException(404, 'Snapshot not found.')
    mints = await rs._ecosystem_mints()
    now = {r['owner']: r['amount'] for r in (await rs._token_holders(mints[snap['asset']]))['rows']}
    then = dict((o, a) for o, a in snap['rows'])
    rows = []
    for o in set(now) | set(then):
        a, b = then.get(o, 0), now.get(o, 0)
        kind = 'new' if not a else 'exited' if not b else 'grew' if b > a * 1.01 else 'shrank' if b < a * 0.99 else 'held'
        rows.append({'owner': o, 'then': a, 'now': b, 'delta': b - a, 'kind': kind})
    rows.sort(key=lambda r: -abs(r['delta']))
    counts = {k: sum(1 for r in rows if r['kind'] == k) for k in ('new', 'exited', 'grew', 'shrank', 'held')}
    return {'snap': {k: v for k, v in snap.items() if k != 'rows'}, 'counts': counts, 'rows': rows[:500],
            'diamondHands': [r['owner'] for r in rows if r['kind'] in ('held', 'grew')]}


@router.get('/api/reputation/admin/grow/detail')
async def admin_grow_detail(request: Request, id: str = Query('', max_length=128)):
    """💰 Owner: one option's hourly points. Only a row the board itself read, so the fee and depth are the venue's, never the page's."""
    rs = _rs()
    rs._require_owner(request)
    import grow_board as _gb
    row_ = next((r_ for r_ in await rs._grow_rows() if r_['id'] == id), None)
    if not row_:
        raise rs.HTTPException(404, 'That option is not on the board any more.')
    hit_ = rs._GROW['detail'].get(id)
    if hit_:
        return hit_

    async def bars(pair_):
        r_ = await rs._fmk_http_get().get(f'http://127.0.0.1:5099/api/candles/solana/{pair_}', params={'interval': '1h'}, timeout=20)
        return r_.json().get('candles') or [] if r_.status_code == 200 else []
    try:
        if row_['kind'] == 'pool':
            own_, sol_ = await rs.asyncio.gather(bars(row_['id']), bars(rs.GROW_SOL_POOL))
            pts_, why_ = _gb.pool_points(row_, own_, sol_)
        elif row_['kind'] == 'stock':
            pts_, why_ = _gb.stock_points(await bars(row_['pair']))
        else:
            r_, sol_ = await rs.asyncio.gather(rs._fmk_http_get().get(f"https://yields.llama.fi/chart/{row_['llama']}", timeout=20), bars(rs.GROW_SOL_POOL) if row_['kind'] == 'stake' else rs.asyncio.sleep(0, []))
            pts_, why_ = _gb.lend_points(row_, (r_.json().get('data') or []) if r_.status_code == 200 else [], sol_, rs.time.time())
    except (rs.httpx.HTTPError, ValueError) as e:
        raise rs.HTTPException(502, f'Its history could not be read: {str(e)[:80]}')
    import range_sim as _rsim
    out_ = {'id': id, 'points': pts_, 'single': row_['kind'] != 'pool', 'why': why_, 'ranges': {'bands': [next(x_ for x_ in _rsim.sweep(pts_, widths=(w_,)) if x_) for w_ in _rsim.WIDTHS] if row_['kind'] == 'pool' and len(pts_) >= 30 else [], 'test': _rsim.walk_forward(pts_) if row_['kind'] == 'pool' else None}}
    rs._GROW['detail'][id] = out_
    return out_


@router.post('/api/reputation/admin/py-agents')
async def admin_py_agents_ask(request: Request):
    """🐍 Owner: one local mind reads the validators' code and record, and proposes. Free, on his own machines. Saved for him to read; nothing is applied."""
    rs = _rs()
    rs._require_owner(request)
    import py_agents as _pa
    body = await request.json() or {}
    if body.get('apply'):   # ⚖ his word: a kind moves to the weights it learned from OSSY and G4, only if they beat proofs they never saw
        sort_ = rs._json_load(rs.DATA_DIR / 'git_manifests' / 'collective_sort.json', {})
        if not _pa.apply_learned(rs.DATA_DIR, sort_, str(body['apply'])):
            raise rs.HTTPException(400, 'Those weights are not ready.')
        return {'seats': _pa.record(rs._cpool.load(rs.POOL_PATH), _pa.filed(rs._json_load(rs.DATA_DIR / 'feecats.json', {}))), 'learned': _pa.learned(rs.DATA_DIR, sort_), **_pa.load(rs.DATA_DIR)}
    who_ = 'g4' if body.get('who') == 'g4' else 'ossy'; which_ = 'LAN' if who_ == 'g4' else 'LOCAL'; base_ = (rs.os.environ.get(f'{which_}_LLM_BASE_URL') or ('http://127.0.0.1:1234/v1' if which_ == 'LOCAL' else '')).rstrip('/')
    if not base_:
        raise rs.HTTPException(400, f'{who_.upper()} has no address set.')
    auth_ = {'Authorization': f"Bearer {rs.os.environ.get(f'{which_}_LLM_API_KEY') or 'lm-studio'}"}
    try:
        async with rs.httpx.AsyncClient(timeout=600) as http:
            ids_ = [m_.get('id') for m_ in (await http.get(f'{base_}/models', headers=auth_, timeout=8)).json().get('data') or [] if 'embed' not in str(m_.get('id'))]
            r_ = await http.post(f'{base_}/chat/completions', headers=auth_, json={'model': ids_[0], 'messages': [{'role': 'system', 'content': _pa.SYS}, {'role': 'user', 'content': _pa.prompt(_pa.record(rs._cpool.load(rs.POOL_PATH)))}], 'max_tokens': 1200, 'temperature': 0.3, 'reasoning_effort': 'none'})
        rows_ = _pa.parse(r_.json()['choices'][0]['message']['content'])
    except (rs.httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise rs.HTTPException(502, f'{who_.upper()} did not answer: {str(e)[:100]}')
    if not rows_:
        raise rs.HTTPException(502, f'{who_.upper()} answered with no usable proposal. Try again.')
    return {'seats': _pa.record(rs._cpool.load(rs.POOL_PATH)), **_pa.add(rs.DATA_DIR, who_, rows_, rs.time.time())}


@router.get('/api/reputation/fees/pricing')
async def fee_pricing(coins: int = Query(3, ge=1, le=12), usd: float = Query(20, ge=0, le=1e6), rounds: int = Query(5, ge=1, le=500), wallet: str = Query('', max_length=64)):
    """Public pricing: the % fee on a normal swap, the bundle price for cards bought all at once, card swaps, round packs —
    plus `plan` = what a card of `coins` coins / $`usd` costs over `rounds` rounds (the Lab's cost receipt)."""
    rs = _rs()
    cfg = rs._fee_cfg()
    return {'swapBps': int(cfg['platformFeeBps'] or 0), 'bundle': rs._hq.clean_bundle(cfg.get('bundle')), 'rounds': {**rs._rounds_cfg(), 'payTo': await rs._rounds_pay_to()},
            'plan': rs._hq.fee_plan(cfg.get('bundle'), rs._rounds_cfg(), coins, usd, rounds),
            'prepay': rs._hq.clean_prepay(cfg.get('prepay')), 'staff': bool(wallet and rs._is_staff(wallet)),
            'choice': {'rounds': list(rs._hq.PLAN_ROUNDS), 'swaps': list(rs._hq.PLAN_SWAPS), 'free': rs._hq.ROUNDS_DEFAULT, 'step': rs._hq.ROUNDS_STEP},
            'cardLegs': {'pools': rs._hq.CARD_POOLS, 'runners': rs._hq.CARD_RUNNERS}, 'freeBuys': ['$FEE', 'FEECAT', 'rFEE']}


@router.post('/api/reputation/admin/fees/prepay')
async def admin_fees_prepay(request: Request, body: dict):
    """HQ › Fees › 💳 Prepaid swaps: $ per swap × swaps per round × rounds, paid up front with a card's first buy (owner only)."""
    rs = _rs()
    admin = rs._require_owner(request)
    async with rs._admin_lock:
        d = rs._admin_load(); pp = rs._hq.clean_prepay(body)
        d.setdefault('fees', {})['prepay'] = {k: pp[k] for k in ('on', 'perSwapUsd', 'swapsPerRound', 'rounds')}
        rs._audit(d, admin, 'fees', f"prepaid swaps {'on' if pp['on'] else 'off'} · ${pp['perSwapUsd']:.2f} × {pp['swapsPerRound']}/round × {pp['rounds']} = ${pp['usd']:.2f}")
        rs._admin_save(d)
    return {'prepay': pp}


@router.post('/api/reputation/admin/fees/bundle')
async def admin_fees_bundle(request: Request, body: dict):
    """Core › Fees › Bundle pricing: flat $ per coin for cards bought all at once (Fuse / runners)."""
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    async with rs._admin_lock:
        d = rs._admin_load()
        b = rs._hq.clean_bundle(body)
        d.setdefault('fees', {})['bundle'] = b
        rs._audit(d, admin, 'fees', f"bundle pricing {'on' if b['on'] else 'off'} · ${b['perLegUsd']:.2f}/coin · max {b['maxPct']:g}% · legs ≤ ${b['maxLegUsd']:g}")
        rs._admin_save(d)
    return {'bundle': b}


@router.post('/api/reputation/admin/fees/rounds')
async def admin_fees_rounds(request: Request, body: dict):
    """Core › Fees › 🔁 Card rounds: $ per +5 rounds, and whether a card's compound may pay for them (owner only)."""
    rs = _rs()
    admin = rs._require_owner(request)
    async with rs._admin_lock:
        d = rs._admin_load()
        r = rs._hq.clean_rounds_cfg(body)
        d.setdefault('fees', {})['rounds'] = {'per5Usd': r['per5Usd'], 'compoundPay': r['compoundPay']}
        rs._audit(d, admin, 'fees', f"card rounds · ${r['per5Usd']:.2f} per {r['step']} · compound pays {'on' if r['compoundPay'] else 'off'}")
        rs._admin_save(d)
    return {'rounds': r}


@router.post('/api/reputation/admin/fees/house')
async def admin_fees_house(request: Request, p: _RSM.HouseFees):
    """🏠 Save the house fees (audited); FeeCat's paper fee is pushed to her service right away (a failed push says so — her old fee stays)."""
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    async with rs._admin_lock:
        d = rs._admin_load()
        d.setdefault('fees', {})['house'] = p.dict()
        rs._audit(d, admin, 'fees-house', f"Fuse creator cap {p.fuseCreatorMaxBps / 100:g}% · FeeCat paper fee {p.feecatFeePct:g}%/side · {p.redeemMp:,} MP → {p.redeemFeecat:,} FEECAT")
        rs._admin_save(d)
    synced = False
    try:
        r_ = await rs._ai_http().post('http://127.0.0.1:5088/api/cats/internal/rules', headers={'x-feeless-internal': rs._internal_key()}, json={'rules': {'feePerSidePct': p.feecatFeePct}}, timeout=5)
        synced = r_.status_code == 200
    except Exception:
        synced = False
    return {'ok': True, 'house': rs._house(), 'feecatSynced': synced}


@router.get('/api/reputation/admin/fees/earnings')
async def admin_fee_earnings(request: Request):
    """Live money: what sits in the fee accounts on-chain right now, plus fees from confirmed trades
    (last hour / 24h / 7d, top coins)."""
    rs = _rs()
    rs._require_admin(request)
    cfg = rs._fee_cfg()
    accounts = [(label, acct) for label, acct in (('SOL', cfg.get('feeAccountSol')), ('USDC', cfg.get('feeAccountUsdc'))) if acct]
    async with rs.httpx.AsyncClient(timeout=15) as http:
        async def balances():
            if not accounts:
                return []
            info = await rs._rpc(http, 'getMultipleAccounts', [[a for _, a in accounts], {'encoding': 'jsonParsed'}])
            rows = []
            for (label, acct), value in zip(accounts, (info or {}).get('value') or []):
                amt = ((((value or {}).get('data') or {}).get('parsed') or {}).get('info') or {}).get('tokenAmount') or {} if isinstance((value or {}).get('data'), dict) else {}
                rows.append({'label': label, 'account': acct, 'amount': float(amt.get('uiAmountString') or 0)})
            return rows

        async def trades():
            try:
                r = await http.get('http://127.0.0.1:5001/api/trading/internal/earnings', headers={'x-feeless-internal': rs._internal_key()})
                return r.json() if r.status_code == 200 else None
            except Exception:
                return None
        bal, stats = await rs.asyncio.gather(balances(), trades())
    for c in (stats or {}).get('coins', []):
        card = rs._fee_coin_names.get(c['mint'])
        if card is None:
            async with rs.httpx.AsyncClient(timeout=6) as http:
                card = rs._fee_coin_names[c['mint']] = (await rs._coin_card(http, c['mint']))['symbol']
        c['symbol'] = card
    return {'balances': bal, 'trades': stats, 'at': rs.time.time()}


@router.get('/api/reputation/admin/shield')
async def shield_admin(request: Request, verdict: str = Query('flagged')):
    """HQ › Security › Bot shield: scan every known wallet with every engine."""
    rs = _rs()
    rs._require_admin(request)
    rows = rs._shield_scan_all()
    counts = {k: sum(1 for r in rows if r['verdict'] == k) for k in ('bot', 'watch', 'clean')}
    engines = {e.__name__: sum(1 for r in rows for h in r['hits'] if h['engine'] == e.__name__) for e in rs._shield.ENGINES}
    shown = [r for r in rows if verdict == 'all' or (verdict == 'flagged' and r['verdict'] != 'clean') or r['verdict'] == verdict]
    return {'scanned': len(rows), 'counts': counts, 'engines': engines, 'rows': sorted(shown, key=lambda r: -r['score'])[:200]}


@router.post('/api/reputation/admin/shield')
async def shield_admin_set(request: Request):
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    a, act = rs.primary_of(str(body.get('address') or '')), body.get('action')
    if act not in ('cleared', 'bot', 'reset') or not a:
        raise rs.HTTPException(400, 'address + cleared | bot | reset')
    async with rs._admin_lock:
        d = rs._json_load(rs.SHIELD_PATH, {})
        m = d.setdefault('manual', {})
        if act == 'reset':
            m.pop(a, None)
        else:
            m[a] = act
        rs._json_save(rs.SHIELD_PATH, d)
    rs._shield_cache.pop(a, None); rs._case_cache.pop(a, None)
    ad = rs._admin_load(); rs._audit(ad, admin, f'shield-{act}', a); rs._admin_save(ad)
    return {'ok': True}


@router.post('/api/reputation/admin/fees')
async def admin_fees_set(request: Request, payload: _RSM.FeeCfg):
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    addr = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
    if payload.engine not in ('swap', 'ultra'):
        raise rs.HTTPException(400, 'Engine must be swap or ultra.')
    for label, v in (('Referral account', payload.referralAccount), ('SOL fee account', payload.feeAccountSol), ('USDC fee account', payload.feeAccountUsdc)):
        if v and not rs._re.match(addr, v):
            raise rs.HTTPException(400, f'{label} must be a Solana address.')
    uses_ultra = payload.engine == 'ultra' or payload.ultraFallback
    if payload.platformFeeBps and payload.engine == 'swap' and not (payload.feeAccountSol or payload.feeAccountUsdc):
        raise rs.HTTPException(400, 'Add a SOL (wSOL) or USDC fee token account: the Swap API pays your fee into it.')
    if payload.platformFeeBps and uses_ultra and not payload.referralAccount:
        raise rs.HTTPException(400, 'Ultra needs a Jupiter referral account (referral.jup.ag) to pay your fee.')
    if payload.engine == 'ultra' and payload.platformFeeBps and not rs.JUP_MIN_BPS <= payload.platformFeeBps <= rs.JUP_MAX_BPS:
        raise rs.HTTPException(400, f'Ultra charges {rs.JUP_MIN_BPS}–{rs.JUP_MAX_BPS} bps (0.5–2.55%). Use the Swap engine for other fees.')
    # Discounts lower the fee, never remove it: at most 90% off.
    tiers = {str(k): max(0.0, min(90.0, float(v))) for k, v in (payload.tierDiscountPct or {}).items() if str(k) in ('0', '1', '2', '3')}
    zero = []  # no fee-free list: only FEELESS coin buys are exempt (see effective_fee)
    promo = {'label': str((payload.promo or {}).get('label') or '')[:40], 'discountPct': max(0.0, min(90.0, float((payload.promo or {}).get('discountPct') or 0))),
             'until': float((payload.promo or {}).get('until') or 0)}
    integrator = (payload.lifiIntegrator or '').strip() or rs.os.environ.get('LIFI_INTEGRATOR', '').strip()
    if integrator and not rs._re.match(r'^[A-Za-z0-9_.-]{2,40}$', integrator):
        raise rs.HTTPException(400, 'LI.FI integrator name: 2–40 letters, numbers, dot, dash or underscore (as registered at portal.li.fi).')
    if payload.lifiFeeBps and not integrator:
        raise rs.HTTPException(400, 'Register an integrator at portal.li.fi and enter its name before setting a LI.FI fee.')
    async with rs._admin_lock:
        d = rs._admin_load()
        d['fees'] = {'platformFeeBps': payload.platformFeeBps, 'referralAccount': payload.referralAccount, 'tierDiscountPct': tiers, 'zeroFeeMints': zero, 'promo': promo,
                     'lifiIntegrator': integrator, 'lifiFeeBps': payload.lifiFeeBps if integrator else 0,
                     'engine': payload.engine, 'ultraFallback': payload.ultraFallback, 'feeAccountSol': payload.feeAccountSol,
                     'feeAccountUsdc': payload.feeAccountUsdc, 'priorityMaxLamports': payload.priorityMaxLamports,
                     'vaultFeeWallet': payload.vaultFeeWallet, 'catMaxModels': payload.catMaxModels, 'catFeeUsd': payload.catFeeUsd, 'agentTradeFeeUsd': payload.agentTradeFeeUsd, 'agentOtherFeeUsd': payload.agentOtherFeeUsd, 'catMinUsd': max(payload.catMinUsd, payload.catFeeUsd + 1), **{k: v for k, v in (d.get('fees') or {}).items() if k in ('bundle', 'rounds', 'prepay', 'crews', 'house')}}
        tier_txt = ' / '.join(f"{float(tiers.get(k, 0)):g}%" for k in ('0', '1', '2', '3'))
        rs._audit(d, admin, 'fees', f"{'Swap API' if payload.engine == 'swap' else 'Ultra'} · fee {payload.platformFeeBps / 100:.2f}% · Ultra fallback {'on' if payload.ultraFallback else 'off'} · "
                                 f"holder discounts {tier_txt} · promo {promo['discountPct']:.0f}% · speed tip ≤ {payload.priorityMaxLamports / 1e9:.4f} SOL")
        rs._admin_save(d)
    return {'ok': True, 'fees': rs._fee_cfg()}


@router.get('/api/reputation/admin/referrals')
async def admin_referrals(request: Request):
    rs = _rs()
    rs._require_admin(request)
    d = rs._json_load(rs.REF_PATH, {'by': {}, 'of': {}})
    earn = rs._json_load(rs.REF_EARN_PATH, {})
    rows = sorted(({'address': a, 'handle': rs.handle_of(a), 'invited': len(v), 'earnedUsd': (earn.get(a) or {}).get('usd', 0), 'earnedSol': (earn.get(a) or {}).get('sol', 0)}
                   for a, v in d['by'].items()), key=lambda r: (-r['earnedUsd'], -r['invited']))
    return {'total': len(d['of']), 'top': rows[:50], 'pct': float(rs._json_load(rs.REF_CFG_PATH, {}).get('pct') or 0),
            'owedUsd': round(sum((r.get('usd') or 0) - (r.get('paidUsd') or 0) for r in earn.values()), 4)}


@router.put('/api/reputation/admin/referrals/config')
async def admin_referral_cfg(request: Request, p: _RSM.RefCfgIn):
    """Every inviter earns this % of the FEELESS fees their invitees pay (accrues on each confirmed trade)."""
    rs = _rs()
    me = rs._require_owner(request)
    rs._json_save(rs.REF_CFG_PATH, {'pct': round(p.pct, 2), 'by': me, 'at': rs.time.time()})
    ad = rs._admin_load(); rs._audit(ad, me, 'referral-pct', f'{p.pct}% of invitee fees'); rs._admin_save(ad)
    return {'pct': round(p.pct, 2)}


@router.post('/api/reputation/admin/ads')
async def admin_ad_save(request: Request, payload: _RSM.AdIn):
    rs = _rs()
    admin = rs._require_admin(request)
    if payload.placement not in rs.AD_PLACEMENTS:
        raise rs.HTTPException(400, 'Unknown placement.')
    url = payload.url if payload.url.startswith('https://') or payload.url.startswith('/') else ''
    ad = {'id': payload.id or rs.uuid.uuid4().hex[:10], 'title': payload.title, 'text': payload.text, 'url': url, 'imageUrl': rs._safe_url(payload.imageUrl),
          'placement': payload.placement, 'startsAt': payload.startsAt, 'endsAt': payload.endsAt, 'active': payload.active, 'sponsor': payload.sponsor}
    async with rs._admin_lock:
        d = rs._json_load(rs.ADS_PATH, {'ads': []})
        old = next((a for a in d['ads'] if a['id'] == ad['id']), None)
        if old:
            ad['views'], ad['clicks'] = old.get('views', 0), old.get('clicks', 0)
            d['ads'] = [ad if a['id'] == ad['id'] else a for a in d['ads']]
        else:
            d['ads'].append(ad)
        rs._json_save(rs.ADS_PATH, d)
        ad_log = rs._admin_load(); rs._audit(ad_log, admin, 'ad', f"{ad['title']} · {ad['placement']} · {'on' if ad['active'] else 'off'}"); rs._admin_save(ad_log)
    return {'ok': True, 'ad': ad}


@router.delete('/api/reputation/admin/ads/{ad_id}')
async def admin_ad_delete(request: Request, ad_id: str):
    rs = _rs()
    rs._require_admin(request)
    async with rs._admin_lock:
        d = rs._json_load(rs.ADS_PATH, {'ads': []})
        d['ads'] = [a for a in d['ads'] if a['id'] != ad_id]
        rs._json_save(rs.ADS_PATH, d)
    return {'ok': True}


@router.get('/api/reputation/admin/pulse')
async def admin_pulse(request: Request):
    rs = _rs()
    rs._require_admin(request)
    now = rs.time.time() * 1000
    rooms = rs._chat_load()['rooms']
    msgs = [m for ms in rooms.values() for m in ms if isinstance(m, dict)]
    last24 = [m for m in msgs if now - m.get('ts', 0) < 86400e3]
    hourly = [0] * 24
    for m in last24:
        hourly[23 - min(23, int((now - m['ts']) // 3600e3))] += 1
    busiest = sorted(((r, sum(1 for m in ms if now - m.get('ts', 0) < 86400e3)) for r, ms in rooms.items()), key=lambda x: -x[1])[:8]
    posters = {}
    for m in last24:
        if not m.get('system'):
            posters[m.get('identity') or m.get('address')] = posters.get(m.get('identity') or m.get('address'), 0) + 1
    profiles = rs._profiles_load()['profiles']
    fee = {}
    try:
        async with rs.httpx.AsyncClient(timeout=6) as http:
            fee = (await http.get('http://127.0.0.1:5088/api/cats/leader')).json().get('cat') or {}
    except Exception:
        pass
    clicks = sorted(rs._json_load(rs.CLICKS_PATH, {}).items(), key=lambda kv: -kv[1][0])[:6]
    return {'messages24h': len(last24), 'hourly': hourly, 'activeWallets24h': len(posters), 'profiles': len(profiles),
            'newProfiles24h': sum(1 for v in profiles.values() if rs.time.time() - (v or {}).get('updatedAt', 0) < 86400),
            'busiestRooms': [{'room': r, 'messages': n} for r, n in busiest if n],
            'topPosters': [{'address': a, 'handle': rs.handle_of(a), 'messages': n} for a, n in sorted(posters.items(), key=lambda x: -x[1])[:8]],
            'fee': {k: fee.get(k) for k in ('balanceSol', 'realizedPnlSol', 'winRate', 'wins', 'losses')} | {'open': len(fee.get('positions') or [])},
            'topClicks': [{'key': k, 'count': v[0]} for k, v in clicks],
            'pushSubscribers': len(rs._push_load()['subs']), 'muted': sum(1 for v in rs._json_load(rs.MUTES_PATH, {}).values() if v > rs.time.time())}


@router.get('/api/reputation/admin/chat-feed')
async def admin_chat_feed(request: Request, limit: int = 80):
    rs = _rs()
    rs._require_admin(request)
    msgs = [m for r, ms in rs._chat_load()['rooms'].items() for m in ms if isinstance(m, dict) and not m.get('system') and not rs._OPS_PING.search(str(m.get('text') or ''))]
    msgs.sort(key=lambda m: -m.get('ts', 0))
    mutes = rs._json_load(rs.MUTES_PATH, {})
    return {'messages': [{**{k: m.get(k) for k in ('id', 'room', 'address', 'username', 'handle', 'text', 'ts')}, 'muted': mutes.get(rs.primary_of(m.get('address', '')), 0) > rs.time.time()} for m in msgs[:max(1, min(limit, 300))]]}


@router.post('/api/reputation/admin/moderate/delete')
async def admin_delete_msg(request: Request, payload: _RSM.ModIn):
    rs = _rs()
    admin = rs._require_admin(request)
    async with rs._chat_lock:
        d = rs._chat_load()
        before = len(d['rooms'].get(payload.room, []))
        d['rooms'][payload.room] = [m for m in d['rooms'].get(payload.room, []) if m['id'] != payload.id]
        rs.CHAT_PATH.write_text(rs.json.dumps(d))
    ad = rs._admin_load(); rs._audit(ad, admin, 'mod-delete', f'{payload.room} #{payload.id}'); rs._admin_save(ad)
    return {'ok': before != len(d['rooms'].get(payload.room, []))}


@router.post('/api/reputation/admin/moderate/mute')
async def admin_mute(request: Request, payload: _RSM.ModIn):
    rs = _rs()
    admin = rs._require_admin(request)
    target = rs.primary_of(payload.address)
    if rs._is_staff(target):
        raise rs.HTTPException(400, "Can't mute the HQ wallet.")
    async with rs._admin_lock:
        d = rs._json_load(rs.MUTES_PATH, {})
        d[target] = rs.time.time() + max(0, min(payload.hours, 24 * 30)) * 3600 if payload.hours > 0 else 0
        rs._json_save(rs.MUTES_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, admin, 'mute' if payload.hours > 0 else 'unmute', f'@{rs.handle_of(target)} {payload.hours:g}h'); rs._admin_save(ad)
    return {'ok': True, 'until': d[target]}


@router.get('/api/reputation/admin/feecat')
async def admin_feecat_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    async with rs.httpx.AsyncClient(timeout=10) as http:
        r = await http.get('http://127.0.0.1:5088/api/cats/internal/rules', headers={'x-feeless-internal': rs._internal_key()})
        prof = (await http.get('http://127.0.0.1:5088/api/cats/leader/profile')).json()
        activity = (await http.get('http://127.0.0.1:5088/api/cats/activity?catId=leader')).json()
    st_fc = rs._json_load(rs.DATA_DIR / 'feecats.json', {}) or {}
    sc_ = st_fc.get('scan') or {}   # 🔎 why she is / isn't trading: her own last scan (scanned → passed → rejections)
    return {**r.json(), 'learning': prof.get('learning'), 'stats': prof.get('stats'), 'events': (activity.get('events') or [])[:30],
            'duoLearn': st_fc.get('duoLearn') or {},   # 🎓 what she takes from OSSY / G4: their record + final-review lessons
            'discipline': prof.get('discipline'), 'strength': prof.get('strength'), 'exits': (prof.get('exits') or [])[-12:],
            'pins': rs._feecat_pins((prof.get('cat') or {}).get('positions') or [], sc_.get('top') or []),   # 🤖🔁 the agents' + OSSY / G4's word on HER coins (HQ only)
            'scan': {k: sc_.get(k) for k in ('at', 'scanned', 'passed', 'rejections', 'top', 'brainRejects', 'safetyRejects')},
            'duo': {k: rs._feecat_ai.get(k) for k in ('read', 'avoid', 'exit', 'split', 'why', 'models')},   # 🤝 her one duo AI read per 10 min
            'cat': {**{k: (prof.get('cat') or {}).get(k) for k in ('balanceSol', 'startingBalanceSol', 'realizedPnlSol', 'winRate', 'wins', 'losses', 'status', 'lastTick', 'positions', 'pnlHistory', 'level', 'xp')},
                    # 👛 her wallet panel reads these: the slim record above had none, so the wallet you'd just assigned vanished on the next 6 s poll (owner 2026-10-31)
                    **{k: ((st_fc.get('cats') or {}).get('leader') or {}).get(k) for k in ('id', 'name', 'isLeader', 'agentWallet', 'mode', 'realWallet', 'budgetSol', 'proposals', 'agentFunded', 'revoked')}},
            'fastTrench': rs._feecat_fast_trench()}


@router.post('/api/reputation/admin/feecat')
async def admin_feecat_set(request: Request):
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    action = body.pop('action', None)
    async with rs.httpx.AsyncClient(timeout=30) as http:
        if action == 'run':
            run = await http.post('http://127.0.0.1:5088/api/cats/leader/action', headers={'x-feeless-internal': rs._internal_key()}, json={'action': 'run'})
            if run.status_code != 200:
                raise rs.HTTPException(run.status_code, 'Fee service could not run the intelligence cycle.')
        r = await http.post('http://127.0.0.1:5088/api/cats/internal/rules', headers={'x-feeless-internal': rs._internal_key()}, json=body)
    if r.status_code != 200:
        raise rs.HTTPException(r.status_code, 'Fee service rejected the change.')
    ad = rs._admin_load(); rs._audit(ad, admin, 'feecat', rs.json.dumps({k: v for k, v in body.items() if k != 'rules'} | {'rules': list((body.get('rules') or {}).keys())})[:160]); rs._admin_save(ad)
    return r.json()


@router.post('/api/reputation/dm')
async def dm_send(payload: _RSM.DmIn):
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    to = rs.primary_of(payload.to)
    if not rs._re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', to) or to == me:
        raise rs.HTTPException(400, 'Pick another wallet to message.')
    if rs.is_muted(me):
        raise rs.HTTPException(403, 'You are muted for now.')
    if rs.time.time() - rs._dm_last.get(me, 0) < 2:
        raise rs.HTTPException(429, 'Slow down.')
    pref = rs._dm_pref(to)
    thread = rs._json_load(rs.DM_PATH, {}).get(rs._dm_key(me, to), [])
    replied = any(m['from'] == to for m in thread)  # they've written to me: the thread is open both ways
    is_admin = rs._is_staff(me)
    request = False
    if not is_admin and not replied and me not in pref['accepted']:
        if pref['policy'] == 'nobody':
            raise rs.HTTPException(403, "This wallet isn't accepting messages.")
        if pref['policy'] == 'requests':
            if thread:
                raise rs.HTTPException(403, 'Your message request is waiting — you can write again once they accept.')
            request = True
    rs._dm_last[me] = rs.time.time()
    msg = {'id': rs.uuid.uuid4().hex[:12], 'from': me, 'to': to, 'text': payload.text.strip(), 'at': rs.time.time(), **({'request': True} if request else {})}
    async with rs._admin_lock:
        d = rs._json_load(rs.DM_PATH, {})
        d.setdefault(rs._dm_key(me, to), []).append(msg)
        d[rs._dm_key(me, to)] = d[rs._dm_key(me, to)][-300:]
        rs._json_save(rs.DM_PATH, d)
    rs.notify(to, 'dm', f"{'📨 Message request from ' if request else ''}@{rs.handle_of(me)}: {payload.text.strip()}", f'/terminal/profile/{to}?dm=1', me)
    return {'ok': True, 'message': msg}


@router.post('/api/reputation/admin/verify')
async def admin_verify(request: Request, payload: _RSM.ModIn):
    rs = _rs()
    admin = rs._require_admin(request)
    a = rs.primary_of(payload.address)
    async with rs._admin_lock:
        d = rs._admin_load()
        v = set(d.get('verified') or [])
        v.add(a) if payload.hours >= 0 else v.discard(a)
        d['verified'] = sorted(v)
        rs._audit(d, admin, 'verify' if payload.hours >= 0 else 'unverify', f'@{rs.handle_of(a)}')
        rs._admin_save(d)
    return {'ok': True, 'verified': rs.is_verified(a)}


@router.post('/api/reputation/admin/site')
async def admin_site(request: Request, payload: _RSM.SiteIn):
    rs = _rs()
    admin = rs._require_admin(request)
    url = payload.publicUrl.strip().rstrip('/')
    if url and not rs._re.match(r'^https://[a-z0-9.-]+\.[a-z]{2,}(/[\w./-]*)?$', url, rs._re.I):
        raise rs.HTTPException(400, 'Use your public https:// domain (e.g. https://feeless.app).')
    async with rs._admin_lock:
        d = rs._admin_load(); d['site'] = {'publicUrl': url}; rs._audit(d, admin, 'site-url', url or '(cleared)'); rs._admin_save(d)
    hook = await rs.sync_helius_webhook(url) if url else {'ok': False, 'reason': 'No domain'}
    return {'ok': True, 'publicUrl': url, 'webhook': hook}


@router.get('/api/reputation/theme/{address}')
async def theme_get(address: str):
    rs = _rs()
    a = rs.primary_of(address)
    held = await rs._eco_holding_usd(a)
    saved = rs._themes().get(a)
    if held >= rs.POOL_BUILDER_MIN_USD:
        seen = rs._json_load(rs.DATA_DIR / 'perk_notices.json', {})
        if not seen.get(a):
            seen[a] = rs.time.time(); rs._json_save(rs.DATA_DIR / 'perk_notices.json', seen)
            rs.notify(a, 'perk', f'🏗 Pool builder unlocked — you hold ${held:,.0f} of $FEE coins. Open your profile to build pools.', f'/terminal/profile/{a}', a)
    staff = rs._is_staff(a)   # the creator / admin wallets always get their colors
    ok = staff or held >= rs.THEME_MIN_USD
    worn = rs._looks.wear((saved or {}).get('look'), ok) if saved else None   # 🎨 a free look anyone may wear; an advanced one only while unlocked
    theme = ({**saved, 'look': worn} if ok else ({'look': worn} if worn else None)) if saved else None
    return {'address': a, 'holdingUsd': held, 'poolBuilder': held >= rs.POOL_BUILDER_MIN_USD, 'minUsd': rs.THEME_MIN_USD, 'eligible': ok, 'staff': staff,
            'theme': theme}


@router.get('/api/reputation/looks')
async def looks_catalog(address: str = ''):
    """🎨 Every look's card; the full colour set of an ADVANCED look only for a wallet that unlocked it (staff, or $1,000+ across $FEE coins)."""
    rs = _rs()
    a = rs.primary_of(address) if address else ''
    ok = bool(a) and (rs._is_staff(a) or (await rs._eco_holding_usd(a)) >= rs.THEME_MIN_USD)
    return {'looks': rs._looks.catalog(ok), 'eligible': ok, 'minUsd': rs.THEME_MIN_USD, 'default': rs._looks.DEFAULT}


@router.post('/api/reputation/theme')
async def theme_set(p: _RSM.ThemePayload):
    rs = _rs()
    if rs.primary_of(rs.session_address(p.session) or '') != rs.primary_of(p.address):
        raise rs.HTTPException(401, 'Sign in again to change your theme.')
    for c in (p.accent, p.accent2, p.logo):
        if c is not None and not rs._HEX.match(c):
            raise rs.HTTPException(400, 'Colors must be #RRGGBB.')
    a = rs.primary_of(p.address)
    held = await rs._eco_holding_usd(a); ok = held >= rs.THEME_MIN_USD or rs._is_staff(a)
    if p.look is not None and p.accent is None:   # 🎨 a look: the four free ones for anyone signed in, the advanced ones once unlocked
        worn = rs._looks.wear(p.look, ok)
        if not worn:
            raise rs.HTTPException(403 if p.look in rs._looks.LOOKS else 400, f'That look unlocks at ${rs.THEME_MIN_USD:,.0f} held across $FEE coins (you hold ${held:,.2f}).' if p.look in rs._looks.LOOKS else 'No such look.')
        row = {'look': p.look, 'at': rs.time.time()}; rs._themes().put(a, row)
        return {'ok': True, 'theme': {**row, 'look': worn}}
    if not p.accent:
        raise rs.HTTPException(400, 'Pick a look or a colour.')
    if not ok:
        raise rs.HTTPException(403, f'Custom site colors unlock at ${rs.THEME_MIN_USD:,.0f} held across $FEE coins (you hold ${held:,.2f}).')
    row = {'accent': p.accent, 'accent2': p.accent2 or p.accent, 'logo': p.logo or p.accent, 'at': rs.time.time()}
    rs._themes().put(a, row)
    return {'ok': True, 'theme': row}


@router.post('/api/reputation/admin/kols')
async def admin_kol_add(request: Request, p: _RSM.KolPayload):
    rs = _rs()
    admin = rs._require_admin(request)
    if p.chain != 'solana' or not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.address):
        raise rs.HTTPException(400, 'KOL tracking reads Solana wallets — enter a valid Solana address.')
    d = rs._json_load(rs.KOLS_PATH, {})
    d[p.address] = {'name': p.name[:40], 'x': (p.x or '').lstrip('@')[:30], 'chain': p.chain, 'addedBy': admin, 'at': rs.time.time()}
    rs._json_save(rs.KOLS_PATH, d)
    return {'ok': True}


@router.delete('/api/reputation/admin/kols/{address}')
async def admin_kol_remove(request: Request, address: str):
    rs = _rs()
    rs._require_admin(request)
    d = rs._json_load(rs.KOLS_PATH, {}); d.pop(address, None); rs._json_save(rs.KOLS_PATH, d)
    return {'ok': True}


@router.get('/api/reputation/admin/traffic')
async def admin_traffic(request: Request):
    rs = _rs()
    rs._require_admin(request)
    d = rs._json_load(rs.TRAFFIC_PATH, {'views': {}, 'uniques': {}, 'coins': {}, 'refs': {}, 'hours': {}})
    days = sorted(d['views'])[-14:]
    def top(pages_by_day, n=12):
        agg = {}
        for day in pages_by_day:
            for pg, c in d['views'].get(day, {}).items():
                agg[pg] = agg.get(pg, 0) + c
        return sorted(({'page': k, 'views': v} for k, v in agg.items()), key=lambda x: -x['views'])[:n]
    return {'daily': [{'day': k, 'views': sum(d['views'][k].values()), 'uniques': d['uniques'].get(k, 0)} for k in days],
            'topPages24h': top(days[-1:]), 'topPages7d': top(days[-7:]),
            'topCoins': sorted(({'pair': k, 'views': v} for k, v in d['coins'].items()), key=lambda x: -x['views'])[:12],
            'referrers': sorted(({'host': k, 'visits': v} for k, v in d['refs'].items()), key=lambda x: -x['visits'])[:10],
            'hours': [d['hours'].get(str(h), 0) for h in range(24)], 'topClicks': (await rs.top_clicks(limit=10))['rows']}


@router.post('/api/reputation/admin/seasons')
async def admin_season_upsert(request: Request, p: _RSM.SeasonPayload):
    rs = _rs()
    admin = rs._require_admin(request)
    if p.end <= p.start or p.end - p.start > 120 * 86400 or not rs._re.match(r'^#[0-9a-fA-F]{6}$', p.accent) or not (0.5 <= p.multiplier <= 5):
        raise rs.HTTPException(400, 'Invalid season (end after start, ≤120 days, #hex accent, multiplier 0.5–5).')
    d = rs._seasons()
    if any(not (p.end <= s['start'] or p.start >= s['end']) for s in d['seasons']):
        raise rs.HTTPException(409, 'Seasons cannot overlap.')
    sid = f"s{len(d['seasons']) + 1}"
    if p.reserveWallet and not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.reserveWallet):
        raise rs.HTTPException(400, 'Fee Reserve wallet must be a valid Solana address.')
    d['seasons'].append({'id': sid, 'name': p.name[:40], 'theme': p.theme[:160], 'start': p.start, 'end': p.end, 'prize': p.prize[:160],
                         'multiplier': p.multiplier, 'accent': p.accent, 'reserveWallet': p.reserveWallet,
                         'badgeRewardPct': p.badgeRewardPct, 'createdBy': admin})
    rs._json_save(rs.SEASONS_PATH, d)
    return {'ok': True, 'id': sid}


@router.post('/api/reputation/admin/roles')
async def admin_role_grant(request: Request, p: _RSM.RolePayload):
    rs = _rs()
    me = rs._require_admin(request)
    if me not in rs._owner_wallets():
        raise rs.HTTPException(403, 'Only the FEELESS owner wallet can grant HQ access.')
    if p.role not in rs.ROLE_NAMES or not (rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.address) or rs._re.match(r'^0x[0-9a-fA-F]{40}$', p.address)):
        raise rs.HTTPException(400, 'Valid wallet + role (admin, moderator, marketing) required.')
    # The creator signs THIS grant (wallet, role, time) — a leaked HQ session alone can never hand out access.
    if abs(rs.time.time() - p.ts) > 600 or not rs._verify_wallet(me, rs.grant_message(p.address, p.role, p.ts), p.sig):
        raise rs.HTTPException(401, 'Sign the grant with the owner wallet (signature missing, expired or wrong).')
    d = rs._json_load(rs.ROLES_PATH, {'grants': {}})
    d['grants'][p.address] = {'role': p.role, 'by': me, 'at': rs.time.time(), 'sig': p.sig[:120]}
    rs._json_save(rs.ROLES_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'role-grant', f'{p.address[:6]}… → {p.role}'); rs._admin_save(ad)
    return {'ok': True}


@router.delete('/api/reputation/admin/roles/{address}')
async def admin_role_revoke(request: Request, address: str):
    rs = _rs()
    me = rs._require_admin(request)
    if me not in rs._owner_wallets():
        raise rs.HTTPException(403, 'Only the owner wallet can revoke access.')
    d = rs._json_load(rs.ROLES_PATH, {'grants': {}}); d['grants'].pop(address, None); rs._json_save(rs.ROLES_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'role-revoke', address[:10]); rs._admin_save(ad)
    return {'ok': True}


@router.post('/api/reputation/admin/ideas')
async def admin_idea_add(request: Request, p: _RSM.IdeaPayload):
    rs = _rs()
    me = rs._require_admin(request)
    d = rs._json_load(rs.IDEAS_PATH, {'ideas': list(rs._IDEA_SEED)})
    d['ideas'].insert(0, {'id': rs.uuid.uuid4().hex[:8], 'title': p.title[:80], 'body': p.body[:1000], 'status': p.status[:20], 'by': me, 'at': rs.time.time()})
    rs._json_save(rs.IDEAS_PATH, d)
    return {'ok': True}


@router.put('/api/reputation/admin/seasons/{sid}')
async def admin_season_edit(request: Request, sid: str, p: _RSM.SeasonEdit):
    rs = _rs()
    admin = rs._require_admin(request)
    d = rs._seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
    if not s:
        raise rs.HTTPException(404, 'Season not found.')
    new = {**s, **{k: v for k, v in p.dict().items() if v is not None and k != 'weeks'}}
    if new['end'] <= new['start'] or new['end'] - new['start'] > 120 * 86400 or not rs._re.match(r'^#[0-9a-fA-F]{6}$', new['accent']) or not (0.5 <= float(new['multiplier']) <= 5):
        raise rs.HTTPException(400, 'Invalid season (end after start, ≤120 days, #hex accent, multiplier 0.5–5).')
    if any(x['id'] != sid and not (new['end'] <= x['start'] or new['start'] >= x['end']) for x in d['seasons']):
        raise rs.HTTPException(409, 'Seasons cannot overlap.')
    if not all(rs._is_upload_url(new.get(k)) for k in ('bannerUrl', 'badgeUrl')):
        raise rs.HTTPException(400, 'Upload images through FEELESS (png, jpg, webp or gif).')
    if new.get('bgFx') not in (None, 'money', 'snow', 'leaves', 'fire', 'stars', 'none'):
        raise rs.HTTPException(400, 'Unknown background effect.')
    if new.get('accent2') and not rs._re.match(r'^#[0-9a-fA-F]{6}$', new['accent2']):
        raise rs.HTTPException(400, 'Second color must be #hex.')
    if new.get('reserveWallet') and not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', new['reserveWallet']):
        raise rs.HTTPException(400, 'Fee Reserve wallet must be a valid Solana address.')
    if p.weeks is not None:
        clean = {}
        for wk, ov in list(p.weeks.items())[:20]:
            if not str(wk).isdigit() or not isinstance(ov, dict) or not rs._is_upload_url(ov.get('imageUrl')):
                raise rs.HTTPException(400, f'Bad week {wk} override.')
            clean[str(int(wk))] = {k: str(ov[k])[:200] for k in ('name', 'glyph', 'story', 'imageUrl') if ov.get(k)}
        new['weeks'] = clean
    new['name'] = new['name'][:40]; new['theme'] = new.get('theme', '')[:160]; new['prize'] = new.get('prize', '')[:160]
    d['seasons'] = [new if x['id'] == sid else x for x in d['seasons']]
    rs._json_save(rs.SEASONS_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, admin, 'season-edit', sid); rs._admin_save(ad)
    return {'ok': True, 'season': new}


@router.delete('/api/reputation/admin/seasons/{sid}')
async def admin_season_delete(request: Request, sid: str):
    rs = _rs()
    admin = rs._require_admin(request)
    d = rs._seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
    if not s:
        raise rs.HTTPException(404, 'Season not found.')
    if s['start'] <= rs.time.time() and d['scores'].get(sid):
        raise rs.HTTPException(409, 'This season already has players — end it early by editing its end date instead.')
    d['seasons'] = [x for x in d['seasons'] if x['id'] != sid]
    rs._json_save(rs.SEASONS_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, admin, 'season-delete', sid); rs._admin_save(ad)
    return {'ok': True}


@router.get('/api/reputation/admin/is-admin/{address}')
async def is_admin(address: str):
    """Public yes/no so the UI can show admin controls. Every admin action still needs a signed session."""
    rs = _rs()
    try:
        staff_ = bool(rs._is_staff(address))
    except Exception:
        staff_ = False
    return {'admin': address in rs._admin_wallets(), 'owner': address in rs._owner_wallets(), 'staff': staff_}   # staff = the creator via ANY linked wallet


@router.post('/api/reputation/local/update')
async def local_update(request: Request):
    """One-click update from the footer, for the machine running FEELESS itself: runs scripts/update.sh detached
    (it restarts this service). Refused from anywhere but localhost, so a public site can never be poked."""
    rs = _rs()
    origin = (request.headers.get('origin') or '').lower()
    if not rs._guard.is_local(request) or (origin and not rs._re.match(r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$', origin)):
        raise rs.HTTPException(403, 'Updates can only be started on the machine running FEELESS.')
    rs._require_admin(request)   # 🔒 2026-11-11: the dev server proxies every LAN call from 127.0.0.1 (and curl sends no Origin), so localhost alone was not proof
    root = rs.Path(__file__).resolve().parents[1]
    log_path = rs.DATA_DIR / 'feeless-update.log'   # 🔒 audit B: never a predictable /tmp path (a planted symlink)
    log = open(log_path, 'w')
    await rs.asyncio.create_subprocess_exec('bash', str(root / 'scripts' / 'update.sh'), cwd=str(root), stdout=log, stderr=log, start_new_session=True)
    rs._version_cache.clear()
    return {'ok': True, 'log': str(log_path)}


@router.put('/api/reputation/admin/treasury/routes')
async def routes_set(request: Request, p: _RSM.RoutesPayload):
    rs = _rs()
    me = rs._require_admin(request)
    if me not in rs._owner_wallets():
        raise rs.HTTPException(403, 'Only the FEELESS owner wallet can change treasury routing.')
    clean = []
    for r in p.routes[:10]:
        addr = str(r.get('address', '')).strip(); pct = float(r.get('pct') or 0)
        if not (rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', addr) or rs._re.match(r'^0x[0-9a-fA-F]{40}$', addr)) or not (0 < pct <= 100):
            raise rs.HTTPException(400, 'Each route needs a valid wallet address and a % between 0 and 100.')
        clean.append({'label': str(r.get('label', ''))[:40], 'address': addr, 'pct': round(pct, 2)})
    if clean and abs(sum(r['pct'] for r in clean) - 100) > 0.01:
        raise rs.HTTPException(400, 'Route percentages must add up to 100%.')
    rs._json_save(rs.ROUTES_PATH, {'routes': clean, 'updatedBy': me, 'at': rs.time.time()})
    ad = rs._admin_load(); rs._audit(ad, me, 'treasury-routes', f"{len(clean)} routes"); rs._admin_save(ad)
    return {'ok': True, 'routes': clean}


@router.put('/api/reputation/admin/launch-costs')
async def launch_costs_set(request: Request, p: _RSM.LaunchCostsIn):
    """Owner/admin: slippage + priority fee for pump.fun launches and priority fee for FEELESS / House launches.
    Stored beside the launch rules (nothing else in that file changes)."""
    rs = _rs()
    me = rs._require_admin(request)
    d = rs._json_load(rs.LAUNCH_RAIL_PATH, {}); d['costs'] = rs.launch_meta.clean_costs(p.model_dump()); rs._json_save(rs.LAUNCH_RAIL_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'launch-costs', ', '.join(f'{k} {v}' for k, v in d['costs'].items())); rs._admin_save(ad)
    return d['costs']


@router.put('/api/reputation/admin/launch-tab')
async def launch_tab_set(request: Request, p: _RSM.LaunchTabIn):
    """Owner picks what the public Launch tab offers. Owners themselves always see every rail."""
    rs = _rs()
    me = rs._require_owner(request)
    d = rs._json_load(rs.LAUNCH_RAIL_PATH, {}); d['tab'] = rs.launch_meta.clean_tab(p.model_dump()); rs._json_save(rs.LAUNCH_RAIL_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'launch-tab', f"rails {','.join(d['tab']['rails'])} · first buy {'≤ ' + str(d['tab']['maxDevBuySol']) + ' SOL' if d['tab']['devBuy'] else 'off'}"); rs._admin_save(ad)
    return d['tab']


@router.post('/api/reputation/coin-profile')
async def coin_profile_set(p: _RSM.CoinProfileIn):
    rs = _rs()
    me = rs.primary_of(rs._session_or_401(p.address, p.session))
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.mint):
        raise rs.HTTPException(400, 'Bad coin address.')
    creator = await rs.resolve_creator('solana', p.mint)
    is_admin = rs._is_staff(me)
    if not is_admin and (not creator or rs.primary_of(creator) != me):
        raise rs.HTTPException(403, "Only this coin's creator wallet can claim and edit its profile.")
    link = lambda v: v.strip()[:200] if v.strip().startswith('https://') else ''
    banner = p.bannerUrl.strip()[:300]
    rec = {'description': p.description.strip()[:600], 'bannerUrl': banner if banner.startswith(('https://', '/api/reputation/uploads/')) else '',
           'website': link(p.website), 'twitter': link(p.twitter), 'telegram': link(p.telegram), 'claimedBy': me, 'updatedAt': rs.time.time()}
    async with rs._admin_lock:
        d = rs._json_load(rs.COIN_PROFILES_PATH, {}); d[p.mint] = rec; rs._json_save(rs.COIN_PROFILES_PATH, d)
    return rec


@router.post('/api/reputation/pump/create-tx')
async def pump_create_tx(p: _RSM.PumpCreateIn, request: Request):
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    rs._legal_hold(me, 'launch', request)   # ⚖ LEGAL-1 (d)
    if not (rs._re.match(rs._B58, p.mint) and rs._re.match(rs._B58, p.address)):
        raise rs.HTTPException(400, 'Bad address.')
    if not (0 <= p.devBuySol <= 50):
        raise rs.HTTPException(400, 'Dev buy must be between 0 and 50 SOL.')
    if not (rs.primary_of(me) in {rs.primary_of(w) for w in rs._owner_wallets()} or rs._is_staff(me)):   # owner + staff (any linked wallet) launch freely
        tab = rs.launch_meta.clean_tab(rs._json_load(rs.LAUNCH_RAIL_PATH, {}).get('tab') or rs.launch_meta.TAB_DEFAULT)
        if 'pump' not in tab['rails']:
            raise rs.HTTPException(403, 'Pump.fun launches are switched off on FEELESS right now.')
        if not rs.launch_meta.dev_buy_ok(tab, p.devBuySol):
            raise rs.HTTPException(400, f"First buy is capped at {tab['maxDevBuySol']} SOL." if tab['devBuy'] else 'First buys are switched off right now.')
    m = rs._re.match(r'^/api/reputation/uploads/([a-f0-9]{32}\.(png|jpg|webp|gif))$', rs.launch_meta.upload_path(p.image))
    if not m or not (rs.UPLOAD_DIR / m.group(1)).exists():
        raise rs.HTTPException(400, 'Upload the coin image first.')
    img = (rs.UPLOAD_DIR / m.group(1)).read_bytes()
    mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'webp': 'image/webp', 'gif': 'image/gif'}[m.group(2)]
    form = rs.launch_meta.pump_form(p.name, p.symbol, p.description, p.website, p.twitter, p.telegram)
    costs = rs.launch_meta.clean_costs(rs._json_load(rs.LAUNCH_RAIL_PATH, {}).get('costs'))   # HQ › Launch › Costs
    async with rs.httpx.AsyncClient(timeout=30, headers={'User-Agent': 'Mozilla/5.0'}) as http:
        r = await http.post('https://pump.fun/api/ipfs', data=form, files={'file': (m.group(1), img, mime)})
        if r.status_code != 200:
            raise rs.HTTPException(502, 'Pump.fun metadata upload failed — try again.')
        uri = (r.json() or {}).get('metadataUri')
        t = await http.post('https://pumpportal.fun/api/trade-local', json={'publicKey': p.address, 'action': 'create', 'tokenMetadata': {'name': form['name'], 'symbol': form['symbol'], 'uri': uri},
                                                                           'mint': p.mint, 'denominatedInSol': 'true', 'amount': p.devBuySol,
                                                                           # the dev buy is the very first buy on a brand-new curve in the same tx: nobody can move
                                                                           # the price in between, so 1% slippage is plenty (10% made wallets preview a 10% bigger spend)
                                                                           'slippage': costs['pumpSlippagePct'], 'priorityFee': costs['pumpPriorityFeeSol'], 'pool': 'pump'})
    if t.status_code != 200:
        raise rs.HTTPException(502, f'Pump.fun could not build the launch ({t.text[:120]}).')
    import base64 as _b64
    return {'tx': _b64.b64encode(t.content).decode(), 'uri': uri}


@router.post('/api/reputation/admin/pools/register')
async def pools_register(request: Request, p: _RSM.PoolRegIn):
    """Record a pool created from the HQ. Verified on-chain: succeeded, signed by this admin."""
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    async with rs.httpx.AsyncClient(timeout=20) as http:
        tx = await rs._rpc(http, 'getTransaction', [p.signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}])
    if not tx or (tx.get('meta') or {}).get('err'):
        raise rs.HTTPException(409, 'Transaction not confirmed yet.')
    keys = tx['transaction']['message']['accountKeys']
    if admin not in [k['pubkey'] for k in keys if k.get('signer')] or p.pool not in [k['pubkey'] for k in keys]:
        raise rs.HTTPException(400, 'That transaction did not create this pool from your wallet.')
    d = rs._json_load(rs.POOLS_REG_PATH, {'pools': []})
    d['pools'] = [x for x in d['pools'] if x['pool'] != p.pool] + [{'pool': p.pool, 'mint': p.mint, 'locked': p.locked, 'signature': p.signature, 'by': admin, 'at': rs.time.time()}]
    rs._json_save(rs.POOLS_REG_PATH, d); rs._rugproof_cache.pop(p.mint, None)
    return {'ok': True}


@router.post('/api/reputation/admin/token-logo')
async def admin_token_logo(request: Request, p: _RSM.LogoIn):
    """Owner sets a coin's logo by hand (FEELESS coins first). Clears the cached lookup so it shows everywhere now."""
    rs = _rs()
    me = rs._require_admin(request)
    if not rs._re.match(rs._B58, p.mint):
        raise rs.HTTPException(400, 'Solana mint required.')
    if p.image and not rs._re.match(r'^/api/reputation/uploads/[a-f0-9]{32}\.(png|jpg|webp|gif)$', p.image):
        raise rs.HTTPException(400, 'Upload the image first.')
    d = rs._json_load(rs.LOGO_OVERRIDE_PATH, {})
    if p.image:
        d[p.mint] = p.image
    else:
        d.pop(p.mint, None)
    rs._json_save(rs.LOGO_OVERRIDE_PATH, d)
    for f in rs.LOGO_DIR.glob(f'{p.mint}.*'):
        f.unlink(missing_ok=True)
    rs._logo_miss.pop(p.mint, None)
    ad = rs._admin_load(); rs._audit(ad, me, 'token-logo', f"{p.mint[:6]}… {'set' if p.image else 'cleared'}"); rs._admin_save(ad)
    return {'ok': True, 'mint': p.mint, 'image': p.image}


@router.get('/api/reputation/admin/marketing')
async def admin_marketing(request: Request):
    rs = _rs()
    rs._require_admin(request)
    rows = await rs._three_day_movers()
    d = rs._json_load(rs.MARKETING_PATH, {'snapshots': []})
    # A dated snapshot every 3 days, kept, so past windows stay reviewable.
    if rows and (not d['snapshots'] or rs.time.time() - d['snapshots'][-1]['at'] >= 3 * 86400):
        d['snapshots'] = (d['snapshots'] + [{'at': rs.time.time(), 'up': rows[:10], 'down': rows[::-1][:10]}])[-60:]
        rs._json_save(rs.MARKETING_PATH, d)
    keys = ('chain', 'address', 'score', 'badge', 'tokenCount', 'bigWinners', 'dumpedCount', 'ruggedCount')
    good, bad = [[{k: r.get(k) for k in keys} for r in (await rs.leaderboard(chain=None, view=v))['rows'][:10]] for v in ('trusted', 'flagged')]
    return {'movers': {'up': [{**r, 'post': rs._post_text(r)} for r in rows[:10]], 'down': [{**r, 'post': rs._post_text(r)} for r in rows[::-1][:10] if r['move3d'] < 0]},
            'reps': {'good': [{**r, 'post': f"🟢 Trusted creator {r['address'][:4]}…{r['address'][-4:]} — {r['bigWinners']} big winner(s), {r['dumpedCount']} dumps. Receipts on FEELESS."} for r in good],
                     'bad': [{**r, 'post': f"🚩 Flagged creator {r['address'][:4]}…{r['address'][-4:]} — {r['ruggedCount']} rug(s), {r['dumpedCount']} dumps. Check any wallet before you ape: FEELESS."} for r in bad]},
            'snapshots': [{'at': x['at'], 'top': (x['up'][:1] or [{}])[0].get('symbol')} for x in d['snapshots'][-20:]]}


@router.post('/api/reputation/admin/badge-pools')
async def admin_badge_pool_save(request: Request, p: _RSM.BadgePoolIn):
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    if not rs._re.match(rs._ADDR_RE, p.wallet):
        raise rs.HTTPException(400, 'Pool wallet must be a Solana address.')
    weights = {}
    for k, v in list(p.weights.items())[:60]:
        if not rs._re.match(r'^(tier|badge):[A-Za-z0-9_-]{1,40}$', str(k)):
            raise rs.HTTPException(400, f'Bad weight key {k}.')
        try:
            w = float(v)
        except (TypeError, ValueError):
            raise rs.HTTPException(400, f'Weight for {k} must be a number.')
        if not 0 <= w <= 100:
            raise rs.HTTPException(400, 'Each badge share is 0–100.')
        if w:
            weights[k] = w
    if p.mode not in ('pct', 'weight'):
        raise rs.HTTPException(400, 'Unknown pool mode.')
    if p.mode == 'pct' and sum(weights.values()) > 100.0001:
        raise rs.HTTPException(400, f'Badge shares add up to {round(sum(weights.values()), 2)}% — keep the total at 100% or less.')
    d = rs._pools()
    pid = p.id or f"pool{int(rs.time.time())}"
    prev = next((x for x in d['pools'] if x['id'] == pid), {})
    fixed = {}
    for k, v in list(p.fixed.items())[:60]:
        if not rs._re.match(r'^(tier|badge):[A-Za-z0-9_-]{1,40}$', str(k)):
            raise rs.HTTPException(400, f'Bad key {k}.')
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise rs.HTTPException(400, f'SOL each for {k} must be a number.')
        if not 0 <= v <= 100:
            raise rs.HTTPException(400, 'SOL each must be 0–100.')
        if v:
            fixed[k] = v
    rec = {**prev, 'id': pid, 'name': p.name, 'wallet': p.wallet, 'pct': p.pct, 'seasonId': p.seasonId, 'weights': weights, 'mode': p.mode, 'fixed': fixed}
    d['pools'] = [x for x in d['pools'] if x['id'] != pid] + [rec]
    rs._json_save(rs.BADGE_POOLS_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, admin, 'badge-pool', f'{p.name} {p.pct}% of {p.wallet[:6]}'); rs._admin_save(ad)
    return {'ok': True, 'pool': rec}


@router.delete('/api/reputation/admin/badge-pools/{pid}')
async def admin_badge_pool_delete(request: Request, pid: str):
    rs = _rs()
    rs._require_admin(request)
    d = rs._pools(); d['pools'] = [x for x in d['pools'] if x['id'] != pid]; rs._json_save(rs.BADGE_POOLS_PATH, d)
    return {'ok': True}


@router.put('/api/reputation/admin/perf/config')
async def perf_config_set(request: Request, p: _RSM.PerfCfgIn):
    rs = _rs()
    admin = rs._require_admin(request)
    rs._json_save(rs.PERF_CFG_PATH, {'forceLite': p.forceLite})
    ad = rs._admin_load(); rs._audit(ad, admin, 'perf-lite', str(p.forceLite)); rs._admin_save(ad)
    return {'forceLite': p.forceLite}


@router.post('/api/reputation/admin/perf/code-health/queue')
async def perf_code_health_queue(p: _RSM.ChQueue, request: Request):
    """🧹 Queue a removal — it NEVER deletes anything from here: the item joins the build queue, and an engineering session applies it in a gated
    commit (frontend + backend tests and the build green) or says why it must stay."""
    rs = _rs()
    admin = rs._require_owner(request)
    if '..' in p.file or p.file.startswith('/') or not p.file.startswith(('frontend/src/', 'backend/')):
        raise rs.HTTPException(400, 'Only a source file in frontend/src or backend.')
    what_ = f"{p.file}" + (f" · {p.name}" if p.name and p.kind != 'dead_file' else '')
    try:
        rs._chat['build'], it_ = rs._aic.build_add(rs._build_state(), f"{rs.CH_QUEUE_TAG}{what_}", f"Code health says: {p.fix or 'unused'} ({p.kind}). Delete it only if nothing really "
                                             f"uses it, in a commit with the full gate green; otherwise mark why it stays.", f'code health · {admin[:6]}', rs.time.time())
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    rs._json_save(rs.BUILD_QUEUE_PATH, rs._chat['build'])
    return {'queued': it_['id'], 'title': it_.get('title')}


@router.post('/api/reputation/admin/perf/code-health/scan')
async def perf_code_health_scan(request: Request):
    rs = _rs()
    rs._require_admin(request)
    rs.asyncio.create_task(rs._code_health_run())
    return {'scanning': True}


@router.get('/api/reputation/admin/treasury/money')
async def treasury_money(request: Request):
    """Every wallet that holds FEELESS money, read live: fee accounts (wSOL / USDC), the admin wallet,
    season reserves and badge pools. Read-only; nothing here can move funds."""
    rs = _rs()
    admin = rs._require_admin(request)
    cfg = rs._fee_cfg()
    fee_accts = [('SOL fee account (wSOL)', cfg.get('feeAccountSol') or '', 'wSOL'), ('USDC fee account', cfg.get('feeAccountUsdc') or '', 'USDC')]
    reserves = [(f"Season reserve · {s['name']}", s['reserveWallet']) for s in rs._seasons()['seasons'] if s.get('reserveWallet')]
    reserves += [(f"Badge pool · {p['name']}", p['wallet']) for p in rs._pools()['pools']]

    async with rs.httpx.AsyncClient(timeout=10) as http:
        async def token(addr):
            if not addr:
                return None
            try:
                v = ((await rs._rpc(http, 'getAccountInfo', [addr, {'encoding': 'jsonParsed'}])) or {}).get('value') or {}
                info = rs._parsed_info(v)
                return {'owner': info.get('owner'), 'mint': info.get('mint'), 'amount': float((info.get('tokenAmount') or {}).get('uiAmount') or 0)}
            except Exception:
                return None

        async def sol(addr):
            try:
                return ((await rs._rpc(http, 'getBalance', [addr])) or {}).get('value', 0) / 1e9
            except Exception:
                return None
        results = await rs.asyncio.gather(*(token(a) for _, a, _ in fee_accts), sol(admin), *(sol(a) for _, a in reserves))
    fee_rows = [{'label': l, 'address': a, 'asset': asset, **(r or {}), 'ok': bool(r)} for (l, a, asset), r in zip(fee_accts, results[:2])]
    return {'admin': admin, 'adminSol': results[2], 'feeAccounts': fee_rows,
            'reserves': [{'label': l, 'address': a, 'sol': b} for (l, a), b in zip(reserves, results[3:])],
            'routes': rs._json_load(rs.ROUTES_PATH, {'routes': []}).get('routes', []), 'splits': (rs._admin_load().get('splits') or [])[-10:][::-1],
            'owners': list(rs._owner_wallets())}


@router.post('/api/reputation/admin/coin-verify')
async def verify_admin(request: Request, p: _RSM.VerifyAdminIn):
    rs = _rs()
    admin = rs._require_admin(request)
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.mint) or p.action not in ('grant', 'revoke', 'clear'):
        raise rs.HTTPException(400, 'Mint + grant / revoke / clear.')
    d = rs._verify_store()
    if p.action == 'clear':
        d['mints'].pop(p.mint, None)
    else:
        d['mints'][p.mint] = {'state': 'granted' if p.action == 'grant' else 'revoked', 'note': p.note, 'by': admin, 'at': rs.time.time()}
    for r in d['requests']:
        if r['mint'] == p.mint and r.get('status') == 'open':
            r['status'] = {'grant': 'granted', 'revoke': 'denied', 'clear': 'closed'}[p.action]
    rs._json_save(rs.VERIFY_PATH, d)
    rs._verify_cache.pop(p.mint, None)
    ad = rs._admin_load(); rs._audit(ad, admin, f'verify-{p.action}', p.mint); rs._admin_save(ad)
    return {'ok': True, 'state': d['mints'].get(p.mint)}


@router.get('/api/reputation/admin/coin-verify')
async def verify_admin_list(request: Request):
    rs = _rs()
    rs._require_admin(request)
    d = rs._verify_store()
    auto = sorted((r for _, r in rs._verify_cache.values() if r.get('level') == 'verified'), key=lambda r: -r['score'])[:40]
    return {'manual': [{'mint': m, **v} for m, v in d['mints'].items()], 'requests': [r for r in d['requests'] if r.get('status') == 'open'][-50:],
            'auto': [{k: r.get(k) for k in ('mint', 'symbol', 'score', 'level', 'at')} for r in auto]}


@router.put('/api/reputation/admin/badges/{bid}')
async def admin_badge_edit(request: Request, bid: str, p: _RSM.BadgeEdit):
    """Edit a badge everywhere it's held (label, icon, tone, why). Holders keep it; only the look changes."""
    rs = _rs()
    admin = rs._require_admin(request)
    tone = p.tone if p.tone in ('mint', 'gold', 'plain', 'bad') else 'gold'
    n = 0
    async with rs._admin_lock:
        d = rs._admin_load()
        for a, items in d['badges'].items():
            if bid in items:
                items[bid].update({'label': p.label, 'icon': p.icon, 'tone': tone, 'why': p.why or items[bid].get('why', '')}); n += 1
                rs._badge_cache.pop(a, None)
        if not n:
            raise rs.HTTPException(404, 'No one holds that badge.')
        rs._audit(d, admin, 'badge-edit', f'{bid} → {p.label}')
        rs._admin_save(d)
    return {'ok': True, 'holders': n}


@router.get('/api/reputation/admin/nft')
async def nft_home(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'platforms': rs._nft_platforms(), 'collections': sorted(rs._nft_load()['collections'], key=lambda c: -c.get('createdAt', 0))}


@router.post('/api/reputation/admin/nft/collections')
async def nft_create(request: Request):
    """Create a collection. Crossmint / Underdog are created here via their API; Metaplex Core is created in the
    browser (your wallet signs) and recorded with /onchain."""
    rs = _rs()
    me = rs._require_owner(request)
    try:
        c = rs.nft_studio.clean_collection(await request.json())
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    site = rs._public_site(request)
    cid = rs.uuid.uuid4().hex[:12]
    c.update({'id': cid, 'createdAt': rs.time.time(), 'by': me, 'drops': [], 'status': 'draft', 'address': None,
              'uri': f'{site}/api/reputation/nft-meta/{cid}.json'})
    if c['platform'] == 'crossmint':
        out = await rs._nft_api('crossmint', 'POST', '/api/2022-06-09/collections', rs.nft_studio.crossmint_collection_body(c, site))
        c.update({'address': out.get('id'), 'status': 'live'})
    elif c['platform'] == 'underdog':
        out = await rs._nft_api('underdog', 'POST', '/v2/projects', rs.nft_studio.underdog_project_body(c, site))
        c.update({'address': str(out.get('projectId') or out.get('id') or ''), 'mint': out.get('mintAddress'), 'status': 'live'})
    async with rs._nft_lock:
        d = rs._nft_load(); d['collections'].append(c); rs._json_save(rs.NFT_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'nft-collection', f"{c['platform']} {c['name']} ({c['symbol']})"); rs._admin_save(ad)
    return c


@router.post('/api/reputation/admin/nft/collections/{cid}/onchain')
async def nft_onchain(request: Request, cid: str, p: _RSM.NftOnchainIn):
    """Metaplex Core: record what the owner's wallet created (collection) or minted (a drop), verified on-chain."""
    rs = _rs()
    me = rs._require_owner(request)
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', p.signature) or not rs._re.match(rs._B58, p.address):
        raise rs.HTTPException(400, 'Bad signature or address.')
    assets = [a for a in p.assets if isinstance(a, dict) and rs._re.match(rs._B58, str(a.get('address') or '')) and rs._re.match(rs._B58, str(a.get('owner') or ''))][:rs.nft_studio.MAX_DROP]
    await rs._nft_verify(p.signature, me, [p.address] + [a['address'] for a in assets])
    async with rs._nft_lock:
        d = rs._nft_load(); c = next((x for x in d['collections'] if x['id'] == cid), None)
        if not c or c['platform'] != 'metaplex':
            raise rs.HTTPException(404, 'Metaplex collection not found.')
        if not assets:
            c.update({'address': p.address, 'status': 'live', 'createSig': p.signature})
        else:
            if c.get('address') != p.address:
                raise rs.HTTPException(400, 'Those NFTs belong to a different collection.')
            c['drops'].append({'at': rs.time.time(), 'ok': [{'to': a['owner'], 'asset': a['address'], 'sig': p.signature} for a in assets], 'failed': []})
        rs._json_save(rs.NFT_PATH, d)
    return c


@router.post('/api/reputation/admin/nft/collections/{cid}/drop')
async def nft_drop(request: Request, cid: str, p: _RSM.NftDropIn):
    """Crossmint / Underdog: mint one NFT to each wallet via the platform API. Type DROP <count> to confirm."""
    rs = _rs()
    me = rs._require_owner(request)
    site = rs._public_site(request)
    c = next((x for x in rs._nft_load()['collections'] if x['id'] == cid), None)
    if not c or c['platform'] == 'metaplex' or c.get('status') != 'live':
        raise rs.HTTPException(404, 'Live Crossmint / Underdog collection not found.')
    to = rs.nft_studio.recipients(p.to)[:rs.nft_studio.room_left(c)]
    if not to:
        raise rs.HTTPException(400, 'No valid Solana wallets (or the supply cap is reached).')
    if p.confirm.strip() != f'DROP {len(to)}':
        raise rs.HTTPException(400, f'Type "DROP {len(to)}" to confirm.')
    start = sum(len(x.get('ok') or []) for x in c['drops']) + 1
    sem = rs.asyncio.Semaphore(4)

    async def one(i, w):
        async with sem:
            try:
                if c['platform'] == 'crossmint':
                    out = await rs._nft_api('crossmint', 'POST', f"/api/2022-06-09/collections/{c['address']}/nfts", rs.nft_studio.crossmint_mint_body(c, site, w, start + i))
                else:
                    out = await rs._nft_api('underdog', 'POST', f"/v2/projects/{c['address']}/nfts", rs.nft_studio.underdog_nft_body(c, site, w, start + i))
                return {'to': w, 'asset': str(out.get('id') or out.get('nftId') or out.get('mintAddress') or ''), 'ok': True}
            except rs.HTTPException as e:
                return {'to': w, 'error': str(e.detail)[:160], 'ok': False}
    res = await rs.asyncio.gather(*(one(i, w) for i, w in enumerate(to)))
    ok, bad = [r for r in res if r['ok']], [r for r in res if not r['ok']]
    async with rs._nft_lock:
        d = rs._nft_load(); cc = next(x for x in d['collections'] if x['id'] == cid)
        cc['drops'].append({'at': rs.time.time(), 'by': me, 'ok': ok, 'failed': bad}); rs._json_save(rs.NFT_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'nft-drop', f"{c['name']}: {len(ok)} minted, {len(bad)} failed"); rs._admin_save(ad)
    return {'minted': len(ok), 'failed': bad}


@router.post('/api/reputation/admin/intel-desk/sweep')
async def intel_desk_sweep(request: Request):
    rs = _rs()
    rs._require_admin(request)
    d = await rs._desk_get(force=True)
    return {'ok': True, 'totals': d['snap']['totals']}


@router.put('/api/reputation/admin/cards/{key:path}')
async def admin_card_edit(request: Request, key: str):
    """Edit a card's look + lore everywhere it shows. Holders keep it; money rules stay in pools / reserve."""
    rs = _rs()
    admin = rs._require_admin(request)
    if not rs._re.match(r'^(badge:[a-z0-9-]{1,40}|season:[\w-]{1,20}|week:[\w-]{1,20}:w\d{1,2})$', key):
        raise rs.HTTPException(400, 'Unknown card.')
    edit = rs.badge_cards.clean_edit(await request.json())
    async with rs._admin_lock:
        d = rs._json_load(rs.CARDS_PATH, {}); d[key] = {**(d.get(key) or {}), **edit}; rs._json_save(rs.CARDS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'card-edit', f"{key} → {edit.get('title', '')} {edit.get('design', '')}".strip()); rs._admin_save(ad)
    rs._cards_cache.pop('all', None)
    rs._badge_cache.clear()   # chat + profile badges pick up the new name / glyph
    return rs._cards_all().get(key) or {'key': key, **edit}


@router.post('/api/reputation/admin/circle/destinations')
async def circle_destination_save(request: Request, p: _RSM.CircleDestIn):
    rs = _rs()
    me = rs._require_owner(request)
    if not (rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.address) or rs._re.match(r'^0x[0-9a-fA-F]{40}$', p.address)):
        raise rs.HTTPException(400, 'That is not a wallet address.')
    d = rs._json_load(rs.CIRCLE_DEST_PATH, {'saved': []})
    d['saved'] = [x for x in d.get('saved', []) if x['address'] != p.address]
    if not p.remove:
        d['saved'] = (d['saved'] + [{'address': p.address, 'label': (p.label or 'Saved wallet')[:40], 'by': me, 'at': rs.time.time()}])[-50:]
    rs._json_save(rs.CIRCLE_DEST_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'circle-dest', f"{'removed' if p.remove else 'saved'} {p.address[:6]}… {p.label[:20]}"); rs._admin_save(ad)
    return {'saved': d['saved']}

