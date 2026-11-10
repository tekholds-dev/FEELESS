"""AGT-14: an owner reads how each kind of proof runs, from the live settings; nobody else can."""
from test_play_studio import _server


def test_paths_are_read_from_live_settings(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    store['cats']['g']['brainsCfg'].update(brains=['a/x', 'b/y'], byKind={'pob': ['c/z']}, promptBy={'pob': 'bet small'}, personaBy={'pob': {'style': 'analyst'}})
    monkeypatch.setattr(fs._stash, 'trust_rows', lambda *a: [])
    j = c.get('/api/cats/g/paths', params={'ownerId': 'g', 'session': 'g'}).json()
    by = {p['kind']: p for p in j['paths']}
    assert by['pob']['minds'] == ['c/z'] and by['pob']['ownMinds'] and by['pob']['prompt'] and by['pob']['persona'] == 'analyst'
    assert by['pow']['minds'] == ['a/x', 'b/y'] and not by['pow']['ownMinds'] and by['pob']['freshMin'] == 30
    assert any('playtest' in x for x in by['pos']['checks']) and 'compare-before-settling' in by['pob']['kits'] and by['pow']['route']
    assert c.get('/api/cats/g/paths', params={'ownerId': 'x', 'session': 'x'}).status_code in (401, 403)
