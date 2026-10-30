"""🏇 AGENT TRADES — a cat's proposal filled FROM ITS OWN Crossmint wallet, no user signature per trade (owner 2026-10-29: "one trade agent made
and funded, that's it, it rides; general can be switched anytime for the user to approve general AI moves or have them do their thing";
DECISIONS #2 → agent wallets). Runs ONLY inside the cat engine's own pass (feecat_service `_agent_pass`) — one writer, never a background task.

Which proposals go: a cat with an agent wallet in mode `auto` (a trading cat always; a general cat on 🚀 DO ITS THING) — every fresh
proposal; mode `approve` (✋ ASK ME) — only one the owner approved on the desk. The proposal itself already passed the cat's rules
(cat_real.propose: its budget, a sell only of a coin it really bought). Then the SERVER GUARDS below, every one a hard stop:
  · one trade in flight per cat (a send waits for the last one to settle)
  · a buy ≤ the cat's per-buy budget (≤ MAX_BUY_SOL) · ≤ its daily cap (DAY_X × budget, ≤ DAY_MAX_SOL, across 24h) · GAS_SOL always left
  · a sell only of what the wallet really holds now (Solana RPC through the trading service) · SOL ↔ coin only
  · the quote must echo the exact coins asked for (never send an order that does not match)
The swap is the SAME engine every FEELESS swap uses (`/api/trading/quote`, Jupiter Swap API + the FEELESS fee) quoted for the cat's wallet;
its unsigned transaction goes to Crossmint (`/wallets/{a}/transactions`, base58), which signs with the API-key signer and broadcasts. The
proposal turns done only when Crossmint reports success with the on-chain signature; a failure says Crossmint's words and nothing retries."""
import base64

import base58

import agent_wallet as _aw

SOL = 'So11111111111111111111111111111111111111112'
TRADE = 'http://127.0.0.1:5001/api/trading'
GAS_SOL = 0.01
MAX_BUY_SOL = 0.5
DAY_X, DAY_MAX_SOL, DAY = 4, 2.0, 86400.0
SLIP_BPS = 300
LIVE = ('sending', 'pending', 'awaiting-approval')
KEEP = 40
REP = 'http://127.0.0.1:5077/api/reputation'
SIGNERS = ('crossmint', 'circle')   # 🟦 owner 2026-10-30: Fee (NEXA) trades from her CIRCLE wallet too — Circle signs, our RPC sends, the same guards run
RETRY_SEC = 60.0


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def in_flight(cat):
    return next((t for t in cat.get('agentTx') or [] if t.get('status') in LIVE), None)


def day_cap(cat):
    return round(min(DAY_MAX_SOL, DAY_X * min(MAX_BUY_SOL, _f(cat.get('budgetSol')) or 0.05)), 4)


def spent_today(cat, now):
    return round(sum(_f(t.get('sol')) for t in cat.get('agentTx') or [] if t.get('side') == 'buy' and t.get('status') != 'failed' and now - _f(t.get('at')) < DAY), 6)


def wants(cat, p, now):
    """Should this proposal go from the agent wallet now? (mode + freshness only; the guards come after)."""
    w = cat.get('agentWallet') or {}
    if w.get('provider', 'crossmint') not in SIGNERS:   # 👁 a watch-only wallet (assigned, its key not held by Crossmint): never traded from
        return False
    if not w.get('address') or p.get('status') != 'pending' or now > _f(p.get('until')) or p.get('agentTx'):
        return False
    if now - _f(p.get('agentTry')) < RETRY_SEC:   # a guard stopped it a moment ago (no SOL yet, over the cap…): wait, don't hammer
        return False
    return w.get('mode') == 'auto' or bool(p.get('approved'))


