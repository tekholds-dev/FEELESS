"""LI.FI proxy: every EVM swap, bridge and gas route goes through here.

- The API key (LIFI_API_KEY) and integrator (LIFI_INTEGRATOR) stay on the server; the browser never sees them.
- The FEELESS fee (HQ -> Fees & Pricing, lifiFeeBps) is added here. If LI.FI refuses the fee
  (integrator not activated yet), the quote is retried without it so trading never breaks.
- Safety check on every quote: the transaction and the token approval must target LI.FI's own contracts,
  on the chain that was asked for, from the wallet that asked. Anything else is refused before it reaches a wallet.
"""
import os
import re
import time

import httpx
from fastapi import APIRouter, HTTPException, Query

LIFI_API = 'https://li.quest/v1'
# LI.FI Diamond (router + approval target). Same address on every EVM chain LI.FI serves, except zkSync.
LIFI_CONTRACTS = {'0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae', '0x341e94069f53234fe6dabef707ad424830525715'}
CHAINS = {1, 8453, 56, 42161, 43114, 137, 10, 324, 7777777, 25, 130, 480}
ADDR = re.compile(r'^0x[0-9a-fA-F]{40}$')
NATIVE = '0x0000000000000000000000000000000000000000'
_cache: dict = {}


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


def verify_route(q, from_chain, from_address):
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
    return {'verified': True, 'contract': tx.get('to'), 'chainId': int(tx.get('chainId'))}


def create_lifi_router():
    router = APIRouter(prefix='/api/lifi', tags=['lifi'])

    @router.get('/quote')
    async def quote(fromChain: int, toChain: int, fromToken: str, toToken: str, fromAmount: str, fromAddress: str,
                    slippage: float = Query(0.005, ge=0.0005, le=0.05)):
        if fromChain not in CHAINS or toChain not in CHAINS:
            raise HTTPException(400, 'Unsupported network.')
        if not ADDR.match(fromAddress):
            raise HTTPException(400, 'Invalid wallet address.')
        for tok in (fromToken, toToken):   # token address, or a plain symbol LI.FI resolves (e.g. USDC)
            if not (ADDR.match(tok) or re.match(r'^[A-Za-z0-9]{2,11}$', tok)):
                raise HTTPException(400, 'Invalid token.')
        if not fromAmount.isdigit() or int(fromAmount) <= 0:
            raise HTTPException(400, 'Invalid amount.')
        params = {'fromChain': fromChain, 'toChain': toChain, 'fromToken': fromToken, 'toToken': toToken,
                  'fromAmount': fromAmount, 'fromAddress': fromAddress, 'slippage': slippage}
        integrator = os.environ.get('LIFI_INTEGRATOR', '').strip()
        if integrator:
            params['integrator'] = integrator
        bps = await _fee_bps()
        fee_note = None
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.get(f'{LIFI_API}/quote', params={**params, **({'fee': bps / 10000} if bps and integrator else {})}, headers=_headers())
            d = r.json()
            if bps and integrator and r.status_code >= 400 and re.search(r'integrator|fee', str(d.get('message') or ''), re.I):
                fee_note = 'FEELESS fee skipped: LI.FI has not activated the integrator fee wallet yet.'
                r = await http.get(f'{LIFI_API}/quote', params=params, headers=_headers())
                d = r.json()
        if r.status_code >= 400 or not d.get('transactionRequest'):
            raise HTTPException(400 if r.status_code < 500 else 503, str(d.get('message') or 'No route for this trade right now.')[:240])
        d['feeless'] = {'safety': verify_route(d, fromChain, fromAddress), 'feeBps': 0 if fee_note else bps, 'note': fee_note}
        return d

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
        if chain not in CHAINS or not ADDR.match(token):
            raise HTTPException(400, 'Invalid token.')
        async with httpx.AsyncClient(timeout=20) as http:
            r = await http.get(f'{LIFI_API}/token', params={'chain': chain, 'token': token}, headers=_headers())
        if r.status_code >= 400:
            raise HTTPException(404, 'Token not found on this network.')
        return r.json()

    @router.get('/status')
    async def status(txHash: str, fromChain: int, toChain: int):
        if not re.match(r'^0x[0-9a-fA-F]{64}$', txHash):
            raise HTTPException(400, 'Invalid transaction hash.')
        async with httpx.AsyncClient(timeout=20) as http:
            r = await http.get(f'{LIFI_API}/status', params={'txHash': txHash, 'fromChain': fromChain, 'toChain': toChain}, headers=_headers())
        d = r.json()
        return {'status': d.get('status'), 'substatus': d.get('substatus'), 'message': d.get('substatusMessage'),
                'receiving': (d.get('receiving') or {}).get('txHash'), 'explorer': d.get('lifiExplorerLink')}

    return router
