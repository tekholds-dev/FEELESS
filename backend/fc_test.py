"""🧪 Slice 0 (owner 2026-11-18): the test agent + a true record. Every filer of every proof kind calls `_record_file` right before its folder
lands, so each folder says which minds REALLY ran (the call log), every source it read and how new its footprint is; `_foot_back` sends a
repeat back once before it files. Claude starts a TEST proof of any kind on Sicario's agent through the internal route below: free local
minds only (`local/…`), nothing bought, nothing bid, nothing posted; it files into that kind's own folder marked TEST, plus a Test bench row.
Same pattern as the other fc_ modules: every service name is looked up on feecat_service when it runs (as rs.<name>)."""
import feecat_service as _RSM  # noqa: E402,F401  (body models; this module is imported at the END of the service)
import json
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

import ps_inspect as _insp   # 🔍 Slice 9: a TEST fix clicks its elements through the page's own inspect tool

router = APIRouter()


class TestIn(BaseModel):   # 🧪 Slice 0's body + Slice 2's studio piece: {id: a real model from the 3D library, height (m), turn (degrees), spin}
    kind: str
    topic: str = ''
    op: str = 'start'
    model: Optional[dict] = None
    ws: str = ''   # 🧪 Slice 3: PoStatic only, a TEST folder to change (a new version of it, to prove it keeps every part that worked)
    agent: str = ''   # 🧪 owner 2026-11-19: '' / 'sicarios' = Sicario's (free local minds) · 'happy' = Happy's (its paid minds, proposals and paper only, TEST_BUDGET_USD in all)
    door: str = ''   # 🎲 Slice 13: PoB only, 'dash' = through the PoB dashboard's door (op pob: a tap on What to file next / his own slip), not the chat line
    slip: Optional[list] = None   # 🧾 Slice 13: with door 'dash', his own slip [{ticker, side, title}]: the minds check it with the same guards
    wizard: Optional[dict] = None   # 🧭 Slice 33: what the start wizard would send (direction, kits, start, research); it rides tools.wizard on the same door the owner's Go takes
    inspect: Optional[list] = None   # 🔍 Slice 9: with ws, [{click: a CSS query, note}]: each element is clicked through the page's own inspect tool on a headless browser, then fixed through the same build door
RUN_MARKED = ('pow', 'pob')   # the kinds with money steps: their TEST mark rides the run itself (folder testRun / pobRead by 'test')
TEST_TTL_S = 3 * 3600   # a TEST claim no filing answered within this is dropped (it never marks a later proof)
SICARIO = 'sicarios'
AGENTS = {'': SICARIO, 'sicarios': SICARIO, 'happy': 'happy-assistant', 'happy-assistant': 'happy-assistant'}
TEST_BUDGET_USD = 1.00      # 💸 owner 2026-11-19: TESTs on Happy's agent spend at most $1.00 of model credit, all of them together
KIND_BUDGET_USD = 0.25      # ... and at most $0.25 per proof type ("max .25-.5c per proof type … dont waste my whole $2")
BUDGET_SINCE = 1795112700   # ... counted from the owner's ruling (every model call Happy's agent made since, test or not: the safe count)
LINES = {'pow': 'propose a pow', 'pop': 'file a pop', 'pob': 'file a pob', 'poc': 'file a poc'}   # 💡 a TEST PoW is always a proposal: nothing is bought
TEST_ASK = {'pos': 'A one-page tool that shows live Solana pool turnover (24h volume ÷ liquidity) from DexScreener, with a chart and a short explainer.'}


def _rs():
    import feecat_service
    return feecat_service


def _sicario(store, agent=''):
    """The TEST agent: Sicario's by default, Happy's when asked (owner 2026-11-19). An unknown name is refused, never guessed."""
    h = AGENTS.get(str(agent or '').lower())
    if not h:
        raise _rs().HTTPException(400, 'Agent: sicarios or happy.')
    return next((c for c in (store.get('cats') or {}).values() if c.get('handle') == h and not c.get('revoked')), None)


