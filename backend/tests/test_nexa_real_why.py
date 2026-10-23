"""🧽 2026-10-23: NEXA's small model echoed the prompt's placeholder ("under 12 words, numbers") into every FeeCat receipt — dropped now."""
import nexa


def test_placeholder_echo_is_dropped_real_reasons_pass():
    for echo in ('under 12 words, numbers', '<the numbers that decided it, max 12 words>', 'numbers', ''):
        assert nexa.real_why(echo) == ''
    assert nexa.real_why('  N2 buyers 3x sellers,  pool $40K ') == 'N2 buyers 3x sellers, pool $40K'
    assert nexa.parse_fast('{"favor":["N1"],"why":"under 12 words, numbers"}', {'N1': 'P1'})['why'] == ''
