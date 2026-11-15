"""👁 COMP watch: the live board prices every held coin from DexScreener's answer, never guesses a missing one, calls a gone pool lost,
and the minds' per-minute bins add up to the calls in the window."""
import comp_watch as cw


def _pair(addr, price, liq=50000):
    return {'pairAddress': addr, 'priceUsd': str(price), 'liquidity': {'usd': liq}, 'baseToken': {'address': 'm' + addr, 'symbol': 'X'}}


def _snap(addr, price, at):
    return {'pair': addr, 'mint': 'm' + addr, 'symbol': addr.upper(), 'dex': 'pumpswap', 'price': price, 'liq': 1, 'at': at}


def test_board_moves_calls_and_unknowns():
    now = 10_000
    snaps = [_snap('a', 1.0, now - 600), _snap('b', 1.0, now - 300), _snap('c', 1.0, now - 100), _snap('d', 1.0, now - 50)]
    pairs = {'a': _pair('a', 1.5), 'b': _pair('b', 0.7), 'c': None}   # d: DexScreener never answered
    b = {r['pair']: r for r in cw.board(snaps, pairs, now)}
    assert b['a']['move'] == 50.0 and b['a']['call'] == 'won' and b['a']['left'] == 3600 - 600
    assert b['b']['move'] == -30.0 and b['b']['call'] == 'lost'
    assert b['c']['gone'] and b['c']['call'] == 'lost' and b['c']['price'] is None
    assert b['d']['price'] is None and b['d']['move'] is None and b['d']['call'] is None and not b['d']['gone']
    assert [r['pair'] for r in cw.board(snaps, pairs, now)][0] == 'd'   # newest first


def test_minds_bins_and_tape():
    now = 100_000
    calls = [{'at': now - 30, 'ok': True, 'ms': 1000, 'model': 'g4'}, {'at': now - 90, 'ok': False, 'ms': 3000, 'model': 'g4'},
             {'at': now - 5000, 'ok': True, 'ms': 10, 'model': 'old'}]
    m = cw.minds(calls, now)
    assert m['calls'] == 2 and m['fail'] == 1
    assert sum(b['ok'] + b['fail'] for b in m['perMin']) == 2 and len(m['perMin']) == cw.WINDOW_MIN
    assert m['tape'][0]['at'] == now - 30 and len(m['tape']) == 3
    assert m['models'][0] == {'model': 'g4', 'calls': 2, 'fail': 1, 'ms': 2000, 'local': False}


def test_view_lean_and_totals():
    now = 5000
    v = cw.view([_snap('a', 1.0, now - 10)], {'a': _pair('a', 1.3)}, [], [{'title': 't', 'outcome': 'won', 'at': 1, 'plan': 'p'}], {'won': 3, 'lost': 4}, now)
    assert v['lean'] == {'won': 1, 'lost': 0, 'flat': 0} and v['totals']['won'] == 3 and v['settled'][0]['outcome'] == 'won'


def test_quiet_hour_falls_back_to_the_day():
    now = 200_000
    m = cw.minds([{'at': now - 7200, 'ok': True, 'ms': 5, 'model': 'x'}], now)
    assert m['unit'] == 'hour' and len(m['perMin']) == 24 and m['calls'] == 1 and m['perMin'][-2]['ok'] == 1
