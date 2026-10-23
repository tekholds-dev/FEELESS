"""🎭 Prompt Studio (owner, 2026-10-22): each model's sets are written from its own record, the record names what is wrong, an applied set rides
every call that model gets — and never changes the desk's rules."""
import asyncio

import ai_router as ar
import prompt_studio as ps

GIVEBACK = [{'pct': 1.0, 'peak': 18, 'heldMin': 40, 'at': i} for i in range(4)] + [{'pct': -14, 'peak': 2, 'heldMin': 9, 'at': 10 + i} for i in range(6)]


def test_stats_read_the_record_and_unknown_stays_none():
    s = ps.stats(GIVEBACK, [{'action': 'HOLD', 'ms': 50000}, {'action': 'NO ANSWER'}, {'action': 'BUY', 'ms': 52000}])
    assert s['n'] == 10 and s['wonPct'] == 40 and s['gaveN'] == 4 and s['quickN'] == 6 and s['quickWonPct'] == 0
    assert s['avgWin'] == 1.0 and s['avgLoss'] == -14.0 and s['answerPct'] == 67 and s['medMs'] == 52000
    e = ps.stats()
    assert e['n'] == 0 and e['wonPct'] is None and e['avgPct'] is None and e['medMs'] is None


def test_diagnose_names_the_habits_with_their_numbers():
    keys = [f['key'] for f in ps.diagnose(ps.stats(GIVEBACK, bench={'n': 200, 'median': -0.4, 'upPct': 43}))]
    assert keys[:3] == ['giveback', 'bleed', 'jumpy'] and 'favor' in keys
    fx = {f['key']: f for f in ps.diagnose(ps.stats(GIVEBACK))}
    assert '4 of 10 trades peaked +10' in fx['giveback']['evidence'] and 'break-even' in fx['giveback']['rule']
    assert ps.diagnose(ps.stats([{'pct': 5, 'peak': 6, 'heldMin': 40}] * 6)) == []                     # a healthy record needs no fix
    assert [f['key'] for f in ps.diagnose(ps.stats(grades={'favor': {'n': 20, 'rightPct': 35, 'typical': -4}}))] == ['yes']


def test_four_sets_per_model_written_from_its_record_and_inside_the_budget():
    s = ps.stats(GIVEBACK)
    fx = ps.diagnose(s)
    g4 = ps.sets('lan', s, fx)
    assert [x['set'] for x in g4] == ['elite', 'degen', 'progressive', 'tuned']
    assert all(len(x['text']) <= ps.MAX_CHARS['lan'] for x in g4) and all(set(x['dials']) == set(ps.DIAL_KEYS) for x in g4)
    assert '10 trades, 40 % won' in g4[0]['text'] and 'G4' in g4[0]['text'] and 'germ floor' in g4[1]['text']
    assert 'quick in, patient in profit' in g4[2]['text'] and 'break-even' in g4[3]['text'] and '3 habits' in g4[3]['tag']
    assert g4[3]['dials']['discipline'] > 70                                                            # the fixes move the dials
    nexa = ps.sets('win', ps.stats(grades={'favor': {'n': 20, 'rightPct': 35}}), [])
    assert all(len(x['text']) <= ps.MAX_CHARS['win'] for x in nexa) and 'YES' in nexa[0]['text']       # her one-word job keeps a tiny overlay


def test_clean_active_keeps_known_models_and_sets_only():
    act = ps.clean_active({'lan': {'set': 'elite', 'text': ' be  calm ', 'at': 5}, 'zz': {'set': 'elite', 'text': 'x'}, 'local': {'set': 'nope', 'text': 'x'},
                           'win': {'set': 'degen', 'text': 'y' * 900}})
    assert set(act) == {'lan', 'win'} and act['lan']['text'] == 'be calm' and len(act['win']['text']) <= ps.MAX_CHARS['win']


def test_the_router_appends_the_applied_set_to_that_model_only():
    msgs = [{'role': 'system', 'content': 'RULES'}, {'role': 'user', 'content': 'q'}]
    try:
        ar.STUDIO['lan'] = 'quick in, patient in profit'
        out = ar.with_studio(msgs, 'lan')
        assert out[0]['content'].startswith('RULES') and '🎭 MINDSET' in out[0]['content'] and 'never your answer format' in out[0]['content']
        assert ar.with_studio(msgs, 'local') == msgs and msgs[0]['content'] == 'RULES'                 # other models + the caller's list untouched
        assert ar.with_studio([{'role': 'user', 'content': 'q'}], 'lan')[0]['role'] == 'user'
    finally:
        ar.STUDIO.clear()
    assert "msgs = with_studio(msgs, p['key'])" in open(ar.__file__).read()                              # every provider call goes through it


