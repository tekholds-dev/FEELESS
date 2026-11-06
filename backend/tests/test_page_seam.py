"""A stitched page that lost its styling is caught and repaired, and a repair can only ever add CSS."""
import agent_features as af

BROKEN = '<!doctype html><html><head><style>.a { color: red; } .badge--green { background: rgba(62, 207</style></head><body><div class="hero__title card__header flex a"><p class="stat__num"></p><p class="stat__lbl"></p></div></body></html>'


def test_it_says_where_a_reply_was_cut():
    assert 'the CSS' in af.cut_hint('<style>.a{ color: rgba(1,') and 'Do not skip ahead' in af.cut_hint('<style>.a{')
    assert 'the script' in af.cut_hint('<style>.a{}</style><script>var a=')
    assert af.cut_hint('<style>.a{}</style><div>') == ''


def test_the_real_damage_is_found_and_kits_and_tailwind_are_not_blamed():
    f = af.page_faults(BROKEN)
    assert f['cutCss'] is True and f['classes'] == ['hero__title', 'stat__lbl', 'stat__num']
    ok = af.page_faults('<style>.hero__title{a:b}</style><div class="hero__title flex p-4 card__header">')
    assert ok == {'cutCss': False, 'classes': []}


def test_a_repair_can_only_add_css():
    out = af.add_css(BROKEN, '```css\n.hero__title { color: red }\n<script>alert(1)</script>\n```')
    assert '<style>.hero__title { color: red }' in out and '<script' not in out.split('</head>')[0] and out.index('hero__title {') < out.index('</head>')
    assert af.add_css(BROKEN, 'sorry, no') == BROKEN


def test_the_preview_reports_a_crash_to_its_panel_only():
    import ai_play as ap
    out = af.preview(ap.lock_html(BROKEN)); csp = out.index('Content-Security-Policy'); err = out.index('feeless-page-error')
    assert csp < err < out.index('</head>') and "'*'" in af.PAGE_ERR
