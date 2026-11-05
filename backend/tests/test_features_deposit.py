"""💵 deposit fees · ⚡ boost payouts · ✨ features · 🧬 fingerprint · 🧠 memory. Fakes only."""
import pytest

import agent_deposit as dep
import agent_features as feat
import agent_print as pr
import cat_fund as cf
import colony
import edge_files as edge
import proof_tools as pt

A, B, C, D = (str(x) for x in ('11111111111111111111111111111112', '4Nd1mBQtrMJVYVfKf2PJy9NZUZdTAsp7D4xWLs4gDB4T', 'So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'))


@pytest.mark.parametrize('usd,first,small,rate,third', [(50, True, 0, 10, False), (500, True, 0, 10, False), (50, False, 0, 10, False), (49.99, False, 0, 5, False), (10, False, 1, 5, False), (10, False, 2, 10, True), (10, False, 3, 5, False), (10, False, 5, 10, True), (100, False, 2, 10, False)])
def test_the_rate(usd, first, small, rate, third):
    q = dep.quote(usd, first, small)
    assert q['ratePct'] == rate and q['third'] is third and q['feelessUsd'] == q['collectiveUsd'] and abs(q['feelessUsd'] + q['collectiveUsd'] + q['restUsd'] - usd) < 0.011


def test_a_first_deposit_starts_at_50_and_staff_pay_nothing():
    with pytest.raises(ValueError):
        dep.quote(49.99, True, 0)
    q = dep.quote(1, True, 0, staff=True)
    assert q['ratePct'] == 0 and q['restUsd'] == 1


def test_splitting_a_big_deposit_still_pays_more_often():
    """Three $20 top-ups: 5%, 5%, then 10%."""
    rates = [dep.quote(20, False, n)['ratePct'] for n in range(3)]
    assert rates == [5, 5, 10] and dep.quote(20, False, 1)['nextIsThird'] is True


def test_only_small_top_ups_after_the_first_count():
    assert dep.small_count([{'usd': 50}, {'usd': 10}, {'usd': 60}, {'usd': 5}]) == 2 and dep.small_count([{'usd': 10}]) == 0
    assert dep.is_first({}) and not dep.is_first({'agentFunded': [{}]}) and not dep.is_first({'creditPaid': [{}]})


def test_the_plan_moves_each_cut_and_the_amounts_add_up():
    pl = cf.plan(100, 200, False, fee_usd=0, min_usd=1, credit_usd=20, credit_to_wallet=True)
    out = dep.apply(pl, dep.quote(100, True, 0))
    assert out['feeLamports'] == 25_000_000 and out['colonyLamports'] == 25_000_000 and out['feeLamports'] + out['colonyLamports'] + out['catLamports'] == pl['totalLamports'] and out['catUsd'] == 90


def test_model_credit_cannot_eat_the_fee():
    pl = cf.plan(50, 200, False, fee_usd=0, min_usd=1, credit_usd=50, credit_to_wallet=True)
    with pytest.raises(ValueError):
        dep.apply(pl, dep.quote(50, True, 0))


def test_one_transaction_has_all_three_legs():
    from solders.transaction import VersionedTransaction
    import base64
    pl = dep.apply(cf.plan(100, 200, False, fee_usd=0, min_usd=1, credit_to_wallet=True), dep.quote(100, True, 0))
    bh = '11111111111111111111111111111111'
    tx = VersionedTransaction.from_bytes(base64.b64decode(cf.build(A, B, C, pl, bh, D)))
    keys = [str(k) for k in tx.message.account_keys]
    assert all(k in keys for k in (A, B, C, D)) and len([i for i in tx.message.instructions if str(tx.message.account_keys[i.program_id_index]) == '11111111111111111111111111111111']) == 3
    with pytest.raises(ValueError):
        cf.build(A, B, C, pl, bh, None)
    with pytest.raises(ValueError):
        cf.build(A, B, C, pl, bh, C)


