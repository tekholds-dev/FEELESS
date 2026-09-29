"""Jupiter-managed Solana swaps. The wallet signs; this service never signs."""
import asyncio
import base64
import os
from pathlib import Path
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal
import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from pymongo import ReturnDocument

SOL_MINT = 'So11111111111111111111111111111111111111112'
JUPITER_API_URL = os.environ.get('JUPITER_API_URL', 'https://api.jup.ag').rstrip('/')
PAPER_AGENT_EXECUTION_BOUNDARY = {
    'mode': 'paper',
    'signing': 'disabled',
    'broadcast': 'disabled',
    'wallet_custody': 'none',
    'decision_adapters': 'market snapshots only',
}

def valid_key(value):
    try:
        Pubkey.from_string(value)
    except Exception:
        raise HTTPException(400, 'Invalid Solana public key')
    return value

class QuoteIn(BaseModel):
    input_mint: str
    output_mint: str
    amount: str = Field(min_length=1, max_length=40, pattern=r'^\d+(\.\d+)?$')
    wallet: str | None = None
    slippage_bps: int = Field(50, ge=1, le=5000)  # up to 50% for thin meme pools

class ExecuteIn(BaseModel):
    order_id: str = Field(min_length=32, max_length=40)
    signed_transaction: str = Field(min_length=40, max_length=20000)

class OrderId(BaseModel):
    order_id: str = Field(min_length=32, max_length=40)

