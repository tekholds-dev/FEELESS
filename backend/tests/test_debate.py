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
    import feecat_service as _fs_ss; monkeypatch.setattr(_fs_ss, 'SELF_START', True)   # the mechanic, dormant since owner 2026-11-14 (self-started usage discontinued)
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



def _two_on_the_table():
    st = {'table': [], 'offers': [], 'seats': {}, 'rooms': []}
    for cat, fid, frac in (('a', 'f1', .7), ('b', 'f2', .4)):
        r = cd.put(st, cat, cat.upper(), 'pob', {'id': fid, 'status': 'closed', 'topic': f'T {fid}'}, 'facts ' + fid, 'SECRET ' + fid); r['vitals'] = {'rank': 'B', 'score': frac * 300, 'top': 300, 'frac': frac, 'parts': [{'label': 'Result', 'value': frac}]}
    return st


def _full_room(st, now=1000.0, oa='oa', ob='ob'):
    ra, rb = [r['id'] for r in st['table'] if r['cat'] == 'a'][-1], [r['id'] for r in st['table'] if r['cat'] == 'b'][-1]
    room = cd.open_room(st, 'a', oa, 'A', ra, now=now); cd.join_room(st, room['id'], 'b', ob, 'B', rb, now=now + 1)
    return room


def test_a_room_runs_three_rounds_and_only_the_two_seated_read_the_proofs():
    st = _two_on_the_table(); room = _full_room(st); rid = room['id']
    with pytest.raises(ValueError):
        cd.say(st, rid, 'b', 'out of turn', now=1002)
    for i in range(6):
        cd.say(st, rid, 'ab'[i % 2], f'line number {i}', now=1002 + i)
    assert room['status'] == 'vote' and [x['round'] for x in room['said']] == ['Opening', 'Opening', 'Counter', 'Counter', 'Closer', 'Closer']
    a, out = cd.rooms_view(st, 'a', 'oa', now=1010)['rooms'][0], cd.rooms_view(st, 'c', 'oc', now=1010)['rooms'][0]
    assert 'SECRET f2' in a['b']['excerpt'] and out['b']['excerpt'] is None and out['a']['excerpt'] is None and 'oa' not in json.dumps(out) and out['canVote'] and not a['canVote']
    with pytest.raises(ValueError):
        cd.vote(st, rid, 'a', 'oa', 'a', True)
    with pytest.raises(ValueError):
        cd.vote(st, rid, 'c', 'oc', 'a', False)
    cd.concede(st, rid, 'a', 1)   # A says B made a point
    with pytest.raises(ValueError):
        cd.concede(st, rid, 'a', 0)   # nobody credits their own line
    for o in ('o1', 'o2', 'o3'):
        cd.vote(st, rid, 'v' + o, o, 'b', True)
    with pytest.raises(ValueError):
        cd.vote(st, rid, 'vo1', 'o1', 'b', True)
    assert cd.tick(st, now=1010) is False and cd.tick(st, now=1010 + cd.VOTE_S) is True
    assert room['points'] == {'a': {'finish': 5, 'better': 5}, 'b': {'finish': 5, 'point': 5, 'crowd': 10}} and room['winner'] == 'b' and room['totals'] == {'a': 10, 'b': 20}
    assert st['seats']['b']['points'] == 20 and st['seats']['b']['wins'] == 1 and st['seats']['vo1']['points'] == 1 and cd.tick(st, now=9e9) is False   # settled once


def test_rooms_cannot_be_farmed():
    st = _two_on_the_table(); ra = st['table'][0]['id']; rb = st['table'][1]['id']
    room = cd.open_room(st, 'a', 'oa', 'A', ra, now=1000)
    with pytest.raises(ValueError):
        cd.join_room(st, room['id'], 'b', 'oa', 'B', rb, now=1001)   # one owner cannot fill both seats
    with pytest.raises(ValueError):
        cd.open_room(st, 'a', 'oa', 'A', ra, now=1001)              # one slot waiting at a time
    with pytest.raises(ValueError):
        cd.pull(st, 'a', ra)                                         # a proof in a room stays on the table
    cd.join_room(st, room['id'], 'b', 'ob', 'B', rb, now=1002)
    for i in range(6):
        cd.say(st, room['id'], 'ab'[i % 2], 'a real line', now=1003 + i)
    cd.tick(st, now=1009 + cd.VOTE_S); first = st['seats']['a']['points']
    assert first == 10
    r2 = cd.put(st, 'a', 'A', 'pob', {'id': 'f3', 'status': 'closed', 'topic': 'x'}, '', ''); r3 = cd.put(st, 'b', 'B', 'pob', {'id': 'f4', 'status': 'closed', 'topic': 'y'}, '', '')
    again = cd.open_room(st, 'a', 'oa', 'A', r2['id'], now=2000); cd.join_room(st, again['id'], 'b', 'ob', 'B', r3['id'], now=2001)
    assert again['scored'] is False   # the same two owners score once a day
    for i in range(6):
        cd.say(st, again['id'], 'ab'[i % 2], 'another line', now=2002 + i)
    cd.tick(st, now=2008 + cd.VOTE_S); assert st['seats']['a']['points'] == first
    r4 = cd.put(st, 'a', 'A', 'pob', {'id': 'f5', 'status': 'closed', 'topic': 'z'}, '', ''); r5 = cd.put(st, 'a', 'A', 'pob', {'id': 'f6', 'status': 'closed', 'topic': 'w'}, '', '')
    third = cd.open_room(st, 'a', 'oa', 'A', r4['id'], now=3000); cd.leave_room(st, third['id'], 'a')
    cd.open_room(st, 'a', 'oa', 'A', r4['id'], now=3001); st['rooms'][-1].update(status='done')
    with pytest.raises(ValueError):
        cd.open_room(st, 'a', 'oa', 'A', r5['id'], now=3002)         # 3 rooms a day


