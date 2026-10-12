"""🆕 Fresh 0–12h trench coins must dominate selection: the old failure (a flat 100-candle old coin outranking an 8-candle accelerating
launch), the candle budget order, the best-available bar, the Pump entry phase, early-wallet pressure, the Judge's loss classes, the
curve switch."""
import agents as ag
import chart_intel as ci
import fuse_wallet as fw
import judge_review as jr
import launch_intel as li
import office_edge as oe
import opportunity as opp


def _bars(closes, vol=1000.0, t0=0):
    out, prev = [], closes[0]
    for i, c in enumerate(closes):
        out.append([t0 + i * 60, prev, max(prev, c), min(prev, c), c, vol * (1 + 0.37 * (i % 3))]); prev = c
    return out


def _row(m, ageH, v5, vol1h, tx, buy, pace, d5, chart, liq=40_000, mcap=120_000):
    return {'mint': m, 'symbol': m, 'px': 1.0, 'nums': {'v5': v5, 'pace': pace, 'liq': liq, 'd5': d5, 'buy': buy},
            'vitals': {'safe': True, 'mcap': mcap, 'liq': liq, 'ageH': ageH, 'vol1h': vol1h, 'txns1h': tx, 'buyShare': buy}, 'chart': chart}


def test_a_new_accelerating_launch_outranks_a_flat_old_coin_with_more_history():
    flat = [1.0 + 0.001 * (i % 3) for i in range(100)]
    old = _row('OLD', 300, 900, 40_000, 300, 50, 0.3, 0.1, ci.compact(ci.read(_bars(flat))) if hasattr(ci, 'compact') else ci.read(_bars(flat)), liq=150_000, mcap=180_000)
    rise = [1.0, 1.04, 1.09, 1.12, 1.18, 1.22, 1.27, 1.33]
    new = _row('NEW', 8 / 60, 9_000, 14_000, 260, 66, 3.0, 9.0, ci.read(_bars(rise)), liq=25_000, mcap=60_000)
    assert opp.hard_fail(new) is None and 'no new entry past 6h' in opp.hard_fail(old)   # a 300h coin is not a new entry at all now
    s_old, s_new = opp.score(old)[0], opp.score(new)[0]
    assert s_new > s_old
    ranked = [r['mint'] for r in opp.rank([old, new])]
    assert ranked[0] == 'NEW'
    assert opp.fresh_bucket(new)[0].startswith('VERY HIGH') and opp.fresh_bucket(old)[0] == '6h+ no new entry'


def test_velocity_is_normalised_by_the_coins_own_life():
    young = _row('Y', 3 / 60, None, 20_000, 300, 70, None, 0, {})
    old = _row('O', 30, 2_000, 100_000, 400, 50, 0.24, 0, {})
    assert opp.velocity(young)[0] > opp.velocity(old)[0]          # $20K in 3 min beats $100K over an hour


def test_a_newborns_launch_move_is_not_a_vertical_candle():
    assert opp.hard_fail(_row('B', 4 / 60, 5000, 9000, 120, 70, 2, 80.0, {})) is None      # +80% in its first minutes: its launch, not a top
    assert opp.hard_fail(_row('M', 3.0, 5000, 9000, 120, 70, 2, 80.0, {})).startswith('+80%')


def test_the_candle_budget_goes_to_fresh_busy_coins_first_and_held_last():
    rows = [{'mint': 'OLD', 'pairAddress': 'Po', 'ageH': 200, 'vol5m': 90_000}, {'mint': 'NEWQ', 'pairAddress': 'Pq', 'ageH': 0.05, 'vol5m': 500},
            {'mint': 'NEWB', 'pairAddress': 'Pb', 'ageH': 0.1, 'vol5m': 20_000}, {'mint': 'MID', 'pairAddress': 'Pm', 'ageH': 2, 'vol5m': 30_000}]
    order = list(oe.candle_order(rows, {'MID': 'Pm'}, {'HELD': 'Ph'}))
    assert order == ['MID', 'NEWQ', 'NEWB', 'OLD', 'HELD']   # 0–5m is the extreme band (trench-desk spec), then 5–15m


def test_a_fresh_launch_with_real_candles_reaches_trigger_and_can_clear():
    rise = [1.0, 1.03, 1.06, 1.05, 1.09, 1.12, 1.15, 1.19]
    row = {'mint': 'NEW', 'symbol': 'NEW', 'pairAddress': 'Pn', 'price': 1.19, 'ageH': 0.15, 'mcap': 60_000, 'liq': 25_000, 'vol1h': 14_000, 'vol5m': 9_000,
           'txns1h': 260, 'buyShare': 66, 'chg5m': 9.0, 'chg1h': 19.0, 'safe': True, 'top10': 18}
    charts = {}
    st, table = ag.desk({}, [row], 1000.0, candles={'NEW': _bars(rise, t0=1000.0 - 7 * 60 - 20)}, charts_out=charts)
    assert charts['NEW']['src'] == 'candles'                       # Trigger read the REAL candles the service had for it
    x = next(t for t in table if t['mint'] == 'NEW')
    assert x['trigger'][0] in ('enter', 'wait') and x['chart']['state'] != ci.DATA_INVALID


