import asyncio
import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    load_dotenv(Path('/app/backend/.env'))
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    if not mongo_url or not db_name:
        print('Missing MONGO_URL/DB_NAME; cleanup skipped')
        return

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    tags = [
        'E2E_TEST_234748',
        'E2E_TEST_234527',
    ]

    deleted_messages = 0
    deleted_events = 0

    for tag in tags:
        msgs = await db.chat_messages.find({'text': {'$regex': tag}}, {'_id': 0, 'id': 1}).to_list(None)
        if msgs:
            ids = [m['id'] for m in msgs if m.get('id')]
            if ids:
                event_ids = [hashlib.sha256(mid.encode()).hexdigest()[:24] for mid in ids]
                res_e = await db.alpha_events.delete_many({'id': {'$in': event_ids}, 'kind': 'CHAT_CA_MENTION'})
                deleted_events += res_e.deleted_count
            res_m = await db.chat_messages.delete_many({'text': {'$regex': tag}})
            deleted_messages += res_m.deleted_count

    print({'deleted_messages': deleted_messages, 'deleted_events': deleted_events})
    client.close()


if __name__ == '__main__':
    asyncio.run(main())
