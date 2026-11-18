"""🧪 Slice 0 (owner 2026-11-18): the test agent + a true record. Every filer of every proof kind calls `_record_file` right before its folder
lands, so each folder says which minds REALLY ran (the call log), every source it read and how new its footprint is; `_foot_back` sends a
repeat back once before it files. Claude starts a TEST proof of any kind on Sicario's agent through the internal route below: free local
minds only (`local/…`), nothing bought, nothing bid, nothing posted; it files into that kind's own folder marked TEST, plus a Test bench row.
Same pattern as the other fc_ modules: every service name is looked up on feecat_service when it runs (as rs.<name>)."""
import feecat_service as _RSM  # noqa: E402,F401  (body models; this module is imported at the END of the service)
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class TestIn(BaseModel):   # 🧪 Slice 0's body + Slice 2's studio piece: {id: a real model from the 3D library, height (m), turn (degrees), spin}
    kind: str
    topic: str = ''
    op: str = 'start'
    model: Optional[dict] = None
RUN_MARKED = ('pow', 'pob')   # the kinds with money steps: their TEST mark rides the run itself (folder testRun / pobRead by 'test')
TEST_TTL_S = 3 * 3600   # a TEST claim no filing answered within this is dropped (it never marks a later proof)
SICARIO = 'sicarios'
LINES = {'pow': 'propose a pow', 'pop': 'file a pop', 'pob': 'file a pob', 'poc': 'file a poc'}   # 💡 a TEST PoW is always a proposal: nothing is bought
TEST_ASK = {'pos': 'A one-page tool that shows live Solana pool turnover (24h volume ÷ liquidity) from DexScreener, with a chart and a short explainer.'}


def _rs():
    import feecat_service
    return feecat_service


def _sicario(store):
    return next((c for c in (store.get('cats') or {}).values() if c.get('handle') == SICARIO and not c.get('revoked')), None)


def _test_live(cat, kind, now=None):
    """The TEST claim on this agent and kind, or None. Read by the money steps: a TEST never buys, bids or sends to the card."""
    rs = _rs(); now = now or rs.time.time()
    t = rs._TEST_ON.get(((cat or {}).get('id'), kind))
    if t and now - float(t.get('at') or 0) > TEST_TTL_S:
        rs._TEST_ON.pop((cat.get('id'), kind), None); return None
    return t


def _since(rows, f):
    """A page or post kept in one workspace files a proof per version: its calls start after the last filing from that workspace."""
    ws = f.get('ws')
    return max([float(x.get('at') or 0) for x in rows if ws and x.get('ws') == ws and x.get('id') != f.get('id')] or [0.0])


async def _studio_piece(m):
    """A real model from the 3D library, set the way the studio sets one (size in metres, turn in degrees → radians, spin). → the stage object"""
    rs = _rs(); m = m if isinstance(m, dict) else {}
    async with rs.httpx.AsyncClient(timeout=30) as h_:
        await rs._assets.ensure(h_, rs.KITS_DIR)
        a = await rs._assets.resolve(h_, rs.KITS_DIR, str(m.get('id') or ''), 'model')
    if not a:
        raise rs.HTTPException(400, 'That model is not in the 3D library.')
    turn = float(m.get('turn') or 0) * rs.math.pi / 180
    return {'id': 'test1', 'name': str(m.get('name') or a.get('name') or 'Model')[:40], 'asset': a, 'height': float(m.get('height') or 0), 'rot': [0, round(turn, 4), 0], 'scale': [1, 1, 1], 'spin': float(m.get('spin') or 0)}


