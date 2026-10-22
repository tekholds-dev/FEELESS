"""🛡 defence.py: honeypots block a fingerprint (escalating), a scanner tool seen from many IPs becomes a rule (never a browser string),
scrapers are tarpitted not blocked, a replayed HQ signature from somewhere new is flagged, everything expires and is capped. Never attacks back."""
import defence as d

T = 1_800_000_000.0
CHROME = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'


def test_a_honeypot_blocks_that_fingerprint_with_escalation_and_answers_like_a_404():
    s = d.new_state()
    assert d.check(s, '1.2.3.4', 'python-requests/2.31', 'GET', '/api/reputation/markets', T) is None
    assert d.check(s, '1.2.3.4', 'python-requests/2.31', 'GET', '/api/reputation/.env', T) == ('honeypot', None)
    assert d.check(s, '1.2.3.4', 'python-requests/2.31', 'GET', '/api/reputation/markets', T + 1)[0] == 'block'
    assert d.check(s, '1.2.3.4', 'python-requests/2.31', 'GET', '/api/reputation/markets', T + d.BLOCK_SEC + 2) is None   # it expires
    d.check(s, '1.2.3.4', 'python-requests/2.31', 'GET', '/api/reputation/wp-login.php', T + d.BLOCK_SEC + 3)
    fp = d.fingerprint('1.2.3.4', 'python-requests/2.31')
    assert s['blocks'][fp]['until'] - (T + d.BLOCK_SEC + 3) == 2 * d.BLOCK_SEC                                        # a repeat doubles it
    assert d.check(s, '9.9.9.9', CHROME, 'GET', '/api/reputation/markets', T) is None                                  # someone else is untouched


def test_a_tool_behind_many_ips_becomes_a_rule_but_a_browser_string_never_does():
    s = d.new_state()
    for i in range(d.SHARED_HITS):
        d.check(s, f'5.5.5.{i}', 'zgrab/0.x', 'GET', '/api/.git/config', T + i)
        d.check(s, f'6.6.6.{i}', CHROME, 'GET', '/api/.git/config', T + i)
    assert d.check(s, '7.7.7.7', 'zgrab/0.x', 'GET', '/api/reputation/markets', T + 10)[0] == 'block'               # learned: the tool, any IP
    assert d.check(s, '8.8.8.8', CHROME, 'GET', '/api/reputation/markets', T + 10) is None                            # real traders share Chrome
    assert len(s['rules']) == 1 and d.browserish(CHROME) and not d.browserish('curl/8.1') and not d.browserish('Mozilla/5.0 (compatible; Googlebot/2.1)')


def test_scrapers_are_tarpitted_not_blocked_and_replays_are_flagged():
    s = d.new_state()
    hits = [d.check(s, '3.3.3.3', 'curl/8', 'GET', f'/api/reputation/coin/{i}', T + i * 0.1) for i in range(d.SCRAPE_PER_MIN + 5)]
    assert hits[-1] == ('tarpit', d.TARPIT_S) and not any(h and h[0] == 'block' for h in hits)
    assert d.seen_sig(s, 'SIG', '4.4.4.4', CHROME, '/api/reputation/admin/x', T) is False
    assert d.seen_sig(s, 'SIG', '4.4.4.4', CHROME, '/api/reputation/admin/x', T + 5) is False                          # same place = fine
    assert d.seen_sig(s, 'SIG', '6.6.1.1', 'curl/8', '/api/reputation/admin/x', T + 9) is True                        # a stolen session
    assert d.check(s, '6.6.1.1', 'curl/8', 'GET', '/api/reputation/x', T + 10) == ('tarpit', d.TARPIT_S)
    assert {i['kind'] for i in s['incidents']} == {'scraper', 'replay'}


def test_internal_traffic_is_never_touched_reports_are_plain_and_memory_is_capped():
    s = d.new_state()
    assert d.check(s, '127.0.0.1', '', 'GET', '/api/reputation/.env', T, internal=True) is None
    for i in range(d.INCIDENTS_MAX + 50):
        d.check(s, f'2.{i // 250}.{i % 250}.1', f'tool/{i}', 'GET', '/api/.env', T + i)
    assert len(s['incidents']) == d.INCIDENTS_MAX
    rep = d.report(s['incidents'][-1])
    assert 'Abuse report' in rep and 'no counter-action' in rep and '/api/.env' in rep
    v = d.view(s, T + d.BLOCK_MAX + 10)
    assert v['blocks'] == [] and 'honeypots' in v


def test_the_service_answers_a_decoy_with_a_plain_404_then_blocks_that_fingerprint(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    monkeypatch.setenv('FEELESS_TRUST_PROXY', '1')
    monkeypatch.setattr(rs, '_def_state', d.new_state())
    c = TestClient(rs.app)
    h = {'x-forwarded-for': '1.1.1.9', 'user-agent': 'python-requests/2.31'}
    r = c.get('/api/reputation/.env', headers=h)
    assert r.status_code == 404 and r.json() == {'detail': 'Not Found'}
    assert c.get('/api/reputation/perf/config', headers=h).status_code == 403
    assert c.get('/api/reputation/perf/config', headers={'x-forwarded-for': '1.1.1.10', 'user-agent': 'python-requests/2.31'}).status_code != 403
    assert c.get('/api/reputation/admin/security/defence').status_code in (401, 403)   # the view is admin-only


def test_the_approvals_check_lists_only_token_accounts_with_a_delegate(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    W = 'So11111111111111111111111111111111111111112'

    async def fake_rpc(http, method, params, scan=True):
        if params[1]['programId'].startswith('Tokenkeg'):
            return {'value': [{'pubkey': 'ACC1', 'account': {'data': {'parsed': {'info': {'mint': 'MINT1', 'delegate': 'DRAINER', 'delegatedAmount': {'uiAmountString': '1000'}, 'tokenAmount': {'uiAmountString': '1000'}}}}}},
                              {'pubkey': 'ACC2', 'account': {'data': {'parsed': {'info': {'mint': 'MINT2', 'tokenAmount': {'uiAmountString': '5'}}}}}}]}
        return {'value': []}
    monkeypatch.setattr(rs, '_rpc', fake_rpc)
    rs._appr_hits.clear()
    r = TestClient(rs.app).get(f'/api/reputation/approvals/{W}')
    assert r.status_code == 200 and [a['account'] for a in r.json()['approvals']] == ['ACC1'] and r.json()['approvals'][0]['delegate'] == 'DRAINER'
    assert TestClient(rs.app).get('/api/reputation/approvals/not-an-address').status_code == 400
