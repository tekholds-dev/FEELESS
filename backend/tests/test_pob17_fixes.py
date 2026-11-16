"""Owner 2026-11-15 PoB #17: a refused Kalshi bid says so in chat; minds may repeat a backed pick; proofs never tour FEELESS."""
import agent_knows as ak
import kalshi_bid as kb
import proof_footprint as fp


def test_shard_refusal_reads_plain():
    w = kb.plain_why('Kalshi refused the order (404): {"error":{"code":"insufficient_shard_balance"}}')
    assert 'Exchange Indexes' in w and 'new PoB' in w
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


def test_started_game_is_named_not_blamed_on_confidence():
    g = [{'teams': [{'short': 'Thunder', 'abbr': 'OKC'}, {'short': 'Kings', 'abbr': 'SAC'}], 'state': 'pre', 'at': '2026-11-16T02:00Z'}]
    t0 = kb._start('2026-11-16T02:00Z')
    assert kb.started_game('Thunder vs Kings team to win', g, t0 - 600) is None
    hit = kb.started_game('Thunder vs Kings team to win', g, t0 + 60)
    assert hit and 'start time' in kb.outcome_line(None, True, hit) and 'confidence' not in kb.outcome_line(None, True, hit)
    assert kb.started_game('Lakers vs Suns', g, t0 + 60) is None
    assert 'confidence' in kb.outcome_line(None, True)


def test_balance_is_read_on_the_market_index():
    j = {'balance': 1000, 'balance_breakdown': [{'balance': '5.0000', 'exchange_index': 1}, {'balance': '0.0000', 'exchange_index': 3}]}
    assert kb.shard_dollars(j, {'exchange_index': 3}) == 0.0
    assert kb.shard_dollars(j, {'exchange_index': 1}) == 5.0
    assert kb.shard_dollars(j, None) == 10.0 and kb.shard_dollars(j, {}) == 10.0


def test_planned_sites_count_as_used():
    folders = [{'status': 'closed', 'topic': 'Thunder vs Kings', 'at': i, 'sites': ['sports.yahoo.com', 'espn.com']} for i in range(3)]
    p = fp.plan('pob', 'Thunder vs Kings', ['sports.yahoo.com', 'espn.com', 'nba.com', 'covers.com'], folders)
    assert p['sites'][0][0] not in ('sports.yahoo.com', 'espn.com') and p['sites'][1][0] not in ('sports.yahoo.com', 'espn.com')


def test_proof_monitors_browse_with_that_proofs_own_minds(monkeypatch):
    """Owner 2026-11-15: PoB set to GPT-6.1 Sol + GLM 5.3, but its monitors browsed with hy4 + gpt-6.1-terra (the agent's main pair)."""
    import feecat_service as fs
    got = {}
    monkeypatch.setattr(fs._ca, 'new_task', lambda tid, text, models, *a, **k: got.setdefault('models', list(models)) and {'id': tid, 'windows': []})
    cat = {'id': 'cX', 'brainsCfg': {'brains': ['tencent/hy4', 'openai/gpt-6.1-terra'], 'credit': 5, 'byKind': {'pob': ['openai/gpt-6.1-sol', 'z-ai/glm-5.3']}}}
    monkeypatch.setitem(fs._WORK, 'cX', None)
    try:
        fs._work_start('cX', cat, 'read', None, None, read_=True, kind='pob')
    except Exception:
        pass
    assert got['models'] == ['openai/gpt-6.1-sol', 'z-ai/glm-5.3']
    got.clear()
    try:
        fs._work_start('cX', cat, 'read', None, None, read_=True, kind='poc')   # no own pair for PoC: the agent's pair
    except Exception:
        pass
    assert got['models'] == ['tencent/hy4', 'openai/gpt-6.1-terra']
