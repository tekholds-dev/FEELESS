"""👤 YOUR SEATS (owner, 2026-10-15: "still no way to add my own coins into seats — they track my every move and study during that seat, AI suggests")
+ 🦠 the germ floor the agents learn on."""


def _card(now, **k):
    leg = lambda m: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': 'runner', 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0, 'at': now - 9999, 'liq': 1e12}
    return {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 3.0, 'startUsd': 4.0, 'roundStartUsd': 4.0, 'compoundedUsd': 0.0,
            'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 1, 'phase': 'degen', 'legs': [leg('A')], **k}


def test_your_pick_takes_its_seat_while_the_agents_hold_the_card():
    import arena_prime as ap
    now = 1_000_000.0
    cfg = ap.clean_cfg({'rotateHours': 99, 'coins': 4, 'compound': True, 'cycles': {'degen': 'off'}, 'rescuePct': 0, 'rideAt': 0, 'tp': 0, 'cycleEvery': 0, 'sl': 0})
    held = _card(now, holdAll=True, holdBy='agents')
    c = ap.queue_seat(held, {'mint': 'MINE', 'pairAddress': 'PMINE', 'symbol': 'MINE', 'price': 1.0, 'liquidityUsd': 1e9, 'ack': True})
    out = ap.tick(c, {'PA': 1.0, 'PMINE': 1.0}, [], [], cfg, now + 10, [], {}, {})
    assert [l['mint'] for l in out['legs']] == ['A', 'MINE'] and out['legs'][1]['picked']   # it used to wait forever: the refill was off under a hold
    none_ = ap.tick(held, {'PA': 1.0}, [], [], cfg, now + 10, [], {}, {})
    assert len(none_['legs']) == 1                                                       # … and the engine still picks nothing by itself under the hold


def test_the_agents_never_take_a_seat_you_queued_a_coin_for():
    import arena_prime as ap, pytest
    card = {'legs': [{'mint': 'A', 'pairAddress': 'PA', 'units': 1.0, 'entry': 1.0}] * 3, 'cash': 2.0, 'events': [],
            'seatPick': {'mint': 'MINE', 'pairAddress': 'PMINE'}}
    with pytest.raises(ValueError, match='reserved'):
        ap.agent_seat(card, {'mint': 'BOT', 'symbol': 'BOT', 'pairAddress': 'PBOT', 'price': 1.0}, {}, {'coins': 4}, 1000.0)


def test_on_your_seat_the_agents_only_suggest():
    from trench_kernel.positions import mine_held
    legs = [{'pairAddress': 'P1', 'picked': True}, {'pairAddress': 'P2'}]
    got = mine_held([{'pair': 'P1', 'symbol': 'MINE', 'action': 'swap', 'to': {'symbol': 'BOT'}, 'why': 'flat'},
                     {'pair': 'P2', 'symbol': 'X', 'action': 'pull', 'why': 'banked'}], legs)
    assert got[0]['action'] == 'hold' and got[0]['would']['action'] == 'swap' and 'swap it for $BOT' in got[0]['why']
    assert got[1]['action'] == 'pull'                                                    # the agents' own coins move as before


def test_your_seat_is_studied_and_compared_with_where_the_agents_would_have_sold():
    import office as of
    p = {}
    of.study_note(p, 'R0 hold', None, 'HOLD', 2.0, 1.02, 100)
    of.study_note(p, 'R7 trailing protection', 'pull', 'TAKE', 12.0, 1.12, 160)
    of.study_note(p, 'R7 trailing protection', 'pull', 'TAKE', 11.0, 1.11, 170)   # same ruling = not filed twice
    assert p['pick'] and len(p['study']) == 2 and p['would'] == {'at': 160, 'rule': 'R7 trailing protection', 'pct': 12.0, 'px': 1.12}
    act, st, ev = of.owner_ask(p, {'picked': True}, 'pull', 'TAKE', 'R7 trailing protection', 'trail', 12.0, 1.12, 170)
    assert act is None and not p.get('ask') and 'only take notes' in ev   # ✋ your trade: the agents only take notes
    rec = of.owner_seats([{'pick': True, 'sym': 'A', 'realPct': 30.0, 'would': {'pct': 12.0}}, {'pick': True, 'sym': 'B', 'realPct': -10.0, 'would': {'pct': -4.0}}, {'sym': 'C', 'realPct': 5.0}])
    assert rec['n'] == 2 and rec['cmp']['n'] == 2 and rec['cmp']['youBetter'] == 1


def test_the_germ_floor_matches_the_chart_tool_and_is_a_learning_token():
    import chart_intel as ci, rule_lab as rl
    rows = [[i, 1, 1.02, 0.98, 1, 1] for i in range(10)] + [[10, 1, 1.0, 0.9, 0.95, 1]] + [[11 + i, 1 + i * .1, 1.1 + i * .1, 1 + i * .1, 1.05 + i * .1, 1] for i in range(8)] + [[30, 1.2, 1.2, 0.96, 0.97, 1]]
    g = ci.germ(rows)
    assert g['px'] == 0.9 and g['runPct'] == 100.0 and not g['lost'] and ci.germ_word(g) == 'floor'
    assert ci.germ_word({'lost': True}) == 'lost' and ci.germ(rows[:10]) is None          # no run ≥ 15% = no germ
    assert 'germ:floor' in rl.trade_feats({'thesis': {'germ': 'floor'}})
    assert 'germ:floor' in rl.row_feats({'chart': {'germ': 'floor'}})
    js = open('frontend/src/lib/chartTools.js').read()
    assert 'span = 12, minRun = 15' in js                                                 # the chart's 🦠 tool and the agents read the SAME germ


def test_germ_floor_is_a_record_only_strategy():
    import paper_desk as pd
    assert 'germ_floor' in pd.STRAT_NAME
    assert pd.germ_floor({'chart': {'germ': 'floor'}}, {'buy': 60, 'd5': 1}) and not pd.germ_floor({'chart': {'germ': 'near'}}, {'buy': 60, 'd5': 1})
