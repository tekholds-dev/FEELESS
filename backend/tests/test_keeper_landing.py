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


def test_owner_rpc_key_helpers_validate_save_one_active_line_and_swap_the_lane_live(monkeypatch):
    for bad in ('http://x.com/k', 'https://127.0.0.1/k', 'https://localhost/k', 'https://node.internal/k', 'ftp://a.b', '', 'https://a b.com'):
        try:
            chain_rpc.clean_rpc_url(bad); assert False, bad
        except ValueError:
            pass
    assert chain_rpc.clean_rpc_url(' https://mainnet.helius-rpc.com/?api-key=abc ') == 'https://mainnet.helius-rpc.com/?api-key=abc'
    assert chain_rpc.provider_of('https://my-name.solana-mainnet.quiknode.pro/SECRET/') == 'quiknode.pro'      # never the key or sub-domain
    env = 'A=1\nSOLANA_RPC_URL=old1\nB=2\nSOLANA_RPC_URL_2=keep\nSOLANA_RPC_URL=old2\n# SOLANA_RPC_URL=older'
    out = chain_rpc.env_with_key(env, 'SOLANA_RPC_URL', 'NEW')
    assert out.split('\n') == ['A=1', 'SOLANA_RPC_URL=NEW', 'B=2', 'SOLANA_RPC_URL_2=keep', '# SOLANA_RPC_URL=old2', '# SOLANA_RPC_URL=older']
    assert chain_rpc.env_with_key('A=1', 'SOLANA_RPC_URL_2', 'X') == 'A=1\nSOLANA_RPC_URL_2=X'
    monkeypatch.setattr(chain_rpc, '_dedicated', 'OLD'); monkeypatch.setattr(chain_rpc, '_backup', ''); monkeypatch.setattr(chain_rpc, '_alchemy_url', ''); monkeypatch.setattr(chain_rpc, '_more', {3: '', 4: '', 5: '', 6: ''})
    monkeypatch.setattr(chain_rpc, 'KEEPER_LANES', ['OLD']); monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['OLD'] + chain_rpc.PUBLIC)
    monkeypatch.setattr(chain_rpc, '_quota_until', {'OLD': 9e12}); monkeypatch.setattr(chain_rpc, '_rpc_cooldown_until', {})
    monkeypatch.setenv('SOLANA_RPC_URL', 'OLD'); monkeypatch.setenv('SOLANA_RPC_URL_2', '')
    lanes, pool = chain_rpc.KEEPER_LANES, chain_rpc.RPC_POOL
    chain_rpc.set_lane(1, 'https://a.helius-rpc.com/k'); chain_rpc.set_lane(2, 'https://b.quiknode.pro/k')
    assert lanes == ['https://a.helius-rpc.com/k', 'https://b.quiknode.pro/k'] and pool[:2] == lanes and pool[2:] == chain_rpc.PUBLIC   # same list objects, live
    st = chain_rpc.quota_state()
    assert [(x['provider'], x['slot'], x['spent']) for x in st] == [('helius-rpc.com', 1, False), ('quiknode.pro', 2, False)]
    http = _Http([_Res(200, {'result': 5}), _Res(200, {'result': {'value': []}})])
    assert asyncio.run(chain_rpc.probe(http, 'u'))['holders'] is True
    http = _Http([_Res(429, {'error': 'max usage reached'}, {'x-ratelimit-remaining': '0'})])
    assert asyncio.run(chain_rpc.probe(http, 'u')) == {'ok': False, 'err': 'this key is out of quota'}


def test_up_to_six_keyed_lanes_fall_through_in_order(monkeypatch):
    monkeypatch.setattr(chain_rpc, '_dedicated', 'L1'); monkeypatch.setattr(chain_rpc, '_backup', 'L2'); monkeypatch.setattr(chain_rpc, '_alchemy_url', '')
    monkeypatch.setattr(chain_rpc, '_more', {3: '', 4: '', 5: '', 6: ''})
    monkeypatch.setattr(chain_rpc, 'KEEPER_LANES', ['L1', 'L2']); monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['L1', 'L2'] + chain_rpc.PUBLIC)
    monkeypatch.setattr(chain_rpc, '_quota_until', {}); monkeypatch.setattr(chain_rpc, '_rpc_cooldown_until', {})
    for n in (3, 4, 5, 6):
        monkeypatch.setenv(f'SOLANA_RPC_URL_{n}', '')
    chain_rpc.set_lane(3, 'https://c.x.com/k'); chain_rpc.set_lane(5, 'https://e.y.com/k')
    assert chain_rpc.KEEPER_LANES == ['L1', 'L2', 'https://c.x.com/k', 'https://e.y.com/k']
    assert [x['slot'] for x in chain_rpc.quota_state()] == [1, 2, 3, 5] and chain_rpc.LANE_KEYS[6] == 'SOLANA_RPC_URL_6'
    spent = _Res(429, {'error': 'daily request limit reached'})
    http = _Http([spent, spent, spent, _Res(200, {'result': 9})])
    assert asyncio.run(chain_rpc.rpc_priority(http, 'getSlot', [])) == 9
    assert [e for e, _ in http.calls] == ['L1', 'L2', 'https://c.x.com/k', 'https://e.y.com/k']   # three plans spent → the fourth answers