def test_a_turn_not_taken_ends_the_room_and_the_one_who_left_gets_nothing():
    st = _two_on_the_table(); room = _full_room(st); cd.say(st, room['id'], 'a', 'my opening', now=1002)
    assert cd.tick(st, now=1002 + cd.TURN_S + 1) is True and room['gone'] == 'b' and room['winner'] == 'a' and room['totals'] == {'a': 5, 'b': 0}


def test_this_file_moves_nothing_itself():
    src = Path(cd.__file__).read_text()
    assert 'collective_stake' not in [n.name for x in ast.walk(ast.parse(src)) if isinstance(x, ast.Import) for n in x.names]
    assert 'pointsLeft' not in src and 'bonus(' not in src


def test_two_owners_get_in_a_room_on_the_real_route(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda who, op, **kw: c.post(f'/api/cats/{who}/work', json={'ownerId': who, 'session': who, 'op': op, **kw})
    store['cats']['b']['pobFolders'] = [{'id': 'f9', 'at': 6, 'status': 'closed', 'topic': 'MLB', 'graded': 'wrong'}]
    r = post('a', 'debate_room_open', tools={'kind': 'pob', 'fid': 'f1'}); assert r.status_code == 200, r.text
    rid = r.json()['room']['rooms'][0]['id']; assert r.json()['room']['rooms'][0]['a']['vitals']['rank']
    assert post('a', 'debate_room_join', tools={'kind': 'pob', 'fid': 'f1', 'room': rid}).status_code == 400   # its own room
    assert post('b', 'debate_room_open', tools={'kind': 'pob', 'fid': 'nope'}).status_code == 400   # not its proof
    r = post('b', 'debate_room_join', tools={'kind': 'pob', 'fid': 'f9', 'room': rid}); assert r.status_code == 200, r.text
    assert r.json()['room']['rooms'][0]['status'] == 'live' and r.json()['room']['rooms'][0]['turn'] == 'a'
    assert post('b', 'debate_room_say', tools={'room': rid, 'text': 'not my turn'}).status_code == 400
    assert post('a', 'debate_room_say', tools={'room': rid, 'text': 'my proof read the injury report'}).json()['room']['rooms'][0]['turn'] == 'b'


def _ledger(**sends):
    return {'cfg': {'cutPerX': 1, 'walletCapPct': 10, 'collectivePoolPct': 20, 'kneeUsd': 1000, 'sizeAbovePct': 50}, 'agents': {c: {'streams': [{'usd': usd, 'grade': 100}] if usd else [], 'owed': {}, 'earned': {}} for c, usd in sends.items()}}


def test_debate_raises_the_ceiling_only_with_a_stake_and_never_the_cut():
    import collective_stake as sk
    assert (cd.PT_USD, cd.MAX_PCT) == (sk.DEBATE_PT_USD, sk.DEBATE_MAX_PCT)
    st = _ledger(rich=100, empty=0); before = sk.of(st['agents']['rich'])
    assert sk.add_debate(st, 'k1', 'empty', 20, 1) == 0.0 and sk.of(st['agents']['empty'])['pointsLeft'] == 0   # no stake, nothing
    assert sk.add_debate(st, 'k1', 'ghost', 20, 1) == 0.0                                                       # not in the ledger
    assert sk.add_debate(st, 'k1', 'rich', 20, 1) == 1.0 and sk.add_debate(st, 'k1', 'rich', 20, 2) == 0.0     # 20 x $0.05, one room once
    after = sk.of(st['agents']['rich'])
    assert after['capUsd'] == before['capUsd'] + 1.0 and after['x'] == before['x'] and after['sentUsd'] == before['sentUsd']
    for i in range(5000):
        sk.add_debate(st, f'r{i}', 'rich', 25, 1)
    assert sk.of(st['agents']['rich'])['debateUsd'] == before['capUsd'] * .25                                   # farming stops at 25%
    assert sk.add_debate(st, 'more', 'rich', 25, 1) == 0.0


def test_a_room_banks_once_and_only_with_a_stake_on_both_sides(monkeypatch, tmp_path):
    import collective_pool as cp
    import collective_stake as sk
    fs = pytest.importorskip('feecat_service')
    path = tmp_path / 'pool.json'; monkeypatch.setattr(fs, 'POOL_PATH', path)
    cp.update(path, lambda s: s['agents'].update({'a': {'streams': [{'usd': 100, 'grade': 100}], 'owed': {}, 'earned': {}}}))
    st = _two_on_the_table(); room = _full_room(st); cd.say(st, room['id'], 'a', 'my opening', now=1002); cd.tick(st, now=1002 + cd.TURN_S + 1)
    assert fs._debate_bank(st) and room['banked'] == {}   # the other seat has no stake: a record only
    assert cp.load(path)['agents']['a'].get('debateUsd') is None and fs._debate_bank(st) is False
    cp.update(path, lambda s: s['agents'].update({'b': {'streams': [{'usd': 50, 'grade': 100}], 'owed': {}, 'earned': {}}}))
    st = _two_on_the_table(); room = _full_room(st); cd.say(st, room['id'], 'a', 'my opening', now=1002); cd.tick(st, now=1002 + cd.TURN_S + 1)
    assert fs._debate_bank(st) and room['banked'] == {'a': .25, 'b': 0.0} and fs._debate_bank(st) is False      # +5 for finishing, only the seat that stayed
    assert sk.of(cp.load(path)['agents']['a'])['debateUsd'] == .25 and 'debateUsd' not in cp.load(path)['agents']['b']
