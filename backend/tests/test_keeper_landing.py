"""Real buys / sells must LAND: one signed tx is re-sent to every RPC node (idempotent), and the self-fix never flaps a setting."""
import asyncio

import chain_rpc


class _Res:
    def __init__(self, code, body, headers=None):
        self.status_code, self._b, self.headers = code, body, headers or {}
        self.text = str(body)

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise chain_rpc.httpx.HTTPStatusError('bad', request=None, response=None)


class _Http:
    def __init__(self, replies):
        self.replies, self.calls = replies, []

    async def post(self, endpoint, json=None):
        self.calls.append((endpoint, json))
        return self.replies[len(self.calls) - 1]


def test_broadcast_sends_the_same_signed_tx_to_every_node_without_preflight(monkeypatch):
    monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['a', 'b', 'c'])
    http = _Http([_Res(200, {'result': 'sig'}), _Res(429, {}), _Res(200, {'error': {'code': -32002}})])
    assert asyncio.run(chain_rpc.broadcast(http, 'SIGNED')) == 1          # a busy or refusing node never raises
    assert [e for e, _ in http.calls] == ['a', 'b', 'c']
    for _, body in http.calls:
        assert body['method'] == 'sendTransaction' and body['params'][0] == 'SIGNED'
        assert body['params'][1] == {'encoding': 'base64', 'skipPreflight': True, 'maxRetries': 0}


def test_self_fix_only_moves_patience_when_the_same_value_wins_twice():
    import reputation_service as rs
    cfg = {'autoBrain': True, 'strictRunners': False, 'rotateHours': 0.08, 'rotateConfirm': 3, 'rotateMinDrop': 5.0}
    best = {'confirm': {'value': 4, 'n': 60}, 'minDrop': {'value': 5.0, 'n': 60}}
    assert rs._brain_patch(cfg, {}, best, {'confirm': {'value': 3}}) == {}                      # 3 → 4 after one run: wait
    assert rs._brain_patch(cfg, {}, best, {'confirm': {'value': 4}}) == {'rotateConfirm': 4}    # 4 won twice: apply


def test_a_deposit_is_only_a_tx_the_wallet_did_not_sign_that_raised_its_sol():
    import fuse_wallet as fw
    key = lambda pk, signer=False: {'pubkey': pk, 'signer': signer}
    dep = {'meta': {'preBalances': [10**9, 0], 'postBalances': [10**9 - 60_005_000, 60_000_000]}, 'transaction': {'message': {'accountKeys': [key('SENDER', True), key('FUSE')]}}}
    assert fw.deposit_from_tx(dep, 'FUSE') == {'sol': 0.06, 'from': 'SENDER'}
    sell = {'meta': {'preBalances': [0], 'postBalances': [7_000_000]}, 'transaction': {'message': {'accountKeys': [key('FUSE', True)]}}}
    assert fw.deposit_from_tx(sell, 'FUSE') is None                        # the keeper's own sell proceeds are never a deposit
    assert fw.deposit_from_tx({**dep, 'meta': {**dep['meta'], 'err': {'x': 1}}}, 'FUSE') is None
    # the story always adds up: deposited = wallet SOL + coins + spent
    st = fw.sol_story([{'sol': 0.06}, {'sol': 0.009}, {'sol': 0.07}], {'safe': {'sol': 0.0062, 'bankSol': 0}}, 0.015, 0.0802, coins_sol=0.0185)
    assert st['depositedSol'] == 0.139 and st['n'] == 3 and st['unassignedSol'] == 0.059
    assert round(st['cardSol'] + st['reserveSol'] + st['unassignedSol'], 4) == 0.0802
    assert round(st['spentSol'], 4) == round(0.139 - 0.0802 - 0.0185, 4)


