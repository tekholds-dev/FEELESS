import ai_play as p


def test_the_document_is_extracted_and_its_network_is_always_blocked():
    h = p.extract("Here you go:\n```html\n<!doctype html><html><head><meta http-equiv='Content-Security-Policy' content='default-src *'></head><body>hi</body></html>\n```")
    assert h.startswith('<!doctype html>') and h.endswith('</html>')
    locked = p.lock(h)
    assert "default-src 'none'" in locked and 'default-src *' not in locked
    assert p.extract('just words, no markup') is None
    assert p.extract('<svg viewBox="0 0 10 10"></svg>').startswith('<!doctype html>')


def test_creations_are_kept_newest_first_and_bounded():
    items = []
    for i in range(35):
        items, it = p.add(items, f'make {i}', '<html><head></head><body></body></html>', 'LOCAL AI', now=1000 + i)
    assert len(items) == p.KEEP and items[0]['prompt'] == 'make 34' and "default-src 'none'" in items[0]['html']
    assert 'Change this document' in p.iterate_prompt('bigger', '<html></html>')
