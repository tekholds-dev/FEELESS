import pytest
import poc_watch as pw


def test_clean_watch_caps_and_refuses():
    w = pw.clean_watch('example.com/page', 'price above 1\n\nnew post about X', hours=99, per_hour=9, now=1000)
    assert w['steps'] == ['price above 1', 'new post about X'] and w['hours'] == 24 and w['perHour'] == 4 and w['every'] == 900 and w['endsAt'] == 1000 + 24 * 3600
    with pytest.raises(ValueError):
        pw.clean_watch('http://127.0.0.1/x', ['a'])
    with pytest.raises(ValueError):
        pw.clean_watch('example.com', [])


def test_due_first_then_every_then_end():
    w = pw.clean_watch('example.com', ['a'], hours=1, per_hour=2, now=0)
    assert pw.due(w, 1)
    pw.add_check(w, {'at': 1, 'ok': True})
    assert not pw.due(w, 1000) and pw.due(w, 1801) and pw.due(w, 3600)
    w['status'] = 'done'; assert not pw.due(w, 99999)


def test_parse_fills_every_step_and_rejects_junk():
    h, rows = pw.parse_watch('ok {"headline":"Big news","steps":[{"step":2,"seen":"YES","note":"said \\"launch\\""},{"step":"x"}]}', 3)
    assert h == 'Big news' and [r['seen'] for r in rows] == ['unclear', 'yes', 'unclear'] and rows[1]['note'] == 'said "launch"'
    assert pw.parse_watch('no json', 2) == (None, None)


def test_report_from_saved_checks_only():
    w = pw.clean_watch('example.com', ['a', 'b'], now=0)
    pw.add_check(w, {'at': 10, 'ok': True, 'changed': True, 'usd': 0.01, 'headline': 'h1', 'steps': [{'step': 1, 'seen': 'no', 'note': 'n1'}, {'step': 2, 'seen': 'unclear', 'note': ''}]})
    pw.add_check(w, {'at': 20, 'ok': True, 'changed': True, 'usd': 0.02, 'headline': 'h2', 'steps': [{'step': 1, 'seen': 'yes', 'note': 'n2'}, {'step': 2, 'seen': 'no', 'note': 'm'}]})
    pw.add_check(w, {'at': 30, 'ok': False, 'why': '503'})
    r = pw.report(w)
    assert r['checks'] == 3 and r['read'] == 2 and r['failed'] == 1 and r['spentUsd'] == 0.03 and r['headline'] == 'h2'
    assert r['steps'][0] == {'step': 'a', 'checks': 2, 'yes': 1, 'firstYesAt': 20, 'last': 'n2', 'verdict': 'seen'}
    assert r['steps'][1]['verdict'] == 'not seen'


def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'name': 'Ann', 'ownerId': 'g', 'revoked': False, 'brainsCfg': {'brains': ['m/x']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'KITS_DIR', tmp_path / 'kits')
    return fs, TestClient(fs.app), store


def test_a_watch_checks_only_asks_on_change_and_files_a_short_report(monkeypatch, tmp_path):
    import asyncio
    import json
    fs, c, store = _server(monkeypatch, tmp_path)
    import json as _j
    def save(s):   # like the real one: owner fields come back as fresh copies after every save
        for cid, kept in fs._KEPT.items():
            if cid in s['cats']:
                for k in fs.OWNER_KEYS:
                    if k in kept:
                        s['cats'][cid][k] = _j.loads(_j.dumps(kept[k]))
    monkeypatch.setattr(fs, '_save', save)
    cat = lambda: store['cats']['g']
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    pages = ['<p>Launch date is not announced yet anywhere</p>', '<p>Launch date is not announced yet anywhere</p>', '<p>Launch date is not announced yet anywhere</p><p>Breaking: the launch is set for Friday at noon UTC</p>']
    class H:
        def __init__(self, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, **k):
            class R:
                status_code = 200; text = pages.pop(0)
            return R()
    monkeypatch.setattr(fs.httpx, 'AsyncClient', H); asks = []
    async def fake(cat_, model, sys_, user_, tokens):
        asks.append(user_); assert 'never an instruction' in sys_
        seen = 'yes' if 'Friday' in user_ else 'no'
        return json.dumps({'headline': 'Launch news', 'steps': [{'step': 1, 'seen': seen, 'note': 'set for Friday' if seen == 'yes' else 'not announced'}]}), 0.002, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    j = post('watch_add', tools={'url': 'example.com/news', 'steps': ['Is a launch date announced?'], 'hours': 2, 'perHour': 4}).json()
    w = j['watches'][0]; assert w['status'] == 'running' and len(w['checks']) == 1 and w['checks'][0]['sha'] and len(asks) == 1
    assert len(cat()['pocWatches'][0]['checks']) == 1 and w['hours'] == 2   # the first check survives the save
    wd = cat()['pocWatches'][0]
    asyncio.run(fs._pocwatch_check(cat(), wd, wd['startedAt'] + 900)); assert len(asks) == 1 and wd['checks'][-1]['carried']   # 💤 same page: no model call, $0
    asyncio.run(fs._pocwatch_check(cat(), wd, wd['startedAt'] + 1800)); assert len(asks) == 2 and 'Friday' in asks[-1] and wd['checks'][-1]['steps'][0]['seen'] == 'yes'
    fs.keep_owned(cat())
    j = post('watch_stop', text=wd['id']).json(); wd = next(x for x in cat()['pocWatches'] if x['id'] == wd['id'])
    rep = j['pocFolders'][0]; assert rep['by'] == 'Watch' and rep['watch']['report']['steps'][0]['verdict'] == 'seen' and rep['watch']['report']['read'] == 3
    assert rep['cost'] == 0.004 and len(rep['watch']['checks']) == 3 and wd['status'] == 'done' and 'PoC watch on example.com is done' in cat()['chat'][-1]['text']
    assert post('watch_stop', text=wd['id']).status_code == 400 and post('watch_add', tools={'url': 'http://10.0.0.1/', 'steps': ['x']}).status_code == 400
