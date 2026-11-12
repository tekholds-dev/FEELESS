from fastapi import FastAPI, APIRouter, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timezone, timedelta


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
load_dotenv(ROOT_DIR / 'market.env')
from market import create_market_router
import ds_pace
import http_ctx
http_ctx.install()   # ⚡ every httpx client in this process shares ONE TLS context (a new client re-read the CA bundle)
ds_pace.install(150, 30)   # 📡 this process's share of DexScreener's ~300/min per IP (reputation service takes 110)
import jup_rest
jup_rest.install()   # 📡 a Jupiter token / price lane that answers 429 rests its Retry-After — every lookup was refused, half a second apart (2026-10-13)
from intelligence import Intelligence
from trading import TradingService
from whitepaper import router as docs_router
from pump_network import network as pump_network, create_pump_router
from lifi import create_lifi_router

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()


app.middleware('http')(http_ctx.sec_headers)   # 🔒 nosniff + no-referrer on every response (SITE-9)
from starlette.middleware.gzip import GZipMiddleware as _GZip
app.add_middleware(_GZip, minimum_size=1024)   # ⚡ every list over 1KB goes compressed (a 287KB trench list was sent raw)
intelligence = Intelligence(db)
market_router = create_market_router(db, intelligence)
app.include_router(market_router)
app.include_router(intelligence.router())
trading_service = TradingService(db)
app.include_router(trading_service.router())
app.include_router(docs_router)
app.include_router(create_pump_router())
app.include_router(create_lifi_router())
api_router = APIRouter(prefix="/api")


class TokenPreview(BaseModel):
    pair: Optional[dict] = None
    provider: Optional[str] = None
    fetched_at: Optional[str] = None
    chainId: Optional[str] = None
    address: Optional[str] = None
    symbol: Optional[str] = None
    name: Optional[str] = None
    priceUsd: Optional[Any] = None
    url: Optional[str] = None
    liquidity: Optional[Any] = None
    volume: Optional[Any] = None
    mcap: Optional[Any] = None
    priceChange24h: Optional[Any] = None
    pairCreatedAt: Optional[Any] = None
    imageUrl: Optional[str] = None


class ChatMessage(BaseModel):
    id: str
    room: str
    username: str
    text: str
    tokens: Optional[List[TokenPreview]] = None
    ts: int


@api_router.get("/")
async def root():
    return {"message": "FEELESS API"}


class ChatHistory(BaseModel):
    room: str
    messages: List[ChatMessage]


@api_router.get("/chat/{room}", response_model=ChatHistory)
async def list_messages(room: str, limit: int = Query(100, ge=1, le=200)):
    cursor = db.chat_messages.find({"room": room}, {"_id": 0}).sort("ts", -1).limit(limit)
    msgs = []
    async for m in cursor:
        m.pop("_id", None)
        msgs.append(m)
    return {"room": room, "messages": list(reversed(msgs))}


# 🔒 2026-11-11: the unsigned POST /chat/{room} is gone: the site never posted here, and anyone could write a message under any name
# that then showed in the globe bubbles. Chat writes go through reputation_service (signed sessions).


@api_router.get("/chat/{room}/online")
async def online_count(room: str):
    # Best-effort: count unique users in last 5 minutes
    cutoff = int(datetime.now(timezone.utc).timestamp() * 1000) - 5 * 60 * 1000
    pipeline = [
        {"$match": {"room": room, "ts": {"$gte": cutoff}}},
        {"$group": {"_id": "$username"}},
        {"$count": "n"},
    ]
    n = 0
    async for r in db.chat_messages.aggregate(pipeline):
        n = r.get("n", 0)
    return {"room": room, "online": n}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    **__import__('guard').cors_kwargs(),   # ALLOWED_ORIGINS=https://your.domain before launch; unset = this machine + LAN only (guard.py)
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🛡 Same request guard as the reputation service (backend/guard.py): write floods get a 429 breather per IP; reads and our
# own services are never limited; nobody is blocked automatically.
import guard as _guard
_guard_state = _guard.new_state()


