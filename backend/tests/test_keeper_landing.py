"""Real buys / sells must LAND: one signed tx is re-sent to every RPC node (idempotent), and the self-fix never flaps a setting."""
import asyncio

import chain_rpc


class _Res:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


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
