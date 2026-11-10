"""COL-15: the owner's hand trade of a proposal is kept as his claim, never a settled result."""
import mission
from test_play_studio import _server


def test_a_hand_trade_is_a_claim(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    store['cats']['g']['powFolders'] = [{'id': 'p1', 'propose': True, 'status': 'closed', 'at': 1, 'sym': 'GONE'}, {'id': 'p2', 'status': 'closed', 'at': 1}]
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': 'pow_claim', **kw})
    assert post(job='p2', tools={'venue': 'x', 'resultUsd': 1}).status_code == 400   # only a proposal
    assert post(job='p1', tools={'venue': 'Crypto.com', 'resultUsd': 'lots'}).status_code == 400
    assert post(job='p1', tools={'venue': 'Crypto.com', 'resultUsd': 5, 'receipt': 'http://x'}).status_code == 400   # https only
    r = post(job='p1', text='sold at the top', tools={'venue': 'Crypto.com', 'resultUsd': '12.5', 'receipt': 'https://crypto.com/r/1'})
    assert r.status_code == 200 and store['cats']['g']['powFolders'][0]['manual']['status'] == 'claim'
    out = mission.envelope('pow', store['cats']['g']['powFolders'][0], 10 ** 10)['outcome']
    assert out['authority'] == 'owner claim' and out['strength'] == 'self' and out['state'] != 'proved'   # never a settled win
