import collective_sort as cs


def test_both_minds_must_agree_and_trash_waits_for_the_owner():
    i = cs.vote({}, 'ossy', 'good', 'ok', 1); assert 'status' not in i
    assert cs.vote(i, 'g4', 'good', 'ok', 2)['status'] == 'good'
    assert cs.vote(i, 'g4', 'bad', 'no', 2)['status'] == 'disputed'
    t = cs.vote(cs.vote({}, 'ossy', 'trash', '', 1), 'g4', 'trash', '', 2); assert t['status'] == 'trash_ask'
    assert cs.rule_trash(t, True)['status'] == 'trash' and cs.rule_trash(t, False)['status'] == 'bad'


def test_the_owner_always_outranks_the_minds():
    i = cs.owner_set({}, {'status': 'good', 'note': 'keep this'}, 1)
    assert cs.vote(cs.vote(i, 'ossy', 'trash', '', 2), 'g4', 'trash', '', 3)['status'] == 'good'
    assert cs.next_path(['snapshots/a.webp'], {'snapshots/a.webp': i}) is None


def test_owner_input_is_cleaned():
    i = cs.owner_set({}, {'note': 'x' * 5000, 'use': ['pow', 'nope'], 'marks': [{'x': 2, 'y': -1, 'w': .5, 'h': .5, 'label': 'l'}, {'x': 'bad'}], 'status': 'hack'}, 1)
    assert len(i['note']) == cs.MAX_NOTE and i['use'] == ['pow'] and i['marks'] == [{'x': 1.0, 'y': 0.0, 'w': .5, 'h': .5, 'label': 'l'}] and 'status' not in i


def test_only_idle_and_only_evidence():
    assert cs.idle(1, False, 0, 1000) and not cs.idle(1, True, 0, 1000) and not cs.idle(9, False, 0, 1000) and not cs.idle(1, False, 950, 1000)
    paths = ['README.md', 'kits/a.md', 'proofs/x.json', 'snapshots/b.webp', 'snapshots/c.webp']
    assert cs.next_path(paths, {}) == 'snapshots/b.webp'
    assert cs.next_path(paths, {'snapshots/c.webp': {'note': 'look'}}) == 'snapshots/c.webp'
    done = {p: {'votes': {'ossy': {}, 'g4': {}}} for p in paths}
    assert cs.next_path(paths, done) is None


def test_a_vague_reply_is_no_vote():
    assert cs.parse_vote('sure') is None and cs.parse_vote('{"verdict":"delete it"}') is None
    assert cs.parse_vote('ok {"verdict":"Good","why":"real chart"}') == ('good', 'real chart')


def test_saved_state_survives_and_counts(tmp_path):
    d = cs.load(tmp_path); assert d['on'] is True
    d['items']['a'] = {'status': 'good'}; d['items']['b'] = {'status': 'trash_ask'}; cs.save(tmp_path, d)
    x = cs.load(tmp_path); c = cs.counts(x['items'], 5); assert c['good'] == 1 and c['trash_ask'] == 1 and c['unsorted'] == 3
