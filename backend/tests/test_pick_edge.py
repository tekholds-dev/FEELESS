import pick_edge as edge

T0 = 1_000_000.0


def _world(n=40):
    """n rounds 15 min apart. OLD-type coins (20h, deep pool, 72% buyers, calm) drift up; NEW-type coins (0.4h, thin, 52% buyers,
    hyper-traded) crash; one NEW coin simply stops trading."""
    rounds, paths = [], {}
    for i in range(n):
        at = T0 + i * 900
        o, w, g = f'OLD{i}', f'NEW{i}', f'GONE{i}'
        rounds.append({'at': at, 'picks': [
            {'mint': o, 'ageH': 20, 'liq': 300_000, 'mcap': 3e6, 'chg1h': 4, 'chg5m': 1, 'buyShare': 72, 'vol1h': 90_000, 'stage': 'graduated', 'score': 40},
            {'mint': w, 'ageH': 0.4, 'liq': 18_000, 'mcap': 30_000, 'chg1h': 180, 'chg5m': 14, 'buyShare': 52, 'vol1h': 90_000, 'stage': 'curve', 'score': 90},
            {'mint': g, 'ageH': 0.4, 'liq': 18_000, 'mcap': 30_000, 'chg1h': 180, 'chg5m': 14, 'buyShare': 52, 'vol1h': 90_000, 'stage': 'curve', 'score': 90}]})
        ts = [at + k * 300 for k in range(40)]
        paths[o] = [[t, 1.0 + 0.002 * k] for k, t in enumerate(ts)]
        paths[w] = [[t, max(0.2, 1.0 - 0.03 * k)] for k, t in enumerate(ts)]
        paths[g] = [[t, 1.0] for t in ts[:6]]                                       # last reading 25 min after the pick
    return rounds, paths


def test_samples_judge_every_pick_three_hours_later_and_a_vanished_coin_is_a_loss_not_a_gap():
    rounds, paths = _world()
    now = T0 + 40 * 900 + edge.HORIZON
    rows = edge.samples(rounds, paths, now)
    assert len(rows) == 120 and rows == sorted(rows, key=lambda r: r['at'])
    by = {r['mint']: r['pct'] for r in rows}
    assert by['OLD0'] > 5 and by['NEW0'] < -70 and by['GONE0'] == round(-edge.GONE * 100, 2)
    assert len(edge.samples(rounds, paths, T0 + edge.HORIZON - 1)) == 0              # nothing is judged before its outcome is known
    again = [{'at': T0 + 60, 'picks': rounds[0]['picks']}] + rounds                 # the same coin picked again a minute later
    assert len(edge.samples(again, paths, now)) == 120                               # … is one sample, not two


def test_the_table_ranks_the_survivors_first_gates_real_money_and_proves_itself_out_of_sample():
    rounds, paths = _world()
    now = T0 + 40 * 900 + edge.HORIZON
    b = edge.build(rounds, paths, now)
    t = b['table']
    assert t and b['proof']['ok'] and b['proof']['top']['medPct'] > 0 > b['proof']['bottom']['medPct'] and b['n'] == 120
    assert b['best'][0]['medPct'] > 0 and b['worst'][0]['medPct'] < -40
    old = {'mint': 'A', 'ageH': 30, 'liq': 400_000, 'mcap': 5e6, 'chg1h': 2, 'chg5m': 0.5, 'buyShare': 75, 'vol1h': 100_000, 'stage': 'graduated', 'score': 10}
    new = {'mint': 'B', 'ageH': 0.2, 'liq': 15_000, 'mcap': 20_000, 'chg1h': 300, 'chg5m': 20, 'buyShare': 51, 'vol1h': 80_000, 'stage': 'curve', 'score': 99}
    assert edge.score(old, t) > 0 > edge.score(new, t)                               # the hand-written score said the opposite
    ranked = edge.rank([new, old, {'mint': 'C'}], t)
    assert [r['mint'] for r in ranked] == ['A', 'C', 'B'] and ranked[0]['edge'] == edge.score(old, t)   # unknown features = the typical result
    major, trench = {**new, 'mint': 'M', 'newMajor': True}, {**new, 'mint': 'T', 'trenchOnly': True}
    assert [r['mint'] for r in edge.gate([new, old, major, trench], t)] == ['A', 'M', 'T']   # majors + the owner's trench choice keep their own rules
    # no table = nothing changes
    assert edge.rank([new, old], None) == [new, old] and edge.gate([new, old], None) == [new, old] and edge.score(old, None) is None


def test_a_short_record_or_a_table_that_does_not_separate_is_not_used():
    rounds, paths = _world(10)
    assert edge.build(rounds, paths, T0 + 10 * 900 + edge.HORIZON)['table'] is None   # 30 samples < MIN_SAMPLES
    rounds, paths = _world()
    for m in list(paths):                                                             # every coin ends flat: nothing to tell apart
        paths[m] = [[t, 1.0] for t, _ in paths[m]] if not m.startswith('GONE') else [[T0 + int(m[4:]) * 900 + k * 300, 1.0] for k in range(40)]
    b = edge.build(rounds, paths, T0 + 40 * 900 + edge.HORIZON)
    assert b['proof']['ok'] is False and b['table'] is None and b['n'] == 120
