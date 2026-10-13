"""👑 The coach: the creator (and the model, inside tighter bounds) strengthens the agents with directives the ranking really uses."""
import coach as co
import opportunity as opp
import trench_kernel.brain as tb
import trench_kernel.state as ts

NOW = 1_000_000.0


def test_an_owner_directive_is_a_bounded_ranking_weight_from_a_fixed_vocabulary():
    s, r = co.add(None, 'Crowd FOMO', 'owner', 'keeps buying the top', NOW)
    assert r['key'] == 'crowd fomo' and r['points'] == co.OWNER_PTS and co.pens(s, NOW) == {'crowd fomo': -8.0}
    assert co.add(s, 'buy everything', 'owner', 'x', NOW)[1] is None and co.add(s, 'bundled', 'hacker', 'x', NOW)[1] is None   # unknown cause / writer: nothing
    s, r2 = co.add(s, 'crowd fomo', 'owner', 'again', NOW + 5)
    assert len(s['rules']) == 1 and r2['n'] == 2                                               # the same cause is refreshed, never stacked
    assert set(co.CAUSES) <= {'thin pool', 'falling now', 'chart says wait', 'weak holders', 'thin data', 'early selling', 'crowd fomo', 'bundled'}
    row = {'mint': 'M', 'li': {'phase': 'CROWD FOMO'}}
    assert opp.judge_hits(row, co.pens(s, NOW)) == [('judge: crowd fomo', -8.0)]              # the kernel reads it exactly like a Judge rule
    assert co.pens(s, NOW + co.OWNER_TTL + 10) == {} and co.prune(s, NOW + co.OWNER_TTL + 10)['rules'] == []   # it expires by itself


def test_the_model_instructs_inside_tighter_bounds_and_the_owner_backs_or_kills_it():
    assert co.from_ai({'directives': [{'key': 'bundled', 'why': 'three bundled rugs in a row'}, {'key': 'ape it', 'why': 'x'}, {'key': 'BUNDLED'}, 'junk']}) == [('bundled', 'three bundled rugs in a row')]
    s, r = co.add(None, 'bundled', 'ai', 'three bundled rugs', NOW)
    assert r['points'] == co.AI_PTS == -4.0 and r['until'] == NOW + co.AI_TTL
    s2, back = co.strengthen(s, r['id'], NOW + 10)
    assert back['by'] == 'owner' and back['points'] == co.OWNER_MAX and co.pens(s2, NOW + 20) == {'bundled': -12.0}
    assert co.add(s2, 'bundled', 'ai', 'again', NOW + 30)[1] is None                           # the model never overrides the owner's rule
    s3, gone = co.kill(s2, back['id'], NOW + 40)
    assert gone and co.pens(s3, NOW + 50) == {} and co.kill(s3, 999, NOW)[1] is None
    assert co.pens(s, NOW, {'bundled': -8.0, 'thin pool': -8.0}) == {'bundled': -8.0, 'thin pool': -8.0}   # merged with the Judge's: the stronger of the two


def test_pull_and_teach_blocks_the_coin_and_ranks_its_kind_down_in_the_kernel():
    s, r = co.add(None, 'early selling', 'owner', 'dev wallets unloading into us', NOW, mint='PULLED', sym='RUG')
    assert co.blocked(s, NOW + 60) == {'PULLED'} and co.blocked(s, NOW + co.BLOCK_SEC + 1) == set() and s['log'][-1]['pull']
    ms = ts.from_row({'mint': 'K', 'symbol': 'K', 'pair': 'PK', 'px': 1.0, 'nums': {'v5': 8000, 'pace': 2, 'liq': 20000, 'd5': 6, 'buy': 62}, 'vitals': {'mcap': 40000, 'liq': 20000, 'ageH': 0.05, 'vol1h': 20000, 'txns1h': 300},
                      'li': {'press': 'WATCH'}}, 100.0)
    a, b = tb.think(ms), tb.think(ms, {'pens': co.pens(s, NOW)})
    assert round(b['rank'] / a['rank'], 2) == 0.92 and b['status'] == a['status']               # a weight: the coin still competes, a seat is never blocked by it
    v = co.view(s, NOW, {'thin pool': -8.0})
    assert [(x['key'], x['by']) for x in v['rules']] == [('early selling', 'owner'), ('thin pool', 'judge')] and v['blocked'] == 1 and len(v['causes']) == len(co.CAUSES)


