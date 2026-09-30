"""Two handlers on one path+method means the second is silently dead (this once broke the launch Shield)."""
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.mark.parametrize('module', ['reputation_service', 'feecat_service'])
def test_no_duplicate_routes(module):
    mod = pytest.importorskip(module)
    seen = Counter((m, r.path) for r in mod.app.routes for m in (getattr(r, 'methods', None) or []))
    dupes = sorted(f'{m} {p}' for (m, p), n in seen.items() if n > 1)
    assert not dupes, f'duplicate routes: {dupes}'
