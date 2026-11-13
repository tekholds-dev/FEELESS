"""📡 COMP LIVE (COMP-1, owner 2026-11-13: "realtime animations… real streamed numbers, no fakes"). Pure: turns what COMP already
writes to disk (COMP v2's train.log + exam.json, a Forge build's progress.json, the stash dataset counts) into ONE small frame the COMP
pages stream once a second. Nothing here invents a number: a value nothing measured is None and the page shows "—".
"""


def _last(pts):
    return pts[-1][1] if pts else None


def comp2_part(st):
    """COMP v2 · 9B: the LoRA run's live iter + loss (and the tail of the curve), the exam as it fills in."""
    st = st or {}
    run = st.get('run') or {}
    curve = run.get('curve') or {}
    train, val = curve.get('train') or [], curve.get('val') or []
    exam = st.get('exam') or {}
    exs = exam.get('examinees') or []
    done = [e for e in exs if (e.get('score') or {}).get('acc') is not None]
    best = max(done, key=lambda e: e['score']['acc'], default=None)
    comp = next((e for e in done if e.get('id') == 'comp'), None)
    base = next((e for e in done if e.get('id') == 'base'), None)
    return {
        'training': bool(run.get('running')), 'iter': curve.get('last') or 0, 'iters': run.get('iters') or 0,
        'loss': _last(train), 'val': _last(val), 'tail': [[i, v] for i, v in train[-60:]], 'valTail': [[i, v] for i, v in val[-20:]],
        'examining': bool(st.get('examRunning')), 'examN': exam.get('n') or 0, 'examAnswered': len(done), 'examTotal': len(exs),
        'best': {'id': best['id'], 'name': best.get('name') or best['id'], 'acc': best['score']['acc']} if best else None,
        'compAcc': (comp or {}).get('score', {}).get('acc'), 'baseAcc': (base or {}).get('score', {}).get('acc'),
        'won': ((st.get('dataset') or {}).get('won')), 'lost': ((st.get('dataset') or {}).get('lost')),
        'market': ({k: (st.get('market') or {}).get(k) for k in ('rows', 'open', 'won', 'lost', 'collects', 'at', 'nextSettle')} if isinstance(st.get('market'), dict) else None),
    }


def forge_part(job):
    """The from-scratch Forge build that is running (or the newest one): step, loss, tokens/second, ETA, its loss history tail."""
    if not job:
        return None
    hist = job.get('history') or []
    return {'id': job.get('id'), 'status': job.get('status'), 'live': job.get('status') in ('tokenizing', 'training'),
            'step': job.get('step'), 'steps': job.get('steps'), 'loss': job.get('loss'), 'val': job.get('val'), 'tps': job.get('tps'),
            'eta': job.get('eta'), 'elapsed': job.get('elapsed'), 'version': job.get('version'),
            'tail': [h for h in hist[-60:] if isinstance(h, (list, tuple, dict))]}


def frame(c2_status, forge_job, ds, now):
    """→ the frame: {'at', 'live', 'comp2', 'forge', 'data'}. `live` = something is training or sitting an exam right now."""
    c2 = comp2_part(c2_status)
    fg = forge_part(forge_job)
    ds = ds or {}
    data = {'rows': ds.get('rows'), 'pairs': ds.get('pairs'), 'graded': ds.get('graded'), 'open': ds.get('open'),
            'kinds': [{'kind': k.get('kind'), 'rows': k.get('rows', 0), 'won': k.get('won', 0), 'lost': k.get('lost', 0)} for k in ds.get('kinds') or []]}
    return {'at': round(now, 1), 'live': bool(c2['training'] or c2['examining'] or (fg and fg['live'])), 'comp2': c2, 'forge': fg, 'data': data}


def changed(a, b):
    """True when two frames differ in anything but the clock (the stream only sends a frame when a real number moved)."""
    if a is None or b is None:
        return True
    return {k: v for k, v in a.items() if k != 'at'} != {k: v for k, v in b.items() if k != 'at'}
