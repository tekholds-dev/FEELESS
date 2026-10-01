"""Owner rule: NO GeckoTerminal sitewide (backend or frontend). DexScreener + our own indexes only."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_no_geckoterminal_anywhere():
    hits = []
    for base, exts in ((ROOT / 'backend', {'.py'}), (ROOT / 'frontend' / 'src', {'.js', '.jsx', '.css'})):
        for f in base.rglob('*'):
            if f.suffix in exts and 'node_modules' not in f.parts and '.venv' not in f.parts and f.name != 'test_no_geckoterminal.py':
                text = f.read_text(errors='ignore')
                if re.search(r'geckoterminal\.com|GeckoTerminal\'|cached\(\'GeckoTerminal', text, re.I):
                    hits.append(str(f.relative_to(ROOT)))
    assert hits == []
