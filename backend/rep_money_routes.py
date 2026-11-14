"""🧩 SITE-5 slice 11 (2026-11-14): MONEY routes (signing, sends, quotes, payouts), moved out of
reputation_service by scripts/move-routes.py --kind money: byte-for-byte the same bodies (every auth / staff / signed = quoted check kept), helpers
looked up on reputation_service when a route runs, body models read off the loaded service (imported at the END of it)."""
import reputation_service as _RSM  # noqa: E402
from fastapi import APIRouter, Query, Request

router = APIRouter()


def _rs():
    import reputation_service
    return reputation_service


@router.post('/api/reputation/fuses/position')
async def fuse_position(p: _RSM.FusePositionIn):
    """A one-click Fuse in landed: each leg counts only if its signature is one of YOUR confirmed FEELESS buys (cost and
    tokens come from that trade record, never from the client)."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    trades = {x.get('tx'): x for w, rows in rs._json_load(rs.FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or []}
    legs = []
    for leg in (p.legs or [])[:rs._fuse.MAX_LEGS]:
        t = trades.get(str(leg.get('signature') or ''))
        if t and t.get('side', 'buy') == 'buy' and rs._fuse._f(t.get('tokens')) > 0:
            legs.append({'pairAddress': str(leg.get('pairAddress'))[:64], 'chainId': str(leg.get('chainId') or 'solana')[:16], 'symbol': str(leg.get('symbol') or '')[:16],
                         'mint': t.get('token'), 'sig': t['tx'], 'usd': rs._hq.pool_usd(t), 'tokens': rs._fuse._f(t.get('tokens')), 'tokens0': rs._fuse._f(t.get('tokens')),
                         'role': 'runner' if leg.get('role') == 'runner' else 'pool'})
    if not legs:
        raise rs.HTTPException(400, 'None of those legs is a confirmed FEELESS buy from your wallet (yet).')
    prepaid_usd = 0.0
    held_ = False
    if p.prepaySig and rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', p.prepaySig) and not rs._pay_sig_used(p.prepaySig):
        await rs._pay_hold(p.prepaySig); held_ = True
        to = await rs._rounds_pay_to()
        tx = None
        if to:
            async with rs.httpx.AsyncClient(timeout=20) as http:
                for _ in range(4):
                    tx = await rs._rpc(http, 'getTransaction', [p.prepaySig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
                    if tx:
                        break
                    await rs.asyncio.sleep(2)
            prepaid_usd = max((rs._hq.paid_lamports(tx, w, to) for w in mine), default=0) / 1e9 * (await rs._sol_usd_live() or 0)
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        used = {leg['sig'] for pos in d.get('positions') or [] for leg in pos['legs']}
        legs = [leg for leg in legs if leg['sig'] not in used]
        if not legs:
            if held_:
                rs._PAY_HELD.discard(p.prepaySig)   # nothing was credited: the payment stays spendable
            return {'ok': True, 'counted': False}
        pos = {'id': rs.uuid.uuid4().hex[:10], 'wallet': me, 'name': p.name.strip() or 'Lab fuse', 'fuseId': p.fuseId[:16], 'at': rs.time.time(), 'legs': legs}
        choice = rs._hq.card_choice(p.plan, rs._fee_cfg().get('prepay'), rs._rounds_cfg())   # 🎟 the buyer's rounds · swaps per round · pay now or not
        credited = rs._hq.choice_credit(pos, prepaid_usd, choice) if choice['chosen'] else (prepaid_usd > 0 and rs._hq.prepay_credit(pos, prepaid_usd, rs._fee_cfg().get('prepay')))
        if credited and p.prepaySig and held_:
            d['roundSigs'] = (d.get('roundSigs') or [])[-500:] + [p.prepaySig]   # a payment is never reused
        elif held_:
            rs._PAY_HELD.discard(p.prepaySig)
        planned = [str(x)[:64] for x in (p.expected or [])[:rs._fuse.MAX_LEGS]]
        pos['missing'] = rs._hq.missing_legs(planned, legs)   # ⚠ approved but not landed — never hidden, never counted
        try:
            plan = rs._hq.clean_plan(p.plan, rs._json_load(rs.FUSE_HQ_PATH, {}).get('cardRules'), [leg['pairAddress'] for leg in legs], [leg['pairAddress'] for leg in legs if leg.get('role') == 'runner']) if p.plan else None
        except ValueError:
            plan = None   # a bad plan never blocks recording a real buy
        if plan:
            pos.update(mode=plan['mode'], onProfit=plan['onProfit'], risk=plan.get('risk', 'custom'), rotateHours=plan.get('rotateHours', 24), slMode=plan.get('slMode', 'sell'), cycle=plan.get('cycle', 'steady'), payoutPct=plan.get('payoutPct', 100), compoundStyle=plan.get('compoundStyle', 'smart'), autoFees=plan.get('autoFees', True),
                       frozen=plan.get('frozen') or [], coinRotate=plan.get('coinRotate') or {}, coinModes=plan.get('coinModes') or {})
            if plan['legs']:
                pos['legGuard'] = {pa: {**g, 'firedAt': None} for pa, g in plan['legs'].items()}
            if plan['at']:
                pos['autoYield'] = {'at': plan['at'], 'base': round(sum(rs._fuse._f(x.get('usd')) for x in legs), 6), 'armedAt': rs.time.time(), 'firedAt': None}
        src = next((x for x in d.get('positions') or [] if p.copyOf and x['id'] == p.copyOf), None)
        if src and rs.primary_of(src['wallet']) != rs.primary_of(me) and src['wallet'] not in set(rs.linked_of(me)):   # never a self-copy
            pos.update(copyOf=src['id'], copyOwner=src['wallet'])
            reign = ((d.get('bracket') or {}).get('champions') or [{}])[-1].get('key')
            if p.champ and reign == f"user:{src['id']}":   # 👑 champion's share: double copy cut for the reigning champion's owner
                pos['champCopy'] = True
        dflt = d.get('autoYieldDefault') or {}
        if dflt.get('on'):   # HQ default: new cards arm 💸 collect-profit at +at% of what was put in
            pos['autoYield'] = {'at': float(dflt.get('at') or rs._hq.YIELD_DEFAULT_AT), 'base': round(sum(rs._fuse._f(x.get('usd')) for x in legs), 6), 'armedAt': rs.time.time(), 'firedAt': None}
        d.setdefault('positions', []).append(pos)
        bt = d.get('battles') or {}
        if p.back and any(p.back in (x['a']['key'], x['b']['key']) for x in bt.get('pairs') or []):
            bt.setdefault('paid', {})[pos['id']] = {'key': p.back, 'wallet': me, 'usd': round(sum(rs._fuse._f(x.get('usd')) for x in legs), 2)}
            pos['backKey'] = p.back
        rs._json_save(rs.FUSE_HQ_PATH, d)
    # AFTER notice (inbox + phone): the card is recorded. Never P&L here — numbers live in Fuse › My cards / the profile.
    miss = pos.get('missing') or []
    rs.notify(me, 'fuse-card', (f"⚠ {pos['name']}: {len(legs)}/{len(legs) + len(miss)} coins landed — retry the other {len(miss)} or sell back, from My cards." if miss else
                             f"🧬 Card bought in one approval: {pos['name']} — {', '.join('$' + (leg.get('symbol') or '?') for leg in legs[:4])}{f' +{len(legs) - 4}' if len(legs) > 4 else ''}{' · ' + rs._hq.RISK_DIALS[pos['risk']]['label'] if pos.get('risk') in rs._hq.RISK_DIALS else ''}. Receipt + live P&L in My cards."),
           url=f"/terminal/fuse?tab=cards&card={pos['id']}", once=f"card-open-{pos['id']}", meta={'claim': 'Confirmed FEELESS buys from your wallet', 'source': 'Fuse cards'})
    return {'ok': True, 'counted': True, 'legs': len(legs), 'id': pos['id'], 'missing': miss}


@router.post('/api/reputation/fuses/receipt')
async def fuse_receipt(p: _RSM.FuseReceiptIn):
    """Before vs after: what the review screen quoted vs what each confirmed FEELESS trade actually cost (exact fill)."""
    rs = _rs()
    mine = set(rs.linked_of(rs.primary_of(p.address))) | {rs.primary_of(p.address), p.address}
    sigs = {str(x.get('sig') or '') for x in (p.legs or [])[:rs._fuse.MAX_LEGS]}
    actual = {x['tx']: x for w, rows in rs._json_load(rs.FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or [] if x.get('tx') in sigs}
    return rs._hq.receipt((p.legs or [])[:rs._fuse.MAX_LEGS], actual)


@router.post('/api/reputation/fuses/position/close')
async def fuse_position_close(p: _RSM.FuseCloseIn):
    """Unfuse: each leg is closed only by one of YOUR confirmed FEELESS sells of that leg's coin (realized $ from that record)."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    sigs = {str(x) for x in (p.signatures or [])[:rs._fuse.MAX_LEGS]}
    sells = [x for w, rows in rs._json_load(rs.FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or [] if x.get('tx') in sigs and x.get('side') == 'sell']
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine), None)
        if not pos:
            raise rs.HTTPException(404, 'No such Fuse position for this wallet.')
        used = {sg for x in d.get('positions') or [] for leg in x['legs'] for sg in (leg.get('sellSigs') or [leg.get('sellSig')])}
        pos, n = rs._hq.close_legs(pos, [t for t in sells if t['tx'] not in used], now=rs.time.time())
        if n and all(leg.get('soldUsd') is not None for leg in pos['legs']):
            pos['closedAt'] = rs.time.time()
        if n and pos.get('autoYield') and not pos.get('closedAt'):   # collected → re-arm from the new held value (next tick)
            pos['autoYield'].update(firedAt=None, rebase=True)
        if n:
            rs._hq.use_prepaid(pos, n)   # 💳 prepaid swaps cover these sells first
        rs._json_save(rs.FUSE_HQ_PATH, d)
    if n:   # AFTER notice — no P&L in the text
        closed = bool(pos.get('closedAt'))
        rs.notify(me, 'fuse-card', f"{'↩ Card withdrawn' if closed else '💰 Profit taken'}: {pos.get('name') or 'your Fuse card'} — {n} coin sell{'s' if n != 1 else ''} confirmed. {'Receipt on your profile.' if closed else 'Live P&L in My cards.'}",
               url=f"/terminal/profile/{me}" if closed else f"/terminal/fuse?tab=cards&card={pos['id']}", once=f"card-sell-{pos['id']}-{sorted(sigs)[0] if sigs else ''}",
               meta={'claim': 'Confirmed FEELESS sells from your wallet', 'source': 'Fuse cards'})
    return {'ok': True, 'closedLegs': n}


