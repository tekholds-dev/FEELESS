"""The PoEco desk: the books, customers, bills and coach are arithmetic on sealed rows, and marking a bill paid moves no money."""
import ast
import json
from pathlib import Path

import pytest

import agent_eco as e

TODAY = '2026-11-06'


def desk(**kw):
    d = e.empty_desk(); e.run_setup(d, {'cash': '1000', 'tax': 25, **kw}, TODAY)
    return d


def test_every_answer_really_changes_the_desk():
    d = desk(who='Freelance', wants=['books', 'bills'], bills=['rent', 'nonsense'], goal='savings', goalAmount='5000', goalBy='2027-05-06', tone='hard')
    assert d['setup']['wants'] == ['books', 'bills'] and d['setup']['tone'] == 'hard' and d['setup']['cash'] == 1000
    assert [b['name'] for b in d['bills']] == ['Rent or mortgage'] and d['bills'][0]['amount'] is None
    assert d['goals'][0]['name'] == 'Build savings' and d['goals'][0]['target'] == 5000
    v = e.view(d, TODAY); assert v['cash'] == 1000 and v['billsNoAmount'] == 1
    e.run_setup(d, {'cash': 2000, 'bills': ['rent'], 'goal': 'savings'}, TODAY)   # asked again it adds no copy and removes nothing
    assert len(d['bills']) == 1 and len(d['goals']) == 1


def test_a_paid_bill_is_a_cost_and_a_repeating_one_moves_on():
    d = desk(); b = e.add_row(d, 'bills', {'name': 'Rent', 'amount': '1400', 'due': '2026-01-31', 'every': 'month'})
    e.bill_paid(d, b['id'], TODAY)
    assert d['ledger'][-1]['amount'] == -1400 and d['ledger'][-1]['from'] == 'bill' and b['due'] == '2026-02-28' and e.view(d, TODAY)['cash'] == -400
    once = e.add_row(d, 'bills', {'name': 'Deposit', 'amount': 50, 'due': '2026-11-01', 'every': 'once'}); assert e.view(d, TODAY)['overdueUsd'] >= 50
    e.bill_paid(d, once['id'], TODAY); assert once['done'] and 'Deposit' not in [c['text'] for c in e.view(d, TODAY)['coach']]
    empty = e.add_row(d, 'bills', {'name': 'Phone'})
    with pytest.raises(ValueError, match='how much'):
        e.bill_paid(d, empty['id'], TODAY)


def test_a_paid_invoice_is_income_once():
    d = desk(); i = e.add_row(d, 'invoices', {'person': 'Sam', 'amount': '2,600', 'due': '2026-10-01'})
    v = e.view(d, TODAY); assert v['owed'] == 2600 and v['owedLateUsd'] == 2600 and v['coach'][0]['tab'] == 'people'
    e.invoice_paid(d, i['id'], TODAY); v = e.view(d, TODAY); assert v['owed'] == 0 and v['cash'] == 3600 and v['income'] == 2600
    with pytest.raises(ValueError):
        e.invoice_paid(d, i['id'], TODAY)


def test_importing_the_same_export_twice_adds_nothing():
    d = desk(); text = 'date,description,amount\n2026-10-03,Stripe sales,7450\n2026-10-05,Office rent,-1400\nbroken line'
    assert e.import_rows(d, text) == {'added': 2, 'skipped': 2, 'repeated': 0}   # the header and the broken line, never guessed
    assert e.import_rows(d, text)['repeated'] == 2 and len(d['ledger']) == 2 and d['ledger'][1]['cat'] == 'Rent'


def test_the_numbers_are_exact():
    d = desk(); e.import_rows(d, '2026-10-03,Sales,4000\n2026-10-05,Software,-200\n2026-11-02,Sales,1000\n2026-11-03,Software,-600')
    v = e.view(d, TODAY)
    assert v['cash'] == 5200 and v['income'] == 1000 and v['costs'] == 600 and v['net'] == 400 and v['taxSetAside'] == 1050 and v['runway'] == 13
    assert v['months'][-1]['cash'] == 5200 and v['catJump'] == {'cat': 'Software', 'up': 400}


def test_the_coach_uses_real_numbers_in_the_tone_asked_and_says_nothing_made_up():
    d = desk(tone='hard'); e.add_row(d, 'bills', {'name': 'Rent', 'amount': 1400, 'due': '2026-11-01'})
    hard = e.view(d, TODAY)['coach'][0]; assert hard['tab'] == 'bills' and '$1,400' in hard['text'] and 'Nothing else matters' in hard['text']
    d['setup']['tone'] = 'gentle'; assert 'Start with one' in e.view(d, TODAY)['coach'][0]['text']
    calm = desk(tone='gentle'); e.add_entry(calm, TODAY, 'Sales', 10); assert e.view(calm, TODAY)['coach'][0]['level'] == 'good'


