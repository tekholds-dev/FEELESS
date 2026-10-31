"""🐝 The Colony (owner 2026-10-31): graded trades, the FEECAT stake gate, and the pot's guards — growth only, honey split, never a send."""
import asyncio

import colony as col
import hive as hv


def test_the_pot_only_pays_growth_under_the_epoch_cap_and_the_floor_only_rises():
    assert col.growth(1200, 1000) == 200 and col.growth(900, 1000) == 0          # a dip pays nothing, never principal
    assert col.payable(1200, 1000, {'epochCapPct': 20}) == 40                     # 20 % of the growth leaves this epoch
    assert col.payable(1200, 1000, {'epochCapPct': 99}) == 100                     # the cap is clamped to 50 %
    assert col.raise_floor(1000, 1200) == 1200 and col.raise_floor(1200, 900) == 1200   # lock gains in; it never goes down
    assert col.clean_policy({'timelockH': 1}) == {'epochCapPct': 20, 'timelockH': 6}
    assert set(col.FIXED_GUARDS) == {'principalLock', 'allowlist', 'ownerSigns'}


def test_payouts_follow_honey_and_skip_agents_without_an_owner_wallet():
    board = [{'cat': 'a', 'name': 'A', 'honey': 6}, {'cat': 'b', 'name': 'B', 'honey': 2}, {'cat': 'c', 'name': 'C', 'honey': 4}, {'cat': 'd', 'honey': -3}]
    out = col.split(board, {'a': 'WA', 'b': 'WB', 'd': 'WD'}, 80)   # c has no owner wallet (staff / Fee): left out
    assert [(r['cat'], r['usd'], r['pct']) for r in out] == [('a', 60.0, 75.0), ('b', 20.0, 25.0)]
    assert col.split(board, {}, 80) == [] and col.stake_ok(24.99) is False and col.stake_ok(25) and col.stake_ok(0, staff=True)


def test_an_entry_is_a_buy_cell_and_an_exit_an_avoid_cell_graded_like_any_other():
    cat = {'id': 'k1', 'name': 'Kit'}; pos = {'pairAddress': 'PAIR123456789', 'symbol': 'HUSS', 'mint': 'M'}
    e = col.trade_cell(cat, 'buy', pos, 0.01, 1_800_000_000); x = col.trade_cell(cat, 'sell', pos, 0.02, 1_800_000_100)
    assert (e['call'], e['kind'], x['call'], x['kind']) == ('BUY', 'entry', 'AVOID', 'exit')
    assert hv.grade(x, 0.014, 1_800_003_800) == 2 and x['move'] == -30.0   # it fell 30 % after the exit: a great exit
    assert col.trade_cell(cat, 'buy', pos, 0, 1) is None and col.trade_cell(cat, 'buy', {}, 1, 1) is None


def test_a_colonized_agents_buy_files_a_cell_and_the_switch_needs_the_feecat_stake(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'k1', 'name': 'Kit', 'hive': {'on': True}, 'brainsCfg': {'brains': ['m/a']}}
    fs._colony_trade(cat, 'buy', {'pairAddress': 'P1', 'symbol': 'HUSS'}, 0.01)
    fs._colony_trade({**cat, 'hive': {'on': False}}, 'buy', {'pairAddress': 'P2', 'symbol': 'X'}, 0.01)   # not colonized: nothing filed
    cells = fs._hive_cells(); assert len(cells) == 1 and cells[0]['kind'] == 'entry' and cells[0]['epoch'] == hv.epoch_of(cells[0]['at'])
    src = open(fs.__file__).read()
    i = src.index("if p.op == 'hive':"); assert '_colony.stake_ok(usd_)' in src[i:i + 900] and '402' in src[i:i + 900]


def test_the_colony_feed_for_the_pot_is_internal_and_names_browsers_never_keys(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    store = {'cats': {'k1': {'id': 'k1', 'name': 'Kit', 'ownerWallet': 'W1', 'hive': {'on': True}, 'brainsCfg': {'brains': ['m']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store)
    monkeypatch.setenv('KERNEL_API_KEY', 'sk_secret_value'); (fs.DATA_DIR / 'internal.key').write_text('test-internal')
    c = TestClient(fs.app)
    assert c.get('/api/cats/internal/colony').status_code == 403
    r = c.get('/api/cats/internal/colony', headers=fs._internal_headers()).json()
    assert r['owners'] == {'k1': 'W1'} and r['colonized'] == 1 and r['browsers'][0] == 'kernel' and 'sk_secret' not in str(r)


def test_the_colony_page_lists_agents_colonized_first_nine_a_page_never_a_secret(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cats = {f'c{i}': {'id': f'c{i}', 'name': f'Cat {i}', 'ownerWallet': 'OWNER_W', 'brainsCfg': {'kind': 'general', 'brains': ['openai/gpt-x:free', 'm/b']}, 'secrets': {'k': 'hunter2'}} for i in range(12)}
    cats['c7']['hive'] = {'on': True}
    store = {'cats': cats, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store)
    c = TestClient(fs.app)
    j = c.get('/api/cats/colony').json()
    assert len(j['agents']) == 9 and j['more'] is True and j['agents'][0]['id'] == 'c7' and j['agents'][0]['colonized'] and j['agents'][0]['brains'][0] == 'gpt-x'
    assert len(c.get('/api/cats/colony?page=1').json()['agents']) == 3
    t = c.get('/api/cats/colony').text; assert 'hunter2' not in t and 'OWNER_W' not in t


def test_a_visitor_sees_its_colony_vitals_beside_the_windows(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import time as _t
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    now = _t.time(); fs._hive_save([{'id': 'x1', 'cat': 'k1', 'call': 'BUY', 'sym': 'HUSS', 'at': now - 10, 'honey': 2, 'why': 'secret-ish reasoning'},
                                    {'id': 'x2', 'cat': 'k1', 'call': 'AVOID', 'sym': 'RUG', 'at': now - 5, 'honey': None, 'kind': 'exit'}])
    store = {'cats': {'k1': {'id': 'k1', 'name': 'Kit', 'hive': {'on': True}, 'brainsCfg': {'brains': ['m']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store)
    j = TestClient(fs.app).get('/api/cats/k1/live').json()
    assert j['colonized'] is True and j['honey'] == 2 and (j['right'], j['graded']) == (1, 1) and j['lastCall'] == {'call': 'AVOID', 'sym': 'RUG', 'honey': None, 'kind': 'exit'}
