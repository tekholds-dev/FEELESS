import agent_eco as eco

CSV = 'date,description,amount\n2026-01-03,Invoice 12 client,5000\n2026-01-09,Office rent,-1200\n2026-02-02,Stripe sale,"$3,000.50"\n2026-02-05,Payroll,(2000)\nnot a line\n'


def test_the_math_is_exact_and_a_bad_line_is_counted_not_guessed():
    rows, skipped = eco.parse(CSV); s = eco.summary(rows, 25)
    assert skipped == 2 and len(rows) == 4
    assert s['income'] == 8000.5 and s['costs'] == 3200 and s['net'] == 4800.5 and s['taxSetAside'] == 1200.12 and s['burnPerMonth'] == 1600
    assert [m['net'] for m in s['months']] == [3800, 1000.5] and s['cats'][0] == {'cat': 'Payroll', 'usd': 2000}


def test_a_loss_sets_no_tax_aside():
    assert eco.summary(eco.parse('2026-01-01,Rent,-500')[0], 30)['taxSetAside'] == 0


def test_the_same_rows_give_the_same_hash_and_one_cent_changes_it():
    a, _ = eco.parse(CSV); b, _ = eco.parse(CSV.replace('5000', '5000.01'))
    assert eco.book_hash(a) == eco.book_hash(eco.parse(CSV)[0]) and eco.book_hash(a) != eco.book_hash(b)


def test_the_receipt_carries_totals_and_the_hash_never_a_row():
    rows, _ = eco.parse(CSV); f = eco.new_folder(1, 'Q1', rows, 25, 1793000000); r = eco.receipt(f)
    assert r['sha256'] == f['hash'] and r['net'] == 4800.5 and 'Payroll' not in str(r) and 'Invoice' not in str(f)
