import importlib


def test_majors_and_stocks_are_always_recorded():
    cs = importlib.import_module('candles_service')
    rows = [[{'pairAddress': 'P1', 'baseAddress': 'SOLMINT'}, {'pairAddress': 'P2', 'mint': 'BTC'}, {'pairAddress': None, 'baseAddress': 'X'}], [{'pairAddress': 'P3', 'baseAddress': 'NVDAx'}], None]
    assert cs.always_pairs(rows) == {'P1': 'SOLMINT', 'P2': 'BTC', 'P3': 'NVDAx'} and cs.always_pairs(None) == {}
    assert cs.ALWAYS_REFRESH >= 300