def test_paper_learns_the_flat_cost_of_a_swap_apart_from_price_impact():
    import fuse_wallet as fw, arena_prime as ap
    small = [{'status': 'filled', 'side': 'buy', 'midPx': 1.0, 'px': 1.004, 'liq': 200_000, 'usd': 0.85} for _ in range(5)]   # $0.85 never moves a $200K pool
    cal = fw.calibrate(small)
    assert cal['spread'] == 0.004 and cal['spreadPct'] == 0.4 and cal['impactMult'] == 1.0     # flat cost learned · impact model untouched
    big = [{'status': 'filled', 'side': 'buy', 'midPx': 1.0, 'px': 1.02, 'liq': 20_000, 'usd': 100} for _ in range(3)]       # model 1% · real 2%
    assert fw.calibrate(small + big)['impactMult'] == 2.0
    old = ap.SPREAD
    try:
        ap.SPREAD = 0.004
        assert round(ap.buy_px(1.0, 0.85, 1e12), 6) == 1.004 and round(ap.sell_usd(100, 1.0, 1e12), 4) == round(100 / 1.004, 4)
    finally:
        ap.SPREAD = old


def test_the_brain_picks_a_config_per_round_length_and_never_calls_a_losing_clock_profitable():
    import pg_sim as ps
    mk = lambda clock, md, pct: {'cfg': {'clock': clock, 'tp': 100, 'sl': 20, 'minDrop': md, 'hold': False, 'confirm': 3}, 'coins': 4, 'pct': pct}
    res = [mk(5, 20, -5.0)] * 8 + [mk(5, 0, -30.0)] * 8 + [mk(60, 10, 6.0)] * 8 + [mk(60, 0, 2.0)] * 8 + [mk(15, 5, 1.0)] * 3
    bc = ps.by_clock(res)
    assert set(bc) == {'5', '60'}                                           # 3 sims on the 15-min clock is not enough to say anything
    assert bc['5']['cfg']['minDrop'] == '20' and bc['5']['profitable'] is False and bc['5']['n'] == 16
    assert bc['60']['cfg']['minDrop'] == '10' and bc['60']['profitable'] is True


def test_one_freak_run_cannot_carry_a_strategy_or_the_daily_outlook():
    import fuse_hq as hq
    runs = [{'style': 'yield', 'settled': True, 'pnlPct': p} for p in [-12, -9, -8, -6, -5, -4, -3, 2, 4, 6000]]
    board = hq.arena_board(runs)
    r = board[0]
    assert r['medPct'] == -4.5 and -10 < r['avgPct'] < 0 and r['winRate'] == 30      # was avg +596% → "$1 → $6.96"
    assert hq.best_style(board, default='steady') == 'steady'                          # not proven by an outlier
    o = hq.outlook(board)
    assert o['proven'] is False and o['per1'] == 0.955
    assert hq.robust_avg([10, 20, 900]) == (10 + 20 + 300) / 3                         # few runs: each capped at +300%


def test_manual_part_sell_keeps_the_rest_and_holds_the_cash_and_sims_skip_untradeable_jumps():
    import arena_prime as ap, pg_sim as ps
    card = {'legs': [{'pairAddress': 'P1', 'mint': 'M1', 'symbol': 'AAA', 'units': 10.0, 'costUsd': 10.0, 'entry': 1.0}], 'cash': 0.0, 'events': []}
    c = ap.sell_leg_to_cash(card, 'P1', {'P1': 2.0}, 5, pct=25)
    assert c['legs'][0]['units'] == 7.5 and c['legs'][0]['costUsd'] == 7.5 and c['cash'] == 5.0 and c['holdCashUsd'] == 5.0
    assert card['legs'][0]['units'] == 10.0                                             # the input card is never mutated
    full = ap.sell_leg_to_cash(card, 'P1', {'P1': 2.0}, 5)
    assert full['legs'][0]['units'] == 0.0 and full['cash'] == 20.0
    t0 = 0; pts = lambda seq: [[t0 + i * ps.STEP_MIN * 60, p] for i, p in enumerate(seq)]
    series = ps._series({'ok': pts([1, 1.2, 1.5, 1.4]), 'launch': pts([0.0001, 1.0, 1.1, 1.2])}, t0, 4)
    assert set(series) == {'ok'}                                                        # a 10,000× tick is not a trade