@router.post('/api/reputation/fuses/plan')
async def fuse_plan(p: _RSM.FusePlanIn):
    """Edit an open card's plan: per-coin TP / SL (re-arms them), collect vs compound, hold vs swap."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise rs.HTTPException(404, 'No such open Fuse card for this wallet.')
        try:
            plan = rs._hq.clean_plan({**p.plan, 'at': None} if p.plan.get('risk') not in rs._hq.RISK_DIALS else p.plan, d.get('cardRules'),
                                  [leg['pairAddress'] for leg in pos['legs'] if leg.get('soldUsd') is None], [leg['pairAddress'] for leg in pos['legs'] if leg.get('role') == 'runner'])
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        pos.update(mode=plan['mode'], onProfit=plan['onProfit'], risk=plan.get('risk', 'custom'), rotateHours=plan.get('rotateHours', 24), slMode=plan.get('slMode', 'sell'), cycle=plan.get('cycle', 'steady'), payoutPct=plan.get('payoutPct', 100), compoundStyle=plan.get('compoundStyle', 'smart'), autoFees=plan.get('autoFees', True),
                   rideAt=plan.get('rideAt', 0.0), rideTrail=plan.get('rideTrail', 10.0), legGuard={pa: {**g, 'firedAt': None} for pa, g in plan['legs'].items()},
                   **({k: plan[k] for k in ('frozen', 'coinRotate', 'coinModes')} if (p.plan or {}).get('coins') else {}))
        if plan.get('risk') in rs._hq.RISK_DIALS and plan.get('at'):   # the dial also re-arms the card's profit level
            pos['autoYield'] = {'at': plan['at'], 'base': round(sum(rs._fuse._f(x.get('heldUsd') or x.get('usd')) for x in pos['legs'] if x.get('soldUsd') is None), 6), 'armedAt': rs.time.time(), 'firedAt': None, 'rebase': True}
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return {'ok': True, 'plan': {k: plan.get(k) for k in ('risk', 'mode', 'onProfit', 'legs', 'at', 'rotateHours', 'slMode')}}


@router.get('/api/reputation/admin/fuses/payouts/plan')
async def admin_fuse_payout_plan(request: Request):
    """💸 This week's Fuse payout: every wallet owed Fee-Back + copy cuts, in SOL at today's price (FEELESS wallets and bots
    excluded, dust waits). The plan is frozen so the paid record uses the same price."""
    rs = _rs()
    rs._require_admin(request)
    book = await rs._feeback_book()
    wallets = [r['wallet'] for r in book['rows'] if r['owedUsd'] > 0]
    verdicts = await rs.asyncio.gather(*[rs._shield_of(w) for w in wallets], return_exceptions=True)
    bots = {w for w, v in zip(wallets, verdicts) if isinstance(v, dict) and v.get('verdict') == 'bot'}
    plan = rs._hq.payout_plan(book['rows'], await rs._sol_usd_live(), exclude=set(rs._protected_wallets()) | bots)
    plan = {**plan, 'id': rs.uuid.uuid4().hex[:10], 'at': rs.time.time(), 'bots': len(bots)}
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); d['payoutPlan'] = plan; rs._json_save(rs.FUSE_HQ_PATH, d)
    return {**plan, 'history': (d.get('payouts') or [])[-8:][::-1]}


@router.post('/api/reputation/admin/fuses/payouts/paid')
async def admin_fuse_payout_paid(request: Request, p: _RSM.FusePaidIn):
    """Record a payout the fee wallet signed. Every signature must be on-chain and succeeded; only SOL transfers whose
    SOURCE signed the transaction count, and each wallet is credited what actually moved (× the plan's price, ≤ owed)."""
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    sigs = [str(x) for x in (p.sigs or [])][:20]
    if not sigs or not all(rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', x) for x in sigs):
        raise rs.HTTPException(400, 'Bad transaction signature.')
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    plan = d.get('payoutPlan') or {}
    if plan.get('id') != p.planId or rs.time.time() - rs._fuse._f(plan.get('at')) > 2 * 3600:
        raise rs.HTTPException(409, 'That payout plan expired — open Pay again for fresh amounts.')
    used = {s for x in d.get('payouts') or [] for s in x.get('sigs') or []}
    if used & set(sigs):
        raise rs.HTTPException(409, 'Those transactions were already recorded.')
    async with rs.httpx.AsyncClient(timeout=20) as http:
        txs = await rs.asyncio.gather(*(rs._rpc(http, 'getTransaction', [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}]) for x in sigs))
    paid_sol: dict = {}
    for sig, tx in zip(sigs, txs):
        if not tx or (tx.get('meta') or {}).get('err'):
            raise rs.HTTPException(400, f'Transaction {sig[:8]}… is not on-chain or failed.')
        signers = {k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')}
        for ix in tx['transaction']['message'].get('instructions') or []:
            info = (ix.get('parsed') or {}).get('info') or {}
            if ix.get('program') == 'system' and (ix.get('parsed') or {}).get('type') == 'transfer' and info.get('source') in signers:
                paid_sol[info['destination']] = round(paid_sol.get(info['destination'], 0) + info['lamports'] / 1e9, 9)
    credit = rs._hq.credit_paid(paid_sol, plan)
    if not credit:
        raise rs.HTTPException(400, 'None of those transfers went to a wallet in this payout plan.')
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        fb = d.setdefault('feebackPaid', {})
        for w, usd in credit.items():
            fb[w] = round(rs._fuse._f(fb.get(w)) + usd, 6)
        d.setdefault('payouts', []).append({'at': rs.time.time(), 'by': admin, 'sigs': sigs, 'planId': plan['id'], 'solUsd': plan['solUsd'],
                                            'rows': [{'wallet': w, 'usd': u, 'sol': paid_sol.get(w)} for w, u in credit.items()]})
        d['payouts'] = d['payouts'][-200:]; d.pop('payoutPlan', None)
        rs._json_save(rs.FUSE_HQ_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'fuse-payout', f"${sum(credit.values()):,.2f} to {len(credit)} wallets"); rs._admin_save(ad)
    for w, usd in credit.items():
        rs.notify(w, 'fuse-guard', f"💸 You were paid ${usd:,.2f} in Fuse Fee-Back + copy cuts ({paid_sol[w]:.4f} SOL).", url='/terminal/fuse?tab=cards',
               once=f"fuse-paid-{sigs[0][:16]}-{w}", meta={'claim': 'SOL transfer confirmed on-chain', 'source': 'Fuse payout'})
    return {'ok': True, 'paidUsd': round(sum(credit.values()), 6), 'wallets': len(credit)}


@router.post('/api/reputation/admin/fuses/rules')
async def admin_fuse_rules_set(request: Request):
    """HQ › Fuse › Card rules: auto-profit levels, swap trigger, Arena top tier, Fee-Back shares. 'paidUsd' + 'wallet'
    records a Fee-Back payout."""
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        if body.get('wallet') and body.get('paidUsd') is not None:
            fb = d.setdefault('feebackPaid', {})
            fb[body['wallet']] = round(rs._fuse._f(fb.get(body['wallet'])) + max(0.0, rs._fuse._f(body['paidUsd'])), 6)
        else:
            d['cardRules'] = rs._hq.clean_rules(body)
        rs._json_save(rs.FUSE_HQ_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, admin, 'fuse-rules', rs.json.dumps(body)[:200]); rs._admin_save(ad)
    rs._arena_mega_cache.update(at=0.0, data=None)
    return {'rules': rs._card_rules(), 'feeback': await rs._feeback_book()}


@router.get('/api/reputation/fuses/receipts/{address}')
async def fuse_receipts(address: str):
    """Profile › Fuse receipts: every withdrawn (closed) card with its whole lifecycle — legs in, take-profits, switches, out."""
    rs = _rs()
    me = rs.primary_of(address)
    mine = set(rs.linked_of(me)) | {me}
    by, rl = rs._ledger_by_sig(), rs._card_rules()
    # each receipt carries its moves (buys / sells / switches / top-ups) and the FEELESS fees actually paid (fee ledger) +
    # a network estimate — shown on the receipt, never inside P&L
    rows = [{**rs._hq.position_pnl(x, {}), 'events': (x.get('events') or [])[-30:], 'feesUsd': rs._card_fees(x, by),
             'netUsd': round(rl['netFeeUsdPerLeg'] * 2 * len(x.get('legs') or []), 4)}
            for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [] if x['wallet'] in mine and x.get('closedAt')]
    return {'receipts': sorted(rows, key=lambda r: -(r.get('closedAt') or 0))[:30]}


@router.get('/api/reputation/fuses/pnl/{address}')
async def fuse_pnl(address: str):
    rs = _rs()
    mine = set(rs.linked_of(rs.primary_of(address))) | {rs.primary_of(address), address}
    pos = [x for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [] if x['wallet'] in mine]
    open_mints = {l.get('mint') for x in pos if not x.get('closedAt') for l in x['legs'] if l.get('soldUsd') is None and l.get('mint')}
    if open_mints:   # 🔗 a card never counts coins the wallet doesn't REALLY hold (on-chain balances, all linked wallets, 60s cache)
        held = await rs._wallet_held(sorted(mine), open_mints)
        if held is not None:
            capped = {x['id']: x for x in rs._hq.cap_to_wallet([x for x in pos if not x.get('closedAt')], held)}
            pos = [capped.get(x['id'], x) for x in pos]
    px = await rs._hq_prices([leg for x in pos for leg in x['legs']]) if pos else {}
    by, rules, now = rs._ledger_by_sig(), rs._card_rules(), rs.time.time()
    hot = {c['id'] for c in (rs._arena_mega_cache.get('data') or []) if c.get('kind') == 'user' and c['activity']['tier'] in ('hot', 'blazing')}
    wins = rs._season_wins()
    by_ = rs._ledger_by_sig()   # FEELESS fees already paid on each card (for the profit trail's book)
    rows = sorted(({**rs._hq.position_pnl(x, px), 'guard': x.get('guard'), 'autoRebalance': x.get('autoRebalance'), 'autoYield': x.get('autoYield'), 'mode': x.get('mode') or 'hold', 'nextSwitchAt': rs._hq.next_switch_at(x), 'rotateHours': x.get('rotateHours') or 24, 'slMode': x.get('slMode') or 'sell', 'coinModes': x.get('coinModes') or {}, 'coinRotate': x.get('coinRotate') or {}, 'cycle': x.get('cycle') or 'steady', 'payoutPct': x.get('payoutPct', 100 if (x.get('onProfit') or 'collect') == 'collect' else 0), 'compoundStyle': x.get('compoundStyle') or 'smart', 'autoFees': x.get('autoFees', True), 'missing': x.get('missing') or [],
                  'heldShort': [l['pairAddress'] for l in x['legs'] if l.get('heldShort')],
                  'roundsLeft': rs._hq.rounds_left(x, rs._is_staff(x['wallet'])), 'roundsUsed': x.get('roundsUsed') or 0, 'roundsOwedUsd': x.get('roundsOwedUsd') or 0,
                  'feesPaidUsd': rs._card_fees(x, by_), 'roundsPaidUsd': round(sum(rs._fuse._f(rb.get('usd')) for rb in x.get('roundBuys') or [] if rb.get('mode') == 'pay'), 4), 'roundPacks': len(x.get('roundBuys') or []), 'parked': x.get('parked') or {}, 'risk': x.get('risk') or 'custom',
                    'onProfit': x.get('onProfit') or 'collect', 'legGuard': x.get('legGuard') or {},
                    'feeback': rs._hq.card_feeback(rs._card_fees(x, by), (x.get('closedAt') or now) - rs._fuse._f(x.get('at')), x['id'] in hot, rules, x['id'] in wins), 'onArena': x['id'] in hot,
                    'seasonWin': wins.get(x['id']), 'beatCat': [w['week'] for w in rs._json_load(rs.FUSE_HQ_PATH, {}).get('catChallenge') or [] if x['id'] in (w.get('ids') or [])]} for x in pos), key=lambda r: -(r['at'] or 0))
    allpos = rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or []
    copies = {}
    for c in allpos:
        if c.get('copyOf'):
            k = copies.setdefault(c['copyOf'], {'n': 0, 'usd': 0.0}); k['n'] += 1; k['usd'] = round(k['usd'] + rs._hq.copy_cut(rs._card_fees(c, by), rules, champ=bool(c.get('champCopy'))), 6)
    box = rs._notif_box(rs.primary_of(address))
    frz = {x['id']: x.get('frozen') or [] for x in pos}
    rows = [{**r, 'frozen': frz.get(r['id'], []), 'autos': rs._hq.card_autos(box, r['id'], now), 'drift': rs._hq.drift(r), 'exitFeeUsd': 0.0 if r['closed'] else rs._exit_fee(r), 'streak': rs._hq.swap_streak(r), 'compound': rs._hq.compound_streak(r),
             'copies': (copies.get(r['id']) or {}).get('n', 0), 'copyEarnedUsd': (copies.get(r['id']) or {}).get('usd', 0.0)} for r in rows]
    held = [r for r in rows if not r['closed']]
    return {**rs._hq.book(rows), 'rows': rows[:20], 'rules': {k: rules[k] for k in ('yieldLevels', 'yieldDefault', 'swapDropPct')},
            'held': {'cards': len(held), 'costUsd': round(sum(r['costUsd'] for r in held), 4), 'valueUsd': round(sum(r['valueUsd'] for r in held), 4),
                     'pnlUsd': round(sum(r['pnlUsd'] for r in held), 4), 'pnlPct': round((sum(r['valueUsd'] for r in held) / max(1e-9, sum(r['costUsd'] for r in held)) - 1) * 100, 2) if held else 0.0},
            'feebackUsd': round(sum(r['feeback']['usd'] for r in rows), 6)}


@router.post('/api/reputation/familia/kalshi/send')
async def familia_kalshi_send(request: Request):
    """✍ A wallet-signed Kalshi order → checked again (signed, a fingerprint FEELESS built, once) → broadcast through the RPC relay."""
    rs = _rs()
    kt_ = rs._kt_need()
    signed_ = str(((await request.json()) or {}).get('signed') or '')
    try:
        from solders.transaction import VersionedTransaction
        payer_ = str(VersionedTransaction.from_bytes(rs.base64.b64decode(signed_, validate=True)).message.account_keys[0])
    except Exception:
        raise rs.HTTPException(400, 'Not a transaction.')
    ok_, why_, fp_ = kt_.verify(signed_, payer_, signed=True)
    if not ok_:
        raise rs.HTTPException(400, f'Refused: {why_}')
    if not kt_.take(fp_, payer_):
        raise rs.HTTPException(409, 'This order was not built by FEELESS, expired, or was already sent — get a fresh one.')
    try:
        r_ = await rs._fmk_http_get().post('http://127.0.0.1:5077/api/reputation/rpc', json={'jsonrpc': '2.0', 'id': 1, 'method': 'sendTransaction',
                                        'params': [signed_, {'encoding': 'base64', 'skipPreflight': False, 'preflightCommitment': 'confirmed', 'maxRetries': 3}]}, timeout=25)
        out_ = r_.json()
    except Exception:
        kt_.remember(fp_, payer_)   # the same signed bytes may go again (same signature — never a second order)
        raise rs.HTTPException(503, 'Solana did not answer — try again.')
    if out_.get('error') or not out_.get('result'):
        kt_.remember(fp_, payer_)
        raise rs.HTTPException(400, f"Solana refused it: {str((out_.get('error') or {}).get('message') or 'no signature')[:200]}")
    return {'signature': out_['result']}


@router.get('/api/reputation/familia-pools')
async def familia_pools():
    """🏦 The Pool Hub: every top + rising Solana pool (v2 · v3 · DLMM · vaults · lending · staking · perps · RWA) with TVL / APY / 7-day move,
    each with its exact deposit page and, for DEX pools, the exact pool for our war room; + each outer city's real-money district. ≤ 10 min old."""
    rs = _rs()
    now = rs.time.time(); c = rs._fpl_cache
    if c['v'] and now - c['at'] < rs.FPL_SEC:
        return c['v']
    if c['lock'] is None:
        c['lock'] = rs.asyncio.Lock()
    async with c['lock']:
        if c['v'] and now - c['at'] < rs.FPL_SEC:
            return c['v']
        ll, pairs = await rs._fpl_fetch()
        v = rs._fpl.hub(ll, pairs, now)
        if v['pools'] or not c['v']:   # a failed read keeps the last good hub
            c.update(at=now, v=v)
        return c['v']


@router.post('/api/reputation/cats/{cat_id}/fund')
async def cat_fund_build(cat_id: str, p: _RSM.CatFundIn):
    """💵 FUND A CAT (cat_fund.py, DECISIONS #2): the receipt + ONE unsigned transaction — the one-time FEELESS fee ($2, first funding only)
    to the FEELESS fee wallet and the rest to the cat's own wallet. Your wallet signs it; /fund/send sends only that exact transaction."""
    rs = _rs()
    me = rs.session_address(p.session)
    if not me or me != p.address:
        raise rs.HTTPException(401, 'Sign in with your wallet first (one signature, no transaction).')
    if p.token not in ('SOL', 'USDC') or p.creditUsd < 0 or p.creditUsd > p.usd:
        raise rs.HTTPException(400, 'Pay in SOL or USDC, and split no more than the amount.')
    cat, w = await rs._cat_for_fund(cat_id, me)
    if p.creditUsd and not cat.get('brainsCfg'):
        raise rs.HTTPException(400, 'This agent runs no paid models.')
    rules_ = rs._cat_fund_rules(me)
    free_credit = bool(rules_.get('staff')) and (cat.get('brainsCfg') or {}).get('kind') != 'general'   # 🧭 a general agent's credit is always real money (owner 2026-10-31)
    first = rs._deposit.is_first(cat)
    try:
        dq = rs._deposit.quote(p.usd, first, bool(rules_.get('staff')), rules_.get('depositPct', rs._deposit.RATE_PCT), rules_.get('minUsd', rs._deposit.FIRST_MIN_USD))   # 💵 all of it to the Collective wallet
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    need_fee = dq['ratePct'] > 0
    colony_w = ((rs._json_load(rs.COLONY_PATH, {}) or {}).get('wallet') or {}).get('address') if need_fee else ''
    if need_fee and not colony_w:
        raise rs.HTTPException(503, 'The Pool wallet is not open yet, so deposits are paused. Nothing was charged.')
    async with rs.httpx.AsyncClient(timeout=10) as http:
        try:
            pl = rs._deposit.apply(rs._cfund.plan(p.usd, await rs._sol_usd(), False, fee_usd=0, min_usd=rs._cfund.TOPUP_MIN_USD, token=p.token, credit_usd=p.creditUsd, free_credit=free_credit, credit_to_wallet=True), dq)
            if not pl['totalLamports']:   # a creator's credit alone: nothing to pay or sign
                await rs._ai_http().post(f'http://127.0.0.1:5088/api/cats/{cat_id}/action', headers={'x-feeless-internal': rs._internal_key()}, timeout=8,
                                      json={'action': 'agent_funded', 'sig': f'creator-{rs.uuid.uuid4().hex[:16]}', 'result': 'confirmed', 'amount': {'token': pl['token'], 'usd': pl['usd'], 'creditUsd': pl['creditUsd'], 'feeUsd': 0, 'catLamports': 0, 'feeLamports': 0, 'solUsd': pl['solUsd']}})
                return {'plan': pl, 'granted': True}
            bh = ((await rs._rpc(http, 'getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
            tx = rs._cfund.build(me, w['address'], w['address'], pl, bh, colony_w)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    now = rs.time.time()
    for k_ in [k_ for k_, v_ in rs._cfund_plans.items() if now - v_['at'] > rs._cfund.PLAN_SEC]:
        rs._cfund_plans.pop(k_, None)
    rs._cfund_plans[f'{cat_id}:{me}'] = {'tx': tx, 'plan': pl, 'at': now, 'catWallet': w['address'], 'colonyWallet': colony_w, 'first': first}
    return {'plan': pl, 'transaction': tx, 'catWallet': w['address'], 'colonyWallet': colony_w, 'first': first, 'expiresIn': rs._cfund.PLAN_SEC}


@router.post('/api/reputation/cats/{cat_id}/withdraw')
async def cat_withdraw(cat_id: str, p: _RSM.CatWithdrawIn):
    """↩ REAL WITHDRAW: SOL or USDC from the agent's own wallet back to its owner's wallet, and nowhere else. Your wallet's session proves it is you; Circle signs; a send the network refuses moves nothing."""
    rs = _rs()
    me = rs.session_address(p.session)
    if not me or me != p.address:
        raise rs.HTTPException(401, 'Sign in with your wallet first (one signature, no transaction).')
    if p.token not in ('SOL', 'USDC') or p.amount < 0:
        raise rs.HTTPException(400, 'Withdraw SOL or USDC.')
    cat, w = await rs._cat_for_fund(cat_id, me)
    if rs.time.time() < float(cat.get('recoveredAt') or 0) + 72 * 3600:   # 🔑 after a recovery its wallet cannot pay out for 3 days: a stolen phrase can't empty it at once
        raise rs.HTTPException(423, 'This agent was recovered in the last 3 days. Its wallet can pay out after that.')
    if w.get('provider') != 'circle' or w.get('circleAcct') != 'agent' or not w.get('circleId'):
        raise rs.HTTPException(400, 'Withdrawals work on its Circle wallet.')
    if cat_id in rs._cat_out_busy:
        raise rs.HTTPException(409, 'A withdrawal is already on its way.')
    rs._cat_out_busy.add(cat_id)
    try:
        async with rs.httpx.AsyncClient(timeout=15) as http:
            if p.token == 'SOL':
                have = int(((await rs._rpc(http, 'getBalance', [w['address'], {'commitment': 'confirmed'}])) or {}).get('value') or 0) - rs._cfund.FEE_RESERVE; scale = rs._cfund.LAMPORTS
            else:
                try:
                    have = int((((await rs._rpc(http, 'getTokenAccountBalance', [str(rs._cfund.ata(w['address'])), {'commitment': 'confirmed'}])) or {}).get('value') or {}).get('amount') or 0)
                except Exception:
                    have = 0
                scale = rs._cfund.USDC_UNITS
            units = have if not p.amount else int(p.amount * scale)
            if units <= 0 or units > have:
                raise rs.HTTPException(400, f'It has {max(0, have) / scale:.6g} {p.token} available.')
            bh = ((await rs._rpc(http, 'getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
            try:
                tx = rs._cfund.build_out(w['address'], w['owner'], p.token, units, bh)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            signed_ = await rs._circle('POST', '/sign', {'walletId': w['circleId'], 'rawTransaction': tx, 'memo': f'FEELESS withdraw {cat_id[:20]}'}, agent=True)
            sig_ = str(signed_.get('signature') or signed_.get('txHash') or '')
            if not signed_.get('signedTransaction') or not sig_:
                raise rs.HTTPException(502, 'Circle did not sign it. Nothing moved.')
            try:
                await rs._rpc(http, 'sendTransaction', [signed_['signedTransaction'], {'encoding': 'base64', 'skipPreflight': False, 'maxRetries': 3}])
            except rs.HTTPException:
                raise
            except Exception as e:
                raise rs.HTTPException(400, f'The network refused it, nothing moved: {str(e)[:160]}')
    finally:
        rs._cat_out_busy.discard(cat_id)
    try:
        await rs._ai_http().post(f'http://127.0.0.1:5088/api/cats/{cat_id}/action', headers={'x-feeless-internal': rs._internal_key()}, timeout=8,
                              json={'action': 'agent_withdrew', 'sig': sig_, 'amount': {'amount': units / scale, 'token': p.token}})
    except Exception as e:
        print(f'[cat withdraw] record {cat_id}: {e}')
    return {'signature': sig_, 'amount': units / scale, 'token': p.token, 'to': w['owner']}


@router.post('/api/reputation/cats/{cat_id}/fund/send')
async def cat_fund_send(cat_id: str, p: _RSM.CatFundIn):
    """💵 Send the signed funding: it must be EXACTLY the transaction /fund built for this owner (one use — never a resubmit), then confirm it
    on-chain and tell the cat service (its `agentFunded` record: the first funding paid the fee)."""
    rs = _rs()
    me = rs.session_address(p.session)
    if not me or me != p.address:
        raise rs.HTTPException(401, 'Sign in with your wallet first (one signature, no transaction).')
    rec = rs._cfund_plans.pop(f'{cat_id}:{me}', None)
    if not rec or rs.time.time() - rec['at'] > rs._cfund.PLAN_SEC:
        raise rs.HTTPException(409, 'That receipt expired — build a fresh one (prices move).')
    try:
        sig = rs._cfund.verify(p.signed, rec['tx'], me)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    async with rs.httpx.AsyncClient(timeout=15) as http:
        try:
            await rs._rpc(http, 'sendTransaction', [p.signed, {'encoding': 'base64', 'skipPreflight': False, 'maxRetries': 3}])
        except Exception as e:
            raise rs.HTTPException(400, f'The network refused it — nothing moved: {str(e)[:160]}')
        ok = None
        for _i in range(20):
            await rs.asyncio.sleep(1.5)
            try:
                st_ = (((await rs._rpc(http, 'getSignatureStatuses', [[sig]])) or {}).get('value') or [None])[0]
            except Exception:
                st_ = None
            if st_ and st_.get('err'):
                ok = False; break
            if st_ and st_.get('confirmationStatus') in ('confirmed', 'finalized'):
                ok = True; break
    if ok is False:
        raise rs.HTTPException(400, f'It failed on-chain — nothing moved ({sig[:10]}…).')
    pl = rec['plan']
    if ok is True:   # only a confirmed on-chain transfer buys model credit or pays the first fee
        if pl.get('colonyLamports'):   # 🪙 it landed: the Pool ledger counts it, once
            try:
                rs._cpool.update(rs.POOL_PATH, lambda st: rs._cpool.income(st, f'deposit:{sig}', pl.get('token') or 'SOL', pl['colonyLamports'], 'deposit' if rec.get('first') else 'topup'))
            except Exception as e:
                print(f'[pool] deposit {sig[:10]}: {e}')
        try:
            await rs._ai_http().post(f'http://127.0.0.1:5088/api/cats/{cat_id}/action', headers={'x-feeless-internal': rs._internal_key()}, timeout=8,
                                  json={'action': 'agent_funded', 'sig': sig, 'result': 'confirmed' if ok else 'submitted', 'amount': {'token': pl.get('token'), 'creditUsd': pl.get('creditUsd'), 'usd': pl['usd'], 'feeUsd': pl['feeUsd'], 'deposit': pl.get('deposit'), 'colonyLamports': pl.get('colonyLamports'), 'catLamports': pl['catLamports'], 'feeLamports': pl['feeLamports'], 'solUsd': pl['solUsd']}})
        except Exception as e:
            print(f'[cat fund] record {cat_id}: {e}')
    return {'state': 'confirmed' if ok else 'submitted', 'signature': sig, 'plan': pl}


@router.post('/api/reputation/familia-pools/earn')
async def familia_pools_earn(request: Request):
    """🏦 Deposit / withdraw in a Jupiter Lend market WITHOUT leaving FEELESS: Jupiter builds the unsigned transaction, `lend_earn.verify`
    opens it (the user pays + signs alone, only Jupiter Lend + Solana's own programs) and only then hands it back for the wallet to sign.
    FEELESS never holds funds and never signs. The market must be a Jupiter Lend row on the Pool Hub."""
    rs = _rs()
    import lend_earn as _le
    body = await request.json()
    try:
        side_, asset_, signer_, amt_ = _le.clean_request(body)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    if side_ != 'withdraw':   # ⚖ LEGAL-1 (d): a withdraw is an exit, never held
        rs._legal_hold(signer_, 'perps', request)
    if not await rs._ip_hit(rs._fle_hits, request, 30, 3600):
        raise rs.HTTPException(429, 'Too many deposit builds from here — try again in a while.')
    hub_ = await rs.familia_pools()
    row_ = next((r_ for r_ in (hub_ or {}).get('pools') or [] if r_.get('project') == 'jupiter-lend' and asset_ in (r_.get('mints') or [])), None)
    if not row_:
        raise rs.HTTPException(400, 'Only Jupiter Lend markets on the Pool Hub can be deposited from here.')
    dec_ = await rs._mint_decimals(asset_)
    units_ = _le.base_units(amt_, dec_) if dec_ is not None else None
    if not units_:
        raise rs.HTTPException(400, 'Type an amount above zero.')
    hosts_ = [(_le.EARN, {'x-api-key': k_}) for k_ in rs._jkeys.lend_keys(rs.os.environ)] + [(_le.EARN_PUBLIC, {})]   # a key at its limit never blocks a deposit
    why_ = 'Jupiter did not answer.'
    for base_, hdr_ in hosts_:
        try:
            r_ = await rs._ai_http().post(f"{base_}/{side_}", json={'asset': asset_, 'signer': signer_, 'amount': units_}, headers=hdr_, timeout=12)
        except Exception:
            continue
        if r_.status_code == 429:
            why_ = 'Jupiter is busy right now — try again in a minute.'
            continue
        tx_ = (r_.json() or {}).get('transaction') if r_.status_code == 200 else None
        if not tx_:
            why_ = f"Jupiter refused it: {str((r_.json() if r_.headers.get('content-type', '').startswith('application/json') else {}).get('error') or r_.status_code)[:120]}"
            continue
        ok_, bad_, progs_ = _le.verify(tx_, signer_)
        if not ok_:
            print('lend earn refused:', bad_, progs_)
            raise rs.HTTPException(502, f"Refused before your wallet saw it: {bad_}")
        return {'transaction': tx_, 'side': side_, 'asset': asset_, 'units': units_, 'decimals': dec_, 'sym': row_.get('sym'), 'apy': row_.get('apy'),
                'programs': sorted({_le.ALLOW[p_] for p_ in progs_})}
    raise rs.HTTPException(503, why_)


@router.post('/api/reputation/familia/perps-real')
async def familia_perps_real_build(request: Request):
    """📉 Open (increase) or close (decrease the entire position, paid out in USDC) a Jupiter Perps position: Jupiter builds it with its own
    quote (entry, liquidation, fees), `jup_perps.verify` opens it, the wallet signs it next."""
    rs = _rs()
    import jup_perps as _jp
    body = await request.json()
    if not await rs._ip_hit(rs._fjp_hits, request, 60, 3600):
        raise rs.HTTPException(429, 'Too many perps builds from here — try again in a while.')
    act_ = str((body or {}).get('act') or 'open')
    if act_ != 'close' and not act_.startswith('tpsl-'):   # ⚖ LEGAL-1 (d): anything that builds an open is checked; closing / TP-SL are exits
        rs._legal_hold((body or {}).get('address') or (body or {}).get('wallet'), 'perps', request)
    meth_, exec_ = 'POST', None
    try:
        if act_.startswith('tpsl-'):
            meth_, path_, req_, exec_ = _jp.tpsl_body(body)
            what_ = {'act': act_}
        elif act_ == 'close':
            req_, what_, path_ = _jp.close_body(body), {'act': 'close', 'pct': _jp._f(body.get('pct')) or 100}, 'positions/decrease'
        else:
            req_, what_ = _jp.clean_open(body, await rs._sol_usd() if str((body or {}).get('input') or '').upper() == 'SOL' else None)
            path_ = 'positions/increase'
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    c_, b_ = await rs._jp_call(meth_, path_, json=req_)
    tx_ = (b_ or {}).get('serializedTxBase64') if c_ == 200 else None
    if not tx_:
        raise rs.HTTPException(400 if c_ in (400, 422) else 502, f"Jupiter said no: {str((b_ or {}).get('message') or c_)[:160]}")
    ok_, bad_ = _jp.verify(tx_, str((body or {}).get('address') or ''))
    if not ok_:
        print('perps refused:', bad_)
        raise rs.HTTPException(502, f'Refused before your wallet saw it: {bad_}')
    return {'transaction': tx_, 'action': exec_ or ('decrease-position' if act_ == 'close' else 'increase-position'), 'quote': (b_ or {}).get('quote') or {},
            'positionPubkey': (b_ or {}).get('positionPubkey'), 'tpsl': [{'kind': r_.get('requestType'), 'pnl': _jp._usd(r_.get('estimatedPnlUsd')),
            'pnlPct': _jp._f(r_.get('estimatedPnlPercent'))} for r_ in (b_ or {}).get('tpslRequests') or []], **what_}


@router.get('/api/reputation/familia-pools/ranges')
async def familia_pools_ranges(mint: str = Query('', max_length=64), quote: str = Query('', max_length=64), top: int = 0, reads: int = 0):
    """🤖 The concentrated pools AutoRange can really open in — Raydium CLMM + Meteora DLMM, read from each venue's own API (fees ÷ TVL over 24h,
    fee tier, tick spacing / bin step). `mint` = the pools holding that token (deepest first); `top=1` = the busiest fee payers right now."""
    rs = _rs()
    import range_pools as _rp
    ray_ = lambda d_: _rp.raydium(((d_ or {}).get('data') or {}).get('data') or [])
    met_ = lambda d_: _rp.meteora((d_ or {}).get('data') or [])
    orc_ = lambda d_: _rp.orca((d_ or {}).get('data') or [])
    if reads:   # 🐋 reads=1: the pool lists that only read also show Orca. AutoRange's own picker never asks for it, because it cannot open there
        q_ = {'size': 50, 'sortBy': 'volume24h', 'sortDirection': 'desc'} if top else {'size': 10, 'token': mint, 'sortBy': 'tvl', 'sortDirection': 'desc'}
        extra_ = await rs._rng_get('orca:top' if top else f'orca:{mint}', 'https://api.orca.so/v2/solana/pools', q_, orc_) if top or 32 <= len(mint) <= 44 else []
    else:
        extra_ = []
    if top:
        a_, b_ = await rs.asyncio.gather(
            rs._rng_get('ray:top', 'https://api-v3.raydium.io/pools/info/list', {'poolType': 'concentrated', 'poolSortField': 'volume24h', 'sortType': 'desc', 'pageSize': 100, 'page': 1}, ray_),
            rs._rng_get('met:top', 'https://dlmm.datapi.meteora.ag/pools', {'page_size': 100, 'sort_by': 'volume_24h:desc'}, met_))
        seen_ = _rp.busiest(a_ + b_ + extra_, 30); deep_ = sorted(a_ + b_ + extra_, key=lambda r_: -r_['tvl'])[:15] if reads else []   # the lists that only read also get the deepest, not just the busiest
        return {'pools': seen_ + [r_ for r_ in deep_ if r_ not in seen_], 'at': round(rs.time.time())}   # (owner 2026-10-31: way more AutoRange options)
    if not 32 <= len(mint) <= 44:
        raise rs.HTTPException(400, 'A token mint, or top=1.')
    a_, b_ = await rs.asyncio.gather(
        rs._rng_get(f'ray:{mint}', 'https://api-v3.raydium.io/pools/info/mint', {'mint1': mint, 'poolType': 'concentrated', 'poolSortField': 'liquidity', 'sortType': 'desc', 'pageSize': 10, 'page': 1}, ray_),
        rs._rng_get(f'met:{mint}', 'https://dlmm.datapi.meteora.ag/pools', {'query': mint, 'page_size': 10}, met_))
    return {'pools': _rp.for_token(a_ + b_ + extra_, mint, quote or None)[:8], 'at': round(rs.time.time())}


@router.get('/api/reputation/familia-pools/run')
async def familia_pools_run(address: str = ''):
    """💵 THE $5 RUN: the two Jupiter Lend Earn doors (USDC · SOL, live APY) + the wallet's own deposits in them — what each is worth NOW
    (on-chain, compounding every block) and Jupiter's own earnings count. Deposits / withdrawals go through /familia-pools/earn."""
    rs = _rs()
    import lend_earn as _le
    if rs.time.time() - rs._frun_tok.get('at', 0) > 60 or not rs._frun_tok.get('rows'):
        code_, b_ = await rs._jl_lend('GET', 'earn/tokens')
        rows_ = _le.run_assets(b_) if code_ == 200 else []
        if rows_:
            rs._frun_tok.update(at=rs.time.time(), rows=rows_)
    assets_ = rs._frun_tok.get('rows') or []
    pos_ = []
    if assets_ and 32 <= len(address or '') <= 44:
        code_, b_ = await rs._jl_lend('GET', 'earn/positions', params={'users': address})
        live_ = _le.run_positions(b_, assets_) if code_ == 200 else []
        earned_ = {}
        for r_ in await rs.asyncio.gather(*[rs._jl_lend('GET', 'earn/earnings', params={'user': address, 'positions': p_['jl']}) for p_ in live_]):
            row_ = (r_[1] or [None])[0] if r_[0] == 200 and isinstance(r_[1], list) else None
            if isinstance(row_, dict):
                earned_[row_.get('address')] = row_.get('earnings')
        pos_ = _le.run_positions(b_, assets_, earned_) if live_ else []
    return {'assets': assets_, 'positions': pos_, 'minUsd': _le.RUN_MIN_USD, 'at': rs.time.time()}


@router.post('/api/reputation/familia/leverage')
async def familia_leverage_build(request: Request):
    """⚡ Open (lock + borrow) or close (repay all + withdraw all) a Jupiter Lend position WITHOUT leaving FEELESS: Jupiter builds the
    unsigned transaction, `lend_borrow.verify` opens it (the user pays + signs alone, only Jupiter Lend + Solana's own programs) and only
    then hands it back for the wallet to sign. FEELESS never holds the collateral, the loan or a key."""
    rs = _rs()
    import lend_borrow as _lb
    body = await request.json()
    try:
        act_, signer_, vid_, pid_, col_, lev_ = _lb.clean_request(body)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    if act_ != 'close':   # ⚖ LEGAL-1 (d): repaying + unlocking is an exit, never held
        rs._legal_hold(signer_, 'perps', request)
    if not await rs._ip_hit(rs._flv_hits, request, 30, 3600):
        raise rs.HTTPException(429, 'Too many leverage builds from here — try again in a while.')
    m_ = next((r_ for r_ in await rs._jl_markets() if r_['vaultId'] == vid_), None)
    if not m_:
        raise rs.HTTPException(400, 'Only the SOL · BTC · JUP leverage markets open from here.')
    plan_ = None
    if act_ == 'open':
        try:
            plan_ = _lb.plan(m_, col_, lev_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    code_, b_ = await rs._jl_borrow('POST', 'operate', json=_lb.body_for(act_, signer_, vid_, pid_, plan_))
    tx_ = (b_ or {}).get('transaction') if code_ == 200 else None
    if not tx_:
        raise rs.HTTPException(503 if code_ in (429, 503) else 502, f"Jupiter refused it: {str((b_ or {}).get('error') or (b_ or {}).get('message') or code_)[:120]}")
    ok_, bad_, progs_ = _lb.verify(tx_, signer_)
    if not ok_:
        print('leverage refused:', bad_, progs_)
        raise rs.HTTPException(502, f"Refused before your wallet saw it: {bad_}")
    return {'transaction': tx_, 'act': act_, 'nftId': (b_ or {}).get('nftId') or pid_, 'vaultId': vid_, 'coin': m_['coin'], 'plan': plan_,
            'programs': sorted({_lb.ALLOW[p_] for p_ in progs_})}


@router.post('/api/reputation/admin/arena/prime')
async def fuse_prime_admin(request: Request):
    """HQ › Arena: turn Prime on/off, set size, rotation (hours / coins), compound; reset deals 3 fresh cards."""
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    kick_real_keeper = False
    rs._prime_resp_clear()   # an owner write is never answered from a cached /fuses/prime
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        was = {t: (rs._prime.clean_cfg(pr.get('cfg') or {}).get('cycles') or {}).get(t) for t in rs._prime.TEMPLATES}
        was.update({t: (l.get('cycles') or {}).get(t) for t, l in (pr.get('locks') or {}).items()})
        inc = dict(body.get('cfg') or {})
        tc = {t: dict(v) for t, v in (rs._prime.clean_cfg(pr.get('cfg') or {}).get('tierCfg') or {}).items()}
        for t, row_ in (inc.pop('tierCfg', None) or {}).items() if isinstance(inc.get('tierCfg'), dict) else ():   # 🃏 one card's own exits
            if t in tc and isinstance(row_, dict):
                tc[t].update(row_)
        for k_ in rs._prime.TIER_KEYS:   # 🃏 exits are each card's OWN: a shared edit never overwrites them (no "all cards at once")
            inc.pop(k_, None)
        pr['cfg'] = rs._prime.clean_cfg({**(pr.get('cfg') or {}), **inc, 'tierCfg': tc})
        if isinstance(body.get('realCfg'), dict):   # 💵 the real card's own config (paper untouched); first edit copies today's paper config
            base = pr.get('realCfg') if isinstance(pr.get('realCfg'), dict) and pr.get('realCfg') else pr['cfg']
            pr['realCfg'] = rs._prime.clean_cfg({**base, **body['realCfg']})
            # 🪙 THE OWNER PICKS: every setting saved here is the owner's — the engine's self-fix never changes it afterwards
            pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {k for k in body['realCfg'] if isinstance(k, str)})[:60]
            # 🪜 switching the ladder ON starts a fresh climb (it sets every stage key); a setting tapped while it is on stays the owner's
            if body['realCfg'].get('ladder') is True:
                pr['ladderKeep'] = []
            elif pr['realCfg'].get('ladder'):
                pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {k for k in body['realCfg'] if k != 'ladder'})[:60]
        if body.get('lock') in rs._prime.TEMPLATES:   # 🔒 lock a tier's FULL config as it is now (engine, tunes and meta config never change it)
            locks = dict(pr.get('locks') or {})
            if isinstance(body.get('patch'), dict) and locks.get(body['lock']):   # ⚙ edit a LOCKED tier: change only its own frozen config
                base = {k: v for k, v in locks[body['lock']].items() if k != 'lockedAt'}
                locks[body['lock']] = {**rs._prime.clean_cfg({**base, **body['patch']}), 'lockedAt': rs.time.time()}
            elif body.get('on', True):
                if not locks.get(body['lock']):   # locking keeps an existing lock as it is (never overwritten by the shared config)
                    locks[body['lock']] = {**rs._prime.clean_cfg(rs._prime.tier_cfg(pr['cfg'], body['lock'])), 'lockedAt': rs.time.time()}   # its OWN exits + clock
            else:
                locks.pop(body['lock'], None)
            pr['locks'] = locks
        now_c = {t: (pr['cfg'].get('cycles') or {}).get(t) for t in rs._prime.TEMPLATES}
        now_c.update({t: (l.get('cycles') or {}).get(t) for t, l in (pr.get('locks') or {}).items()})
        for t, cards_ in [(t, pr.get('cards') or {}) for t in rs._prime.TEMPLATES if now_c.get(t) != was.get(t) and t in (pr.get('cards') or {})]:
            cards_[t] = rs._prime.owner_cycle(cards_[t], now_c[t], rs.time.time())   # 🎛 the owner's new cycle beats any auto safe / rescue fix
        hd = body.get('hold') or {}
        if hd.get('tpl') in rs._prime.TEMPLATES and (pr.get('cards') or {}).get(hd['tpl']):   # ✋ hold all: no swaps / re-shapes (stops + rug shield still run)
            c_ = pr['cards'][hd['tpl']]; c_['holdAll'] = bool(hd.get('on'))
            by_ = c_.pop('holdBy', None) if not hd.get('on') else None
            if by_ in ('proof', 'agents') and c_.get('real'):   # ▶ the owner releases a proof-gate / agent-control hold = their call: that switch goes off
                pr['realCfg'] = rs._prime.clean_cfg({**(pr.get('realCfg') or {}), 'proofGate' if by_ == 'proof' else 'agentControl': False})
            elif hd.get('on'):
                c_.pop('holdBy', None)   # a hold set by hand is the owner's — the gate never lifts it
            c_['events'] = (list(c_.get('events') or []) + [{'kind': 'hold', 'at': rs.time.time(), 'why': '✋ hold all — no swaps or re-shapes until released' if hd.get('on') else '▶ released — the engine swaps and re-shapes again'}])[-60:]
        ho = body.get('handsOff') or {}
        if ho.get('tpl') in rs._prime.TEMPLATES and (pr.get('cards') or {}).get(ho['tpl']):   # 🔒 hands-off lock (owner's own picks / hand swaps wait)
            pr['cards'][ho['tpl']] = rs._prime.set_hands_off(pr['cards'][ho['tpl']], ho.get('hours'), rs.time.time())
        if body.get('reset'):
            pr['cards'] = {}
        if body.get('fix') in rs._prime.TEMPLATES and ((pr.get('cards') or {}).get(body['fix']) or {}).get('real'):
            c_ = pr['cards'][body['fix']]   # 🔧 manual fix: re-fund every waiting buy from the SOL anchor NOW + fresh retries (no 60s / round wait)
            c_['rebuyAt'], c_['rebuyRound'] = 0, -1
            c_['events'] = (list(c_.get('events') or []) + [{'kind': 'fix', 'at': rs.time.time(), 'why': '🔧 fix buys/sells — waiting coins re-funded, fresh retries'}])[-60:]
        if body.get('redeal') in rs._prime.TEMPLATES:          # one tier fresh
            cur_ = (pr.get('cards') or {}).get(body['redeal'])
            if cur_ and cur_.get('real'):   # 💵 a real card re-deals its coins in place (same money, same run) — never a fresh $100 paper card
                cur_['redealNow'] = True
            else:
                (pr.get('cards') or {}).pop(body['redeal'], None)
        rs._json_save(rs.FUSE_HQ_PATH, d)
    if body.get('fix') in rs._prime.TEMPLATES:   # 🔧 (outside the HQ lock — never hold both locks at once)
        async with rs._fw_tick_lock, rs._fw_lock:
            fd = rs._fw_load(); b_ = fd['books'].get(body['fix'])
            if b_ is not None:
                b_['misses'] = {}   # every coin gets fresh retries (benched coins stay benched — they really failed the safety checks)
                b_['manualCashSol'] = 0.0   # 🔧 held cash goes back to work: Fix = "use this card's money" (✂ again to hold some apart)
                rs._fw_save(fd)
    if isinstance(body.get('callAlert'), dict):   # 🔔 the owner's early-caller alert: off (0) or the cap (in $K) a coin must be under
        ck_ = int(rs._fuse._f(body['callAlert'].get('capK')))
        if ck_ not in rs._pc.RUSH_CAPS_K:
            raise rs.HTTPException(400, 'Pick one of the listed caps.')
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); d.setdefault('prime', {})['callAlert'] = {'capK': ck_}; rs._json_save(rs.FUSE_HQ_PATH, d)
    if isinstance(body.get('trenchCfg'), dict):   # 🎛 the owner's trench settings (auto = engine widens by itself · own = these numbers)
        async with rs._admin_lock:
            # a PATCH: only the keys sent change (the editor used to post its whole, up-to-30s-old copy and put an old mode back)
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); d.setdefault('prime', {})['trenchCfg'] = rs._trench.clean_own({**((d.get('prime') or {}).get('trenchCfg') or {}), **body['trenchCfg']})
            rs._json_save(rs.FUSE_HQ_PATH, d)
        rs._trench_judge()             # the finalists already scanned are re-judged NOW by the new rules
        rs._trench_cache['at'] = 0.0   # … and a fresh scan runs on the next warm pass
    pk = body.get('pickSwap') or {}
    if not pk and (body.get('fillSeat') or {}).get('tpl'):   # 🪑 the owner's pick for the card's EMPTY seat: same checks as a swap pick
        pk = {**body['fillSeat'], 'pairAddress': '__seat__'}
    if pk.get('tpl') in rs._prime.TEMPLATES and pk.get('pairAddress'):   # 🎯 the owner picks WHICH coin comes in at the next round (or cancels)
        cand = None
        why_pick = ''
        if pk.get('to'):
            # only a coin the Gauntlet ranks RIGHT NOW (live price, real pool, not a dollar coin) can be picked
            ct_ = await rs._contenders_build()
            row = next((r for dv in (ct_.get('divisions') or []) for r in dv.get('rows') or [] if r.get('mint') == pk['to']), None)
            row = row or next((r for r in ct_.get('all') or [] if r.get('mint') == pk['to']), None)   # 🏁 any coin the Gauntlet ranks (Arena lens)
            row = row or next((r for r in rs._trench_cache.get('rows') or [] if r.get('mint') == pk['to']), None)   # 🗑 a passing trench coin
            if not row and not pk.get('toPair'):   # 📋 a pasted contract address alone: its deepest live pool is looked up (Jupiter search knows every pool)
                try:
                    async with rs.httpx.AsyncClient(timeout=8) as http_:
                        jp_ = await rs._launchpad_board.jup_lookup(http_, pk['to'])
                    if jp_ and jp_.get('pairAddress'):
                        pk['toPair'] = jp_['pairAddress']
                except Exception as e:
                    print('pick lookup:', str(e)[:80])
                if not pk.get('toPair'):
                    raw_ = next((p_ for p_ in rs._open_pairs if (p_.get('baseToken') or {}).get('address') == pk['to']), None)
                    pk['toPair'] = (raw_ or {}).get('pairAddress')
            if not row and pk.get('toPair'):   # 🔎 any coin from the Lab lenses / search: verified LIVE on its own pool right now
                lp = (await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': pk['toPair'], 'mint': pk.get('to')}])).get(pk['toPair']) or {}
                lp = rs._fuse.with_curve(lp)   # 🆕 the owner may pick a coin still on Pump's curve (the keeper's quote checks still decide)
                fcfg_ = rs._fw.clean_cfg(rs._fw_peek().get('cfg') or {})
                raw_ = next((p_ for p_ in rs._open_pairs if (p_.get('baseToken') or {}).get('address') == pk['to']), None)   # 🚪 a launch coin the open list shows
                if raw_ is not None and (lp.get('baseToken') or {}).get('address') != pk['to']:
                    lp = rs._fuse.with_curve(raw_)   # the live lookup missed (busy source / pool not indexed yet): the feed's own pair for this coin stands in
                # 🗑 a launch coin is held to the lower of the owner's pick floor and the trench floor — and keeps that floor at the keeper
                floor_ = min(fcfg_['pickMinLiqUsd'], fcfg_['trenchMinLiqUsd']) if raw_ is not None else fcfg_['pickMinLiqUsd']
                row = rs._pick_row(lp, pk['to'], floor_)
                if row and raw_ is not None and row['liq'] < fcfg_['pickMinLiqUsd']:
                    row['trenchOnly'] = True
                why_pick = '' if row else rs._pick_why(lp, pk['to'], floor_)
            if not row:
                raise rs.HTTPException(400, why_pick or 'That coin is not on any live list right now — search it by ticker or paste its address.')
            _age_c = next((r.get('ageH') for r in rs._runner_cands if r.get('mint') == row['mint'] and r.get('ageH') is not None), row.get('ageH'))
            cand = {'mint': row['mint'], 'pairAddress': row['pairAddress'], 'symbol': row.get('symbol'), 'price': row.get('price'), 'liquidityUsd': row.get('liq'),
                    **({'ageH': round(rs._fuse._f(_age_c), 2)} if _age_c is not None else {}),
                    **({'trenchOnly': True} if row.get('trenchOnly') else {}),
                    **({'now': True} if pk.get('now') and pk['pairAddress'] != '__seat__' else {}),
                    **({'tag': '🤝 agents suggested · your pick'} if pk.get('via') == 'agents' else {}),   # 🤝 a coin taken from the agents' alert: its own record
                    'division': next((dv['key'] for dv in (rs._contenders_cache.get('data') or {}).get('divisions') or [] if any(r.get('mint') == row['mint'] for r in dv.get('rows') or [])), None)}
        # ✅ VERIFIED PICKS (real cards, on by default): a hand-picked coin is queued only once it passes every safety check.
        # 2026-10-06: a hand pick rugged 3.5 minutes after the bell (−98%) — picks used to skip every engine check.
        _pv_miss = []
        _pr = rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}
        if cand and ((_pr.get('cards') or {}).get(pk['tpl']) or {}).get('real') and rs._prime.clean_cfg(_pr.get('realCfg') or {})['pickVerify']:
            _pv_ok, _pv_miss, _pv_c = await rs._pick_verify(cand['mint'], cand['pairAddress'])
            _pv_miss = list(_pv_miss or []) + rs._prime.chase_why(_pv_c)   # 🔥 a warning, never a block: you can still pick it
            _eg = rs._prime.entry_gate({**(_pv_c or {}), 'pairAddress': cand.get('pairAddress')}) if not cand.get('trenchOnly') else None
            if _eg and _eg not in ' '.join(_pv_miss):
                _pv_miss.append(f"not a clean entry: {_eg}")   # 🎯 the same gate the engine uses — a warning on your picks, never a block
            try:   # 🎯 … quoting the owner's OWN record on this kind of entry (only when it lost, ≥ 8 picks)
                import owner_edge as _oe
                _pv_miss += _oe.warnings({'chg5m': (_pv_c or {}).get('chg5m'), 'vol1h': (_pv_c or {}).get('vol1h'), 'liq': (_pv_c or {}).get('liq')}, rs._owner_edge_rec())
            except Exception:
                pass
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(pk['tpl'])
            if not card:
                raise rs.HTTPException(404, 'No card for that tier yet.')
            if cand and card.get('real'):   # 💵 real money keeps its own floor: the pick must be buyable
                floor = rs._fw.liq_floor(rs._fw_peek().get('cfg') or {}, trench=bool(cand.get('trenchOnly')), picked=True)   # 🗑 trench picks use the trench floor
                if rs._fuse._f(cand.get('liquidityUsd')) < floor:
                    raise rs.HTTPException(400, f"${cand['symbol']} pool is ${rs._fuse._f(cand.get('liquidityUsd')):,.0f} — under the ${floor:,.0f} real-buy floor (Edit Fuse › Limits).")
            # ⚠ WARN, NEVER BLOCK (owner's rule: "warn users, don't stop them"): a pick that fails a check comes back as a warning
            # (HTTP 409 + the list); the owner taps "pick anyway" and the same pick is sent again with `ack` → it goes through,
            # marked `ack` so the pre-bell re-check leaves it alone. Nothing is ever silently refused.
            if cand and card.get('real') and _pv_miss and not pk.get('ack'):
                raise rs.HTTPException(409, f"⚠ ${cand['symbol']} did not pass: {'; '.join(_pv_miss[:5])}.")
            if cand and pk.get('ack') and _pv_miss:
                cand['ack'] = True
            if cand and rs._prime.hands_off_left(card, rs.time.time()):
                raise rs.HTTPException(400, f"🔒 Hands-off lock: {int(rs._prime.hands_off_left(card, rs.time.time()) // 60) + 1} min left — picks wait. The engine and your stops keep working.")
            # 🎯 THE OWNER'S PICK IS NEVER COOLED: cool-downs (no back-to-back, left at a loss, removed by the owner) limit the ENGINE
            # only — the owner sells off a peak and buys the same coin back at its new level whenever they choose
            if cand and pk['pairAddress'] != '__seat__':
                rs._cook_warn(card, pk['pairAddress'], pk.get('ack'))   # ⏳ swapping out a coin you bought minutes ago asks first
            if cand and rs._fuse._f(pk.get('limitPx')) > 0:   # 🎯 BUY LIMIT: every check above already ran — it waits for the price, then takes this same path
                try:
                    cards[pk['tpl']] = rs._lim.add(card, rs._lim.make('buy', pk['limitPx'], rs.time.time(), pk.get('hours') or 24, mint=cand['mint'], pair=cand['pairAddress'],
                                                                symbol=cand.get('symbol'), target=pk['pairAddress'], cand={k_: v_ for k_, v_ in cand.items() if k_ != 'now'}))
                except ValueError as e:
                    raise rs.HTTPException(400, str(e))
                rs._json_save(rs.FUSE_HQ_PATH, d)
                return {'ok': True, 'limit': rs._lim.word(cards[pk['tpl']]['limits'][-1])}
            try:
                cards[pk['tpl']] = rs._prime.queue_seat(card, cand, more=bool(pk.get('more'))) if pk['pairAddress'] == '__seat__' else rs._prime.queue_swap(card, pk['pairAddress'], cand)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.FUSE_HQ_PATH, d)
        if cand and (cand.get('now') or pk['pairAddress'] == '__seat__'):   # ⚡ swap in NOW / 🪑 your seat pick: run the engine pass at once (it is locked — never two at a time)
            rs.asyncio.create_task(rs._prime_tick(rs.time.time()))
        if cand:   # 👤 the pick is in: note what the coin looked like (teaches the paper cards that pick like the owner)
            await rs._pick_style_note(cand['mint'], cand.get('symbol'), cand.get('pairAddress'))
    ls_ = body.get('limitSell') or {}; lc_ = body.get('limitCancel') or {}
    if ls_.get('tpl') in rs._prime.TEMPLATES or lc_.get('tpl') in rs._prime.TEMPLATES:   # 🎯 SELL LIMIT (take ≥ / stop ≤) on a coin of the card · cancel any limit
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            tpl_ = ls_.get('tpl') or lc_.get('tpl'); card = cards.get(tpl_)
            if not card:
                raise rs.HTTPException(404, 'No card for that tier yet.')
            try:
                if lc_:
                    cards[tpl_] = rs._lim.cancel(card, lc_.get('id'))
                else:
                    l_ = next((x for x in card.get('legs') or [] if x.get('pairAddress') == ls_.get('pairAddress') and not x.get('placeholder')), None)
                    if not l_:
                        raise ValueError('That coin is not on this card.')
                    cards[tpl_] = rs._lim.add(card, rs._lim.make('sell', ls_.get('px'), rs.time.time(), ls_.get('hours') or 24, mint=l_.get('mint'), pair=l_['pairAddress'],
                                                           symbol=l_.get('symbol'), pct=ls_.get('pct'), stop=ls_.get('stop')))
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.FUSE_HQ_PATH, d)
        return {'ok': True, 'limits': [rs._lim.word(x) for x in cards[tpl_].get('limits') or []]}
    hm = body.get('human') or {}
    if hm.get('tpl') in rs._prime.TEMPLATES:   # 👤 switch a PAPER card to / from the owner's pick style
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr_ = d.setdefault('prime', {})
            cur_ = set(rs.HUMAN_TIERS_DEFAULT if pr_.get('humanTiers') is None else pr_['humanTiers'])
            (cur_.add if hm.get('on') else cur_.discard)(hm['tpl'])
            pr_['humanTiers'] = sorted(cur_); rs._json_save(rs.FUSE_HQ_PATH, d)
    rb = body.get('rebuy') or {}
    if rb.get('tpl') in rs._prime.TEMPLATES and rb.get('pairAddress'):   # 🔄 sell this coin and buy it straight back at today's price (new entry)
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(rb['tpl'])
            if not card:
                raise rs.HTTPException(404, 'No card for that tier yet.')
            px_rb = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': rb['pairAddress']}])
            try:
                cards[rb['tpl']] = rs._prime.rebuy_out(card, rb['pairAddress'], px_rb, {}, rs.time.time())
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.FUSE_HQ_PATH, d)
            kick_real_keeper = bool(card.get('real'))
    rep = body.get('replace') or {}
    if rep.get('tpl') in rs._prime.TEMPLATES and rep.get('pairAddress'):   # ⇄ one coin on one Prime card
        pools, runners, anchors = await rs._prime_candidates()
        # ⇄ a manual swap picks only BUYABLE coins (same gates as the engine): pool ≥ the real-buy floor, not benched, not on another tier
        fw_cfg = rs._fw_load().get('cfg') or {}
        bench = set().union(*[rs._fw.benched(b, rs.time.time()) for b in (rs._fw_peek().get('books') or {}).values()] or [set()])
        def _lq(x):
            v = x.get('liquidity'); return rs._fuse._f(v.get('usd') if isinstance(v, dict) else v) or rs._fuse._f(x.get('liq')) or rs._fuse._f(x.get('liquidityUsd'))
        other = {l.get('mint') for t, cc in rs._prime_cards().items() if t != rep['tpl'] for l in cc.get('legs') or [] if l.get('role') != 'anchor'}
        ok_ = lambda xs: [x for x in xs if _lq(x) >= rs._fw.liq_floor(fw_cfg, x.get('arena')) and x.get('mint') not in bench]
        pools, runners = ok_(pools), sorted(ok_(runners), key=lambda x: x.get('mint') in other)
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(rep['tpl'])
            rs._cook_warn(card, rep['pairAddress'], rep.get('ack'))   # ⏳ a hand swap of a fresh coin asks first
            if not card:
                raise rs.HTTPException(404, 'No card for that tier yet.')
            if rs._prime.hands_off_left(card, rs.time.time()):
                raise rs.HTTPException(400, f"🔒 Hands-off lock: {int(rs._prime.hands_off_left(card, rs.time.time()) // 60) + 1} min left — hand swaps wait. The engine and your stops keep working.")
            px = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in card['legs']])
            try:
                old_m = {l.get('mint') for l in card['legs']}
                cfg_r = rs._prime_real_cfg(d.get('prime') or {}) if card.get('real') else pr['cfg']
                cool_r = rs._prime.cooling(card, rs.time.time(), cfg_r['rotateHours'], px)   # 🧊 a hand swap never brings back a coin that just left
                pools, runners = [x for x in pools if x.get('mint') not in cool_r], [x for x in runners if x.get('mint') not in cool_r]
                anchors_r = anchors
                if card.get('real'):   # ⏳ the hand swap is a door too: the card's min age and no dollar-named tickers
                    lim_ = rs._fuse._f(cfg_r.get('runnerMinAgeH'))
                    runners = [x for x in runners if not rs._fw.dollar_named(x.get('symbol')) and not (lim_ > 0 and x.get('ageH') is not None and rs._fuse._f(x.get('ageH')) < lim_)]
                if card.get('real'):   # 🧹 ⇄ takes CLEAN coins only: the engine's 🏆 Best list first, then coins with no rug / wash / blow-off read
                    runners = rs._swap_clean(runners)
                if card.get('real') and cfg_r.get('newOnly'):
                    # 🆕 NEW COINS ONLY: ⇄ on ANY seat brings a launch coin — it used to replace a coin with the best of the SAME KIND
                    # ($ORCA / $TRUMP again and again), then the biggest 1h pump (washed / already-ran coins, owner 2026-10-09)
                    pools, anchors_r = runners, runners
                cards[rep['tpl']] = rs._prime.note_dropped(card, rs._prime.replace_leg(card, rep['pairAddress'], px, pools, runners, anchors_r, cfg_r, rs.time.time()), rs.time.time(), cfg_r['rotateHours'], px)
                if card.get('real') and cfg_r.get('newOnly'):
                    for l in cards[rep['tpl']]['legs']:
                        if l.get('mint') not in old_m:
                            l['role'] = 'runner'   # a launch coin is never a "major": it keeps its stop, rug shield and rotation
                kick_real_keeper = bool(card.get('real'))   # manual ⇄ on real money runs NOW; keeper enforces sell-confirm-before-buy
                for l in cards[rep['tpl']]['legs']:   # 👆 YOUR pick: carried through the next re-shape (it once got sold 4 min later)
                    if l.get('mint') not in old_m:
                        l['picked'] = True
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.FUSE_HQ_PATH, d)
    rh = body.get('releaseHeld') or {}
    if rh.get('tpl') in rs._prime.TEMPLATES:   # ↩ the owner's held-for-you cash goes back into the card's coins
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            if not cards.get(rh['tpl']):
                raise rs.HTTPException(400, 'No such card.')
            try:
                px_h = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in cards[rh['tpl']].get('legs') or [] if l.get('pairAddress') == rh.get('pairAddress')]) if rh.get('pairAddress') else {}
                cards[rh['tpl']], _held = rs._prime.release_held(cards[rh['tpl']], rs.time.time(), rh.get('pairAddress'), px_h)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.FUSE_HQ_PATH, d)
            kick_real_keeper = kick_real_keeper or bool(cards[rh['tpl']].get('real'))
    ms = body.get('manualSell') or {}
    if ms.get('tpl') in rs._prime.TEMPLATES and (ms.get('pairAddress') or ms.get('all')):
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(ms['tpl'])
            if not card or not card.get('real'):
                raise rs.HTTPException(400, 'Manual sell-to-cash is only available on a real card.')
            if not ms.get('all') and rs._fuse._f(ms.get('pct') or 100) >= 100:
                rs._cook_warn(card, ms['pairAddress'], ms.get('ack'))   # ⏳ selling a fresh coin WHOLE asks first (trims never do)
            px = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in card.get('legs') or []])
            try:
                # ✂ the owner's manual sell: one coin or every coin, any % (25 / 50 / 100) — the only way principal ever leaves a card
                pairs_ms = [l['pairAddress'] for l in card.get('legs') or [] if l.get('mint') != rs._fw.SOL_MINT and rs._fuse._f(l.get('units')) > 0] if ms.get('all') else [ms['pairAddress']]
                for pa in pairs_ms:
                    card = rs._prime.sell_leg_to_cash(card, pa, px, rs.time.time(), ms.get('pct') or 100)
                cards[ms['tpl']] = card
                kick_real_keeper = True
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.FUSE_HQ_PATH, d)
    du = body.get('duel') or {}
    if du.get('tpl') in rs._prime.TEMPLATES:   # ⚔ the owner picks who their real card duels next (None = the best other card); the running duel is called off
        st_ = rs._json_load(rs.DUELS_PATH, {}); pk_ = dict(st_.get('pick') or {})
        if du.get('vs') in rs._prime.TEMPLATES and du['vs'] != du['tpl']:
            pk_[f"prime:{du['tpl']}"] = f"prime:{du['vs']}"
        else:
            pk_.pop(f"prime:{du['tpl']}", None)
        rs._json_save(rs.DUELS_PATH, {**st_, 'pick': pk_}); rs._proof_cache['at'] = 0.0
    sk = body.get('skim') or {}
    if sk.get('tpl') in rs._prime.TEMPLATES and sk.get('pairAddress'):   # 💰 take ONE coin's profit now (stake keeps riding) → other coins, or held as cash
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(sk['tpl'])
            if not card:
                raise rs.HTTPException(404, 'No card for that tier yet.')
            px = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in card.get('legs') or []])
            try:
                cards[sk['tpl']] = (rs._prime.stake_leg(card, sk['pairAddress'], px, {}, rs.time.time(), sk.get('to') or 'cash') if sk.get('stake')   # 🏠 the initial out, profit rides
                                    else rs._prime.skim_leg(card, sk['pairAddress'], px, {}, rs.time.time(), sk.get('to') or 'card', hold=sk.get('rounds')))
                kick_real_keeper = bool(card.get('real'))
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.FUSE_HQ_PATH, d)
    lg = body.get('leg') or {}
    if lg.get('tpl') in rs._prime.TEMPLATES and lg.get('pairAddress'):   # ❄ freeze / own stop mode for one coin on one tier card
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            if not cards.get(lg['tpl']):
                raise rs.HTTPException(404, 'No card for that tier yet.')
            try:
                cards[lg['tpl']] = rs._prime.set_leg(cards[lg['tpl']], lg['pairAddress'], lg.get('frozen'), lg.get('slMode'), lg.get('tp'), lg.get('sl'), lg.get('flowExit'), now=rs.time.time(), certified=lg.get('certified'), gstop=lg.get('gstop'), pick_lock=lg.get('pickLock'))
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.FUSE_HQ_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, admin, 'arena-prime', rs.json.dumps(pr['cfg'])[:120] + (' reset' if body.get('reset') else '') + (f" manualSell {rs.json.dumps(ms)[:60]}" if ms else '') + (f" leg {rs.json.dumps(lg)[:60]}" if lg else '')); rs._admin_save(ad)
    if body.get('reset') or body.get('redeal'):
        await rs._prime_tick(rs.time.time())
    if kick_real_keeper:
        rs._fw_kick_now()   # manual real-money ⇄ / ✂: the keeper starts NOW in the background — the button answers at once (it used to wait for every sell to confirm)
    return {'cfg': pr['cfg'], 'cards': await rs._prime_view()}


