"""Owner 2026-11-06: every proof runs from the desk, by name, and stays the one being talked to."""
import proof_commands as pc


def test_the_owners_words():
    got = pc.parse('create a PoB named Lakers v Suns 10/12')
    assert got == {'kind': 'pob', 'name': 'Lakers v Suns 10/12', 'ask': ''}
    assert pc.line_for(got) == 'file a pob Lakers v Suns 10/12'


def test_every_kind_and_a_build_with_its_ask():
    assert pc.parse('/pow')['kind'] == 'pow' and pc.line_for(pc.parse('/pow')) == 'file a PoW'
    assert pc.parse('make a pop')['kind'] == 'pop' and pc.line_for(pc.parse('make a pop')) == 'file a perp'
    assert pc.parse('start a new PoC on lakers memes')['name'] == 'lakers memes'
    got = pc.parse('create a PoST named Tip page: a tip jar with a chart')
    assert got['kind'] == 'pos' and got['name'] == 'Tip page' and got['ask'] == 'a tip jar with a chart' and pc.line_for(got) is None
    assert pc.parse('new postatic called Radar')['kind'] == 'pos'


def test_ordinary_sentences_stay_sentences():
    for t in ('make a post about the lakers', 'post about the lakers', 'what is a pob', 'pop quiz tomorrow', 'buy 0.05 SOL of $BONK', 'start the music', 'do a popcorn run'):
        assert pc.parse(t) is None, t


def test_leaving_and_the_note():
    assert pc.leaving('back to the desk') and pc.leaving('/back to desk') and not pc.leaving('back to the lakers')
    f = pc.focus({'kind': 'pob', 'name': 'Lakers', 'ask': ''}, 5)
    assert f['open'] == 'bids' and 'Lakers' in pc.note_for(f, 'check injuries')
    assert any(c.startswith('create a PoB') for c, _ in pc.COMMANDS)


def _desk(monkeypatch, brains=('m/a', 'm/b')):
    import pytest
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'me', 'revoked': False, 'cloud': {'pool': 'feeless'}, 'brainsCfg': {'kind': 'general', 'brains': list(brains), 'credit': 5}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_work_live', lambda: True); monkeypatch.setattr(fs._lc, 'can_ask', lambda b: True)
    runs = []; asks = []
    monkeypatch.setattr(fs, '_ws_start', lambda cid, ws, to, text, region: runs.append((ws, text)))
    monkeypatch.setattr(fs, '_work_start', lambda cid, cat, text, to=None, files=None: asks.append(text))
    c = TestClient(fs.app)
    say = lambda t: c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': t})
    return say, store['cats']['g'], runs, asks, fs


def test_a_named_pob_files_at_once_and_stays_in_focus(monkeypatch):
    say, cat, _, asks, fs = _desk(monkeypatch)
    r = say('create a PoB named Lakers v Suns 10/12'); assert r.status_code == 200, r.text
    assert cat['pobAsk'] == 'Lakers v Suns 10/12' and 'proofAsk' not in cat and fs._POB_WANT.pop('g') == 'start'
    assert r.json()['deskProof']['name'] == 'Lakers v Suns 10/12' and 'Filing a PoB on Lakers v Suns' in r.json()['chat'][-1]['text']
    r = say('weigh the injuries more'); assert r.status_code == 200, r.text   # nothing is running in this test, so its minds answer, with the proof in mind
    assert 'Lakers v Suns' in cat['proofNote']['text'] and 'weigh the injuries' in cat['proofNote']['text'] and asks[-1].startswith('weigh the injuries')
    cat['pobRead'] = True; n = len(asks)
    r = say('also check the line'); assert 'Told the minds' in r.json()['chat'][-1]['text'] and len(asks) == n   # running: no second paid ask
    r = say('back to the desk'); assert r.json()['deskProof'] is None and 'proofNote' not in cat and 'deskProof' not in cat


def test_a_post_opens_its_folder_and_words_build_there(monkeypatch):
    say, cat, runs, _, fs = _desk(monkeypatch)
    r = say('create a PoST named Tip page'); assert r.status_code == 200, r.text
    ws = r.json()['deskProof']['ws']; assert any(w['id'] == ws and w['name'] == 'Tip page' for w in cat['workspaces']) and not runs
    r = say('a tip jar with a live chart'); assert r.status_code == 200, r.text
    assert runs == [(ws, 'a tip jar with a live chart')] and fs._ws_load('g', ws)['busy']
    assert say('make it blue').status_code == 409   # one build at a time, the same as its folder


def test_a_post_with_its_ask_starts_right_away(monkeypatch):
    say, cat, runs, _, _ = _desk(monkeypatch)
    say('create a PoST named Radar: a radar of new pools')
    assert runs[0][1] == 'a radar of new pools'


def test_no_model_no_build(monkeypatch):
    say, cat, runs, _, fs = _desk(monkeypatch)
    monkeypatch.setattr(fs._lc, 'can_ask', lambda b: False)
    assert say('create a PoST named X: a page').status_code == 402 and not runs