def test_best_available_needs_a_b_tier_entry_score():
    ok = ['scan', True, ''], ['age', True, ''], ['pool', True, ''], ['burn', True, ''], ['devil', True, '']
    weak = {'mint': 'W', 'cleared': False, 'checks': list(ok) + [['chart', False, 'WAIT']], 'row': _row('W', 300, 400, 3000, 30, 45, 0.2, -2, {'state': 'RANGE', 'risk': [0.75, ''], 'q': {'readOk': True}})}
    assert oe.near_ready([weak], {'W': {'score': 80}}) == []       # the least-bad coin is not a seat
    assert oe.near_ready([weak], {'W': {'score': 80}}, min_entry=0)


def test_pump_phase_and_early_wallet_pressure():
    assert li.pump_phase({'d5': 4, 'pace': 2.0}) == 'EARLY ACCELERATION'
    assert li.pump_phase({'d5': -2}, 'PULLBACK IN UPTREND') == 'FIRST PULLBACK' and li.pump_phase({'d5': 1}, 'PULLBACK IN UPTREND') == 'RECLAIM'
    assert li.pump_phase({'d5': 20, 'c1': 200}) == 'LATE FOMO' and li.pump_phase({}, fomo='DISTRIBUTION') == 'DISTRIBUTION'
    m = li.early_map([{'w': f'w{i}', 'slot': i, 'sol': 1 + i, 'pct': 2} for i in range(4)], {'w0': 0, 'w1': 0, 'w2': 2, 'w3': 2})
    assert li.wallet_pressure(m) == 'DUMPING' and li.wallet_pressure(None, press='HIGH') == 'DUMPING'
    h = li.early_map([{'w': f'w{i}', 'slot': i, 'sol': 1 + i, 'pct': 2} for i in range(4)], {f'w{i}': 2 for i in range(4)})
    assert li.wallet_pressure(h, 'IMPROVING') == 'POSITIVE' and li.wallet_pressure(h) == 'NEUTRAL'
    assert opp.score({**_row('P', 0.5, 3000, 8000, 100, 60, 1.5, 3, {}), 'li': {'pump': 'EARLY ACCELERATION', 'ewp': 'POSITIVE'}})[0] > \
           opp.score({**_row('P', 0.5, 3000, 8000, 100, 60, 1.5, 3, {}), 'li': {'pump': 'LATE FOMO', 'ewp': 'DUMPING'}})[0]


def test_old_coins_only_return_to_intake_when_they_wake_up():
    assert oe.stale_old({'ageH': 30, 'vol5m': 500, 'vol1h': 20_000})
    assert not oe.stale_old({'ageH': 30, 'vol5m': 5000, 'vol1h': 20_000})       # pace 3× on $5K: waking up
    assert not oe.stale_old({'ageH': 3, 'vol5m': 10})


def test_judge_classifies_every_loss():
    base = {'mint': 'M', 'realPct': -8, 'path': [-1, -2], 'peak': 1, 'low': -8, 'rule': 'R5 stop'}
    r = jr.review({**base, 'tag': '🤖 agents · best available'})
    assert r['cause'] == 'fallback_entry' and r['lossClass'] == 'BAD ENTRY'
    assert jr.review({**base, 'launch': {'ageH': 40}})['cause'] == 'too_old'
    assert jr.review({**base, 'peak': 10, 'realPct': -1})['lossClass'] == 'BAD EXIT'


def test_fresh_view_counts_buckets_repeats_and_age_at_entry():
    t = [{'mint': 'A', 'vitals': {'ageH': 0.1}}, {'mint': 'B', 'vitals': {'ageH': 2}}, {'mint': 'C', 'vitals': {'ageH': 40}}]
    v = oe.fresh_view(t, deep=['A'], prev=['C'], positions=[{'since': 99_000, 'launch': {'ageH': 0.5}}, {'since': 1, 'launch': {'ageH': 50}}], now=100_000)
    assert sum(v['buckets'][k] for k in ('0–5m', '5–15m')) == 1 and v['buckets']['6h+'] == 1 and sum(v['deep'][k] for k in ('0–5m', '5–15m')) == 1
    assert v['repeats'] == 1 and v['newUnique'] == 2 and v['boughtAgeMin24h'] == 30 and v['boughtAgeMinBefore'] == 3000


def test_the_curve_switch_lets_an_agent_seat_buy_a_curve_coin_on_its_curve_depth():
    pair = {'baseToken': {'address': 'M'}, 'priceUsd': '0.0001', 'liquidity': {'usd': 0}, 'dexId': 'pumpfun', 'marketCap': 40_000}
    cfg = fw.clean_cfg({}) if hasattr(fw, 'clean_cfg') else {}
    assert not fw.live_buy_market({'side': 'buy', 'mint': 'M', 'trench': True}, pair, cfg)[0]                 # the engine's other doors: never
    ok, why, info = fw.live_buy_market({'side': 'buy', 'mint': 'M', 'trench': True, 'curve': True}, pair, cfg)
    assert info['liq'] > 0                                                                                       # judged on the curve's own depth