def test_since_grades_the_overlay_on_trades_after_it():
    assert ps.since(GIVEBACK, 10) == {'n': 6, 'wonPct': 0, 'avgPct': -14.0} and ps.since(GIVEBACK, 0)['n'] == 0


def test_the_studio_view_and_apply(monkeypatch):
    import reputation_service as rs

    async def lms():
        return {'lan': {'model': 'qwen', 'loaded': [{'ctx': 8704}]}, 'local': None}
    monkeypatch.setattr(rs, '_lms_states', lms)
    monkeypatch.setattr(rs, '_duo_tape', lambda: ([{'mint': 'M', 'since': 100, 'aiBy': 'lan'}],
                                                   [{'mint': 'M', 'at': 100, 'state': 'sold', 'result': {'pct': -9.0, 'peak': 12, 'heldMin': 8}}]))
    v = asyncio.run(rs._studio_view())
    g4 = next(m for m in v['models'] if m['key'] == 'lan')
    assert g4['ctx'] == 8704 and g4['record']['n'] == 1 and len(g4['sets']) == 4 and g4['layers'][0]['k'] == 'job' and g4['layers'][0]['tok'] > 50
    assert g4['active'] is None and [m['key'] for m in v['models']] == ['lan', 'local', 'win']
    rs._json_save(rs.PROMPT_STUDIO_PATH, {'lan': {'set': 'progressive', 'text': 'rush in, ride green', 'at': 50}})
    v2 = asyncio.run(rs._studio_view())
    g4b = next(m for m in v2['models'] if m['key'] == 'lan')
    assert g4b['active']['set'] == 'progressive' and g4b['active']['since']['n'] == 1 and rs._air.STUDIO['lan'] == 'rush in, ride green'
    rs._json_save(rs.PROMPT_STUDIO_PATH, {})
    rs._studio_apply()
    assert 'lan' not in rs._air.STUDIO


RED = [{'pct': -8.0, 'peak': 3, 'heldMin': 12, 'usd': -0.03, 'at': 1000 + i} for i in range(7)] + [{'pct': 4.0, 'peak': 6, 'heldMin': 40, 'usd': 0.01, 'at': 2000 + i} for i in range(2)]


def test_red_is_read_on_the_recent_window_and_needs_a_sample():
    assert ps.is_red(ps.recent(RED)) and not ps.is_red(ps.recent(RED[:3]))                               # 3 trades prove nothing
    assert not ps.is_red(ps.recent([{'pct': 5, 'at': i} for i in range(8)]))
    assert ps.recent([{'pct': -1, 'at': i} for i in range(30)] + [{'pct': 9, 'at': 100 + i} for i in range(10)])['wonPct'] == 100   # the LAST 10
    assert 'last 9 trades: 22 % won' in ps.red_word(ps.recent(RED))


def test_the_switch_applies_auto_tuned_only_when_on_red_and_past_the_cooldown():
    tuned = {'set': 'tuned', 'text': 'cut red at your line'}
    rec = ps.recent(RED)
    assert ps.auto_pick(False, None, rec, tuned, 10_000) is None                                         # switch off
    pick = ps.auto_pick(True, None, rec, tuned, 10_000)
    assert pick['set'] == 'tuned' and pick['text'] == 'cut red at your line' and 'turned red' in pick['why']
    assert ps.auto_pick(True, None, ps.recent(RED[-2:] * 4), tuned, 10_000) is None                     # green → nothing
    assert ps.auto_pick(True, {'set': 'progressive', 'at': 9_000}, rec, tuned, 10_000) is None          # your set gets its 6 h
    assert ps.auto_pick(True, {'set': 'progressive', 'at': 1}, rec, tuned, 30_000)['set'] == 'tuned'
    assert ps.auto_pick(True, {'set': 'tuned', 'text': 'cut red at your line', 'at': 1}, rec, tuned, 90_000) is None   # already on this tune
    assert ps.auto_pick(True, {'set': 'tuned', 'text': 'older tune', 'at': 1}, rec, tuned, 90_000)['set'] == 'tuned'  # the record moved → a new tune