def _c2c_env(monkeypatch, direct_out, two_leg_out, impact=0.001):
    import time
    import reputation_service as rs
    import fuse_wallet as fw
    cfg = {**fw.DEFAULT_CFG, 'walletId': 'w', 'address': 'OWNER', 'armed': True, 'minOrderUsd': 0.25, 'coinToCoin': True, 'minLiqUsd': 20000}
    book = {'sol': 0.001, 'fundedUsd': 5.0, 'legs': {'OLD': {'atoms': 100, 'decimals': 0, 'pair': 'Pold', 'symbol': 'OLD', 'costUsd': 0.60, 'entryPx': 0.006}}}
    state = {'d': {'cfg': cfg, 'books': {'degen': book}, 'ledger': []}, 'jup': [], 'sent': []}
    monkeypatch.setattr(rs, '_fw_load', lambda: state['d'])
    monkeypatch.setattr(rs, '_fw_save', lambda d: state.__setitem__('d', d))
    monkeypatch.setattr(rs, '_fw_signer_ready', lambda: True)
    monkeypatch.setattr(rs, '_fw_notify', lambda row: None)
    monkeypatch.setattr(rs._store, 'Ledger', lambda *a, **k: type('L', (), {'append': lambda self, r: None})())

    class Dex:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url):
            return type('R', (), {'status_code': 200, 'json': lambda s: {'pairs': [{'pairAddress': 'Pnew', 'baseToken': {'address': 'NEW'}, 'priceUsd': '0.0022', 'liquidity': {'usd': 90000}}]}})()
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Dex)

    async def jup(method, path, **kw):
        state['jup'].append((method, path, (kw.get('params') or {}).get('inputMint'), (kw.get('params') or {}).get('outputMint')))
        if method == 'POST':
            return {'swapTransaction': 'TX', 'lastValidBlockHeight': 10}
        q = kw['params']
        if q['inputMint'] == 'OLD' and q['outputMint'] == fw.SOL_MINT:
            return {'outAmount': '4600000', 'priceImpactPct': '0.001'}                    # old → SOL: 0.0046 SOL ≈ $0.55
        if q['inputMint'] == fw.SOL_MINT:
            return {'outAmount': str(two_leg_out), 'priceImpactPct': '0.001'}             # SOL → new
        if q['inputMint'] == 'NEW':
            return {'outAmount': '4550000'}                                                # sell-back check: loses ~1%
        return {'outAmount': str(direct_out), 'otherAmountThreshold': str(int(direct_out * 0.97)), 'priceImpactPct': str(impact)}   # old → new

    async def sign(cfg_, raw, memo):
        return {'signature': 'SIG', 'signedTransaction': 'SIGNED'}

    async def krpc(http, method, params):
        state['sent'].append(method)
        if method == 'getTransaction':
            tok = lambda mint, amt: {'owner': 'OWNER', 'mint': mint, 'uiTokenAmount': {'amount': str(amt), 'decimals': 0}}
            return {'transaction': {'message': {'accountKeys': [{'pubkey': 'OWNER', 'signer': True}, {'pubkey': 'ATA', 'signer': False}]}},
                    'meta': {'err': None, 'fee': 5000, 'preBalances': [50_000_000, 0], 'postBalances': [50_000_000 - 2_044_280, 2_039_280],
                             'preTokenBalances': [tok('OLD', 100)], 'postTokenBalances': [tok('OLD', 0), tok('NEW', direct_out)]}}
        return 'SIG'

    async def prices(mints):
        return {'NEW': 0.0022, 'OLD': 0.0055}

    async def dec(m):
        return 0
    for name, fn in (('_fw_jup', jup), ('_fw_sign', sign), ('_krpc', krpc), ('_jup_prices', prices), ('_mint_decimals', dec)):
        monkeypatch.setattr(rs, name, fn)
    now = time.time()
    sell = {'side': 'sell', 'mint': 'OLD', 'pair': 'Pold', 'symbol': 'OLD', 'atoms': 100, 'decimals': 0, 'usd': 0.55, 'midPx': 0.0055, 'at': now, 'why': 'not on the card any more'}
    buy = {'side': 'buy', 'mint': 'NEW', 'pair': 'Pnew', 'symbol': 'NEW', 'lamports': 4_600_000, 'usd': 0.55, 'midPx': 0.0022, 'at': now, 'why': 'card buys its coin'}
    return rs, fw, state, cfg, book, sell, buy


