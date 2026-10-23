"""⚡ scripts/cash-check.py — the fast real-card cash check judges each swap against the chain without the network."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location('cash_check', Path(__file__).resolve().parents[2] / 'scripts' / 'cash-check.py')
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)


def test_a_sell_that_matches_the_chain_is_ok():
    row = {'side': 'sell', 'sol': 0.003277679, 'feeSol': 9.579e-06, 'at': 100}
    assert cc.explain(row, 0.0032681, [])[0] == 'ok'


def test_a_buy_counts_swap_plus_new_account_rent():
    row = {'side': 'buy', 'sol': 0.004494133, 'feeSol': 9.53e-06, 'at': 100}
    assert cc.explain(row, -0.004503663, [])[0] == 'ok'


def test_route_rent_on_a_sell_is_explained_only_by_a_later_credited_close():
    row = {'side': 'sell', 'sol': 0.002499267, 'feeSol': 5.239e-06, 'at': 100}
    chain = -0.000482852                                   # the route opened 2 accounts (0.00297688 rent) inside the sell
    assert cc.explain(row, chain, [])[0] == 'GAP'
    assert cc.explain(row, chain, [{'side': 'close', 'status': 'credited', 'sol': 0.00449072, 'at': 400}])[0] == 'route rent'
    assert cc.explain(row, chain, [{'side': 'close', 'status': 'credited', 'sol': 0.00449072, 'at': 9000}])[0] == 'GAP'   # an hour+ later is not this sell's


def test_coverage_splits_card_cash_from_the_gas_reserve():
    cov = cc.coverage(0.013605, {'sol': 0.006128, 'bankSol': 0}, 0.019)
    assert cov['covered'] and abs(cov['reserveHeld'] - 0.007477) < 1e-9 and cov['outsideSol'] == 0
    assert not cc.coverage(0.005, {'sol': 0.006}, 0.019)['covered']


def test_pnl_replay_rebuilds_the_books_average_cost_in_dollars():
    rows = [{'side': 'buy', 'mint': 'A', 'symbol': 'A', 'usd': 1.0, 'units': 100, 'feeUsd': 0.01},
            {'side': 'buy', 'mint': 'A', 'symbol': 'A', 'usd': 3.0, 'units': 100, 'feeUsd': 0.01},
            {'side': 'sell', 'mint': 'A', 'symbol': 'A', 'units': 50, 'costUsd': 1.0, 'proceedsUsd': 1.5, 'realizedPnlUsd': 0.5, 'feeUsd': 0.01},   # avg $0.02 × 50
            {'side': 'sell', 'mint': 'A', 'symbol': 'A', 'units': 150, 'costUsd': 2.0, 'proceedsUsd': 2.0, 'realizedPnlUsd': 0.4, 'feeUsd': 0.01},   # book says $2, replay $3; realized ≠ 2 − 2
            {'side': 'sell', 'mint': 'OLD', 'symbol': 'OLD', 'units': 5, 'costUsd': 9.0, 'proceedsUsd': 1.0, 'realizedPnlUsd': -8.0}]                 # bought before the window: not judged
    out = cc.pnl_replay(rows)
    assert out['sells'] == 2 and out['ok'] == 1 and out['off'] == [('A', 2.0, 3.0)] and out['bad'] == 1
    assert round(out['realized'], 4) == -7.1 and round(out['fees'], 4) == 0.04
    wo = cc.pnl_replay([{'side': 'buy', 'mint': 'C', 'usd': 0.4753, 'units': 1237}, {'side': 'writeoff', 'mint': 'C', 'costUsd': 0.4753},
                        {'side': 'sell', 'mint': 'C', 'symbol': 'C', 'units': 1237, 'costUsd': 0.0, 'proceedsUsd': 0.0038, 'realizedPnlUsd': 0.0038}])
    assert wo['ok'] == 1 and wo['off'] == [] and wo['writeoffs'] == 1 and round(wo['realized'], 4) == -0.4715   # a drained pool: cost written off, then $0 basis
