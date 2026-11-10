"""COL-1: the mission envelope reads every proof kind into one shape, never changes what it reads, and never claims more than the record holds."""
import copy
import json
from pathlib import Path

import mission
import proof_weights

FIX = json.loads((Path(__file__).parent / 'fixtures' / 'mission_folders.json').read_text())
CAT = FIX['cat']
KEY_KIND = {v[1]: k for k, v in mission.KINDS.items()}
DAY = 86400


def _fx(label):
    row = FIX['folders'][label]
    return KEY_KIND[row['key']], copy.deepcopy(row['folder'])


def _later(f):
    return float(f.get('soldAt') or f.get('closedAt') or f.get('at') or 0) + 2 * DAY


def test_every_real_shape_reads_into_one_envelope():
    want = {'v', 'id', 'kind', 'code', 'title', 'agent', 'status', 'minds', 'attribution', 'cost', 'sources', 'kits', 'artifacts', 'recordSha',
            'quality', 'outcome', 'improvement', 'evidence', 'mark', 'sent'}
    seen = set()
    for label in FIX['folders']:
        k, f = _fx(label)
        e = mission.envelope(k, f, _later(f), CAT)
        assert want <= set(e), label
        assert e['kind'] == k and e['code'] == mission.KINDS[k][0] and e['v'] == mission.VERSION
        assert e['evidence']['level'] in mission.LEVELS
        seen.add(k)
    assert seen == set(mission.KINDS)   # all six kinds, PoEco included


def test_it_never_changes_the_folder_or_the_agent():
    cat = copy.deepcopy(CAT)
    for label in FIX['folders']:
        k, f = _fx(label); before, cat_before = copy.deepcopy(f), copy.deepcopy(cat)
        e = mission.envelope(k, f, _later(f), cat)
        e['sources'].append('x'); e['minds'][0]['spentUsd'] = 99   # the envelope holds no live references back into the folder
        assert f == before and cat == cat_before, label


def test_record_sha_follows_the_record():
    k, f = _fx('pos_right')
    a = mission.envelope(k, f, _later(f), CAT)['recordSha']
    assert a == mission.envelope(k, copy.deepcopy(f), _later(f), CAT)['recordSha']
    f['graded'] = 'wrong'
    assert mission.envelope(k, f, _later(f), CAT)['recordSha'] != a


def test_improvement_is_never_claimed():
    for label in FIX['folders']:
        k, f = _fx(label)
        assert mission.envelope(k, f, _later(f), CAT)['improvement']['state'] == 'unverified'


def test_poeco_gets_no_invented_grade_or_outcome():
    k, f = _fx('poe_test_books')
    assert k == 'poe' and f.get('graded') == 'right'   # the real test folder carries a mark
    e = mission.envelope(k, f, _later(f), CAT, quality={'parts': [{'key': 'x', 'value': 1}], 'score': 300})
    assert e['quality']['state'] == 'none' and e['outcome']['state'] == 'none' and e['outcome']['won'] is None
    assert e['mark'] == 'right'   # the mark is reported as a mark, never as a result
    assert e['artifacts']['booksHash'] == f['hash'] and e['evidence']['level'] == 'L1'


def test_a_real_pow_without_chain_fills_stays_at_l1():
    k, f = _fx('pow_real_closed')
    e = mission.envelope(k, f, _later(f), CAT)
    assert e['real'] and e['outcome']['strength'] == 'server' and e['outcome']['sigs'] == []
    assert e['outcome']['state'] in ('proved', 'not') and e['evidence']['level'] == 'L1'


def test_a_chain_reconciled_pow_reaches_l2():
    k, f = _fx('pow_real_closed')
    f.update(settlementVerified=True, buySig='SIG_BUY', sellSig='SIG_SELL')
    e = mission.envelope(k, f, _later(f), CAT)
    assert e['outcome']['strength'] == 'chain' and e['outcome']['sigs'] == ['SIG_BUY', 'SIG_SELL'] and e['evidence']['level'] == 'L2'