def test_the_ladder_credits_each_trade_to_the_mindset_active_when_it_opened():
    hist = ps.hist_add(ps.hist_add(ps.hist_add([], 'lan', 'elite', 1500, 'owner'), 'lan', 'progressive', 1990, 'owner'), 'local', 'degen', 1, 'owner')
    trades = RED + [{'pct': 12.0, 'at': 2500 + i, 'usd': 0.04} for i in range(5)]
    lad = ps.ladder(trades, hist, 'lan', 3000, {'set': 'progressive', 'at': 1990})
    by = {r['set']: r for r in lad}
    assert by['plain']['n'] == 7 and by['progressive']['n'] == 7 and by['elite']['n'] == 0 and by['degen']['n'] == 0   # OSSY's history is not G4's
    assert lad[0]['set'] == 'progressive' and lad[0]['avgPct'] > 0 and lad[0]['active'] and lad[1]['set'] == 'plain'
    assert by['progressive']['usd'] == 0.22 and [r['set'] for r in lad[-3:]] == ['elite', 'degen', 'tuned']
    assert ps.periods(None, 'lan', 100, {'set': 'elite', 'at': 50}) == [('plain', 0.0, 50.0), ('elite', 50.0, 101.0)]
    assert ps.ladder(trades, [], 'lan', 3000)[0]['set'] == 'plain'                                       # nothing applied yet: all plain


def test_the_auto_switch_runs_on_the_ai_round(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs, '_duo_tape', lambda: ([{'mint': f'M{i}', 'since': t['at'], 'aiBy': 'lan'} for i, t in enumerate(RED)],
                                                   [{'mint': f'M{i}', 'at': t['at'], 'state': 'sold', 'result': {'pct': t['pct'], 'peak': t['peak'], 'heldMin': t['heldMin'], 'usd': t['usd']}} for i, t in enumerate(RED)]))
    rs._json_save(rs.PROMPT_STUDIO_PATH, {'auto': {'lan': True}})
    rs._studio_auto_at['t'] = 0.0
    assert asyncio.run(rs._studio_auto(50_000)) == 1
    raw = rs._json_load(rs.PROMPT_STUDIO_PATH, {})
    assert raw['lan']['set'] == 'tuned' and raw['lan']['by'] == 'auto' and raw['history'][-1]['set'] == 'tuned' and 'turned red' in raw['autoLog'][-1]['why']
    assert rs._air.STUDIO['lan'] == raw['lan']['text'] and 'local' not in raw                          # OSSY's switch is off
    assert asyncio.run(rs._studio_auto(50_100)) == 0                                                    # once per 5 min
    rs._studio_auto_at['t'] = 0.0
    assert asyncio.run(rs._studio_auto(50_400)) == 0                                                    # already on this tune
    rs._json_save(rs.PROMPT_STUDIO_PATH, {})
    rs._studio_apply()
    assert "asyncio.ensure_future(_studio_auto_safe(now))" in open(rs.__file__).read()


def test_every_call_that_carries_the_mindset_is_stamped(monkeypatch):
    # owner, 2026-10-23: "when I reload a model I have no way of seeing if the prompt loaded" — the call log + the studio show the last call that CARRIED it
    async def fake_call0(self, http, p, env, msgs, now):
        return '{"ok":1}', None
    monkeypatch.setattr(ar.Router, '_call0', fake_call0)
    try:
        ar.STUDIO['lan'] = 'rush in'; ar.STUDIO_SET['lan'] = 'progressive'
        asyncio.run(ar.ROUTER._call(None, {'key': 'lan', 'model': 'm'}, {}, [{'role': 'system', 'content': 'RULES'}, {'role': 'user', 'content': 'q'}], 0))
        assert ar.CALL_LOG[-1]['mindset'] == 'progressive' and ar.MINDSET_SEEN['lan']['set'] == 'progressive' and ar.MINDSET_SEEN['lan']['ok']
        asyncio.run(ar.ROUTER._call(None, {'key': 'local', 'model': 'm'}, {}, [{'role': 'system', 'content': 'RULES'}], 0))
        assert 'mindset' not in ar.CALL_LOG[-1]                                                           # OSSY has none applied
    finally:
        ar.STUDIO.clear(); ar.STUDIO_SET.clear(); ar.MINDSET_SEEN.clear()


