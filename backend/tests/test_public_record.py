"""AGT-10: an agent's public record is counts only, open to visitors, with nothing private in it."""
from test_play_studio import _server


def test_public_record_counts_only(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    store['cats']['g'].update(pobFolders=[{'id': 'b1', 'status': 'closed', 'at': 1, 'closedAt': 1, 'graded': 'right', 'gradedBy': 'scoreboard', 'games': [{'final': True}], 'why': 'SECRET-NOTE', 'sites': ['espn.com']}],
                              powFolders=[{'id': 'w1', 'status': 'closed', 'at': 1, 'soldAt': 1, 'real': True, 'pnlSol': -0.001, 'mint': 'MINTSECRET'}])
    j = c.get('/api/cats/g/record').json()   # no sign-in: visitors read it
    by = {k['kind']: k for k in j['kinds']}
    assert (by['pob']['proved'], by['pob']['verified'], by['pob']['verifiedWon']) == (1, 1, 1) and j['total']['filed'] == 2
    assert 'SECRET' not in str(j) and 'espn' not in str(j) and 'ownerId' not in str(j)
    assert c.get('/api/cats/nope/record').status_code == 404
