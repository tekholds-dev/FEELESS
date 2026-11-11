import cat_policy as cp


def test_a_minds_private_thinking_is_never_an_answer():
    leak = 'hy4: I need to follow the standing orders and the task structure. Let me think about what\'s required: - First turn must include "plan"'
    assert cp.thinking_leak(leak) and cp.thinking_leak(leak.split(': ', 1)[1])
    assert cp.thinking_leak('<think>hmm</think> let me check the odds first')
    for fine in ('I need your login for this site to keep going.', 'Dallas Cowboys: 27 - 23 · 0:40 - 4th. From your PoB on Cowboys vs Colts.',
                 'Let me know if you want the 3-leg parlay.', 'BUY $WIF — volume doubled in 5 minutes'):
        assert not cp.thinking_leak(fine), fine
    rows = [{'text': leak}, {'text': 'KEEP the Colts line'}, 'hy4: Okay, so let me think. Wait, actually the standing orders say']
    assert cp.no_thinking(rows) == [{'text': 'KEEP the Colts line'}]
