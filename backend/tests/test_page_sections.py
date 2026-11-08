"""🧩 A page too big for one reply is built in sections: a shell, then a section per call, put together into one finished page."""
import asyncio

import agent_features as af
import feecat_service as fs

SHELL = ('<!doctype html><html><head><style>.card{padding:8px}</style></head><body><main>'
         '<section data-part="1" data-brief="hero with the vault balance"></section>'
         '<section data-part="2" data-brief="deposits table"></section>'
         '<section data-part="3" data-brief="withdraw form"></section></main><script>const x=1</script></body></html>')


def test_shell_parts_and_assemble():
    assert af.shell_parts(SHELL) == [('1', 'hero with the vault balance'), ('2', 'deposits table'), ('3', 'withdraw form')]
    page = af.assemble(SHELL, {'1': '<h1>Vault</h1>', '2': '<table></table>'})
    assert '<section data-part="1" data-brief="hero with the vault balance"><h1>Vault</h1></section>' in page
    assert '<section hidden data-part="3"' in page and af.page_complete(page)
    assert af.part_html('```html\n<div>x</div>\n```') == '<div>x</div>'
    assert af.part_html('<html><body><div>y</div></body></html>') == '<div>y</div>'


def test_sections_are_shared_between_the_minds(monkeypatch):
    seen = []

    async def ask(cat, model, sys_, user_, tokens):
        seen.append((model, 'plan' if 'plan one web page' in sys_ else 'part'))
        if 'plan one web page' in sys_:
            return 'Checked: x\nAnswer: {"title":"Live Vault","accent":"#2563eb","daynight":true,"sections":[{"name":"Hero","brief":"the vault"},{"name":"Table","brief":"deposits"},{"name":"Form","brief":"withdraw"}]}', 0.001, False
        n = user_.split('THIS SECTION (')[1].split(')')[0]
        return f'<div class="card">part {n}</div>', 0.001, False

    monkeypatch.setattr(fs, '_ws_ask', ask)
    html, usd, own, n = asyncio.run(fs._ws_sections({'id': 'c'}, ['a/one', 'b/two'], 'a live vault page', ''))
    assert n == 3 and 'part 1' in html and 'part 3' in html and af.page_complete(html)
    assert [m for m, k in seen if k == 'part'] == ['a/one', 'b/two', 'a/one'] and round(usd, 3) == 0.004


def test_a_plan_the_mind_garbled_still_builds_a_page_and_the_switch_works():
    plan = af.plan_sections('not json at all', 'a desk with a day and night switch')
    assert len(plan['sections']) == 3 and plan['daynight'] is True
    shell = af.code_shell(plan)
    assert af.page_complete(shell) and len(af.shell_parts(shell)) == 3 and 'id="dn"' in shell and ':root[data-theme=night]' in shell
    assert '&lt;script&gt;' in af.code_shell({**plan, 'title': '<script>x</script>'})


def test_a_minds_report_never_lands_on_the_page():
    raw = '**Missing:** no names given. **Checked:** the four sections.\n<div class="card"><h3>Vault</h3><p>**Plan:** 1. build a card</p><p>Balance $4,200</p></div>'
    out = af.part_html(raw)
    assert out.startswith('<div') and 'Missing' not in out and 'Checked' not in out and 'Plan' not in out and 'Balance $4,200' in out