def spent_since(rows, since=BUDGET_SINCE, kind=None):
    """$ the agent's model calls cost since the budget started (call log rows), all kinds or one kind's. Pure."""
    return round(sum(float(r.get('usd') or 0) for r in rows or [] if float(r.get('at') or 0) >= since and (kind is None or r.get('kind') == kind)), 6)


CAP_MIN_TOKENS = 400        # 💸 Slice 28 (Slice 27's #72 spent $0.54 of $0.25): a TEST call that cannot afford this much reply is refused before it is sent
UNPRICED_USD = 0.15         # ... a model with no listed price is held at its dearest past call, or this


def call_worst(row, messages, max_tokens):
    """$ the most one call can cost: its prompt (~3 bytes a token + 256) and every reply token it may write, at the listed price. Pure.
    row = the model's catalog row {inUsd, outUsd} ($ per 1M) or None (unpriced → None)."""
    if not row:
        return None
    sent = len(json.dumps(messages or [], ensure_ascii=False).encode('utf-8')) / 3 + 256
    return (sent * float(row.get('inUsd') or 0) + int(max_tokens or 0) * float(row.get('outUsd') or 0)) / 1e6


def fit_tokens(row, messages, room_usd):
    """The longest reply that still fits `room_usd` at the listed price. Pure."""
    if not row or not float(row.get('outUsd') or 0):
        return 10 ** 9
    sent = len(json.dumps(messages or [], ensure_ascii=False).encode('utf-8')) / 3 + 256
    return max(0, int((room_usd - sent * float(row.get('inUsd') or 0) / 1e6) / float(row['outUsd']) * 1e6))


def room_left(claim, rows, kind, since=BUDGET_SINCE):
    """$ this TEST may still spend: the lower of what is left of the all-TEST cap and of this kind's, less what its calls in flight hold.
    The base is read from the call log once per claim, then each finished call adds its real $ (cap_done). Mutates claim. Pure otherwise."""
    if 'base' not in claim:
        claim['base'] = min(TEST_BUDGET_USD - spent_since(rows, since), KIND_BUDGET_USD - spent_since(rows, since, kind))
        claim.setdefault('used', 0.0); claim.setdefault('held', {})
    return claim['base'] - float(claim.get('used') or 0) - sum((claim.get('held') or {}).values())


def cap_take(cat, ctx, model, messages, max_tokens, rows=None, shrink=True):
    """💸 The TEST cap, checked on EVERY paid call inside a TEST on Happy's agent (not only at the door): the call's worst case is held
    against what is left, its reply is shortened to fit, and when even a short reply would pass the cap it raises OverCap before anything
    is sent. → (hold id, max_tokens) | None when no capped TEST is running for this call."""
    rs = _rs(); cat = cat if isinstance(cat, dict) else {}; kind = (ctx or {}).get('kind')
    if not kind or cat.get('handle') == SICARIO or str(model).startswith('local/'):
        return None
    claim = _test_live(cat, kind)
    if not claim:
        return None
    rows = rows if rows is not None else rs._calls_of(cat.get('id'))
    room = room_left(claim, rows, kind)
    row = next((m for m in ((rs._MODELS.get('rows') or {}).get('models') or []) if m.get('id') == model), None)
    want = int(max_tokens or rs._lc.OUT_TOK)
    worst = call_worst(row, messages, want)
    if worst is None:   # unpriced: held at its dearest call so far
        worst = max([float(r.get('usd') or 0) for r in rows if r.get('asked') == model] or [UNPRICED_USD])
    elif worst > room and shrink:
        want = min(want, fit_tokens(row, messages, room)); worst = call_worst(row, messages, want)
    if room <= 0 or worst > room + 1e-9 or (row and want < CAP_MIN_TOKENS):
        raise rs._sg.OverCap(f"Stopped before it cost anything: the TEST cap (${TEST_BUDGET_USD:.2f} for all TESTs, ${KIND_BUDGET_USD:.2f} for {kind}). "
                             f"${max(0.0, room):.3f} is left and this call could cost ${worst:.3f}.")
    hid = rs.uuid.uuid4().hex[:8]; claim['held'][hid] = worst
    return hid, want