def _record_file(cat, kind, f, now=None):
    """🧾 The true record on a folder being filed (proof_record.stamp), the TEST mark + its Test bench row when Claude started it.
    Never stops a filing: a record that cannot be read is said on the folder. → the folder"""
    rs = _rs(); now = now or rs.time.time(); claimed = False
    try:
        rows = [x for x in cat.get(rs._prec.KEYS[kind]) or [] if isinstance(x, dict)]
        earlier = [x for x in rows if x.get('id') != f.get('id') and not x.get('live')]
        back = rs._prec.back_due(cat.get('footBack'), kind, now)
        test = _test_live(cat, kind, now)
        if kind in RUN_MARKED:   # 💰 PoW/PoB: only the run that carries the mark is the TEST; a real proof filed meanwhile is never tagged
            test = (test or {'at': f.get('at') or now, 'by': 'Claude', 'run': None, 'lost': True}) if f.get('testRun') else None
        pair = rs._lc.minds_for(cat.get('brainsCfg'), kind)
        mark = {'by': test.get('by') or 'Claude', 'at': round(float(test['at'])), 'agent': cat.get('name'), 'free': True, 'pair': pair, 'run': test.get('run')} if test else None
        rs._prec.stamp(kind, f, rs._calls_of(cat.get('id'), 6000), pair, earlier, _since(rows, f), back, mark, now)
        if back:
            (cat.get('footBack') or {}).pop(kind, None)
        if test:
            rs._TEST_ON.pop((cat.get('id'), kind), None); claimed = True
            row = rs._tbench.file_run(rs.DATA_DIR, cat.get('id'), **rs._prec.test_row(kind, f, test.get('at')), by='Claude',
                                      files={'record.json': rs.json.dumps({k: v for k, v in f.items() if k not in ('_page',)}, indent=1, default=str)[:300_000]})
            f['test']['bench'] = row['id']
    except Exception as e:   # noqa: BLE001: the proof still files; its record says it could not be read
        print(f'[record] {kind}: {type(e).__name__}: {str(e)[:120]}')
        f['recordError'] = f'{type(e).__name__}'
        if not claimed and (kind not in RUN_MARKED or f.get('testRun')):   # a record that broke never leaves its claim on for the next real filing
            rs._TEST_ON.pop((cat.get('id'), kind), None)
    return f


def _foot_back(cat, kind, draft, now=None):
    """👣 The footprint gate, before a proof files: mostly the same sources, topic and angle as a past filing of its kind on this agent →
    sent back ONCE (True: do not file, read again). The retry always files, with its send-back on the record."""
    rs = _rs(); now = now or rs.time.time()
    if rs._prec.back_due(cat.get('footBack'), kind, now):
        return False
    earlier = [x for x in cat.get(rs._prec.KEYS[kind]) or [] if isinstance(x, dict) and not x.get('live')]
    g = rs._prec.gate(kind, draft, earlier)
    if not g['repeat']:
        return False
    cat.setdefault('footBack', {})[kind] = {'at': round(now), 'nearest': g['nearest'], 'avoid': g['avoid'], 'like': g['like']}
    code = rs._prec.CODE.get(kind, kind)
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"👣 {code} sent back before filing: it read mostly what {code} #{g['nearest']} read"
                   + (f" ({', '.join(g['shared'][:3])})" if g['shared'] else '') + ('. It reads other pools now, then it files.' if kind == 'poe' else '. Its minds read new sources now, then it files.'), 'at': now}])[-200:]
    return True


def _test_view(cat):
    """The last TEST proof of each kind on this agent + any claim still running."""
    rs = _rs(); out = {}
    for kind, key in rs._prec.KEYS.items():
        last = next((f for f in reversed(cat.get(key) or []) if isinstance(f, dict) and f.get('test')), None)
        live = _test_live(cat, kind)
        out[kind] = {'running': bool(live), 'since': (live or {}).get('at'),
                     'last': {k: last.get(k) for k in ('id', 'n', 'at', 'topic', 'sym', 'test', 'ran', 'mindsCheck', 'read', 'foot', 'status', 'noTrade', 'why', 'ws', 'studio')} | {'checks': last.get('proofChecks') or (last.get('checks') if isinstance(last.get('checks'), list) else [])} if last else None}
    return out


@router.get('/api/cats/internal/test-proof')
async def test_proof_state(request: Request):
    """🧪 Internal key only: Sicario's TEST proofs, per kind (the last one filed and any still running)."""
    rs = _rs()
    rs._internal(request)
    cat = _sicario(rs._load())
    if not cat:
        raise rs.HTTPException(404, "No Sicario's agent.")
    return {'agent': cat.get('name'), 'tests': _test_view(cat)}


