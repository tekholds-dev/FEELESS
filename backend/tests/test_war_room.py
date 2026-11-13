import war_room as w


def test_feed_and_hourly():
    s = w.new_state()
    t = 1_000_000.0
    w.log(s, 'probe', '1.2.3.4', 'curl/8', '/.env', 'GET', 'seen', now=t)
    w.log(s, 'block', '1.2.3.4', 'curl/8', '/.env', 'GET', 'blocked', now=t + 10)
    assert s['seq'] == 2
    assert len(w.since(s, 1)) == 1
    rows = w.hourly(s, now=t + 20, hours=2)
    assert sum(r.get('probe', 0) + r.get('block', 0) for r in rows) == 2


def test_capture_filters_headers_and_truncates_body():
    s = w.new_state()
    cap = w.capture(s, '9.9.9.9', 'py', 'POST', '/admin/export-keys', query='x=1',
                    headers={'User-Agent': 'py', 'X-Secret-Internal': 'nope', 'Referer': 'http://evil'}, body='A' * 9000)
    assert 'x-secret-internal' not in cap['headers']
    assert cap['headers']['referer'] == 'http://evil'
    assert len(cap['body']) == w.BODY_MAX
    assert w.view(s)['captures'][0]['bodyLen'] == w.BODY_MAX


def test_canary_open_and_key_use():
    s = w.new_state()
    tok, url, key = w.mint_canary(s, origin='env-decoy')
    assert url.endswith(tok) and key.startswith('sk_live_')
    assert w.canary_open(s, 'unknown', '1.1.1.1', 'x') is None
    hit = w.canary_open(s, tok, '5.6.7.8', 'Mozilla', headers={'Referer': 'http://x', 'Accept-Language': 'ru'})
    assert hit['ip'] == '5.6.7.8' and hit['lang'] == 'ru'
    assert s['canaries'][tok]['opens'] == 1
    c = w.canary_key_hit(s, f'Bearer {key}', '5.6.7.8', 'ua', '/api/x')
    assert c and c['keyUses'] == 1
    assert w.canary_key_hit(s, 'sk_live_notours', '5.6.7.8', 'ua') is None


def test_subnet_ban_after_three_fingerprints():
    s = w.new_state()
    t = 2_000_000.0
    assert w.note_net(s, '8.8.8.1', 'fpA', now=t) is None
    assert w.note_net(s, '8.8.8.2', 'fpB', now=t + 1) is None
    m = w.note_net(s, '8.8.8.9', 'fpC', now=t + 2)
    assert m and m['kind'] == 'ban-net'
    assert w.net_banned(s, '8.8.8.77', now=t + 3) is True
    assert w.net_banned(s, '9.9.9.9', now=t + 3) is False
    # expires
    assert w.net_banned(s, '8.8.8.77', now=t + w.NET_BAN + 10) is False


def test_session_revoke_on_second_device():
    s = w.new_state()
    t = 3_000_000.0
    assert w.note_sig(s, 'SIG1', '1.1.1.1', 'Chrome on Mac', now=t) is None
    assert w.note_sig(s, 'SIG1', '1.1.1.1', 'Chrome on Mac', now=t + 5) is None   # same device = fine
    m = w.note_sig(s, 'SIG1', '2.2.2.2', 'python-requests', now=t + 10)
    assert m and m['kind'] == 'revoke-session'
    assert w.sig_revoked(s, 'SIG1', now=t + 11) is True
    assert w.sig_revoked(s, 'OTHER', now=t + 11) is False


def test_trace_summary_and_evidence_pack():
    s = w.new_state()
    transfers = [
        {'sig': 'a', 'from': 'SUS', 'to': 'EXCH', 'amount': 1.5, 'token': 'SOL'},
        {'sig': 'b', 'from': 'SUS', 'to': 'EXCH', 'amount': 2.0, 'token': 'SOL'},
        {'sig': 'c', 'from': 'SUS', 'to': 'MIX', 'amount': 0.3, 'token': 'USDC'},
        {'sig': 'd', 'from': 'OTHER', 'to': 'SUS', 'amount': 9.0},
    ]
    tr = w.trace_summary(transfers, 'SUS')
    assert tr['outCount'] == 3 and tr['counterparties'] == 2
    assert tr['hops'][0]['to'] == 'EXCH' and tr['hops'][0]['amount'] == 3.5
    w.capture(s, '9.9.9.9', 'py', 'GET', '/.env')
    pack = w.evidence_pack(s, 'SUS', tr, now=4_000_000.0)
    assert 'evidence pack' in pack and 'SUS' in pack and 'EXCH' in pack
    assert 'No counter-action' in pack


def test_decoy_page_plants_canary():
    _, env = w.decoy_page('env', '/api/reputation/c/abc', 'sk_live_xyz')
    assert 'sk_live_xyz' in env and '/api/reputation/c/abc' in env
    ct, html = w.decoy_page('panel', '/api/reputation/c/abc', 'sk_live_xyz')
    assert ct == 'text/html' and 'abc' in html
    assert w.page_kind('/API/.env/') == 'env'
    assert w.page_kind('/admin/export-keys') == 'keys'
    assert w.page_kind('/totally/normal') is None


def test_reports_capped_and_sanitised():
    s = w.new_state()
    r = w.add_report(s, wallet='W' * 200, url='http://x', detail='D' * 5000)
    assert len(r['wallet']) == 64 and len(r['detail']) == 2000
    assert w.view(s)['counts']['reports'] == 1
