from fee_report import ledger_row, fee_report

NOW = 1_000_000_000


def test_week_and_total():
    # a = selling $FEE (FeeBack), b + c = ordinary coin trades (fee paid, no FeeBack)
    rows = [ledger_row(NOW - 3600, 'a', 100, 50, feeback=True), ledger_row(NOW - 3 * 86400, 'b', 200, 50), ledger_row(NOW - 30 * 86400, 'c', 1000, 50)]
    r = fee_report(rows, NOW)
    assert r['fees7dUsd'] == 1.5 and r['trades7d'] == 2 and r['feesTotalUsd'] == 6.5
    assert r['days'][6] == 0.5 and r['days'][3] == 1.0 and len(r['days']) == 7
    assert r['feeBackUsd'] == 0.5 and r['feeBack7dUsd'] == 0.5 and r['feeBackStatus'] == 'accruing'


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


def test_referral_credit():
    from fee_report import referral_credit
    book = referral_credit({}, 'INV', 'A', {'feeUsd': 2.0, 'feeSol': 0.01}, 10, NOW)
    book = referral_credit(book, 'INV', 'B', {'feeUsd': 1.0}, 10, NOW)
    assert book['INV']['usd'] == 0.3 and book['INV']['sol'] == 0.001 and book['INV']['trades'] == 2 and book['INV']['invitees'] == ['A', 'B']
    assert referral_credit({}, 'INV', 'A', {'feeUsd': 2.0}, 0, NOW) == {}
    assert referral_credit({}, 'INV', 'A', {'feeUsd': 2.0}, 90, NOW)['INV']['usd'] == 1.0   # capped at 50%


def test_lifetime_fee_book():
    from fee_report import add_total, fee_book
    tot = {}
    for i in range(3):
        add_total(tot, 'A', ledger_row(NOW + i, f's{i}', 100, 50, feeback=True))
    add_total(tot, 'B', ledger_row(NOW, 'b', 1000, 50, feeback=True))
    add_total(tot, 'C', ledger_row(NOW, 'c', 1000, 50))   # SOL → ordinary coin: fee on the books, no FeeBack
    assert tot['A']['trades'] == 3 and tot['A']['feeUsd'] == 1.5 and tot['A']['first'] == NOW and tot['A']['last'] == NOW + 2
    book = fee_book(tot, {'B': 1.0}, 100)
    assert [r['address'] for r in book][:1] == ['B'] and book[0]['owedUsd'] == 4.0
    by = {r['address']: r for r in book}
    assert by['A']['owedUsd'] == 1.5 and by['C']['feeUsd'] == 5.0 and by['C']['feeBackUsd'] == 0
