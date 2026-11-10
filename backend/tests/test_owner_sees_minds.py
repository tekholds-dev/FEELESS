"""AGT-2: Sicario's chats showed "FeeCat AI" for both minds even to its owner. The owner now reads the real minds; visitors still read FeeCat AI."""
from test_play_studio import _server


def test_owner_reads_real_minds_visitors_do_not(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    store['cats']['g'].update(brainLabel='OSSY + G4', chat=[{'by': 'G4', 'text': 'G4 says hold'}])
    own = c.get('/api/cats/g', params={'ownerId': 'g', 'session': 'g'}).json()['cat']
    assert own['brainLabel'] == 'OSSY + G4' and own['chat'][0]['by'] == 'G4'
    seen = c.get('/api/cats/g', params={'ownerId': 'x', 'session': 'x'}).json()['cat']
    assert 'OSSY' not in str(seen) and 'G4' not in str(seen)
