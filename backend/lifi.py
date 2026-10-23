"""LI.FI proxy: every EVM swap, bridge and gas route goes through here.

- The API key (LIFI_API_KEY) and integrator (LIFI_INTEGRATOR) stay on the server; the browser never sees them.
- The FEELESS fee (HQ -> Fees & Pricing, lifiFeeBps) is added here. If LI.FI refuses the fee
  (integrator not activated yet), the quote is retried without it so trading never breaks.
- Safety check on every quote: the transaction and the token approval must target LI.FI's own contracts,
  on the chain that was asked for, from the wallet that asked. Anything else is refused before it reaches a wallet.
- 🌉 SOLANA (2026-10-23): SOL / USDC out to every EVM chain and back. LI.FI builds the Solana transaction; `verify_svm` opens it and refuses
  it unless the user pays + is the ONLY signer, only `SVM_ALLOW` programs run (LI.FI's router must), nothing approves a delegate or hands the
  wallet away, and plain transfers never move more than the quote. The quote's fingerprint (the message minus its blockhash) is remembered;
  /solana/send only broadcasts a wallet-signed transaction whose fingerprint FEELESS quoted, once.
"""
import base64
import hashlib
import os
import re
import struct
import time

import httpx
from fastapi import APIRouter, Body, HTTPException, Query

