import candles_service as cs


def test_a_lone_bad_print_wick_is_cut_back_but_normal_wicks_stay():
    rows = [[i * 60, 100, 103, 97, 101, 1] for i in range(12)]
    rows[6] = [360, 100, 103, 34, 101, 1]          # one print at a third of the price
    out = cs._clip_wicks(rows)
    assert out[6][3] > 90                           # cut back near the body
    assert out[3][3] == 97 and out[3][2] == 103     # ordinary wicks untouched


def test_a_market_that_wicks_hard_everywhere_keeps_its_wicks():
    rows = [[i * 60, 100, 140, 70, 101, 1] for i in range(12)]
    assert cs._clip_wicks(rows)[6][3] == 70