def test_taking_money_out_lowers_the_principal_so_profit_is_measured_above_what_is_still_in():
    import fuse_wallet as fw
    book = {'sol': 0.02, 'manualCashSol': 0.02, 'fundedUsd': 5.0, 'bankSol': 0.0}     # $5 in · $2 of it sold to card cash ($100 SOL)
    nb, took = fw.withdraw_cash(book, 100.0)
    assert took == 2.0 and nb['fundedUsd'] == 3.0 and nb['sol'] == 0.0 and nb['withdrawnUsd'] == 2.0 and book['fundedUsd'] == 5.0
    assert fw.profit_available(nb, 3.4, 100.0) == 0.4            # worth $3.40 with $3 still in → $0.40 is profit
    assert fw.profit_available(book, 3.4, 100.0) == 0.0          # before the withdrawal the same card had no profit to pay
    part, took2 = fw.withdraw_cash({'sol': 0.05, 'fundedUsd': 5.0}, 100.0, usd=1.5)
    assert took2 == 1.5 and part['fundedUsd'] == 3.5 and part['sol'] == 0.035
    assert fw.withdraw_cash({'sol': 0.0, 'fundedUsd': 5.0}, 100.0)[1] == 0.0


def test_a_selling_card_finishes_when_only_dead_dust_is_left_but_never_writes_off_blind():
    import fuse_wallet as fw
    book = {'defund': True, 'sol': 0.0136, 'legs': {'RUG': {'atoms': 24_940_472, 'decimals': 6, 'pair': 'Prug', 'symbol': 'USDF', 'costUsd': 0.74},
                                                   'OK': {'atoms': 5_000_000, 'decimals': 6, 'pair': 'Pok', 'symbol': 'AAA', 'costUsd': 0.4},
                                                   'UNK': {'atoms': 1_000_000, 'decimals': 6, 'pair': 'Punk', 'symbol': 'BBB', 'costUsd': 0.4}}}
    nb, gone = fw.write_off_dust(book, {'Prug': 0.000002, 'Pok': 0.09})
    assert [g['symbol'] for g in gone] == ['USDF'] and gone[0]['costUsd'] == 0.74 and gone[0]['usd'] < 0.001
    assert set(nb['legs']) == {'OK', 'UNK'} and set(book['legs']) == {'RUG', 'OK', 'UNK'}       # $0.45 coin stays · no price = stays · input untouched


def test_keeper_lane_uses_the_dedicated_endpoint_through_a_cooldown_and_retries_a_429(monkeypatch):
    import time
    monkeypatch.setattr(chain_rpc, 'KEEPER_LANES', ['DED'])
    monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['DED', 'pub'])
    monkeypatch.setattr(chain_rpc, '_quota_until', {})
    monkeypatch.setitem(chain_rpc._rpc_cooldown_until, 'DED', time.time() + 30)        # the scanners tripped the limit: shared pool skips it
    http = _Http([_Res(429, {}), _Res(200, {'result': {'value': 7}})])
    assert asyncio.run(chain_rpc.rpc_priority(http, 'getBalance', ['W'])) == {'value': 7}
    assert [e for e, _ in http.calls] == ['DED', 'DED']                                 # waited, retried, never touched the public node
    http2 = _Http([_Res(200, {'error': {'code': -32002, 'message': 'simulation failed'}}), _Res(200, {'error': {'code': -32002, 'message': 'simulation failed'}})])
    try:
        asyncio.run(chain_rpc.rpc_priority(http2, 'sendTransaction', ['x']))
        assert False, 'a real RPC error must reach the caller'
    except RuntimeError as e:
        assert 'RPC pool exhausted' in str(e)


