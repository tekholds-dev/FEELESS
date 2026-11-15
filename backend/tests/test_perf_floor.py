import perf


def test_pages_report_the_25_fps_floor_and_steps():
    s = [{'page': '/terminal', 'fps': 20, 'fx': {'level': 1}}, {'page': '/terminal', 'fps': 50, 'fx': {'level': 0}}, {'page': '/terminal', 'fps': 24}]
    row = next(p for p in perf.summarize(s)['pages'] if p['page'] == '/terminal')
    assert row['fpsLow'] == 20 and row['underFloor'] == 2 and row['stepped'] == 1 and row['fps'] == 31