def _leg(m='D'):
    return {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'entry': 1.0, 'units': 1.0, 'at': 1, 'liq': 30_000, 'liqNow': 30_000, 'bought': {'tag': '🤖 agents · B-tier'}}


def test_a_dead_holding_exits_to_cash_after_15_min_without_a_replacement():
    import office as of
    row = {'mint': 'D', 'symbol': 'D', 'pair': 'PD', 'px': 0.99, 'why': {'lean': 0.5, 'drivers': []}, 'trigger': ['wait', ''], 'devil': ['—', ''],
           'nums': {'d5': 0, 'buy': 50, 'liq': 30_000, 'v5': 40, 'pace': 0.1}, 'vitals': {'safe': True, 'rug': 5}}
    cfg = {'agentTakePct': 20, 'agentScalp': False}
    pos, rep, _ = of.reap([_leg()], [row], {'PD': 0.99}, cfg, None, 600, control=True)
    assert rep[0]['rule'] == 'R11 dead coin' and rep[0]['run'] == 'DEAD'
    assert of.merge_reaper([], [dict(rep[0])], buys_left=0) == []                                  # no replacement yet: swap waits …
    pos, rep, _ = of.reap([_leg()], [row], {'PD': 0.99}, cfg, pos, 600 + 15 * 60 + 5, control=True)
    assert rep[0]['rule'] == 'R11x dead coin → cash'
    out = of.merge_reaper([], [dict(rep[0])], buys_left=0)
    assert out and out[0]['action'] == 'pull'                                                       # … 15 min dead: cash, no replacement needed


def test_an_old_reject_cools_three_times_longer():
    e = {'review': 1000, 'reject': 'WAIT', 'snap': {'ageH': 30}}
    assert not oe.review_due(e, 1000 + oe.REVIEW_COOL_SEC + 5)[0]
    assert oe.review_due(e, 1000 + oe.REVIEW_COOL_SEC * 3 + 5)[0]
    assert oe.review_due({**e, 'snap': {'ageH': 2}}, 1000 + oe.REVIEW_COOL_SEC + 5)[0]


def test_one_active_index_reads_the_same_row_every_desk_reads():
    rise = [1.0, 1.03, 1.06, 1.05, 1.09, 1.12, 1.15, 1.19]
    row = {'mint': 'NEW', 'symbol': 'NEW', 'pairAddress': 'Pn', 'price': 1.19, 'ageH': 0.15, 'mcap': 60_000, 'liq': 25_000, 'vol1h': 14_000, 'vol5m': 9_000,
           'txns1h': 260, 'buyShare': 66, 'chg5m': 9.0, 'chg1h': 19.0, 'safe': True, 'top10': 18, 'src': ['open', 'pulse']}
    st, table = ag.desk({}, [row], 1000.0, candles={'NEW': _bars(rise, t0=1000.0 - 7 * 60 - 20)})
    x = next(t for t in table if t['mint'] == 'NEW')
    ix = next(r for r in oe.active_index(table, {}, 1000.0) if r['mint'] == 'NEW')
    assert ix['liveMC'] == x['vitals']['mcap'] and ix['launchAgeMin'] == round(x['vitals']['ageH'] * 60, 1) and ix['holderStatus'] == 'passed'
    assert ix['eligible'] == (opp.hard_fail(x) is None) and ix['realCandles'] is True and ix['fresh'] == opp.fresh_bucket(x)[0] and ix['fresh'].startswith(('EXTREME', 'VERY HIGH'))


def test_the_agents_own_holder_line_passes_concentration_only_and_never_a_rugger():
    base = {'safe': False, 'top10': 32, 'insiders': 12, 'bundled': 2, 'dev': 7}
    assert ag.agent_holder_pass({**base, 'fails': ['Top 10 under 25%', 'Dev holds under 5%']})
    assert ag.agent_holder_pass({**base, 'fails': ['Top 10 under 25%', 'Creator not flagged (Bot shield / blocklist)']}) is None   # a flagged creator stays a NO
    assert ag.agent_holder_pass({**base, 'top10': 45, 'fails': ['Top 10 under 25%']}) is None                                     # past the agents' 40% line
    assert ag.agent_holder_pass({**base, 'dev': None, 'fails': ['Dev holds under 5%']}) is None                                   # unread = fails closed
    assert ag.agent_holder_pass({**base, 'safe': True, 'fails': []}) is None
    import office as of
    w = of.warden(1.0, {'holderSoft': ['Top 10 under 25%']}, floor=0.05)
    assert any(r['id'] == 'W21 concentrated launch' and r['mult'] == 0.5 for r in w['rules'])
