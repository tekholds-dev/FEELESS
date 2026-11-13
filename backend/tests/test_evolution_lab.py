"""COL-11 Evolution Lab: frozen baseline vs a challenger fit on the past only, judged on held-out exits; gate, rollback, history. Fake paths, no network."""
import evolution_lab as ev
import office as of

TUNE = of.TUNABLE['reaper']
BASE = {k: v[0] for k, v in TUNE.items()}


def pos(i, path):
    return {'sym': f'C{i}', 'closedAt': 1000 + i, 'path': path}


def runner_book(n=60):
    """Coins that run to +12 then give most of it back: a tighter give-back banks more, in the past AND the future."""
    return [pos(i, [2, 5, 9, 12, 8, 4, 1, -3]) for i in range(n)]


def test_split_is_chronological_and_the_held_out_is_never_searched():
    ps = runner_book(10)[::-1]
    learn, held = ev.split(ps)
    assert [p['closedAt'] for p in learn] == list(range(1000, 1006)) and [p['closedAt'] for p in held] == list(range(1006, 1010))


def test_a_real_edge_on_unseen_exits_is_promoted_and_frozen_with_a_hash():
    ledger = []
    j = ev.run(ledger, 'reaper', BASE, TUNE, runner_book(), of.reaper_replay, 50.0, now=1)
    assert j['verdict'] == 'PROMOTE' and j['held']['edge'] >= ev.EDGE_PTS and j['changed'] >= ev.MIN_CHANGED
    assert [e['action'] for e in ledger] == ['freeze', 'challenge', 'promote']
    assert ledger[0]['hash'] == ev.phash(BASE) and ledger[-1]['gen'] == 2
    assert all(r['chall'] != r['base'] for r in j['shadow'])   # shadow trades are only the exits that changed


def test_one_lucky_trade_is_never_learning():
    ps = [pos(i, [1, -1]) for i in range(59)] + [pos(99, [2, 5, 9, 12, 8, 4, 1, -3])]
    ledger = []
    j = ev.run(ledger, 'reaper', BASE, TUNE, ps, of.reaper_replay, 50.0, now=1)
    assert j['verdict'] in ('HOLD', 'REJECT') and 'promote' not in [e['action'] for e in ledger]


def test_too_few_held_out_exits_holds():
    j = ev.judge(BASE, {**BASE, 'giveBackPct': 30.0}, runner_book(10), of.reaper_replay, 50.0)
    assert j['verdict'] == 'HOLD' and 'too few' in j['why']


def test_fit_the_past_not_the_future_is_rejected():
    past = [pos(i, [2, 5, 9, 12, 8, 4, 1, -3]) for i in range(36)]
    future = [pos(100 + i, [2, 7, 4, 9, 15, 25]) for i in range(24)]   # here a tight give-back sells the winner early
    j = ev.judge(BASE, {**BASE, 'giveBackPct': 30.0, 'protectAt': 4.0}, past + future, of.reaper_replay, 50.0)
    assert j['verdict'] == 'REJECT' and j['held']['edge'] < 0


def test_rollback_restores_the_previous_generation_and_history_is_append_only():
    ledger = []
    ev.run(ledger, 'reaper', BASE, TUNE, runner_book(), of.reaper_replay, 50.0, now=1)
    n = len(ledger); before = [dict(e) for e in ledger]
    row = ev.rollback(ledger, now=2)
    assert row['hash'] == ev.phash(BASE) and ev.baseline(ledger)['params'] == BASE and row['gen'] == 3
    assert ledger[:n] == before   # nothing earlier was rewritten
    assert ev.history(ledger)[0]['action'] == 'rollback'
    assert ev.rollback([ledger[0]], now=3) is None


def test_the_route_runs_on_the_sandboxed_archive_and_never_touches_live_tunables(monkeypatch, tmp_path):
    import json
    import reputation_service as rs
    from fastapi.testclient import TestClient
    monkeypatch.setattr(rs, 'ARCHIVE_PATH', tmp_path / 'arch.json'); monkeypatch.setattr(rs, 'EVO_PATH', tmp_path / 'evo.json'); monkeypatch.setattr(rs, 'FUSE_HQ_PATH', tmp_path / 'hq.json')
    (tmp_path / 'arch.json').write_text(json.dumps({'positions': [pos(i, [2, 5, 9, 6, 3, 1, -3]) for i in range(60)]})); rs._evo_memo.clear()
    live_before = dict(of.TUNABLE['reaper'])
    r = TestClient(rs.app).get('/api/reputation/evolution/reaper')
    assert r.status_code == 200, r.text
    d = r.json(); assert d['exits'] == 60 and d['judge']['verdict'] == 'PROMOTE' and d['baseline']['action'] == 'promote'
    assert [e['action'] for e in d['history']][:3] == ['promote', 'challenge', 'freeze']
    assert of.TUNABLE['reaper'] == live_before   # the lab never writes live trading rules
    rs._evo_memo.clear(); again = TestClient(rs.app).get('/api/reputation/evolution/reaper').json()
    assert len(again['history']) == 3   # same exits, no new pass appended
    assert TestClient(rs.app).get('/api/reputation/evolution/scout').status_code == 404
    assert TestClient(rs.app).post('/api/reputation/admin/evolution/reaper/rollback').status_code in (401, 403)