def test_a_boost_takes_a_bigger_part_but_the_pot_pays_the_same():
    shares = [{'at': 10, 'owner': 'a', 'sent': True, 'sig': 's', 'sol': 1}, {'at': 10, 'owner': 'b', 'sent': True, 'sig': 't', 'sol': 1}]
    r = {x['owner']: x for x in colony.airdrop(shares, {'a', 'b'}, 300, 0, {'a': 100})}
    assert r['a']['usd'] == 200 and r['b']['usd'] == 100 and r['a']['boost'] == 2.0
    r = {x['owner']: x for x in colony.airdrop(shares, {'a', 'b'}, 300, 0, {'a': 100}, 'rank')}
    assert r['a']['usd'] == 150 and r['b']['usd'] == 150
    assert colony.boost_weight(100000) == 2.0 and colony.clean_policy({'boostMode': 'rank'})['boostMode'] == 'rank' and colony.clean_policy({'boostMode': 'x'})['boostMode'] == 'payout'


def test_folder_limits_and_clean_names():
    cat = {}
    row = feat.new_folder(cat, 'build', '<script>alert(1)</script> Site', 1)
    assert '<' not in row['name'] and row['kind'] == 'build' and feat.clean_kind('nope') is None
    for _ in range(feat.MAX_FOLDERS - 1):
        feat.new_folder(cat, 'edge', '', 1)
    with pytest.raises(ValueError):
        feat.new_folder(cat, 'edge', '', 1)


def test_a_dragged_box_becomes_words_and_the_helper_stays_in_its_sandbox():
    n = feat.region_note({'x': .1, 'y': .2, 'w': .5, 'h': 9, 'html': '<b>x</b>' * 400})
    assert '10% across' in n and '100% tall' in n and len(n) < 800 and feat.region_note('nope') == ''
    assert 'feeless-pick' in feat.preview('<html><body>a</body></html>') and 'fetch' not in feat.PICKER


def test_fresh_memory_keeps_its_record():
    cat = {'personal': 'x', 'brainsCfg': {'cloud': [{}], 'minds': {'m': [{}]}}, 'powFolders': [{'id': 1}], 'boosts': [{}]}
    feat.memory_fresh(cat, 5)
    assert cat['brainsCfg']['cloud'] == [] and cat['brainsCfg']['minds'] == {} and cat['personal'] == '' and cat['powFolders'] and cat['boosts'] and feat.memory_view(cat)['freshAt'] == 5


def _pow(pnl, src='pump', at=1000):
    return {'status': 'closed', 'pnlSol': pnl, 'soldAt': at, 'mint': 'M', 'coins': [{'mint': 'M', 'src': src, 'liq': 30e3, 'mc': 1e6}]}


def test_the_fingerprint_weighs_wins_and_fades():
    now = 1000
    p = pr.build({'powFolders': [_pow(1)] * 3 + [_pow(-1, 'dex')] * 3, 'pobFolders': [{'topic': 'lakers', 'graded': 'right', 'at': now}]}, now)
    by = {t['t']: t for t in p['traits']}
    assert by['source pump']['score'] == 3 and by['source dex']['score'] == -3 and by['topic lakers']['won'] == 1 and p['proofs'] == 7 and 0 < p['level'] < 100
    old = pr.build({'powFolders': [_pow(1, at=0)]}, pr.HALF_LIFE_S)
    assert {t['t']: t for t in old['traits']}['source pump']['score'] == 0.5


def test_outsiders_see_a_level_and_nothing_inside():
    p = pr.build({'powFolders': [_pow(1)] * 3}, 1000); pub = pr.public(p)
    assert set(pub) == {'level', 'proofs', 'kinds'} and 'pump' not in str(pub)
    assert 'strongest on source pump' in pr.note(p) and pr.note({}) == ''


def test_edge_files_are_complete_and_indicators_are_ours():
    rows = edge.rows()
    assert len(rows) >= 24 and all(all(r[k] for k in edge.FIELDS) and r['cat'] in edge.CATEGORIES for r in rows) and len({r['id'] for r in rows}) == len(rows)
    assert all(v[1].startswith('//@version=5') and 'FEELESS' in v[1] for v in edge.INDICATORS.values()) and 'check' in edge.checklist()


def test_book_and_news_parsing():
    b = pt.parse_book({'levels': [[{'px': '100', 'sz': '3'}], [{'px': '101', 'sz': '1'}]]})
    assert b['spread'] == 1 and b['tilt'] == 0.75 and pt.parse_book(None) is None
    assert pt.parse_rss('<rss><channel><item><title><![CDATA[Hello]]></title></item></channel></rss>') == ['Hello']
