"""FEELESS Pump network: one shared PumpPortal connection for the whole app.

Free stream (no key): every pump.fun launch and every migration, pushed in real time.
Paid stream (PUMPPORTAL_API_KEY, funded PumpPortal wallet): live trades for the coins people
are actually viewing. PumpPortal bills per message, so trade subscriptions are limited to
recently viewed coins and hard-capped per day (PUMPPORTAL_DAILY_MESSAGE_CAP).
The key never leaves the server.
"""
import asyncio
import json
import os
import time
from collections import deque

import httpx
import websockets
from fastapi import APIRouter, HTTPException

WS_URL = 'wss://pumpportal.fun/api/data'
PUMP_SUPPLY = 1_000_000_000          # every pump.fun coin mints exactly 1B tokens
CURVE_START_VSOL = 30.0              # virtual SOL in a fresh bonding curve
CURVE_GRADUATE_SOL = 85.0            # approx. real SOL raised when a curve completes
MAX_WATCHED = 12                     # simultaneous trade subscriptions
WATCH_TTL = 90                       # seconds a coin stays subscribed after its last viewer poll
BASE58 = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')


def _valid_mint(value):
    return isinstance(value, str) and 32 <= len(value) <= 44 and set(value) <= BASE58


def _curve_progress(v_sol):
    if not isinstance(v_sol, (int, float)):
        return None
    return round(max(0.0, min(100.0, (v_sol - CURVE_START_VSOL) / CURVE_GRADUATE_SOL * 100)), 1)


