"""🎓 COMP v2 exam — run under .venv-mlx: `.venv-mlx/bin/python backend/comp_v2_exam.py backend/data/comp_v2`.

Every examinee answers the same held-out proofs (test_rows.json, never trained on: real, judged proofs only, Slice 7): the base Qwen3.5-9B,
COMP v2 (base + the owner's LoRA adapter), the always-the-majority baseline, the owner's own OSSY, G4 and ZED (each on its own LM Studio,
never a fallback), and the flagship APIs when their key is in backend/.env (Claude via the Anthropic SDK,
GPT and Grok via their HTTP APIs). A flagship with no key is listed as blocked, never scored. exam.json is rewritten after each examinee.
At the end the ship rule runs (comp_v2.ship): COMP ships only if it beats the base model, and exam.json says why either way.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comp_v2 as cv  # noqa: E402
import guardrails as _gr  # noqa: E402

MAX_FLAGSHIP_Q = 40          # spend cap: at most this many questions per paid API (each is ~200 tokens in, a few out)


def env_keys():
    """The flagship keys saved in backend/.env (HQ › Agents writes them there) or this process's env."""
    keys = {}
    try:
        for ln in (Path(__file__).resolve().parent / '.env').read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith('#') and '=' in ln:
                k, v = ln.split('=', 1)
                keys[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return {k: (keys.get(k) or os.environ.get(k) or '') for k in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'XAI_API_KEY', 'OPENAI_MODEL', 'XAI_MODEL',
                                                               'LOCAL_LLM_ENABLED', 'LOCAL_LLM_BASE_URL', 'LOCAL_LLM_MODEL', 'LOCAL_LLM_API_KEY',
                                                               'LAN_LLM_BASE_URL', 'LAN_LLM_MODEL', 'LAN_LLM_API_KEY',
                                                               'ZED_LLM_BASE_URL', 'ZED_LLM_MODEL', 'ZED_LLM_API_KEY')}


OR_FLAGSHIP = {'claude': 'anthropic/claude-opus-5.5', 'gpt': 'openai/gpt-4o-mini', 'grok': 'x-ai/grok-4.7'}   # ids read from OpenRouter /models 2026-11-17


def owner_openrouter(store_path=None):
    """The owner's shared OpenRouter key (the one his agents use: cat_keys.owner_key, as COMP's teacher reads it), or ''."""
    import cat_keys
    data = Path(__file__).resolve().parent / 'data'
    return cat_keys.owner_key(store_path or (data / 'feecats.json'), 'openrouter', data_dir=data)[0] or ''


def owner_spend(store_path=None, data=None):
    """💵 → (the donor agent's id, a fn that raises spend_guard.OverCap when his day cap is reached). The exam spends HIS money, so it is
    counted with his agents' other calls (owner 2026-11-17: "assure real money readyness")."""
    import cat_keys
    import spend_guard as sg
    data = Path(data or Path(__file__).resolve().parent / 'data')
    try:
        cats = list((json.loads(Path(store_path or (data / 'feecats.json')).read_text()).get('cats') or {}).values())
    except (OSError, ValueError):
        cats = []
    got = cat_keys.newest_owner_row(cats, 'openrouter'); donor = got[1] if got else None
    key, ids = sg.group(cats, next((c for c in cats if c.get('id') == donor), {'id': donor}))   # the same group the service counts
    try:
        cap = sg.clean_cap(sg.caps_read(data / 'spend_caps.json').get(key, sg.DAILY_CAP_USD))
    except ValueError:
        cap = sg.DAILY_CAP_USD

    def check():
        since = sg.day_start()
        sg.check(sg.spent(sg.read_rows(data / 'model_receipts.jsonl', since), ids, since), 0, 0, cap)
    return donor, check


