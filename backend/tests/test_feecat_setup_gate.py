import feecat_service as fs


def test_feecat_needs_a_setup_skips_the_gun_line_and_listens_to_the_models():
    assert fs.setup_gate({'_read': {'setups': [], 'bad': None}})[:2] == (False, 'no HH/HL · germ · FVG support · breakout setup')
    assert fs.setup_gate({'_read': {'setups': ['germ'], 'bad': 'pressed under its gun line'}})[0] is False
    assert fs.setup_gate({'_read': {'setups': ['hhhl']}, '_duo': {'who': 'G4', 'action': 'SELL'}})[:2] == (False, '🤝 G4 said sell')
    ok, why, mult, tags = fs.setup_gate({'_read': {'setups': ['germ', 'hhhl']}, '_duo': {'who': 'OSSY', 'action': 'BUY'}})
    assert ok and mult == 1.2 and tags == ['germ', 'hhhl'] and 'OSSY' in why
    assert fs.setup_gate({}) == (True, '', 1.0, [])   # no read yet: her own lanes decide (never MORE trades)


def test_each_new_model_lesson_lands_once_in_her_activity():
    store = {'events': [], 'cats': {fs.LEADER_ID: {'id': fs.LEADER_ID, 'name': 'Fee'}}}
    duo = {'record': {}, 'lessons': [{'who': 'G4', 'symbol': 'X', 'pct': 4.0, 'at': 10, 'lesson': 'held to the take line'}]}
    fs._duo_learn(store, duo, 100)
    fs._duo_learn(store, duo, 200)
    evs = [e for e in store['events'] if e['type'] == 'LEARN']
    assert len(evs) == 1 and 'from the FEELESS desk on $X (+4.0%)' in evs[0]['detail']
    assert store['duoLearn']['at'] == 200 and store['duoSeen'] == ['G4:10']
