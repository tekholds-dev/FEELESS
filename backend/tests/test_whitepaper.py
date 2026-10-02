"""The whitepaper module must import, list its chapters and render the real PDF (the server mounts it — a syntax slip here
takes the API down)."""
import pytest


def test_whitepaper_loads_and_renders_pdf():
    pytest.importorskip('reportlab')
    import whitepaper as w
    d = w.document()
    titles = [c['title'] for c in d['chapters']]
    assert d['version'] and 'Roadmap' in titles and 'FUSE Cards' in titles and 'Top-Tier Cards and the Vault' in titles
    pdf = w.render_pdf()
    assert pdf[:4] == b'%PDF' and len(pdf) > 10_000
