"""⚡ FEELESS MCP: read-only tools, the protocol, the LAN / token wall, and web_fetch never reaching a private network."""
import inspect

import feeless_mcp as m


def test_every_tool_only_reads():
    for name, (fn, desc, _p) in m.TOOLS.items():
        assert not set(name.split('_')) & set(m.FORBIDDEN_WORDS), name   # whole words: 'trades' (what happened) is a read
        src = inspect.getsource(fn)
        assert '/admin' not in src and 'sign' not in src.replace('signal', '')
        assert '.post(' not in src or name == 'web_search'   # the only POST is DuckDuckGo's search form
    for t in m.tool_list():
        assert t['annotations']['readOnlyHint'] is True and t['annotations']['destructiveHint'] is False


def test_protocol_answers():
    r = m.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}})
    assert r['result']['capabilities'] == {'tools': {'listChanged': False}} and r['result']['serverInfo']['name'] == 'feeless'
    assert m.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) is None
    names = [t['name'] for t in m.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})['result']['tools']]
    assert 'web_search' in names and 'feeless_card' in names
    assert m.handle({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'nope'}})['error']['code'] == -32602
    bad = m.handle({'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'feeless_coin', 'arguments': {'mint': 'x'}}})
    assert 'mint address' in bad['result']['content'][0]['text']


def test_web_fetch_refuses_private_hosts_and_the_server_serves_the_lan_only(monkeypatch):
    for u in ('http://127.0.0.1:5077/api', 'http://localhost/', 'http://10.0.0.249:1236/v1', 'http://169.254.169.254/latest', 'file:///etc/passwd',
              'http://user:pw@example.com/'):
        assert m.safe_url(u), u
    monkeypatch.setattr(m.socket, 'getaddrinfo', lambda *a, **k: [(0, 0, 0, '', ('93.184.215.14', 0))])
    assert m.safe_url('https://example.com/x') is None
    monkeypatch.setattr(m.socket, 'getaddrinfo', lambda *a, **k: [(0, 0, 0, '', ('10.1.1.1', 0))])   # DNS pointing inside = refused
    assert m.safe_url('https://evil.example/x')
    assert m.client_ok('127.0.0.1') and m.client_ok('10.0.0.249') and m.client_ok('192.168.1.2') and not m.client_ok('8.8.8.8')


def test_search_parser_drops_ads_and_unwraps_links():
    raw = ('<a rel="nofollow" class="result__a" href="https://duckduckgo.com/y.js?ad=1">Ad</a>'
           '<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fpump.fun%2Fx&rut=1">Pump <b>x</b></a>'
           '<a class="result__snippet" href="#">a <b>bonding</b> curve</a>')
    assert m.ddg_results(raw) == [{'title': 'Pump x', 'url': 'https://pump.fun/x', 'snippet': 'a bonding curve'}]