class PumpNetwork:
    def __init__(self):
        self.launches = deque(maxlen=200)
        self.migrations = deque(maxlen=60)
        self.by_curve = {}                  # bondingCurveKey -> launch (for pair lookups)
        self.by_mint = {}
        self.launch_minutes = deque(maxlen=60)   # [minute, count]
        self.trades = {}                    # mint -> deque of trades
        self.watch = {}                     # mint -> last viewer poll (monotonic)
        self.subscribed = set()
        self.free_status = 'connecting'
        self.paid_status = 'no-key'
        self.paid_note = ''
        self.sol_usd = None
        self._sol_at = 0
        self.msg_day = time.strftime('%Y-%m-%d')
        self.msg_count = 0
        self._paid_ws = None
        self._tasks = []

    # ---- lifecycle -----------------------------------------------------------------------
    def start(self):
        if self._tasks:
            return
        self._tasks = [asyncio.create_task(self._free_loop())]
        if self.key:
            self.paid_status = 'connecting'
            self._tasks.append(asyncio.create_task(self._paid_loop()))

    @property
    def key(self):
        return (os.environ.get('PUMPPORTAL_API_KEY') or '').strip()

    @property
    def cap(self):
        try:
            return max(0, int(os.environ.get('PUMPPORTAL_DAILY_MESSAGE_CAP', '20000')))
        except ValueError:
            return 20000

    # ---- free stream: launches + migrations ----------------------------------------------
    async def _free_loop(self):
        backoff = 2
        while True:
            try:
                async with websockets.connect(WS_URL, ping_interval=20, close_timeout=5) as ws:
                    await ws.send(json.dumps({'method': 'subscribeNewToken'}))
                    await ws.send(json.dumps({'method': 'subscribeMigration'}))
                    self.free_status = 'live'
                    backoff = 2
                    async for raw in ws:
                        self._on_free(json.loads(raw))
            except Exception as exc:  # network blips: reconnect with backoff
                self.free_status = 'reconnecting'
                print('pump network free stream', type(exc).__name__, exc)
            await asyncio.sleep(backoff)
            backoff = min(60, backoff * 2)

    def _on_free(self, d):
        kind = d.get('txType')
        if kind == 'create' and _valid_mint(d.get('mint')):
            launch = {
                'mint': d['mint'], 'name': str(d.get('name') or '')[:60], 'symbol': str(d.get('symbol') or '')[:20],
                'curve': d.get('bondingCurveKey'), 'creator': d.get('traderPublicKey'), 'uri': d.get('uri'),
                'devBuySol': round(float(d.get('solAmount') or 0), 4), 'marketCapSol': d.get('marketCapSol'),
                'curveProgress': _curve_progress(d.get('vSolInBondingCurve')), 'mayhem': bool(d.get('is_mayhem_mode')),
                'signature': d.get('signature'), 'at': time.time() * 1000,
            }
            self.launches.appendleft(launch)
            self.by_mint[launch['mint']] = launch
            if launch['curve']:
                self.by_curve[launch['curve']] = launch
            if len(self.by_mint) > 5000:   # bounded memory: keep the most recent launches only
                keep = {l['mint'] for l in self.launches}
                self.by_mint = {m: l for m, l in self.by_mint.items() if m in keep}
                self.by_curve = {l['curve']: l for l in self.by_mint.values() if l.get('curve')}
            minute = int(time.time() // 60)
            if self.launch_minutes and self.launch_minutes[-1][0] == minute:
                self.launch_minutes[-1][1] += 1
            else:
                self.launch_minutes.append([minute, 1])
        elif kind == 'migrate' and _valid_mint(d.get('mint')):
            known = self.by_mint.get(d['mint']) or {}
            self.migrations.appendleft({'mint': d['mint'], 'pool': d.get('pool'), 'symbol': known.get('symbol'),
                                        'name': known.get('name'), 'signature': d.get('signature'), 'at': time.time() * 1000})

    # ---- paid stream: trades for viewed coins --------------------------------------------
    def _count(self):
        day = time.strftime('%Y-%m-%d')
        if day != self.msg_day:
            self.msg_day, self.msg_count = day, 0
        self.msg_count += 1

    def _capped(self):
        if time.strftime('%Y-%m-%d') != self.msg_day:
            return False
        return self.msg_count >= self.cap

    async def _paid_loop(self):
        backoff = 5
        while True:
            try:
                async with websockets.connect(f'{WS_URL}?api-key={self.key}', ping_interval=20, close_timeout=5) as ws:
                    self._paid_ws, self.subscribed = ws, set()
                    self.paid_status, self.paid_note = 'live', ''
                    sync = asyncio.create_task(self._sync_subscriptions(ws))
                    try:
                        async for raw in ws:
                            self._on_paid(json.loads(raw))
                            if self.paid_status in ('invalid-key', 'unfunded'):
                                break  # don't hold a useless connection; retry slowly below
                    finally:
                        sync.cancel()
            except Exception as exc:
                if self.paid_status not in ('invalid-key', 'unfunded'):
                    self.paid_status = 'reconnecting'
                print('pump network paid stream', type(exc).__name__, exc)
            self._paid_ws = None
            # A bad key will not fix itself; an unfunded wallet is re-checked every 2 minutes.
            await asyncio.sleep({'invalid-key': 600, 'unfunded': 120}.get(self.paid_status, backoff))
            backoff = min(120, backoff * 2)

    def _on_paid(self, d):
        if d.get('errors') or d.get('message'):
            text = str(d.get('errors') or d.get('message'))
            if 'Invalid API key' in text:
                self.paid_status, self.paid_note = 'invalid-key', 'PumpPortal rejected the API key.'
            elif 'funded' in text:
                self.paid_status, self.paid_note = 'unfunded', 'PumpPortal wallet needs at least 0.02 SOL for trade data.'
            return
        if d.get('txType') not in ('buy', 'sell') or not _valid_mint(d.get('mint')):
            return
        self._count()
        tokens = float(d.get('tokenAmount') or 0)
        sol = float(d.get('solAmount') or 0)
        trade = {'side': d['txType'], 'sol': round(sol, 4), 'tokens': tokens, 'trader': d.get('traderPublicKey'),
                 'marketCapSol': d.get('marketCapSol'), 'curveProgress': _curve_progress(d.get('vSolInBondingCurve')),
                 'signature': d.get('signature'), 'pool': d.get('pool'), 'at': time.time() * 1000}
        self.trades.setdefault(d['mint'], deque(maxlen=120)).appendleft(trade)

    async def _sync_subscriptions(self, ws):
        while True:
            now = time.monotonic()
            for mint, seen in list(self.watch.items()):
                if now - seen > WATCH_TTL:
                    self.watch.pop(mint, None)
            wanted = set() if self._capped() else set(sorted(self.watch, key=self.watch.get, reverse=True)[:MAX_WATCHED])
            if self._capped():
                self.paid_status, self.paid_note = 'capped', f'Daily trade-data cap reached ({self.cap:,} messages).'
            drop, add = self.subscribed - wanted, wanted - self.subscribed
            if drop:
                await ws.send(json.dumps({'method': 'unsubscribeTokenTrade', 'keys': sorted(drop)}))
            if add:
                await ws.send(json.dumps({'method': 'subscribeTokenTrade', 'keys': sorted(add)}))
            self.subscribed = wanted
            await asyncio.sleep(2)

    # ---- helpers for API + market fallbacks -------------------------------------------------
    async def sol_price(self):
        if self.sol_usd and time.time() - self._sol_at < 30:
            return self.sol_usd
        sol = 'So11111111111111111111111111111111111111112'
        key = (os.environ.get('JUPITER_API_KEY') or '').strip()
        # Keyed Jupiter first (the free lite endpoint is shared and often rate-limited).
        sources = ([('https://api.jup.ag/price/v3', {'x-api-key': key})] if key else []) + [('https://lite-api.jup.ag/price/v3', {})]
        async with httpx.AsyncClient(timeout=6) as http:
            for url, headers in sources:
                try:
                    r = await http.get(url, params={'ids': sol}, headers=headers)
                    self.sol_usd, self._sol_at = float(r.json()[sol]['usdPrice']), time.time()
                    break
                except Exception:
                    continue
        return self.sol_usd

    def pair_for(self, address, sol_usd):
        """Market-contract pair for a launch we saw on the stream (DexScreener may lag new curves)."""
        launch = self.by_curve.get(address) or self.by_mint.get(address)
        if not launch:
            return None
        trades = self.trades.get(launch['mint'])
        mc_sol = (trades[0]['marketCapSol'] if trades else None) or launch.get('marketCapSol')
        mc_usd = round(mc_sol * sol_usd, 2) if mc_sol and sol_usd else None
        return {
            'chainId': 'solana', 'network': 'solana', 'pairAddress': launch['curve'] or launch['mint'],
            'dexId': 'pump.fun', 'launchpadId': 'pump', 'url': f"https://pump.fun/coin/{launch['mint']}",
            'baseToken': {'address': launch['mint'], 'name': launch['name'], 'symbol': launch['symbol']},
            'quoteToken': {'address': 'So11111111111111111111111111111111111111112', 'name': 'Wrapped SOL', 'symbol': 'SOL'},
            # Exact for pump.fun: fixed 1B supply, so price = market cap / supply.
            'priceUsd': str(mc_usd / PUMP_SUPPLY) if mc_usd else None, 'marketCap': mc_usd, 'fdv': mc_usd,
            'pairCreatedAt': int(launch['at']), 'marketStage': 'new', 'source': 'PumpPortal stream',
        }

    def flow(self, mint, sol_usd):
        trades = list(self.trades.get(mint) or [])
        cutoff = time.time() * 1000 - 5 * 60 * 1000
        recent = [t for t in trades if t['at'] >= cutoff]
        buys = [t for t in recent if t['side'] == 'buy']
        sells = [t for t in recent if t['side'] == 'sell']
        buy_sol, sell_sol = sum(t['sol'] for t in buys), sum(t['sol'] for t in sells)
        launch = self.by_mint.get(mint) or {}
        last = trades[0] if trades else None
        mc_sol = (last or {}).get('marketCapSol') or launch.get('marketCapSol')
        return {
            'mint': mint, 'status': self.paid_status, 'note': self.paid_note, 'watching': mint in self.subscribed,
            'solUsd': sol_usd, 'trades': [{**t, 'usd': round(t['sol'] * sol_usd, 2) if sol_usd else None} for t in trades[:40]],
            'window': '5m', 'buys': len(buys), 'sells': len(sells), 'buySol': round(buy_sol, 3), 'sellSol': round(sell_sol, 3),
            'netSol': round(buy_sol - sell_sol, 3), 'traders': len({t['trader'] for t in recent if t.get('trader')}),
            'whales': sum(1 for t in recent if t['sol'] >= 2),
            'marketCapUsd': round(mc_sol * sol_usd, 2) if mc_sol and sol_usd else None,
            'curveProgress': (last or {}).get('curveProgress', launch.get('curveProgress')),
            'devBuySol': launch.get('devBuySol'), 'launchedAt': launch.get('at'),
        }


network = PumpNetwork()


def create_pump_router():
    router = APIRouter(prefix='/api/pump', tags=['pump-network'])

    @router.get('/pulse')
    async def pulse(limit: int = 40):
        sol_usd = await network.sol_price()
        minute = int(time.time() // 60)
        counts = dict((m, c) for m, c in network.launch_minutes)
        series = [counts.get(m, 0) for m in range(minute - 14, minute + 1)]
        launches = [{**l, 'marketCapUsd': round(l['marketCapSol'] * sol_usd, 2) if l.get('marketCapSol') and sol_usd else None}
                    for l in list(network.launches)[:max(1, min(100, limit))]]
        return {'provider': 'PumpPortal', 'status': network.free_status, 'tradeStream': network.paid_status,
                'tradeNote': network.paid_note, 'solUsd': sol_usd, 'launches': launches,
                'migrations': list(network.migrations)[:15], 'launchesPerMinute': series,
                'lastMinute': series[-2] if len(series) > 1 else 0}

    @router.get('/coin/{mint}/flow')
    async def flow(mint: str):
        if not _valid_mint(mint):
            raise HTTPException(400, 'Invalid Solana mint.')
        if network.paid_status not in ('no-key', 'invalid-key', 'unfunded'):
            network.watch[mint] = time.monotonic()   # viewer heartbeat keeps the trade subscription alive
        return network.flow(mint, await network.sol_price())

    return router
