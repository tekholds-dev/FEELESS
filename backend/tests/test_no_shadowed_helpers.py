"""Guards against a later `def` silently replacing an earlier helper of the same name
(a duplicate `_safe_url` once turned every saved profile image into `True`)."""
import ast
import collections
import pathlib

SERVICES = ['reputation_service.py', 'candles_service.py', 'feecat_service.py', 'server.py']
INTENTIONAL = {'season_award'}  # wraps the original via _orig_season_award


def test_no_duplicate_top_level_functions():
    root = pathlib.Path(__file__).resolve().parent.parent
    for name in SERVICES:
        tree = ast.parse((root / name).read_text())
        counts = collections.Counter(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        dupes = {k for k, v in counts.items() if v > 1} - INTENTIONAL
        assert not dupes, f'{name} redefines {sorted(dupes)}'


def test_safe_url_returns_the_url():
    import reputation_service as rs
    url = '/api/reputation/uploads/' + 'a' * 32 + '.webp'
    assert rs._safe_url(url) == url
    assert rs._safe_url('javascript:alert(1)') == ''
