"""🧩 SITE-5: the reputation service's routes live in reputation_service.py AND the rep_*.py modules the mover filled. A test that reads the
service's SOURCE reads all of it, with the mover's mechanical edits undone (`rs.NAME` → `NAME`, `@router.` → `@app.`, no `rs = _rs()` line),
so an assertion about a route's body holds wherever the route lives."""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def service_src():
    parts = [(BACKEND / 'reputation_service.py').read_text()]
    for f in sorted(BACKEND.glob('rep_*.py')):
        t = re.sub(r'^\s*rs = _rs\(\)\n', '', f.read_text(), flags=re.M)
        parts.append(re.sub(r'\b(?:rs|_RSM)\.', '', t.replace('@router.', '@app.')))
    return '\n\n\n'.join(parts)
