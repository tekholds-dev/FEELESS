"""Jupiter-managed Solana swaps. The wallet signs; this service never signs."""
import asyncio
import hmac
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
from pydantic import BaseModel, Field, field_validator
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from pymongo import ReturnDocument

from fee_tx import DECIMALS, build_transaction, fee_instructions, lookup_tables, split_fee

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

    @field_validator('amount', mode='before')
    @classmethod
    def _amount(cls, v):
        # Accept what traders type: ".01" → "0.01", "1." → "1", "1,5" → "1.5".
        s = str(v or '').strip().replace(',', '.')
        s = ('0' + s) if s.startswith('.') else s
        return s[:-1] if s.endswith('.') else s
    wallet: str | None = None
    slippage_bps: int = Field(50, ge=1, le=5000)  # up to 50% for thin meme pools
    probe: bool = False   # fee self-test only (needs the internal key): quote as the fee wallet without its balance

class ExecuteIn(BaseModel):
    order_id: str = Field(min_length=32, max_length=40)
    signed_transaction: str = Field(min_length=40, max_length=20000)

class OrderId(BaseModel):
    order_id: str = Field(min_length=32, max_length=40)

def _usd_value(quote):
    for k in ('inUsdValue', 'swapUsdValue'):
        try:
            v = float(quote.get(k) or 0)
            if v > 0:
                return round(v, 4)
        except (TypeError, ValueError):
            pass
    return None


# Stable coins / SOL are the settlement side; the other mint is "the coin" a trade was about.
SETTLEMENT = {SOL_MINT, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}
POINTS_PER_USD_FEE = 100  # 1 FEE point per $0.01 of platform fee paid


def summarize_orders(orders, now=None):
    """Confirmed trades → earnings windows and per-coin totals (fee = trade value × fee bps)."""
    now = now or time.time()
    out = {'hour': 0.0, 'day': 0.0, 'week': 0.0, 'trades': 0, 'volumeUsd': 0.0, 'coins': {}}
    for o in orders:
        usd, bps = o.get('in_usd') or 0, o.get('fee_bps') or 0
        fee = usd * bps / 10000
        try:
            at = datetime.fromisoformat(o['created_at']).timestamp()
        except (KeyError, ValueError):
            continue
        age = now - at
        if age > 7 * 86400:
            continue
        out['week'] += fee; out['trades'] += 1; out['volumeUsd'] += usd
        if age <= 86400:
            out['day'] += fee
        if age <= 3600:
            out['hour'] += fee
        coin = o['output_mint'] if o.get('input_mint') in SETTLEMENT else o.get('input_mint')
        c = out['coins'].setdefault(coin, {'mint': coin, 'feesUsd': 0.0, 'trades': 0})
        c['feesUsd'] += fee; c['trades'] += 1
    coins = sorted(out['coins'].values(), key=lambda c: -c['feesUsd'])[:10]
    return {**{k: round(v, 4) if isinstance(v, float) else v for k, v in out.items() if k != 'coins'}, 'coins': [{**c, 'feesUsd': round(c['feesUsd'], 4)} for c in coins]}


# SOL kept back on a SOL-paid trade: network + priority fee and the temporary wSOL/token-account rent.
SOL_RESERVE_LAMPORTS = 4_500_000


def insufficient_message(mint, held, decimals, _out_symbol=None):
    have = held / 10 ** decimals
    if mint == SOL_MINT:
        room = max(0, held - SOL_RESERVE_LAMPORTS) / 1e9
        return (f'Not enough SOL: you have {have:.4f} SOL. The most you can swap is {room:.4f} SOL '
                f'(about {SOL_RESERVE_LAMPORTS / 1e9:.4f} SOL stays for network fees and account rent).')
    return f'Not enough of this coin: you hold {have:,.6g}.'


