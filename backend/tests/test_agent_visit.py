"""Owner 2026-11-06: agents browse FEELESS safely, before and after deploy. Read-only, public numbers, no way to act."""
import asyncio

import agent_knows as ak
import agent_visit as av
import cat_agent as ca

WALLET = 'ANwSewb5AaKv4DarsDQ4NSEQ9APNtTGVxygPzn9u5K8P'


class Http:
    def __init__(self, rows=None, down=False):
        self.rows = rows or {}; self.down = down; self.asked = []

    async def get(self, url, timeout=None):
        self.asked.append(url)
        if self.down:
            raise OSError('down')
        body = next((v for k, v in self.rows.items() if k in url), {})

        class R:
            status_code = 200

            @staticmethod
            def json():
                return body
        return R()


def page(url, **k):
    return asyncio.run(av.render(Http(**k), url))


def test_only_its_own_name_counts():
    assert av.is_visit('https://visit.feeless/') and av.is_visit('http://visit.feeless/proofs?x=1') and av.is_visit('https://visit.feeless')
    for u in ('https://visit.feeless.evil.com/', 'https://evil.com/visit.feeless/', 'https://xvisit.feeless/', 'file:///etc/passwd'):
        assert not av.is_visit(u), u


def test_every_page_opens_even_with_every_service_down():
    for p in ('/', '/collective', '/proofs', '/agents', '/markets', '/whitepaper', '/whitepaper/1'):
        status, body = page('https://visit.feeless' + p, down=True)
        assert status == 200 and 'read-only' in body and '<nav>' in body, p


def test_nothing_else_is_served_and_nothing_can_act():
    for p in ('/admin', '/api/cats/leader/work', '/../etc/passwd', '/whitepaper/999', '/whitepaper/x'):
        assert page('https://visit.feeless' + p)[0] == 404, p
    status, body = page('https://visit.feeless/collective')
    assert "default-src 'none'" in body and '<form' not in body and '<script' not in body and '<input' not in body


def test_only_public_reads_on_our_own_services():
    h = Http(); [asyncio.run(av.render(h, 'https://visit.feeless' + p)) for p in ('/', '/collective', '/proofs', '/agents', '/markets')]
    assert h.asked and all(u.startswith(('http://127.0.0.1:5088/api/cats/', 'http://127.0.0.1:5001/api/market/')) for u in h.asked) and not any('work' in u or 'admin' in u or 'internal' in u for u in h.asked)


def test_a_wallet_or_an_email_never_shows_and_data_cannot_inject():
    rows = {'leaderboard': {'rows': [{'name': f'<script>x</script> {WALLET} a@b.co', 'trades': 3, 'winRate': 50, 'realizedPnlSol': 0.1}]}}
    status, body = page('https://visit.feeless/agents', rows=rows)
    assert WALLET not in body and 'a@b.co' not in body and '<script>x' not in body and 'a wallet' in body


def test_the_collective_page_shows_the_real_rule():
    body = page('https://visit.feeless/collective')[1]
    assert '200x' in body and '$400' in body and 'ceiling' in body


def test_research_tasks_may_visit_and_the_brief_sends_them_there():
    assert ca._on_list({}, 'https://visit.feeless/proofs')
    assert 'https://visit.feeless/' in ak.brief() and 'Never invent' in ak.brief()
