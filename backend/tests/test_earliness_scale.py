import trench as t
import pay_map as pm


def test_earliness_groups_settled_coins_by_age_when_first_seen():
    st = {}
    st = t.meta_track(st, {'fresh': [('A', 1.0, 0.1), ('B', 1.0, 2.0), ('C', 1.0, None)]}, lambda m: None, 0, keys=('fresh',))
    px = {'A': 3.0, 'B': 0.5, 'C': 1.0}
    st = t.meta_track(st, {}, lambda m: px[m], t.PROOF_SEC + 1, keys=('fresh',))
    e = t.earliness(st, keys=('fresh',))
    assert e['<15m']['n'] == 1 and e['<15m']['big'] == 1 and e['<15m']['medPct'] == 200.0
    assert e['1-3h']['n'] == 1 and e['1-3h']['medPct'] == -50.0
    assert sum(v['n'] for v in e.values()) == 2          # no age recorded = not counted


def _ledger(cost_each, ret, n=45, card='degen'):
    rows = []
    for i in range(n):
        m = f'M{i}-{cost_each}'
        rows.append({'card': card, 'status': 'filled', 'side': 'buy', 'sig': f'b{i}{cost_each}', 'mint': m, 'px': 1.0, 'units': cost_each, 'at': 1000 + i * 100})
        rows.append({'card': card, 'status': 'filled', 'side': 'sell', 'sig': f's{i}{cost_each}', 'mint': m, 'px': 1.0 + ret, 'units': cost_each, 'at': 1000 + i * 100 + 1800})
    return rows


def test_same_percent_at_every_size_reads_as_one_population():
    ledger = _ledger(0.3, 0.05) + _ledger(1.0, 0.05) + _ledger(5.0, 0.05)
    r = pm.pay_map(ledger, 'degen', 10 ** 6)
    assert set(r['bySize']) == {'<$0.50', '$0.50-2', '$2+'}
    adv = [a for a in r['advice'] if a['key'] == 'scale']
    assert adv and 'ONE population' in adv[0]['text']
    assert r['bySize']['$2+']['perHr'] is not None and r['bySize']['$2+']['perHr'] > 0     # profit speed = % per hour in coins


def test_real_hold_fix_runs_once_and_keeps_a_backup(tmp_path, monkeypatch):
    import asyncio, json
    import reputation_service as rs
    hq = rs.FUSE_HQ_PATH
    hq.write_text(json.dumps({'prime': {'realCfg': {'minHoldMins': 0.0, 'trenchHouseAt': 50, 'rotateHours': 0.08}, 'realOwnerSet': ['rotateHours']}}))
    assert asyncio.run(rs._real_hold_fix(1000.0)) is True
    pr = json.loads(hq.read_text())['prime']
    assert pr['realCfg']['minHoldMins'] == 30.0 and pr['realCfg']['trenchHouseAt'] == 100 and pr['realCfg']['rotateHours'] == 0.08   # the 5-min clock stays
    assert 'minHoldMins' in pr['realOwnerSet'] and json.loads((rs.DATA_DIR / 'realcfg_before_hold30.json').read_text())['minHoldMins'] == 0.0
    assert asyncio.run(rs._real_hold_fix(2000.0)) is False
