"""🚀 Go live: hosts ranked cheapest first, each row kept 'checked' only while its pricing page still says it (no network)."""
import asyncio

import deploy_hosts as d


def _rows(**over):
    return [{**h, 'state': over.get(h['id'], 'checked'), 'checkedAt': 0} for h in d.HOSTS]


def test_unmetered_free_hosts_lead_and_visits_follow_page_size():
    r = d.rank(_rows(), page_mb=0.5)
    assert [h['id'] for h in r[:2]] == ['cloudflare', 'surge']
    gh = next(h for h in r if h['id'] == 'github')
    assert gh['visits'] == 204800 and r[0]['visits'] is None


def test_a_page_over_a_hosts_cap_sinks_and_a_changed_page_drops_below_checked():
    big = d.rank(_rows(), page_mb=30)
    assert big[-1]['id'] == 'cloudflare' and big[-1]['fits'] is False
    ch = d.rank(_rows(surge='changed'))
    assert [h['id'] for h in ch].index('surge') > [h['id'] for h in ch].index('render')


def test_the_check_reads_the_hosts_own_sentence(monkeypatch):
    class R:
        def __init__(self, t): self.status_code, self.text = 200, t
    class C:
        async def get(self, url): return R('<p>Requests to static assets are <b>free and unlimited</b>.</p>' if 'cloudflare' in url else '<p>new prices</p>')
    monkeypatch.setattr(d, '_client', C()); d._seen.clear()
    out = asyncio.run(d.hosts(mb=0.1))
    st = {h['id']: h['state'] for h in out['hosts']}
    assert st['cloudflare'] == 'checked' and st['vercel'] == 'changed'
    assert all('proof' not in h for h in out['hosts'])
