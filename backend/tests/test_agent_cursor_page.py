"""🖱 AGT-19: the agent's cursor lands on the right spot on page-only screenshots, not just in the live view (which shows the window chrome).
Reproduced 2026-11-10 with headed Chrome: inner 1280x720, window 1282x800 → the window share drew the cursor ~72 px low at the top of a screenshot."""
import cat_browser
import feecat_service


def test_page_shares_ignore_the_toolbar():
    win = [1280, 720, 1282, 800]   # measured: headed Chrome, 80 px of toolbar
    p = cat_browser._page_xy(640, 20, win)
    assert p == {'px': 0.5, 'py': round(20 / 720, 4)}
    window_y = (win[3] - win[1] + 20) / win[3]
    assert abs(window_y * win[1] - 20) > 60          # the old share was ~70 px off on a 720 px screenshot
    assert abs(p['py'] * win[1] - 20) < 1             # the page share is exact
    assert cat_browser._page_xy(1, 1, [0, 0, 0, 0]) == {}


def test_public_cursor_keeps_page_shares_and_clamps():
    c = feecat_service._pub_cursor({'x': 0.5, 'y': 0.9, 'px': 0.5, 'py': 1.4, 'act': 'click', 'at': 1, 'typed': 'secret'})
    assert c == {'x': 0.5, 'y': 0.9, 'px': 0.5, 'py': 1, 'act': 'click', 'at': 1}
    assert feecat_service._pub_cursor({'x': 0.2, 'y': 0.3}) == {'x': 0.2, 'y': 0.3, 'act': 'move', 'at': None}   # old cursors still pass
    assert feecat_service._pub_cursor(None) is None
