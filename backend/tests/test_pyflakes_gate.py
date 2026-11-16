"""🧹 The push gate's lint step (owner 2026-11-16 "no dups or dead code"): a finding fails unless its own line says noqa (a deliberate re-export)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('pyflakes_gate', ROOT / 'scripts' / 'pyflakes-gate.py'); pg = importlib.util.module_from_spec(spec); spec.loader.exec_module(pg)


def test_only_a_noqa_line_is_excused(tmp_path):
    f = tmp_path / 'm.py'
    f.write_text("import random\nimport os   # noqa: F401 (re-exported)\nx = f'plain'\n")
    out = f"{f}:1:1: 'random' imported but unused\n{f}:2:1: 'os' imported but unused\n{f}:3:5: f-string is missing placeholders\n"
    bad = pg.findings(out)
    assert len(bad) == 2 and "'random'" in bad[0] and 'f-string' in bad[1]


def test_the_backend_is_clean_now():
    assert pg.main() == 0