LIFI_API = 'https://li.quest/v1'
RELAY = 'http://127.0.0.1:5077/api/reputation/rpc'   # the reputation service's Solana relay (keyed lanes → public nodes)
# LI.FI Diamond (router + approval target). Same address on every EVM chain LI.FI serves, except zkSync.
LIFI_CONTRACTS = {'0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae', '0x341e94069f53234fe6dabef707ad424830525715'}
SOLANA = 1151111081099710
# Zora is off: LI.FI stopped routing it (2026-10-23: "/toChain must be equal to one of the allowed values").
CHAINS = {1, 8453, 56, 42161, 43114, 137, 10, 324, 25, 130, 480, SOLANA}
ADDR = re.compile(r'^0x[0-9a-fA-F]{40}$')
SOL_ADDR = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
SOL_SIG = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$')
NATIVE = '0x0000000000000000000000000000000000000000'
SOL_NATIVE = '11111111111111111111111111111111'
LIFI_SVM = '3i5JeuZuUxeKtVysUnwQNGerJP2bSMX9fTFfS4Nxe3Br'   # in every Solana route LI.FI builds (relay, mayan, near, layerswap)
SYSTEM, TOKEN = '11111111111111111111111111111111', 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
SVM_ALLOW = {LIFI_SVM: 'LI.FI router', '99vQwtBwYtrqqD9YSXbdum3KBdxPAVxYTaQ3cfnJSrN2': 'Relay depository',
             'D8C8iW6zmoKg5TRr8nQ7h14TMWqQX8FiBdj2ju5MF3wa': 'Mayan', 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4': 'Jupiter (swap leg)',
             SYSTEM: 'System', 'ComputeBudget111111111111111111111111111111': 'Compute budget', TOKEN: 'Token',
             'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'Associated token account', 'Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo': 'Memo'}
SYS_REFUSE = {1: 'hands your wallet to a program', 4: 'touches a nonce', 5: 'touches a nonce', 6: 'touches a nonce', 7: 'touches a nonce',
              10: 'hands your wallet to a program'}
TOKEN_REFUSE = {4: 'approves a spender', 6: 'changes an account owner', 13: 'approves a spender'}
RENT_SLACK = 10_000_000   # 0.01 SOL: account rent + relayer tips a route may move beside the amount itself
MAX_TX_BYTES = 1232
_cache: dict = {}
_svm_quotes: dict = {}    # fingerprint → {'at', 'payer'}: the Solana routes FEELESS quoted (15 min, sent once)


def _headers():
    key = os.environ.get('LIFI_API_KEY', '').strip()
    return {'x-lifi-api-key': key} if key else {}


async def _fee_bps():
    """HQ setting (reputation service); 0 when unset or unreachable."""
    hit = _cache.get('fee')
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    bps = 0
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            d = (await http.get('http://127.0.0.1:5077/api/reputation/fees/public')).json()
            bps = int(round(float((d.get('lifi') or {}).get('fee') or 0) * 10000))
    except Exception:
        bps = 0
    _cache['fee'] = (time.time(), bps)
    return bps


def verify_route(q, from_chain, from_address, to_address=None):
    """Refuse any route that doesn't send the user's own transaction to LI.FI's contract on the right chain."""
    tx = q.get('transactionRequest') or {}
    est = q.get('estimate') or {}
    to = str(tx.get('to') or '').lower()
    if to not in LIFI_CONTRACTS:
        raise HTTPException(502, 'Route refused by FEELESS safety check: unexpected contract.')
    if int(tx.get('chainId') or 0) != int(from_chain):
        raise HTTPException(502, 'Route refused by FEELESS safety check: wrong network.')
    approval = str(est.get('approvalAddress') or '').lower()
    if approval and approval not in LIFI_CONTRACTS:
        raise HTTPException(502, 'Route refused by FEELESS safety check: unexpected approval target.')
    if str((q.get('action') or {}).get('fromAddress') or '').lower() != from_address.lower():
        raise HTTPException(502, 'Route refused by FEELESS safety check: quote is for a different wallet.')
    _same_payout(q, to_address or from_address)
    return {'verified': True, 'contract': tx.get('to'), 'chainId': int(tx.get('chainId'))}


def _same_payout(q, to_address):
    got = str((q.get('action') or {}).get('toAddress') or '')
    if got and (got.lower() != to_address.lower() if got.startswith('0x') else got != to_address):
        raise HTTPException(502, 'Route refused by FEELESS safety check: it pays out to a different wallet.')


def eco(chain):
    return 'svm' if int(chain) == SOLANA else 'evm'


def address_ok(chain, address):
    return bool((SOL_ADDR if eco(chain) == 'svm' else ADDR).match(str(address or '')))


def fingerprint(msg):
    """The message minus its recent blockhash: the wallet may sign it with a fresh blockhash, nothing else may change."""
    raw = bytes(msg)
    return hashlib.sha256(raw.replace(bytes(msg.recent_blockhash), bytes(32), 1)).hexdigest()


def verify_svm(b64, payer, from_token=SOL_NATIVE, from_amount=0, signed=False):
    """A LI.FI Solana transaction → (ok, why, fingerprint). The user pays and is the ONLY signer; only SVM_ALLOW programs run and LI.FI's
    router does; nothing approves a spender, changes an owner or hands the wallet to a program; plain SOL / token transfers out of the wallet
    never add up to more than the quoted amount (+ RENT_SLACK of SOL for rent). `signed`: the wallet's signature must be on it. Pure."""
    from solders.transaction import VersionedTransaction
    try:
        raw = base64.b64decode(str(b64 or ''), validate=True)
        tx = VersionedTransaction.from_bytes(raw)
    except Exception:
        return False, 'Not a transaction.', None
    if len(raw) > MAX_TX_BYTES:
        return False, 'Not a transaction.', None
    msg = tx.message; keys = [str(k) for k in msg.account_keys]
    if not keys or keys[0] != payer:
        return False, 'The fee payer is not your wallet.', None
    if msg.header.num_required_signatures != 1:
        return False, 'Someone besides you would sign it — refused.', None
    progs, sol_out, tok_out = set(), 0, 0
    for ix in msg.instructions:
        if ix.program_id_index >= len(keys):
            return False, 'It calls a program it does not list.', None
        prog, data = keys[ix.program_id_index], bytes(ix.data)
        acc = [keys[a] if a < len(keys) else None for a in ix.accounts]
        progs.add(prog)
        if prog == SYSTEM and len(data) >= 4:
            tag = struct.unpack('<I', data[:4])[0]
            if tag in SYS_REFUSE:
                return False, f'It {SYS_REFUSE[tag]} — refused.', None
            if tag == 2 and len(data) >= 12 and acc and acc[0] == payer:
                sol_out += struct.unpack('<Q', data[4:12])[0]
        elif prog == TOKEN and data:
            if data[0] in TOKEN_REFUSE:
                return False, f'It {TOKEN_REFUSE[data[0]]} — refused.', None
            owner = acc[2] if data[0] == 3 and len(acc) > 2 else acc[3] if data[0] == 12 and len(acc) > 3 else None
            if owner == payer and len(data) >= 9:
                tok_out += struct.unpack('<Q', data[1:9])[0]
    bad = sorted(p for p in progs if p not in SVM_ALLOW)
    if bad:
        return False, f'It calls a program FEELESS does not know ({bad[0][:6]}…) — refused.', None
    if LIFI_SVM not in progs:
        return False, 'It never goes through LI.FI — refused.', None
    amount = int(from_amount or 0)
    if sol_out > (amount if from_token == SOL_NATIVE else 0) + RENT_SLACK:
        return False, 'It sends more SOL than the quote — refused.', None
    if from_token != SOL_NATIVE and tok_out > amount:
        return False, 'It sends more tokens than the quote — refused.', None
    if signed and bytes(tx.signatures[0]) == bytes(64):
        return False, 'Your wallet did not sign it.', None
    return True, None, fingerprint(msg)


def remember(fp, payer, now=None):
    now = now or time.time()
    for k in [k for k, v in _svm_quotes.items() if now - v['at'] > 900]:
        _svm_quotes.pop(k, None)
    if len(_svm_quotes) > 2000:
        _svm_quotes.clear()
    _svm_quotes[fp] = {'at': now, 'payer': payer}


def take(fp, payer, now=None):
    """A quoted, unexpired fingerprint for this payer → True once (no resubmits)."""
    hit = _svm_quotes.get(fp)
    if not hit or hit['payer'] != payer or (now or time.time()) - hit['at'] > 900:
        return False
    _svm_quotes.pop(fp, None)
    return True


def create_lifi_router():
    router = APIRouter(prefix='/api/lifi', tags=['lifi'])

    @router.get('/quote')
    async def quote(fromChain: int, toChain: int, fromToken: str, toToken: str, fromAmount: str, fromAddress: str,
                    slippage: float = Query(0.005, ge=0.0005, le=0.05), toAddress: str = ''):
        if fromChain not in CHAINS or toChain not in CHAINS:
            raise HTTPException(400, 'Unsupported network.')
        to_address = toAddress or (fromAddress if eco(fromChain) == eco(toChain) else '')
        if not address_ok(fromChain, fromAddress):
            raise HTTPException(400, 'Invalid wallet address.')
        if not address_ok(toChain, to_address):
            raise HTTPException(400, 'Connect your wallet on the other side to receive.')
        for chain, tok in ((fromChain, fromToken), (toChain, toToken)):   # token address, or a plain symbol LI.FI resolves (e.g. USDC)
            if not ((SOL_ADDR if eco(chain) == 'svm' else ADDR).match(tok) or re.match(r'^[A-Za-z0-9]{2,11}$', tok)):
                raise HTTPException(400, 'Invalid token.')
        if not fromAmount.isdigit() or int(fromAmount) <= 0:
            raise HTTPException(400, 'Invalid amount.')
        params = {'fromChain': fromChain, 'toChain': toChain, 'fromToken': fromToken, 'toToken': toToken,
                  'fromAmount': fromAmount, 'fromAddress': fromAddress, 'toAddress': to_address, 'slippage': slippage}
        integrator = os.environ.get('LIFI_INTEGRATOR', '').strip()
        if integrator:
            params['integrator'] = integrator
        bps = await _fee_bps()
        fee_note = None
        svm = eco(fromChain) == 'svm'
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.get(f'{LIFI_API}/quote', params={**params, **({'fee': bps / 10000} if bps and integrator else {})}, headers=_headers())
            d = r.json()
            if bps and integrator and r.status_code >= 400 and re.search(r'integrator|fee', str(d.get('message') or ''), re.I):
                fee_note = 'FEELESS fee skipped: LI.FI has not activated the integrator fee wallet yet.'
                r = await http.get(f'{LIFI_API}/quote', params=params, headers=_headers())
                d = r.json()
            if r.status_code >= 400 or not d.get('transactionRequest'):
                raise HTTPException(400 if r.status_code < 500 else 503, str(d.get('message') or 'No route for this trade right now.')[:240])
            if svm:   # a route FEELESS refuses → ask once more without that bridge
                ok, why, fp = verify_svm((d.get('transactionRequest') or {}).get('data'), fromAddress, fromToken, fromAmount)
                if not ok and d.get('tool'):
                    print('lifi svm refused:', d.get('tool'), why)
                    r2 = await http.get(f'{LIFI_API}/quote', params={**params, 'denyBridges': d['tool']}, headers=_headers())
                    d2 = r2.json() if r2.status_code < 400 else {}
                    if d2.get('transactionRequest'):
                        d = d2
                        ok, why, fp = verify_svm(d['transactionRequest'].get('data'), fromAddress, fromToken, fromAmount)
        if svm:
            if not ok:
                raise HTTPException(502, f'Route refused by FEELESS safety check: {why}')
            if str((d.get('action') or {}).get('fromAddress') or '') != fromAddress:
                raise HTTPException(502, 'Route refused by FEELESS safety check: quote is for a different wallet.')
            _same_payout(d, to_address)
            remember(fp, fromAddress)
            safety = {'verified': True, 'chainId': SOLANA, 'fingerprint': fp}
        else:
            safety = verify_route(d, fromChain, fromAddress, to_address)
        d['feeless'] = {'safety': safety, 'feeBps': 0 if fee_note else bps, 'note': fee_note}
        return d

    @router.post('/solana/send')
    async def solana_send(body: dict = Body(...)):
        """A wallet-signed LI.FI Solana route → checked again (same rules, signed, a fingerprint FEELESS quoted, once) → broadcast."""
        signed = str((body or {}).get('signed') or '')
        try:
            from solders.transaction import VersionedTransaction
            tx = VersionedTransaction.from_bytes(base64.b64decode(signed, validate=True))
            payer = str(tx.message.account_keys[0])
        except Exception:
            raise HTTPException(400, 'Not a transaction.')
        ok, why, fp = verify_svm(signed, payer, signed=True, from_amount=10 ** 18)   # the amount was checked at quote time; the fingerprint pins it
        if not ok:
            raise HTTPException(400, f'Refused: {why}')
        if not take(fp, payer):
            raise HTTPException(409, 'This transaction was not quoted by FEELESS, expired, or was already sent — get a fresh quote.')
        try:
            async with httpx.AsyncClient(timeout=25) as http:
                r = await http.post(RELAY, json={'jsonrpc': '2.0', 'id': 1, 'method': 'sendTransaction',
                                                 'params': [signed, {'encoding': 'base64', 'skipPreflight': False, 'preflightCommitment': 'confirmed', 'maxRetries': 3}]})
                out = r.json()
        except Exception:
            remember(fp, payer)   # the same signed bytes may be sent again (same signature — never a second transfer)
            raise HTTPException(503, 'Solana did not answer — try again.')
        if out.get('error') or not out.get('result'):
            remember(fp, payer)
            raise HTTPException(400, f"Solana refused it: {str((out.get('error') or {}).get('message') or 'no signature')[:200]}")
        return {'signature': out['result']}

    @router.get('/tokens')
    async def tokens(chain: int, q: str = Query('', max_length=64)):
        """Token list for one chain (cached 10 min), filtered by name / symbol / address, top 60."""
        if chain not in CHAINS:
            raise HTTPException(400, 'Unsupported network.')
        hit = _cache.get(('tokens', chain))
        if not hit or time.time() - hit[0] > 600:
            async with httpx.AsyncClient(timeout=30) as http:
                d = (await http.get(f'{LIFI_API}/tokens', params={'chains': chain}, headers=_headers())).json()
            rows = [{'address': t.get('address'), 'symbol': t.get('symbol'), 'name': t.get('name'), 'decimals': t.get('decimals'),
                     'logoURI': t.get('logoURI'), 'priceUSD': t.get('priceUSD')} for t in (d.get('tokens') or {}).get(str(chain), [])]
            hit = (time.time(), rows)
            _cache[('tokens', chain)] = hit
        rows = hit[1]
        needle = q.strip().lower()
        if needle:
            exact = [t for t in rows if (t['address'] or '').lower() == needle or (t['symbol'] or '').lower() == needle]
            rest = [t for t in rows if t not in exact and (needle in (t['symbol'] or '').lower() or needle in (t['name'] or '').lower())]
            rows = exact + rest
        return {'chain': chain, 'tokens': rows[:60]}

    @router.get('/token')
    async def token(chain: int, token: str):
        if chain not in CHAINS or not address_ok(chain, token):
            raise HTTPException(400, 'Invalid token.')
        async with httpx.AsyncClient(timeout=20) as http:
            r = await http.get(f'{LIFI_API}/token', params={'chain': chain, 'token': token}, headers=_headers())
        if r.status_code >= 400:
            raise HTTPException(404, 'Token not found on this network.')
        return r.json()

    @router.get('/status')
    async def status(txHash: str, fromChain: int, toChain: int):
        if not (re.match(r'^0x[0-9a-fA-F]{64}$', txHash) or SOL_SIG.match(txHash)):
            raise HTTPException(400, 'Invalid transaction hash.')
        async with httpx.AsyncClient(timeout=20) as http:
            r = await http.get(f'{LIFI_API}/status', params={'txHash': txHash, 'fromChain': fromChain, 'toChain': toChain}, headers=_headers())
        d = r.json()
        rec = d.get('receiving') or {}
        tok = rec.get('token') or {}
        got = None
        try:
            got = int(rec.get('amount')) / 10 ** int(tok.get('decimals'))
        except (TypeError, ValueError):
            pass
        return {'status': d.get('status'), 'substatus': d.get('substatus'), 'message': d.get('substatusMessage'),
                'receiving': rec.get('txHash'), 'receivingLink': rec.get('txLink'), 'got': got, 'symbol': tok.get('symbol'),
                'explorer': d.get('lifiExplorerLink')}

    return router
