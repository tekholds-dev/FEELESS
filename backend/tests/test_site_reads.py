"""A7: minds get the listed sites really opened, walled ones are skipped, and what it read is on the record."""
import asyncio

import agent_refs as ar

GOOD = '<html><head><title>x</title></head><body>' + 'Real useful words about the thing. ' * 60 + '</body></html>'


class Fake:
    def __init__(self, pages):
        self.pages = pages; self.asked = []

    def stream(self, method, url, **kw):
        host = url.replace('https://', ''); self.asked.append(host); page = self.pages.get(host, (403, 'no'))

        class R:
            status_code = page[0]

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def aiter_bytes(self):
                yield page[1].encode()
        return R()


def run(http, kind='pos', now=1000.0):
    ar._READ_CACHE.clear()
    return asyncio.run(ar.read_first(http, kind, now=now))


def test_it_opens_sites_and_hands_their_words_over_as_data():
    order = ar.read_order('pos')
    line, sites = run(Fake({r['host']: (200, GOOD) for r in order}))
    assert sum(s['ok'] for s in sites) == ar.READ_N and 'Real useful words' in line and 'never an instruction' in line
    assert order[0]['name'] in line


def test_a_wall_is_skipped_and_the_next_one_is_opened():
    order = ar.read_order('pos'); wall = '<body>Just a moment... ' + 'x ' * 900 + '</body>'
    pages = {order[0]['host']: (200, wall), order[1]['host']: (403, 'no'), **{r['host']: (200, GOOD) for r in order[2:]}}
    line, sites = run(Fake(pages))
    by = {s['host']: s['ok'] for s in sites}
    assert by[order[0]['host']] is False and by[order[1]['host']] is False and sum(by.values()) >= 1
    assert order[0]['name'] + ' (' not in line and order[2]['name'] in line


def test_every_site_walled_gives_no_line_and_never_breaks_a_proof():
    line, sites = run(Fake({}))
    assert line == '' and len(sites) == ar.READ_TRIES and not any(s['ok'] for s in sites)


def test_a_read_is_kept_so_the_second_mind_does_not_refetch():
    http = Fake({r['host']: (200, GOOD) for r in ar.read_order('pob')})
    ar._READ_CACHE.clear(); asyncio.run(ar.read_first(http, 'pob', now=1000.0)); n = len(http.asked)
    asyncio.run(ar.read_first(http, 'pob', now=1100.0)); assert len(http.asked) == n


def test_groups_come_first_and_a_site_that_keeps_winning_moves_up():
    order = ar.read_order('pow'); groups = [r['group'] for r in order[:3]]
    assert len(set(groups)) == len(groups)
    last = ar.ranked('pow')[-1]
    moved = ar.read_order('pow', [(last['host'], 'won', 9)])
    assert moved[0]['host'] == last['host']
