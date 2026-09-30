"""Every hard-coded well-known mint in the codebase must be the real one (a typo silently breaks money flows)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANON = {'EPjFWdd5': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So111111': 'So11111111111111111111111111111111111111112'}


def test_usdc_and_wsol_mints_are_canonical_everywhere():
    bad = []
    for base in ('backend', 'frontend/src'):
        for f in (ROOT / base).rglob('*'):
            if f.suffix not in ('.py', '.js', '.jsx') or 'node_modules' in f.parts:
                continue
            for m in re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,44}", f.read_text(errors='ignore')):
                for prefix, real in CANON.items():
                    if m.startswith(prefix) and m != real and len(m) >= 43:
                        bad.append(f'{f.relative_to(ROOT)}: {m}')
    assert not bad, bad
