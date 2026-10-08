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
