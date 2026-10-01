"""One alert stream: phone alerts (watch rules, FeeCat, snipers-out) also land in the wallet's in-app inbox, with the
rule and its data source, and never trigger a second push. All network is faked."""
import pytest

rs = pytest.importorskip('reputation_service')

W = 'Aaaa1111111111111111111111111111111111111111'


def test_watch_alert_lands_in_inbox_with_its_source_and_no_second_push(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'NOTIF_PATH', tmp_path / 'n.json')
    monkeypatch.setattr(rs, 'PUSH_PATH', tmp_path / 'p.json', raising=False)
    pushed = []
    monkeypatch.setattr(rs, '_send_push', lambda *a, **k: pushed.append(a) or 'ok')
    monkeypatch.setattr(rs, '_push_load', lambda: {'subs': {'s': {'subscription': {}, 'prefs': {'address': W}, 'watch': []}}})
    entry = {'subscription': {}, 'prefs': {'address': W}}
    w = {'chainId': 'solana', 'pairAddress': 'PoolX', 'symbol': 'WIF'}
    rs._inbox_alert(entry, 'volSpike', 'WIF volume spike: last 5m running 4.0× its daily pace', w)
    box = rs._json_load(tmp_path / 'n.json', {})[rs.primary_of(W)]
    assert box[0]['kind'] == 'alert'
    assert box[0]['meta'] == {'symbol': 'WIF', 'rule': 'volSpike', 'claim': 'WIF volume spike: last 5m running 4.0× its daily pace',
                              'source': '5m vs 24h volume (DexScreener)'}
    assert box[0]['url'] == '/?coin=solana:PoolX'
    assert pushed == []


def test_subscription_without_a_wallet_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'NOTIF_PATH', tmp_path / 'n.json')
    rs._inbox_alert({'subscription': {}, 'prefs': {}}, 'up', 'WIF up 20%', {'chainId': 'solana', 'pairAddress': 'P'})
    assert rs._json_load(tmp_path / 'n.json', {}) == {}
