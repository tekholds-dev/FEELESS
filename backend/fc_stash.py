"""🧠 Slice 10 · the stash panel's one route: growth, hit rate and $ saved per category, and the last runs' hits vs browsed.
Counts, categories and freshness only — no page, address, title, tag or number from a page ever leaves here (stash_brain.stats).
Same pattern as the other fc_ modules: service names are looked up on feecat_service when it runs (as rs.<name>)."""
from fastapi import APIRouter

router = APIRouter()


def _rs():
    import feecat_service
    return feecat_service


@router.get('/api/cats/proofs/stash-brain')
async def stash_brain_panel():
    rs = _rs()
    return await rs.asyncio.to_thread(rs._sbrain.stats, rs._sbrain.root_of(rs.DATA_DIR))