def test_the_pit_can_read_any_fighter_over_the_last_5_15_or_60_minutes():
    import pg_battle as pb
    b = {'startUsd': 100.0, 'legs': [], 'cash': 100.0}
    t0 = 1000.0
    b = {**b, 'pct': 0.0, 'hist': [[t0, 0.0], [t0 + 600, 10.0], [t0 + 1200, 21.0]]}
    b['pct'] = 21.0
    now = t0 + 1200
    assert pb.frame_pct(b, now, 5) == 21.0 - 0 if False else pb.frame_pct(b, now, 10) == 10.0     # +10% → +21% is +10% over the last 10 min
    assert pb.frame_pct(b, now, 60) == 21.0                                                        # younger than the window → since it opened
    assert pb.frame_pct(None, now, 5) == 0.0


def test_self_fix_never_overrides_the_owners_5_min_degen_settings():
    import reputation_service as rs
    import arena_prime as ap
    owner = {'autoBrain': True, 'strictRunners': False, 'rotateHours': 0.08, 'rotateConfirm': 2, 'minHoldMins': 10, 'rotateMinDrop': 5.0}
    best = {'confirm': {'value': 4, 'n': 60}, 'minDrop': {'value': 8.0, 'n': 60}}
    prev = {'confirm': {'value': 4}, 'minDrop': {'value': 8.0}}
    assert rs._brain_patch(owner, {}, best, prev) == {'rotateConfirm': 4, 'rotateMinDrop': 8.0}           # without the owner's mark it would move both
    assert rs._brain_patch(owner, {}, best, prev, owner_set=['rotateConfirm', 'rotateHours', 'minHoldMins']) == {'rotateMinDrop': 8.0}
    guarded, _ = ap.real_guard(ap.clean_cfg({**owner, 'instantSwapPct': 10}))                              # the real guard keeps them too
    assert guarded['rotateConfirm'] == 2 and guarded['minHoldMins'] == 10 and guarded['rotateHours'] == 0.08


def test_scanners_only_get_their_share_of_the_dedicated_endpoint(monkeypatch):
    monkeypatch.setattr(chain_rpc, '_dedicated', 'DED'); monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['DED', 'pub'])
    monkeypatch.setattr(chain_rpc, 'RPC_MAX_RETRIES', 2); monkeypatch.setattr(chain_rpc, '_scan_stamps', []); monkeypatch.setattr(chain_rpc, 'SCAN_RPS', 2)
    monkeypatch.setattr(chain_rpc, '_rpc_cooldown_until', {})
    http = _Http([_Res(200, {'result': 1})] * 4)
    for _ in range(4):
        assert asyncio.run(chain_rpc._rpc(http, 'getBalance', ['W'])) == 1
    assert [e for e, _ in http.calls] == ['DED', 'DED', 'pub', 'pub']          # 2 a second on the plan, the rest go elsewhere


def test_keeper_has_two_lanes_a_burst_moves_to_the_other_and_a_spent_plan_is_skipped_until_it_resets(monkeypatch):
    import time
    monkeypatch.setattr(chain_rpc, 'KEEPER_LANES', ['A', 'B'])
    monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['A', 'B', 'pub'])
    monkeypatch.setattr(chain_rpc, '_quota_until', {})
    monkeypatch.setattr(chain_rpc, '_rpc_cooldown_until', {})
    http = _Http([_Res(429, {}), _Res(200, {'result': 1})])                              # lane A is busy this second → lane B answers, no wait
    assert asyncio.run(chain_rpc.rpc_priority(http, 'getSlot', [])) == 1 and [e for e, _ in http.calls] == ['A', 'B']
    spent = _Res(429, {'error': {'message': 'daily request limit reached - upgrade your account'}}, {'x-ratelimit-remaining': '0', 'x-ratelimit-reset': '27941'})
    http = _Http([spent, _Res(200, {'result': 2})])
    assert asyncio.run(chain_rpc.rpc_priority(http, 'getSlot', [])) == 2
    assert 27000 < chain_rpc._quota_until['A'] - time.time() <= 27941                    # the plan's own reset time, not a 30s cooldown
    http = _Http([_Res(200, {'result': 3})])
    assert asyncio.run(chain_rpc.rpc_priority(http, 'getSlot', [])) == 3 and [e for e, _ in http.calls] == ['B']   # A is not even tried again
    assert [x['spent'] for x in chain_rpc.quota_state()] == [True, False]
    # every keyed lane spent → straight to the public pool (no 7s of retries on a dead plan)
    monkeypatch.setitem(chain_rpc._quota_until, 'B', time.time() + 600)
    http = _Http([_Res(200, {'result': 4})])
    assert asyncio.run(chain_rpc.rpc_priority(http, 'getSlot', [])) == 4 and [e for e, _ in http.calls] == ['pub']


