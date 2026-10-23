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
