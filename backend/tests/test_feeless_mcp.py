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


def test_levers_name_real_controls_with_their_direction():
    o = {'capital': {'record': {'n': 30, 'wonPct': 63, 'avgWin': 6.6, 'avgLoss': -34.2, 'expPct': -8.3},
                     'leaks': [{'rule': 'R5x catastrophic stop', 'n': 3, 'avgPct': -76.3}]},
         'policy': {'controls': [{'key': 'agentMinAgeH', 'value': 0.5, 'who': 'CREATOR OVERRIDE', 'options': [0, 0.5, 1, 2]},
                                 {'key': 'agentPoolMin', 'value': 0, 'who': 'AGENTS CHOOSE', 'options': [0, 5000, 12000]},
                                 {'key': 'agentMcMin', 'value': 20000, 'who': 'CREATOR OVERRIDE', 'options': [12000, 20000, 30000]}]},
         'regret': {'record': {'taken': {'n': 50, 'med': -50}, 'ai:CAUTION': {'n': 20, 'med': 40}, 'gate:gap': {'n': 30, 'med': -80}}}}
    L = m.levers(o)
    assert any('Break-even needs 84% won' in x for x in L)
    leak = next(x for x in L if x.startswith('BIGGEST LEAK'))
    assert 'RAISE' in leak and 'agentMinAgeH now 0.5' in leak and "options [12000, 20000, 30000]" in leak
    assert any('ai:CAUTION' in x and 'blocking WINNERS' in x for x in L) and any('gate:gap' in x and 'SAVING' in x for x in L)


def test_the_desktop_installer_writes_the_preset_and_merges_only_its_own_mcp_entry():
    import feeless_mcp as m
    s = m.install_script('http://10.0.0.104:8765/mcp', 'tok123', preset_json='{"name": "X {braces}"}')
    assert s.startswith('#!/bin/bash') and '{"name": "X {braces}"}' in s
    assert 'cur.mcpServers.feeless = {"url": "http://10.0.0.104:8765/mcp", "headers": {"Authorization": "Bearer tok123"}}' in s
    assert "environment.objectForKey('HOME')" in s and 'cur.mcpServers = cur.mcpServers || {}' in s   # other servers stay; $HOME respected
