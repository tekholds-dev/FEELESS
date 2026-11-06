"""Any filed proof can go with $1 or more, and what checks it fits what it is. A real trade keeps its own rule."""
import agent_features as af
import colony
import proof_validators as val

POC = {'id': 'c1', 'n': 1, 'topic': 'Narrative', 'calls': [{'post': 'A thesis long enough to count as written work on file.'}]}


def test_every_kind_of_filed_proof_can_be_picked_once():
    cat = {'id': 'a', 'pocFolders': [POC], 'psFolders': [{'id': 's1', 'n': 2, 'ws': 'w'}]}
    rows = colony.proofs_of(cat, [{'cat': 'a', 'proof': {'id': 's1'}}])
    assert {r['kind'] for r in rows} == {'PoC', 'PoS'} and next(r for r in rows if r['id'] == 's1')['used'] is True
    assert colony.attach_of(cat, [], 'c1', '')['proof']['kind'] == 'PoC'


def test_work_is_judged_on_the_work_and_the_dollars():
    ok = val.review_work(POC, 'PoC', 5.0, 'sig', (), 1); assert ok['ok'] and {s['k'] for s in ok['seats']} == set(val.SEATS)
    assert not val.review_work(POC, 'PoC', 0.5, 'sig', (), 1)['ok']                                            # under $1
    assert not val.review_work({'id': 'x', 'calls': [{'post': 'hi'}]}, 'PoC', 5.0, 'sig', (), 1)['ok']         # no real work on file
    assert not val.review_work({**POC, 'graded': 'wrong'}, 'PoC', 5.0, 'sig', (), 1)['ok']                     # its own mark says it failed
    assert not val.review_work(POC, 'PoC', 5.0, 'sig', ('sig',), 1)['ok']                                      # one transaction, once
    assert val.review_work({'id': 's', 'ws': 'w1'}, 'PoS', 2.0, 'sig', (), 1)['ok']                             # a built page is the work


def test_a_held_proof_grades_low_so_it_earns_little_until_cleared():
    import collective_stake as cs
    good = cs.grade_of(val.review_work(POC, 'PoC', 5.0, 's', (), 1), 50); held = cs.grade_of(val.review_work({'id': 'x'}, 'PoC', 0.5, 's', ('s',), 1), 50)
    assert good > held


def test_a_folder_answer_files_from_the_minds_not_the_owner():
    doc = {'messages': [{'by': 'You', 'text': 'write me a thesis please, a long one'}, {'by': 'Mind A', 'text': 'x' * 60}, {'by': 'Mind A', 'text': 'y' * 60}, {'by': 'Mind B', 'text': 'z' * 60}, {'by': 'Mind B', 'text': 'short'}]}
    rows = af.answers_of(doc, ('You',))
    assert [r['name'] for r in rows] == ['Mind A', 'Mind B'] and rows[0]['post'] == 'y' * 60 and rows[1]['post'] == 'z' * 60
    assert af.answers_of({}, ()) == []
