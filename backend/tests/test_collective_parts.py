"""COL-26: proven page blocks become parts, offered to the next build, reuse logged (never paid), stale parts stop being offered."""
import collective_parts as cp

PAGE = ('<html><body><header class="top"><h1>GONE</h1><p>' + 'x' * 80 + '</p></header><main>'
        '<section id="roadmap"><h2>Roadmap</h2><p>' + 'phase one phase two ' * 6 + '</p></section>'
        '<section id="tokenomics"><h2>Tokenomics</h2><p>' + 'supply burn locked liquidity ' * 5 + '</p></section></main>'
        '<footer><p>' + 'made by the collective ' * 5 + '</p></footer></body></html>')
CAT = {'three': {'license': 'MIT'}, 'gpl-kit': {'license': 'GPL-3.0'}}
PROVED = {'kind': 'pos', 'id': 'ps1', 'ws': 'w1', 'state': 'proved'}


def test_a_proved_page_gives_its_blocks_once(tmp_path):
    p = tmp_path / 'parts.db'
    got = cp.harvest(p, 'c1', PROVED, PAGE, ['three'], CAT, now=100)
    rows = cp.family(p, now=100)
    assert len(got['kept']) == 4 and {r['tag'] for r in rows} == {'header', 'section', 'footer'}   # the main split into its two sections
    assert {r['title'] for r in rows} >= {'GONE', 'Roadmap', 'Tokenomics'} and all(r['licenses'] == ['MIT'] for r in rows)
    assert cp.harvest(p, 'c1', PROVED, PAGE, ['three'], CAT, now=200)['kept'] == []   # once only


def test_only_proved_licensed_clean_code_is_kept(tmp_path):
    p = tmp_path / 'parts.db'
    assert cp.harvest(p, 'c1', {**PROVED, 'state': 'waiting'}, PAGE, [], CAT)['kept'] == []
    assert 'GPL' in cp.harvest(p, 'c1', PROVED, PAGE, ['gpl-kit'], CAT)['skipped'][0][1]
    bad = '<section><h2>Bad</h2><script src="https://evil.example/x.js"></script><p>' + 'y' * 90 + '</p></section><section><h2>Eval</h2><script>eval("1")</script><p>' + 'z' * 90 + '</p></section>'
    r = cp.harvest(p, 'c1', PROVED, bad, [], CAT)
    assert r['kept'] == [] and [w for _, w in r['skipped']] == ['loads a script from evil.example', 'uses eval']
    assert cp.check('<script src="https://cdn.jsdelivr.net/npm/three"></script>') == ''


def test_offer_reuse_and_staleness(tmp_path):
    p = tmp_path / 'parts.db'; cp.harvest(p, 'c1', PROVED, PAGE, ['three'], CAT, now=100)
    off = cp.offer(p, 'a coin page with tokenomics and a roadmap', now=200)
    assert {o['title'] for o in off[:2]} == {'Tokenomics', 'Roadmap'} and 'data-part="pt_' in cp.offer_line(off)
    page = f'<section data-part="{off[0]["id"]}">reused</section>'
    assert cp.reused_in(page) == [off[0]['id']]
    assert cp.use(p, cp.reused_in(page), 'pos', 'w2', 'c2', now=300) == [off[0]['id']] and cp.use(p, [off[0]['id']], 'pos', 'w2', 'c2', now=301) == []   # once per proof
    fam = {r['id']: r for r in cp.family(p, now=300)}
    assert fam[off[0]['id']]['uses'] == 1 and fam[off[0]['id']]['reusedBy'] == [{'kind': 'pos', 'ref': 'w2', 'at': 300}]
    later = 300 + cp.STALE_S + 10
    assert [o['id'] for o in cp.offer(p, 'tokenomics roadmap', now=later)] == []   # nobody reused it in 30 days: not offered (a muscle not worked weakens)
    assert all(r['stale'] for r in cp.family(p, now=later))
    assert cp.offer(p, '', now=200) == []
