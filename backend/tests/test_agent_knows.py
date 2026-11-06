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
    for word in ('feeless.family', 'Never research FEELESS on the web', 'PoStatic', 'grades 0 to 300', 'Two Minds', 'Fingerprint', 'Never invent', 'Never promise profit', 'visit.feeless', 'FUSE', 'Fee-Back'):
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