@app.middleware('http')
async def _guard_mw(request, call_next):
    from fastapi.responses import JSONResponse
    ip = _guard.client_ip(request.headers, request.client.host if request.client else '', os.environ.get('FEELESS_TRUST_PROXY') == '1')
    stop = _guard.check(_guard_state, ip, request.method, request.url.path)
    if stop:
        return JSONResponse({'detail': stop[1]}, status_code=stop[0])
    return await call_next(request)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def start_pump_network():
    pump_network.start()


@app.on_event("startup")
async def start_trade_confirmations():
    # Confirms submitted swaps on-chain even after the trader closed the page (positions, P&L, notifications).
    asyncio.create_task(trading_service.confirm_loop())


# Self-cleaning (2026-10-28): market_cache only ever dropped an old entry when the
# same request came round again, and alpha_events was never trimmed, so both
# grew without end (34 GB + 17 GB of data in five weeks, 21 GB on disk). The
# tape reads the newest 100 events and the cache serves minutes-old data, so
# anything past these windows is dead weight. Pruned hourly by the timestamp
# the app maintains (ISO strings, same format, so they compare in order).
CACHE_KEEP = timedelta(days=2)
EVENTS_KEEP = timedelta(days=7)

PRUNE_BATCH = 5000   # 🗄 rows per delete batch — a 35 GB cache once took one delete_many (and the Mac) hostage for half an hour


async def _prune_batched(coll, field, before):
    """Delete rows older than `before` in small batches (ids first, then delete by id) so the database never locks up; → rows deleted."""
    gone = 0
    while True:
        ids = [d["_id"] async for d in coll.find({field: {"$lt": before}}, {"_id": 1}).limit(PRUNE_BATCH)]
        if not ids:
            return gone
        gone += (await coll.delete_many({"_id": {"$in": ids}})).deleted_count
        await asyncio.sleep(0.2)   # breathe between batches


async def prune_loop():
    await asyncio.sleep(30)   # let the server answer first
    while True:
        try:
            now = datetime.now(timezone.utc)
            a = await _prune_batched(db.market_cache, "fetched_at", (now - CACHE_KEEP).isoformat())
            b = await _prune_batched(db.alpha_events, "observed_at", (now - EVENTS_KEEP).isoformat())
            if a or b:
                logging.getLogger("prune").info("pruned %s cache rows, %s tape events", a, b)
        except Exception as e:  # never let housekeeping take the server down
            logging.getLogger("prune").warning("prune failed: %s", e)
        await asyncio.sleep(3600)


async def _ensure_indexes():
    # Unindexed lookups on these growing collections stalled every market request once they reached ~100k docs.
    # 🩹 2026-10-28: built in the BACKGROUND — startup used to await them; on a 35 GB cache that took longer than the watcher's patience,
    # so every restart queued another index build (≈ 40 stacked up) and the Mac froze. The server answers first; indexes follow.
    try:
        await db.market_cache.create_index("fetched_at")
        await db.market_cache.create_index("key")
        await db.alpha_events.create_index("id")
        await db.alpha_events.create_index([("chain", 1), ("observed_at", -1)])
        await db.alpha_events.create_index([("observed_at", -1)])
        await db.market_observations.create_index("key")
        await db.chat_messages.create_index([("room", 1), ("ts", -1)])
        # Locked trade fills (entry / P&L): one row per wallet + coin + tx, read by every chart load.
        await db.wallet_fills.create_index([("wallet", 1), ("mint", 1)])
        await db.wallet_fills.create_index([("wallet", 1), ("mint", 1), ("tx", 1)], unique=True)
        await db.swap_orders.create_index("signature")
    except Exception as e:
        logging.getLogger("indexes").warning("index build failed: %s", e)


@app.on_event("startup")
async def start_housekeeping():
    asyncio.create_task(_ensure_indexes())
    asyncio.create_task(prune_loop())


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
