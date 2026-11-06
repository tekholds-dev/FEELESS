"""The trench theory's shadow test reads bands the way verdict needs them, and only ever reports."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('theory_shadow', Path(__file__).resolve().parents[2] / 'scripts' / 'theory-shadow.py')
ts = importlib.util.module_from_spec(spec); spec.loader.exec_module(ts)


def test_bands_become_a_case():
    c = ts.case_of(['age:<15m', 'cap:<30K', 'stage:graduated'])
    assert c['ageMin'] == 5 and c['cap'] < 30000 and c['status'] == 'graduated'
    assert ts.case_of(['cap:100-300K'])['cap'] > 30000 and ts.case_of(['cap:1M+'])['cap'] >= 1e6 and ts.case_of(['nonsense']) == {}


def test_a_vanished_coin_is_a_total_loss_and_an_unsettled_one_is_left_out():
    assert ts.outcome({'gone': True}) == -100 and ts.outcome({'end': 10}) == 10 - ts.COST_PCT and ts.outcome({}) is None


def test_it_groups_the_newest_coins_by_score():
    coins = [{'at': i, 'end': 50, 'f': ['age:12h+', 'stage:graduated', 'cap:<30K']} for i in range(6)] + [{'at': 10 + i, 'end': -50, 'f': ['age:<15m', 'stage:curve']} for i in range(4)]
    rows = {r['score']: r for r in ts.shadow(coins)}
    assert rows[-2]['n'] == 4 and rows[-2]['upPct'] == 0 and 1 not in rows   # only the newest 40% were scored
