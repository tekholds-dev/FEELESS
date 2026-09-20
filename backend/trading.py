"""Jupiter-managed Solana swaps. The wallet signs; this service never signs."""
import asyncio
import base64
import os
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
    slippage_bps: int = Field(50, ge=1, le=500)

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

    async def rpc(self, method, params):
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
        try:
            async with httpx.AsyncClient(timeout=25) as http:
                res = await http.request(method, os.environ['JUPITER_API_URL'] + path,
                                         headers={'x-api-key': os.environ['JUPITER_API_KEY']}, **kwargs)
                data = res.json()
            if res.status_code >= 400:
                detail = data.get('errorMessage') or data.get('error') or 'Jupiter route unavailable'
                raise HTTPException(503 if res.status_code >= 500 else 400, str(detail)[:200])
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

    def router(self):
        router = APIRouter(prefix='/api/trading')

        @router.get('/status')
        async def status():
            return {'provider': 'Jupiter', 'network': 'solana-mainnet', 'signing': 'Phantom',
                    'configured': bool(os.environ.get('JUPITER_API_KEY') and os.environ.get('SOLANA_RPC_URL')),
                    'fee_back_status': 'PLANNED', 'eligible_fee_rules': 'Not activated',
                    'supported_execution_chains': ['solana']}

        @router.get('/mint/{mint}')
        async def mint_info(mint: str):
            return await self.metadata(mint)

        @router.get('/balance/{wallet}')
        async def balance(wallet: str):
            result = await self.rpc('getBalance', [valid_key(wallet), {'commitment': 'confirmed'}])
            return {'lamports': result['value'], 'slot': result['context']['slot'], 'source': 'Solana RPC'}

        @router.post('/quote')
        async def quote(body: QuoteIn, request: Request):
            ip = request.client.host
            queue = self.rate[ip]
            while queue and time.monotonic() - queue[0] > 60:
                queue.popleft()
            if len(queue) >= 12:
                raise HTTPException(429, 'Quote limit reached. Wait one minute.')
            queue.append(time.monotonic())
            valid_key(body.input_mint); valid_key(body.output_mint)
            if body.wallet:
                valid_key(body.wallet)
            if body.input_mint == body.output_mint:
                raise HTTPException(400, 'Choose different input and output tokens')
            meta_in = await self.metadata(body.input_mint)
            # Exact input units. Never silently round a user's amount.
            human = Decimal(body.amount)
            atoms = human * (Decimal(10) ** meta_in['decimals'])
            if human <= 0 or atoms != atoms.to_integral_value() or atoms > 2**64 - 1:
                raise HTTPException(400, 'Invalid amount or too many decimal places')
            params = {'inputMint': body.input_mint, 'outputMint': body.output_mint,
                      'amount': str(int(atoms)), 'slippageBps': body.slippage_bps}
            if body.wallet:
                params['taker'] = body.wallet
            data = await self.jupiter('GET', '/swap/v2/order', params=params)
            if data.get('errorCode') or not data.get('outAmount'):
                raise HTTPException(400, data.get('errorMessage') or 'No executable route available for this pair')
            try:
                meta_out = await self.metadata(body.output_mint)
            except HTTPException:
                meta_out = None
            order_id = str(uuid.uuid4())
            created = datetime.now(timezone.utc).isoformat()
            record = {'order_id': order_id, 'wallet': body.wallet, 'state': 'quoted', 'created_at': created,
                      'expires_at': time.time() + 45, 'input_mint': body.input_mint, 'output_mint': body.output_mint,
                      'quote': data, 'simulated': False}
            await self.db.swap_orders.insert_one(record)
            return {'order_id': order_id, 'created_at': created, 'expires_at': record['expires_at'],
                    'input_metadata': meta_in, 'output_metadata': meta_out, 'quote': data,
                    'fee_back': {'status': 'PLANNED', 'eligible_usd': None, 'distribution': None}}

        @router.post('/simulate')
        async def simulate(body: OrderId):
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
            valid_key(wallet)
            orders = await self.db.swap_orders.find({'wallet': wallet, 'signature': {'$exists': True}},
                {'_id': 0, 'order_id': 1, 'state': 1, 'signature': 1, 'created_at': 1, 'input_mint': 1, 'output_mint': 1}).sort('created_at', -1).limit(30).to_list(30)
            return {'transactions': orders, 'eligible_fees_usd': None, 'distributions': [], 'fee_back_status': 'PLANNED'}
        return router