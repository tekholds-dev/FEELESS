"""💼 Slice 16 (owner 2026-11-19): PoEco earns real money with faceless paid work, wired. eco_earn.py is the pure part (terms, scoring, bids,
stages, grade); this module reads the public feeds, runs both minds blind and moves a filing through the approve door. Ops on /work:

  · earn_find  reads every kept platform's public feed → the board (the best listings with expected profit, what was left out and why)
  · earn_bid   both PoEco minds draft the bid blind for one listing (text = its id; '' = the board's best) → an earn filing in the PoEco folder
  · earn_go    the OWNER's tap only (the internal key and auto runs get 403): bid_approved · sent · won · lost · delivery_approved · paid · unpaid
  · earn_work  the OWNER's tap after a win: both minds do the work blind, the stronger is kept, the Collective (OSSY + G4) checks it
  · earn_view  the board, the platforms' terms and every earn filing

FEELESS never sends, delivers, signs up, logs in or holds money: an approve hands the owner the bid to send from HIS OWN account, and the
platform pays him directly. Same pattern as the other fc_ modules: every service name is looked up on feecat_service (as rs.<name>)."""
import asyncio

import eco_earn as _ee

OPS = ('earn_find', 'earn_bid', 'earn_go', 'earn_work', 'earn_view')
BOARD_FRESH_S = 1800
MIND_WAIT_S = 240
UA = {'User-Agent': 'FEELESS-earn-finder/1.0 (public listings reader)', 'Accept': 'application/json'}
_BUSY = set()


def _rs():
    import feecat_service
    return feecat_service


async def _get_json(http, url, reads, host):
    """One public GET (no login, no cookies). Every read is kept on the record, the failed ones too."""
    try:
        r = await http.get(url, headers=UA, timeout=15, follow_redirects=True)
        ok = r.status_code == 200
        reads.append({'host': host, 'url': url, 'ok': ok, 'code': r.status_code})
        return r.json() if ok else None
    except Exception as e:   # noqa: BLE001: one feed down never stops the others
        reads.append({'host': host, 'url': url, 'ok': False, 'err': type(e).__name__})
        return None


async def _sol_usd(http, reads):
    j = await _get_json(http, 'https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112', reads, 'dexscreener.com')
    pairs = [p for p in (j or {}).get('pairs') or [] if (p.get('quoteToken') or {}).get('symbol') in ('USDC', 'USDT') and p.get('priceUsd')]
    pairs.sort(key=lambda p: -float((p.get('liquidity') or {}).get('usd') or 0))
    return float(pairs[0]['priceUsd']) if pairs else None


async def _contributing(http, repo, reads):
    """The repo's own AI rule (its CONTRIBUTING, read raw from GitHub). None when it has none."""
    for path in ('CONTRIBUTING.md', '.github/CONTRIBUTING.md', 'AI_POLICY.md'):
        url = f'https://raw.githubusercontent.com/{repo}/HEAD/{path}'
        try:
            r = await http.get(url, timeout=10, follow_redirects=True)
        except Exception:   # noqa: BLE001
            continue
        if r.status_code == 200:
            reads.append({'host': 'raw.githubusercontent.com', 'url': url, 'ok': True, 'code': 200})
            return r.text[:60000]
    return None


async def read_feeds(http):
    """Every kept platform's public feed → (kept, out, reads)."""
    reads, kept, out = [], [], []
    sol = await _sol_usd(http, reads)
    seen = set()
    for url in _ee.PLAT['superteam']['feeds']:
        k, o = _ee.parse_superteam(await _get_json(http, url, reads, 'superteam.fun'), {'SOL': sol} if sol else None)
        for r in k + o:
            if r['id'] in seen:
                continue
            seen.add(r['id']); (out if r.get('outWhy') else kept).append(r)
    k, o = _ee.parse_freelancer(await _get_json(http, _ee.PLAT['freelancer']['feeds'][0], reads, 'freelancer.com'))
    kept += k; out += o
    gh = await _get_json(http, _ee.PLAT['algora']['feeds'][0], reads, 'api.github.com')
    repos = list(dict.fromkeys(_ee.repo_of(i.get('html_url')) for i in (gh or {}).get('items') or [] if isinstance(i, dict)))[:8]
    rules = {}
    for repo in repos:
        rules[repo] = _ee.ai_rule(await _contributing(http, repo, reads))
    k, o = _ee.parse_algora(gh, rules)
    kept += k; out += o
    return kept, out, reads


