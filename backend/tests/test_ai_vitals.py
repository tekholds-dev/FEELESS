"""🫀 THE MODEL'S TRENCH VITALS (owner, 2026-10-12: "pull more vital info from the AI provider to trench better on coins $12K–$300K").
More vital info goes IN (the brief), more comes OUT (rug · narrative · crowd · momentum 0–100, a timing word, ≤ 4 flags), and every vital is
judged on its own record — it weighs nothing (±10% cap with the stance) until proven."""
import time

import ai_learn as al
import ai_router as air


def test_the_answer_carries_clamped_vitals_a_timing_word_and_short_flags():
    a = air.parse_advice('{"stance": "watch", "summary": "early move, bots light", "vitals": {"rug": 140, "narrative": 55.4, "crowd": -3, "momentum": "high", '
                         '"extra": 9}, "timing": "on_time", "flags": ["top10 18%", "' + 'k' * 40 + '", "", 7, "dev 0%", "a", "b"]}')
    assert a['stance'] == 'WATCH' and a['vitals'] == {'rug': 100, 'narrative': 55, 'crowd': 0}          # clamped, non-numbers and unknown keys dropped
    assert a["timing"] == "ON TIME" and len(a["flags"]) == 4 and all(len(f) <= air.FLAG_LEN + 1 for f in a["flags"])
    assert '•••' in a['flags'][1]                                                                       # a key-shaped run never reaches the page
    old = air.parse_advice('{"stance": "AVOID", "summary": "bundled"}')
    assert old and 'vitals' not in old and 'timing' not in old and 'flags' not in old                  # an answer without vitals is still valid
    assert air.parse_advice('{"stance": "AVOID", "summary": "x", "timing": "SOON"}').get('timing') is None


def test_the_prompt_asks_for_the_vitals_and_the_new_brief_fields_reach_the_model():
    sys_ = air.messages({}, 'sherlock')[0]['content']
    assert '"vitals"' in sys_ and 'EARLY|ON TIME|LATE|CHASE|DEAD' in sys_ and '"flags"' in sys_
    case = {'mint': 'M', 'symbol': 'NEW', 'band': 'EARLY TRENCH · $40K cap', 'tape': 'last 90s $900 bought vs $200 sold', 'tapeRead': 'burst', 'early': 'first-10 buyers hold 22%',
            'dev': 'dev holds 3%', 'socials': 'set: site, X', 'pump': '3 Pump callers', 'curve': 'on the launch curve 62%', 'memory': 'our real card: −8% typical',
            'record': 'AVOID −75% (4)', 'fresh': 'HIGH 15–60m', 'velocity': '$1,200/min traded', 'wallet': 'NEVER', 'url': 'https://x.com/a'}
    c = air.compact(case)
    assert all(k in c for k in ('band', 'tape', 'tapeRead', 'early', 'dev', 'socials', 'pump', 'curve', 'memory', 'record', 'fresh', 'velocity'))
    assert 'wallet' not in c and 'url' not in c                                                          # still a whitelist
    # 🪙 low usage: the detail lines change every pass and are NOT in the cache key — the tape's WORD is
    k1 = air.case_key({**case, 'tape': 'last 90s $901 bought'}, 'sherlock')
    assert k1 == air.case_key(case, 'sherlock') and k1 != air.case_key({**case, 'tapeRead': 'dump'}, 'sherlock')


def test_the_router_knows_a_case_it_already_answered():
    r = air.Router()
    case = {'mint': 'M', 'status': 'READY', 'cap': 40_000}
    assert not r.fresh(case, 'sherlock')
    r.cache[air.case_key(case, 'sherlock')] = (time.time(), {'advice': {'stance': 'WATCH'}})
    assert r.fresh(case, 'sherlock') and not r.fresh(case, 'devil')
    assert not r.fresh(case, 'sherlock', now=time.time() + air.CACHE_SEC + 1)


def test_each_vital_is_judged_on_its_own_record_and_weighs_only_when_proven():
    b = {}
    for i in range(25):   # the model said rug 80 / LATE on 25 coins that then fell 60%, rug 10 / EARLY on 25 that held
        b = al.note(b, 'sherlock', f'R{i}', 'WATCH', 1.0, 1000 + i, vitals={'rug': 80}, timing='LATE')
        b = al.note(b, 'sherlock', f'S{i}', 'WATCH', 1.0, 1000 + i, vitals={'rug': 10}, timing='EARLY')
    early = al.view(b)
    assert early['state'] == 'LEARNING' and all(r['factor'] == 1.0 for r in early['vitals'])            # nothing judged yet → nothing weighs
    b = al.settle(b, {**{f'R{i}': 0.4 for i in range(25)}, **{f'S{i}': 1.0 for i in range(25)}}, 1000 + al.JUDGE_SEC + 60)
    vr, rec = al.vital_record(b), al.record(b)
    assert vr['RUG:HIGH']['n'] == 25 and vr['RUG:HIGH']['med'] == -60 and vr['RUG:LOW']['med'] == 0
    assert al.advice_factor(rec, vr, {'stance': 'WATCH', 'vitals': {'rug': 90}}) == al.DOWN               # a proven high-rug read ranks a coin lower
    assert al.advice_factor(rec, vr, {'stance': 'WATCH', 'vitals': {'rug': 50}}) == 1.0                   # a mid read is in no bucket
    w = al.weights({'X': {'sherlock': {'advice': {'stance': 'WATCH', 'timing': 'CHASE'}, 'at': 5000}}}, rec, 5000, vr)
    assert w == {'X': al.DOWN}                                                                           # CHASE sits in the LATE bucket
    v = al.view(b)
    assert v['state'] == 'IN USE' and {r['bucket']: r['factor'] for r in v['vitals']}['RUG:HIGH'] == al.DOWN
    assert al.advice_factor(rec, vr, None) == 1.0 and al.buckets_of({}) == []


