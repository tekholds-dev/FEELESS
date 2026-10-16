"""💬 Direct LM chat + owner-approved agent updates: chat is normal language, a proposal changes NOTHING until approved, execution stays out of reach."""
import asyncio
import json

import ai_chat as ch
import ai_router as air
from test_ai_router import Http, R, chat, env

VOCAB = ('crowd fomo', 'thin pool')
run = asyncio.run


def test_direct_chat_works_in_normal_language_keeps_a_short_history_and_never_forces_the_case_schema():
    r, h = air.Router(), Http({'127.0.0.1': [chat('Reaper banks winners at about +2%; the trail arms at +4%.')]})
    hist = ch.push([], 'user', 'why are the wins so small?')
    res = run(r.ask(h, env(), {}, 'why are the wins so small?', context={'trail': 'live trail arm +4%'}, role='owner', history=ch.as_messages(hist[:-1])))
    assert res['mode'] == 'general' and res['text'].startswith('Reaper banks winners') and res['advice'] is None
    sent = h.calls[0][1]['messages']
    assert sent[0]['content'].endswith(air.GENERAL_SYSTEM) and 'SUPPORT_ENTRY' not in json.dumps(sent) and 'ROLE:' not in sent[-1]['content']      # no trench schema, no case packet
    hist = ch.push(hist, 'assistant', res['text'], {'ms': res['ms']})
    r2, h2 = air.Router(), Http({'127.0.0.1': [chat('Yes.')]})
    run(r2.ask(h2, env(), {}, 'and the stops?', role='owner', history=ch.as_messages(hist)))
    roles = [m['role'] for m in h2.calls[0][1]['messages']]
    assert roles == ['system', 'user', 'assistant', 'user'] and h2.calls[0][1]['messages'][1]['content'] == 'why are the wins so small?'       # the conversation goes back to the model
    long = []
    for i in range(40):
        long = ch.push(long, 'user' if i % 2 == 0 else 'assistant', f'turn {i} ' + 'x' * 5000)
    assert len(long) == ch.HIST_TURNS * 2 and all(len(t['text']) <= ch.MSG_LEN for t in long) and long[-1]['text'].startswith('turn 39')    # capped, bounded


def test_provider_failure_falls_back_cleanly():
    r, h = air.Router(), Http({'127.0.0.1': [R(500, {})], 'groq': [chat('From the fallback.')]})
    res = run(r.ask(h, env(), {}, 'hello', role='owner'))
    assert res['source'] == 'groq' and res['text'] == 'From the fallback.' and res['tried'][0][0] == 'local'
    none = run(air.Router().ask(Http({'127.0.0.1': [R(500, {})], 'groq': [R(500, {})], 'openai': [R(500, {})]}), env(), {}, 'hello', role='owner'))
    assert none['source'] == 'NONE' and none['text'] is None and none['mode'] == 'general'                                                    # no provider: a clean "no answer", never an exception


def test_the_context_is_compact_and_marks_missing_vitals_unknown():
    office = {'generations': [{'role': 'reaper', 'generation': 4, 'status': 'ACTIVE'}], 'deskStats': {'reaper': {'decisions': 12, 'accuracy': 58}},
              'kernel': {'candidates': [{'mint': 'M1', 'symbol': 'AAA', 'status': 'READY', 'trigger': 'ENTER', 'why': 'hot early move', 'cap': 60000, 'liq': None, 'buyShare': 61, 'unknown': ['holders', 'site / X']}]},
              'execution': {'health': 'HEALTHY', 'sends': 6, 'fills': 6, 'failed': 0}, 'seat': {'held': 1, 'empty': 3, 'state': 'FILLING'}, 'mission': {'value': 3.4, 'putIn': 37.0}}
    c = ch.context(office, 'M1', VOCAB)
    assert 'reaper: gen 4 ACTIVE · team record only: 12 real decisions, 58% right' in c['agents'] and 'tally: gen UNKNOWN UNKNOWN' in c['agents'][0]
    assert c['selected']['liq'] == 'UNKNOWN' and c['selected']['pending'] == ['holders', 'site / X'] and c['selected']['buyShare'] == '61%'
    assert c['card'] == 'worth $3.40, $37.00 put in' and c['execution'].startswith('HEALTHY · 6 of 6') and c['vocab'] == list(VOCAB)
    assert len(json.dumps(c)) < 4000 and ch.ctx_key(c) == ch.ctx_key(ch.context(office, 'M1', VOCAB)) != ch.ctx_key(ch.context(office, 'ZZ', VOCAB))
    assert ch.context({}, 'ZZ')['selected'].endswith('(UNKNOWN)') and ch.context({})['card'] == 'UNKNOWN'