def _earns(cat):
    return [f for f in cat.get('poeFolders') or [] if isinstance(f, dict) and f.get('kind') == 'earn']


def _view(cat):
    b = cat.get('earnBoard') or {}
    return {'board': b, 'platforms': _ee.PLATFORMS, 'earns': _earns(cat)[::-1], 'busy': cat.get('id') in _BUSY, 'poeFolders': (cat.get('poeFolders') or [])[::-1]}


async def _find(cat_id):
    rs = _rs()
    async with rs.httpx.AsyncClient() as http:
        kept, out, reads = await read_feeds(http)
    store = rs._load(); cat = store['cats'].get(cat_id) or {}
    per = _ee.per_call(rs._calls_of(cat_id, 4000))
    filed = [(f.get('listing') or {}).get('id') for f in _earns(cat)]
    b = _ee.board(kept, out, per, filed)
    b['reads'] = reads; b['perCall'] = per
    b['best'] = [{**r, 'desc': _ee._cut(r.get('desc'), 400)} for r in b['best']]
    cat['earnBoard'] = b; rs.keep_owned(cat); rs._save(store)
    return b


def _chat(cat, text):
    rs = _rs()
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': text, 'at': rs.time.time(), 'open': 'poe'}])[-200:]


async def _two(cat, brains, sys_, user_, parse, tokens):
    """Both minds, blind (neither sees the other), one stricter retry on an unreadable reply. → [(parsed, usd, own, raw, err)]"""
    rs = _rs()

    async def one(i, m):
        usd_all, own_any, raw, err = 0.0, False, '', ''
        for n_ in range(2):
            try:
                raw, usd, own = await asyncio.wait_for(rs._ws_ask(cat, m, sys_ + f'\nYou are Mind {"AB"[i % 2]}.' + ('\n' + _ee.RETRY if n_ else ''), user_, tokens), MIND_WAIT_S)
            except Exception as e:   # noqa: BLE001: one mind down never stops the other
                err = type(e).__name__; break
            usd_all += usd or 0; own_any = own_any or own
            if parse(raw):
                break
        return parse(raw), usd_all, own_any, raw, err
    return await asyncio.gather(*(one(i, m) for i, m in enumerate(brains[:2])))


def _kit_names(cat_id):
    rs = _rs(); ids = rs._KIT_LAST.get((cat_id, 'poe')) or []
    names = {k['id']: k.get('name') for k in rs._kits.all_rows(rs.KITS_DIR)}
    return [names.get(i, i) for i in ids]