def openrouter_answers(rows, key, model, cat_id, check, ledger=None, timeout=90):
    """🔑 A flagship on the owner's OpenRouter key: one call per question, plain OpenRouter fields only (no LM Studio switches), every
    billed call written to the receipt ledger, and his day cap checked before each one. → answers"""
    import httpx
    ledger = Path(ledger or Path(__file__).resolve().parent / 'data' / 'model_receipts.jsonl'); out = []
    with httpx.Client(timeout=timeout, headers={'Authorization': f'Bearer {key}'}) as h:
        for r in rows:
            check()
            res = h.post('https://openrouter.ai/api/v1/chat/completions', json={'model': model, 'max_tokens': 300, 'messages': [
                {'role': 'system', 'content': cv.SYSTEM}, {'role': 'user', 'content': cv.prompt_of(r)}]})
            res.raise_for_status(); d = res.json(); usd = float((d.get('usage') or {}).get('cost') or 0)
            if usd > 0:
                with ledger.open('a') as f_:
                    f_.write(json.dumps({'id': str(d.get('id') or '')[:40], 'cat': cat_id, 'at': time.time(), 'provider': 'OpenRouter', 'model': d.get('model') or model,
                                         'usd': usd, 'tokens': (d.get('usage') or {}).get('total_tokens'), 'status': 'provider reported', 'funding': 'owner key',
                                         'for': 'COMP exam'}, separators=(',', ':')) + '\n')
            out.append(cv.answer_of(((d.get('choices') or [{}])[0].get('message') or {}).get('content') or ''))
    return out


def own_minds(keys, pick=None):
    """🖥 AGX-6 + Slice 7: the owner's three judges sit the same exam, each on ITS OWN LM Studio only (never a fallback model, never a paid
    API): OSSY = LM Studio on this Mac, G4 = LM Studio on the desktop Mac (LAN), ZED = a Google Gemma (ZED_LLM_BASE_URL, else this Mac's
    LM Studio). ZED answers only from a Gemma: a Qwen answering as ZED would be OSSY twice, so with no Gemma loaded it is blocked, named.
    → [(id, name, base, model, key, why_blocked)]"""
    on = str(keys.get('LOCAL_LLM_ENABLED') or '').strip().lower() in ('1', 'true', 'yes', 'on')
    ossy_base = (keys.get('LOCAL_LLM_BASE_URL') or 'http://127.0.0.1:1234/v1').rstrip('/')
    g4_base = (keys.get('LAN_LLM_BASE_URL') or '').rstrip('/')
    zed_base = (keys.get('ZED_LLM_BASE_URL') or ossy_base).rstrip('/')
    zed_key = keys.get('ZED_LLM_API_KEY') or keys.get('LOCAL_LLM_API_KEY') or ''
    zed_model, zed_why = keys.get('ZED_LLM_MODEL') or '', None
    if not zed_model or 'gemma' not in zed_model.lower():   # `pick` asks its LM Studio which Gemma it has (main passes zed_pick)
        zed_model = pick(zed_base, zed_key) if pick else ''
        zed_why = None if zed_model else 'no Gemma loaded in its LM Studio (ZED never answers with another family\'s model)'
    return [('ossy', f"OSSY · {(keys.get('LOCAL_LLM_MODEL') or 'qwen2.5-7b-instruct-mlx').split('/')[-1]}", ossy_base, keys.get('LOCAL_LLM_MODEL') or 'qwen2.5-7b-instruct-mlx',
             keys.get('LOCAL_LLM_API_KEY') or '', None if on else 'off: LOCAL_LLM_ENABLED is not true'),
            ('g4', f"G4 · {(keys.get('LAN_LLM_MODEL') or 'qwen/qwen3.5-4b').split('/')[-1]}", g4_base, keys.get('LAN_LLM_MODEL') or 'qwen/qwen3.5-4b',
             keys.get('LAN_LLM_API_KEY') or '', None if g4_base else 'off: LAN_LLM_BASE_URL is not set'),
            ('zed', f"ZED · {(zed_model or 'Gemma').split('/')[-1]}", zed_base, zed_model, zed_key, zed_why)]


def zed_pick(base, key, get=None):
    """The Gemma ZED's LM Studio has (loaded models first, from LM Studio's own list), or '' when it has none or does not answer."""
    import httpx
    get = get or (lambda url: httpx.get(url, headers={'Authorization': f'Bearer {key}'} if key else {}, timeout=8))
    try:
        ids = [m.get('id') for m in (get(f'{base}/models').json().get('data') or [])]
    except Exception:   # noqa: BLE001 — an LM Studio that does not answer gives ZED nothing to use
        return ''
    return next((i for i in ids if 'gemma' in str(i).lower()), '')