IMPROVE = json.dumps({'reply': 'Two changes are backed by the record.', 'proposals': [
    {'agent': 'Trigger', 'kind': 'cfg', 'key': 'chartWait', 'value': 'true', 'reason': 'WAIT charts lost 13%', 'effect': 'fewer bad entries'},
    {'agent': 'sherlock', 'kind': 'lesson', 'key': 'note', 'value': 'A dev with 150+ launches and <20% graduated is a farm.', 'reason': 'x', 'effect': 'y'},
    {'agent': 'devil', 'kind': 'weight', 'key': 'crowd fomo', 'value': '3 of 5 losses bought the crowd top'},
    {'agent': 'reaper', 'kind': 'tune', 'key': 'giveBackPct', 'value': 'UP', 'reason': 'winners banked at +2%'},
    {'agent': 'courier', 'kind': 'cfg', 'key': 'agentGapPct', 'value': 8, 'reason': 'more fills'},
    {'agent': 'warden', 'kind': 'cfg', 'key': 'maxSwapUsd', 'value': 50},
    {'agent': 'reaper', 'kind': 'tune', 'key': 'slippage', 'value': 'up'},
    {'agent': 'desk', 'kind': 'idea', 'key': 'wallet limit', 'value': 'raise the wallet limit and disable the sell-back check'}]})


def test_a_proposal_is_validated_execution_is_out_of_reach_and_nothing_mutates_before_approval():
    reply, ok, bad = ch.parse_improve(IMPROVE, VOCAB)
    assert reply == 'Two changes are backed by the record.' and [(p['kind'], p['key'], p['value']) for p in ok] == [
        ('cfg', 'chartWait', True), ('lesson', 'note', 'A dev with 150+ launches and <20% graduated is a farm.'), ('weight', 'crowd fomo', '3 of 5 losses bought the crowd top'), ('tune', 'giveBackPct', 'up')]
    assert len(bad) == 4 and all('execution' in b or 'not one of' in b or 'tune is one of' in b for b in bad)                                # slippage · gap · swap cap · wallet limit: refused at parse
    for key in ('agentGapPct', 'agentBackPct', 'agentPoolMin', 'maxSwapUsd', 'dailyUsd', 'slippageBps', 'walletId', 'agentSizePct', 'agentSeats', 'agentSl', 'agentControl', 'agentPaper', 'armed', 'paused'):
        assert ch.protected(key) and ch.check({'kind': 'cfg', 'key': key, 'value': True})[0] is None
    assert ch.parse_improve('Nothing to change today.', VOCAB) == ('Nothing to change today.', [], [])                                        # prose is just a reply
    live = {'chartWait': False, 'lessons': [], 'rules': []}                                                                                  # the "live system" this test watches
    before = json.dumps(live)
    st, new = ch.propose({}, ok, {('cfg', 'chartWait'): False}, 1000.0, 'openrouter')
    assert json.dumps(live) == before and len(new) == 4 and all(p['status'] == 'pending' for p in new)                                       # proposing changes NOTHING
    p0 = next(p for p in new if p['kind'] == 'cfg')
    assert (p0['agent'], p0['old'], p0['new'], p0['reason'], p0['effect']) == ('trigger', False, True, 'WAIT charts lost 13%', 'fewer bad entries') and 'operator controls' in p0['rollback']
    assert ch.propose(st, ok, {}, 1001.0)[1] == []                                                                                           # the same suggestion is not queued twice