def test_the_brief_carries_the_trench_vitals_from_readings_the_desk_already_has(monkeypatch):
    import reputation_service as rs
    from trench_kernel import universe as un
    un.set_band({})
    row = {'mint': 'M1', 'symbol': 'NEW', 'pair': 'P1', 'site': 'https://a.example', 'x': True,
           'vitals': {'mcap': 45_000, 'ageH': 0.5, 'top10': 18.0, 'dev': 2.5, 'bundledN': 1, 'holders': 340, 'organic': 30, 'safe': True, 'curve': True, 'curvePct': 61},
           'nums': {'d5': 6.0, 'c1': 40.0, 'pace': 2.4, 'v5': 6_000, 'buy': 64, 'liq': 16_000}, 'li': {'first10': 22.0, 'ewp': 'POSITIVE', 'press': 'NONE', 'fresh': 'HIGH 15–60m'},
           'chart': {'state': 'UPTREND', 'entry': ['ENTER NOW', 'E1']}, 'launch': {'pad': 'pumpfun', 'curvePct': 61}, 'mind': {'callers': 2}}
    monkeypatch.setitem(rs._agents, 'table', [row])
    monkeypatch.setitem(rs._flow_now, 'P1', (time.time(), {'buyUsd': 900.0, 'sellUsd': 150.0, 'n': 14, 'pxChg': 2.1, 'bigSell': {'usd': 60.0, 'wallet': 'W'}}))
    monkeypatch.setitem(rs._pump_calls, 'map', {'M1': {'mint': 'M1', 'callers': 3, 'pro': 1, 'firstMc': 20_000, 'lead': {'mult': 2.2}}})
    monkeypatch.setattr(rs, '_real_mem', lambda now: {'base': -12.0, 'n': 40, 'cells': {'struct:UPTREND': {'est': -4.0, 'n': 9}}})
    monkeypatch.setitem(rs._ai, 'book', {'done': [{'stance': 'AVOID', 'pct': -70.0}] * 3 + [{'stance': 'WATCH', 'pct': -10.0}] * 2, 'open': []})
    b = rs._ai_brief('M1')
    assert 'inside your $12K–$300K band' in b['band'] and b['fresh'] == 'HIGH 15–60m'
    assert '$900 bought vs $150 sold' in b['tape'] and b['tapeRead'] == 'burst'
    assert 'first-10 buyers hold 22%' in b['early'] and 'early wallets positive' in b['early']
    assert b['socials'] == 'set: site, X' and 'https' not in b['socials']                               # presence only, never a link
    assert '3 Pump callers' in b['pump'] and 'proven callers 1' in b['pump'] and '2.2×' in b['pump']
    assert b['curve'] == 'on the launch curve 61%' and '-4%' in b['memory'] and 'struct:UPTREND' in b['memory']
    assert b['record'].startswith('AVOID -70% (3)') and 'your own judged calls' in b['record']
    assert '$1,200/min traded' in b['velocity']
    case = rs._ai_case({'mint': 'M1', 'symbol': 'NEW', 'status': 'READY', 'cap': 45_000})
    assert {'band', 'tape', 'early', 'pump', 'memory'} <= set(air.compact(case))


def test_every_ready_coin_in_the_band_is_asked_before_the_top_contenders(monkeypatch):
    import reputation_service as rs
    from trench_kernel import universe as un
    un.set_band({})
    cands = [{'mint': 'OUT', 'symbol': 'BIG', 'status': 'READY', 'cap': 900_000},
             {'mint': 'R1', 'symbol': 'A', 'status': 'READY', 'cap': 40_000}, {'mint': 'R2', 'symbol': 'B', 'status': 'READY', 'cap': 90_000},
             {'mint': 'C1', 'symbol': 'C', 'status': 'CONTENDING', 'cap': 60_000}, {'mint': 'C2', 'symbol': 'D', 'status': 'CONTENDING', 'cap': 70_000}]
    monkeypatch.setitem(rs._office, 'payload', {'kernel': {'candidates': cands}})
    monkeypatch.setattr(rs, '_office_state', lambda: {})
    monkeypatch.setattr(rs, '_ai_brief', lambda m: {})
    jobs = rs._ai_jobs(time.time())
    assert [(r, c['mint']) for r, c, _u in jobs] == [('sherlock', 'R1'), ('sherlock', 'R2'), ('sherlock', 'C1'), ('sherlock', 'C2')]
    assert jobs[0][2] == 'high' and len(jobs) == rs.AI_JOBS                                              # READY first, the out-of-band coin never asked
    old = rs._air.ROUTER.cache.copy()
    try:   # R1 already answered in this state → its slot goes to the next coin
        rs._air.ROUTER.cache[rs._air.case_key(rs._ai_case(cands[1]), 'sherlock')] = (time.time(), {'advice': {'stance': 'WATCH'}})
        assert 'R1' not in [c['mint'] for _r, c, _u in rs._ai_jobs(time.time())]
    finally:
        rs._air.ROUTER.cache = old
