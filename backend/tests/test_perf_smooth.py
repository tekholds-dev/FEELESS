import perf


def test_pages_report_how_often_they_ran_rough_and_stepped_down():
    s = [{'page': '/terminal', 'fps': 20, 'fx': {'level': 1}}, {'page': '/terminal', 'fps': 50, 'fx': {'level': 0}}, {'page': '/terminal', 'fps': 38}]
    row = next(p for p in perf.summarize(s)['pages'] if p['page'] == '/terminal')
    assert row['fpsLow'] == 20 and row['underSmooth'] == 2 and row['stepped'] == 1 and row['fps'] == 36