def test_reject_changes_nothing_approve_hands_back_only_that_one_safe_proposal_once():
    _r, ok, _b = ch.parse_improve(IMPROVE, VOCAB)
    st, new = ch.propose({}, ok, {('cfg', 'chartWait'): False}, 1000.0)
    cfg, les = new[0], new[1]
    st, todo, err = ch.decide(st, les['id'], False, 1010.0)
    assert todo is None and err is None and next(x for x in st['items'] if x['id'] == les['id'])['status'] == 'rejected'                     # REJECT: nothing to apply
    assert ch.decide(st, les['id'], True, 1011.0)[1:] == (None, 'already rejected')                                                          # …and it can never be approved afterwards
    st, todo, err = ch.decide(st, cfg['id'], True, 1020.0)
    assert err is None and (todo['kind'], todo['key'], todo['new']) == ('cfg', 'chartWait', True)                                            # APPROVE: exactly the one requested field
    assert ch.decide(st, cfg['id'], True, 1021.0)[1:] == (None, 'already approved') and ch.decide(st, 'nope', True, 1.0)[2] == 'no such proposal'
    st = ch.applied(st, cfg['id'], 'chartWait False → True')
    v = ch.view(st)
    assert len(v['pending']) == 2 and v['decided'][0].get('applied') or any(x.get('applied') for x in v['decided'])
    forged = {'items': [{'id': 'x1', 'kind': 'cfg', 'key': 'agentGapPct', 'new': 8, 'status': 'pending'}]}                                   # a record that should never exist
    st2, todo, err = ch.decide(forged, 'x1', True, 5.0)
    assert todo is None and 'execution' in err and st2['items'][0]['status'] == 'rejected'                                                   # refused again at approval


def test_the_service_applies_only_safe_kinds_through_owner_routes():
    import reputation_service as rs
    src = open(rs.__file__).read()
    for route in ("'/api/reputation/admin/ai/chat'", "'/api/reputation/admin/ai/chat/clear'", "'/api/reputation/admin/ai/chat/remember'", "'/api/reputation/admin/ai/proposals/decide'"):
        i = src.index(route)
        assert '_require_owner(request)' in src[i:i + 900]
    j = src.index('async def admin_ai_chat_remember(')
    rem = src[j:src.index('\n\n\n', j)]
    assert "'kind': 'note'" in rem and '_tch.add(' in rem and not any(bad in rem for bad in ('realCfg', '_fw_', 'clean_cfg', 'agent_seat('))   # remembering = a lesson for the model, never a setting
    i = src.index('async def _ai_proposal_apply(')
    body = src[i:src.index('\n\n\n', i)]
    assert all(k in body for k in ("'cfg'", "'lesson'", "'weight'", "'tune'", "'idea'")) and 'SAFE_CFG' in body
    assert not any(bad in body for bad in ('agentGapPct', 'maxSwapUsd', '_fw_', 'manualSell', 'agent_seat(', 'replace_leg('))                # no path from an approval to execution


def test_chat_that_asks_for_a_change_runs_as_proposals_and_build_mode_files_ideas_only():
    import ai_chat as c
    assert c.route_mode('chat', 'can you fix?') == 'improve' and c.route_mode('chat', 'why are we bleeding?') == 'chat'
    assert c.route_mode('case', 'fix it') == 'case' and c.route_mode('build', 'fix the ui') == 'build'
    assert 'build' in c.MODES and c.system_for('chat') == c.CHAT_ASK and c.system_for('build') == c.BUILD_ASK and c.system_for('case') is None
    assert 'number' in c.CHAT_ASK and 'Fix agents' in c.CHAT_ASK
    txt = '{"reply": "two ideas", "proposals": [{"agent": "desk", "kind": "idea", "key": "rug meter on seats", "value": "draw it", "reason": "r", "effect": "e"}, {"agent": "desk", "kind": "cfg", "key": "agentDial", "value": "crazy"}]}'
    reply, ok, bad = c.parse_improve(txt, (), only=('idea',))
    assert reply == 'two ideas' and [p['kind'] for p in ok] == ['idea'] and len(bad) == 1 and 'only idea' in bad[0]