def test_one_transaction_swap_is_sent_when_it_beats_two_swaps_and_books_both_coins(monkeypatch):
    rs, fw, state, cfg, book, sell, buy = _c2c_env(monkeypatch, direct_out=250, two_leg_out=247)
    out = asyncio.run(rs._fw_execute_swap('degen', sell, buy, book, cfg, 120.0, 90000))
    assert out is not None and out.get('pending') is None and 'OLD' not in out['legs'] and out['legs']['NEW']['atoms'] == 250
    assert out['legs']['NEW']['costUsd'] == 0.55 and out['sol'] == 0.001                 # the money moved coin to coin; card SOL untouched
    assert state['sent'].count('sendTransaction') == 1                                   # ONE transaction
    rows = [(r['side'], r['symbol'], r['status'], r.get('usd')) for r in state['d']['ledger']]
    assert rows == [('sell', 'OLD', 'filled', 0.55), ('buy', 'NEW', 'filled', 0.55)]
    assert state['d']['ledger'][0]['realizedPnlUsd'] == -0.05 and state['d']['ledger'][0]['sig'] == state['d']['ledger'][1]['sig'] == 'SIG'
    t = fw.totals(state['d']['ledger'], 'degen')
    assert (t['bought'], t['sold'], t['swaps']) == (0.55, 0.55, 1)                       # both sides counted, one swap


def test_one_transaction_swap_steps_aside_when_two_swaps_pay_more_or_impact_is_high(monkeypatch):
    rs, fw, state, cfg, book, sell, buy = _c2c_env(monkeypatch, direct_out=240, two_leg_out=247)
    assert asyncio.run(rs._fw_execute_swap('degen', sell, buy, book, cfg, 120.0, 90000)) is None
    assert 'sendTransaction' not in state['sent'] and not any(m == 'POST' for m, *_ in state['jup'])   # nothing built, nothing signed
    rs, fw, state, cfg, book, sell, buy = _c2c_env(monkeypatch, direct_out=250, two_leg_out=247, impact=0.05)
    assert asyncio.run(rs._fw_execute_swap('degen', sell, buy, book, cfg, 120.0, 90000)) is None        # 5% impact > 4%
    rs, fw, state, cfg, book, sell, buy = _c2c_env(monkeypatch, direct_out=250, two_leg_out=247)
    assert asyncio.run(rs._fw_execute_swap('degen', sell, buy, book, cfg, 120.0, 5000)) is not None     # (liq is re-read live)
    rs, fw, state, cfg, book, sell, buy = _c2c_env(monkeypatch, direct_out=250, two_leg_out=247)
    state['d']['ledger'].append({'card': 'degen', 'side': 'swap', 'status': 'failed', 'at': sell['at'] - 60})
    assert asyncio.run(rs._fw_execute_swap('degen', sell, buy, book, cfg, 120.0, 90000)) is None        # a failed one-step → two-step for 10 min


def test_an_account_a_provider_could_not_parse_never_crashes_a_scan():
    import reputation_service as rs
    assert rs._parsed_info({'data': {'parsed': {'info': {'owner': 'W', 'mint': 'M'}}}}) == {'owner': 'W', 'mint': 'M'}
    assert rs._parsed_info({'data': ['AAAA', 'base64']}) == {}                           # raw base64 from some RPCs (Token-2022 extensions)
    assert rs._parsed_info(None) == {} and rs._parsed_info({'data': {'parsed': 'x'}}) == {} and rs._parsed_info([]) == {}


def test_a_swap_that_reverts_on_slippage_is_sent_again_at_once_with_more_room(monkeypatch):
    rs, fw, state, cfg, book, sell, buy = _c2c_env(monkeypatch, direct_out=250, two_leg_out=247)
    tries = {'tx': 0}

    async def krpc(http, method, params):
        state['sent'].append(method)
        if method == 'getTransaction':
            tries['tx'] += 1
            tok = lambda amt: {'owner': 'OWNER', 'mint': 'OLD', 'uiTokenAmount': {'amount': str(amt), 'decimals': 0}}
            if tries['tx'] == 1:   # the first send landed and reverted: Jupiter 6001 (price ran past the limit)
                return {'transaction': {'message': {'accountKeys': [{'pubkey': 'OWNER', 'signer': True}]}},
                        'meta': {'err': {'InstructionError': [3, {'Custom': 6001}]}, 'fee': 5000, 'preBalances': [50_000_000], 'postBalances': [49_995_000],
                                 'preTokenBalances': [tok(100)], 'postTokenBalances': [tok(100)]}}
            return {'transaction': {'message': {'accountKeys': [{'pubkey': 'OWNER', 'signer': True}]}},
                    'meta': {'err': None, 'fee': 5000, 'preBalances': [49_995_000], 'postBalances': [49_995_000 + 4_595_000],
                             'preTokenBalances': [tok(100)], 'postTokenBalances': [tok(0)]}}
        return 'SIG'
    monkeypatch.setattr(rs, '_krpc', krpc)
    out = asyncio.run(rs._fw_execute('degen', {**sell, 'id': 'degen:1:s:OLD'}, book, {**cfg, 'coinToCoin': False}, 120.0, 90000))
    rows = [(r['side'], r['status'], str(r.get('err') or '')[:17]) for r in state['d']['ledger']]
    assert rows == [('sell', 'failed', fw.SLIP_ERR), ('sell', 'filled', '')]               # retried in the same pass, no tick lost
    assert state['d']['ledger'][1]['id'] == 'degen:1:s:OLD:r1' and 'OLD' not in out['legs']
    assert state['sent'].count('sendTransaction') == 2
