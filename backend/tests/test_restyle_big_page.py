"""🎨 Owner 2026-11-16: "upgrade this look, make it look alive" on a 26K PoStatic failed twice ("Its changes did not match the page", $0.21 spent).
A look on a page too big to write whole is now one CSS block that wins; a patch the model retyped a little still lands. Models faked."""
import asyncio

import agent_features as af
from test_play_studio import _server

BIG = ('<!doctype html><html><head><style>.hero{color:#111}.card{padding:4px}</style></head><body>'
       + '<section class="hero"><h1 class="t">GONE</h1></section>' + ''.join(f'<div class="card" id="c{i}">tomb {i} {"x" * 300}</div>' for i in range(90))
       + '<script>var n=1;</script></body></html>')


def test_look_words_are_a_restyle_and_a_fix_is_not():
    assert af.wants_restyle('upgrade this look, make it look alive, i like the narrative.')
    assert af.wants_restyle('new colors and a glow') and af.wants_restyle('animate the cards')
    assert not af.wants_restyle('the buy button does nothing') and not af.wants_restyle('add a FAQ section')


def test_a_retyped_find_still_lands_once_and_an_ambiguous_one_never_does():
    page = '<!doctype html><html><head></head><body><div class="a"><b class="x">One</b>   <i>two</i></div></body></html>'
    raw = '{"edits":[{"find":"<b class=\'x\'>One</b> <i>two</i>","replace":"<b class=\\"x\\">Won</b>"}]}'   # quotes and spaces retyped
    out, n, _ = af.apply_page_edits(page, raw)
    assert n == 1 and '<div class="a"><b class="x">Won</b></div>' in out
    twice = '<!doctype html><html><body><p class="z">same text here</p><p class="z">same text here</p></body></html>'
    assert af.apply_page_edits(twice, '{"edits":[{"find":"<p class=\'z\'>same text here</p>","replace":"y"}]}')[0] is None
    assert af._loose_find('abc', 'ab') is None   # too short to trust a loose match


def _run(monkeypatch, tmp_path, ask, replies):
    fs, c, store = _server(monkeypatch, tmp_path)
    cat = store['cats']['g']; cat['brainsCfg']['brains'] = ['m/x']
    row = fs._feat.new_folder(cat, 'build', 'trench build', 1.0)
    doc = fs._feat.new_doc(row); fs._feat.add_version(doc, BIG, 'Mind A', 1.0); doc['plan'] = {'approved': True}
    doc['busy'] = {'at': 1000, 'to': 'a', 'stage': 'build'}; fs._ws_save('g', doc)
    asked = []
    async def fake(cat_, model, sys_, user_, tokens):
        asked.append(sys_)
        return replies.pop(0) if replies else '', 0.01, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    asyncio.run(fs._ws_run('g', row['id'], 'a', ask, None))
    return fs._ws_load('g', row['id']), asked


def test_a_new_look_on_a_big_page_lands_as_one_css_block(monkeypatch, tmp_path):
    assert not af.wants_rewrite(BIG, 'upgrade this look')   # too big to write whole: this was the edit path that failed
    css = '.hero{background:linear-gradient(#0b0f14,#10241a)} .card{animation:rise .5s ease both} @keyframes rise{from{opacity:0;transform:translateY(8px)}}'
    done, asked = _run(monkeypatch, tmp_path, 'upgrade this look, make it look alive', [css])
    assert len(asked) == 1 and asked[0].count('You restyle one existing HTML page') == 1   # one paid call, the restyle one
    page = done['versions'][-1]['html']
    assert len(done['versions']) == 2 and '@keyframes rise' in page and page.index('@keyframes rise') > page.index('.hero{color:#111}')   # after the old CSS, so it wins
    assert 'GONE' in page and 'var n=1;' in page and done['messages'][-1]['text'].startswith('Page 2 is ready')


def test_a_restyle_that_returns_nothing_falls_back_to_edits_and_says_what_to_do(monkeypatch, tmp_path):
    done, asked = _run(monkeypatch, tmp_path, 'make it look alive', ['no css here', '{"edits":[{"find":"not on the page at all","replace":"x"}]}'])
    assert len(done['versions']) == 1 and 'say "rebuild"' in done['messages'][-1]['text'] and 'the last page is safe' in done['messages'][-1]['text']
