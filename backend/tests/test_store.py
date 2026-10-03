import json
import store


def test_kv_imports_old_json_once_and_writes_atomically(tmp_path):
    p = tmp_path / 'fuse_wallet.json'
    p.write_text(json.dumps({'cfg': {'armed': False}, 'books': {}}))
    kv = store.KV(p)
    assert kv.get()['cfg'] == {'armed': False}                         # imported
    kv.put({'cfg': {'armed': True}, 'books': {'safe': {'sol': 1}}})
    assert store.KV(p).get()['books']['safe']['sol'] == 1             # a new handle sees the committed write
    p.write_text('{"cfg": {"armed": false}}')                          # the old file is never re-imported
    assert store.KV(p).get()['cfg']['armed'] is True
    assert store.KV(tmp_path / 'nothing.json').get({'x': 1}) == {'x': 1}


def test_ledger_is_append_only_and_queryable(tmp_path):
    lg = store.Ledger(tmp_path / 'fuse_wallet.json')
    for i in range(5):
        lg.append({'at': i, 'card': 'safe' if i % 2 else 'gold', 'side': 'buy', 'usd': i})
    assert lg.count() == 5 and [r['usd'] for r in lg.rows(limit=2)] == [4, 3] and len(lg.rows(card='safe')) == 2


def test_service_fuse_wallet_lives_in_sqlite():
    import pytest
    rs = pytest.importorskip('reputation_service')
    d = rs._fw_load(); d['cfg'] = {'armed': False, 'reserveSol': 0.015}
    rs._fw_record(d, {'at': 1, 'card': 'safe', 'side': 'topup', 'usd': 4})
    rs._fw_save(d)
    assert rs._fw_load()['cfg']['reserveSol'] == 0.015 and rs.FUSE_WALLET_PATH.with_suffix('.db').exists()
    assert store.Ledger(rs.FUSE_WALLET_PATH).rows()[0]['usd'] == 4
