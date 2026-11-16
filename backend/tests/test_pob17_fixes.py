"""Owner 2026-11-15 PoB #17: a refused Kalshi bid says so in chat; minds may repeat a backed pick; proofs never tour FEELESS."""
import agent_knows as ak
import kalshi_bid as kb
import proof_footprint as fp


def test_shard_refusal_reads_plain():
    w = kb.plain_why('Kalshi refused the order (404): {"error":{"code":"insufficient_shard_balance"}}')
    assert 'Exchange Indexes' in w and 'Approve' in w
    assert 'does not cover' in kb.plain_why('x insufficient_balance y')
    assert kb.plain_why('') and kb.plain_why('odd') == 'odd'


def test_proof_prompt_has_no_feeless_tour():
    assert 'Go there first' not in ak.WHERE and 'never opens it' in ak.WHERE
    assert 'Go there first' in ak.brief()   # asked about FEELESS itself, it may still walk around it


def test_pob_footprint_allows_the_same_pick():
    rows = [{'status': 'closed', 'topic': 'Thunder vs Kings team to win', 'at': 1, 'calls': [{'picks': [{'pick': 'OKC to win'}]}], 'sitesRead': ['nba.com']}]
    n = fp.note('pob', rows, 0)
    if 'LAST FOOTPRINTS' in n:
        assert 'pick it again' in n
    assert 'pick it again' not in fp.note('pow', rows, 0)


def test_refused_send_posts_a_chat_line():
    import feecat_service as fs
    cat = {'chat': []}
    fs._kalshi_say_no(cat, {'title': 'Oklahoma City wins', 'why': 'Kalshi refused the order (404): insufficient_shard_balance'})
    t = cat['chat'][-1]['text']
    assert t.startswith('🛑 Nothing bought on Oklahoma City wins') and 'Exchange Indexes' in t