def test_auto_tune_is_on_for_the_seat_models_until_the_owner_turns_it_off():
    """🤖 owner, 2026-10-23: "G4 was losing so I asked for auto-updated prompts" — the switch was silently off for everyone."""
    import prompt_studio as ps
    assert ps.auto_on({}, 'lan') and ps.auto_on({}, 'local') and not ps.auto_on({}, 'win')
    assert not ps.auto_on({'auto': {'lan': False}}, 'lan') and ps.auto_on({'auto': {'win': True}}, 'win')


def test_auto_tuned_keeps_the_best_proven_mindset_and_how_winners_held():
    import prompt_studio as ps
    tr = [{'pct': 12, 'peak': 20, 'heldMin': 42, 'at': 10 + i} for i in range(3)] + [{'pct': -9, 'peak': 2, 'heldMin': 6, 'at': 20 + i} for i in range(9)]
    st = ps.stats(tr)
    assert st['winHeld'] == 42 and st['lossHeld'] == 6
    best = ps.best_rung([{'set': 'plain', 'n': 9, 'avgPct': 3}, {'set': 'progressive', 'n': 6, 'avgPct': 1.4}, {'set': 'elite', 'n': 2, 'avgPct': 9}])
    assert best['set'] == 'progressive'                                       # proven (≥ 5) and green; a 2-trade +9 % proves nothing
    assert ps.best_rung([{'set': 'degen', 'n': 8, 'avgPct': -2}]) is None
    tuned = next(x for x in ps.sets('lan', st, ps.diagnose(st), best) if x['set'] == 'tuned')['text']
    assert 'winners held a median 42 min, your losers 6 min' in tuned and 'best proven mindset is PROGRESSIVE (+1.4 % avg over 6 trades)' in tuned
    assert len(tuned) <= ps.MAX_CHARS['lan']


def test_the_live_lm_studio_preset_mirrors_what_feeless_sends(tmp_path):
    """📌 LM Studio's own box only feeds its chat window — FEELESS writes 'FEELESS LIVE · OSSY' with what OSSY really gets; never the owner's preset."""
    import json
    import lms_preset as lp
    d = tmp_path / '.lmstudio' / 'config-presets'
    assert lp.write('local', 'SEAT', home=tmp_path) is None                  # no LM Studio here → nothing written
    d.mkdir(parents=True)
    (d / 'FEELESS FEE Master.preset.json').write_text('{"name": "FEELESS FEE Master"}')
    p = lp.write('local', 'SEAT PROMPT\n\n🎭 MINDSET: quick in', {'temp': 0.6, 'topP': 0.9, 'stop': ['</s>']}, home=tmp_path)
    body = json.loads(open(p).read())
    assert body['name'] == 'FEELESS LIVE · OSSY' and body['identifier'] == '@local:feeless-live-local'
    f = {x['key']: x['value'] for x in body['operation']['fields']}
    assert f['llm.prediction.systemPrompt'].endswith('quick in') and f['llm.prediction.temperature'] == 0.6
    assert f['llm.prediction.topPSampling'] == {'checked': True, 'value': 0.9} and f['llm.prediction.stopStrings'] == ['</s>']
    assert lp.write('local', 'SEAT PROMPT\n\n🎭 MINDSET: quick in', {'temp': 0.6, 'topP': 0.9, 'stop': ['</s>']}, home=tmp_path) is None   # unchanged → no rewrite
    assert json.loads((d / 'FEELESS FEE Master.preset.json').read_text()) == {'name': 'FEELESS FEE Master'}   # the owner's own preset untouched
    assert lp.write('lan', 'G4', home=tmp_path) is None                      # G4's LM Studio is on the desktop — never written from here
    assert lp.write('local', 'X') is None                                    # a test never writes the real home folder


def test_the_applied_mindsets_ride_the_first_call_after_a_restart(monkeypatch):
    """🐛 2026-10-23: the startup apply ran at import time before _json_load existed → no mindset after any restart until Brain › Prompts opened."""
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    rs._json_save(rs.PROMPT_STUDIO_PATH, {'lan': {'set': 'elite', 'text': 'ELITE MINDSET — G4 test', 'at': 1.0, 'by': 'owner'}})
    rs._air.STUDIO.clear()
    asyncio.run(rs._studio_boot())
    assert rs._air.STUDIO.get('lan') == 'ELITE MINDSET — G4 test' and rs._air.STUDIO_SET.get('lan') == 'elite'