@router.post('/api/reputation/admin/circle/profile')
async def circle_profile_save(request: Request, body: dict):
    """Owner: edit the public profile of one of YOUR Circle wallets (name, @handle, bio, avatar, banner). Audited."""
    rs = _rs()
    me = rs._require_owner(request)
    addr = str(body.get('address') or '')
    ws = (await rs._circle('GET', '/wallets')).get('wallets') or []
    if addr not in {w.get('address') for w in ws}:
        raise rs.HTTPException(403, 'Only your own Circle wallets can be edited here.')
    async with rs._profile_lock:
        d = rs._profiles_load()
        prev = d['profiles'].get(addr, {})
        clean = rs._clean_profile(rs.circle_profile_merge(prev, body.get('profile') or {}))
        if clean.get('handle') and any(a != addr and (v or {}).get('handle') == clean['handle'] for a, v in d['profiles'].items()):
            raise rs.HTTPException(409, f"@{clean['handle']} is taken.")
        row_ = rs._prof().update(addr, lambda cur: {**(cur or {}), **clean, 'lastTs': rs.time.time(), 'updatedAt': rs.time.time(), 'editedBy': me})
    ad = rs._admin_load(); rs._audit(ad, me, 'circle-profile', f'{addr[:6]}… {clean.get("handle") or clean.get("name") or ""}'); rs._admin_save(ad)
    return {'ok': True, 'address': addr, 'profile': row_}


