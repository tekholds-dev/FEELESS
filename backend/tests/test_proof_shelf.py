"""Owner 2026-11-06: a $Proof folder that OSSY and G4 read first and score deeply."""
import json

import collective_git as cg
import collective_sort as cs


def test_sent_proofs_get_their_own_shelf_and_an_owner():
    files, index = cg.proof_tree([{'id': 'abc12345', 'cat': 'c', 'agent': 'tag1', 'kind': 'PoS', 'name': 'Tip Page', 'at': 5, 'usd': 5}])
    path = next(iter(files)); assert path.startswith('$Proof/PoS/tip-page') and json.loads(files[path])['usd'] == 5 and index[0]['agent'] == 'tag1' and index[0]['path'] == path


def test_they_are_read_first():
    paths = ['$Proof/PoS/a.json', 'proofs/x.json', 'snapshots/y.webp']
    assert cs.next_path(paths, {'snapshots/y.webp': {'note': 'look'}}) == '$Proof/PoS/a.json'
    done = {'votes': {w: {'marks': []} for w in cs.VOTERS}}
    assert cs.next_path(paths, {'$Proof/PoS/a.json': done}) != '$Proof/PoS/a.json'


def test_a_score_stays_inside_the_top_and_a_vague_reply_scores_nothing():
    assert cs.parse_score('{"score": 280}', 300) == 280 and cs.parse_score('{"score": 900}', 300) == 300 and cs.parse_score('{"score":"-3"}', 300) == 0
    assert cs.parse_score('looks flawless', 300) is None


def test_both_minds_must_have_read_it():
    assert cs.scores_done({'votes': {'ossy': {'score': 200}}}) is None and cs.scores_done({'votes': {'ossy': {'score': 200}, 'g4': {'score': 100}}}) == [200, 100] and cs.scores_done({}) is None


def test_a_long_file_keeps_its_start_and_end_for_a_small_model():
    t = cs.deep_excerpt(b'A' * 50000 + b'END')
    assert len(t) < cs.DEEP_CHARS + 80 and t.startswith('AAA') and t.endswith('END') and 'left out' in t and cs.deep_excerpt('short') == 'short'
