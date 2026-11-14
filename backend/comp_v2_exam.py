"""🎓 COMP v2 exam — run under .venv-mlx: `.venv-mlx/bin/python backend/comp_v2_exam.py backend/data/comp_v2`.

Every examinee answers the same held-out proofs (test_rows.json, never trained on): the base Qwen3.5-9B, COMP v2 (base + the owner's
LoRA adapter), the always-the-majority baseline, the owner's own OSSY + G4 (each on its own LM Studio, never a fallback), and the flagship APIs when their key is in backend/.env (Claude via the Anthropic SDK,
GPT and Grok via their HTTP APIs). A flagship with no key is listed as blocked, never scored. exam.json is rewritten after each examinee.
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
                                                               'LAN_LLM_BASE_URL', 'LAN_LLM_MODEL', 'LAN_LLM_API_KEY')}


def own_minds(keys):
    """🖥 AGX-6: the owner's two judges sit the same exam, each on ITS OWN LM Studio only (never a fallback model, never a paid API):
    OSSY = LM Studio on this Mac, G4 = LM Studio on the desktop Mac (LAN). → [(id, name, base, model, key, why_blocked)]"""
    on = str(keys.get('LOCAL_LLM_ENABLED') or '').strip().lower() in ('1', 'true', 'yes', 'on')
    ossy_base = (keys.get('LOCAL_LLM_BASE_URL') or 'http://127.0.0.1:1234/v1').rstrip('/')
    g4_base = (keys.get('LAN_LLM_BASE_URL') or '').rstrip('/')
    return [('ossy', f"OSSY · {(keys.get('LOCAL_LLM_MODEL') or 'qwen2.5-7b-instruct-mlx').split('/')[-1]}", ossy_base, keys.get('LOCAL_LLM_MODEL') or 'qwen2.5-7b-instruct-mlx',
             keys.get('LOCAL_LLM_API_KEY') or '', None if on else 'off: LOCAL_LLM_ENABLED is not true'),
            ('g4', f"G4 · {(keys.get('LAN_LLM_MODEL') or 'qwen/qwen3.5-4b').split('/')[-1]}", g4_base, keys.get('LAN_LLM_MODEL') or 'qwen/qwen3.5-4b',
             keys.get('LAN_LLM_API_KEY') or '', None if g4_base else 'off: LAN_LLM_BASE_URL is not set')]


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
                {'role': 'system', 'content': cv.SYSTEM}, {'role': 'user', 'content': cv.prompt_of(r)}]})
            res.raise_for_status()
            out.append(cv.answer_of(res.json()['choices'][0]['message']['content']))
    return out


def main(folder):
    folder = Path(folder)
    rows = json.loads((folder / 'test_rows.json').read_text())
    train = [{'outcome': m['messages'][2]['content']} for m in map(json.loads, (folder / 'train.jsonl').read_text().splitlines())]
    exam = {'at': round(time.time()), 'n': len(rows), 'task': 'won or lost, from what the proof said before it settled', 'examinees': []}

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
    qs = rows[:min(MAX_FLAGSHIP_Q, int(_gr.value(g_, 'compFlagships')))]   # the PAID flagships' questions
    own_qs = rows[:MAX_FLAGSHIP_Q]   # OSSY + G4 are free: the paid switch never limits them
    for eid, name, base, model, key, why in own_minds(keys):   # 🖥 OSSY + G4: free, on the owner's own machines
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
    for eid, name, var, run in flag:
        if not qs:
            put({'id': eid, 'name': name, 'kind': 'flagship', 'blocked': 'off in your guardrails'}); continue
        if not keys[var]:
            put({'id': eid, 'name': name, 'kind': 'flagship', 'blocked': 'no key: add it in HQ › Agents'}); continue
        try:
            put({'id': eid, 'name': name, 'kind': 'flagship', 'score': cv.score(qs, run(keys[var]))})
        except Exception as e:   # noqa: BLE001 — one provider failing never stops the exam
            put({'id': eid, 'name': name, 'kind': 'flagship', 'blocked': f'call failed: {type(e).__name__}'})
    exam['done'] = round(time.time())
    (folder / 'exam.json').write_text(json.dumps(exam))
    cv.keep_history(folder, exam)   # 🏁 AGX-6: every finished exam joins the race


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else cv.DATA)
