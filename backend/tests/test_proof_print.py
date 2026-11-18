"""🧬 owner 2026-11-17: "true fingerprinting … each proof type should have unique fingerprints". Pure; no network."""
import proof_print as pp

POB = {'id': 'p1', 'n': 1, 'at': 1, 'topic': 'Jazz vs Clippers', 'games': [{'id': '401910006'}], 'kalshi': {'ticker': 'KXNBAGAME-X-LAC', 'side': 'yes'},
       'browsed': {'0': {'sites': ['espn.com', 'foxsports.com']}}, 'calls': [{'mind': 0, 'picks': [{'pick': 'Clippers to win', 'confidence': 68}]}]}


def test_the_same_work_has_the_same_print_and_any_new_fact_changes_it():
    a = pp.of('pob', POB); b = pp.of('pob', {**POB, 'id': 'other', 'at': 999})
    assert a['digest'] == b['digest'] and a['id'].startswith('PoB-') and len(a['id']) == len('PoB-XXXX-XXXX')   # never its id or its time
    assert pp.digest('pob', {**POB, 'kalshiPicks': [{'ticker': 'KXNBASPREAD-X-LAC5', 'side': 'yes'}]}) != a['digest']
    assert pp.digest('pob', {**POB, 'browsed': {'0': {'sites': ['espn.com', 'rotowire.com']}}}) != a['digest']
    assert pp.digest('pow', POB) != a['digest']   # each kind reads its own facts


def test_each_kind_is_read_by_its_own_rules():
    assert pp.traits('pob', POB) == ['1 game', '1 Kalshi bet', '2 sites', '0 agreed']
    assert pp.evidence('pow', {'mint': 'M1', 'buyPx': 0.1})['coin'] == 'M1' and pp.traits('pow', {'mint': 'Mabcdefg', 'buyPx': 0.1})[-1] == 'traded'
    assert pp.evidence('pop', {'market': 'SOL', 'side': 'long'})['market'] == 'SOL' and pp.traits('pop', {'market': 'SOL', 'side': 'long'})[:2] == ['SOL', 'long']
    assert pp.evidence('ps', {'code': '<p>a</p>'})['code'] != pp.evidence('ps', {'code': '<p>b</p>'})['code']
    assert pp.traits('poe', {'hash': 'abcdef123'}) == ['hash abcdef']


def test_how_new_it_is_beside_the_proofs_of_its_kind_before_it():
    first = pp.of('pob', POB)
    assert first['uniquePct'] == 100 and first['nearest'] is None
    again = pp.of('pob', {**POB, 'id': 'p2', 'n': 2, 'at': 2}, [POB]); assert again['uniquePct'] == 0 and again['nearest'] == 1 and 'espn.com' in again['shared']
    fresh = pp.of('pob', {**POB, 'id': 'p3', 'n': 3, 'at': 3, 'topic': 'Hornets vs Lakers', 'games': [{'id': '9'}], 'kalshi': None, 'calls': [], 'browsed': {'0': {'sites': ['covers.com']}}}, [POB])
    assert fresh['uniquePct'] == 100
    rows = pp.all_of({'pobFolders': [POB, {**POB, 'id': 'p2', 'n': 2, 'at': 2}], 'psFolders': [{'id': 's1', 'code': 'x'}]})
    assert set(rows) == {'p1', 'p2', 's1'} and rows['p2']['uniquePct'] == 0 and rows['s1']['kind'] == 'ps'
