from fastapi import FastAPI, APIRouter, HTTPException
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

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")


class TokenPreview(BaseModel):
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


@api_router.get("/chat/{room}")
async def list_messages(room: str, limit: int = 100):
    cursor = db.chat_messages.find({"room": room}).sort("ts", 1).limit(limit)
    msgs = []
    async for m in cursor:
        m.pop("_id", None)
        msgs.append(m)
    return {"room": room, "messages": msgs}


@api_router.post("/chat/{room}")
async def post_message(room: str, msg: ChatMessageCreate):
    if not room or len(room) > 50:
        raise HTTPException(status_code=400, detail="invalid room")
    doc = {
        "id": str(uuid.uuid4()),
        "room": room,
        "username": msg.username[:40],
        "text": msg.text[:1000],
        "tokens": [t.dict() for t in msg.tokens] if msg.tokens else None,
        "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
    }
    await db.chat_messages.insert_one(doc)
    doc.pop("_id", None)
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
