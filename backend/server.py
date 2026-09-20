from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
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
from intelligence import Intelligence
from trading import TradingService
from whitepaper import router as docs_router
import re

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
intelligence = Intelligence(db)
market_router = create_market_router(db, intelligence)
app.include_router(market_router)
app.include_router(intelligence.router())
app.include_router(TradingService(db).router())
app.include_router(docs_router)
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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
