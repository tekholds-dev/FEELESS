"""The vault's API drawer on the page is a copy of cat_keys.PROVIDERS (owner 2026-11-11: Kalshi was on the server but missing from the drawer)."""
import re
from pathlib import Path

import cat_keys as ck


def test_every_server_key_has_a_row_in_the_page_drawer():
    src = (Path(__file__).resolve().parents[2] / 'frontend/src/components/command/LaunchCat.jsx').read_text()
    block = src[src.index('export const API_PROVIDERS'):src.index('export function ApiDrawer')]
    page = set(re.findall(r"\[\s*'([a-z_]+)',\s*'", block))
    server = {p for p in ck.PROVIDERS if not p.startswith('github')}
    assert server <= page, f'missing on the page: {sorted(server - page)}'