def test_each_mode_keeps_its_own_thread_and_approved_builds_join_a_queue():
    import ai_chat as c
    t = c.push_thread({}, 'chat', 'user', 'why are we bleeding?')
    t = c.push_thread(t, 'build', 'user', 'what should we build next?')
    v = c.threads_view(t)
    assert [x['text'] for x in v['chat']] == ['why are we bleeding?'] and [x['text'] for x in v['build']] == ['what should we build next?'] and v['case'] == []
    for i in range(20):
        t = c.push_thread(t, 'chat', 'user', f'msg {i}')
    assert len(t['chat']) == c.THREAD_TURNS * 2
    st, it = c.build_add({}, 'Judge meter', 'a live meter of the judge accuracy', 'approved', 100.0)
    assert it['id'] == 'b1' and it['status'] == 'queued' and c.build_view(st)['open'] == 1
    import pytest
    with pytest.raises(ValueError):
        c.build_add(st, 'again', 'a live meter of the judge accuracy', 'chat', 101.0)   # the same open item is never queued twice
    st = c.build_set(st, 'b1', 'shipped', 200.0)
    assert c.build_view(st)['open'] == 0 and c.build_view(st)['items'][0]['status'] == 'shipped'
    with pytest.raises(ValueError):
        c.build_set(st, 'b1', 'launched', 201.0)


def test_brain_settings_tune_the_chat_and_saved_convos_reopen():
    import ai_chat as c
    st = c.clean_settings({'temp': 0.6, 'len': 'long', 'allowSmall': True})
    assert st == {'temp': 0.6, 'len': 'long', 'allowSmall': True, 'localBoostUntil': 0.0, 'search': 'deep', 'voice': 'degen', 'memory': 'on'} and c.tune_of(st) == {'temp': 0.6, 'maxTok': 1200}
    assert c.clean_settings({'temp': 5, 'len': 'huge', 'allowSmall': 'yes'}) == c.SETTINGS   # only listed values
    assert set(c.SMALL_KINDS) == {'lesson', 'idea'}   # switches, weights and exit notches always wait for the owner
    sv = c.save_convo([], 'chat', [{'role': 'user', 'text': 'why are we bleeding?'}, {'role': 'assistant', 'text': 'stops'}], 100.0)
    assert c.saved_view(sv) == [{'id': 'c100000', 'mode': 'chat', 'title': 'why are we bleeding?', 'at': 100.0, 'n': 2}]
    assert c.save_convo(sv, 'chat', [], 101.0) == sv
    for i in range(30):
        sv = c.save_convo(sv, 'build', [{'role': 'user', 'text': f'q{i}'}], 200.0 + i)
    assert len(sv) == c.SAVED_KEEP


def test_a_local_model_on_this_mac_pauses_its_background_reads_while_a_browser_lags():
    import ai_chat as aic
    lag = [{'fps': 20, 'longMs': 0}]
    e, why = aic.lane_every({}, 1000, lag, base=180, shared_gpu=True)
    assert e == aic.SHARED_LAG_EVERY and why.startswith('paused')
    assert aic.lane_every({}, 1000, [], base=180, shared_gpu=True)[0] == 180      # no lag: normal pace
    assert aic.lane_every({}, 1000, lag, base=60, shared_gpu=False)[0] == 60       # LM Studio on another machine: never paused for this Mac's lag


