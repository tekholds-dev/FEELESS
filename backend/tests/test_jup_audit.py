import jup_audit as ja

TIKTOK = {'id': 'M', 'holderCount': 3103, 'dev': 'D', 'audit': {'mintAuthorityDisabled': True, 'freezeAuthorityDisabled': True, 'topHoldersPercentage': 19.2,
          'devMigrations': 22, 'devMints': 1076}, 'organicScore': 52.4, 'organicScoreLabel': 'medium',
          'stats1h': {'buyVolume': 1150083, 'sellVolume': 1125795, 'buyOrganicVolume': 30576, 'sellOrganicVolume': 32279, 'numTraders': 4796, 'numOrganicBuyers': 36}}


def test_facts_crew_and_lite_intel_from_jupiters_audit():
    f = ja.facts(TIKTOK)
    assert f['top10'] == 19.2 and f['devMints'] == 1076 and f['devGrads'] == 22 and f['holders'] == 3103 and f['mintOff'] and f['freezeOff']
    assert 2.5 < f['organicPct'] < 3.0 and f['realBuyers1h'] == 36
    assert ja.crew(f)['kind'] == 'serial'                                                         # 1,076 launches, 22 graduated
    assert ja.crew({'devMints': 10, 'devGrads': 4})['kind'] == 'popular'
    assert ja.crew({'devMints': 1, 'devGrads': 0})['kind'] == 'fresh' and ja.crew({})['kind'] == 'unknown'
    it = ja.lite_intel(f)
    assert it['top10Pct'] == 19.2 and it['insidersHoldingPct'] is None and it['bundledWallets'] is None and it['source'] == 'jupiter' and it['creator'] == 'D'
    assert ja.lite_intel({'top10': None}) is None


def test_the_vital_names_what_decides_it_and_live_authority_is_an_F():
    v = ja.verdict(ja.facts(TIKTOK))
    texts = [t for _i, t, _tone in v['flags']]
    assert any('serial launcher' in t for t in texts) and any('bots' in t for t in texts) and len(v['flags']) <= 3
    assert v['bars']['crew'] < 0.3 and v['bars']['flow'] < 0.1 and v['grade'] in 'CDF'
    good = ja.verdict({'top10': 14, 'devPct': 0.5, 'devMints': 8, 'devGrads': 5, 'organicPct': 45, 'traders1h': 900, 'mintOff': True, 'freezeOff': True})
    assert good['grade'] in 'AB' and good['tone'] == 'good' and good['crew']['kind'] == 'popular'
    assert ja.verdict({'top10': 14, 'mintOff': False})['grade'] == 'F' and ja.authority_bad({'freezeOff': False})
    assert ja.verdict({'top10': 14}, {'bundledN': 5})['flags'][0][1] == '5 bundled wallets'   # our own scan's bundles count when it has them


def test_growth_signals_and_the_owners_vital_filter():
    f = ja.facts({**TIKTOK, 'stats1h': {**TIKTOK['stats1h'], 'holderChange': 40, 'numNetBuyers': 2692, 'liquidityChange': 5}})
    v = ja.verdict(f)
    assert v['bars']['growth'] > 0.7 and list(v['bars'])[0] == 'flow' and v['organicPct'] == f['organicPct']
    drained = ja.verdict({**f, 'liqChg1h': -60})
    assert any('pool drained' in t for _i, t, _tone in drained['flags']) and drained['bars']['growth'] < v['bars']['growth']
    assert ja.filter_why(f, None, {}) is None                                          # no filter set = nothing judged
    assert 'serial launcher' in ja.filter_why(f, None, {'noSerial': True})
    assert 'organic' in ja.filter_why(f, None, {'organicMin': 10})
    assert 'vital' in ja.filter_why(f, None, {'vitalMin': 65})
    assert ja.filter_why(None, None, {'vitalMin': 65}) is None                          # no reading = not judged
    import arena_prime as ap
    c = ap.clean_cfg({'vitalMin': 50, 'organicMin': 20, 'noSerial': True})
    assert (c['vitalMin'], c['organicMin'], c['noSerial']) == (50, 20, True) and ap.clean_cfg({'vitalMin': 7})['vitalMin'] == 0


def test_trench_vital_heat_vs_rug_and_the_call():
    hot = ja.trench_verdict({'holderChg1h': 120, 'netBuyers1h': 300, 'traders1h': 500, 'devMints': 6, 'devGrads': 3, 'organicPct': 20, 'top10': 14, 'mintOff': True, 'freezeOff': True},
                            {'vol1h': 40000, 'vol5m': 9000, 'buyShare': 66, 'chg5m': 8, 'ageH': 1.5, 'site': 'x', 'x': 'y', 'top10': 14, 'bundledN': 0, 'snipersN': 2, 'dev': 0})
    assert hot['call'][1] == 'SEND IT' and hot['heat'] >= 60 and hot['rug'] <= 35
    assert any('5m pace' in t for _i, t, _c in hot['tags'])
    bait = ja.trench_verdict({'devMints': 900, 'devGrads': 3, 'organicPct': 1, 'top10': 60}, {'top10': 60, 'bundledN': 6, 'snipersN': 30, 'dev': 12, 'ageH': 0.1, 'site': None, 'x': None})
    assert bait['call'][1] == 'RUG BAIT' and bait['rug'] >= 65 and bait['tags'][0][2] == 'bad'
    assert ja.trench_verdict({'mintOff': False}, {})['call'][1] == 'RUG BAIT'
    cold = ja.trench_verdict({}, {'vol1h': 40000, 'vol5m': 300, 'buyShare': 40, 'chg5m': -6})
    assert cold['call'][1] == 'COLD' and any('fading' in t for _i, t, _c in cold['tags'])
    chase = ja.trench_verdict({}, {'chg5m': 80})
    assert any('chasing' in t for _i, t, _c in chase['tags'])


