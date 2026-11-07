"""Owner 2026-11-06: told to write about the Collective, the minds searched the web and landed on a different company called Feeless."""
import agent_knows as ak


def test_it_knows_when_it_is_being_asked_about_itself():
    for t in ('write a post about the feeless collective and how its better than the leading agent sites', 'explain Fee-Back', 'what is a PoB', 'how do boost points work', 'explain our platform'):
        assert ak.asks_about(t), t
    for t in ('research Kalshi fees', 'find the best NFL picks', 'buy 0.05 SOL of $BONK'):
        assert not ak.asks_about(t), t
    assert ak.for_ask('research Kalshi fees') == ''


def test_the_brief_holds_the_whole_operation_and_warns_about_namesakes():
    b = ak.for_ask('write about the feeless collective')
    assert len(b) <= ak.BRIEF_MAX + len(ak.NAME_CLASH) + len(ak.FLOOR) + len(ak.RULES) + 100
    for word in ('feeless.family', 'Never research FEELESS on the web', 'PoStatic', 'base top score is 300', 'Two Minds', 'Fingerprint', 'Never invent', 'Never promise profit', 'visit.feeless', 'FUSE', 'Fee-Back'):
        assert word in b, word


def test_an_ask_about_feeless_reaches_its_minds_and_your_words_stay_yours(monkeypatch):
    import pytest
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'me', 'revoked': False, 'cloud': {'pool': 'feeless'}, 'brainsCfg': {'kind': 'general', 'brains': ['m/a', 'm/b'], 'credit': 5}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_work_live', lambda: True); monkeypatch.setattr(fs._lc, 'can_ask', lambda b: True)
    seen = []
    monkeypatch.setattr(fs, '_work_start', lambda cid, cat, text, to=None, files=None: seen.append(text))
    r = TestClient(fs.app).post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': 'write a post about the feeless collective'})
    assert r.status_code == 200, r.text
    assert 'Never research FEELESS on the web' in seen[0] and seen[0].startswith('write a post')
    assert store['cats']['g']['chat'][-1]['text'] == 'write a post about the feeless collective'


def test_the_brain_says_where_it_is_and_never_tells_it_to_move_money():
    for word in ('visit.feeless', 'PoStatic', 'Nothing here tells you to trade, sign, send or spend'):
        assert word in ak.WHERE, word
    for word in ('api key', 'seed', 'private key', 'password', 'token'):
        assert word not in ak.WHERE.lower(), word


def test_score_words_come_from_the_rubric_in_use():
    import proof_weights as pw
    line = ak.score_line('PoStatic')
    for _k, label, w, _r in pw.RUBRIC['pos']:
        assert f'{label} {w}' in line
    assert 'simple request well is not a high score' in line and ak.score_line('nope') == ''


def test_it_is_told_where_its_last_proof_lost_the_most():
    import proof_weights as pw
    line = ak.weak_line(pw.view('PoStatic', {'status': 'closed', 'graded': 'right', 'ws': 'w', 'version': 1, 'at': 1}, earlier=[], page=lambda f: {'chars': 9000, 'fns': 4, 'handlers': 1, 'state': 0, 'visuals': 0, 'kits': 0}))
    assert 'lost the most on Real build' in line and '9K page' in line and ak.weak_line(None) == ''


def test_a_page_gets_the_brain_and_a_pow_never_does(tmp_path):
    import pytest
    fs = pytest.importorskip('feecat_service')
    cat = {'id': 'g', 'psFolders': [{'id': 'p', 'at': 1, 'status': 'closed', 'topic': 'tool'}], 'powFolders': [{'id': 'w', 'at': 1, 'status': 'closed', 'pnlPct': -5}]}
    assert 'HOW THIS PROOF IS SCORED' in fs._proof_brain(cat, 'pos') and 'YOUR LAST ONE' in fs._proof_brain(cat, 'pos')
    assert fs._proof_brain(cat, 'pow') == '' and 'HOW THIS PROOF IS SCORED' not in fs._recall(cat, 'Trades', 'WIF') and 'HOW THIS PROOF IS SCORED' in fs._recall(cat, 'Code', 'a tool')
    assert 'WHERE YOU ARE' in fs._job_brain(cat, 'anything') and 'WHERE YOU ARE' in fs._general_mind(cat)