def guard(cat, p, sol_bal, token_amt, now):
    """→ (input_mint, output_mint, amount str) for the quote, or ValueError naming the rule that stopped it."""
    if in_flight(cat):
        raise ValueError('one trade at a time — the last one is still settling')
    if p.get('side') == 'buy':
        sol = _f(p.get('sol'))
        cap = min(MAX_BUY_SOL, _f(cat.get('budgetSol')) or 0.05)
        if not 0 < sol <= cap + 1e-9:
            raise ValueError(f'{sol:g} SOL is over its {cap:g} SOL per-buy budget')
        if spent_today(cat, now) + sol > day_cap(cat) + 1e-9:
            raise ValueError(f'its daily cap is {day_cap(cat):g} SOL — {spent_today(cat, now):g} spent in the last 24h')
        if sol + GAS_SOL > _f(sol_bal) + 1e-9:
            raise ValueError(f'the wallet holds {_f(sol_bal):.4f} SOL — {sol:g} + {GAS_SOL:g} for gas is needed')
        return SOL, p['mint'], f'{sol:.9f}'.rstrip('0').rstrip('.')
    if p.get('side') == 'sell':
        if p.get('mint') not in (cat.get('realHeld') or {}):
            raise ValueError('it only sells a coin it really bought')
        amt = _f(token_amt) * min(1.0, max(0.0, _f(p.get('fraction'), 1.0)))
        if amt <= 0:
            raise ValueError('the wallet holds none of that coin')
        if _f(sol_bal) < GAS_SOL / 2:
            raise ValueError('no SOL left for gas')
        return p['mint'], SOL, f'{amt:.9f}'.rstrip('0').rstrip('.')
    raise ValueError('buy or sell only')


def b58_tx(b64):
    return base58.b58encode(base64.b64decode(b64, validate=True)).decode()


async def send(http, cm_key, cat, p, now):
    """Quote for the cat's wallet → Crossmint signs + sends. → the tx record (also on cat['agentTx'] and p['agentTx']). Raises ValueError."""
    w = cat.get('agentWallet') or {}; addr = w.get('address'); circle = w.get('provider') == 'circle'
    env = _aw.env_of(cm_key)
    if not addr or not (env or circle):
        raise ValueError('no agent wallet or no CROSSMINT_API_KEY')
    h = await http.get(f'{TRADE}/holdings/{addr}', timeout=15)
    if h.status_code != 200:
        raise ValueError(f'could not read the wallet ({h.status_code})')
    held = {t.get('mint'): _f(t.get('amount')) for t in (h.json() or {}).get('tokens') or []}
    i, o, amount = guard(cat, p, held.get(SOL, 0.0), held.get(p.get('mint'), 0.0), now)
    q = await http.post(f'{TRADE}/quote', json={'input_mint': i, 'output_mint': o, 'amount': amount, 'wallet': addr, 'slippage_bps': SLIP_BPS}, timeout=20)
    if q.status_code != 200:
        raise ValueError(f"no quote: {str((q.json() or {}).get('detail') if q.headers.get('content-type', '').startswith('application/json') else q.text)[:160]}")
    qj = q.json() or {}
    if qj.get('input_mint') != i or qj.get('output_mint') != o or not (qj.get('quote') or {}).get('transaction'):
        raise ValueError('the quote did not match the coins asked for — nothing sent')
    rec = {'pid': p['id'], 'side': p['side'], 'mint': p.get('mint'), 'symbol': p.get('symbol'), 'sol': _f(p.get('sol')) if p['side'] == 'buy' else 0.0,
           'amount': amount, 'orderId': qj.get('order_id'), 'status': 'sending', 'at': round(now), 'key': f"feeless-{cat.get('id')}-{p['id']}",
           'tx': qj['quote']['transaction'] if circle else b58_tx(qj['quote']['transaction'])}   # kept until the signer answers: a lost reply is re-asked with the SAME idempotency key (never a 2nd trade)
    cat['agentTx'] = ([rec] + list(cat.get('agentTx') or []))[:KEEP]   # written BEFORE the send: a trade that may have gone out is never forgotten
    p['agentTx'] = rec['key']
    if circle:
        rec['via'] = 'circle'
        await _circle_post(http, cat, rec)
    else:
        await _post(http, cm_key, env, addr, rec)
    return rec