async def _bid(cat_id, lid='', wiz=None):
    """One listing → both minds' blind bids → the stronger kept → an earn filing (footprint-gated, true record, TEST mark)."""
    rs = _rs()
    try:
        store = rs._load(); cat = store['cats'].get(cat_id) or {}
        b = cat.get('earnBoard') or {}
        if not b.get('best') or rs.time.time() - float(b.get('at') or 0) > BOARD_FRESH_S:
            b = await _find(cat_id); store = rs._load(); cat = store['cats'].get(cat_id) or {}
        filed = {(f.get('listing') or {}).get('id') for f in _earns(cat)}
        rows = sorted((s_ for s_ in (_ee.score(r, b.get('perCall') or 0.002) for r in b.get('best') or [] if r['id'] not in filed) if s_['score']),
                      key=lambda r: (-r['score'], -(r['expProfit'] or 0)))   # re-scored with today's rules: a board kept from before a rule change never picks for it (2026-11-20 TEST #2)
        row = next((r for r in rows if r['id'] == lid), None) if lid else (rows[0] if rows else None)
        if not row:
            raise RuntimeError('no open faceless listing left on the board' if not lid else 'that listing is not on the board (or was already bid on)')
        wiz_line, wiz_rec = '', None
        if wiz:   # 🧭 Slice 33: the start wizard's kits (via _recall), its research pass and the owner's direction reach both minds
            rs._wiz.CTX.set(wiz)
            async with rs.httpx.AsyncClient(timeout=12) as http_w:
                found_ = await rs._wiz.research(wiz, f"{row['title']} {row.get('cat') or ''}".strip(), http_w, rs._tools.build_refs, rs._fc_desk.wiz_ask(cat, 'poe', row['id']))
            base_ = rs._wiz.start_row(_earns(cat), wiz.get('start')); wiz_line = rs._wiz.line(wiz, found_, base_); wiz_rec = rs._wiz.record(wiz, found_, base_)
        for attempt in range(2):
            fid = f'earn{int(rs.time.time())}{attempt or ""}'; brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poe') or []
            rs._CALL_CTX.set({'kind': 'poe', 'ref': fid, 'minds': brains})
            sys_ = _ee.SYS + rs._recall(cat, 'Earn', f"{row['title']} {row.get('cat')} bid proposal") + rs._prec.back_line(cat.get('footBack'), 'poe', rs.time.time()) + wiz_line
            got = await _two(cat, brains, sys_, _ee.ask_text(row), _ee.parse_bid, 1400)
            cost = sum(g[1] for g in got); own = any(g[2] for g in got)
            k, scored = _ee.pick([g[0] for g in got], row)
            calls = [{'mind': i, 'name': str(brains[i]).split('/')[-1][:24], 'model': brains[i], 'read': bool(g[0]), 'err': g[4], 'raw': str(g[3] or '')[:600]} for i, g in enumerate(got)]
            store = rs._load(); c_ = store['cats'].get(cat_id)
            if not c_:
                return
            list_ = c_.setdefault('poeFolders', [])
            f_ = _ee.new_folder(rs._next_n(list_), row, k, scored, calls, cost)
            f_.update(id=fid, kits=_kit_names(cat_id), callRefs=[fid], sitesRead=[{'host': r['host'], 'ok': r['ok']} for r in b.get('reads') or []],
                      sources={'listing': [{'url': row['url']}], 'feeds': [{'url': r['url']} for r in b.get('reads') or [] if r.get('ok')][:12]},
                      **({'testRun': True} if (cat_id, 'poe') in rs._TEST_ON else {}), **({'wizard': wiz_rec} if wiz_rec else {}))
            if cost and not own and c_.get('brainsCfg'):
                rs._lc.charge(c_['brainsCfg'], cost)
            if k is None:
                rs._save(store)
                raise RuntimeError('neither mind drafted a readable bid')
            if attempt == 0 and rs._foot_back(c_, 'poe', f_):   # 👣 mostly what a past filing read and bid on → back once, on the next listing
                rs._save(store); filed.add(row['id'])
                row = next((r for r in rows if r['id'] not in filed), row); continue
            list_.append(rs._record_file(c_, 'poe', f_))
            _chat(c_, f"💼 PoEco #{f_['n']}: a bid is drafted for \"{_ee._cut(row['title'], 70)}\" on {f_['platform']['name']} ({row['pay']}, expected profit ${float(row.get('expProfit') or 0):.2f}). Approve it, then send it from your own account. Nothing was sent.")
            rs.keep_owned(c_); rs._save(store)
            return f_
    except Exception as e:   # noqa: BLE001
        print(f'[earn] {cat_id}: {type(e).__name__}: {str(e)[:140]}')
        try:
            store = rs._load(); c_ = store['cats'].get(cat_id)
            if c_:
                _chat(c_, f'💼 No bid was drafted: {str(e)[:140]}. Nothing was sent.'); rs._save(store)
        except Exception:   # noqa: BLE001
            pass
        rs._TEST_ON.pop((cat_id, 'poe'), None)
    finally:
        _BUSY.discard(cat_id)


