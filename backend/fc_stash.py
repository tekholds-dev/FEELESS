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


@router.get('/api/cats/proofs/comp-ahead')
async def comp_ahead_panel():
    """📡 Slice 11 · COMP stays ahead: its passes (counts), the games it holds a reference for, the atlas (atoms by kind, fresh / stale,
    from 2+ sources) and the trust table. No page, fact or address leaves here (comp_ahead.panel, atlas.stats)."""
    rs = _rs()
    return await rs.asyncio.to_thread(rs._cahead.panel, rs.DATA_DIR)