class TradingService:
    def __init__(self, db):
        self.db = db
        self.metadata_cache = {}
        self.rate = defaultdict(deque)

    def configured(self):
        return bool(os.environ.get('JUPITER_API_KEY') and os.environ.get('SOLANA_RPC_URL'))

    def require_configured(self):
        if not self.configured():
            raise HTTPException(503, 'Trading execution is not configured. Add backend Jupiter and Solana RPC settings.')

    async def rpc(self, method, params):
        self.require_configured()
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                res = await http.post(os.environ['SOLANA_RPC_URL'], json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
                res.raise_for_status()
                data = res.json()
            if data.get('error'):
                raise HTTPException(503, 'Solana RPC rejected the request. Try later or configure a dedicated RPC.')
            return data.get('result')
        except (httpx.HTTPError, ValueError):
            raise HTTPException(503, 'Solana RPC unavailable. No transaction was submitted.')

    async def jupiter(self, method, path, **kwargs):
        self.require_configured()
        try:
            async with httpx.AsyncClient(timeout=25) as http:
                # Jupiter rate-limits per key: back off and retry briefly instead of failing the trade.
                for attempt in range(3):
                    res = await http.request(method, JUPITER_API_URL + path,
                                             headers={'x-api-key': os.environ['JUPITER_API_KEY']}, **kwargs)
                    if res.status_code != 429:
                        break
                    await asyncio.sleep(1.2 * (attempt + 1))
                if res.status_code == 429:
                    raise HTTPException(503, 'Jupiter is busy right now — try again in a few seconds. Nothing was sent.')
                data = res.json()
            if res.status_code >= 400:
                detail = str(data.get('errorMessage') or data.get('error') or data.get('message') or 'Jupiter route unavailable')
                if 'failed to get quotes' in detail.lower() or 'no routes' in detail.lower():
                    detail = 'No route for this pair right now — it may be too new, too thin, or not indexed by Jupiter yet. Try a smaller amount or check the coin in a moment.'
                raise HTTPException(503 if res.status_code >= 500 else 400, detail[:240])
            return data
        except (httpx.HTTPError, ValueError):
            raise HTTPException(503, 'Jupiter unavailable. Check status before retrying a submitted swap.')

    async def metadata(self, mint):
        valid_key(mint)
        hit = self.metadata_cache.get(mint)
        if hit and time.time() - hit['checked'] < 300:
            return hit['value']
        if mint == SOL_MINT:
            return {'mint': mint, 'decimals': 9, 'symbol': 'SOL', 'source': 'Solana native unit definition', 'supply': None}
        result = await self.rpc('getAccountInfo', [mint, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
        value = result.get('value') if result else None
        parsed = (value or {}).get('data', {}).get('parsed', {})
        if parsed.get('type') != 'mint':
            raise HTTPException(400, 'Address is not an RPC-verified token mint')
        info = parsed['info']
        metadata = {'mint': mint, 'decimals': info['decimals'], 'supply': info.get('supply'),
                    'mint_authority': info.get('mintAuthority'), 'freeze_authority': info.get('freezeAuthority'),
                    'owner_program': value.get('owner'), 'source': 'Solana RPC · confirmed',
                    'checked_at': datetime.now(timezone.utc).isoformat()}
        self.metadata_cache[mint] = {'checked': time.time(), 'value': metadata}
        return metadata

    async def fee_rule(self, body):
        """Creator-controlled FEELESS fee (Jupiter integrator fee → creator's referral account).
        The fee service is local and fast; if it is down or slow, no fee is charged — never a surprise fee."""
        try:
            key = (Path(__file__).parent / 'data' / 'internal.key').read_text().strip()
            async with httpx.AsyncClient(timeout=3) as http:
                r = await http.get('http://127.0.0.1:5077/api/reputation/internal/fees', headers={'x-feeless-internal': key},
                                   params={'wallet': body.wallet or '', 'inputMint': body.input_mint, 'outputMint': body.output_mint})
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {'bps': 0, 'notes': [], 'referralAccount': None}

    def router(self):
        router = APIRouter(prefix='/api/trading')

        @router.get('/status')
        async def status():
            return {'provider': 'Jupiter', 'network': 'solana-mainnet', 'signing': 'Phantom',
                    'configured': self.configured(),
                    'execution_ready': self.configured(),
                    'paper_agent_execution': PAPER_AGENT_EXECUTION_BOUNDARY,
                    'fee_back_status': 'PLANNED', 'eligible_fee_rules': 'Not activated',
                    'supported_execution_chains': ['solana'],
                    'detail': 'Backend execution is ready.' if self.configured()
                    else 'Add backend Jupiter and Solana RPC settings before requesting a signed swap.'}

        @router.get('/mint/{mint}')
        async def mint_info(mint: str):
            return await self.metadata(mint)

        @router.get('/balance/{wallet}')
        async def balance(wallet: str):
            result = await self.rpc('getBalance', [valid_key(wallet), {'commitment': 'confirmed'}])
            return {'lamports': result['value'], 'slot': result['context']['slot'], 'source': 'Solana RPC'}

        @router.get('/holdings/{wallet}')
        async def holdings(wallet: str):
            """Coins in the wallet (SOL + SPL + Token-2022), with symbol/icon/USD value from Jupiter,
            sorted by value — used to show "your coins first" in the swap picker."""
            valid_key(wallet)
            sol = await self.rpc('getBalance', [wallet, {'commitment': 'confirmed'}])
            amounts = {'So11111111111111111111111111111111111111112': sol['value'] / 1e9}
            for program in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
                res = await self.rpc('getTokenAccountsByOwner', [wallet, {'programId': program}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
                for row in (res or {}).get('value', []):
                    info = (((row.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
                    ui = float((info.get('tokenAmount') or {}).get('uiAmount') or 0)
                    if ui > 0 and info.get('mint'):
                        amounts[info['mint']] = amounts.get(info['mint'], 0) + ui
            mints = list(amounts)[:100]
            meta = {}
            if mints and os.environ.get('JUPITER_API_KEY'):
                try:
                    async with httpx.AsyncClient(timeout=12) as http:
                        r = await http.get(JUPITER_API_URL + '/tokens/v2/search', params={'query': ','.join(mints)},
                                           headers={'x-api-key': os.environ['JUPITER_API_KEY']})
                        meta = {t.get('id'): t for t in (r.json() or []) if isinstance(t, dict)}
                except (httpx.HTTPError, ValueError):
                    meta = {}
            out = []
            for mint in mints:
                t = meta.get(mint) or {}
                price = t.get('usdPrice')
                out.append({'mint': mint, 'symbol': t.get('symbol') or mint[:4], 'name': t.get('name') or '', 'icon': t.get('icon'),
                            'amount': amounts[mint], 'usd': round(amounts[mint] * price, 2) if price else None, 'verified': bool(t.get('isVerified'))})
            out.sort(key=lambda x: -(x['usd'] or 0))
            return {'wallet': wallet, 'tokens': out, 'source': 'Solana RPC + Jupiter tokens'}

        @router.post('/quote')
        async def quote(body: QuoteIn, request: Request):
            self.require_configured()
            ip = request.client.host
            queue = self.rate[ip]
            while queue and time.monotonic() - queue[0] > 60:
                queue.popleft()
            # Room for the swap card's 10s auto-refresh (6/min) plus manual quotes.
            if len(queue) >= 20:
                raise HTTPException(429, 'Quote limit reached. Wait one minute.')
            queue.append(time.monotonic())
            valid_key(body.input_mint); valid_key(body.output_mint)
            if body.wallet:
                valid_key(body.wallet)
            if body.input_mint == body.output_mint:
                raise HTTPException(400, 'Choose different input and output tokens')
            # Independent lookups run together: pay-coin decimals, receive-coin metadata and the FEELESS fee rule.
            meta_in, meta_out, fee = await asyncio.gather(self.metadata(body.input_mint), self.metadata(body.output_mint),
                                                          self.fee_rule(body), return_exceptions=True)
            if isinstance(meta_in, BaseException):
                raise meta_in
            meta_out = None if isinstance(meta_out, BaseException) else meta_out
            if isinstance(fee, BaseException):
                fee = {'bps': 0, 'notes': [], 'referralAccount': None}
            # Exact input units. Never silently round a user's amount.
            human = Decimal(body.amount)
            atoms = human * (Decimal(10) ** meta_in['decimals'])
            if human <= 0 or atoms != atoms.to_integral_value() or atoms > 2**64 - 1:
                raise HTTPException(400, 'Invalid amount or too many decimal places')
            params = {'inputMint': body.input_mint, 'outputMint': body.output_mint,
                      'amount': str(int(atoms)), 'slippageBps': body.slippage_bps}
            if body.wallet:
                params['taker'] = body.wallet
            fee_fallback = None
            if fee.get('bps') and fee.get('referralAccount'):
                params['referralAccount'] = fee['referralAccount']
                params['referralFee'] = int(fee['bps'])
            try:
                data = await self.jupiter('GET', '/swap/v2/order', params=params)
            except HTTPException as exc:
                # A broken fee setup (referral account / fee-mint token account not initialized at Jupiter)
                # must never block a user's trade: re-quote without the fee and flag it for the creator.
                if 'referralAccount' not in params or 'referral' not in str(exc.detail).lower():
                    raise
                params.pop('referralAccount'); params.pop('referralFee')
                fee_fallback = 'FEELESS fee skipped — the fee referral account is not set up for this route yet.'
                fee = {'bps': 0, 'notes': [fee_fallback], 'referralAccount': None}
                data = await self.jupiter('GET', '/swap/v2/order', params=params)
            if data.get('errorCode') or not data.get('outAmount'):
                raise HTTPException(400, data.get('errorMessage') or 'No executable route available for this pair')
            order_id = str(uuid.uuid4())
            created = datetime.now(timezone.utc).isoformat()
            record = {'order_id': order_id, 'wallet': body.wallet, 'state': 'quoted', 'created_at': created,
                      'expires_at': time.time() + 45, 'input_mint': body.input_mint, 'output_mint': body.output_mint,
                      'quote': data, 'simulated': False}
            await self.db.swap_orders.insert_one(record)
            return {'order_id': order_id, 'created_at': created, 'expires_at': record['expires_at'],
                    # Echoed so the UI can refuse to show or sign an order that no longer matches the picked coins.
                    'input_mint': body.input_mint, 'output_mint': body.output_mint, 'amount': body.amount,
                    'input_metadata': meta_in, 'output_metadata': meta_out, 'quote': data,
                    'feeless_fee': {'bps': int(fee.get('bps') or 0), 'notes': fee.get('notes') or [], 'fallback': bool(fee_fallback)},
                    'fee_back': {'status': 'PLANNED', 'eligible_usd': None, 'distribution': None}}

        @router.post('/simulate')
        async def simulate(body: OrderId):
            self.require_configured()
            order = await self.db.swap_orders.find_one({'order_id': body.order_id}, {'_id': 0})
            if not order or order['state'] != 'quoted' or order['expires_at'] <= time.time():
                raise HTTPException(409, 'Order expired. Request a fresh quote.')
            tx = order['quote'].get('transaction')
            if not tx or not order['wallet']:
                raise HTTPException(400, 'Connect a Solana wallet and request a new quote')
            result = await self.rpc('simulateTransaction', [tx, {'encoding': 'base64', 'sigVerify': False,
                                     'replaceRecentBlockhash': False, 'commitment': 'confirmed'}])
            value = result.get('value', {})
            if value.get('err'):
                raise HTTPException(400, f'Simulation failed: {str(value["err"])[:150]}. No transaction submitted.')
            await self.db.swap_orders.update_one({'order_id': body.order_id, 'state': 'quoted'}, {'$set': {'simulated': True}})
            return {'success': True, 'units_consumed': value.get('unitsConsumed'), 'broadcast': False}

        @router.post('/execute')
        async def execute(body: ExecuteIn):
            self.require_configured()
            order = await self.db.swap_orders.find_one({'order_id': body.order_id}, {'_id': 0})
            if not order:
                raise HTTPException(404, 'Unknown order')
            if order['state'] != 'quoted':
                return {'state': order['state'], 'signature': order.get('signature'), 'detail': 'Already processed. Check status; do not resubmit.'}
            if order['expires_at'] <= time.time() or not order.get('simulated'):
                raise HTTPException(409, 'Fresh quote and successful simulation required before signing')
            try:
                original = VersionedTransaction.from_bytes(base64.b64decode(order['quote']['transaction'], validate=True))
                signed = VersionedTransaction.from_bytes(base64.b64decode(body.signed_transaction, validate=True))
                if to_bytes_versioned(original.message) != to_bytes_versioned(signed.message):
                    raise ValueError('Transaction was changed')
                if str(signed.message.account_keys[0]) != order['wallet'] or not all(signed.verify_with_results()):
                    raise ValueError('Invalid wallet signatures')
                signature = str(signed.signatures[0])
            except Exception:
                raise HTTPException(400, 'Signed transaction does not match the approved Jupiter order')
            locked = await self.db.swap_orders.find_one_and_update({'order_id': body.order_id, 'state': 'quoted'},
                {'$set': {'state': 'submitted', 'signature': signature}}, projection={'_id': 0}, return_document=ReturnDocument.AFTER)
            if not locked:
                raise HTTPException(409, 'Order already submitted. Check its transaction status.')
            try:
                payload = {'signedTransaction': body.signed_transaction, 'requestId': order['quote']['requestId']}
                if order['quote'].get('lastValidBlockHeight') is not None:
                    payload['lastValidBlockHeight'] = order['quote']['lastValidBlockHeight']
                result = await self.jupiter('POST', '/swap/v2/execute', json=payload)
                if result.get('signature') and result['signature'] != signature:
                    raise HTTPException(502, 'Provider signature mismatch. Check transaction status.')
                if result.get('status') == 'Failed':
                    await self.db.swap_orders.update_one({'order_id': body.order_id}, {'$set': {'state': 'failed', 'provider_error': str(result.get('error') or result.get('code'))[:150]}})
                # No success claim without RPC confirmation, even if Jupiter says Success.
            except HTTPException:
                return {'state': 'submitted', 'signature': signature, 'detail': 'Provider response uncertain. Check status before any new trade.'}
            return await check_status(body.order_id)

        @router.get('/order/{order_id}')
        async def check_status(order_id: str):
            self.require_configured()
            order = await self.db.swap_orders.find_one({'order_id': order_id}, {'_id': 0})
            if not order:
                raise HTTPException(404, 'Order not found')
            signature = order.get('signature')
            state = order['state']
            if signature and state not in ['confirmed', 'failed']:
                try:
                    rpc = await self.rpc('getSignatureStatuses', [[signature], {'searchTransactionHistory': True}])
                    status = (rpc.get('value') or [None])[0]
                    if status and status.get('err'):
                        state = 'failed'
                    elif status and status.get('confirmationStatus') in ['confirmed', 'finalized']:
                        state = 'confirmed'
                    await self.db.swap_orders.update_one({'order_id': order_id}, {'$set': {'state': state}})
                except HTTPException:
                    pass
            return {'state': state, 'signature': signature, 'order_id': order_id,
                    'fee_back': 'Eligibility not activated; no distribution has been created.'}

        @router.get('/history/{wallet}')
        async def history(wallet: str):
            self.require_configured()
            valid_key(wallet)
            orders = await self.db.swap_orders.find({'wallet': wallet, 'signature': {'$exists': True}},
                {'_id': 0, 'order_id': 1, 'state': 1, 'signature': 1, 'created_at': 1, 'input_mint': 1, 'output_mint': 1}).sort('created_at', -1).limit(30).to_list(30)
            return {'transactions': orders, 'eligible_fees_usd': None, 'distributions': [], 'fee_back_status': 'PLANNED'}
        return router