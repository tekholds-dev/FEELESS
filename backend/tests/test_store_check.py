"""📱 Store check: a built page read the way App Review / Google Play would see it wrapped as an app. Static rows are pure; the phone pass
needs Chromium and says 'skip' without it (never a fake pass)."""
import asyncio

import store_check as sc

GOOD = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Wick Breaker</title><link rel="apple-touch-icon" href="icon-512.png"><link rel="manifest" href="manifest.json"></head>'
        '<body><h1>Wick Breaker</h1><img src="a.png" alt="ball"><a href="https://x.org" target="_blank" rel="noopener">help</a></body></html>')


def by_id(rows):
    return {r['id']: r['state'] for r in rows}


def test_a_clean_game_page_is_ready_to_wrap():
    rows = sc.static_checks(GOOD)
    assert all(r['state'] == 'pass' for r in rows), [r for r in rows if r['state'] != 'pass']
    v = sc.verdict(rows)
    assert v == {'score': 100, 'state': 'ready', 'fails': 0, 'warns': 0, 'line': 'Ready to wrap and submit'}


def test_what_a_store_rejects_and_what_needs_a_decision():
    bad = ('<html><head><title>x</title><script src="http://cdn.evil/x.js"></script><script>eval("1")</script></head><body>'
           '<form><input type="email" name="email"><input type="password"></form><p>Sign up and create an account. Lorem ipsum.</p>'
           '<p>Place a bet with real money, connect wallet</p><img src="a.png"><a href="https://a" target="_blank">x</a></body></html>')
    s = by_id(sc.static_checks(bad))
    assert s['viewport'] == 'fail' and s['https'] == 'fail' and s['privacy'] == 'fail' and s['delete'] == 'fail' and s['complete'] == 'fail'
    assert s['gambling'] == 'warn' and s['crypto'] == 'warn' and s['code'] == 'warn' and s['a11y'] == 'warn' and s['links'] == 'warn' and s['icon'] == 'warn'
    v = sc.verdict(sc.static_checks(bad))
    assert v['state'] == 'blocked' and v['fails'] == 5 and 'reject' in v['line']


def test_no_browser_means_skip_not_pass():
    rows = asyncio.run(sc.device_checks(GOOD, chromium=''))
    assert [r['state'] for r in rows] == ['skip']
    res = asyncio.run(sc.check(GOOD, device=False))
    assert res['state'] == 'ready' and res['rows'][0]['state'] == 'pass'
    assert sc.verdict(rows + sc.static_checks(GOOD))['score'] == 100   # a skipped row never counts for or against