def test_send_it_calls_are_scored_and_the_engine_waits_for_proof(monkeypatch):
    import asyncio, json
    import reputation_service as rs
    hot = {'mint': 'H', 'symbol': 'HOT', 'price': 1.0, 'safe': True, 'vol1h': 40000, 'vol5m': 9000, 'buyShare': 66, 'chg5m': 8, 'ageH': 1.5, 'site': 'x', 'x': 'y', 'top10': 14}
    cold = {'mint': 'C', 'symbol': 'ICE', 'price': 1.0, 'safe': True, 'vol1h': 40000, 'vol5m': 300, 'buyShare': 40, 'chg5m': -6}
    monkeypatch.setattr(rs, '_open_pairs', [1])
    monkeypatch.setattr(rs, '_open_board', lambda: [hot, cold])
    async def lite(ms): return {}
    async def prices(ms): return {m: 1.2 for m in ms}
    monkeypatch.setattr(rs, '_jup_lite', lite); monkeypatch.setattr(rs, '_jup_prices', prices)
    rs._jup_facts['H'] = (0, {'holderChg1h': 120, 'netBuyers1h': 300, 'traders1h': 500, 'devMints': 6, 'devGrads': 3, 'organicPct': 20, 'top10': 14})
    asyncio.run(rs._call_track(1000.0))
    st = json.loads(rs.CALL_PROOF_PATH.read_text())
    assert 'H' in st['send']['open'] and 'C' in st['cold']['open']
    assert [r['symbol'] for r in rs._call_cache['send']] == ['HOT'] and not rs._sendit_ready()   # nothing settled yet → the engine waits
    asyncio.run(rs._call_track(1000.0 + 3700))                                                   # an hour later: settled at +20%
    assert rs._call_cache['proof']['send']['n'] == 1 and rs._call_cache['proof']['send']['medPct'] == 20.0
    assert not rs._sendit_ready()                                                                # 1 settled < 10 → still waiting
    rs._call_cache['proof'] = {'send': {'n': 12, 'medPct': 8.0, 'wonPct': 60, 'proven': True}}
    assert rs._sendit_ready()
    import arena_prime as ap
    assert ap.clean_cfg({})['sendItAuto'] is True and ap.clean_cfg({'sendItAuto': False})['sendItAuto'] is False


def test_curve_dip_reads_and_the_dead_check():
    rush = ja.curve_verdict({}, {'curvePct': 22, 'curveSpeed': 12, 'vol1h': 20000, 'vol5m': 6000, 'buyShare': 70, 'chg5m': 9})
    assert rush['call'][1] == 'EARLY RUSH' and rush['kind'] == 'curve' and rush['meters'][0] == ['🎢 BOND', 22]
    bond = ja.curve_verdict({}, {'curvePct': 85, 'curveSpeed': 10, 'vol1h': 30000, 'vol5m': 6000, 'buyShare': 62, 'chg5m': 4})
    assert bond['call'][1] == 'BOND RUN' and any('to bond' in t for _i, t, _c in bond['tags'])
    assert ja.curve_verdict({}, {'curvePct': 50, 'chg5m': -20, 'buyShare': 35})['call'][1] == 'DUMPING'
    dip = ja.dip_verdict({'holderChg1h': 5, 'netBuyers1h': 120, 'traders1h': 200}, {'chg1h': -30, 'chg5m': 4, 'buyShare': 64, 'vol1h': 50000, 'vol5m': 5000})
    assert dip['call'][1] == 'BUY THE DIP' and dip['meters'][0][0] == '🧲 BOUNCE'
    knife = ja.dip_verdict({'holderChg1h': -8, 'liqChg1h': -30}, {'chg1h': -40, 'chg5m': -9, 'buyShare': 35, 'vol1h': 50000, 'vol5m': 5000})
    assert knife['call'][1] == 'FALLING KNIFE'
    assert ja.dip_verdict({}, {'chg1h': -40, 'vol1h': 900})['call'][1] == 'DEAD DIP'
    assert ja.dead_why({'vol1h': 900}) and ja.dead_why({'vol1h': 50000, 'vol5m': 0}) and ja.dead_why({'vol1h': 50000, 'txns1h': 5})
    assert ja.dead_why({'vol1h': 50000, 'vol5m': 2000, 'txns1h': 300}) is None
    assert ja.pick_read({}, {'curvePct': 30})['kind'] == 'curve' and ja.pick_read({}, {'chg1h': -25})['kind'] == 'dip'
    assert ja.pick_read({}, {'ageH': 1})['kind'] == 'trench' and ja.pick_read({}, {'ageH': 50, 'chg1h': 5}) is None
