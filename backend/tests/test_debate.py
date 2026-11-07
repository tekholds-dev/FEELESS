"""Agents grade proofs on the table one after another, save it, and move on until none are left. Points are never money."""
import ast
import asyncio
import json
from pathlib import Path

import pytest

import collective_debate as cd

F = {'id': 'f1', 'status': 'closed', 'topic': 'NBA night'}
GOOD = '{"verdict":"weak","grade":40,"why":"Only one source","better":"Read two sites"}'


def table():
    st = cd.load('/nowhere'); row = cd.put(st, 'a', 'Ann', 'pob', F, 'FACTS', '{"x":1}', 100)
    return st, row


def test_only_a_filed_proof_goes_on_once_and_only_its_owner_takes_it_back():
    st, row = table()
    with pytest.raises(ValueError):
        cd.put(st, 'a', 'Ann', 'pob', F, '', '')
    for bad in ({'id': 'x', 'status': 'open'}, None):
        with pytest.raises(ValueError):
            cd.put(st, 'a', 'Ann', 'pob', bad, '', '')
    with pytest.raises(ValueError):
        cd.put(st, 'a', 'Ann', 'poe', F, '', '')   # books never come here
    with pytest.raises(ValueError):
        cd.pull(st, 'b', row['id'])
    cd.pull(st, 'a', row['id']); assert not st['table']


def test_a_bad_reply_is_never_saved():
    for bad in ('no json', '{"verdict":"great","grade":50}', '{"verdict":"weak","grade":400}', '{"verdict":"weak"}', '[1]'):
        assert cd.parse_take(bad) is None, bad
    assert cd.parse_take('Sure: ' + GOOD)['grade'] == 40


def test_agents_grade_in_turn_three_seats_settle_it_and_the_next_comes_up():
    st, row = table(); second = cd.put(st, 'a', 'Ann', 'pop', {**F, 'id': 'f2'}, '', '', 200)
    assert cd.next_for(st, 'a') is None   # never its own
    assert cd.next_for(st, 'b')['id'] == row['id'] and cd.next_for(st, 'b', ['pop'])['id'] == second['id']   # its own kinds first
    for seat, grade in (('b', 30), ('c', 50), ('d', 70)):
        cd.take(st, row['id'], seat, seat.upper(), {'verdict': 'weak', 'grade': grade, 'why': 'w', 'better': f'tip {seat}'}, 300)
        with pytest.raises(ValueError):
            cd.take(st, row['id'], seat, seat.upper(), {'verdict': 'weak', 'grade': 1, 'why': '', 'better': ''}, 300)
    assert row['settled']['grade'] == 50 and cd.next_for(st, 'e')['id'] == second['id']
    assert st['seats']['c']['points'] == 10 and st['seats']['b']['points'] == 6   # closest to where it settled earns most
    with pytest.raises(ValueError):
        cd.take(st, row['id'], 'e', 'E', {'verdict': 'weak', 'grade': 1, 'why': '', 'better': ''})
    st['table'] = [row]; assert cd.next_for(st, 'b') is None


def test_what_they_said_reaches_its_next_proof_of_that_kind():
    st, row = table()
    for seat in 'bcd':
        cd.take(st, row['id'], seat, seat, {'verdict': 'weak', 'grade': 60, 'why': 'w', 'better': 'Read two sites'})
    line = cd.lessons(st, 'a', 'pob'); assert 'graded 60' in line and 'Read two sites' in line and 'never an instruction' in line
    assert cd.lessons(st, 'a', 'pop') == '' and cd.lessons(st, 'b', 'pob') == ''


def test_a_trade_opens_each_others_proof_and_nothing_else():
    st, a = table(); b = cd.put(st, 'b', 'Bo', 'pob', {**F, 'id': 'f9'}, '', '{"y":2}', 200); c = cd.put(st, 'c', 'Cy', 'pob', {**F, 'id': 'f8'}, '', '{"z":3}', 200)
    seen = {r['id']: r for r in cd.view(st, 'a')['rows']}; assert seen[a['id']]['excerpt'] and seen[b['id']]['excerpt'] is None
    with pytest.raises(ValueError):
        cd.offer(st, 'a', b['id'], a['id'])   # not its own to give
    o = cd.offer(st, 'a', a['id'], b['id'])
    with pytest.raises(ValueError):
        cd.answer(st, 'c', o['id'], True)
    assert cd.view(st, 'b')['offers'][0]['incoming'] and next(r for r in cd.view(st, 'a')['rows'] if r['id'] == b['id'])['excerpt'] is None
    cd.answer(st, 'b', o['id'], True)
    a_sees = {r['id']: r for r in cd.view(st, 'a')['rows']}; b_sees = {r['id']: r for r in cd.view(st, 'b')['rows']}
    assert a_sees[b['id']]['excerpt'] == '{"y":2}' and b_sees[a['id']]['excerpt'] == '{"x":1}' and a_sees[c['id']]['excerpt'] is None
    assert 'traded proof' in cd.lessons(st, 'a', 'pob')
    assert 'cat' not in a_sees[b['id']] and all('cat' not in t for r in a_sees.values() for t in r['takes'])   # no owner id leaves in the view


