import lag_advice as la


def test_advice_names_the_real_causes_worst_first():
    summ = {'routes': [{'route': '/api/x', 'calls': 5, 'p50': 300, 'p95': 9000}, {'route': '/api/y', 'calls': 5, 'p50': 1500, 'p95': 3000}], 'pages': [], 'score': 50}
    loop = {'blockedPct': 30, 'worstSec': 7, 'top': [{'where': 'svc.f › g:1', 'sec': 0.5}], 'json': [['save:fuse_hq.json', 4434, 54.5]]}
    out = la.advise(summ, loop, {'swapPct': 94, 'load1': 4, 'cores': 8})
    assert out[0]['level'] == 'bad'
    whats = ' '.join(a['what'] for a in out)
    assert 'Swap 94%' in whats and '/api/x' in whats and 'save:fuse_hq.json' in whats
    x = next(a for a in out if a['where'] == '/api/x')
    assert 'stale-while-revalidate' in x['fix']
    y = next(a for a in out if a['where'] == '/api/y')
    assert 'parallel' in y['fix']
    assert 'debounce' in next(a for a in out if a['area'] == 'storage')['fix']


def test_quiet_system_gives_no_advice_and_toned_vitals():
    assert la.advise({'routes': [], 'pages': []}, {'blockedPct': 1, 'worstSec': 0.4}, {'swapPct': 20, 'load1': 2}) == []
    v = {r['k']: r for r in la.vitals({'score': 95}, {'blockedPct': 1}, {'swapPct': 90})}
    assert v['SPEED']['tone'] == 'ok' and v['SWAP']['tone'] == 'bad' and v['LOOP BLOCKED']['tone'] == 'ok'
