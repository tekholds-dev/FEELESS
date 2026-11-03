import json

import pytest

import poi


def _fact(site='solscan.io'):
    return {'label': 'top 10 holders', 'value': '23%', 'site': site, 'url': f'https://{site}/token/M',
            'at': 100, 'support': 'top 10 holders 23%', 'verified': True}


def test_research_dna_is_private_authenticated_versioned_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv('FEELESS_VAULT_KEY_FILE', str(tmp_path / 'master.key'))
    data = tmp_path / 'data'
    first = poi.append(data, 'cat', 0, 'folder-1', 'M', 100, [_fact(), {**_fact('pump.fun'), 'verified': False}],
                       {'verified': 1, 'costUsd': .002}, ['route-hash'])
    again = poi.append(data, 'cat', 0, 'folder-1', 'M', 101, [_fact()], {'verified': 1}, [])
    second = poi.append(data, 'cat', 0, 'folder-2', 'N', 102, [_fact('birdeye.so')], {'verified': 1}, [])
    assert first == again and [first['generation'], second['generation']] == [1, 2]
    assert second['prev'] == first['integrity']
    assert first['sites'] == ['solscan.io'] and first['facts'][0]['label'] == 'top 10 holders'
    assert first['facts'][0]['ref'] == poi._digest({k: v for k, v in _fact().items() if k != 'verified'})
    assert poi.load(data, 'cat', 0) == [first, second]
    assert poi.load(data, 'cat', 1) == [] and poi.load(data, 'other', 0) == []
    raw = poi._path(data, 'cat', 0).read_text()
    assert 'solscan.io' not in raw and 'top 10 holders' not in raw and 'route-hash' not in raw
    assert all(json.loads(line)['v'] == poi.VERSION for line in raw.splitlines())
    assert poi._path(data, 'cat', 0).stat().st_mode & 0o777 == 0o600


def test_research_dna_tamper_or_wrong_mind_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv('FEELESS_VAULT_KEY_FILE', str(tmp_path / 'master.key'))
    data = tmp_path / 'data'
    poi.append(data, 'cat', 0, 'f', 'M', 100, [_fact()], {}, [])
    path = poi._path(data, 'cat', 0)
    with path.open() as fh, pytest.raises(ValueError):
        poi._read_locked(fh, 'cat', 1)
    content = path.read_text()
    row = json.loads(content)
    row['sealed'] = row['sealed'][:-2] + 'aa'
    path.write_text(json.dumps(row) + '\n')
    with pytest.raises(ValueError, match='unreadable or altered'):
        poi.load(data, 'cat', 0)


def test_each_mind_has_evidence_fingerprint_independent_of_trade_wins(tmp_path, monkeypatch):
    monkeypatch.setenv('FEELESS_VAULT_KEY_FILE', str(tmp_path / 'master.key'))
    data = tmp_path / 'data'
    poi.append(data, 'cat', 0, 'f1', 'M', 100, [_fact()], {'gaps': ['pump.fun']}, ['route-a'], ['solscan.io', 'pump.fun'])
    poi.append(data, 'cat', 0, 'f2', 'N', 110, [_fact()], {}, ['route-b'], ['solscan.io'])
    poi.append(data, 'cat', 1, 'f1', 'M', 100, [_fact('birdeye.so')], {}, ['route-c'], ['birdeye.so'])
    a = poi.fingerprint(poi.load(data, 'cat', 0), 0)
    b = poi.fingerprint(poi.load(data, 'cat', 1), 1)
    assert a['generations'] == 2 and a['uniqueRoutes'] == 2 and a['verified'] == 2
    assert a['coverage']['solscan.io']['reads'] == 2 and a['coverage']['solscan.io']['yield'] == 1
    assert a['coverage']['pump.fun']['gaps'] == 1 and a['coverage']['pump.fun']['verified'] == 0
    assert 'solscan.io' not in b['coverage'] and b['coverage']['birdeye.so']['verified'] == 1


def test_evolution_promotes_on_later_evidence_then_retires_on_regression(tmp_path, monkeypatch):
    monkeypatch.setenv('FEELESS_VAULT_KEY_FILE', str(tmp_path / 'master.key'))
    data = tmp_path / 'data'
    for i in range(4):
        poi.append(data, 'cat', 0, f'f{i}', f'M{i}', i + 1, [_fact()], {}, [f'route-{i}'], ['solscan.io'])
    first = poi.load(data, 'cat', 0)
    assert first[-1]['policy']['events'] == [{'generation': 4, 'site': 'solscan.io', 'state': 'promoted'}]
    assert poi.evolution(first)['states']['solscan.io'] == 'promoted'
    for i in range(4, 6):
        poi.append(data, 'cat', 0, f'f{i}', f'M{i}', i + 1, [], {'gaps': ['solscan.io']}, [], ['solscan.io'])
    last = poi.load(data, 'cat', 0)
    assert last[-1]['policy']['events'] == [{'generation': 6, 'site': 'solscan.io', 'state': 'retired'}]
    assert poi.evolution(last)['states']['solscan.io'] == 'retired'


def test_model_swap_memory_is_sealed_and_recoverable_without_changing_dna(tmp_path, monkeypatch):
    monkeypatch.setenv('FEELESS_VAULT_KEY_FILE', str(tmp_path / 'master.key'))
    data = tmp_path / 'data'
    original = {'brains': ['old/model'], 'cloud': [{'text': 'original note'}], 'decisions': [{'word': 'WATCH'}], 'minds': {'A': 'old'}}
    saved = poi.preserve_model_memory(data, 'cat', original, ['new/model'], 100)
    assert poi.preserve_model_memory(data, 'cat', original, ['new/model'], 101) == saved
    assert poi.memory_versions(data, 'cat')[0]['source'] == original
    assert 'original note' not in poi._path(data, 'cat', 2).read_text()
    assert poi.load(data, 'cat', 0) == []


def test_manual_challenge_outcomes_keep_only_counts(monkeypatch):
    import feecat_service as fs
    store = {'cats': {'cat': {'id': 'cat'}}}
    monkeypatch.setattr(fs, '_load', lambda: store)
    monkeypatch.setattr(fs, '_save', lambda value: None)
    monkeypatch.setattr(fs, 'keep_owned', lambda value: None)
    fs._challenge_note('cat', 'pump.fun', 'timedOut')
    fs._challenge_note('cat', 'pump.fun', 'manualPass')
    assert store['cats']['cat']['challengeStats']['pump.fun']['timedOut'] == 1
    assert store['cats']['cat']['challengeStats']['pump.fun']['manualPass'] == 1
    assert 'cookies' not in str(store['cats']['cat']['challengeStats'])
