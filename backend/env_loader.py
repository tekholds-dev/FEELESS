"""Loads backend/.env into os.environ (without overriding real env vars)."""
import os
from pathlib import Path


def load_env():
    path = Path(__file__).parent / '.env'
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if key and key.replace('_', '').isalnum():
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


load_env()