async def _collective(f):
    """OSSY + G4 (the Collective) judge the deliverable on the earn rubric. → the combined review (verdict None when no judge answered)."""
    rs = _rs(); store = rs._load()
    sic = next((c for c in store['cats'].values() if c.get('handle') == 'sicarios'), None) or {'id': 'collective', 'ownerStaff': True}
    body = rs._review.brief('poe', f); by = {}
    for key, model, _name in rs._review.REVIEWERS[:2]:
        tok = rs._CALL_CTX.set({'kind': 'poe', 'ref': f'review:{f.get("id")}', 'minds': [model]})
        try:
            raw, _u, _v = await asyncio.wait_for(rs._think({**sic, 'ownerStaff': True}, model, [{'role': 'system', 'content': rs._review.SYS}, {'role': 'user', 'content': body}], max_tokens=700), 240)
            by[key] = rs._review.verdict_of(raw, rs.time.strftime('%Y-%m-%d', rs.time.gmtime()))
        except Exception as e:   # noqa: BLE001
            print(f'[earn] judge {key}: {type(e).__name__}'); by[key] = None
        finally:
            rs._CALL_CTX.reset(tok)
    return {**rs._review.combine(by, (), [], body), 'at': round(rs.time.time())}


async def _work(cat_id, fid):
    rs = _rs()
    try:
        store = rs._load(); cat = store['cats'].get(cat_id) or {}; f = _folder(cat, fid)
        if f.get('stage') == 'won':
            brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poe') or []
            rs._CALL_CTX.set({'kind': 'poe', 'ref': fid, 'minds': brains})
            sys_ = _ee.WORK_SYS + rs._recall(cat, 'Earn', f"{(f.get('listing') or {}).get('title')} deliver acceptance checks")
            got = await _two(cat, brains, sys_, _ee.work_text(f), _ee.parse_work, 6000)
            scored = [(*_ee.work_score(g[0], f), g[0]) for g in got]; k = max(range(len(scored)), key=lambda i: scored[i][0]) if scored else None
            cost = sum(g[1] for g in got)
            store = rs._load(); cat = store['cats'].get(cat_id) or {}; f = _folder(cat, fid)
            if k is None or not scored[k][0]:
                _chat(cat, f"💼 PoEco #{f.get('n')}: neither mind made a readable deliverable. Nothing was delivered."); rs._save(store); return
            f['work'] = {**scored[k][2], 'mind': k, 'scores': [{'mind': i, 'score': s, 'why': w} for i, (s, w, _x) in enumerate(scored)], 'cost': round(cost, 5), 'kits': _kit_names(cat_id)}
            _ee.move(f, 'work', 'minds'); rs._save(store)
        rv = await _collective(f)
        store = rs._load(); cat = store['cats'].get(cat_id) or {}; f = _folder(cat, fid)
        f['collective'] = rv
        if rv.get('verdict'):
            _ee.move(f, 'checked', 'collective', verdict=rv['verdict'], score=rv.get('score'))
        _chat(cat, f"💼 PoEco #{f.get('n')}: the work is done; the Collective says {rv.get('verdict') or 'nothing yet (no judge answered: tap Do the work again to re-check)'}. Approve the delivery, then deliver it from your own account.")
        f['proofChecks'] = rs._prec.checks('poe', f, rs._lc.minds_for(cat.get('brainsCfg'), 'poe'))
        rs.keep_owned(cat); rs._save(store)
    except Exception as e:   # noqa: BLE001
        print(f'[earn] work {cat_id}: {type(e).__name__}: {str(e)[:140]}')
    finally:
        _BUSY.discard(cat_id)