@router.get('/api/reputation/admin/fuse-wallet')
async def fuse_wallet_view(request: Request):
    """HQ › Fuse › 👛 Fuse wallet: the wallet's funds, each funded tier card's real book, caps, calibration and the audit trail."""
    rs = _rs()
    rs._require_owner(request)
    await rs._fw_signer_check()
    d = rs._fw_load(); cfg = rs._fw.clean_cfg(d.get('cfg') or {})
    wallets, bal, err = [], None, None
    try:
        wallets = [w for w in await rs._circle_wallets_live() if str(w.get('blockchain', '')).startswith('SOL')]
    except rs.HTTPException as e:
        err = str(e.detail)
    if cfg['address']:
        try:
            bal = await rs._fw_balances(cfg['address'])
            rs._FW_BAL.update(bal=bal, at=rs.time.time(), addr=cfg['address'])
        except Exception as e:   # 🛟 RPC busy (rate limit): never show an EMPTY wallet — last good read, else Circle's own balances
            bal = rs._FW_BAL.get('bal') if rs._FW_BAL.get('addr') == cfg['address'] else None
            if bal is None:
                bal = rs._fw.circle_balances(wallets, cfg['address'])
            if bal is None:
                err = err or f'balance read failed: {str(e)[:80]}'
            else:
                bal = {**bal, 'stale': True}
    sol_px = await rs._sol_usd_live()
    cards = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    market_rows = rs._fw_market_rows(cards, d.get('books') or {})
    px = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in market_rows]) if market_rows else {}
    jup = await rs._jup_prices([l.get('mint') for l in market_rows]) if market_rows else {}
    px.update({l['pairAddress']: jup[l['mint']] for l in market_rows if jup.get(l.get('mint'))})
    full_hq = rs._fw_full_ledger()   # 🧾 every row, not the trimmed KV copy
    books = {tid: {**b, 'valueUsd': rs._fw.book_value(b, px, sol_px), 'label': (cards.get(tid) or {}).get('label') or tid, **rs._fw_led_memo('tot', tid, lambda L: rs._fw.totals(L, tid))} for tid, b in d['books'].items()}
    recoverable = []
    if bal and bal.get('source') != 'circle':
        booked = {}
        for b in d['books'].values():
            for mint, leg in (b.get('legs') or {}).items():
                booked[mint] = booked.get(mint, 0) + int(rs._fuse._f(leg.get('atoms')))
        for mint, held in (bal.get('tokens') or {}).items():
            excess = int(rs._fuse._f(held)) - int(booked.get(mint, 0))
            if excess <= 0:
                continue
            hist = [r for r in d['ledger'] if r.get('mint') == mint and r.get('card') in d['books'] and r.get('pair')]
            if not hist:
                continue   # never offer unrelated wallet tokens
            last = hist[-1]
            recoverable.append({'card': last['card'], 'mint': mint, 'symbol': last.get('symbol') or mint[:6],
                                'pair': last.get('pair'), 'atoms': excess, 'decimals': int((bal.get('decimals') or {}).get(mint) or last.get('decimals') or 0),
                                'lastStatus': last.get('status'), 'lastErr': (last.get('err') or '')[:100], 'lastAt': last.get('at')})
    rent_returned = round(sum(rs._fuse._f(r.get('sol')) for r in full_hq
                              if r.get('side') == 'close' and r.get('status') == 'sent'), 9)
    funded_sol = round(sum(rs._fuse._f(r.get('sol')) for r in full_hq
                           if r.get('side') == 'topup' and r.get('status') == 'done'), 9)
    dep_doc = rs._json_load(rs.FUSE_DEPOSITS_PATH, {})
    dep_rows = (dep_doc.get('rows') or []) if dep_doc.get('address') == cfg.get('address') else []
    return {'cfg': cfg, 'signer': rs._fw_signer_ready(), 'wallets': wallets, 'balances': bal, 'solUsd': sol_px, 'error': err,
            'freeSol': rs._fw.free_sol((bal or {}).get('sol'), d['books'], cfg['reserveSol']) if bal else None,
            'topupSol': rs._fw.free_for_topup((bal or {}).get('sol'), d['books'], cfg['reserveSol'], rs._fuse._f((rs._fw_rent_parked or {}).get('sol'))) if bal else None,   # what a top-up may assign: free SOL + the part of the reserve parked as refundable rent
            # Unassigned SOL is fungible: it can include owner deposits and token-account rent returned after card sells.
            # Expose both audit totals so the UI never presents it as known-new owner funding or card profit.
            'solProvenance': {'cardFundedSol': funded_sol, 'rentReturnedSol': rent_returned,
                              **(rs._fw.sol_story(dep_rows, d['books'], cfg['reserveSol'], bal.get('sol'), sum(rs._fuse._f(b.get('valueUsd')) for b in books.values()) / sol_px - sum(rs._fuse._f(b.get('sol')) + rs._fuse._f(b.get('bankSol')) for b in d['books'].values())) if bal and sol_px and dep_rows else {}),
                              'deposits': dep_rows[-12:][::-1]},
            'missing': rs._fw.reconcile((bal or {}).get('tokens'), d['books']) if bal and bal.get('source') != 'circle' else [],   # Circle rows have no mints
            'books': books, 'tiers': {k: v['label'] for k, v in rs._prime.TEMPLATES.items()}, 'recoverable': recoverable, 'calibration': rs._fw_calibration(d),
            'paperMatch': rs._fw.paper_match(d.get('quoteAudit')), 'quoteAudit': (d.get('quoteAudit') or [])[-20:][::-1],
            'totals': rs._fw_led_memo('tot', None, lambda L: rs._fw.totals(L)), 'ledger': d['ledger'][-200:][::-1]}


@router.post('/api/reputation/admin/colony')
async def admin_colony_set(request: Request):
    """🐝 Owner: create the pot's Circle wallet (one, ever) · lock today's value in as principal (only ever up) · set the guards.
    Nothing here sends money: payouts are a proposal the owner approves after the timelock."""
    rs = _rs()
    import colony as _col
    me_ = rs._require_owner(request)
    body = await request.json() or {}
    act = str(body.get('action') or '')
    d = rs._json_load(rs.COLONY_PATH, {}); now = int(rs.time.time())
    if act == 'create':
        if not (d.get('wallet') or {}).get('address'):
            import uuid as _uuid
            r_ = await rs._circle('POST', '/wallets', {'blockchain': 'SOL', 'name': 'FEELESS colony pot', 'key': str(_uuid.uuid5(_uuid.NAMESPACE_URL, 'feeless-colony-pot'))}, agent=True)
            w_ = (r_ or {}).get('wallet') or {}
            if not w_.get('address'):
                raise rs.HTTPException(502, 'Circle did not make the wallet.')
            d['wallet'] = {'address': w_['address'], 'id': w_.get('id'), 'at': now, 'by': str(me_)[:44]}
    elif act == 'lock':
        if not (d.get('wallet') or {}).get('address'):
            raise rs.HTTPException(400, 'Create the pot wallet first.')
        val = await rs._colony_value(d['wallet']['address'])
        if not val:
            raise rs.HTTPException(503, "Couldn't read the pot's balance — nothing changed.")
        d['principalUsd'] = _col.raise_floor(d.get('principalUsd'), val['usd'])
    elif act == 'policy':
        d['policy'] = _col.clean_policy({**(d.get('policy') or {}), **(body.get('policy') or {})})
    elif act == 'pool_preview':   # 🌊 build + simulate the Meteora pool (free) — remembered so 'pool_create' may follow with the SAME amounts
        args_, r_ = await rs._colony_pool_build(d, body)
        d['poolDraft'] = {k: args_[k] for k in ('mintA', 'mintB', 'amountA', 'amountB', 'feeBps', 'compoundingBps', 'lock')} | {'at': now, 'ok': bool(r_.get('ok')) and r_.get('sim', {}).get('err') is None,
                          'pool': r_.get('pool'), 'price': r_.get('price'), 'err': r_.get('error') or (r_.get('sim') or {}).get('err'), 'logs': (r_.get('sim') or {}).get('logs')}
    elif act == 'pool_create':   # 🌊 the real thing: only after a clean preview of the same amounts in the last 10 min — Circle signs as the colony wallet, we broadcast
        dr_ = d.get('poolDraft') or {}
        same_ = dr_.get('amountA') == float(body.get('amountA', body.get('feecat')) or 0) and dr_.get('amountB') == float(body.get('amountB', body.get('sol')) or 0) and dr_.get('mintA') == str(body.get('mintA') or dr_.get('mintA')) and dr_.get('mintB') == rs.POOL_QUOTES.get(str(body.get('quote') or 'SOL').upper(), ('',))[0] and dr_.get('feeBps') == int(body.get('feeBps') or 100) and dr_.get('lock') == (body.get('lock') is True)
        if not (dr_.get('ok') and same_ and now - int(dr_.get('at') or 0) < 600):
            raise rs.HTTPException(400, 'Preview these exact amounts first (the simulation must pass) — then create within 10 minutes.')
        args_, r_ = await rs._colony_pool_build(d, body)
        if not r_.get('ok') or (r_.get('sim') or {}).get('err') is not None:
            raise rs.HTTPException(400, f"The fresh simulation failed — nothing was sent ({str(r_.get('error') or r_.get('sim', {}).get('err'))[:120]}).")
        sg_ = await rs._circle('POST', '/sign', {'walletId': d['wallet']['id'], 'rawTransaction': r_['tx'], 'memo': 'FEELESS colony pool (Meteora)'}, agent=True)
        if not (sg_ or {}).get('signedTransaction'):
            raise rs.HTTPException(502, 'Circle did not sign the pool — nothing was sent.')
        async with rs.httpx.AsyncClient(timeout=20) as http_:
            took_ = await rs._rpc_broadcast(http_, sg_['signedTransaction'])
        made_ = {'address': r_['pool'], 'platform': 'Meteora DAMM v2', 'at': now, 'sig': sg_.get('signature') or sg_.get('txHash'), 'nodes': took_,
                 'mintA': args_['mintA'], 'mintB': args_['mintB'], 'amountA': args_['amountA'], 'amountB': args_['amountB'], 'feeBps': args_['feeBps'], 'lock': args_['lock']}
        if (d.get('pool') or {}).get('address'):   # the first stays the Collective's main pool
            d['poolsMore'] = (d.get('poolsMore') or []) + [made_]
        else:
            d['pool'] = made_
        rs._cpool.update(rs.POOL_PATH, lambda st: rs._stake.add_pool(st, 'meteora', str(body.get('name') or 'New pool')[:32], r_['pool'], f"Opened {args_['amountA']} + {args_['amountB']}", rs.time.time()))
        d.pop('poolDraft', None)
    else:
        raise rs.HTTPException(400, 'Unknown colony action.')
    d['log'] = (d.get('log') or [])[-40:] + [{'at': now, 'what': act, 'by': str(me_)[:8], 'principalUsd': d.get('principalUsd'), 'policy': d.get('policy')}]
    rs._json_save(rs.COLONY_PATH, d)
    return await rs._colony_view()


