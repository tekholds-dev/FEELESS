"""🎨 LOOK-1 / STYLE-1: scripts/hex-to-tokens.py turns hand-written hex into meta.css tokens by role, keeps alpha, flips in day theme."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location('hex_to_tokens', Path(__file__).resolve().parents[2] / 'scripts' / 'hex-to-tokens.py')
h2t = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h2t)


def test_roles_alpha_day_and_comments():
    out = h2t.convert('.a{color:#fff;background:#0a0a19f2;border:1px solid #57c7ff40}'
                      ' body.theme-day .a{background:#fff;color:#101a44} .b{color:#ff8fa3;fill:#ffc24d} /* #123456 */')
    assert '.a{color:var(--m-text);' in out
    assert 'color-mix(in srgb, var(--m-surface) 95%, transparent)' in out
    assert 'color-mix(in srgb, var(--m-accent) 25%, transparent)' in out
    assert 'body.theme-day .a{background:var(--m-surface);color:var(--m-text)}' in out
    assert '.b{color:var(--m-danger);fill:var(--m-warn)}' in out
    assert '/* #123456 */' in out and h2t.count(out) == 0


def test_only_filter_leaves_other_rules():
    out = h2t.convert('.clx-a{color:#fff} .other{color:#fff}', only=r'\.clx-')
    assert out == '.clx-a{color:var(--m-text)} .other{color:#fff}'


def test_palette_mode_is_pixel_identical_and_idempotent():
    """STYLE-1: every colour → one page token declared once; putting the hex back gives the original exactly; url()/comments untouched."""
    css = "/* keep #123 */\n.a{color:#FF0000;background:#111;border:1px solid #ff0000}\n.b{background:url('x#fff.png');box-shadow:0 0 0 #19e68c80}\n@media (max-width:640px){.c{color:#111}}\n"
    H = h2t
    out, pal = H.palette(css, 'xy')
    assert H.outside(out) == 0 and len(pal) == 3                     # #FF0000 / #ff0000 are one token
    assert "url('x#fff.png')" in out and '/* keep #123 */' in out
    assert H.unpalette(out).replace('#ff0000', '#FF0000', 1) == css or H.unpalette(out).lower() == css.lower()
    assert H.palette(out, 'xy')[0] == out                             # a second run changes nothing
    assert H.prefix('catWorkbench.css') == 'cw' and H.prefix('boosts.css') == 'boo'


def test_palette_lands_after_an_import_whose_url_holds_semicolons():
    css = "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap');\n.a{color:#123456}"
    out, _ = h2t.palette(css, 'q')
    assert out.startswith("@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap');\n:root {")