async def _circle_post(http, cat, rec):
    """🟦 Circle signs (only the wallet assigned to this cat), our RPC sends; the reputation service keeps key → signature, so a lost
    reply asked again with the SAME key never sends a second trade."""
    w = cat.get('agentWallet') or {}
    r = await http.post(f'{REP}/internal/agent-circle-send', headers=_internal_headers(), json={'catId': cat.get('id'), 'acct': w.get('circleAcct'), 'walletId': w.get('circleId'), 'address': w.get('address'),
                        'tx': rec['tx'], 'key': rec['key']}, timeout=40)
    if r.status_code != 200:
        if 400 <= r.status_code < 500:
            rec.update(status='failed', error=f"Circle refused it ({r.status_code}): {str((r.json() or {}).get('detail') if r.content else '')[:120]}"); rec.pop('tx', None)
            raise ValueError(rec['error'])
        raise ValueError(f'Circle did not answer ({r.status_code}) — asked again next pass, never sent twice')
    rec.update(status='pending', sig=(r.json() or {}).get('signature')); rec.pop('tx', None)


def _internal_headers():
    from pathlib import Path
    try:
        return {'x-feeless-internal': (Path(__file__).parent / 'data' / 'internal.key').read_text().strip()}
    except OSError:
        return {}


async def _circle_status(http, sig):
    """→ 'success' | 'failed' | None (not landed yet), from our own RPC proxy."""
    r = await http.post(f'{REP}/rpc', json={'jsonrpc': '2.0', 'id': 1, 'method': 'getSignatureStatuses', 'params': [[sig], {'searchTransactionHistory': True}]}, timeout=15)
    v = (((r.json() or {}).get('result') or {}).get('value') or [None])[0] if r.status_code == 200 else None
    if not v:
        return None
    return 'failed' if v.get('err') else ('success' if v.get('confirmationStatus') in ('confirmed', 'finalized') else None)


async def _post(http, cm_key, env, addr, rec):
    """Create (or, with the same idempotency key, re-read) the Crossmint tx for `rec`. A refusal fails the record with Crossmint's words."""
    r = await http.post(f"{_aw.API[env]}/wallets/{addr}/transactions", headers={'X-API-KEY': cm_key, 'Content-Type': 'application/json', 'x-idempotency-key': rec['key']},
                        json={'params': {'transaction': rec['tx']}}, timeout=25)
    if r.status_code not in (200, 201):
        if 400 <= r.status_code < 500:
            rec.update(status='failed', error=f'Crossmint refused it ({r.status_code}): {_aw._err(r)}'); rec.pop('tx', None)
            raise ValueError(rec['error'])
        raise ValueError(f'Crossmint did not answer ({r.status_code}) — it is asked again next pass, never sent twice')
    j = r.json() or {}
    rec.update(id=j.get('id'), status=j.get('status') or 'pending'); rec.pop('tx', None)


def settle(cat, rec, reply, now):
    """Crossmint's read of one tx → the record + its proposal. success → the proposal is done with its on-chain signature (a buy marks the
    coin held, a full sell clears it); failed → the proposal fails with Crossmint's words. → True when it changed."""
    st = (reply or {}).get('status')
    if not st or st == rec.get('status'):
        return False
    rec['status'] = st
    p = next((x for x in cat.get('proposals') or [] if x.get('id') == rec.get('pid')), None)
    if st == 'success':
        sig = str(((reply or {}).get('onChain') or {}).get('txId') or '')[:100] or None
        rec['sig'] = sig
        if p and p.get('status') in ('pending', 'expired'):   # it went through: the coin is held even if the proposal's clock ran out meanwhile
            p.update(status='done', answeredAt=now, sig=sig, by='agent')
            held = cat.setdefault('realHeld', {})
            if p['side'] == 'buy':
                held[p['mint']] = {'at': now, 'symbol': p.get('symbol'), 'pair': p.get('pair'), 'agent': True}
            elif _f(p.get('fraction'), 1.0) >= 0.99:
                held.pop(p.get('mint'), None)
    elif st == 'failed':
        rec['error'] = str((reply or {}).get('error') or 'failed on chain')[:160]
        if p and p.get('status') in ('pending', 'expired'):
            p.update(status='failed', answeredAt=now, why2=rec['error'])
    return True