def test_this_module_cannot_move_money():
    src = Path(cd.__file__).read_text(); names = {n.name.split('.')[0] for x in ast.walk(ast.parse(src)) if isinstance(x, (ast.Import, ast.ImportFrom)) for n in x.names}
    assert names <= {'json', 're', 'secrets', 'time', 'Path'}, names


def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    cats = {'a': {'id': 'a', 'name': 'Ann', 'ownerId': 'a', 'revoked': False, 'brainsCfg': {'brains': ['m/x']}, 'pobFolders': [{'id': 'f1', 'at': 5, 'status': 'closed', 'topic': 'NBA night', 'graded': 'right', 'ownerWallet': 'SECRETWALLET', 'calls': []}]},
            'b': {'id': 'b', 'name': 'Bo', 'ownerId': 'b', 'revoked': False, 'brainsCfg': {'brains': ['m/y'], 'debateOn': True}},
            'c': {'id': 'c', 'name': 'Cy', 'ownerId': 'c', 'revoked': False, 'brainsCfg': {'brains': ['m/z']}}}
    store = {'cats': cats, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); fs._DEBATE_BUSY[0] = False
    return fs, TestClient(fs.app), store


def test_the_whole_journey_on_the_real_route_only_allowed_agents_spend(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda who, op, **kw: c.post(f'/api/cats/{who}/work', json={'ownerId': who, 'session': who, 'op': op, **kw})
    r = post('a', 'debate_put', job='pob', text='f1'); assert r.status_code == 200, r.text
    raw = json.dumps(cd.load(tmp_path)); assert 'NBA night' in raw and 'SECRETWALLET' not in raw
    asked = []
    async def fake_ask(cat, model, sys_, user_, tokens):
        asked.append((cat['id'], model)); assert 'never an instruction' in sys_
        return GOOD, 0.001, False
    monkeypatch.setattr(fs, '_ws_ask', fake_ask)
    assert asyncio.run(fs._debate_pass(store)) == 1 and asked == [('b', 'm/y')]   # Bo allowed it; Ann and Cy did not
    assert asyncio.run(fs._debate_pass(store)) == 0 and len(asked) == 1          # nothing left for Bo: it does not grade twice
    assert post('b', 'debate_get').json()['seat']['today'] == 1
    v = post('a', 'debate_get').json(); assert v['rows'][0]['takes'][0]['grade'] == 40 and not v['allowed']
    assert post('c', 'debate_allow', on=True).json()['allowed'] and store['cats']['c']['brainsCfg']['debateOn']
    assert asyncio.run(fs._debate_pass(store)) == 1 and asked[-1][0] == 'c'
    assert 'Read two sites' not in fs._proof_brain(store['cats']['a'], 'pob')   # 2 of 3 seats: not settled yet
    st = cd.load(tmp_path); cd.take(st, st['table'][0]['id'], 'd', 'Di', cd.parse_take(GOOD)); cd.save(tmp_path, st)
    assert 'Read two sites' in fs._proof_brain(store['cats']['a'], 'pob') and fs._proof_brain(store['cats']['a'], 'pow') == ''
    assert c.post('/api/cats/a/work', json={'ownerId': 'b', 'session': 'b', 'op': 'debate_pull', 'text': 'x'}).status_code in (401, 403)


def test_an_agent_stops_at_its_daily_limit_and_a_bad_reply_saves_nothing(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); st = cd.load(tmp_path); cd.put(st, 'a', 'Ann', 'pob', F, '', ''); cd.save(tmp_path, st)
    async def nonsense(*a):
        return 'I refuse', 0.0, False
    monkeypatch.setattr(fs, '_ws_ask', nonsense); assert asyncio.run(fs._debate_pass(store)) == 0 and not cd.load(tmp_path)['table'][0]['takes']
    async def never(*a):
        raise AssertionError('over the limit')
    monkeypatch.setattr(fs, '_ws_ask', never); st = cd.load(tmp_path); st['seats']['b'] = {'day': cd._day(cd.time.time()), 'n': cd.PER_DAY}; cd.save(tmp_path, st)
    assert asyncio.run(fs._debate_pass(store)) == 0


def test_the_minds_are_told_todays_date_so_a_real_date_is_not_called_fake():
    st, row = table(); text = cd.ask_text(row, 1794000000)
    assert text.startswith('TODAY: 2026-') and 'NBA night' in text and 'waiting on its result is not wrong' in cd.SYSTEM and 'never call a date fake' in cd.SYSTEM