def local_margins(rows_sets, adapter=None, makers=(cv.prompt_of,)):
    """One model load. For every prompt style × row set → the model's confidence gap logit(won) − logit(lost) on its first answer token.
    Reading the confidence (not a sampled word) shows real signal even when the top word is always the same."""
    import mlx.core as mx
    from mlx_lm import load
    model, tok = load(str(cv.BASE), adapter_path=adapter)
    def first_ids(words):   # every single-token spelling: won / Won / " won" … (WON splits into W+ON, so it is left out)
        return sorted({tok.encode(w, add_special_tokens=False)[0] for w in words})
    W, L = first_ids(('won', 'Won', ' won', ' Won')), first_ids(('lost', 'Lost', ' lost', ' Lost'))
    outs = []
    for make in makers:
        per = []
        for rows in rows_sets:
            ms = []
            for r in rows:
                msgs = [{'role': 'system', 'content': cv.SYSTEM}, {'role': 'user', 'content': make(r)}]
                try:
                    p = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, enable_thinking=False)
                except TypeError:
                    p = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
                x = mx.array(tok.encode(p, add_special_tokens=False))[None]
                lg = model(x)[0, -1]
                ms.append(float(mx.logsumexp(lg[mx.array(W)]) - mx.logsumexp(lg[mx.array(L)])))
            per.append(ms)
        outs.append(per)
    del model
    return outs


def threshold(margins, rows):
    """The cut-off on the confidence gap that answers the VALID proofs best (0 = the model's own top word when nothing beats it)."""
    cands = sorted(set([0.0] + [round(m, 4) for m in margins]))
    best = (cv.score(rows, ['won' if m > 0 else 'lost' for m in margins])['acc'], 0.0)
    for i in range(len(cands)):
        t = (cands[i] + cands[i + 1]) / 2 if i + 1 < len(cands) else cands[i] + 1e-3
        acc = cv.score(rows, ['won' if m > t else 'lost' for m in margins])['acc']
        if acc > best[0] + 1e-9:
            best = (acc, t)
    base = cv.score(rows, ['won' if m > 0 else 'lost' for m in margins])['acc']
    if best[0] - base < 2 / max(1, len(rows)) - 1e-9:   # a cut must win at least 2 more valid proofs, or it is noise: keep its own word
        return 0.0, base
    return best[1], best[0]


def judged(rows, margins, t):
    return cv.score(rows, ['won' if m > t else 'lost' for m in margins])


def pick_checkpoint(folder, valid):
    """Early stopping on what matters: every saved checkpoint is read on the VALID proofs (never the exam), calibrated there; the most right
    wins, the earliest on a tie (less memorised). → (adapter dir, [[iter, valid acc]])."""
    import shutil
    import tempfile
    ad = folder / 'adapter'
    cks = sorted(ad.glob('*_adapters.safetensors'))
    if not valid or not cks:
        return str(ad), []
    curve, best = [], (-1, None)
    for ck in cks:
        tmp = Path(tempfile.mkdtemp())
        shutil.copy(ad / 'adapter_config.json', tmp); shutil.copy(ck, tmp / 'adapters.safetensors')
        (vm,), = local_margins([valid], str(tmp))
        acc = threshold(vm, valid)[1]
        it = int(ck.name.split('_')[0]); curve.append([it, acc])
        print('checkpoint', it, acc, flush=True)
        if acc > best[0]:
            best = (acc, tmp)
    return str(best[1]), curve


def claude_answers(rows, key):
    import anthropic
    client = anthropic.Anthropic(api_key=key, max_retries=2, timeout=60)
    out = []
    for r in rows:
        resp = client.messages.create(model='claude-opus-5-5', max_tokens=2000, system=cv.SYSTEM, output_config={'effort': 'low'},
                                      messages=[{'role': 'user', 'content': cv.prompt_of(r)}])
        if resp.stop_reason == 'refusal':
            out.append(None); continue
        out.append(cv.answer_of(' '.join(b.text for b in resp.content if b.type == 'text')))
    return out