async def poll(http, cm_key, cat, now):
    """Re-read every live tx of this cat from Crossmint. → how many changed."""
    addr = (cat.get('agentWallet') or {}).get('address'); env = _aw.env_of(cm_key); n = 0
    if (cat.get('agentWallet') or {}).get('provider') == 'circle':   # 🟦 Circle: re-ask a lost send (same key), then read each signature on-chain
        for rec in [t for t in cat.get('agentTx') or [] if t.get('status') == 'sending' and t.get('tx')]:
            try:
                await _circle_post(http, cat, rec); n += 1
            except ValueError:
                n += rec.get('status') == 'failed'
        for rec in [t for t in cat.get('agentTx') or [] if t.get('status') in LIVE and t.get('sig')]:
            st = await _circle_status(http, rec['sig'])
            if st and settle(cat, rec, {'status': st, 'onChain': {'txId': rec['sig']}, 'error': 'failed on chain' if st == 'failed' else None}, now):
                n += 1
        return n
    for rec in [t for t in cat.get('agentTx') or [] if t.get('status') == 'sending' and t.get('tx')]:   # its reply was lost: ask again, same key
        try:
            await _post(http, cm_key, env, addr, rec); n += 1
        except ValueError:
            n += rec.get('status') == 'failed'
    for rec in [t for t in cat.get('agentTx') or [] if t.get('status') in LIVE and t.get('id')]:
        r = await http.get(f"{_aw.API[env]}/wallets/{addr}/transactions/{rec['id']}", headers={'X-API-KEY': cm_key}, timeout=15)
        if r.status_code == 200 and settle(cat, rec, r.json(), now):
            n += 1
    return n


async def run(http, cm_key, cat, now):
    """ONE cat's agent pass (the engine calls it): settle what is in flight, then send the next proposal it wants. A guard that stops a
    proposal writes its reason on it (`agentWhy`) and waits RETRY_SEC. → list of event words for the cat's log."""
    words = []
    w = cat.get('agentWallet') or {}
    if not w.get('address') or w.get('provider', 'crossmint') not in SIGNERS or (w.get('provider', 'crossmint') == 'crossmint' and not _aw.env_of(cm_key)):
        return words
    before = {t.get('key') or t.get('id'): t.get('status') for t in cat.get('agentTx') or []}
    await poll(http, cm_key, cat, now)
    for t in cat.get('agentTx') or []:
        if before.get(t.get('key') or t.get('id')) != t.get('status') and t.get('status') in ('success', 'failed'):
            words.append(f"{'✅' if t['status'] == 'success' else '⚠'} {t['side'].upper()} ${t.get('symbol')} from its wallet — "
                         + (f"done on-chain ({str(t.get('sig') or '')[:8]}…)" if t['status'] == 'success' else t.get('error') or 'failed'))
    if in_flight(cat):
        return words
    for p in sorted(cat.get('proposals') or [], key=lambda x: _f(x.get('at'))):
        if not wants(cat, p, now):
            continue
        try:
            rec = await send(http, cm_key, cat, p, now)
            words.append(f"🏇 {p['side'].upper()} ${p.get('symbol')} sent from its wallet ({rec['amount']} {'SOL' if p['side'] == 'buy' else 'coins'})")
        except ValueError as e:
            p['agentWhy'], p['agentTry'] = str(e)[:160], now
        break   # one trade at a time
    return words
