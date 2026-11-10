"""AGT-11: each agent's private database is sealed on disk, grows by itself from closed proofs, and only rows its owner shares reach another agent."""
import cat_keys as ck

import agent_db as adb


def test_rows_are_sealed_on_disk_and_only_shared_rows_reach_another_agent(tmp_path, monkeypatch):
    seal = lambda cid: (lambda raw: ck.seal_bytes(raw, cid)); unseal = lambda cid: (lambda raw: ck.unseal_bytes(raw, cid))
    pa, pb = adb.path_of(tmp_path, 'a'), adb.path_of(tmp_path, 'b')
    assert adb.add(pa, 'p1', 'pob', 'PoB · NBA', {'why': 'Knicks at home SECRETWORD'}, seal('a'))
    assert not adb.add(pa, 'p1', 'pob', 'again', {}, seal('a'))                 # one row per proof, ever
    adb.add(pa, 'p2', 'pow', 'PoW · X', {'why': 'private'}, seal('a'))
    assert b'SECRETWORD' not in pa.read_bytes()                                  # sealed on disk
    assert adb.read(pa, 'p1', unseal('a'))['why'].endswith('SECRETWORD')
    assert adb.shared_to(tmp_path, 'b', ['a', 'b'], unseal) == []               # nothing shared yet
    adb.share(pa, 'p1', 'b', True)
    got = adb.shared_to(tmp_path, 'b', ['a', 'b'], unseal)
    assert [r['id'] for r in got] == ['p1'] and got[0]['body']['why'].endswith('SECRETWORD') and 'SHARED WITH YOU' in adb.shared_line(got)
    assert adb.shared_to(tmp_path, 'b', ['a', 'b'], unseal, kind='pow') == []    # only the kind asked for
    adb.share(pa, 'p1', 'b', False); assert adb.shared_to(tmp_path, 'b', ['a', 'b'], unseal) == []
    assert all('body' not in r for r in adb.rows(pa)) and not pb.exists()


def test_the_service_grows_each_agents_database_once_and_its_ops_are_its_owners(monkeypatch, tmp_path):
    from test_play_studio import _server
    fs, c, store = _server(monkeypatch, tmp_path)
    store['cats']['g']['pobFolders'] = [{'id': 'b1', 'status': 'closed', 'topic': 'NBA', 'closedAt': 5, 'ownerWallet': 'W'}, {'id': 'b2', 'status': 'live'}]
    fs._ADB_SEEN.clear()
    assert fs._db_grow(store) == 1 and fs._db_grow(store) == 0
    j = c.post('/api/cats/g/work', json={'op': 'db_list', 'ownerId': 'g', 'session': 'g'}).json()
    assert [r['id'] for r in j['rows']] == ['b1'] and any(t['id'] == 'collective' for t in j['targets'])
    body = c.post('/api/cats/g/work', json={'op': 'db_read', 'job': 'b1', 'ownerId': 'g', 'session': 'g'}).json()['body']
    assert body['topic'] == 'NBA' and 'ownerWallet' not in body
    assert c.post('/api/cats/g/work', json={'op': 'db_share', 'job': 'b1', 'text': 'someone-else', 'on': True, 'ownerId': 'g', 'session': 'g'}).status_code == 400
    r = c.post('/api/cats/g/work', json={'op': 'db_share', 'job': 'b1', 'text': 'collective', 'on': True, 'ownerId': 'g', 'session': 'g'}).json()
    assert r['rows'][0]['shared'] == ['collective']
    assert c.post('/api/cats/g/work', json={'op': 'db_list', 'ownerId': 'x', 'session': 'x'}).status_code in (401, 403)