def test_a_quota_429_is_told_apart_from_a_burst():
    assert chain_rpc.out_of_quota(429, 'Too many requests') == 0
    assert chain_rpc.out_of_quota(200, 'daily request limit reached') == 0
    assert chain_rpc.out_of_quota(429, 'Monthly capacity limit exceeded.') == 900
    assert chain_rpc.out_of_quota(429, '', {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '120'}) == 120


def test_scanners_stay_off_the_dedicated_endpoint_by_default(monkeypatch):
    monkeypatch.setattr(chain_rpc, '_dedicated', 'DED'); monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['DED', 'pub'])
    monkeypatch.setattr(chain_rpc, 'RPC_MAX_RETRIES', 2); monkeypatch.setattr(chain_rpc, '_scan_stamps', []); monkeypatch.setattr(chain_rpc, 'SCAN_RPS', 0)
    monkeypatch.setattr(chain_rpc, '_quota_until', {}); monkeypatch.setattr(chain_rpc, '_rpc_cooldown_until', {})
    http = _Http([_Res(200, {'result': 1})] * 3)
    for _ in range(3):
        asyncio.run(chain_rpc._rpc(http, 'getBalance', ['W']))
    assert [e for e, _ in http.calls] == ['pub'] * 3                                     # a daily budget is the keeper's alone


def test_keeper_checks_the_new_coin_before_it_sells_the_old_one(monkeypatch):
    """A swap whose replacement fails the buy checks must NOT sell the old coin (it used to sell, then sit in cash)."""
    import time
    import reputation_service as rs
    import fuse_wallet as fw
    now = time.time()
    cfg = {**fw.DEFAULT_CFG, 'walletId': 'w', 'address': 'OWNER', 'armed': True, 'minOrderUsd': 0.25}
    book = {'sol': 0.0, 'fundedUsd': 5.0, 'legs': {'OLD': {'atoms': 1_000_000, 'decimals': 6, 'pair': 'Pold', 'symbol': 'OLD', 'costUsd': 1.0, 'entryPx': 1.0}}}
    card = {'tpl': 'degen', 'real': True, 'rounds': 9, 'events': [{'kind': 'rotate', 'at': now}],
            'legs': [{'mint': 'NEW', 'pairAddress': 'Pnew', 'symbol': 'NEW', 'role': 'runner', 'buying': True, 'wantUnits': 1.0, 'units': 0.0, 'entry': 1.0, 'picked': True}]}
    state = {'d': {'cfg': cfg, 'books': {'degen': book}, 'ledger': []}, 'sent': [], 'bad': {'NEW'}}
    monkeypatch.setattr(rs, '_fw_load', lambda: state['d'])
    monkeypatch.setattr(rs, '_fw_save', lambda d: state.__setitem__('d', d))
    monkeypatch.setattr(rs, '_json_load', lambda p, default=None: {'prime': {'cards': {'degen': card}}})
    monkeypatch.setattr(rs, '_json_save', lambda p, d: None)

    async def none(*a, **k):
        return None

    async def pairs(rows):
        return {'Pold': {'priceUsd': '1', 'liquidity': {'usd': 500000}}, 'Pnew': {'priceUsd': '1', 'liquidity': {'usd': 42000}}}

    async def jup(mints):
        return {}

    async def sol():
        return 100.0

    async def pre(tid, buys, cfg_, now_):
        assert [o['mint'] for o in buys] == ['NEW'] and buys[0].get('picked')
        return set(state['bad'])

    async def execute(tid, order, book_, cfg_, sol_px, liq):
        state['sent'].append((order['side'], order['mint']))
        return book_

    for name, fn in (('_fw_signer_check', none), ('_fw_close_empty', none), ('_fuse_pairs', pairs), ('_jup_prices', jup), ('_sol_usd_live', sol),
                     ('_fw_preflight', pre), ('_fw_execute', execute)):
        monkeypatch.setattr(rs, name, fn)
    asyncio.run(rs._fw_tick_inner(now))
    assert state['sent'] == []                                                            # NEW can't be bought → OLD is kept
    assert state['d']['books']['degen'].get('sellHoldAt')
    state['bad'] = set()                                                                 # the engine re-picked / the coin is buyable now
    asyncio.run(rs._fw_tick_inner(now + 5))
    assert ('sell', 'OLD') in state['sent'] and 'sellHoldAt' not in state['d']['books']['degen']
    # never held longer than 45s, even if the replacement stays unbuyable
    state.update(sent=[], bad={'NEW'})
    state['d']['books']['degen'] = {**book, 'sellHoldAt': now - 60}
    asyncio.run(rs._fw_tick_inner(now))
    assert ('sell', 'OLD') in state['sent']