@router.post('/api/reputation/admin/fuse-wallet/preview')
async def fuse_wallet_preview(request: Request):
    """Dry run: the swaps a $ amount on one tier would need right now, each with a REAL Jupiter quote. Never signs or sends."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json()
    tid, usd = body.get('tpl'), rs._fuse._f(body.get('usd'))
    cards = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    if tid not in rs._prime.TEMPLATES or not cards.get(tid) or not 1 <= usd <= 50000:
        raise rs.HTTPException(400, 'Pick a dealt tier and $1–$50,000.')
    card, sol_px = cards[tid], await rs._sol_usd_live()
    px = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in card['legs']])
    scale = usd / (rs._prime.value({**card, 'walletUsd': 0, 'parked': {}}, px) or 1)
    want = {**card, 'legs': [{**l, 'units': l['units'] * scale} for l in card['legs']]}
    cfg = {**rs._fw_cfg(), 'maxSwapUsd': 10000, 'minOrderUsd': 0.25}
    status = rs._fw.paper_status(card, px, usd)
    rows = []
    for o in rs._fw.orders(tid, want, rs._fw.new_book(usd, sol_px, rs.time.time()), px, sol_px, cfg, rs.time.time()):
        try:
            q = await rs._fw_quote(o, cfg)
            out = int(q.get('outAmount') or 0)
            rows.append({**o, 'impactPct': round(rs._fuse._f(q.get('priceImpactPct')) * 100, 3), 'outAmount': out, 'route': [r.get('swapInfo', {}).get('label') for r in q.get('routePlan') or []][:3]})
        except rs.HTTPException as e:
            rows.append({**o, 'err': str(e.detail)[:120]})
    held_mints = set()
    if rs._fw_cfg()['address']:
        try:
            held_mints = set((await rs._fw_balances(rs._fw_cfg()['address']))['tokens'])
        except Exception:
            pass
    new_coins = len({o['mint'] for o in rows if o.get('side') == 'buy' and o['mint'] not in held_mints})
    net_usd, rent_usd = round(len(rows) * 0.00006 * sol_px, 4), round(new_coins * 0.00204 * sol_px, 4)
    return {'orders': rows, 'card': status, 'solUsd': sol_px, 'networkUsdEst': net_usd, 'rentUsdEst': rent_usd, 'newCoins': new_coins,
            'feesUsdEst': round(net_usd + rent_usd, 4), 'cardUsd': usd,
            'note': 'Fund continues THIS card with real money: same coins, same phase, same clock and config — only the $ and the start time change.'}


@router.post('/api/reputation/admin/fuse-wallet/topup')
async def fuse_wallet_topup(request: Request):
    """Owner only: fund (or add to) one tier card from the Fuse wallet's free SOL. A top-up RESETS the card as a new real run."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    tid, usd = body.get('tpl'), round(rs._fuse._f(body.get('usd')), 2)
    cfg = rs._fw_cfg()
    if tid not in rs._prime.TEMPLATES or usd < 1:
        raise rs.HTTPException(400, 'Pick a tier and at least $1.')
    if not cfg['armed'] or not rs._fw_signer_ready():
        raise rs.HTTPException(400, 'Arm the Fuse wallet first (signing must be enabled).')
    bal, sol_px = await rs._fw_balances(cfg['address']), await rs._sol_usd_live()
    now = rs.time.time()
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        d = rs._fw_load()
        parked_ = rs._fuse._f((rs._fw_rent_parked or {}).get('sol'))   # rent parked in coin accounts = the reserve's own money, back on the next sweep
        free0_ = rs._fw.free_for_topup(bal['sol'], d['books'], cfg['reserveSol'], parked_)
        if usd / sol_px > free0_ + 1e-6:
            raise rs.HTTPException(400, f"Only ${free0_ * sol_px:.2f} of SOL in the Fuse wallet is free to assign right now (wallet {bal['sol']:.4f} SOL · cards hold {sum(rs._fuse._f(b_.get('sol')) + rs._fuse._f(b_.get('bankSol')) for b_ in d['books'].values()):.4f} · fee reserve {cfg['reserveSol']} of which {parked_:.4f} is parked as refundable rent).")
        cards = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
        card = cards.get(tid)
        px = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in (card or {}).get('legs') or []]) if card else {}
        jup = await rs._jup_prices([l.get('mint') for l in (card or {}).get('legs') or []]) if card else {}
        if card:
            px.update({l['pairAddress']: jup[l['mint']] for l in card.get('legs') or [] if jup.get(l.get('mint'))})
        first = tid not in d['books']
        cur = rs._fw.book_value(d['books'][tid], px, sol_px) if not first else 0
        if cur + usd > cfg['maxCardUsd']:
            raise rs.HTTPException(400, f"Over the ${cfg['maxCardUsd']:g} per-card cap (card holds ${cur:.2f}).")
        if rs._FW_GAS.get('sol') is not None and sol_px > 0:   # 💵 a top-up only ASSIGNS SOL already in the wallet — never more than is unassigned
            free = rs._fw.free_for_topup(rs._FW_GAS['sol'], d['books'], cfg['reserveSol'], parked_)
            if usd / sol_px > free + 1e-6:
                raise rs.HTTPException(400, f"Only ${free * sol_px:.2f} unassigned SOL in the Fuse wallet (fee reserve kept apart) — send SOL to it first.")
        if first:   # the SAME card goes real: same coins, phase, clock and config — scaled to the $, time + P&L start over
            if not card or not card.get('legs'):
                raise rs.HTTPException(503, 'That tier has no card dealt yet — try again in a minute.')
            new = rs._fw.topup_card(card, usd, px, now, first=True)
            d['books'][tid] = rs._fw.new_book(usd, sol_px, now)
        else:
            b = d['books'][tid]
            truth = rs._fw.sync_card(card, b, px, sol_px)
            current = rs._prime.value(truth, px)
            new = rs._fw.topup_card(truth, usd, px, now, current_usd=current)
            d['books'][tid] = rs._fw.owner_add(b, usd, usd / sol_px, now)   # journalled: a keeper pass in flight can't save over it
        rs._fw_record(d, {'card': tid, 'side': 'topup', 'usd': usd, 'sol': round(usd / sol_px, 9), 'at': now, 'by': me, 'status': 'done',
                       'why': 'funded — new real run' if first else 'new money top-up — new run'})
        rs._fw_save(d)
    async with rs._admin_lock:
        h = rs._json_load(rs.FUSE_HQ_PATH, {}); h.setdefault('prime', {}).setdefault('cards', {})[tid] = new; rs._json_save(rs.FUSE_HQ_PATH, h)
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-wallet-topup', f'{tid} ${usd:.2f}{" (first funding)" if first else ""}'); rs._admin_save(ad)
    rs.asyncio.create_task(rs._fw_tick(rs.time.time()))
    return {'ok': True, 'tpl': tid, 'usd': usd, 'first': first}


@router.post('/api/reputation/admin/fuse-wallet/payout-profit')
async def fuse_wallet_payout_profit(request: Request):
    """Owner only: move currently available PROFIT cash from the card into paid-out SOL.
    Funded principal is a hard floor; this never sells a coin and never touches principal."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    tid = body.get('tpl')
    ask = body.get('usd')
    if tid not in rs._prime.TEMPLATES:
        raise rs.HTTPException(400, 'Pick a funded tier.')
    sol_px = await rs._sol_usd_live()
    cards = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    card = cards.get(tid)
    if not card:
        raise rs.HTTPException(404, 'Card not found.')
    pairs_ = await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in card.get('legs') or []])
    px = {k: rs._fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}
    jup = await rs._jup_prices([l.get('mint') for l in card.get('legs') or []])
    for l in card.get('legs') or []:
        if jup.get(l.get('mint')):
            px[l['pairAddress']] = jup[l['mint']]
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        d = rs._fw_load(); b = d['books'].get(tid)
        if not b:
            raise rs.HTTPException(400, 'That tier is not funded.')
        if b.get('pending'):
            raise rs.HTTPException(409, 'Wait for the current transaction to settle first.')
        equity = rs._fw.book_value(b, px, sol_px)
        avail = rs._fw.profit_available(b, equity, sol_px)
        nb, paid = rs._fw.payout_profit_cash(b, equity, sol_px, ask)
        if paid <= 0:
            raise rs.HTTPException(400, 'No profit cash is available to pay out right now.')
        d['books'][tid] = nb
        rs._fw_record(d, {'card': tid, 'side': 'payout', 'usd': paid, 'sol': round(paid / sol_px, 9), 'at': rs.time.time(), 'by': me,
                       'status': 'done', 'why': 'owner payout - profit only; funded principal protected'})
        rs._fw_save(d)
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-wallet-payout-profit', f'{tid} ${paid:.2f}'); rs._admin_save(ad)
    return {'ok': True, 'tpl': tid, 'paidUsd': paid, 'availableBeforeUsd': avail, 'fundedUsd': b.get('fundedUsd')}


@router.post('/api/reputation/admin/fuse-wallet/close-dust')
async def fuse_wallet_close_dust(request: Request):
    """♻ Owner only — FREE THE RENT OF DEAD COINS: every Fuse-wallet coin account no card holds whose leftover is worth under $0.05 at
    Jupiter's live price (or was written off) gets its leftover BURNED and the account CLOSED in one transaction, so the rent comes back
    to the wallet. `{confirm: false}` = the dry run (which coins, their $ value, the rent). `{confirm: true}` = Circle signs ONE Burn +
    CloseAccount transaction for ≤ 8 accounts; it is booked as a 'close' row and credited like every sweep once it lands. The keeper
    never burns anything by itself — this button is the owner's approval. Nothing here can touch a coin a card holds."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json() or {}
    cfg = rs._fw_cfg()
    if not cfg.get('address'):
        raise rs.HTTPException(400, 'Pick the Fuse wallet first.')
    d = rs._fw_peek()
    keep = {m for b in (d.get('books') or {}).values() for m in (b.get('legs') or {})} | {(b.get('pending') or {}).get(k_) for b in (d.get('books') or {}).values() for k_ in ('mint', 'toMint')}
    off = {r.get('mint'): rs._fuse._f(r.get('usd')) for r in rs._fw_full_ledger() if r.get('side') == 'writeoff' and r.get('mint')}   # the newest write-off's own $ value
    never = set(rs._fuse.ALL_MAJORS) | {rs._fw.SOL_MINT, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}   # majors, SOL, USDC, USDT: never burned
    async with rs.httpx.AsyncClient(timeout=15) as http:
        res = await rs.asyncio.gather(*[rs._krpc(http, 'getTokenAccountsByOwner', [cfg['address'], {'programId': pg}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}]) for pg in rs._FW_TOKEN_PROGRAMS])
        rows = [{'pubkey': a.get('pubkey'), 'program': pg, 'lamports': (a.get('account') or {}).get('lamports'), 'info': rs._parsed_info(a.get('account'))}
                for pg, r in zip(rs._FW_TOKEN_PROGRAMS, res) for a in (r or {}).get('value') or []]
        mints = [r_['info'].get('mint') for r_ in rows if (r_.get('info') or {}).get('mint') and r_['info']['mint'] not in keep]
        px = await rs._jup_prices(mints) if mints else {}
        dead = rs._fw.dead_accounts(rows, keep, px, off, never=never)
        if body.get('mints'):   # 🔥 one chip's Burn: only the coins asked for (still only dead ones — a coin worth 5¢+ is sold, never burned)
            want_ = {str(m_) for m_ in body['mints']}
            dead = [x_ for x_ in dead if x_['mint'] in want_]
        sol_px = await rs._sol_usd_live()
        plan = {'accounts': [{**x_, 'symbol': next((r_.get('symbol') for r_ in reversed(rs._fw_full_ledger()) if r_.get('mint') == x_['mint'] and r_.get('symbol')), None)} for x_ in dead],
                'rentSol': round(sum(x_['rentSol'] for x_ in dead), 9), 'dustUsd': round(sum(x_['usd'] or 0 for x_ in dead), 4), 'solUsd': sol_px,
                'held': len(rows), 'kept': len(rows) - len(dead)}
        plan['rentUsd'] = round(plan['rentSol'] * sol_px, 2) if sol_px > 0 else None
        if not body.get('confirm') or not dead:
            return {'ok': True, 'dry': True, **plan}
        if not rs._fw_signer_ready():
            raise rs.HTTPException(400, 'Signing is not enabled for the Fuse wallet.')
        if any(b.get('pending') for b in (d.get('books') or {}).values()):
            raise rs.HTTPException(409, 'An order is in flight — try again in a minute.')
        bh = ((await rs._krpc(http, 'getLatestBlockhash', [{'commitment': 'finalized'}])) or {}).get('value', {}).get('blockhash')
        signed = await rs._fw_sign(cfg, rs._dust.burn_close_tx(cfg['address'], dead, bh), f'FEELESS free rent of {len(dead)} dead coins')
        sig = signed.get('signature') or signed.get('txHash')
        await rs._krpc(http, 'sendTransaction', [signed.get('signedTransaction'), {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
    now = rs.time.time()
    row = {'id': f'close:dust:{now:.0f}', 'card': 'wallet', 'side': 'close', 'burn': True, 'n': len(dead), 'sol': plan['rentSol'], 'sig': sig, 'at': now, 'status': 'sent',
           'closed': [{'mint': x_['mint'], 'lamports': int(x_['rentSol'] * 1e9)} for x_ in dead],
           'why': f"♻ owner freed the rent of {len(dead)} dead coin accounts (leftovers worth ${plan['dustUsd']:.3f} burned) — the rent comes back to the wallet once confirmed"}
    async with rs._fw_lock:
        d2 = rs._fw_load(); rs._fw_record(d2, row); rs._fw_save(d2)
    rs._fw_notify(row)
    ad = rs._admin_load(); rs._audit(ad, 'owner', 'fuse-close-dust', f"{len(dead)} accounts · rent {plan['rentSol']:.6f} SOL · sig {str(sig)[:12]}"); rs._admin_save(ad)
    return {'ok': True, 'dry': False, 'sig': sig, **plan}


@router.post('/api/reputation/admin/fuse-wallet/withdraw-cash')
async def fuse_wallet_withdraw_cash(request: Request):
    """Owner only: take card cash OUT of a real card (all of it, or `usd`). The principal drops by what was taken, so profit is
    measured above what is still in. An internal reallocation — no coin sold, nothing sent: the SOL becomes unassigned wallet SOL."""
    rs = _rs()
    me = rs._require_owner(request)
    body = await request.json()
    tid = body.get('tpl')
    if tid not in rs._prime.TEMPLATES:
        raise rs.HTTPException(400, 'Pick a funded tier.')
    sol_px = await rs._sol_usd_live()
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        d = rs._fw_load(); b = d['books'].get(tid)
        if not b:
            raise rs.HTTPException(400, 'That tier is not funded.')
        if b.get('pending') or b.get('defund'):
            raise rs.HTTPException(409, 'Wait for the current Fuse transaction to settle, then withdraw.')
        nb, took = rs._fw.withdraw_cash(b, sol_px, body.get('usd'))
        if took <= 0:
            raise rs.HTTPException(400, 'This card has no cash to withdraw — sell part of a coin to card cash first.')
        d['books'][tid] = nb
        rs._fw_record(d, {'card': tid, 'side': 'withdraw', 'sol': round(took / sol_px, 9), 'usd': round(took, 4), 'at': rs.time.time(), 'by': me, 'status': 'done',
                       'why': f"owner took ${took:.2f} out — principal is now ${nb['fundedUsd']:.2f}"})
        rs._fw_save(d)
    async with rs._admin_lock:   # the paper side stops holding that cash for the owner
        hd = rs._json_load(rs.FUSE_HQ_PATH, {}); cd = ((hd.get('prime') or {}).get('cards') or {}).get(tid)
        if cd:
            cd['holdCashUsd'] = round(max(0.0, rs._fuse._f(cd.get('holdCashUsd')) - took), 6); rs._json_save(rs.FUSE_HQ_PATH, hd)
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-wallet-withdraw', f"{tid} ${took:.2f} principal→${nb['fundedUsd']:.2f}"); rs._admin_save(ad)
    return {'ok': True, 'tookUsd': took, 'principalUsd': nb['fundedUsd']}


@router.get('/api/reputation/admin/agents/stream')
async def admin_agents_stream(request: Request, since: int = 0):
    """📡 The office's live DELTAS as Server-Sent Events (creator / admin wallets): the page loads the snapshot once (GET /admin/agents)
    and then applies these — `candidate_update` · `hunter_update` · `position_update` · `agent_update` · `lifecycle_update` ·
    `execution_update` · `metric_update` · `mint_update` (a live price) · `snapshot` (a pass ended). `resync` = the page fell behind (or
    the service restarted): reload the snapshot once. Read-only: a stream runs no desk, no scan, no quote and no wallet call."""
    rs = _rs()
    rs._require_admin(request)
    H = rs._tke.HUB
    if len(H.subs) >= rs._tke.MAX_SUBS:
        raise rs.HTTPException(429, 'Too many live office streams are open — close another HQ tab.')

    async def gen():
        seq, t0 = int(since or 0), rs.time.time()
        rs._SSE['connects'] += 1; rs._SSE['active'] += 1
        try:
            async for chunk in _sse_body(seq, t0):
                yield chunk
        finally:
            rs._SSE['active'] -= 1; rs._SSE['disconnects'] += 1

    async def _sse_body(seq, t0):
        evs, gap = H.since(seq)
        if gap:
            rs._SSE['resyncs'] += 1
        yield f"event: hello\ndata: {rs.json.dumps({'seq': H.seq, 'resync': bool(gap), 'snapshotAt': (rs._office.get('payload') or {}).get('at')})}\n\n"
        if gap:
            seq = H.seq
        while rs.time.time() - t0 < rs.STREAM_MAX_SEC:
            if await request.is_disconnected():
                return
            evs, gap = H.since(seq)
            if gap:
                seq = H.seq; rs._SSE['resyncs'] += 1
                yield f"event: resync\ndata: {rs.json.dumps({'seq': seq})}\n\n"
                continue
            for e_ in evs:
                yield rs._tke.sse(e_)
                seq = e_['seq']
            if not await H.wait(seq, rs.STREAM_BEAT_SEC):
                yield ': beat\n\n'
        yield f"event: bye\ndata: {rs.json.dumps({'seq': seq})}\n\n"
    return rs.StreamingResponse(gen(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no', 'Content-Encoding': 'identity', 'Connection': 'keep-alive'})


@router.post('/api/reputation/admin/agents')
async def admin_agents_set(request: Request):
    """🤖 Creator: the agents' controls for the real Fuse card — `feed` (their GO coins in the rush; honoured only once the 5-min stage is
    conquered), `cfg` {agentTakePct, agentMode, agentSeats, … + the creator's limits office_edge.POLICY_KEYS (validated by clean_cfg)},
    `idea` {id, action: approve | reject} on a tactic they proposed, and `review` {key, mark: agree | disagree | seen | clear, note} on a
    review item (display state — the office never reads it back, so a review never holds the agents up)."""
    rs = _rs()
    rs._require_owner(request)
    body = await request.json()
    ch = {}
    if 'feed' in body:
        ch['agentFeed'] = bool(body.get('feed'))
    for k in ('agentTakePct', 'agentMode', 'agentStyle', 'agentSeats', 'agentLearn', 'agentLearnPct', 'agentTrust', 'agentDial', 'agentScalp', 'agentControl', 'agentCurve', 'agentPaper', 'deskBuysOff', 'agentOpen', 'agentAiLearn', 'chartWait', 'agentCapital', 'agentAiGate', 'agentValve', 'agentDuoGate', 'agentAiExit', 'nightGuard', 'nightShift', 'candleClock', 'edgePick', 'pickYoung', 'aiSeatPicksOnly') + rs._oe.POLICY_KEYS:
        if k in (body.get('cfg') or {}):
            ch[k] = body['cfg'][k]
    if ch:
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
            pr['realCfg'] = rs._prime.clean_cfg({**(pr.get('realCfg') or {}), **ch})
            pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
            pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
            rs._json_save(rs.FUSE_HQ_PATH, d)
            rs._uni.set_band(pr['realCfg'])   # 🎯 a new MC band applies on the very next tick, not the next agents' pass
        if 'agentControl' in ch:   # 🎮 the hold on the card follows the switch at once
            await rs._agent_control_set(bool(ch['agentControl']), rs.time.time())
    rv = body.get('review') or {}
    marked = None
    if rv.get('key'):   # 📝 the creator's mark on a review item — display state only: no desk reads it back, nothing waits on it
        try:
            of_ = rs._office_state()
            of_['reviewMarks'] = rs._oe.mark_review(of_.get('reviewMarks'), str(rv['key']), rv.get('mark'), rv.get('note'), rs.time.time())
            rs._json_save(rs.OFFICE_PATH, of_)
            marked = of_['reviewMarks'].get(str(rv['key'])[:160])
            p_ = (rs._office.get('payload') or {}).get('review')
            if p_:   # the open page sees the mark at once (the next pass rebuilds the queue with it anyway)
                for its in (p_.get('items') or {}).values():
                    for it in its:
                        if it.get('key') == str(rv['key']):
                            it['mark'] = marked
                p_['open'] = {k: sum(1 for it in v if not it.get('mark')) for k, v in (p_.get('items') or {}).items()}
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    sh_ = body.get('seatHint') or {}
    if sh_.get('mint') and sh_.get('kind') in ('hold', 'good', 'clear'):   # ✋ / 👍 your one click on a seat: Reaper holds its soft exits 30 min; graded 30 min later, the agents + models learn it
        now_ = rs.time.time(); m_ = str(sh_['mint'])
        p_ = (rs._office.get('pos') or {}).get(m_)
        if not p_:
            raise rs.HTTPException(409, 'That coin is not on a seat any more.')
        if sh_['kind'] == 'clear':
            p_.pop('hint', None)
        else:
            px_ = rs._fuse._f((await rs._live_px([m_])).get(m_)) or rs._fuse._f((rs._jup_px_cache.get(m_) or (0, 0))[1])
            hs_, hw_ = rs._of.hint_sec(rs._study.get('hints'))   # ✋ your record decides how long your hold holds
            p_['hint'] = {'kind': sh_['kind'], 'at': now_, 'until': now_ + hs_, 'why': hw_}
            of_ = rs._office_state()
            of_['hintLog'] = (list(of_.get('hintLog') or []) + [{'mint': m_, 'sym': p_.get('sym'), 'kind': sh_['kind'], 'px': px_, 'at': now_, 'pct': p_.get('pct'), 'peak': p_.get('peak'),
                                                                    'reaper': next((r_.get('rule') for r_ in rs._office.get('reports') or [] if r_.get('mint') == m_), None), 'base': rs._of.base_of((rs._office.get('charts') or {}).get(m_))}])[-200:]
            rs._json_save(rs.OFFICE_PATH, of_)
            ai_l = next((l_ for l_ in rs._duo_card_legs() if l_.get('mint') == m_), {})   # 💬 it lands in the duo chat too: the models read it (ownerSays) and the market grades it
            hrow_ = {'at': round(now_), 'mode': 'real', 'model': 'YOU', 'by': 'owner', 'talk': True, 'action': 'TALK', 'view': 'HOLD', 'mint': m_, 'symbol': p_.get('sym'),
                     'why': (f"✋ HOLD this — give it time ({hw_}); still sell it if it really breaks" if sh_['kind'] == 'hold' else f"👍 good entry — trust it through the noise ({hw_}); this is NOT a buy signal"),
                     **({} if ai_l.get('aiSeat') else {'coinTalk': True})}
            rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'log': rs._seat.note((rs._g4_mem.get() or {}).get('log') or [], hrow_)}, now_)
            rs._dv_note(hrow_, px_, now_)
        ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'seat-hint', f"{sh_['kind']} ${p_.get('sym')}"); rs._admin_save(ad_)
        rs._agents['wake'] = now_
        return {'ok': True, 'hint': p_.get('hint')}
    ra_ = body.get('reaperAsk') or {}
    if ra_.get('mint'):   # ✋ your answer to Reaper's question on a coin with YOUR line: approve (it sells next tick) or keep your line (quiet 10 min)
        p_ = (rs._office.get('pos') or {}).get(str(ra_['mint']))
        q_ = (p_ or {}).get('ask')
        if not q_:
            raise rs.HTTPException(409, 'Reaper has no question open on that coin any more.')
        now_ = rs.time.time(); ok_ = bool(ra_.get('ok'))
        p_['askOk' if ok_ else 'askNo'] = {'rule': q_['rule'], 'at': now_}
        p_.pop('ask', None)
        of_ = rs._office_state()
        of_['askLog'] = (list(of_.get('askLog') or []) + [{'mint': str(ra_['mint']), 'sym': p_.get('sym'), 'rule': q_['rule'], 'choice': 'approve' if ok_ else 'keep',
                                                         'pct': q_.get('pct'), 'px': q_.get('px'), 'at': now_}])[-200:]
        rs._json_save(rs.OFFICE_PATH, of_)
        ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'reaper-ask', f"{'approved' if ok_ else 'kept your line on'} ${p_.get('sym')} ({q_['rule']})"); rs._admin_save(ad_)
        rs._agents['wake'] = now_
    ow = body.get('owner') or {}
    owned = None
    if ow.get('input') or ow.get('mint'):   # 👤 owner coin review: REVIEW · TRACK · ARM · IGNORE — it edits the owner's list only (no order, no quote, no wallet call)
        try:
            owned = await rs._owner_act(str(ow.get('input') or ow.get('mint')), str(ow.get('action') or 'review').lower(), rs.time.time())
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        if rs._office.get('payload') is not None:
            rs._office['payload']['ownerReview'] = rs._owner_view(rs.time.time())
    tr_ = body.get('taughtRule') or {}
    if tr_.get('key'):   # 🎓 the creator tunes one lesson-rule: mode (off · flag · rank · skip), strength, its knob
        try:
            rs._teach['st'] = {**rs._teach_state(), 'rules': rs._trl.patch(rs._teach_state().get('rules'), str(tr_['key']), {k_: tr_[k_] for k_ in ('mode', 'strength', 'run', 'hours') if k_ in tr_})}
            rs._json_save(rs.TEACH_PATH, rs._teach['st'])
            rs._taught_stamp(rs._agents.get('table') or [], rs.time.time())
            if rs._office.get('payload') is not None:
                rs._office['payload']['teach'] = {**rs._tch.view(rs._teach['st']), 'rules': rs._taught_view()}
            ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'agent-rule', f"{tr_['key']} → {rs._taught_rules()[str(tr_['key'])]}"); rs._admin_save(ad_)
            rs._agents['wake'] = rs.time.time()
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    tc = body.get('teach') or {}
    taught = None
    if tc:   # 🎓 the creator teaches the desk: a note, a narrative or a chart lesson (with a FEELESS-uploaded image) — read by every fitting model case
        try:
            rs._teach['st'] = rs._tch.remove(rs._teach_state(), str(tc['remove'])) if tc.get('remove') else rs._tch.add(rs._teach_state(), tc, rs.time.time())
            rs._json_save(rs.TEACH_PATH, rs._teach['st'])
            taught = (rs._teach['st'].get('items') or [None])[0]
            if rs._office.get('payload') is not None:
                rs._office['payload']['teach'] = {**rs._tch.view(rs._teach['st']), 'rules': rs._taught_view()}
            if not tc.get('remove') and taught:
                rs._tk.KERNEL.note('owner', 'TEACH', f"🎓 {taught['kind']}: {taught['text'][:120]}", rs.time.time(), mint=taught.get('mint'), key=f"teach:{taught['id']}")
                wired_ = rs._trl.from_text(taught['text'])   # 🎓 a lesson that names a rule switches that rule ON (rank down) — your words now act, not only the model's prompt
                if wired_:
                    rl_ = rs._teach_state().get('rules')
                    for k_ in wired_:
                        if rs._trl.clean(rl_)[k_]['mode'] in ('off', 'flag'):
                            rl_ = rs._trl.patch(rl_, k_, {'mode': 'rank'})
                    rs._teach['st'] = {**rs._teach_state(), 'rules': rs._trl.clean(rl_)}
                    rs._json_save(rs.TEACH_PATH, rs._teach['st'])
                    if rs._office.get('payload') is not None:
                        rs._office['payload']['teach'] = {**rs._tch.view(rs._teach['st']), 'rules': rs._taught_view()}
                    rs._tk.KERNEL.note('owner', 'TEACH', f"🎓 wired to rule: {', '.join(wired_)}", rs.time.time(), key=f"teachwire:{taught['id']}")
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    idea = body.get('idea') or {}
    if idea.get('id'):
        try:
            rs._agents_mem.put(rs._pd.review(rs._agents_mem.get(), str(idea['id']), idea.get('action')), force=True)   # the creator's click is written at once
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    cb = body.get('coach') or {}
    coached = None
    if cb:   # 👑 the creator strengthens the agents: a directive from the fixed vocabulary (a ranking weight the kernel reads on its next pass) — never an order, a size or a sell
        now_ = rs.time.time()
        st_ = rs._coach_state()
        if cb.get('strengthen') is not None:
            st_, coached = rs._co.strengthen(st_, cb['strengthen'], now_)
        elif cb.get('kill') is not None:
            st_, coached = rs._co.kill(st_, cb['kill'], now_)
        else:   # add {key, why, strong} · pull-and-teach adds {mint, sym}: the coin is off the agents' buy list for 6h (the SELL is the card's own ✂ path)
            mint_ = str(cb.get('mint') or '')[:64] or None
            st_, coached = rs._co.add(st_, cb.get('key'), 'owner', cb.get('why'), now_, mint=mint_, sym=str(cb.get('sym') or '')[:24] or None, strong=bool(cb.get('strong')))
        if not coached:
            raise rs.HTTPException(400, 'Pick a cause from the list (or that directive is gone).')
        rs._coach_put(st_)
        try:
            ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'agent-coach', f"{'strengthen' if cb.get('strengthen') is not None else 'kill' if cb.get('kill') is not None else 'pull+teach' if cb.get('mint') else 'add'} {coached.get('key')}"); rs._admin_save(ad_)
        except Exception as e:
            print('coach audit:', str(e)[:100])
        rs._tk.KERNEL.note('judge', 'COACHED', f"👑 {coached.get('key')} {coached.get('points', 0):+.0f} — {coached.get('why') or 'the creator said so'}", now_, key=f"coach:{int(now_)}")
        rs._agents['wake'] = now_
    rs._agents['view'] = None
    return {'ok': True, **({'coach': rs._coach_view(rs.time.time())} if cb else {}), **ch, **({'review': marked} if rv.get('key') else {}), **({'owner': {'mint': owned, 'list': rs._owner_view(rs.time.time())}} if owned else {})}


