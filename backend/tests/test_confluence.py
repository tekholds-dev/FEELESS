import confluence as cf

LREC = {'ptrend': {'n': 60, 'medPct': -1.5}, 'movers': {'n': 60, 'medPct': -87.0}, 'fed': {'n': 42, 'medPct': -0.5}, 'pump': {'n': 3, 'medPct': 50}}
CREC = {'bond': {'n': 52, 'medPct': -81.7}, 'cooling': {'n': 60, 'medPct': -3.6}}


def test_evidence_beats_hype_a_bond_run_in_movers_ranks_under_a_cooling_pump_trending_coin():
    lists = {'movers': [{'mint': 'B', 'tv': {'call': ['🎢', 'BOND RUN', 'good']}}], 'ptrend': [{'mint': 'P', 'tv': {'call': ['🧊', 'COOLING', 'warn']}}], 'fed': [{'mint': 'P'}]}
    key = {'BOND RUN': 'bond', 'COOLING': 'cooling'}
    out = cf.rank(lists, LREC, CREC, call_key_of=lambda r: key.get(((r.get('tv') or {}).get('call') or [0, ''])[1]))
    assert [r['mint'] for r in out] == ['P', 'B']
    p = out[0]['edge']
    assert p['lists'] == ['ptrend', 'fed'] and p['known'] == 2 and out[1]['edge']['edge'] < -80


def test_unproven_list_adds_nothing_and_a_learned_combo_counts_once_settled():
    e = cf.edge({}, {'pump': 1}, LREC, CREC)
    assert e['edge'] == 0 and e['known'] == 0   # pump has 3 settled — not evidence yet
    row = {'vol1h': 10000, 'vol5m': 1500, 'tv': {'call': ['🔥', 'SEND IT', 'good']}}
    b = cf.bucket(2, 'good', 1.8)
    e2 = cf.edge(row, {'ptrend': 1, 'fed': 3}, LREC, {}, {b: {'n': 9, 'medPct': 12.0}})
    assert e2['bucket'] == b and any(p[0].startswith('combo') and p[1] == 12.0 for p in e2['parts'])


def test_hand_set_tilts_are_capped_and_labelled():
    row = {'vital': {'score': 100, 'organicPct': 40}, 'pc': {'pros': 2}}
    e = cf.edge(row, {}, {}, {})
    assert e['edge'] == cf.TILT_MAX and 'hand-set' in e['parts'][-1][0]


def test_gather_merges_one_row_per_coin_with_every_rank():
    g = cf.gather({'ptrend': [{'mint': 'A', 'symbol': 'A'}], 'volume': [{'baseAddress': 'X'}, {'mint': 'A', 'liq': 5}]})
    assert g['A'][1] == {'ptrend': 1, 'volume': 2} and g['A'][0]['liq'] == 5 and 'X' in g