@router.post('/api/cats/internal/test-proof')
async def test_proof_start(p: TestIn, request: Request):
    """🧪 Internal key only (Claude's tests): one TEST proof of `kind` on Sicario's agent, through the SAME door the owner's chat takes.
    Free local minds only; a TEST PoW is a proposal (nothing bought, never sent to the card seat), a TEST PoB never bids, nothing posts.
    op 'stop' ends an open paper PoP so it files now."""
    rs = _rs()
    rs._internal(request)
    kind = str(p.kind or '').lower()
    if kind not in rs._prec.KEYS:
        raise rs.HTTPException(400, 'Kind: pow, pop, pob, poc, pos or poe.')
    store = rs._load(); cat = _sicario(store)
    if not cat:
        raise rs.HTTPException(404, "No Sicario's agent.")
    pair = rs._lc.minds_for(cat.get('brainsCfg'), kind)
    if not pair or any(not str(m).startswith('local/') for m in pair):   # §1: a TEST runs on the owner's own LM Studio only, $0
        raise rs.HTTPException(409, f"Sicario's {kind} pair is {pair or 'not set'}: a TEST runs only on free local minds (local/…).")
    cid = cat['id']; now = rs.time.time()
    if p.op == 'stop':
        if kind != 'pop':
            raise rs.HTTPException(400, 'Only an open paper PoP is stopped this way.')
        return await rs._cat_work(cid, rs.WorkPayload(op='ask', text='stop pop', session=rs._AUTO_TOKEN, auto=True))
    if _test_live(cat, kind, now):
        raise rs.HTTPException(409, f'A TEST {kind} is still running on {cat.get("name")}.')
    rs._TEST_ON[(cid, kind)] = {'at': now, 'by': 'Claude', 'run': rs.uuid.uuid4().hex[:10], 'topic': str(p.topic or '')[:120]}
    try:
        if kind == 'poe':   # 📊 PoEco: one sealed market call on live pools, no model
            out = await rs._cat_work(cid, rs.WorkPayload(op='eco_call', session=rs._AUTO_TOKEN, auto=True))
        elif kind == 'pos':   # 💻 a new PoStatic folder, its plan approved by the test (no owner tap to wait for), built by its own pair
            row_ = rs._feat.new_folder(cat, 'build', f"TEST {rs.time.strftime('%m-%d %H%M', rs.time.gmtime(now))}", now)
            rs._ws_save(cid, {**rs._feat.new_doc(row_), 'cfg': {'suggest': False}, 'test': True}); rs.keep_owned(cat); rs._save(store)
            if p.model:   # 🪦 Slice 2: a piece made in the 3D studio goes into the folder through the studio's own step, then the build runs
                await rs._cat_work(cid, rs.WorkPayload(op='play3d_model_to', tools={'to': row_['id'], 'obj': await _studio_piece(p.model)}, session=rs._AUTO_TOKEN, auto=True))
            out = await rs._cat_work(cid, rs.WorkPayload(op='ws_build', job=row_['id'], text=str(p.topic or TEST_ASK['pos'])[:2000], session=rs._AUTO_TOKEN, auto=True))
            out = {'ws': row_['id']}
        else:
            line = LINES[kind] + (f' {p.topic}' if p.topic and kind in ('pob', 'poc') else '')
            out = await rs._cat_work(cid, rs.WorkPayload(op='ask', text=line, session=rs._AUTO_TOKEN, auto=True))
    except Exception:
        rs._TEST_ON.pop((cid, kind), None)
        raise
    said = [c.get('text') for c in (out or {}).get('chat') or []][-1:] if isinstance(out, dict) else []
    return {'ok': True, 'kind': kind, 'pair': pair, 'run': rs._TEST_ON.get((cid, kind), {}).get('run'), 'said': said, **({'ws': out.get('ws')} if isinstance(out, dict) and out.get('ws') else {})}