def test_a_goal_says_what_it_needs_and_a_habit_counts_its_streak():
    d = desk(); g = e.add_row(d, 'goals', {'name': 'Save', 'target': 1200, 'saved': 200, 'by': '2027-05-06'}); h = e.add_row(d, 'goals', {'name': 'Walk', 'kind': 'habit'})
    e.check_in(d, h['id'], '2026-11-04'); e.check_in(d, h['id'], '2026-11-05')
    v = {x['name']: x for x in e.view(d, TODAY)['goals']}
    assert v['Save']['pct'] == 16.7 and v['Save']['left'] == 1000 and 160 < v['Save']['perMonth'] < 170 and g['saved'] == 200
    assert v['Walk']['streak'] == 2 and not v['Walk']['doneToday']
    e.check_in(d, h['id'], TODAY); assert e.view(d, TODAY)['goals'][1]['streak'] == 3
    e.check_in(d, h['id'], TODAY); assert TODAY not in h['checks']


def test_samples_are_marked_clear_in_one_tap_and_never_touch_real_rows():
    d = desk(sample=True); v = e.view(d, TODAY); assert v['hasSamples'] and v['count'] > 5 and v['overdue'] == 1 and v['owedLate'] == 1 and v['pipeline'][2]['n'] == 1
    real = e.add_entry(d, TODAY, 'Real sale', 50); e.clear_samples(d); v = e.view(d, TODAY)
    assert not v['hasSamples'] and d['ledger'] == [real] and not d['people'] and not d['bills']


def test_bad_rows_are_refused_in_words_and_a_pay_link_can_only_be_https():
    d = desk()
    for kind, row in (('bills', {}), ('people', {}), ('invoices', {'person': 'x'}), ('goals', {}), ('people', {'name': 'x', 'stage': 'Nope'}), ('bills', {'name': 'x', 'due': 'tomorrow'}), ('bills', {'name': 'x', 'link': 'javascript:alert(1)'}), ('bills', {'name': 'x', 'link': 'http://pay.me'}), ('nope', {'name': 'x'})):
        with pytest.raises(ValueError):
            e.add_row(d, kind, row)
    assert e.add_row(d, 'bills', {'name': 'x', 'link': 'https://pay.example.com/a'})['link'] == 'https://pay.example.com/a'


def test_a_change_of_tone_never_brings_back_what_you_removed():
    d = desk(goal='savings', bills=['rent'], tone='straight'); e.drop_row(d, 'goals', d['goals'][0]['id']); e.set_tone(d, 'hard')
    assert d['setup']['tone'] == 'hard' and not d['goals'] and d['setup']['cash'] == 1000
    with pytest.raises(ValueError):
        e.set_tone(d, 'mean')


def test_the_day_is_theirs_but_a_wild_date_is_ignored():
    assert e.their_today('2026-11-05', TODAY) == '2026-11-05' and e.their_today('2026-11-07', TODAY) == '2026-11-07'
    for bad in ('2030-01-01', 'soon', None, 7):
        assert e.their_today(bad, TODAY) == TODAY


def test_this_module_cannot_move_money():
    src = (Path(e.__file__)).read_text(); names = {n.name.split('.')[0] for x in ast.walk(ast.parse(src)) if isinstance(x, (ast.Import, ast.ImportFrom)) for n in x.names}
    assert names <= {'calendar', 'csv', 'datetime', 'hashlib', 'io', 'json', 're', 'secrets'}, names


def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'me', 'revoked': False, 'cloud': {'pool': 'feeless'}, 'brainsCfg': {}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    return fs, TestClient(fs.app), store


def test_the_whole_journey_on_the_real_route_and_only_sealed_data_on_disk(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': op, **kw})
    assert post('eco_d_get').json()['desk']['setup'] is None
    r = post('eco_d_setup', tools={'who': 'Freelance', 'cash': '500', 'bills': ['rent'], 'tone': 'straight', 'tax': 25}); assert r.status_code == 200, r.text
    bill = r.json()['desk']['bills'][0]
    assert post('eco_d_bill_paid', text=bill['id']).status_code == 400   # no amount yet
    assert post('eco_d_edit', job='bills', text=bill['id'], tools={'amount': '400', 'due': '2026-11-01'}).status_code == 200
    assert post('eco_d_bill_paid', text=bill['id']).json()['view']['cash'] == 100
    assert post('eco_d_import', text='2026-10-03,Sales SECRETWORD,900').json()['said']['added'] == 1
    p = post('eco_d_add', job='people', tools={'name': 'Sam', 'stage': 'Proposal', 'value': 900}).json(); assert p['view']['openUsd'] == 900
    proved = post('eco_d_prove', job='All').json(); assert proved['poeFolders'][0]['count'] == 2 and proved['poeFolders'][0]['hash']
    sealed = (tmp_path / 'agent_eco' / 'g' / 'desk.seal').read_bytes(); assert b'SECRETWORD' not in sealed and b'Sam' not in sealed
    assert 'SECRETWORD' not in json.dumps(store) and post('eco_d_get').json()['view']['cash'] == 1000
    assert c.post('/api/cats/g/work', json={'ownerId': 'stranger', 'session': 'stranger', 'op': 'eco_d_get'}).status_code in (401, 403)


def test_a_desk_that_cannot_be_opened_is_never_overwritten(monkeypatch, tmp_path):
    _fs, c, _s = _server(monkeypatch, tmp_path); f = tmp_path / 'agent_eco' / 'g' / 'desk.seal'; f.parent.mkdir(parents=True); f.write_bytes(b'broken')
    assert c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'eco_d_add', 'job': 'people', 'tools': {'name': 'x'}}).status_code == 500 and f.read_bytes() == b'broken'
