"""🔒 Kalshi v2 order check that CANNOT trade (owner runs it; Claude never does). It sends ONE order for a market that does not exist
(FEELESS-NO-SUCH-MARKET), signed with the owner's saved key, in exactly the body a real bid uses. Kalshi must refuse it, and HOW it refuses
proves the path:
  404 / 400 'market not found'-style  → endpoint, signature and body shape are right: a real bid will reach Kalshi.
  410 deprecated_v1_order_endpoint    → still the old endpoint (should not happen after 7ae743c4).
  401 / 403                            → the key or signature is wrong.
  400 naming a field                   → the body shape is wrong (send Claude the line).
Run from the repo root:  .venv/bin/python scripts/kalshi-v2-check.py
"""
import asyncio
import json
import sys

sys.path[:0] = ['backend', '.']
import httpx  # noqa: E402
import cat_keys as ck  # noqa: E402
import kalshi_bid as kb  # noqa: E402

DATA = 'backend/data'
CAT = 'e23464a6114e492c8ac6fee02a19c1d6'
FAKE = 'FEELESS-NO-SUCH-MARKET'


async def main():
    cat = json.load(open(f'{DATA}/feecats.json'))['cats'][CAT]
    kid, pem = kb.split_key(ck.key_for(cat, 'kalshi', data_dir=DATA) or '')
    if not kid:
        print('No Kalshi key saved on this agent.'); return
    body = kb.order({'ticker': FAKE, 'side': 'yes'}, 1, 0.01, 'feeless-v2-check')
    assert body['ticker'] == FAKE   # never a real market
    async with httpx.AsyncClient(timeout=10) as h:
        r = await h.post(f'{kb.BASE}{kb.ORDER_PATH}', json=body, headers=kb.headers(kid, pem, 'POST', kb.ORDER_PATH))
    print('Kalshi answered', r.status_code, r.text[:300])
    print('✅ path, key and body are right: a real bid will reach Kalshi.' if r.status_code in (400, 404) and 'deprecated' not in r.text and 'field' not in r.text.lower()
          else '⚠ send this line to Claude before bidding.')

asyncio.run(main())
