import ai_duet as d
import ai_learn
import ai_router


def _c(prov, mint, stance, pct, at):
    return {'prov': prov, 'mint': mint, 'stance': stance, 'pct': pct, 'at': at}


def test_agreed_stance_stands_and_a_split_is_neutral_until_one_model_proves_it_wins_splits():
    m = d.merge({'stance': 'CAUTION', 'risk_flags': ['dev 40%']}, {'stance': 'CAUTION', 'risk_flags': ['top10 80%']})
    assert m['agree'] is True and m['stance'] == 'CAUTION' and m['flags'] == ['dev 40%', 'top10 80%']
    assert d.merge({'stance': 'CAUTION'}, {'stance': 'FAVOR'})['stance'] == 'NEUTRAL'
    # Gemma right on 12 of 12 called splits, Qwen on none → the pair listens to Gemma
    done = []
    for i in range(12):
        done += [_c('lan', f'm{i}', 'CAUTION', -20, 100 * i), _c('local', f'm{i}', 'FAVOR', -20, 100 * i + 30)]
    rec = d.record(done)
    assert rec['pairs'] == 12 and rec['agreePct'] == 0 and rec['leadPct'] == 100 and rec['secondPct'] == 0
    assert d.trusted(rec) == 'lan'
    assert d.merge({'stance': 'CAUTION'}, {'stance': 'FAVOR'}, rec)['stance'] == 'CAUTION'


def test_reads_far_apart_are_not_a_pair_and_the_second_only_rereads_real_calls():
    assert d.pairs([_c('lan', 'x', 'FAVOR', 5, 0), _c('local', 'x', 'FAVOR', 5, 5000)]) == []
    assert d.second_due({'stance': 'NEUTRAL'}, 0, 1000) is False
    assert d.second_due({'stance': 'CAUTION'}, 0, 1000) is True
    assert d.second_due({'stance': 'CAUTION'}, 0, 1000, lagging=True) is False
    assert d.second_due({'stance': 'CAUTION'}, 950, 1000) is False


def test_both_models_keep_their_own_call_on_the_same_coin():
    b = ai_learn.note({}, 'sherlock', 'M', 'CAUTION', 1.0, 100, src='lan')
    b = ai_learn.note(b, 'sherlock', 'M', 'CAUTION', 1.0, 110, src='local')
    assert [c['prov'] for c in b['open']] == ['lan', 'local']


def test_an_agreed_duet_caution_may_hold_a_seat_a_lone_small_model_may_not():
    adv = {'stance': 'CAUTION', 'confidence_delta': -0.3, 'risk_flags': ['dev holds 60%'], 'summary': 'dev bag'}
    lone = {'sherlock': {'source': 'lan', 'advice': adv, 'at': 100}}
    assert ai_router.gate_verdict(lone, 110) == (None, None)
    duet = {**lone, 'duet': {'source': 'duet', 'at': 100, 'advice': {**adv, 'agree': True}}}
    assert ai_router.gate_verdict(duet, 110)[0] == 'wait'


def test_chat_reply_shows_both_models():
    assert d.combine('a', 'b').startswith('🖥 G4') and '💻 OSSY' in d.combine('a', 'b')
    assert d.combine('a', None) == 'a'
    assert 'PUSH BACK' in d.second_prompt('why?', 'because')


def test_each_local_model_has_its_own_name_in_the_owners_chat():
    env = {'LAN_LLM_NAME': 'Vega'}
    assert 'Your name is Vega' in ai_router.identity_line(env, 'lan') and 'partner model is OSSY' in ai_router.identity_line(env, 'lan')
    assert ai_router.identity_line(env, 'groq') == ''
    assert 'LATEST message' in ai_router.GENERAL_SYSTEM and 'yurrr' in ai_router.GENERAL_SYSTEM
    assert d.combine('a', 'b', {'lan': 'Vega', 'local': 'Kai'}).startswith('🖥 VEGA\n')


def test_a_read_at_the_top_of_a_spike_holds_the_buy():
    top = {'groq': {'source': 'groq', 'at': 100, 'advice': {'stance': 'NEUTRAL', 'confidence_delta': 0, 'chart_phase': 'LATE FOMO', 'summary': 'up 300% in 10 min'}}}
    assert ai_router.gate_verdict(top, 110)[0] == 'wait'
    lone = {'sherlock': {'source': 'lan', 'at': 100, 'advice': {'stance': 'NEUTRAL', 'timing': 'CHASE'}}}
    assert ai_router.gate_verdict(lone, 110)[0] != 'wait'          # a lone small model still never holds a seat
    ok = {'groq': {'source': 'groq', 'at': 100, 'advice': {'stance': 'FAVOR', 'confidence_delta': 0.1, 'chart_phase': 'EARLY ACCELERATION'}}}
    assert ai_router.gate_verdict(ok, 110) == ('go', None)