def cap_done(cat, ctx, hold, usd):
    """The call finished: its hold is let go and its real $ counted."""
    if not hold:
        return
    claim = _test_live(cat if isinstance(cat, dict) else {}, (ctx or {}).get('kind'))
    if claim:
        (claim.get('held') or {}).pop(hold[0], None); claim['used'] = float(claim.get('used') or 0) + float(usd or 0)


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


async def _inspect_picks(cid, doc, rows):
    """🔍 Slice 9: each {click, note} clicked through the page's own inspect tool (the script the viewer's sandbox runs) on the folder's
    newest page, as the viewer shows it. → the inspected elements, each with the owner-style note, ready for ws_build's region"""
    rs = _rs(); rows = [r for r in rows or [] if isinstance(r, dict)][:_insp.MAX]
    html = rs._feat.preview(rs._ws_placed(cid, (doc.get('versions') or [{}])[-1].get('html') or ''))
    got = await rs.asyncio.wait_for(_insp.pick_in_page(html, [str(r.get('click') or '')[:200] for r in rows], rs._fb.chromium_path()), 120)
    picks = [{**g, 'kind': 'el', 'mode': 'fix', 'note': str(r.get('note') or '')[:300]} for g, r in zip(got, rows) if g]
    if not picks:
        raise rs.HTTPException(400, 'Inspect found none of those elements on the page.')
    return picks


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
        try:   # 🧠 Slice 10: what its brains took from the stash vs browsed, the time and $ saved, each page as metadata only (never a word of it)
            st_ = rs._sbrain.record_for(rs._sbrain.root_of(rs.DATA_DIR), rs._prec.refs_of(f))
            if st_:
                if st_.get('from'):   # which filed proofs first kept the pages it was handed (any agent's)
                    want_ = {str(r)[5:]: r for r in st_['from'] if str(r).startswith('read:')}; got_ = []
                    for c_ in (rs._load().get('cats') or {}).values() if want_ else []:
                        for k_, key_ in rs._prec.KEYS.items():
                            got_ += [{'kind': rs._prec.CODE[k_], 'n': x.get('n'), 'id': x.get('id'), 'agent': c_.get('name'), 'test': bool(x.get('test'))} for x in c_.get(key_) or []
                                     if isinstance(x, dict) and str(x.get('readTid') or '') in want_]
                    st_['fromProofs'] = got_[:8]
                f['stash'] = st_
        except Exception as e:   # noqa: BLE001 — the proof still files
            print(f'[record] stash: {type(e).__name__}')
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
                     'last': {k: last.get(k) for k in ('id', 'n', 'at', 'topic', 'sym', 'test', 'wizard', 'ran', 'mindsCheck', 'read', 'foot', 'status', 'noTrade', 'why', 'ws', 'studio', 'version', 'kitsDid', 'unique', 'keep', 'brief', 'stash', 'kind', 'listing', 'bids', 'kept', 'bid', 'stage', 'platform', 'kits')}
                             | ({'codeCheck': {k: (last.get('codeCheck') or {}).get(k) for k in ('passed', 'total', 'failed', 'notRun')}} if last.get('codeCheck') else {}) | {'checks': last.get('proofChecks') or (last.get('checks') if isinstance(last.get('checks'), list) else [])} if last else None}
    return out


