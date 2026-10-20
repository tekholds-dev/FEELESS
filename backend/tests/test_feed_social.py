import pytest
import feed_social as fs


def test_like_toggles_once_per_wallet_and_counts_batch():
    st = {}
    assert fs.like(st, 'w1', 'tg:abc', 1) == (True, 1)
    assert fs.like(st, 'w2', 'tg:abc', 2) == (True, 2)
    assert fs.like(st, 'w1', 'tg:abc', 3) == (False, 1)
    c = fs.counts(st, ['tg:abc', 'none', 'bad id!'], me='w2')
    assert c['tg:abc'] == {'likes': 1, 'comments': 0, 'mine': True} and c['none']['likes'] == 0 and 'bad id!' not in c
    assert 'none' not in st['posts']


def test_comments_are_trimmed_capped_and_need_text():
    st = {}
    for i in range(70):
        fs.comment(st, 'w', 'me', 'p1', f'  gm {i} ', i)
    th = fs.thread(st, 'p1')
    assert len(th) == fs.COMMENTS_MAX and th[-1]['text'] == 'gm 69'
    with pytest.raises(ValueError):
        fs.comment(st, 'w', 'me', 'p1', '   ', 1)


def test_store_drops_the_oldest_posts_past_the_cap(monkeypatch):
    monkeypatch.setattr(fs, 'POSTS_MAX', 3)
    st = {}
    for i in range(5):
        fs.like(st, 'w', f'p{i}', i)
    assert sorted(st['posts']) == ['p2', 'p3', 'p4']
