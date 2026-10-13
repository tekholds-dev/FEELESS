"""🎓 Teach the desk: the owner's notes, narratives and chart lessons reach every fitting model case; reads on taught coins are graded apart."""
import pytest
import teach as T
import ai_learn as ail

M = 'So11111111111111111111111111111111111111112'


def test_a_teaching_is_cleaned_and_only_our_own_uploads_are_kept_as_images():
    t = T.clean({'kind': 'chart', 'text': '  bought the reclaim\x00 of the 15m base  ', 'img': '/api/reputation/uploads/abc123.webp', 'mint': M, 'sym': 'SOL'})
    assert t == {'kind': 'chart', 'text': 'bought the reclaim of the 15m base', 'img': '/api/reputation/uploads/abc123.webp', 'mint': M, 'sym': 'SOL'}
    assert 'img' not in T.clean({'kind': 'chart', 'text': 'lesson', 'img': 'https://evil.example/x.png'})
    assert T.clean({'kind': 'yolo', 'text': 'x y z'}) is None and T.clean({'kind': 'note', 'text': 'a'}) is None
    with pytest.raises(ValueError):
        T.add({}, {'kind': 'note', 'text': ''})
    assert T.words('AI agent coins running, cat meta cooling') == ['agent', 'running', 'cat', 'cooling']


def test_every_fitting_case_reads_the_owners_words_and_taught_reads_are_graded_apart():
    st = T.add({}, {'kind': 'narrative', 'text': 'frog season — frogs with a site and X keep running'}, 100)
    st = T.add(st, {'kind': 'note', 'text': 'never chase a +15% five minute candle'}, 101)
    st = T.add(st, {'kind': 'chart', 'text': 'entries on the first higher low after the bond dip'}, 102)
    st = T.add(st, {'kind': 'note', 'text': 'this one has a real dev', 'mint': M}, 103)
    lines = T.for_case(st, 'FROGGY', None)
    assert lines[0].startswith('owner narrative on this coin: frog season') and any(l.startswith('owner chart lesson') for l in lines) and any('chase' in l for l in lines)
    assert T.for_case(st, 'XYZ', M)[0] == 'owner note on this coin: this one has a real dev'
    assert T.hits(st, 'DOGE', None) == [] and len(T.remove(st, st['items'][0]['id'])['items']) == 3
    v = T.view(st)
    assert v['counts'] == {'note': 2, 'narrative': 1, 'chart': 1} and 'frog' in v['narratives']
    b = ail.note({}, 'sherlock', M, 'CAUTION', 1.0, 100.0, 'X', 0, None, False, True)
    assert 'TAUGHT' in ail.buckets_of(b['open'][0])
