import asyncio

import pytest

import free_browser as fb
import page_look as pl


def test_the_score_reads_the_measures():
    clean = {'texts': 20, 'overlaps': 0, 'covered': 0, 'side': 0, 'errors': 0}
    assert pl.score({'desktop': clean, 'phone': clean}) == (1.0, 'Nothing overlaps at either size')
    v, note = pl.score({'desktop': clean, 'phone': {**clean, 'overlaps': 4, 'side': 40}})
    assert v < pl.BROKEN and 'phone: 4 overlaps, scrolls sideways' in note
    assert pl.score({'desktop': {'texts': 0}})[0] == 0.0 and pl.score({})[0] is None


@pytest.mark.skipif(not fb.chromium_path(), reason='no local browser')
def test_a_real_browser_tells_a_clean_page_from_a_broken_one():
    clean = '<html><body><h1>Title</h1><p>Some words here</p><p>More words below them</p></body></html>'
    broken = '<html><body style="margin:0"><p style="position:absolute;top:10px;left:10px;margin:0;font-size:30px">First words sit here</p><p style="position:absolute;top:12px;left:12px;margin:0;font-size:30px">Second words on top</p><div style="width:3000px;height:10px"></div><p style="margin-top:100px">Hidden words <span>under</span></p><div style="position:absolute;top:90px;left:0;width:900px;height:120px;background:#123"></div></body></html>'
    a, b = asyncio.run(pl.measure(clean, fb.chromium_path())), asyncio.run(pl.measure(broken, fb.chromium_path()))
    assert pl.score(a)[0] == 1.0, a
    v, note = pl.score(b)
    assert v < 1.0 and 'overlaps' in note and 'sideways' in note and 'covered' in note, b
