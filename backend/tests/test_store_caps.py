"""🗄 store_caps: every data file gets a class + cap; money is kept whole, old snapshots are listed stale, caches / logs / memory are capped."""
import store_caps as sc

NOW = 1_800_000_000.0
MB = sc.MB


def test_classes_and_states():
    assert sc.classify('fuse_wallet.db')[0] == 'money' and sc.classify('realcfg_before_clean1009.json')[0] == 'snapshot'
    assert sc.classify('chat.json')[0] == 'log' and sc.classify('nexa_kb.json')[0] == 'memory' and sc.classify('candle_ticks.json')[0] == 'cache'
    a = sc.audit([('fuse_wallet.db', 80 * MB, NOW), ('proof_before_clean1013.json', MB, NOW - 30 * 86400), ('pump_callers.json', 29 * MB, NOW),
                  ('chat.json', 7 * MB, NOW), ('odd.json', MB, NOW)], NOW)
    st = {r['name']: r['state'] for r in a['stores']}
    assert st == {'fuse_wallet.db': 'keep', 'proof_before_clean1013.json': 'stale', 'pump_callers.json': 'over', 'chat.json': 'watch', 'odd.json': 'ok'}
    assert a['stores'][0]['name'] == 'pump_callers.json' and a['over'] == 1 and a['stale'] == 1 and a['staleMb'] == 1.0