@router.post('/api/reputation/admin/fuses/verdict/act')
async def fuse_verdict_act(request: Request, p: _RSM.VerdictActIn):
    """🧾 One click on a verdict row (owner, audited): ➕ add a proven sim setting to ALL paper cards (a shared edit — every card follows
    it), to ONE tier card, or to the 💵 real card · 🗑 scrap / 📌 keep a strategy on the trader rails · 🎚 use a proven engine dial ·
    🃏 re-deal a losing tier card."""
    rs = _rs()
    me = rs._require_owner(request)
    now = rs.time.time(); done = ''
    if p.area == '🧠 Sim config':
        word, _, val = p.name.partition(' = ')
        key = next((rs.SIM_KEYS[k] for k in rs.SIM_KEYS if rs._verdict.TRAIT_WORDS.get(k, k) == word), None)
        if not key:
            raise rs.HTTPException(400, 'That setting has no card equivalent.')
        v = rs._prime.clean_exit(key, val)
        if v is None:
            raise rs.HTTPException(400, f'{val} is not an option for {word}.')
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
            if p.act == 'apply-one' and p.tier in rs._prime.TEMPLATES:
                cfg = rs._prime.clean_cfg(pr.get('cfg') or {}); tc = cfg['tierCfg']; tc.setdefault(p.tier, {})[key] = v
                pr['cfg'] = rs._prime.clean_cfg({**(pr.get('cfg') or {}), 'tierCfg': tc}); done = f'{key} = {v:g} on {p.tier}'
            elif p.act == 'apply-real':
                base = pr.get('realCfg') if isinstance(pr.get('realCfg'), dict) and pr.get('realCfg') else pr.get('cfg') or {}
                pr['realCfg'] = rs._prime.clean_cfg({**base, key: v})
                pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {key})[:60]; done = f'{key} = {v:g} on the real card'
            else:
                raise rs.HTTPException(400, 'Every card keeps its own config — pick one card or the real card.')
            rs._json_save(rs.FUSE_HQ_PATH, d)
    elif p.area == '🏟 Strategy' and p.act in ('scrap', 'keep'):
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {})
            scr = set(d.get('scrappedStyles') or []); kept = set(d.get('keptStyles') or [])
            (scr.add if p.act == 'scrap' else scr.discard)(p.name); (kept.add if p.act == 'keep' else kept.discard)(p.name)
            d['scrappedStyles'] = sorted(scr); d['keptStyles'] = sorted(kept); rs._json_save(rs.FUSE_HQ_PATH, d)
        done = f"strategy {p.name} {'scrapped' if p.act == 'scrap' else 'kept'}"
    elif p.area == '🎚 Engine dial' and p.act == 'apply':
        dial = p.name.split(' · ')[0]
        try:
            dialed = rs._rn.engine_dial(dial, rs._runner_cfg())
        except ValueError:
            raise rs.HTTPException(400, 'Unknown dial.')
        dial, cfg = dialed.pop('dial'), rs._rn.clean_cfg(dialed)
        async with rs._admin_lock:
            d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['cfg'] = cfg; d['cfgDial'] = dial; rs._json_save(rs.RUNNERS_PATH, d)
        done = f'engine dial {dial}'
    elif p.area == '⭐ Tier card' and p.act == 'redeal':
        tpl = next((t for t, x in rs._prime.TEMPLATES.items() if x.get('label') == p.name), None)
        if not tpl:
            raise rs.HTTPException(400, 'Unknown tier card.')
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.setdefault('prime', {}).setdefault('cards', {}))
            if (cards.get(tpl) or {}).get('real'):
                raise rs.HTTPException(400, 'That is the real-money card — withdraw it from HQ › Fuse wallet instead.')
            cards.pop(tpl, None); rs._json_save(rs.FUSE_HQ_PATH, d)
        done = f'{p.name} re-dealt'
    else:
        raise rs.HTTPException(400, 'Nothing to do for that row.')
    ad = rs._admin_load(); rs._audit(ad, me, 'verdict-act', f'{p.area} {p.name}: {done}'[:200]); rs._admin_save(ad)
    return {'ok': True, 'done': done, 'at': now}


@router.post('/api/reputation/fuses/{fid}/buy')
async def fuse_buy(fid: str, payload: _RSM.FuseBuy):
    """A Fuse leg bought: counted once, only if the signature is already one of YOUR confirmed FEELESS trades.
    The creator's share of that trade's FEELESS fee is recorded for payout."""
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    mine = set(rs.linked_of(me)) | {me}
    trade = next((x for w, rows in rs._json_load(rs.FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or [] if x.get('tx') == payload.signature), None)
    if not trade:
        raise rs.HTTPException(400, 'That trade is not a confirmed FEELESS trade from your wallet (yet).')
    async with rs._admin_lock:
        store = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
        f = store['fuses'].get(fid)
        if not f:
            raise rs.HTTPException(404, 'No such Fuse.')
        if any(b['sig'] == payload.signature for b in store.get('buys', [])):
            return {'ok': True, 'counted': False}
        fee = float(trade.get('feelessFeeUsd') or 0)
        self_deal = rs.primary_of(f.get('creator') or '') == me or me in set(rs.linked_of(rs.primary_of(f.get('creator') or '')))
        bot = (await rs._shield_of(me))['verdict'] == 'bot'
        store.setdefault('buys', []).append({'fuse': fid, 'sig': payload.signature, 'wallet': me, 'usd': float(trade.get('usd') or trade.get('poolUsd') or 0),
                                             'feeUsd': fee, 'creatorUsd': 0.0 if self_deal or bot else rs._fuse.creator_cut(fee, f.get('creatorBps', 0), rs._house()['fuseCreatorMaxBps']),
                                             'selfDeal': self_deal, 'bot': bot, 'at': rs.time.time()})
        rs._json_save(rs.FUSES_PATH, store)
    return {'ok': True, 'counted': True}


@router.post('/api/reputation/admin/fuses')
async def admin_fuses_save(request: Request):
    """Create / edit / delete a Fuse, or record a creator payout. Launch prices are captured on create (index = 100)."""
    rs = _rs()
    admin = rs._require_admin(request)
    body = await request.json()
    async with rs._admin_lock:
        store = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
        fid = body.get('id') or rs.uuid.uuid4().hex[:10]
        if body.get('delete'):
            store['fuses'].pop(fid, None)
        elif body.get('paidUsd') is not None:
            store.setdefault('paid', {})[fid] = round(float((store.get('paid') or {}).get(fid, 0)) + max(0.0, float(body['paidUsd'])), 6)
        else:
            legs = rs._fuse.clean_legs(body.get('legs'))
            name = str(body.get('name') or '').strip()[:40]
            if not name or len(legs) < 2:
                raise rs.HTTPException(400, 'A Fuse needs a name and at least 2 pools.')
            prev = store['fuses'].get(fid) or {}
            pairs = await rs._fuse_pairs(legs)
            base = {**(prev.get('basePrices') or {}), **{leg['pairAddress']: float(pairs[leg['pairAddress']].get('priceUsd') or 0) for leg in legs
                                                         if pairs.get(leg['pairAddress']) and leg['pairAddress'] not in (prev.get('basePrices') or {})}}
            store['fuses'][fid] = {'name': name, 'emoji': str(body.get('emoji') or '⚛️')[:4], 'tagline': str(body.get('tagline') or '')[:120], 'legs': legs,
                                   'creator': body.get('creator') or prev.get('creator') or admin, 'creatorBps': max(0, min(rs._house()['fuseCreatorMaxBps'], int(body.get('creatorBps') or 0))),
                                   'enabled': bool(body.get('enabled', True)), 'basePrices': base, 'createdAt': prev.get('createdAt') or rs.time.time(),
                                   'featured': bool(body.get('featured', prev.get('featured', False))), 'aura': prev.get('aura', ''),
                                   'arena': bool(body.get('arena', prev.get('arena', not prev))),   # a NEW HQ card goes on the Arena by default
                                   **rs._card_look(body, prev)}
            rs._arena_mega_cache.update(at=0.0, data=None)
        rs._json_save(rs.FUSES_PATH, store)
        ad = rs._admin_load(); rs._audit(ad, admin, 'fuse', rs.json.dumps({'id': fid, **{k: body.get(k) for k in ('name', 'delete', 'paidUsd') if k in body}})[:160]); rs._admin_save(ad)
    return {'ok': True, 'id': fid}


@router.get('/api/reputation/vaults')
async def vaults_list(deposit: float = Query(10.0, gt=0, le=100000)):
    rs = _rs()
    d = rs._json_load(rs.VAULTS_PATH, {'vaults': {}})
    return {'vaults': await rs.asyncio.gather(*[rs._vault_view(vid, v, deposit) for vid, v in d['vaults'].items() if v.get('status') != 'off'])}


@router.post('/api/reputation/admin/security/war-room/trace')
async def admin_war_trace(p: _RSM.WarTrace, request: Request):
    """Read-only on-chain trace of a suspect wallet's recent outbound transfers + a plain-text evidence pack. We never touch the wallet."""
    rs = _rs()
    rs._require_owner(request)
    wallet = (p.wallet or '').strip()
    if not rs._re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', wallet):
        raise rs.HTTPException(400, 'Not a Solana address.')
    transfers = []
    try:
        async with rs.httpx.AsyncClient(timeout=20) as http:
            sigs = await rs._chain._rpc(http, 'getSignaturesForAddress', [wallet, {'limit': 25}])
            sigs = sigs if isinstance(sigs, list) else (sigs or {}).get('result') or []
            for row in sigs[:25]:
                tx = await rs._chain._rpc(http, 'getTransaction', [row['signature'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}])
                tx = tx.get('result') if isinstance(tx, dict) and 'result' in tx else tx
                meta = (tx or {}).get('meta') or {}
                pre, post = meta.get('preBalances') or [], meta.get('postBalances') or []
                keys = [k.get('pubkey') if isinstance(k, dict) else k for k in ((tx or {}).get('transaction', {}).get('message', {}).get('accountKeys') or [])]
                if keys and keys[0] == wallet and pre and post:
                    delta = (pre[0] - post[0]) / 1e9 - (meta.get('fee') or 0) / 1e9
                    if delta > 0 and len(keys) > 1:
                        transfers.append({'sig': row['signature'], 'from': wallet, 'to': keys[1], 'amount': round(delta, 6), 'token': 'SOL', 'at': row.get('blockTime')})
    except Exception as e:
        raise rs.HTTPException(502, f'Chain read failed: {e}')
    tr = rs._war.trace_summary(transfers, wallet)
    rs._war.log(rs._war_s(), 'trace', '', '', '', '', 'owner traced a suspect wallet', wallet); rs._war_save(force=True)
    return {'trace': tr, 'pack': rs._war.evidence_pack(rs._war_s(), wallet, tr)}


@router.post('/api/reputation/security/bounty')
async def war_bounty_report(p: _RSM.BountyReport, request: Request):
    """Public responsible-disclosure inbox (guard rate-limits upstream). The owner triages in the War Room. Pay-outs are the owner's call."""
    rs = _rs()
    rs._war.add_report(rs._war_s(), wallet=p.wallet, url=p.url, detail=p.detail, reward=p.reward); rs._war_save(force=True)
    return {'ok': True, 'message': 'Thanks — your report reached the FEELESS security desk. No automated payout; the owner reviews every report.'}


@router.get('/api/reputation/internal/legal-gate')
async def internal_legal_gate(request: Request, wallet: str = '', feature: str = 'swap', country: str = ''):
    """Internal key only: the swap engine (server, 5001) asks before it quotes a wallet. → {'ok', 'why'}"""
    rs = _rs()
    import hmac
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key()):
        raise rs.HTTPException(403, 'Internal endpoint.')
    if feature not in rs._legal.FEATURES:
        raise rs.HTTPException(400, 'No such feature.')
    c_ = country.upper() if rs._legal.COUNTRY_RE.match(country.upper()) else None
    why_ = rs._legal.hold(rs._legal_s(), feature, rs.primary_of(wallet), c_) if wallet else ''
    if why_ and wallet in rs._any_agent_wallets():
        why_ = ''
    return {'ok': not why_, 'why': why_}


@router.post('/api/reputation/legal/delete')
async def legal_delete(p: _RSM.LegalMine):
    """Delete this wallet's personal / social data (profile, follows, inbox, push, DMs sent, chat posted, linked accounts, sessions).
    Kept, with the reason shown: proof of consent, money receipts, points/payout ledgers, security logs, and everything on-chain."""
    rs = _rs()
    if (p.confirm or '') != 'DELETE':
        raise rs.HTTPException(400, 'Type DELETE to confirm.')
    me = rs._legal_me(p.wallet, p.session, fresh=True)
    n = await rs._legal_wipe(me)
    rs._legal.note_request(rs._legal_s(), me, 'delete', n); rs._legal_save()
    return {'ok': True, 'removed': n, 'kept': rs._legal.KEEP, 'signedOut': True}


@router.get('/api/reputation/fees/quote')
async def fee_quote(wallet: str = '', inputMint: str = '', outputMint: str = ''):
    rs = _rs()
    out = await rs.effective_fee(wallet, inputMint, outputMint)
    return {k: v for k, v in out.items() if k not in ('referralAccount', 'feeAccount', 'feeAccounts')} | {'active': bool(out['bps'])}


