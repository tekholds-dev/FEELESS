import trench_theory as tt


def test_the_theory_reads_a_case_from_measured_laws():
    fresh = tt.verdict({'ageMin': 4, 'curve': 'bonding curve 40%', 'liq': 3000})
    assert set(fresh['breaks']) == {'fresh', 'curve', 'thin'} and fresh['score'] == -3 and 'BREAKS' in fresh['line']
    proven = tt.verdict({'ageMin': 300, 'status': 'graduated', 'cap': 22000, 'liq': 9000})
    assert proven['fits'] == ['proven'] and not proven['breaks'] and 'FITS the proven setup' in proven['line'] and '52 %' in proven['line']
    big = tt.verdict({'ageMin': 900, 'status': 'graduated', 'cap': 2e6, 'liq': 2e5})
    assert big['fits'] == [] and big['breaks'] == [] and 'no proven edge' in big['line']
    assert tt.verdict({'heldMin': 40})['fits'] == ['hold'] and tt.verdict({'heldMin': 6})['breaks'] == ['hold'] and tt.verdict({'heldMin': 20})['fits'] == []
    assert tt.verdict(None)['score'] == 0 and 'exits set first' in tt.verdict({})['line']
    assert len(tt.laws_text()) == len(tt.EVIDENCE)


def test_the_router_lets_the_theory_through():
    import ai_router
    assert 'theory' in ai_router.CASE_KEYS
