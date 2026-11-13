"""🤖 AGENT-AUTO: nothing runs before 3 answers + confirm; bounds are honoured exactly; the kill-switch stops it; the already-ran guard holds."""
import agent_auto as aa


def _setup(kind='pob', per='$0.50', every='every 30m', stop='$2 total, 10 proofs, 24h', now=1000.0):
    p, say = aa.start(kind, now)
    assert '1 of 3' in say
    p, cfg, say = aa.answer(p, per, now); assert cfg is None and '2 of 3' in say
    p, cfg, say = aa.answer(p, every, now); assert cfg is None and '3 of 3' in say
    p, cfg, say = aa.answer(p, stop, now); assert cfg is None and 'confirm' in say
    return p, say


def test_commands():
    assert aa.command('auto pob') == ('auto', 'pob', '') and aa.command('/auto PoStatic nba') == ('auto', 'pos', 'nba')
    for t in ('stop auto', 'kill', 'auto off', 'kill switch', 'stop all auto'):
        assert aa.command(t)[0] == 'stop', t
    assert aa.command('auto status')[0] == 'status' and aa.command('file a pob') is None and aa.command('automatic') is None


def test_three_questions_then_confirm_then_runs():
    p, say = _setup()
    assert 'PoB every 30m, at most $0.5 each' in say and '$2 total' in say
    p2, cfg, say = aa.answer(p, 'sure thing', 1001); assert cfg is None and p2 and 'confirm' in say   # only confirm runs it
    p3, cfg, say = aa.answer(p, 'confirm', 1001); assert p3 is None and cfg['on'] and cfg['perUsd'] == 0.5 and cfg['everyS'] == 1800
    assert cfg['totalUsd'] == 2 and cfg['maxRuns'] == 10 and cfg['forS'] == 86400 and aa.due(cfg, 1001) == (True, '')


def test_bad_answers_reask_and_cancel():
    p, _ = aa.start('pop', 0)
    p, cfg, say = aa.answer(p, 'lots', 1); assert p['step'] == 0 and 'amount' in say
    p, cfg, say = aa.answer(p, '$500', 2); assert p['step'] == 0 and 'at most $100' in say
    p, cfg, say = aa.answer(p, '$1', 3); p, cfg, say = aa.answer(p, 'every 5m', 4); assert p['step'] == 1 and '15 minutes' in say
    p, cfg, say = aa.answer(p, 'cancel', 5); assert p is None and cfg is None and 'Nothing will run' in say
    assert aa.answer({'kind': 'pob', 'step': 0, 'answers': {}, 'at': 0}, '$1', 10 ** 6)[0] is None   # a stale setup never resumes


def test_budget_count_time_and_already_ran():
    p, _ = _setup(stop='$1.25 total')
    _, cfg, _ = aa.answer(p, 'confirm', 1000)
    assert aa.due(cfg, 1000, busy=True) == (False, 'the last one is still running')
    cfg = aa.fired(cfg, 1000); assert cfg['on'] and cfg['spentUsd'] == 0.5 and aa.due(cfg, 1500)[0] is False   # waits 30m
    cfg = aa.fired(cfg, 2800); assert cfg['spentUsd'] == 1.0 and cfg['on'] is False and 'budget' in cfg['stopped']   # a 3rd would cross $1.25
    p, _ = _setup(stop='2 proofs'); _, c2, _ = aa.answer(p, 'confirm', 0)
    c2 = aa.fired(c2, 0); assert c2['on']; c2 = aa.fired(c2, 1800); assert not c2['on'] and 'proofs done' in c2['stopped']
    p, _ = _setup(stop='1h'); _, c3, _ = aa.answer(p, 'confirm', 0)
    c3 = aa.fired(c3, 0); assert c3['on']; c3 = aa.fired(c3, 1800); assert not c3['on'] and c3['stopped'] == 'time is up'


def test_kill_switch_and_money_line():
    p, say = _setup(kind='pow')
    assert 'wallet' in say   # a PoW config says every real buy still waits for the signature
    _, cfg, _ = aa.answer(p, 'confirm', 1000)
    k = aa.kill(cfg, 1100); assert k['on'] is False and aa.due(k, 5000) == (False, 'stopped by the owner')
