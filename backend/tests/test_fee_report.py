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
