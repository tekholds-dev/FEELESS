"""A backend module imported for the first time inside a test is still sandboxed (never writes real backend/data)."""
import sys
from pathlib import Path

REAL = (Path(__file__).resolve().parents[1] / 'data').resolve()


def test_lazy_import_is_sandboxed():
    sys.modules.pop('runners_sandbox_probe', None)
    probe = Path(__file__).resolve().parents[1] / 'runners_sandbox_probe.py'
    probe.write_text("from pathlib import Path\nP = Path(__file__).resolve().parent / 'data' / 'probe.json'\n")
    try:
        import runners_sandbox_probe as m
        assert REAL not in m.P.resolve().parents        # redirected to the per-test sandbox
    finally:
        probe.unlink()
        sys.modules.pop('runners_sandbox_probe', None)