@router.get('/api/cats/internal/test-proof')
async def test_proof_state(request: Request, agent: str = ''):
    """🧪 Internal key only: the TEST agent's proofs, per kind (the last one filed and any still running)."""
    rs = _rs()
    rs._internal(request)
    cat = _sicario(rs._load(), agent)
    if not cat:
        raise rs.HTTPException(404, 'No such TEST agent.')
    tests = _test_view(cat); last_ = (tests.get('pos') or {}).get('last')
    if last_:   # 🔍 Slice 9: the TEST PoStatic's inspect before / after
        f_ = next((x for x in cat.get('psFolders') or [] if isinstance(x, dict) and x.get('id') == last_.get('id')), {})
        last_['inspect'] = f_.get('inspect')
    tasks_ = [rs._fc_taskchat._tc.view(t) for t in rs._fc_taskchat.tasks_of(cat['id'], cat) if t.get('test')][-3:]   # 🧵 Slice 35: its TEST task chats
    return {'agent': cat.get('name'), 'id': cat.get('id'), 'tests': tests, 'tasks': tasks_}


def busy_with(cat, kind, poc_busy=False):
    """The OTHER proof this agent is working on right now ('' when none): a chat start line sent then would only steer that one. Pure."""
    c = cat or {}
    runs = {'pop': c.get('popRun') or c.get('popRead'), 'pob': c.get('pobRun') or c.get('pobRead'),
            'pow': (c.get('powRun') or {}).get('folder') if isinstance(c.get('powRun'), dict) else None, 'poc': poc_busy}
    return next(({'pop': 'PoP', 'pob': 'PoB', 'pow': 'PoW', 'poc': 'PoC'}[k] for k, v in runs.items() if v and k != kind), '')


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
    store = rs._load(); cat = _sicario(store, p.agent)
    if not cat:
        raise rs.HTTPException(404, 'No such TEST agent.')
    pair = rs._lc.minds_for(cat.get('brainsCfg'), kind); cid = cat['id']; now = rs.time.time()
    if cat.get('handle') == SICARIO and (not pair or any(not str(m).startswith('local/') for m in pair)):   # §1: a TEST on Sicario's runs on the owner's own LM Studio only, $0
        raise rs.HTTPException(409, f"Sicario's {kind} pair is {pair or 'not set'}: a TEST runs only on free local minds (local/…).")
    if cat.get('handle') != SICARIO and p.op != 'stop':   # 💸 Happy's: its own paid minds, capped for every TEST together
        rows_ = rs._calls_of(cid); spent_, kind_ = spent_since(rows_), spent_since(rows_, kind=kind)
        if spent_ >= TEST_BUDGET_USD or kind_ >= KIND_BUDGET_USD:
            raise rs.HTTPException(402, f"TESTs on {cat.get('name')} have spent ${spent_:.2f} of ${TEST_BUDGET_USD:.2f} in all and ${kind_:.2f} of ${KIND_BUDGET_USD:.2f} on {kind}: the owner's caps.")
    if p.op == 'stop':
        if kind != 'pop':
            raise rs.HTTPException(400, 'Only an open paper PoP is stopped this way.')
        return await rs._cat_work(cid, rs.WorkPayload(op='ask', text='stop pop', session=rs._AUTO_TOKEN, auto=True))
    if p.door == 'task':   # 🧵 Slice 35: one TEST task chat split off this kind's newest folder, through the owner's own op (text work only, no money)
        f_ = next((f for f in reversed(cat.get(rs._prec.KEYS[kind]) or []) if isinstance(f, dict) and f.get('id')), None)
        out = await rs._cat_work(cid, rs.WorkPayload(op='task_new', job=f"{kind}:{f_['id']}" if f_ else kind, text=str(p.topic or 'Check this filing and list three things to do better next time.')[:600],
                                                    tools={'test': True}, session=rs._AUTO_TOKEN, auto=True))
        return {'ok': True, 'kind': kind, 'door': 'task', 'task': (out.get('task') or {}).get('id'), 'scope': (out.get('task') or {}).get('scope')}
    if _test_live(cat, kind, now):
        raise rs.HTTPException(409, f'A TEST {kind} is still running on {cat.get("name")}.')
    other_ = busy_with(cat, kind, cid in getattr(rs, '_POC_BUSY', ()))
    if other_ and kind in LINES:   # 🧪 Slice 6: the chat door hears a start line as a note to the proof it is working on ("propose a pow" went to a running PoP)
        raise rs.HTTPException(409, f'{cat.get("name")} is working on a {other_}; a TEST {kind} starts once it files.')
    rs._TEST_ON[(cid, kind)] = {'at': now, 'by': 'Claude', 'run': rs.uuid.uuid4().hex[:10], 'topic': str(p.topic or '')[:120]}
    try:
        if kind == 'poe' and p.door == 'earn':   # 💼 Slice 16: an earn filing through the same door the owner's tap takes: a real listing, both minds bid blind; nothing is sent
            out = await rs._cat_work(cid, rs.WorkPayload(op='earn_bid', text=str(p.topic or '')[:200], session=rs._AUTO_TOKEN, auto=True, tools={'wizard': p.wizard} if p.wizard else None))
        elif kind == 'poe':   # 📊 PoEco: one sealed market call on live pools, no model
            out = await rs._cat_work(cid, rs.WorkPayload(op='eco_call', session=rs._AUTO_TOKEN, auto=True))
        elif kind == 'pos' and p.ws:   # ⏫ Slice 3: a change to a TEST folder Claude made: its next version, through the same build door
            doc_ = rs._ws_load(cid, p.ws) or {}
            if not doc_.get('test') or not (doc_.get('versions') or []):
                raise rs.HTTPException(400, 'Only a TEST PoStatic folder that already has a page can be changed this way.')
            region_ = await _inspect_picks(cid, doc_, p.inspect) if p.inspect else None
            await rs._cat_work(cid, rs.WorkPayload(op='ws_build', job=p.ws, text=str(p.topic or 'Make it better.')[:2000], tools={'region': region_} if region_ else None, session=rs._AUTO_TOKEN, auto=True))
            out = {'ws': p.ws}
        elif kind == 'pos':   # 💻 a new PoStatic folder, its plan approved by the test (no owner tap to wait for), built by its own pair
            row_ = rs._feat.new_folder(cat, 'build', f"TEST {rs.time.strftime('%m-%d %H%M', rs.time.gmtime(now))}", now)
            rs._ws_save(cid, {**rs._feat.new_doc(row_), 'cfg': {'suggest': False}, 'test': True}); rs.keep_owned(cat); rs._save(store)
            if p.model:   # 🪦 Slice 2: a piece made in the 3D studio goes into the folder through the studio's own step, then the build runs
                await rs._cat_work(cid, rs.WorkPayload(op='play3d_model_to', tools={'to': row_['id'], 'obj': await _studio_piece(p.model)}, session=rs._AUTO_TOKEN, auto=True))
            out = await rs._cat_work(cid, rs.WorkPayload(op='ws_build', job=row_['id'], text=str(p.topic or TEST_ASK['pos'])[:2000], session=rs._AUTO_TOKEN, auto=True))
            out = {'ws': row_['id']}
        elif kind == 'pob' and (p.door == 'dash' or p.slip):   # 🎲 Slice 13: the dashboard's one-tap door, exactly as a tap sends it (a TEST never bids)
            if not str(p.topic or '').strip():
                raise rs.HTTPException(400, 'The dashboard door files a game: pass its topic.')
            out = await rs._cat_work(cid, rs.WorkPayload(op='pob', text=str(p.topic)[:120], tools={'slip': p.slip} if p.slip else None, session=rs._AUTO_TOKEN, auto=True))
        else:
            line = LINES[kind] + (f' {p.topic}' if p.topic and kind in ('pob', 'poc') else '')
            out = await rs._cat_work(cid, rs.WorkPayload(op='ask', text=line, session=rs._AUTO_TOKEN, auto=True))
    except Exception:
        rs._TEST_ON.pop((cid, kind), None)
        raise
    said = [c.get('text') for c in (out or {}).get('chat') or []][-1:] if isinstance(out, dict) else []
    return {'ok': True, 'kind': kind, 'pair': pair, 'run': rs._TEST_ON.get((cid, kind), {}).get('run'), 'said': said, **({'ws': out.get('ws')} if isinstance(out, dict) and out.get('ws') else {})}