def test_the_trade_tape_is_one_story_per_real_buy_from_records_that_exist():
    buy = {'card': 'degen', 'side': 'buy', 'status': 'filled', 'agent': True, 'sig': 'B1', 'mint': 'A', 'symbol': 'AAA', 'usd': 1.0, 'px': 1.02, 'midPx': 1.0, 'landSec': 3.1, 'confirmedAt': 1000.0, 'why': 'card buys its coin'}
    ledger = [buy, {**buy, 'sig': 'E1', 'agent': False, 'mint': 'ENG'}, {**buy, 'sig': None, 'mint': 'NOSIG'}, {**buy, 'sig': 'B2', 'mint': 'OPEN', 'symbol': 'OPN', 'confirmedAt': 2000.0},
              {'card': 'degen', 'side': 'sell', 'status': 'filled', 'sig': 'S1', 'mint': 'A', 'usd': 1.2, 'confirmedAt': 1300.0, 'why': 'R7 trail'}]
    pos = [{'mint': 'A', 'since': 1000.0, 'closedAt': 1300.0, 'realPct': 20.0, 'peak': 31.0, 'rule': 'R7 trail', 'tag': '🤖 agents · ⚡ READY (kernel)', 'src': ['pump'], 'thesis': {'structure': 'UPTREND', 'triggerRule': 'E12'}, 'li': {'phase': 'PRE-FOMO'}}]
    rev = [{'mint': 'A', 'at': 1300.0, 'kind': 'win', 'why': 'banked into the trail'}]
    ai = [{'mint': 'A', 'at': 990.0, 'stance': 'NEUTRAL', 'summary': 'clean, dev holding', 'label': 'GROQ', 'role': 'sherlock'}]
    t = co.trade_tape(ledger, pos, rev, ai, card='degen')
    assert [r['sym'] for r in t] == ['OPN', 'AAA']                                              # newest first; the engine's buy and the unsigned row are not agent trades
    a = t[1]
    assert a['buy']['slipPct'] == 2.0 and a['why']['structure'] == 'UPTREND' and a['ai']['summary'] == 'clean, dev holding' and a['sells'][0]['sig'] == 'S1'
    assert a['result'] == {'pct': 20.0, 'usd': 0.2, 'peak': 31.0, 'heldMin': 5.0, 'rule': 'R7 trail'} and a['judge']['kind'] == 'win' and not a['open']
    assert t[0]['open'] and 'result' not in t[0] and t[0]['ai'] is None                         # an open trade claims no result
    assert co.tape_stats(t) == {'n': 1, 'won': 1, 'medPct': 20.0, 'open': 1, 'medSlipPct': 2.0}


def test_sources_and_exit_rules_are_graded_on_real_fills_only():
    pos = [{'confirmed': True, 'realPct': -30.0 - i, 'src': ['movers'], 'rule': 'R5 stop'} for i in range(8)] + [{'confirmed': True, 'realPct': 6.0, 'src': ['pump', 'movers'], 'rule': 'R4f sellers took over'},
          {'confirmed': False, 'realPct': 500.0, 'src': ['pump'], 'rule': 'R7 trail'}, {'confirmed': True, 'realPct': 9e9, 'src': ['calls'], 'rule': 'left the card by another rule'}]
    rec = co.source_record(pos)
    assert rec['movers'] == {'n': 9, 'med': -33.0, 'won': 1} and rec['pump'] == {'n': 1, 'med': 6.0, 'won': 1} and rec['calls']['med'] == 100.0   # unconfirmed not counted · a broken figure capped
    assert co.source_factor(rec, ['movers']) == co.SRC_DOWN and co.source_factor(rec, ['movers', 'pump']) == 1.0 and co.source_factor(rec, ['new']) == 1.0 and co.source_factor(rec, []) == 1.0
    rr = co.rule_record(pos)
    assert rr['R5'] == {'n': 8, 'med': -33.5, 'won': 0} and rr['R4f'] == {'n': 1, 'med': 6.0, 'won': 1} and rr['other']['n'] == 1 and 'R7' not in rr


def test_the_model_coach_answers_from_the_vocabulary_and_the_memory_halves_a_worse_half_seat():
    import ai_router as air
    ad = air.parse_advice({'summary': 'desk keeps aping the top', 'directives': [{'key': 'Crowd FOMO', 'why': '3 of 5 losses bought the crowd top'}, {'key': 'send it', 'why': 'x'}, 'junk']})
    assert co.from_ai(ad) == [('crowd fomo', '3 of 5 losses bought the crowd top')] and 'coach' in air.ADVISORY_ROLES and not air.local_ok({}, 'coach')   # never the local model
    case = co.coach_case([{'sym': 'A', 'pct': -30, 'cause': 'crowd_fomo', 'phase': 'CROWD FOMO', 'held': 4}, {'sym': 'B', 'pct': 12, 'phase': 'PRE-FOMO', 'held': 9}], None, [{'key': 'bundled', 'points': -8.0, 'by': 'owner'}])
    assert case['losses'] and case['wins'] and case['vocab'] == list(co.CAUSES) and set(air.compact(case)) >= {'losses', 'wins', 'rules', 'vocab'}
    ms = ts.from_row({'mint': 'K', 'symbol': 'K', 'pair': 'PK', 'px': 1.0, 'nums': {'v5': 8000, 'pace': 2, 'liq': 20000, 'd5': 6, 'buy': 62}, 'vitals': {'mcap': 40000, 'liq': 20000, 'ageH': 1.0, 'vol1h': 20000, 'txns1h': 300, 'safe': True}}, 100.0)
    full, half = tb.think(ms)['opinions']['warden'], tb.think(ms, {'weights': {'K': 0.8}})['opinions']['warden']
    assert half['size'] == max(0.5, round(full['size'] * tb.MEM_SIZE, 2)) and 'worse half' in half['why'] and tb.think(ms, {'weights': {'K': 1.2}})['opinions']['warden'] == full