def test_a_proposed_pow_has_no_outcome():
    k, f = _fx('pow_proposed')
    e = mission.envelope(k, f, _later(f), CAT)
    assert e['outcome']['state'] == 'none' and e['outcome']['strength'] == 'paper'


def test_who_verified_each_outcome():
    k, f = _fx('pob_scoreboard')
    e = mission.envelope(k, f, _later(f), CAT)
    assert (e['outcome']['authority'], e['outcome']['strength'], e['evidence']['level']) == ('scoreboard', 'outside', 'L2')
    for label in ('pob_owner_mark', 'poc_marked', 'pos_right'):
        k, f = _fx(label); e = mission.envelope(k, f, _later(f), CAT)
        assert (e['outcome']['authority'], e['outcome']['strength'], e['evidence']['level']) == ('owner mark', 'self', 'L1'), label
        assert e['markedBy'] == 'owner'
    k, f = _fx('pos_unmarked'); e = mission.envelope(k, f, _later(f), CAT)
    assert (e['outcome']['state'], e['outcome']['strength'], e['outcome']['won'], e['evidence']['level']) == ('unsettled', 'none', None, 'L1')


def test_no_result_is_unsettled_not_a_loss():
    k, f = _fx('pop_any')
    assert f.get('roePct') is None   # the real PoP made no trade: both minds did not agree
    e = mission.envelope(k, f, _later(f), CAT)
    assert e['outcome']['authority'] == 'true prices' and e['outcome']['state'] == 'unsettled' and e['evidence']['level'] == 'L1'
    f['roePct'] = 12.5
    e = mission.envelope(k, f, _later(f), CAT)
    assert e['outcome']['state'] == 'proved' and e['outcome']['won'] is True and e['evidence']['level'] == 'L2'


def test_waiting_until_the_day_is_up():
    k, f = _fx('pob_scoreboard')
    e = mission.envelope(k, f, float(f.get('closedAt') or f['at']), CAT)
    assert e['outcome']['state'] == 'waiting' and e['outcome']['dueAt']


def test_one_score_not_two():
    k, f = _fx('pos_right')
    assert mission.envelope(k, f, _later(f), CAT)['quality']['state'] == 'not computed'
    q = proof_weights.view(k, f)
    e = mission.envelope(k, f, _later(f), CAT, quality=q)
    assert e['quality']['state'] == 'scored' and e['quality']['score'] == q['score'] and e['quality']['rank'] == q['rank']


def test_minds_say_what_is_and_is_not_recorded():
    k, f = _fx('pow_real_closed')
    e = mission.envelope(k, f, _later(f), CAT)
    assert [m['configuredNow'] for m in e['minds']] == ['local/ossy', 'local/g4'] and all(m['local'] for m in e['minds'])
    assert all(m['answeredBy'] is None for m in e['minds']) and e['attribution'] == mission.NOT_YET
    assert e['cost']['byMind'] == {m['i']: m['spentUsd'] for m in e['minds']}
    assert 'wallet' not in json.dumps(e['agent']).lower()


def test_kinds_and_bad_input():
    k, f = _fx('pos_right')
    for name in ('pos', 'PoStatic', 'postatic'):
        assert mission.envelope(name, f, _later(f), CAT)['kind'] == 'pos'
    assert mission.kind_of('eco') == 'poe' and mission.kind_of('bids') == 'pob'
    assert mission.envelope('nope', f, 0, CAT) is None and mission.envelope('pos', None, 0, CAT) is None


def test_all_of_reads_every_kind_newest_first_and_never_scores_poeco():
    cat = copy.deepcopy(CAT); asked = []
    for row in FIX['folders'].values():
        cat.setdefault(row['key'], []).append(copy.deepcopy(row['folder']))
    rows = mission.all_of(cat, 2e9, quality_of=lambda k, f: asked.append(k) or None)
    assert len(rows) == len(FIX['folders']) and {r['kind'] for r in rows} == set(mission.KINDS)
    assert [r['at'] for r in rows] == sorted((r['at'] for r in rows), reverse=True)
    assert 'poe' not in asked and len(asked) == len(rows) - 1
