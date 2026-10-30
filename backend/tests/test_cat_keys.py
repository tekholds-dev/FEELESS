import asyncio
import pytest
import cat_keys as ck


ENV = {'BROKER_SECRET_KEY': 'test-secret'}
OR_KEY = 'sk-or-v1-' + 'a' * 40


def test_key_is_sealed_and_never_public():
    cat = {}
    rows = ck.put(cat, 'openrouter', OR_KEY, env=ENV, now=1)
    assert OR_KEY not in str(cat['apiKeys'])            # sealed at rest
    row = next(r for r in rows if r['provider'] == 'openrouter')
    assert row['saved'] and row['last4'] == OR_KEY[-4:] and row['wired']
    assert OR_KEY not in str(rows)                      # the page sees the last 4 only
    assert ck.key_for(cat, 'openrouter', env=ENV) == OR_KEY
    assert ck.key_for(cat, 'openrouter', env={'BROKER_SECRET_KEY': 'other'}) is None
    ck.drop(cat, 'openrouter')
    assert ck.key_for(cat, 'openrouter', env=ENV) is None


def test_bad_shapes_and_no_server_secret_are_refused():
    with pytest.raises(ValueError):
        ck.put({}, 'openrouter', 'hello', env=ENV)
    with pytest.raises(ValueError):
        ck.put({}, 'binance', 'x' * 40, env=ENV)
    with pytest.raises(RuntimeError):
        ck.put({}, 'openrouter', OR_KEY, env={})


def test_trading_cat_venues_are_feeless_rails_only():
    assert ck.venues(None) == ['trench']
    assert ck.venues(['perps', 'trench', 'perps']) == ['perps', 'trench']
    with pytest.raises(ValueError):
        ck.venues(['binance'])


def test_service_never_sends_sealed_keys_and_byok_skips_credit(monkeypatch):
    import feecat_service as svc
    cat = {'id': 'c1', 'ownerId': 'o', 'name': 'Specter', 'brainsCfg': {'brains': ['a/b'], 'brainMode': 'turns', 'credit': 0.0, 'spent': 0, 'asks': 0,
           'billing': 'payg', 'kind': 'trading', 'decisions': [], 'chime': [], 'owed': 0, 'efforts': {}}, 'status': 'running'}
    monkeypatch.setenv('BROKER_SECRET_KEY', 'test-secret')
    ck.put(cat, 'openrouter', OR_KEY)
    out = svc._pub({'cat': cat})['cat']
    assert 'apiKeys' not in out and OR_KEY not in str(out)
    assert next(r for r in out['apiDrawer'] if r['provider'] == 'openrouter')['saved']
    seen = {}

    async def fake_call(model, messages, max_tokens=None, effort=None, key=None):
        seen['key'] = key
        return 'BUY — germ floor', 0.01
    monkeypatch.setattr(svc, '_or_call', fake_call)
    monkeypatch.setattr(svc, '_brains_live', lambda: False)   # the owner's switch is off — your own key still runs
    monkeypatch.setattr(svc, '_log_event', lambda *a, **k: None)
    r = asyncio.run(svc._brain_decide({'events': []}, cat, 'buy', 'GERM', {}))
    assert r is not None and seen['key'] == OR_KEY
    assert cat['brainsCfg']['credit'] == 0.0                 # no FEELESS credit charged
