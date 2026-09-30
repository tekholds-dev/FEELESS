from fee_report import ledger_row, fee_report

NOW = 1_000_000_000


def test_week_and_total():
    rows = [ledger_row(NOW - 3600, 'a', 100, 50), ledger_row(NOW - 3 * 86400, 'b', 200, 50), ledger_row(NOW - 30 * 86400, 'c', 1000, 50)]
    r = fee_report(rows, NOW)
    assert r['fees7dUsd'] == 1.5 and r['trades7d'] == 2 and r['feesTotalUsd'] == 6.5
    assert r['days'][6] == 0.5 and r['days'][3] == 1.0 and len(r['days']) == 7
    assert r['feeBackUsd'] == 6.5 and r['feeBackStatus'] == 'accruing'


def test_empty_and_fee_free():
    assert fee_report([], NOW)['feesTotalUsd'] == 0
    assert ledger_row(NOW, 'x', 50, 0)['feeUsd'] == 0


def test_real_fee_atoms_win():
    from fee_report import SOL_MINT, USDC_MINT
    r = ledger_row(NOW, 's', 0, 50, 5_000_000, SOL_MINT, 150)   # USD value missing from the quote
    assert r['feeSol'] == 0.005 and r['feeUsd'] == 0.75
    assert ledger_row(NOW, 'u', 100, 50, 480_000, USDC_MINT)['feeUsd'] == 0.48
    assert ledger_row(NOW, 'x', 100, 50)['feeUsd'] == 0.5
    assert fee_report([ledger_row(NOW - 60, 's', 0, 50, 5_000_000, SOL_MINT)], NOW)['fees7dSol'] == 0.005
