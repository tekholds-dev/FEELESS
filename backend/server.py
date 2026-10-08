from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
load_dotenv(ROOT_DIR / 'market.env')
from market import create_market_router
import ds_pace
ds_pace.install(150, 30)   # 📡 this process's share of DexScreener's ~300/min per IP (reputation service takes 110)
from intelligence import Intelligence
from trading import TradingService
from whitepaper import router as docs_router
from pump_network import network as pump_network, create_pump_router
from lifi import create_lifi_router
import re

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
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


class ChatMessageCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=40)
    text: str = Field(..., min_length=1, max_length=1000)
    tokens: Optional[List[TokenPreview]] = None


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


@api_router.post("/chat/{room}", response_model=ChatMessage)
async def post_message(room: str, msg: ChatMessageCreate):
    if not room or len(room) > 50:
        raise HTTPException(status_code=400, detail="invalid room")
    if not msg.text.strip() or not msg.username.strip():
        raise HTTPException(status_code=400, detail="Message and username cannot be blank")
    token_previews = None
    address = re.search(r'\b0x[a-fA-F0-9]{40}\b|\b[1-9A-HJ-NP-Za-km-z]{32,44}\b', msg.text)
    if address:
        try:
            pairs, meta = await market_router.resolve_ca(address.group(0))
            if pairs:
                p = pairs[0]
                token_previews = [{'pair': p, 'provider': meta['provider'], 'fetched_at': meta['fetched_at'],
                                   'address': p['baseToken']['address'], 'chainId': p['chainId'],
                                   'symbol': p['baseToken'].get('symbol'), 'name': p['baseToken'].get('name')}]
        except HTTPException:
            pass
    doc = {
        "id": str(uuid.uuid4()),
        "room": room,
        "username": msg.username[:40],
        "text": msg.text.strip()[:1000],
        "tokens": token_previews,
        "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
    }
    await db.chat_messages.insert_one(doc)
    doc.pop("_id", None)
    if token_previews:
        await intelligence.event('CHAT_CA_MENTION', f'{token_previews[0]["symbol"]} · mentioned in Trenches',
            f'Exact contract resolved from a real message in {room}.', token_previews[0]['pair'],
            'DexScreener + public chat', datetime.now(timezone.utc).isoformat(),
            context=re.sub(r'-(general|alpha|launches|trading|whales|new-pools)$', '', room), unique=doc['id'])
    return doc


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
    allow_origins=[o.strip() for o in (os.environ.get('ALLOWED_ORIGINS') or '*').split(',') if o.strip()],   # set ALLOWED_ORIGINS=https://your.domain before launch
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


@app.on_event("startup")
async def ensure_indexes():
    # Unindexed lookups on these growing collections stalled every market request once they reached ~100k docs.
    await db.alpha_events.create_index("id")
    await db.alpha_events.create_index([("chain", 1), ("observed_at", -1)])
    await db.alpha_events.create_index([("observed_at", -1)])
    await db.market_observations.create_index("key")
    await db.market_cache.create_index("key")
    await db.chat_messages.create_index([("room", 1), ("ts", -1)])
    # Locked trade fills (entry / P&L): one row per wallet + coin + tx, read by every chart load.
    await db.wallet_fills.create_index([("wallet", 1), ("mint", 1)])
    await db.wallet_fills.create_index([("wallet", 1), ("mint", 1), ("tx", 1)], unique=True)
    await db.swap_orders.create_index("signature")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