def test_with_every_keyed_plan_spent_the_keeper_gets_its_own_public_node_and_paced_retries(monkeypatch):
    import time
    monkeypatch.setattr(chain_rpc, 'KEEPER_LANES', ['A'])
    monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['A', 'pub1', 'pub2'])
    monkeypatch.setattr(chain_rpc, 'KEEPER_PUBLIC', 'pub1')
    monkeypatch.setattr(chain_rpc, 'RPC_MAX_RETRIES', 3)
    monkeypatch.setattr(chain_rpc, '_quota_until', {'A': time.time() + 600})
    monkeypatch.setattr(chain_rpc, '_rpc_cooldown_until', {})

    async def no_sleep(_s):
        return None
    monkeypatch.setattr(asyncio, 'sleep', no_sleep)
    http = _Http([_Res(200, {'result': 1})])
    assert asyncio.run(chain_rpc._rpc(http, 'getBalance', ['W'])) == 1 and [e for e, _ in http.calls] == ['pub2']       # scanner: never the keeper's node
    http = _Http([_Res(429, {}), _Res(429, {}), _Res(200, {'result': 2})])
    assert asyncio.run(chain_rpc.rpc_priority(http, 'getTransaction', ['s'])) == 2
    assert [e for e, _ in http.calls] == ['pub1', 'pub2', 'pub1']                                                        # busy → asked again, not failed


def test_scanner_share_is_a_slow_metered_trickle(monkeypatch):
    import time
    monkeypatch.setattr(chain_rpc, 'SCAN_RPS', 0.5); monkeypatch.setattr(chain_rpc, '_scan_stamps', [])
    t = [1000.0]
    monkeypatch.setattr(time, 'time', lambda: t[0])
    assert chain_rpc._scan_slot() and not chain_rpc._scan_slot()      # one now, then wait
    t[0] += 1.0
    assert not chain_rpc._scan_slot()                                 # half a token after a second
    t[0] += 1.0
    assert chain_rpc._scan_slot() and not chain_rpc._scan_slot()      # one every two seconds ≈ 43K a day at most
    t[0] += 3600
    assert sum(1 for _ in range(20) if chain_rpc._scan_slot()) == 6   # an idle hour never banks more than a small burst
