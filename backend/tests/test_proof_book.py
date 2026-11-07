import pytest

import proof_book as pb


def test_an_untouched_proof_keeps_the_engines_own_order():
    assert pb.apply({}, 'pob', ['espn.com', 'covers.com']) == ['espn.com', 'covers.com']
    assert pb.rank(None, 'pow', ['solscan.io', 'rugcheck.xyz']) == ['solscan.io', 'rugcheck.xyz']
    assert pb.goal_line({}, 'pop') == ''


def test_the_owners_order_goes_first_and_an_off_site_is_never_opened():
    book = {'pob': pb.clean('pob', {'order': ['https://www.Covers.com/nba', 'rotowire.com', 'espn.com'], 'off': ['espn.com']})}
    assert book['pob'] == {'order': ['covers.com', 'rotowire.com', 'espn.com'], 'off': ['espn.com']}
    assert pb.apply(book, 'pob', ['espn.com', 'nba.com', 'covers.com']) == ['covers.com', 'rotowire.com', 'nba.com']
    assert 'Never open espn.com' in pb.goal_line(book, 'pob')


def test_a_pow_drops_rugcheck_when_switched_off_but_keeps_a_required_site():
    book = {'pow': pb.clean('pow', {'order': ['dexscreener.com', 'solscan.io', 'rugcheck.xyz', 'birdeye.so'], 'off': ['rugcheck.xyz', 'solscan.io']})}
    assert pb.rank(book, 'pow', ['solscan.io', 'rugcheck.xyz', 'birdeye.so', 'dexscreener.com'], keep=['solscan.io']) == ['solscan.io', 'dexscreener.com', 'birdeye.so']


def test_bad_lists_are_refused():
    with pytest.raises(ValueError):
        pb.clean('poc', {'order': ['a.com', 'b.com']})
    with pytest.raises(ValueError):
        pb.clean('pob', {'order': ['espn.com', 'covers.com'], 'off': ['espn.com']})   # one site left on
    assert pb.clean('pow', {'order': ['dexscreener.com', 'mysite.com', 'solscan.io']})['order'] == ['dexscreener.com', 'solscan.io']   # a PoW opens coin pages by address
    assert pb.host('http://localhost:8000') == '' and pb.host('192.168.1.2') == ''


def test_the_folder_view_lists_placed_sites_then_the_rest():
    rows = pb.view({'pop': {'order': ['x.com', 'mydesk.io'], 'off': ['x.com']}}, 'pop')
    assert rows[0] == {'host': 'x.com', 'on': False, 'mine': False} and rows[1]['mine'] and len(rows) == len(pb.DEFAULTS['pop']) + 1
