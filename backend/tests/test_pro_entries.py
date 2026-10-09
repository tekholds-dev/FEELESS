import pump_calls as pc

NOW = 10_000_000.0


def test_pro_entries_follow_proven_callers_at_their_price_only():
    callers = {'ace': {'proven': True, 'medMult': 2.0, 'wonPct': 80, 'n': 5}, 'meh': {'proven': False, 'medMult': 0.9, 'n': 9}}
    rows = [{'mint': 'A', 'pairAddress': 'pa', 'price': 1.0, 'mcap': 11_000, 'safe': True},
            {'mint': 'B', 'pairAddress': 'pb', 'price': 1.0, 'mcap': 30_000, 'safe': True},
            {'mint': 'C', 'pairAddress': 'pc', 'price': 1.0, 'mcap': 10_000, 'safe': False},
            {'mint': 'D', 'pairAddress': 'pd', 'price': 1.0, 'mcap': 10_000, 'safe': True}]
    m = 60_000
    calls = [{'user': 'ace', 'mint': 'A', 'at': NOW - 5 * m, 'atMc': 10_000},     # ✅ fresh, +10% since the call, safe
             {'user': 'ace', 'mint': 'B', 'at': NOW - 5 * m, 'atMc': 10_000},     # ✗ already 3× past the caller's price
             {'user': 'ace', 'mint': 'C', 'at': NOW - 5 * m, 'atMc': 10_000},     # ✗ failed the safety scan
             {'user': 'meh', 'mint': 'D', 'at': NOW - 1 * m, 'atMc': 10_000},     # ✗ caller not proven
             {'user': 'ace', 'mint': 'D', 'at': NOW - 40 * m, 'atMc': 10_000}]    # ✗ call too old
    out = pc.pro_entries(calls, callers, rows, NOW)
    assert [r['mint'] for r in out] == ['A']
    assert out[0]['proCall']['user'] == 'ace' and out[0]['proCall']['mins'] == 5.0 and out[0]['trenchScore'] == 220
    assert pc.pro_entries(calls, {}, rows, NOW) == []