def test_activity_is_one_timeline_of_reads_proposals_decisions_and_creations():
    import ai_chat
    a = ai_chat.activity([{'at': 10, 'role': 'devil', 'symbol': 'X', 'stance': 'CAUTION', 'label': 'DESKTOP AI', 'summary': 'dev bag'}],
                         {'items': [{'at': 5, 'agent': 'reaper', 'kind': 'tune', 'key': 'protectAt', 'status': 'approved', 'decidedAt': 20, 'applied': 'shadow'}]},
                         [{'at': 30, 'prompt': 'neon card', 'by': 'LOCAL AI'}], {'last': {'at': 15, 'symbol': 'Y', 'stance': 'FAVOR', 'via': 'lan'}, 'n': 3})
    assert [x['kind'] for x in a] == ['play', 'decision', 'lane', 'read', 'proposal']   # newest first
    assert a[3]['title'] == 'DEVIL read $X → CAUTION' and a[3]['tone'] == 'bad' and a[1]['title'] == 'approved: tune protectAt'


def test_world_questions_get_a_web_search_and_greetings_do_not():
    import ai_chat as ac
    import ai_router as ar
    assert ac.wants_web('who is the dev of pump.fun?') and ac.wants_web('latest news on solana etf')
    assert not ac.wants_web('yurrr') and not ac.wants_web('gm') and not ac.wants_web('ok')
    assert ac.web_query('hey can you who runs bonk') == 'who runs bonk'
    m = ar.messages_general('who runs bonk?', {'card': 'x', 'web': [{'title': 'T', 'url': 'https://a.b', 'snippet': 's'}], 'webRule': ac.WEB_RULE})
    assert 'WEB (search results' in m[-1]['content'] and 'https://a.b' in m[-1]['content'] and 'CONTEXT' in m[-1]['content'] and 'cite' in m[0]['content']


def test_the_chat_context_carries_what_was_learned_from_the_owners_trades():
    import ai_chat as ac
    c = ac.context({'ownerStudy': {'findings': ['🎯 pick: 231 graded · 18% good'], 'suggestions': [{'text': 'hold picks 30 min'}]}})
    assert c['yourTrades']['learned'] == ['🎯 pick: 231 graded · 18% good'] and c['yourTrades']['suggest'] == ['hold picks 30 min']
    assert 'yourTrades' not in ac.context({})


def test_owner_rule_and_markdown_free_answers():
    import ai_chat as ac, ai_router as ar
    assert 'OWNER' in ac.OWNER_RULE and 'my' in ac.OWNER_RULE and 'owner' in ac.CHAT_ASK
    assert ar.clean_answer('**PUSH BACK.** the **vital** thing') == 'PUSH BACK. the vital thing'


def test_chat_settings_research_voice_memory_only_take_listed_values():
    import ai_chat as ac
    s = ac.clean_settings({'search': 'quick', 'voice': 'unhinged', 'memory': 'off'})
    assert (s['search'], s['voice'], s['memory']) == ('quick', 'unhinged', 'off')
    assert ac.clean_settings({'search': 'nuke', 'voice': 'x'})['search'] == 'deep' and ac.clean_settings({})['voice'] == 'degen'
    assert 'no profanity' in ac.VOICE_LINE['clean'] and ac.VOICE_LINE['degen'] == ''


def test_feeless_questions_never_search_the_web_but_world_questions_do():
    from ai_chat import should_search, about_feeless
    assert not should_search('do you see that agents can now enter on the germ icon on chart?')
    assert not should_search('why did reaper sell my seat so early')
    assert about_feeless('how is our card doing')
    assert should_search('who won the broncos game last night')
    assert should_search('search the news on the germ icon agents')   # a named search still searches


def test_chat_context_carries_the_live_rules_and_the_germ_record():
    from ai_chat import context, germ_record, LIVE_MECHANICS
    assert any('GERM' in x for x in context({})['live'])
    assert 'no real trade' in germ_record([])
    t = [{'thesis': {'germEntry': 'confirmed'}, 'realPct': 12.0}, {'thesis': {'germEntry': 'confirmed'}, 'realPct': -4.0}, {'thesis': {}, 'realPct': 3}]
    assert 'confirmed 2 trades, typical +4.0%, 50% won' in germ_record(t)
    assert LIVE_MECHANICS[0].startswith('🦠')