def openai_style(rows, key, base, model, timeout=60):
    import httpx
    out = []
    with httpx.Client(timeout=timeout, headers={'Authorization': f'Bearer {key}'} if key else {}) as h:
        for r in rows:
            res = h.post(f'{base}/chat/completions', json={'model': model, 'messages': [
                {'role': 'system', 'content': cv.SYSTEM}, {'role': 'user', 'content': cv.prompt_of(r)}],
                # 🧠 Qwen 3.5 thinks out loud by default: 28 questions × minutes of thinking hit the timeout (2026-11-14 race: OSSY + G4 ReadTimeout). Off = ~1 s an answer.
                'max_tokens': 300, 'chat_template_kwargs': {'enable_thinking': False}, 'reasoning_effort': 'none'})   # the desktop's LM Studio only honours reasoning_effort
            res.raise_for_status()
            out.append(cv.answer_of(res.json()['choices'][0]['message']['content']))
    return out


def main(folder, free=False):
    """`free` = no paid call at all (the flagships are listed, never asked): how Claude runs the exam (Slice 7, §1: never spend)."""
    folder = Path(folder)
    rows = json.loads((folder / 'test_rows.json').read_text())
    train = [{'outcome': m['messages'][2]['content']} for m in map(json.loads, (folder / 'train.jsonl').read_text().splitlines())]
    try:
        ds = json.loads((folder / 'dataset.json').read_text())
    except (OSError, ValueError):
        ds = {}
    exam = {'at': round(time.time()), 'n': len(rows), 'task': 'won or lost, from what the proof said and did before it settled', 'examinees': [],
            'only': ds.get('only') or '', 'byKind': ds.get('byKind') or [], 'droppedN': ds.get('droppedN') or 0}

    def put(e):
        exam['examinees'] = [x for x in exam['examinees'] if x['id'] != e['id']] + [e]
        (folder / 'exam.json').write_text(json.dumps(exam))
        print(e['id'], e.get('score', {}).get('acc'), e.get('blocked', ''), flush=True)

    maj = cv.majority(train)
    put({'id': 'baseline', 'name': f'Always "{maj}"', 'kind': 'baseline', 'score': cv.score(rows, [maj] * len(rows))})
    try:
        mem = json.loads((folder / 'train_rows.json').read_text())
    except (OSError, ValueError):
        mem = []
    try:
        valid = json.loads((folder / 'valid_rows.json').read_text())
    except (OSError, ValueError):
        valid = []
    recall = lambda r: cv.memory_prompt(r, mem)   # noqa: E731 — 🧠 memory: the past proofs most like it, and how they ended

    def put_local(eid, name, vm, tm, sec):
        t, vacc = threshold(vm, valid) if valid else (0.0, None)
        put({'id': eid, 'name': name, 'kind': 'local', 'score': judged(rows, tm, t), 'raw': judged(rows, tm, 0.0), 'cut': round(t, 3),
             'validAcc': vacc, 'seconds': sec})

    t0 = time.time(); ((bv, bt),) = local_margins([valid, rows], None)
    put_local('base', cv.BASE_NAME, bv, bt, round(time.time() - t0))
    chosen = None
    if not (folder / 'adapter' / 'adapters.safetensors').exists():
        put({'id': 'comp', 'name': 'COMP v2 · 9B LoRA', 'kind': 'local', 'blocked': 'not trained yet'})
    else:
        chosen, exam['checkpoints'] = pick_checkpoint(folder, valid)
        exam['picked'] = max(exam['checkpoints'], key=lambda x: (x[1], -x[0]))[0] if exam['checkpoints'] else None
        t0 = time.time(); outs = local_margins([valid, rows], chosen, (cv.prompt_of, recall) if mem else (cv.prompt_of,))
        sec = round(time.time() - t0)
        put_local('comp', 'COMP v2 · 9B LoRA', outs[0][0], outs[0][1], sec)
        if len(outs) > 1:
            put_local('comp_mem', 'COMP v2 + memory', outs[1][0], outs[1][1], sec)
    keys = env_keys(); g_ = _gr.load(Path(__file__).resolve().parent / 'data' / 'guardrails.json')   # 🛡 AGX-7: the owner's paid-exam switch + question cap
    qs = [] if free else rows[:min(MAX_FLAGSHIP_Q, int(_gr.value(g_, 'compFlagships')))]   # the PAID flagships' questions
    own_qs = rows   # 🖥 Slice 7: OSSY, G4 and ZED are free: they answer every held-out proof, so their scores compare with COMP's
    for eid, name, base, model, key, why in own_minds(keys, zed_pick):   # 🖥 OSSY + G4 + ZED: free, on the owner's own machines
        if why:
            put({'id': eid, 'name': name, 'kind': 'own', 'blocked': why}); continue
        try:
            t0 = time.time(); put({'id': eid, 'name': name, 'kind': 'own', 'score': cv.score(own_qs, openai_style(own_qs, key, base, model, timeout=120)), 'seconds': round(time.time() - t0)})
        except Exception as e:   # noqa: BLE001 — an unreachable desktop never stops the exam
            put({'id': eid, 'name': name, 'kind': 'own', 'blocked': f'its LM Studio did not answer ({type(e).__name__})'})
    flag = (('claude', 'Claude Opus 5.5', 'ANTHROPIC_API_KEY', lambda k: claude_answers(qs, k)),
            ('gpt', keys['OPENAI_MODEL'] or 'gpt-4o-mini', 'OPENAI_API_KEY',
             lambda k: openai_style(qs, k, 'https://api.openai.com/v1', keys['OPENAI_MODEL'] or 'gpt-4o-mini')),
            ('grok', keys['XAI_MODEL'] or 'grok-3-mini', 'XAI_API_KEY',
             lambda k: openai_style(qs, k, 'https://api.x.ai/v1', keys['XAI_MODEL'] or 'grok-3-mini')))
    or_key = owner_openrouter() if qs else ''   # 🔑 owner 2026-11-17: "my openrouter key to be useable with comp": a flagship with no key of its own sits the exam on it
    or_cat, or_check = owner_spend() if or_key else (None, None)
    for eid, name, var, run in flag:
        if not qs:
            put({'id': eid, 'name': name, 'kind': 'flagship', 'blocked': 'free exam: no paid call' if free else 'off in your guardrails'}); continue
        if not keys[var] and or_key:
            name_ = f'{name} · your OpenRouter'
            try:
                put({'id': eid, 'name': name_, 'kind': 'flagship', 'via': 'openrouter', 'score': cv.score(qs, openrouter_answers(qs, or_key, OR_FLAGSHIP[eid], or_cat, or_check))})
            except Exception as e:   # noqa: BLE001 — one provider failing never stops the exam
                import spend_guard as _sg
                put({'id': eid, 'name': name_, 'kind': 'flagship', 'blocked': str(e) if isinstance(e, _sg.OverCap) else f'call failed: {type(e).__name__}'})
            continue
        if not keys[var]:
            put({'id': eid, 'name': name, 'kind': 'flagship', 'blocked': 'no key: add it in HQ › Agents, or save an OpenRouter key on one of your agents'}); continue
        try:
            put({'id': eid, 'name': name, 'kind': 'flagship', 'score': cv.score(qs, run(keys[var]))})
        except Exception as e:   # noqa: BLE001 — one provider failing never stops the exam
            put({'id': eid, 'name': name, 'kind': 'flagship', 'blocked': f'call failed: {type(e).__name__}'})
    exam['done'] = round(time.time())
    cv.ship(folder, exam, chosen)   # 🚦 Slice 7: shipped only if it beats the base model, and the exam says why either way
    (folder / 'exam.json').write_text(json.dumps(exam))
    cv.keep_history(folder, exam)   # 🏁 AGX-6: every finished exam joins the race


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--free']
    main(args[0] if args else cv.DATA, free='--free' in sys.argv[1:])
