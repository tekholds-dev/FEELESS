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
