"""🧪 MODEL LAB routes (owner only): the live dataset for FEELESS's own model, the human review queue, and the clean export.
The logic is `model_lab` (pure); this file only reads the stash, the model-call log and the owner's grades, and saves a grade.
Nothing here trains, spends or sends anything: the export comes back to the owner's own browser as a file."""
import json
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

import model_lab as _ml

router = APIRouter()
CALLS_MAX = 20000   # the model-call log is read from its newest end, at most this many lines


def _rs():
    import reputation_service
    return reputation_service


def _paths(rs):
    return rs.DATA_DIR / 'stash', rs.DATA_DIR / 'mind_calls.jsonl', rs.DATA_DIR / 'model_lab_grades.json'


def _calls(path):
    try:
        lines = path.read_text(errors='ignore').splitlines()[-CALLS_MAX:]
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def _view(rs):
    stash, calls, grades_p = _paths(rs)
    items = rs._stash.catalog(stash); grades = rs._json_load(grades_p, {})
    return {**_ml.summary(items, _calls(calls), grades), 'queue': _ml.queue(items, grades), 'at': round(time.time())}


@router.get('/api/reputation/admin/model-lab')
async def model_lab_view(request: Request):
    """🧪 The dataset as it stands, the rented minds' real record and the next proofs waiting for the owner's grade."""
    rs = _rs()
    rs._require_owner(request)
    return await rs.asyncio.to_thread(_view, rs)


class Grade(BaseModel):
    key: str
    verdict: str
    note: str = ''


@router.post('/api/reputation/admin/model-lab/grade')
async def model_lab_grade(request: Request, g: Grade):
    """👍 / 👎 / skip on one open proof: the human label a model learns from where no market settled it."""
    rs = _rs()
    rs._require_owner(request)
    _, _, grades_p = _paths(rs)
    try:
        nxt = _ml.grade(rs._json_load(grades_p, {}), g.key, g.verdict, g.note, time.time())
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    await rs.asyncio.to_thread(rs._json_save, grades_p, nxt)
    return await rs.asyncio.to_thread(_view, rs)


def _export(rs):
    stash, _, grades_p = _paths(rs)
    items = rs._stash.catalog(stash); grades = rs._json_load(grades_p, {})
    return [json.loads(x) for x in _ml.export_lines(items, lambda k: rs._stash.read(stash, k), grades)]


@router.get('/api/reputation/admin/model-lab/export')
async def model_lab_export(request: Request):
    """⬇ Every clean training row (scrubbed of wallets, addresses, emails, phones and keys). The page saves it as a .jsonl file."""
    rs = _rs()
    rs._require_owner(request)
    rows = await rs.asyncio.to_thread(_export, rs)
    return {'rows': rows, 'count': len(rows), 'at': round(time.time())}