def _folder(cat, fid):
    f = next((x for x in _earns(cat) if x.get('id') == str(fid or '')), None)
    if not f:
        raise _rs().HTTPException(404, 'No such earn filing.')
    return f


async def op(cat_id, cat, store, p, internal_):
    """The earn door. Finding and drafting may run on the internal key (Claude's TEST); every step that sends, delivers or marks money is the owner's."""
    rs = _rs(); t_ = p.tools if isinstance(p.tools, dict) else {}
    if p.op == 'earn_view':
        return _view(cat)
    if p.op == 'earn_find':
        await _find(cat_id)
        return _view(rs._load()['cats'].get(cat_id) or cat)
    if p.op == 'earn_bid':
        if cat_id in _BUSY:
            raise rs.HTTPException(409, 'A bid or a job is already being drafted on this agent.')
        _BUSY.add(cat_id)
        rs.asyncio.create_task(_bid(cat_id, str(p.text or ''), t_.get('wizard')))   # 🧭 Slice 33: + the start wizard's choices
        return {**_view(cat), 'busy': True, 'said': 'Both minds are drafting the bid blind. Nothing will be sent.'}
    by = 'auto' if internal_ or p.auto else 'owner'
    f = _folder(cat, p.job)
    if p.op == 'earn_work':
        why = _ee.can_go({**f, 'stage': 'won'} if f.get('stage') == 'work' else f, 'work', by)
        if why:
            raise rs.HTTPException(403 if by != 'owner' else 409, why)
        if cat_id in _BUSY:
            raise rs.HTTPException(409, 'A bid or a job is already being drafted on this agent.')
        _BUSY.add(cat_id)
        rs.asyncio.create_task(_work(cat_id, f['id']))
        return {**_view(cat), 'busy': True, 'said': 'Both minds are doing the work blind; the Collective checks it after. Nothing will be delivered.'}
    stage = str(t_.get('stage') or '')
    why = _ee.can_go(f, stage, by, t_.get('real') is True)
    if why:
        raise rs.HTTPException(403 if by != 'owner' else 409, why)
    kw = {'why': str(t_.get('why') or '')[:300]}
    if stage in ('lost', 'unpaid') and not kw['why']:
        raise rs.HTTPException(400, 'Say why, so the grade carries it.')
    if stage == 'paid':
        try:
            f['receipt'] = _ee.receipt(t_.get('amount'), t_.get('fee'), t_.get('currency') or 'USD', t_.get('rate') or 1, t_.get('ref'))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        if not f['receipt']['amount']:
            raise rs.HTTPException(400, 'Put in the amount the platform paid you.')
    if stage == 'bid_approved':
        f['approved'] = {'seal': _ee.seal(f), 'at': round(rs.time.time())}
    if stage == 'sent':
        kw['link'] = str(t_.get('link') or '')[:300]
    _ee.move(f, stage, by, **kw)
    g = _ee.grade(f)
    if g:
        f['graded'] = g
    f['proofChecks'] = rs._prec.checks('poe', f, rs._lc.minds_for(cat.get('brainsCfg'), 'poe'))
    said = {'bid_approved': f"Approved. Send it yourself from your {f['platform']['name']} account: {(f.get('listing') or {}).get('url')}. Then mark it sent.",
            'paid': f"Graded: {g['why']}" if g else '', 'lost': f"Graded lost: {kw['why']}", 'unpaid': f"Graded unpaid: {kw['why']}"}.get(stage, f'Marked {stage.replace("_", " ")}.')
    _chat(cat, f"💼 PoEco #{f.get('n')}: {said}")
    rs.keep_owned(cat); rs._save(store)
    return {**_view(cat), 'said': said, **({'send': {'url': (f.get('listing') or {}).get('url'), 'bid': (f.get('bid') or {}).get('bid')}} if stage == 'bid_approved' else {})}
