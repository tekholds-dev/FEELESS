"""COL-4: the owner reads every proof in one shape, the three evaluations kept apart, with who answered and the tamper-proof record."""
from test_play_studio import _server


def test_owner_reads_missions_others_cannot(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    store['cats']['g']['pobFolders'] = [{'id': 'b1', 'status': 'closed', 'at': 1, 'closedAt': 1, 'graded': 'right', 'gradedBy': 'scoreboard', 'games': [{'final': True}]}]
    j = c.get('/api/cats/g/missions', params={'ownerId': 'g', 'session': 'g'}).json()
    m = j['missions'][0]
    assert (m['code'], m['outcome']['authority'], m['improvement']['state'], m['quality']['state']) == ('PoB', 'scoreboard', 'unverified', 'scored')
    assert m['record']['state'] == 'none' and j['chain']['intact'] is True   # nothing recorded yet in this sandbox, and it says so
    assert c.get('/api/cats/g/missions', params={'ownerId': 'x', 'session': 'x'}).status_code in (401, 403)