@router.post('/api/reputation/internal/agent-fee')
async def internal_agent_fee(request: Request, body: dict):
    """🤖 One agent fee, from its own wallet to the Collective wallet and nowhere else: a % of a trade by its size, or the flat task fee. One key = one charge, ever. Staff-owned agents pay nothing."""
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    key_, wid_, addr_, owner_ = str(body.get('key') or ''), str(body.get('walletId') or ''), str(body.get('address') or ''), str(body.get('owner') or '')
    if not (key_ and wid_ and addr_) or body.get('kind') not in ('trade', 'other'):
        raise rs.HTTPException(400, 'key, wallet and kind are required.')
    book_ = rs._json_load(rs.AGENT_FEES_SENT, {})
    if book_.get(key_):
        return {'signature': book_[key_], 'again': True}
    cfg = rs._fee_cfg(); usd_ = rs._cpool.txn_fee_usd(rs._cpool.load(rs.POOL_PATH)['cfg'], body.get('usd'))[0] if body['kind'] == 'trade' else max(0.0, rs._fuse._f(cfg.get('agentOtherFeeUsd')))
    if usd_ <= 0 or (owner_ and rs._is_staff(owner_)):
        return {'skipped': True}
    w_ = (await rs._circle('POST', '/wallet', {'id': wid_}, agent=True)).get('wallet')
    if not w_ or w_.get('address') != addr_:
        raise rs.HTTPException(403, "That is not this agent's wallet.")
    async with rs.httpx.AsyncClient(timeout=15) as http:
        fee_w = ((rs._json_load(rs.COLONY_PATH, {}) or {}).get('wallet') or {}).get('address')
        if not fee_w:
            raise rs.HTTPException(503, 'The Collective wallet is not open.')
        try:
            usdc = int((((await rs._rpc(http, 'getTokenAccountBalance', [str(rs._cfund.ata(addr_)), {'commitment': 'confirmed'}])) or {}).get('value') or {}).get('amount') or 0)
        except Exception:
            usdc = 0
        units = int(usd_ * rs._cfund.USDC_UNITS); token = 'USDC'
        if usdc < units + int(rs._apay.RESERVE_USD * rs._cfund.USDC_UNITS):
            px = await rs._sol_usd(); token = 'SOL'; units = int(usd_ / px * rs._cfund.LAMPORTS) if px > 0 else 0
            sol = int(((await rs._rpc(http, 'getBalance', [addr_, {'commitment': 'confirmed'}])) or {}).get('value') or 0)
            if not units or sol < units + 2_000_000:
                raise rs.HTTPException(409, 'Not enough in its wallet for the fee yet.')
        bh = ((await rs._rpc(http, 'getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
        tx = rs._cfund.build_out(addr_, fee_w, token, units, bh)
        signed_ = await rs._circle('POST', '/sign', {'walletId': wid_, 'rawTransaction': tx, 'memo': f"FEELESS agent fee {str(body.get('catId') or '')[:16]}"}, agent=True)
        sig_ = str(signed_.get('signature') or signed_.get('txHash') or '')
        if not signed_.get('signedTransaction') or not sig_:
            raise rs.HTTPException(502, 'Circle did not sign it.')
        rs._json_save(rs.AGENT_FEES_SENT, {**book_, key_: sig_})   # written BEFORE the send: never a second charge
        await rs._rpc(http, 'sendTransaction', [signed_['signedTransaction'], {'encoding': 'base64', 'skipPreflight': False, 'maxRetries': 3}])
    rs._cpool.update(rs.POOL_PATH, lambda st: rs._cpool.income(st, f'fee:{key_}', token, units, 'txn' if body['kind'] == 'trade' else 'task'))
    return {'signature': sig_, 'usd': usd_, 'token': token}


@router.post('/api/reputation/admin/collective')
async def admin_collective_set(request: Request):
    """🪙 Owner: change the settings, inside their limits. New money and the next tick use them; nothing already owed shrinks."""
    rs = _rs()
    me_ = rs._require_owner(request)
    body = await request.json() or {}
    if body.get('clear'):   # ⚖ the owner clears a held proof
        ok_ = rs._cpool.update(rs.POOL_PATH, lambda st: rs._cpool.clear_review(st, str(body['clear'].get('cat')), str(body['clear'].get('id'))))
        if not ok_:
            raise rs.HTTPException(404, 'No held proof like that.')
        return await rs._collective_view()
    if body.get('siteSig'):   # 🌍 the owner moved the site's share to the Collective wallet: it counts only once the chain shows it landed
        sig_ = str(body['siteSig']).strip(); pot_ = ((rs._json_load(rs.COLONY_PATH, {}) or {}).get('wallet') or {}).get('address')
        if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{60,100}$', sig_) or not pot_:
            raise rs.HTTPException(400, 'That is not a transaction.')
        async with rs.httpx.AsyncClient(timeout=15) as http:
            tx_ = await rs._rpc(http, 'getTransaction', [sig_, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
        got_ = rs._site_landed(tx_, pot_)
        if not got_:
            raise rs.HTTPException(400, 'That transaction did not put SOL or USDC into the Collective wallet.')
        px_ = float(await rs._sol_usd() or 0); st_tok, units_ = got_
        def go_site(st):
            if rs._cpool.income(st, f'site:{sig_}', st_tok, units_, 'site'):
                st['siteMovedUsd'] = round(float(st.get('siteMovedUsd') or 0) + units_ / rs._cpool.UNITS[st_tok] * (px_ if st_tok == 'SOL' else 1), 6)
                return True
            return False
        if not rs._cpool.update(rs.POOL_PATH, go_site):
            raise rs.HTTPException(409, 'That transaction was already counted.')
        return await rs._collective_view()
    if body.get('poolAdd') or body.get('poolSet'):   # 🏊 the owner lists a pool he opened. It only records a label: it moves nothing
        try:
            if body.get('poolAdd'):
                a_ = body['poolAdd']; rs._cpool.update(rs.POOL_PATH, lambda st: rs._stake.add_pool(st, a_.get('platform'), a_.get('pair'), a_.get('address'), a_.get('note'), rs.time.time(), a_.get('mint')))
            else:
                a_ = body['poolSet']; rs._cpool.update(rs.POOL_PATH, lambda st: rs._stake.set_pool(st, str(a_.get('id')), {k: v for k, v in a_.items() if k != 'id'}))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        return await rs._collective_view()
    if 'payPaused' in body:   # 🛑 the owner's stop: profit keeps compounding, and no cut is paid until he turns it back on
        rs._cpool.update(rs.POOL_PATH, lambda st: st.__setitem__('payPaused', bool(body['payPaused'])))
        return await rs._collective_view()
    if body.get('payEarly') or body.get('bonus'):   # 💸 ledger only: withdrawals stay off, so this moves no money on the chain. A stake can never be spent here
        a_ = body.get('payEarly') or body.get('bonus'); tok_ = str(a_.get('token') or 'USDC'); px_ = float(await rs._sol_usd() or 0)
        if tok_ not in rs._cpool.TOKENS or (tok_ == 'SOL' and px_ <= 0):
            raise rs.HTTPException(400, 'That token cannot be priced right now.')
        try:
            usd_ = float(a_.get('usd') or 0)
        except (TypeError, ValueError):
            raise rs.HTTPException(400, 'Pick an amount.')
        rate_ = (px_ if tok_ == 'SOL' else 1) / rs._cpool.UNITS[tok_]; units_ = int(usd_ / rate_) if rate_ else 0; key_ = f"owner:{a_.get('nonce') or ''}"
        if not a_.get('nonce'):
            raise rs.HTTPException(400, 'Missing nonce.')
        try:
            done_ = rs._cpool.update(rs.POOL_PATH, (lambda st: rs._stake.pay_early(st, key_, str(a_.get('source')), tok_, units_, rate_, rs.time.time())) if body.get('payEarly') else (lambda st: rs._stake.bonus(st, key_, str(a_.get('cat')), tok_, units_, rate_, a_.get('why'), rs.time.time())))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        if not done_:
            raise rs.HTTPException(409, 'That was already done.')
        return await rs._collective_view()
    if body.get('profitSig'):   # 💧 a real pool profit: it counts only when the chain shows it landed in the Collective wallet, and once
        sig_ = str(body['profitSig']).strip(); pot_ = ((rs._json_load(rs.COLONY_PATH, {}) or {}).get('wallet') or {}).get('address')
        if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{60,100}$', sig_) or not pot_:
            raise rs.HTTPException(400, 'That is not a transaction.')
        async with rs.httpx.AsyncClient(timeout=15) as http:
            tx_ = await rs._rpc(http, 'getTransaction', [sig_, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
        got_ = rs._site_landed(tx_, pot_)
        if not got_:
            raise rs.HTTPException(400, 'That transaction did not put SOL or USDC into the Collective wallet.')
        px_ = float(await rs._sol_usd() or 0); tok_, units_ = got_; unit_ = (px_ if tok_ == 'SOL' else 1) / rs._cpool.UNITS[tok_]
        if not rs._cpool.update(rs.POOL_PATH, lambda st: rs._stake.pay_profit(st, f'profit:{sig_}', tok_, units_, unit_, rs.time.time(), str(body.get('pool') or ''))):
            raise rs.HTTPException(409, 'That transaction was already counted.')
        return await rs._collective_view()
    if not isinstance(body.get('cfg'), dict):
        raise rs.HTTPException(400, 'cfg is required.')

    def go(st):
        before = st['cfg']; after = rs._cpool.clean_cfg({**before, **{k: v for k, v in body['cfg'].items() if k in rs._cpool.DEFAULTS}})
        changed = {k: [before[k], after[k]] for k in after if before[k] != after[k]}
        st['cfg'] = after
        if changed:
            st['cfgLog'] = (st.get('cfgLog') or [])[-19:] + [{'at': round(rs.time.time()), 'by': me_[:6], 'changed': changed}]
    rs._cpool.update(rs.POOL_PATH, go)
    return await rs._collective_view()


@router.get('/api/reputation/admin/fees/health')
async def admin_fee_health(request: Request):
    """Will Jupiter actually pay the FEELESS fee? Checks the referral account on-chain: it must belong to the
    Jupiter Ultra referral project (the one /swap/v2 pays into) and have SOL + USDC fee token accounts."""
    rs = _rs()
    rs._require_admin(request)
    if rs._engine_cfg(rs._fee_cfg())['engine'] == 'swap':
        return await rs._swap_fee_health()
    import base64
    from solders.pubkey import Pubkey
    referral = str(rs._fee_cfg().get('referralAccount') or '').strip()
    if not referral:
        return {'ok': False, 'problem': 'No referral account configured.', 'fix': 'Create one under the Jupiter Ultra project at referral.jup.ag and paste it here.'}
    async with rs.httpx.AsyncClient(timeout=20) as http:
        info = await rs._rpc(http, 'getAccountInfo', [referral, {'encoding': 'base64'}])
        value = (info or {}).get('value')
        if not value or value.get('owner') != rs.JUP_REFERRAL_PROGRAM:
            return {'ok': False, 'problem': 'This address is not a Jupiter referral account.', 'fix': 'Create a referral account at referral.jup.ag (Jupiter Ultra project).'}
        raw = base64.b64decode(value['data'][0])
        project = str(Pubkey.from_bytes(raw[40:72]))
        partner = str(Pubkey.from_bytes(raw[8:40]))
        # Fee vaults = token accounts owned by the referral account (Jupiter Ultra creates regular token
        # accounts for it; the legacy referral_ata PDA layout is not guaranteed), so look them up by owner.
        held = set()
        for program in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
            res = await rs._rpc(http, 'getTokenAccountsByOwner', [referral, {'programId': program}, {'encoding': 'jsonParsed'}])
            for row in (res or {}).get('value', []):
                held.add(rs._parsed_info(row.get('account')).get('mint'))
        vaults = {'SOL': 'So11111111111111111111111111111111111111112' in held, 'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' in held}
    if project != rs.JUP_ULTRA_REFERRAL_PROJECT:
        return {'ok': False, 'project': project, 'partner': partner, 'vaults': vaults,
                'problem': 'Referral account was created under an older Jupiter referral project, so Jupiter rejects the fee and every swap runs fee-free.',
                'fix': f'At referral.jup.ag, connect the partner wallet {partner[:4]}…{partner[-4:]}, choose the Jupiter Ultra project, create a referral account, create SOL and USDC token accounts, then paste the new referral account here.'}
    missing = [k for k, ok in vaults.items() if not ok]
    if missing:
        return {'ok': False, 'project': project, 'partner': partner, 'vaults': vaults,
                'problem': f"Missing fee token account for {', '.join(missing)}.", 'fix': 'Create the missing token accounts for this referral account at referral.jup.ag.'}
    return {'ok': True, 'project': project, 'partner': partner, 'vaults': vaults, 'note': 'Jupiter will pay the FEELESS fee into this referral account (SOL/USDC vaults ready).'}


@router.get('/api/reputation/admin/fees/selftest')
async def admin_fee_selftest(request: Request):
    """Prove FEELESS gets paid: quotes go through the SAME server endpoints the swap boxes use
    (/api/trading/quote for Solana, /api/lifi/quote for EVM swaps + bridges). Nothing is signed or sent."""
    rs = _rs()
    rs._require_admin(request)
    cfg = rs._fee_cfg()
    usdc = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    mints = await rs._ecosystem_mints()
    checks = []
    async with rs.httpx.AsyncClient(timeout=40) as http:
        pump = None
        try:
            board = (await http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': 'trending', 'chain': 'solana', 'page': 1, 'scope': 'pump'})).json().get('pairs') or []
            pump = next(((p.get('baseToken') or {}).get('address') for p in board if (p.get('baseToken') or {}).get('address', '').endswith('pump')), None)
        except Exception:
            pump = None
        cases = [('SOL → USDC', rs.WSOL, usdc, '0.01'), ('SOL → top Pump coin', rs.WSOL, pump, '0.01'), ('Top Pump coin → SOL (sell)', pump, rs.WSOL, '1000')]
        if mints.get('fee'):
            cases += [('SOL → $FEE (free buy)', rs.WSOL, mints['fee'], '0.01'), ('$FEE → SOL (sell pays fee)', mints['fee'], rs.WSOL, '10000')]
        # Build the real transaction (not just a price) so Jupiter validates the fee account exactly as it does
        # for traders. The fee wallet is the test signer; nothing is signed or sent.
        test_wallet = await rs._fee_wallet_owner(http, cfg)
        for label, a, b, amount in cases:
            if not a or not b:
                checks.append({'label': label, 'ok': False, 'detail': 'No live Pump coin found to test with.'})
                continue
            # Same wallet as the quote below, so holder-tier discounts match.
            expected = int((await rs.effective_fee(test_wallet or '', a, b))['bps'])
            try:
                r = await http.post('http://127.0.0.1:5001/api/trading/quote', headers={'x-feeless-internal': rs._internal_key()},
                                  json={'input_mint': a, 'output_mint': b, 'amount': amount, 'slippage_bps': 50, 'wallet': test_wallet, 'probe': True})
                d = r.json()
            except Exception as exc:
                checks.append({'label': label, 'ok': False, 'detail': f'Swap server unreachable: {exc}'})
                continue
            if r.status_code != 200 or not (d.get('quote') or {}).get('outAmount'):
                checks.append({'label': label, 'ok': False, 'detail': f"Quote failed ({r.status_code}): {str(d.get('detail') or d)[:140]}"})
                continue
            q = d['quote']
            charged = rs._quote_fee_bps(q)
            ff = d.get('feeless_fee') or {}
            fee_note = '; '.join(ff.get('notes') or [])
            engine = 'Swap API' if d.get('engine') == 'swap' else 'Ultra'
            if expected:
                ok = charged >= expected and not ff.get('fallback')
                detail = (f'✓ {engine} · Jupiter confirms your {charged / 100:.2f}% fee on this trade' if ok
                          else f'FEELESS fee NOT applied ({engine}) — Jupiter confirmed {charged / 100:.2f}%. {fee_note}')
            else:
                ok = True
                detail = 'Free by rule' + (f" · Jupiter's own fee {charged / 100:.2f}%" if charged else '')
            checks.append({'label': label, 'ok': ok, 'rule': expected, 'charged': charged, 'detail': detail})
            await rs.asyncio.sleep(1.2)   # stay under Jupiter's per-key rate limit
        lifi_bps = int(cfg.get('lifiFeeBps') or 0)
        integrator = cfg.get('lifiIntegrator') or rs.os.environ.get('LIFI_INTEGRATOR', '')
        lifi = []
        for label, fc, tc in (('Base swap ETH → USDC', 8453, 8453), ('Bridge Arbitrum → Base', 42161, 8453)):
            if not integrator or not lifi_bps:
                lifi.append({'label': label, 'ok': None, 'skipped': True, 'detail': 'Skipped: no LI.FI fee set, so EVM swaps and bridges are free (set one below to charge).'})
                continue
            to_token = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' if tc == fc else '0x0000000000000000000000000000000000000000'
            try:
                r = await http.get('http://127.0.0.1:5001/api/lifi/quote', params={'fromChain': fc, 'toChain': tc, 'fromToken': '0x0000000000000000000000000000000000000000',
                                   'toToken': to_token, 'fromAmount': '10000000000000000', 'fromAddress': '0x552008c0f6870c2f77e5cC1d2eb9bdff03e30Ea0'})
                d = r.json()
            except Exception as exc:
                lifi.append({'label': label, 'ok': False, 'detail': f'LI.FI proxy unreachable: {exc}'})
                continue
            if r.status_code != 200:
                lifi.append({'label': label, 'ok': False, 'detail': f"Quote failed: {str(d.get('detail'))[:140]}"})
                continue
            ours = int((d.get('feeless') or {}).get('feeBps') or 0)
            total = sum(float(f.get('percentage') or 0) for f in (d.get('estimate') or {}).get('feeCosts') or [])
            ok = ours == lifi_bps and total >= 0.0025 + lifi_bps / 10000 - 1e-6
            lifi.append({'label': label, 'ok': ok, 'detail': (f"FEELESS fee {ours / 100:.2f}% applied (LI.FI total {total * 100:.2f}% incl. its own 0.25%)" if ok
                                                         else (d.get('feeless') or {}).get('note') or f'FEELESS fee not applied (got {ours / 100:.2f}%)')})
    live = [x for x in lifi if not x.get('skipped')]
    return {'checks': checks, 'lifiChecks': lifi, 'lifi': {'ok': all(x['ok'] for x in live) if live else None, 'skipped': not live, 'detail': ' · '.join(x['detail'] for x in lifi)}, 'at': rs.time.time(),
            'note': 'Quotes only through the real swap endpoints — nothing is signed or sent. A pass means FEELESS is paid on real trades.'}


@router.post('/api/reputation/admin/broadcast')
async def admin_broadcast(request: Request, payload: _RSM.BroadcastIn):
    rs = _rs()
    admin = rs._require_admin(request)
    url = payload.url if payload.url.startswith('/') or payload.url.startswith('https://') else '/terminal'
    posted = 0
    for room in [r for r in payload.rooms[:20] if rs._re.match(r'^[A-Za-z0-9_-]{3,160}$', str(r))]:
        rs.feeless_post(room, f'📢 {payload.title}\n{payload.body}')
        posted += 1
    sent = gone = 0
    if payload.push:
        subs = rs._push_load()['subs']
        for sid, entry in list(subs.items()):
            res = await rs.asyncio.to_thread(rs._send_push, entry['subscription'], payload.title, payload.body, url, 'feeless-broadcast')
            sent += res == 'ok'
            gone += res == 'gone'
    ad = rs._admin_load(); rs._audit(ad, admin, 'broadcast', f"{payload.title} · {posted} rooms · push {sent}"); rs._admin_save(ad)
    return {'ok': True, 'rooms': posted, 'pushed': sent, 'stale': gone}


@router.post('/api/reputation/shop/buy')
async def shop_buy(payload: _RSM.BuyIn):
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    it = next((x for x in rs.SHOP if x['id'] == payload.item), None)
    if not it:
        raise rs.HTTPException(404, 'Unknown item.')
    week_ = rs.time.strftime('%G-W%V', rs.time.gmtime())
    if it['kind'] == 'mp':   # 💎 points → your family's bank: a family first, and the weekly cap
        import crews as _cr
        if not _cr.crew_of(rs._json_load(rs.CREWS_PATH, {}), rs._seat_of(rs._json_load(rs.CREWS_PATH, {}), me)):
            raise rs.HTTPException(400, 'Join a family first — the MP goes into its bank.')
        wk_ = (rs._pts().get(me) or {}).get('mpWeek') or {}
        if (wk_.get('pts', 0) if wk_.get('wk') == week_ else 0) + it['cost'] > rs.PTS_TO_MP_WEEK:
            raise rs.HTTPException(400, f'{rs.PTS_TO_MP_WEEK:,} points a week can go into the family bank — the rest waits for next week.')
    async with rs._admin_lock:
        d = rs._pts(); rec = d.get(me) or {'total': 0, 'claims': {}, 'log': []}
        balance = rec.get('total', 0) - rec.get('spent', 0)
        if balance < it['cost']:
            raise rs.HTTPException(400, f"Need {it['cost'] - balance} more points.")
        rec['spent'] = rec.get('spent', 0) + it['cost']
        un = rec.setdefault('unlocks', {})
        g = it['grant']
        if it['kind'] == 'style':
            for k, v in g.items():
                un[f'{k}:{v}'] = rs.time.time() + it['days'] * 86400
        elif it['kind'] == 'boost':
            rec['boostCredits'] = rec.get('boostCredits', 0) + g['boosts']
        elif it['kind'] == 'raffle':
            rec['tickets'] = rec.get('tickets', 0) + 1
        elif it['kind'] == 'mp':
            wk_ = rec.get('mpWeek') or {}
            rec['mpWeek'] = {'wk': week_, 'pts': (wk_.get('pts', 0) if wk_.get('wk') == week_ else 0) + it['cost']}
        else:
            un[f"badge:{g['badge']}"] = 'forever'
        rec.setdefault('log', []).insert(0, {'id': it['id'], 'label': f"Bought {it['label']}", 'points': -it['cost'], 'at': rs.time.time()})
        d[me] = rec; rs._json_save(rs.POINTS_PATH, d)
    rs._badge_cache.pop(me, None)
    if it['kind'] == 'mp':   # the points are spent → the MP lands in the family bank (refunded if the family vanished meanwhile)
        import crews as _cr
        async with rs._crews_lock:
            st_ = rs._json_load(rs.CREWS_PATH, {}); c_ = _cr.crew_of(st_, rs._seat_of(st_, me))
            if c_:
                city_ = rs._fcity.city_of(c_, rs.time.time()); city_['bank'] += it['grant']['mp']
                rs._json_save(rs.CREWS_PATH, st_)
        if not c_:
            async with rs._admin_lock:
                d = rs._pts(); rec = d.get(me) or rec; rec['spent'] = max(0, rec.get('spent', 0) - it['cost']); d[me] = rec; rs._json_save(rs.POINTS_PATH, d)
            raise rs.HTTPException(409, 'Your family was not found — the points are back.')
    return {'ok': True, 'balance': rec['total'] - rec['spent']}


@router.post('/api/reputation/webhooks/helius')
async def helius_webhook(request: Request):
    rs = _rs()
    secret = rs.os.environ.get('HELIUS_WEBHOOK_SECRET') or (rs._admin_load().get('helius') or {}).get('secret', '')
    if not secret or not rs.hmac.compare_digest(request.headers.get('authorization', ''), secret):
        raise rs.HTTPException(403, 'Bad webhook secret.')
    events = await request.json()
    n = 0
    for ev in events if isinstance(events, list) else [events]:
        for tt in (ev.get('tokenTransfers') or [])[:20]:
            usd = None
            amt = float(tt.get('tokenAmount') or 0)
            mint = tt.get('mint')
            if not mint or amt <= 0:
                continue
            rs._radar['whales'].insert(0, {'pair': None, 'mint': mint, 'symbol': None, 'kind': 'transfer', 'usd': usd, 'wallet': tt.get('fromUserAccount'),
                                        'tx': ev.get('signature'), 'at': rs.time.strftime('%Y-%m-%dT%H:%M:%SZ', rs.time.gmtime(ev.get('timestamp') or rs.time.time()))})
            n += 1
        rs._radar['whales'] = rs._radar['whales'][:120]
    return {'ok': True, 'ingested': n}


@router.put('/api/reputation/admin/launch-rail')
async def launch_rail_set(request: Request, p: _RSM.LaunchRailIn):
    rs = _rs()
    me = rs._require_admin(request)   # owner and admins: the config is verified on-chain below, and every change is audited
    if not (rs._re.match(rs._B58, p.config) and rs._re.match(rs._B58, p.feeClaimer)):
        raise rs.HTTPException(400, 'Config and fee claimer must be Solana addresses.')
    # Only accept a config that really exists on-chain and belongs to the DBC program.
    async with rs.httpx.AsyncClient(timeout=10) as http:
        info = await rs._rpc(http, 'getAccountInfo', [p.config, {'encoding': 'base64'}])
    owner = ((info or {}).get('value') or {}).get('owner')
    if owner != rs.DBC_PROGRAM:
        raise rs.HTTPException(409, 'That config is not on-chain yet (or is not a Meteora DBC config). Wait for confirmation and retry.')
    keep = {k: p.params[k] for k in ('initialMarketCap', 'migrationMarketCap', 'startingFeeBps', 'endingFeeBps', 'feeDecayMin', 'creatorFeePct', 'lockedLpPct', 'supply', 'quote', 'preset', 'buyBurn', 'poolCreationFeeSol') if k in p.params}
    rec = {'config': p.config, 'feeClaimer': p.feeClaimer, 'params': keep, 'setBy': me, 'at': rs.time.time()}
    d = rs._json_load(rs.LAUNCH_RAIL_PATH, {})
    if p.scope == 'house':
        # House configs never replace the public one; they sit beside it for owner-only launches.
        house = [h for h in d.get('house') or [] if h['config'] != p.config]
        house.append({**rec, 'id': p.config[:8], 'label': (p.label or 'House config')[:40]})
        d['house'] = house[-8:]
    elif p.scope == 'public':
        d = {**d, **rec}
    else:
        raise rs.HTTPException(400, 'Scope must be public or house.')
    rs._json_save(rs.LAUNCH_RAIL_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'launch-rail', f"{p.scope} config {p.config[:8]}"); rs._admin_save(ad)
    return d


@router.post('/api/reputation/admin/circle/wallets')
async def circle_create_wallet(request: Request, p: _RSM.CircleWalletIn):
    rs = _rs()
    me = rs._require_owner(request)
    out = await rs._circle('POST', '/wallets', {'blockchain': p.blockchain, 'name': p.name[:40]})
    ad = rs._admin_load(); rs._audit(ad, me, 'circle-wallet', f"{p.blockchain} {(out.get('wallet') or {}).get('address', '')}"); rs._admin_save(ad)
    return out


@router.post('/api/reputation/admin/reserve/{sid}/paid')
async def admin_reserve_paid(request: Request, sid: str, p: _RSM.ReservePaid):
    """Record a payout the reserve wallet signed. Every signature must be on-chain, succeeded and signed by the reserve wallet."""
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    d = rs._seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
    if not s:
        raise rs.HTTPException(404, 'Season not found.')
    if (d.get('reservePayouts') or {}).get(sid):
        raise rs.HTTPException(409, 'This season was already paid out.')
    wallet = s.get('reserveWallet')
    if not wallet:
        raise rs.HTTPException(400, 'Assign a Fee Reserve wallet to this season first.')
    if not all(rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', x) for x in p.sigs):
        raise rs.HTTPException(400, 'Bad transaction signature.')
    plan = await rs._reserve_plan(s, d)
    async with rs.httpx.AsyncClient(timeout=20) as http:
        txs = await rs.asyncio.gather(*(rs._rpc(http, 'getTransaction', [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}]) for x in p.sigs))
    for sig, tx in zip(p.sigs, txs):
        if not tx or (tx.get('meta') or {}).get('err'):
            raise rs.HTTPException(400, f'Transaction {sig[:8]}… is not on-chain or failed.')
        if wallet not in [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]:
            raise rs.HTTPException(400, 'Payout must be signed by the season Fee Reserve wallet.')
    paid = {}  # record what actually moved on-chain, not what was planned
    for tx in txs:
        for ix in tx['transaction']['message'].get('instructions') or []:
            info = (ix.get('parsed') or {}).get('info') or {}
            if ix.get('program') == 'system' and (ix.get('parsed') or {}).get('type') == 'transfer' and info.get('source') == wallet:
                paid[info['destination']] = round(paid.get(info['destination'], 0) + info['lamports'] / 1e9, 9)
    if not paid:
        raise rs.HTTPException(400, 'No SOL transfers from the reserve wallet in those transactions.')
    tiers = {r['address']: r['tier'] for r in plan['rows']}
    d = rs._seasons()
    d.setdefault('reservePayouts', {})[sid] = {'sigs': p.sigs, 'at': rs.time.time(), 'by': admin, 'potSol': plan['potSol'],
                                               'rows': [{'address': a, 'tier': tiers.get(a, ''), 'sol': v} for a, v in paid.items()]}
    rs._json_save(rs.SEASONS_PATH, d)
    col = rs._json_load(rs.COLLECTION_PATH, {})
    for a, items in col.items():
        for it in items:
            if it.get('id') == f'{sid}:season' and a in paid:
                it['rewardStatus'] = 'paid'; it['rewardSol'] = paid[a]; it['rewardSig'] = p.sigs[0]
    rs._json_save(rs.COLLECTION_PATH, col)
    total = round(sum(paid.values()), 6)
    ad = rs._admin_load(); rs._audit(ad, admin, 'reserve-payout', f"{sid} {total} SOL to {len(paid)}"); rs._admin_save(ad)
    return {'ok': True, 'paidSol': total, 'wallets': len(paid)}


@router.post('/api/reputation/admin/reserve/{sid}/pay-circle')
async def admin_reserve_pay_circle(request: Request, sid: str, p: _RSM.CirclePayIn):
    """Season reserve held in a Circle wallet: Circle sends each badge holder's share. Retries only the rows that failed."""
    rs = _rs()
    me = rs._require_owner(request)
    async with rs._circle_pay_lock:
        d = rs._seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
        if not s or not s.get('reserveWallet'):
            raise rs.HTTPException(404, 'Season or reserve wallet not found.')
        prev = (d.get('reservePayouts') or {}).get(sid)
        if prev and prev.get('via') != 'circle':
            raise rs.HTTPException(409, 'This season was already paid out.')
        if prev:
            todo = prev.get('failed') or []
        else:
            plan = await rs._reserve_plan(s, d)
            todo = [{'address': r['address'], 'tier': r['tier'], 'sol': r['sol']} for r in plan['rows']]
        todo = [{k: r[k] for k in ('address', 'tier', 'sol') if k in r} for r in todo]
        if not todo:
            raise rs.HTTPException(409, 'Nothing left to pay for this season.')
        res = await rs._circle_pay(s['reserveWallet'], todo, f'reserve:{sid}', p.confirm)
        ok, bad = [r for r in res if r.get('circleTx')], [r for r in res if not r.get('circleTx')]
        d = rs._seasons()
        rec = d.setdefault('reservePayouts', {}).get(sid) or {'via': 'circle', 'sigs': [], 'at': rs.time.time(), 'by': me, 'rows': []}
        rec['rows'] = (rec.get('rows') or []) + ok; rec['failed'] = bad; rec['updatedAt'] = rs.time.time()
        if ok or prev:
            d['reservePayouts'][sid] = rec
            rs._json_save(rs.SEASONS_PATH, d)
        if ok:
            col = rs._json_load(rs.COLLECTION_PATH, {}); sent = {r['address']: r for r in ok}
            for a, items in col.items():
                for it in items:
                    if it.get('id') == f'{sid}:season' and a in sent:
                        it['rewardStatus'] = 'paid'; it['rewardSol'] = sent[a]['sol']; it['rewardCircleTx'] = sent[a]['circleTx']
            rs._json_save(rs.COLLECTION_PATH, col)
        ad = rs._admin_load(); rs._audit(ad, me, 'reserve-payout-circle', f"{sid} {round(sum(r['sol'] for r in ok), 6)} SOL to {len(ok)}, {len(bad)} failed"); rs._admin_save(ad)
    return {'ok': not bad, 'paidSol': round(sum(r['sol'] for r in ok), 6), 'wallets': len(ok), 'failed': bad}


@router.post('/api/reputation/admin/badge-pools/{pid}/pay-circle')
async def admin_badge_pool_pay_circle(request: Request, pid: str, p: _RSM.CirclePayIn):
    """Badge pool held in a Circle wallet: Circle sends each holder's share of the current plan."""
    rs = _rs()
    me = rs._require_owner(request)
    async with rs._circle_pay_lock:
        pool = next((x for x in rs._pools()['pools'] if x['id'] == pid), None)
        if not pool:
            raise rs.HTTPException(404, 'Pool not found.')
        plan = await rs._pool_plan(pool)
        if (plan.get('cooldownLeft') or 0) > 0:
            raise rs.HTTPException(409, 'This pool was paid within the last hour.')
        rows = [{'address': r['address'], 'sol': r['sol']} for r in plan['rows'] if r.get('sol', 0) > 0]
        if not rows:
            raise rs.HTTPException(400, 'Nothing to pay from this pool yet.')
        res = await rs._circle_pay(pool['wallet'], rows, f"pool:{pid}:{len(pool.get('payouts') or [])}", p.confirm)
        ok, bad = [r for r in res if r.get('circleTx')], [r for r in res if not r.get('circleTx')]
        d = rs._pools(); pool = next((x for x in d['pools'] if x['id'] == pid), None)
        if ok and pool:
            scale = sum(r['sol'] for r in ok) / plan['paidSol'] if plan.get('paidSol') else 0
            pool.setdefault('payouts', []).append({'via': 'circle', 'sigs': [], 'at': rs.time.time(), 'by': me, 'rows': ok, 'failed': bad,
                                                   'perKey': {k: int(v * scale * 1e6) / 1e6 for k, v in (plan.get('perKey') or {}).items()},
                                                   'totalSol': round(sum(r['sol'] for r in ok), 6)})
            pool['payouts'] = pool['payouts'][-50:]
            rs._json_save(rs.BADGE_POOLS_PATH, d)
        ad = rs._admin_load(); rs._audit(ad, me, 'badge-pool-payout-circle', f"{pid} {round(sum(r['sol'] for r in ok), 6)} SOL to {len(ok)}, {len(bad)} failed"); rs._admin_save(ad)
    return {'ok': not bad, 'paidSol': round(sum(r['sol'] for r in ok), 6), 'wallets': len(ok), 'failed': bad}


@router.get('/api/reputation/admin/badge-pools')
async def admin_badge_pools(request: Request):
    rs = _rs()
    rs._require_admin(request)
    ad = rs._admin_load(); seen = {}
    for items in (ad.get('badges') or {}).values():
        for b in items.values():
            x = seen.setdefault(b['id'], {'id': b['id'], 'label': b.get('label'), 'icon': b.get('icon'), 'count': 0}); x['count'] += 1
    return {'pools': [{**p, 'payouts': (p.get('payouts') or [])[-5:]} for p in rs._pools()['pools']], 'badges': sorted(seen.values(), key=lambda b: -b['count']),
            'tiers': [t for t, _ in rs.SEASON_TIERS], 'seasons': [{'id': s['id'], 'name': s['name']} for s in rs._seasons()['seasons']]}


@router.post('/api/reputation/admin/badge-pools/{pid}/paid')
async def admin_badge_pool_paid(request: Request, pid: str, p: _RSM.ReservePaid):
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    d = rs._pools(); pool = next((x for x in d['pools'] if x['id'] == pid), None)
    if not pool:
        raise rs.HTTPException(404, 'Pool not found.')
    used = {s for x in d['pools'] for po in x.get('payouts') or [] for s in po['sigs']}
    if used & set(p.sigs):
        raise rs.HTTPException(409, 'Those transactions were already recorded.')
    if not all(rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', x) for x in p.sigs):
        raise rs.HTTPException(400, 'Bad transaction signature.')
    async with rs.httpx.AsyncClient(timeout=20) as http:
        txs = await rs.asyncio.gather(*(rs._rpc(http, 'getTransaction', [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}]) for x in p.sigs))
    paid = {}
    for sig, tx in zip(p.sigs, txs):
        if not tx or (tx.get('meta') or {}).get('err'):
            raise rs.HTTPException(400, f'Transaction {sig[:8]}… is not on-chain or failed.')
        if pool['wallet'] not in [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]:
            raise rs.HTTPException(400, 'Payout must be signed by the pool wallet.')
        for ix in tx['transaction']['message'].get('instructions') or []:
            info = (ix.get('parsed') or {}).get('info') or {}
            if ix.get('program') == 'system' and (ix.get('parsed') or {}).get('type') == 'transfer' and info.get('source') == pool['wallet']:
                paid[info['destination']] = round(paid.get(info['destination'], 0) + info['lamports'] / 1e9, 9)
    if not paid:
        raise rs.HTTPException(400, 'No SOL transfers from the pool wallet in those transactions.')
    moved = sum(paid.values()); scale = min(1.0, moved / p.plannedSol) if p.plannedSol > 0 else 0
    per_key = {str(k)[:60]: int(float(v) * scale * 1e6) / 1e6 for k, v in list((p.perKey or {}).items())[:200] if isinstance(v, (int, float)) and v > 0}
    pool.setdefault('payouts', []).append({'sigs': p.sigs, 'at': rs.time.time(), 'by': admin, 'rows': [{'address': a, 'sol': v} for a, v in paid.items()], 'perKey': per_key,
                                           'totalSol': round(sum(paid.values()), 6)})
    pool['payouts'] = pool['payouts'][-50:]
    rs._json_save(rs.BADGE_POOLS_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, admin, 'badge-pool-payout', f"{pool['name']} {round(sum(paid.values()), 6)} SOL to {len(paid)}"); rs._admin_save(ad)
    return {'ok': True, 'paidSol': round(sum(paid.values()), 6), 'wallets': len(paid)}


@router.post('/api/reputation/admin/treasury/split')
async def treasury_split_record(request: Request, p: _RSM.SplitRecord):
    """Record a split the owner signed from their own wallet. Every signature is re-read on-chain and only the
    transfers the signer really made are stored."""
    rs = _rs()
    admin = rs._require_owner(request)   # 🔒 owner only: it decides where money goes (audit 2026-11-12 #2)
    if not all(rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', x) for x in p.sigs):
        raise rs.HTTPException(400, 'Bad transaction signature.')
    ad = rs._admin_load()
    if {s for sp in ad.get('splits') or [] for s in sp['sigs']} & set(p.sigs):
        raise rs.HTTPException(409, 'Already recorded.')
    async with rs.httpx.AsyncClient(timeout=20) as http:
        txs = await rs.asyncio.gather(*(rs._rpc(http, 'getTransaction', [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}]) for x in p.sigs))
    moved, signer = [], None
    allowed = set(rs._owner_wallets()) | set(rs._admin_wallets())
    for sig, tx in zip(p.sigs, txs):
        if not tx or (tx.get('meta') or {}).get('err'):
            raise rs.HTTPException(400, f'Transaction {sig[:8]}… is not on-chain or failed.')
        signers = [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]
        signer = next((s for s in signers if s in allowed), None)
        if not signer:
            raise rs.HTTPException(400, 'Splits must be signed by a FEELESS owner/admin wallet.')
        moved += rs.reserve_pool.parsed_transfers(tx, signer)
    if not moved:
        raise rs.HTTPException(400, 'No transfers found in those transactions.')
    rec = {'sigs': p.sigs, 'asset': p.asset[:10], 'by': signer, 'at': rs.time.time(), 'moved': moved[:60], 'total': round(sum(m['amount'] for m in moved), 6)}
    ad.setdefault('splits', []).append(rec); ad['splits'] = ad['splits'][-50:]
    rs._audit(ad, admin, 'treasury-split', f"{rec['total']} {p.asset} in {len(p.sigs)} tx"); rs._admin_save(ad)
    return {'ok': True, 'total': rec['total'], 'transfers': len(moved)}


@router.get('/api/reputation/cards/{address}')
async def cards_of(address: str):
    """The cards this wallet holds, with what THIS wallet has earned from each."""
    rs = _rs()
    me = rs.primary_of(address)
    cards = rs._cards_all()
    held = {}
    try:
        for b in (await rs.wallet_badges(address)).get('badges', []):
            held[f"badge:{b['id']}"] = {'why': b.get('why')}
    except Exception:
        pass
    for bid, b in ((rs._admin_load().get('badges') or {}).get(address) or {}).items():
        held[f'badge:{bid}'] = {'why': b.get('why')}
    for it in rs._json_load(rs.COLLECTION_PATH, {}).get(me, []):
        k = rs._collection_card_key(it)
        if k:
            held[k] = {'why': it.get('how'), 'rarity': it.get('rarity'), 'rank': it.get('rank'), 'tier': it.get('tier'), 'rewardSol': it.get('rewardSol'), 'at': it.get('at')}
    mine_paid = {}
    for p in rs._pools()['pools']:
        for po in p.get('payouts') or []:
            if any(r.get('address') == me for r in po.get('rows') or []):
                for k, v in (po.get('perKey') or {}).items():
                    mine_paid[k] = mine_paid.get(k, 0) + v
    out = []
    for k, h in held.items():
        c = cards.get(k)
        if not c:
            continue
        mine = h.get('rewardSol') if k.startswith('season:') and h.get('rewardSol') else mine_paid.get(k, 0)
        out.append({**c, **({'rarity': h['rarity']} if h.get('rarity') else {}), 'why': h.get('why'), 'rank': h.get('rank'), 'tier': h.get('tier'), 'earnedMine': round(float(mine or 0), 6)})
    order = {r: i for i, r in enumerate(reversed(rs.badge_cards.RARITIES))}
    out.sort(key=lambda c: (order.get(c['rarity'], 9), c['title']))
    return {'address': me, 'cards': out}


@router.put('/api/reputation/admin/circle/wallets/{wid}')
async def circle_wallet_meta(request: Request, wid: str, p: _RSM.CircleMetaIn):
    rs = _rs()
    me = rs._require_owner(request)
    try:
        await rs._circle('POST', '/wallets/rename', {'id': wid, 'name': p.name})
    except rs.HTTPException:
        pass  # Circle rename is best effort; the FEELESS label below is what the HQ shows
    d = rs._json_load(rs.CIRCLE_META_PATH, {})
    d[wid] = {'name': p.name, 'description': p.description, 'at': rs.time.time()}
    rs._json_save(rs.CIRCLE_META_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, me, 'circle-meta', f'{wid[:8]} → {p.name}'); rs._admin_save(ad)
    return {'ok': True, **d[wid]}


@router.post('/api/reputation/admin/circle/transfer')
async def circle_transfer(request: Request, p: _RSM.CircleSendIn):
    rs = _rs()
    me = rs._require_owner(request)
    if not (rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.to) or rs._re.match(r'^0x[0-9a-fA-F]{40}$', p.to)):
        raise rs.HTTPException(400, 'Destination must be a wallet address.')
    if p.confirm != p.to[-4:]:
        raise rs.HTTPException(400, 'Type the last 4 characters of the destination to confirm.')
    dest = {x['address'] for x in await rs._circle_destinations()}
    if p.to not in dest:
        raise rs.HTTPException(403, 'Circle wallets only send to FEELESS wallets or wallets you saved. Save this address first.')
    if not rs._re.match(r'^\d+(\.\d+)?$', p.amount) or float(p.amount) <= 0:
        raise rs.HTTPException(400, 'Amount must be a positive number.')
    await rs._fuse_send_guard(p.walletId, p.tokenId, float(p.amount))
    out = await rs._circle('POST', '/transfer', {'walletId': p.walletId, 'tokenId': p.tokenId, 'to': p.to, 'amount': p.amount, 'idempotencyKey': str(rs.uuid.uuid4())})
    ad = rs._admin_load(); rs._audit(ad, me, 'circle-send', f'{p.amount} from {p.walletId[:8]} to {p.to[:6]}…'); rs._admin_save(ad)
    return out


@router.post('/api/reputation/internal/agent-x402-pay')
async def internal_agent_x402_pay(request: Request, body: dict):
    """💳 Sign one model-call payment for an agent's own wallet (agent_pay.py checks asset, size and fee payer). Signs only: the provider settles it."""
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    wid_, addr_, entry_ = str(body.get('walletId') or ''), str(body.get('address') or ''), body.get('entry') or {}
    creator_ = bool(body.get('creator')) and body.get('catId') == 'leader'   # 🐱 only FEE's wallet may sit in the creator's Circle project (owner 2026-10-31)
    if body.get('creator') and not creator_:
        raise rs.HTTPException(403, "Only Fee's wallet pays from the creator's Circle project.")
    w_ = (await rs._circle('POST', '/wallet', {'id': wid_}, agent=not creator_)).get('wallet')
    if not w_ or w_.get('address') != addr_:
        raise rs.HTTPException(403, "That is not this agent's wallet.")
    async with rs.httpx.AsyncClient(timeout=15) as http:
        bh = ((await rs._rpc(http, 'getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
    try:
        tx = rs._apay.build_payment(addr_, entry_, bh)
    except (ValueError, KeyError) as e:
        raise rs.HTTPException(400, str(e)[:160])
    signed_ = await rs._circle('POST', '/sign', {'walletId': wid_, 'rawTransaction': tx, 'memo': f"FEELESS model call {str(body.get('catId') or '')[:20]}"}, agent=not creator_)
    if not signed_.get('signedTransaction'):
        raise rs.HTTPException(502, 'Circle did not sign it.')
    return {'signedTransaction': signed_['signedTransaction']}


@router.post('/api/reputation/internal/agent-circle-wallet')
async def internal_agent_circle_wallet(request: Request, body: dict):
    """🟦 One Solana wallet for one agent, on the family + agent Circle account. The same cat always gets the same request key, so a double click can't make two."""
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    cid_ = str(body.get('catId') or '')
    if not rs._re.match(r'^[A-Za-z0-9_-]{1,64}$', cid_):
        raise rs.HTTPException(400, 'Not an agent id.')
    import uuid as _uuid
    return await rs._circle('POST', '/wallets', {'blockchain': 'SOL', 'name': f'agent {cid_[:30]}', 'key': str(_uuid.uuid5(_uuid.NAMESPACE_URL, f'feeless-cat-{cid_}'))}, agent=True)