def explain_sim_error(err):
    """Solana simulation errors → plain English (what the big swap apps show instead of raw codes)."""
    text = str(err)
    code = None
    if isinstance(err, dict) and isinstance(err.get('InstructionError'), list) and len(err['InstructionError']) == 2:
        inner = err['InstructionError'][1]
        code = inner.get('Custom') if isinstance(inner, dict) else inner
    if code == 1 or 'InsufficientFunds' in text:
        return 'Not enough balance for this trade once fees are included. Lower the amount.'
    if code in (6001, 0x1771) or 'SlippageToleranceExceeded' in text:
        return 'Price moved more than your slippage. Get a fresh quote or raise slippage.'
    if 'BlockhashNotFound' in text:
        return 'Quote expired. Get a fresh quote.'
    if 'AccountNotFound' in text:
        return 'Your wallet has no SOL on this network yet. Fund it first.'
    return f'Simulation failed ({text[:120]}).'


class TradingService:
    def __init__(self, db):
        self.db = db
        self._http = None
        self.metadata_cache = {}
        self.rate = defaultdict(deque)

    @property
    def http(self):
        # One pooled client for every RPC / Jupiter call (keep-alive), instead of a new connection per request.
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(limits=httpx.Limits(max_connections=200, max_keepalive_connections=50))
        return self._http

    def configured(self):
        return bool(os.environ.get('JUPITER_API_KEY') and os.environ.get('SOLANA_RPC_URL'))

    def require_configured(self):
        if not self.configured():
            raise HTTPException(503, 'Trading execution is not configured. Add backend Jupiter and Solana RPC settings.')

    async def rpc(self, method, params):
        self.require_configured()
        try:
            res = await self.http.post(os.environ['SOLANA_RPC_URL'], json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}, timeout=15)
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
            # Jupiter rate-limits per key: back off and retry briefly instead of failing the trade.
            for attempt in range(3):
                res = await self.http.request(method, JUPITER_API_URL + path, timeout=25,
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

    async def swap_order(self, params, fee, wallet):
        """Jupiter Swap API with the FEELESS fee LOCKED in as its own transfer inside the trade (any fee up to the
        FEELESS cap; Jupiter's built-in fee tops out at 2.55%):
        - pay side is SOL/USDC (a buy): the fee is split off the amount and sent before the swap;
        - receive side is SOL/USDC (a sell): the fee is taken from the guaranteed minimum output, after the swap.
        If neither side can pay, the trade is refused (the quote endpoint may hand it to the Ultra fallback)."""
        by_mint = fee.get('feeAccountsByMint') or {}
        bps = int(fee.get('bps') or 0)
        in_mint, out_mint = params['inputMint'], params['outputMint']
        mode = ('none' if not bps else 'input' if by_mint.get(in_mint) and in_mint in DECIMALS
                else 'output' if by_mint.get(out_mint) and out_mint in DECIMALS else None)
        if mode is None:
            raise HTTPException(400, 'Every FEELESS trade pays the platform fee in SOL or USDC. Put SOL or USDC on one side.')
        query = {k: v for k, v in params.items() if k != 'taker'}
        fee_atoms = 0
        if mode == 'input':
            fee_atoms, swap_atoms = split_fee(int(params['amount']), bps)
            query['amount'] = str(swap_atoms)
        quote = await self.jupiter('GET', '/swap/v1/quote', params=query)
        if not quote.get('outAmount'):
            raise HTTPException(400, quote.get('error') or 'No executable route available for this pair')
        if mode == 'output':
            fee_atoms = int(quote['otherAmountThreshold']) * bps // 10000
        tx = last_valid = priority = None
        if wallet:
            req = {'quoteResponse': quote, 'userPublicKey': wallet, 'wrapAndUnwrapSol': True, 'dynamicComputeUnitLimit': True}
            cap = int(fee.get('priorityMaxLamports') or 0)
            if cap:
                req['prioritizationFeeLamports'] = {'priorityLevelWithMaxLamports': {'maxLamports': cap, 'priorityLevel': 'high'}}
            parts, latest = await asyncio.gather(self.jupiter('POST', '/swap/v1/swap-instructions', json=req),
                                                 self.rpc('getLatestBlockhash', [{'commitment': 'confirmed'}]))
            keys = parts.get('addressLookupTableAddresses') or []
            alts = ((await self.rpc('getMultipleAccounts', [keys, {'encoding': 'base64'}])) or {}).get('value') or [] if keys else []
            fee_mint = in_mint if mode == 'input' else out_mint
            fee_ixs = fee_instructions(wallet, fee_mint, by_mint[fee_mint], fee_atoms) if fee_atoms else []
            tx = build_transaction(wallet, parts, fee_ixs, lookup_tables(keys, alts), latest['value']['blockhash'], after=mode == 'output')
            last_valid, priority = latest['value']['lastValidBlockHeight'], parts.get('prioritizationFeeLamports')
            if fee_atoms:
                fee = {**fee, 'feeAccount': by_mint[fee_mint]}
        usd = float(quote.get('swapUsdValue') or 0) or None
        if usd and mode == 'input' and int(query['amount']):
            usd = usd * int(params['amount']) / int(query['amount'])  # value of everything the trader pays, fee included
        net = {}
        if mode == 'output' and fee_atoms:
            # What the trader actually keeps: received minus the FEELESS fee.
            net = {'outAmount': str(int(quote['outAmount']) - fee_atoms), 'otherAmountThreshold': str(int(quote['otherAmountThreshold']) - fee_atoms)}
        data = {**quote, **net, 'transaction': tx, 'router': 'Jupiter Swap API', 'lastValidBlockHeight': last_valid,
                'signatureFeeLamports': 5000, 'prioritizationFeeLamports': priority, 'rentFeeLamports': None,
                'inUsdValue': usd, 'feelessFeeMode': mode, 'feelessFeeAtoms': str(fee_atoms) if fee_atoms else None,
                'platformFee': {'feeBps': bps, 'amount': str(fee_atoms)} if mode != 'none' else None}
        return data, {**fee, 'bps': bps if mode != 'none' else 0}

    async def ultra_order(self, params, fee):
        """Jupiter Ultra: Jupiter builds and lands the transaction; fee via the referral account (0.5–2.55%)."""
        params = dict(params)
        bps = int(fee.get('ultraBps') or 0)
        if bps and fee.get('referralAccount'):
            params['referralAccount'] = fee['referralAccount']
            params['referralFee'] = bps
        try:
            data = await self.jupiter('GET', '/swap/v2/order', params=params)
        except HTTPException as exc:
            if 'referralAccount' not in params or 'referral' not in str(exc.detail).lower():
                raise
            params.pop('referralAccount'); params.pop('referralFee')
            data = await self.jupiter('GET', '/swap/v2/order', params=params)
            note = 'FEELESS fee skipped: the fee referral account is not set up for this route yet.'
            return self._ultra_checked(data), {**fee, 'bps': 0, 'notes': [note], 'fallback': note}
        return self._ultra_checked(data), {**fee, 'bps': bps if 'referralAccount' in params else 0}

    @staticmethod
    def _ultra_checked(data):
        if data.get('errorCode') or not data.get('outAmount'):
            raise HTTPException(400, data.get('errorMessage') or 'No executable route available for this pair')
        return data

    async def broadcast(self, signed_b64, signature, last_valid_block_height=None):
        """Swap API trades are ours to land: send, then re-send every 2s until confirmed, failed or expired."""
        opts = {'encoding': 'base64', 'skipPreflight': True, 'maxRetries': 0}
        for _ in range(30):
            try:
                await self.rpc('sendTransaction', [signed_b64, opts])
                status = ((await self.rpc('getSignatureStatuses', [[signature]])) or {}).get('value', [None])[0]
                if status and (status.get('err') or status.get('confirmationStatus') in ('confirmed', 'finalized')):
                    return
                if last_valid_block_height and (await self.rpc('getBlockHeight', [{'commitment': 'confirmed'}])) > last_valid_block_height:
                    return
            except HTTPException:
                pass
            await asyncio.sleep(2)

    async def balance_atoms(self, wallet, mint):
        """What the wallet holds of the coin it pays with (atoms), or None when unknown (no wallet / RPC down)."""
        if not wallet:
            return None
        try:
            if mint == SOL_MINT:
                return int(((await self.rpc('getBalance', [wallet, {'commitment': 'confirmed'}])) or {}).get('value') or 0)
            res = await self.rpc('getTokenAccountsByOwner', [wallet, {'mint': mint}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
            return sum(int((((a.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info', {}).get('tokenAmount', {}).get('amount') or 0)
                       for a in (res or {}).get('value') or [])
        except Exception:
            return None  # unknown balance never blocks a quote; the simulation still guards it

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

    async def trade_landed(self, order):
        """A confirmed trade earns season points (fees paid weigh most). Best effort, idempotent per signature."""
        try:
            key = (Path(__file__).parent / 'data' / 'internal.key').read_text().strip()
            async with httpx.AsyncClient(timeout=5) as http:
                await http.post('http://127.0.0.1:5077/api/reputation/internal/trade', headers={'x-feeless-internal': key},
                                json={'wallet': order.get('wallet') or '', 'signature': order.get('signature') or '', 'inUsd': order.get('in_usd') or 0,
                                      'feeBps': order.get('fee_bps') or 0, 'inputMint': order.get('input_mint') or '', 'outputMint': order.get('output_mint') or '',
                                      # the fee actually built into the transaction (Swap API): atoms of the input or output mint
                                      'feeAtoms': int((order.get('quote') or {}).get('feelessFeeAtoms') or 0),
                                      'feeMint': order.get('input_mint') if (order.get('quote') or {}).get('feelessFeeMode') == 'input' else order.get('output_mint') if (order.get('quote') or {}).get('feelessFeeMode') == 'output' else ''})
        except Exception:
            pass

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
            # The Command Center fee self-test quotes as the fee wallet, which doesn't hold the coins it tests with.
            # Only a caller holding the internal key may skip the balance check; nothing is ever signed or sent.
            probe = False
            if body.probe:
                try:
                    probe = hmac.compare_digest(request.headers.get('x-feeless-internal', ''), (Path(__file__).parent / 'data' / 'internal.key').read_text().strip())
                except OSError:
                    probe = False
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
            meta_in, meta_out, fee, held = await asyncio.gather(self.metadata(body.input_mint), self.metadata(body.output_mint),
                                                                self.fee_rule(body), self.balance_atoms(body.wallet, body.input_mint), return_exceptions=True)
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
            # Like the big swap apps: never quote what the wallet can't pay (SOL also covers fees + temporary rent).
            if isinstance(held, int) and not probe:
                need = int(atoms) + (SOL_RESERVE_LAMPORTS if body.input_mint == SOL_MINT else 0)
                if held < need:
                    raise HTTPException(400, insufficient_message(body.input_mint, held, meta_in['decimals'], (meta_out or {}).get('symbol')))
            params = {'inputMint': body.input_mint, 'outputMint': body.output_mint,
                      'amount': str(int(atoms)), 'slippageBps': body.slippage_bps}
            if body.wallet:
                params['taker'] = body.wallet
            if fee.get('blocked'):
                raise HTTPException(400, fee['blocked'])
            # Primary: Jupiter Swap API (FEELESS fee, capped priority fee, our broadcast).
            # Ultra runs only when configured as the engine, or as a fallback the creator switched on.
            engine = fee.get('engine') or 'swap'
            try:
                data, fee = await (self.ultra_order(params, fee) if engine == 'ultra' else self.swap_order(params, fee, body.wallet))
            except HTTPException as exc:
                if engine != 'swap' or not fee.get('ultraFallback'):
                    if exc.status_code >= 500:
                        raise HTTPException(503, f'Trading engine unavailable right now: {exc.detail} Nothing was sent.')
                    raise
                engine = 'ultra'
                data, fee = await self.ultra_order(params, fee)
                fee['notes'] = [*fee.get('notes', []), 'Routed by the Ultra fallback.']
            fee_fallback = fee.get('fallback')
            order_id = str(uuid.uuid4())
            created = datetime.now(timezone.utc).isoformat()
            record = {'order_id': order_id, 'wallet': body.wallet, 'state': 'quoted', 'created_at': created,
                      'expires_at': time.time() + 45, 'input_mint': body.input_mint, 'output_mint': body.output_mint,
                      'quote': data, 'simulated': False, 'engine': engine,
                      'fee_bps': int(fee.get('bps') or 0), 'in_usd': _usd_value(data)}
            await self.db.swap_orders.insert_one(record)
            return {'order_id': order_id, 'created_at': created, 'expires_at': record['expires_at'],
                    # Echoed so the UI can refuse to show or sign an order that no longer matches the picked coins.
                    'input_mint': body.input_mint, 'output_mint': body.output_mint, 'amount': body.amount,
                    'input_metadata': meta_in, 'output_metadata': meta_out, 'quote': data,
                    'engine': engine,
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
                raise HTTPException(400, f'{explain_sim_error(value["err"])} Nothing was sent.')
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
            if order.get('engine') == 'swap':
                try:
                    await self.rpc('sendTransaction', [body.signed_transaction, {'encoding': 'base64', 'skipPreflight': True, 'maxRetries': 0}])
                except HTTPException:
                    pass  # the rebroadcast loop keeps trying; status is checked below
                asyncio.create_task(self.broadcast(body.signed_transaction, signature, order['quote'].get('lastValidBlockHeight')))
                await asyncio.sleep(1.5)
                return await check_status(body.order_id)
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
                    moved = await self.db.swap_orders.update_one({'order_id': order_id, 'state': {'$nin': ['confirmed', 'failed']}}, {'$set': {'state': state}})
                    if state == 'confirmed' and getattr(moved, 'modified_count', 0):
                        asyncio.create_task(self.trade_landed(order))
                except HTTPException:
                    pass
            return {'state': state, 'signature': signature, 'order_id': order_id,
                    'fee_back': 'Eligibility not activated; no distribution has been created.'}

        @router.get('/internal/earnings')
        async def earnings(request: Request):
            # Internal only: the Command Center reads this through the reputation service (admin-signed).
            key = (Path(__file__).parent / 'data' / 'internal.key').read_text().strip()
            if request.headers.get('x-feeless-internal') != key:
                raise HTTPException(403, 'Internal only.')
            since = datetime.fromtimestamp(time.time() - 7 * 86400, timezone.utc).isoformat()
            orders = await self.db.swap_orders.find({'state': 'confirmed', 'created_at': {'$gte': since}},
                {'_id': 0, 'created_at': 1, 'in_usd': 1, 'fee_bps': 1, 'input_mint': 1, 'output_mint': 1}).to_list(50000)
            return summarize_orders(orders)

        @router.get('/points/{wallet}')
        async def points(wallet: str):
            """FEE points: earned from platform fees actually paid on confirmed trades. Redemption rules are
            published before any payout; points are a record, not a promise of value."""
            valid_key(wallet)
            orders = await self.db.swap_orders.find({'wallet': wallet, 'state': 'confirmed'},
                {'_id': 0, 'in_usd': 1, 'fee_bps': 1}).to_list(20000)
            fees = sum((o.get('in_usd') or 0) * (o.get('fee_bps') or 0) / 10000 for o in orders)
            return {'wallet': wallet, 'trades': len(orders), 'volumeUsd': round(sum(o.get('in_usd') or 0 for o in orders), 2),
                    'feesUsd': round(fees, 4), 'points': int(fees * POINTS_PER_USD_FEE), 'status': 'Points only · redemption rules TBA'}

        @router.get('/history/{wallet}')
        async def history(wallet: str):
            self.require_configured()
            valid_key(wallet)
            orders = await self.db.swap_orders.find({'wallet': wallet, 'signature': {'$exists': True}},
                {'_id': 0, 'order_id': 1, 'state': 1, 'signature': 1, 'created_at': 1, 'input_mint': 1, 'output_mint': 1}).sort('created_at', -1).limit(30).to_list(30)
            return {'transactions': orders, 'eligible_fees_usd': None, 'distributions': [], 'fee_back_status': 'PLANNED'}
        return router