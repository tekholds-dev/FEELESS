import after_path as ap
import office as of


def test_a_soft_exit_that_keeps_losing_to_holding_is_benched_and_stops_selling():
    pos, done = [], {}
    for i in range(30):
        p = {'id': f'p{i}', 'mint': f'M{i}', 'since': i, 'confirmed': True, 'realPct': 2.0, 'rule': 'R6 take line'}
        pos.append(p); done[ap.key_of(p)] = [3.0, 9.0 if i % 4 else 0.0]      # 30 min later the coin sat at +9% (3 in 4 times)
    b = ap.rule_bench(pos, done, {'R6'})
    assert b['R6']['benched'] and b['R6']['n'] == 30 and b['R6']['held'] == 7.0
    assert not ap.rule_bench(pos[:29], done, {'R6'})['R6']['benched']            # under 30 exits: not judged
    good = [{**p, 'id': 'g' + p['id']} for p in pos]
    done2 = {ap.key_of(p): [-20.0] for p in good}
    assert not ap.rule_bench(good, done2, {'R6'})['R6']['benched']               # selling beat holding: stays
    assert 'R7' in of.SOFT_EXITS and hasattr(of, 'BENCHED')
