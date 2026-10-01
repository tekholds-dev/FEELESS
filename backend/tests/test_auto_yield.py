"""Auto-collect: fires once at +X% of the held base, sells only the gain, re-arms from the new base after collecting."""
import pytest

import fuse_hq as hq


def test_fires_at_trigger_and_sells_only_the_gain():
    y = {'at': 50, 'base': 100.0}
    assert not hq.yield_due({'valueUsd': 149, 'realizedUsd': 0}, y)
    r = {'valueUsd': 150, 'realizedUsd': 0}
    assert hq.yield_due(r, y) and hq.collect_pct(r, y) == 33.3          # sell 50 of 150 → base 100 stays in
    assert not hq.yield_due(r, {**y, 'firedAt': 1})                     # once per arming
    assert not hq.yield_due(r, {**y, 'rebase': True})                   # waiting to re-arm after a collect


def test_held_value_excludes_what_was_taken_out():
    assert hq.held_value({'valueUsd': 180, 'realizedUsd': 50}) == 130
    assert not hq.yield_due({'valueUsd': 180, 'realizedUsd': 50}, {'at': 50, 'base': 100})   # 130 held < 150


def test_trigger_bounds():
    assert hq.clean_yield_at(50) == 50 and hq.YIELD_DEFAULT_AT == 50
    with pytest.raises(ValueError):
        hq.clean_yield_at(5)
