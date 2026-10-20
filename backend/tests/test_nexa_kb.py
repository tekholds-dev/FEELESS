import nexa_kb as kb_


def test_base_files_recalls_and_stays_capped(monkeypatch):
    kb = {}
    kb_.auto(kb, [{'mint': 'MiNt1', 'symbol': 'CAT', 'cap': 42000, 'ageMin': 30, 'setups': ['germ'], 'creator': 'Dev1', 'crew': 'serial'}], now=100)
    kb_.remember(kb, [['narrative', 'ai agents', 'AI agent coins ran this week'], ['bogus', 'x', 'y'], {'cat': 'lesson', 'key': 'l1', 'fact': 'skip serial crews'}], now=110)
    lines = kb_.recall(kb, keys=['mint1', '$cat'], words=['agents'], now=120)
    assert any('cap $42K' in l for l in lines) and any('AI agent' in l for l in lines) and any('skip serial' in l for l in lines)
    assert 'bogus' not in kb and kb['coin']['mint1']['hits'] == 1
    assert kb_.need_web(kb, ['MiNt1', 'other'], now=200) == ['other']
    assert kb_.need_web(kb, ['MiNt1'], now=100 + kb_.FRESH_SEC + 1) == ['MiNt1']
    monkeypatch.setitem(kb_.CAPS, 'fact', 3)
    for i in range(10):
        kb_.put(kb, 'fact', f'k{i}', 'x' * 500, now=i)
    assert len(kb['fact']) == 3 and len(kb['fact']['k9']['f']) == kb_.FACT_LEN
    kb_.rug(kb, 'm2', 'RUG', -80, now=5)
    assert 'fell -80%' in kb['rug']['m2']['f'] and kb_.stats(kb)['total'] >= 5
