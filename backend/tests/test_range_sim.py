import math

import range_sim as rs


def flat(n=100, fee=0.0005):
    return [{'t': i, 'a': 100.0, 'b': 1.0, 'fee': fee} for i in range(n)]


def test_with_no_price_move_a_tighter_band_earns_more_fees():
    wide, tight = rs.replay(flat(), 40), rs.replay(flat(), 5)
    assert tight['pct'] > wide['pct'] > 0 and tight['inRange'] == 100 and tight['moves'] == 0
    assert rs.concentration(5) > rs.concentration(40) > 1


def test_a_price_that_runs_away_earns_nothing_and_costs_a_recenter():
    rows = [{'t': i, 'a': 100.0 * 1.01 ** i, 'b': 1.0, 'fee': 0.00002} for i in range(100)]
    r = rs.replay(rows, 2, wait=1); assert r['moves'] > 5 and r['pct'] < r['holdPct']   # selling the winner each time loses to holding
    never = rs.replay(rows, 2, wait=9999); assert never['moves'] == 0 and never['inRange'] < 10


def test_full_range_math_and_hold_are_right():
    rows = [{'t': 0, 'a': 100.0, 'b': 1.0, 'fee': 0.0}, {'t': 1, 'a': 110.0, 'b': 1.0, 'fee': 0.0}, {'t': 2, 'a': 121.0, 'b': 1.0, 'fee': 0.0}]
    r = rs.replay(rows, 40); assert r['holdPct'] == 10.5 and r['fullPct'] == 10.0
    assert rs.replay([], 5) is None and rs.walk_forward(flat(20)) is None


def test_the_band_is_chosen_on_old_hours_and_scored_on_new_ones():
    w = rs.walk_forward(flat(100)); assert w['hours'] == 50 and w['width'] == 2 and w['pct'] > 0
    assert math.isclose(rs.sweep(flat(40))[0]['pct'], max(x['pct'] for x in rs.sweep(flat(40))))


def test_ideas_are_only_words_and_a_refused_one_is_not_asked_twice(tmp_path):
    import idea_board as ib
    good = '{"ideas":[{"topic":"money","title":"Stable band floor for the Pool","what":"Keep idle cash in tight stable bands","why":"6 of 6 stable pools beat holding","test":"Paper it a week"},{"title":"","what":"x"},{"topic":"nope","title":"Debate leaderboard rewards","what":"Show who grades best"}]}'
    rows = ib.parse(good, [], 'OSSY', 1.0); assert [r['title'] for r in rows] == ['Stable band floor for the Pool', 'Debate leaderboard rewards'] and rows[1]['topic'] == 'mechanics' and rows[0]['mark'] == 'new'
    assert ib.parse(good, rows, 'G4', 2.0) == [] and ib.parse('nothing', [], 'G4', 2.0) == []
    ib.mark(rows, rows[0]['id'], 'bad'); ib.mark(rows, rows[1]['id'], 'build'); ib.save(tmp_path, rows); assert ib.load(tmp_path)[0]['mark'] == 'bad'
    m = ib.memory(rows); assert 'refused: Stable band' in m and 'liked: Debate' in m
    try:
        ib.mark(rows, 'gone', 'good'); assert False
    except ValueError:
        pass


def test_ideas_are_the_owners_and_thinking_cost_comes_from_receipts(monkeypatch, tmp_path):
    import json
    import pytest
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'g', 'revoked': False, 'brainsCfg': {}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'KITS_DIR', tmp_path / 'k')
    assert TestClient(fs.app).post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': 'ideas_get'}).status_code == 403
    (tmp_path / 'model_receipts.jsonl').write_text('\n'.join(json.dumps(r) for r in [{'cat': 'g', 'at': 1e7, 'usd': 1.0}, {'cat': 'g', 'at': 1e7 + 86400, 'usd': 1.0}, {'cat': 'x', 'at': 1e7, 'usd': 9.0}, {'cat': 'g', 'at': 1.0, 'usd': 5.0}]))
    t = fs._wallet_think('g', now=1e7 + 2 * 86400); assert t['usd'] == 2 and t['calls'] == 2 and t['perDay'] == 1 and fs._wallet_think('none')['calls'] == 0
    f = json.loads(fs._idea_facts({'cats': {'g': {'id': 'g', 'psFolders': [{'graded': 'right', 'ownerWallet': 'SECRET'}]}}})); assert f['proofs']['pos'] == {'filed': 1, 'right': 1, 'wrong': 0} and 'SECRET' not in json.dumps(f)
