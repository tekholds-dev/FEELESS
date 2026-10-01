"""Guard: no backend module may reference an undefined name (a deleted constant once broke Pump Pulse 65× in a day)."""
import pathlib

import pytest

pyflakes_api = pytest.importorskip('pyflakes.api')
reporter = pytest.importorskip('pyflakes.reporter')


def test_backend_has_no_undefined_names():
    import io
    out = io.StringIO()
    rep = reporter.Reporter(out, out)
    for f in sorted(pathlib.Path(__file__).resolve().parents[1].glob('*.py')):
        pyflakes_api.checkPath(str(f), rep)
    bad = [line for line in out.getvalue().splitlines() if 'undefined name' in line or 'referenced before assignment' in line]
    assert bad == []
