"""🎬 Showcase ads: one per proof type, one at a time, never past the $1.25 cap; no browser → no video, never a fake one."""
import asyncio
from pathlib import Path

import show_ads as sa


def test_builds_stop_before_the_cap():
    cost = {'a': 0.30, 'b': 0.40, 'c': 0.35}.get
    jobs = {'pos': {'ws': 'a'}, 'pow': {'ws': 'b'}}
    ok, s = sa.may_start(jobs, cost); assert ok and s == 0.70           # 0.70 + avg 0.35 = 1.05 ≤ 1.25
    jobs['pop'] = {'ws': 'c'}
    ok, s = sa.may_start(jobs, cost); assert not ok and s == 1.05       # 1.05 + 0.35 > 1.25: the next one never starts
    assert sa.next_kind(jobs) == 'pob' and sa.next_kind({k: {'ws': k} for k in sa.KINDS}) is None


def test_every_kind_has_its_own_brief_and_the_view_counts_money():
    assert len({sa.ask_for(k) for k in sa.KINDS}) == 6 and all('16:9' in sa.ask_for(k) for k in sa.KINDS)
    v = sa.view({'pos': {'ws': 'a', 'state': 'done'}}, {'a': 0.2}.get, lambda k: k == 'pos')
    assert v['spent'] == 0.2 and v['left'] == 1.05 and v['rows']['pos']['video'] and v['rows']['pow']['state'] == 'waiting'


def test_no_browser_writes_no_video(tmp_path):
    assert asyncio.run(sa.record('<b>x</b>', Path(tmp_path) / 'pos.webm', '')) is False


def test_health_counts_live_runs_so_the_watcher_never_reloads_mid_build(monkeypatch):
    """🔁 keep-alive.sh reloads new backend code only when /api/cats/health says busy == 0: live folder builds + ad runs count, finished ones don't."""
    import feecat_service as fs

    class T:
        def __init__(self, done): self._d = done
        def done(self): return self._d
    monkeypatch.setattr(fs, '_WS_LIVE', {('c', 'w1'): T(False), ('c', 'w2'): T(True)})
    monkeypatch.setattr(fs, '_ADS_LIVE', {'c': T(False)})
    assert asyncio.run(fs.health())['busy'] == 2
    monkeypatch.setattr(fs, '_WS_LIVE', {}); monkeypatch.setattr(fs, '_ADS_LIVE', {'c': T(True)})
    assert asyncio.run(fs.health())['busy'] == 0


def test_ad_folders_never_take_the_owners_folder_room():
    """🗂 Six ads once stopped at 'no room for a folder' (Happy had 11 of 12): an ad's folder is made past the cap and never counts toward it."""
    import pytest
    import agent_features as af
    cat = {'workspaces': [{'id': f'w{i}'} for i in range(af.MAX_FOLDERS)]}
    with pytest.raises(ValueError):
        af.new_folder(cat, 'build', 'One more', 0)
    row = af.new_folder(cat, 'build', 'Ad · PoW', 0, ad=True)
    assert row['ad'] is True
    cat['workspaces'] = [{'id': 'a', 'ad': True}] * 6 + [{'id': f'w{i}'} for i in range(af.MAX_FOLDERS - 1)]
    assert af.new_folder(cat, 'build', 'Mine', 0)['id']      # 6 ads + 11 of its own: the owner still has room for his 12th


def test_a_build_a_restart_killed_still_counts_toward_the_cap():
    jobs = {'pos': {'ws': 'a'}, 'pow': {'ws': None, 'lostWs': ['b']}}
    assert sa.spent(jobs, {'a': 0.3, 'b': 0.5}.get) == 0.8 and sa.next_kind(jobs) == 'pow'


def test_hidden_means_hidden_in_a_recorded_ad():
    p = sa.playable('<!doctype html><html><head><title>x</title></head><body><div class="nojs" hidden>Animation unavailable</div></body></html>')
    assert p.startswith('<!doctype html><html><head>' + sa.HIDDEN_FIX) and '[hidden]{display:none!important}' in sa.HIDDEN_FIX   # inside head: the doctype stays first (no quirks mode)
    assert sa.playable('<b>bare</b>').startswith(sa.HIDDEN_FIX)


def test_a_crashing_ad_gets_its_own_errors_back_once():
    ask = sa.fix_ask(["Identifier 'scene' has already been declared", "Unexpected token ')'", 'x', 'y'])
    assert "Identifier 'scene' has already been declared" in ask and 'change nothing else' in ask and ask.count(' | ') == 2   # 3 errors at most
    v = sa.view({'poc': {'ws': 'a', 'state': 'page error', 'err': 'boom'}}, {'a': 0.01}.get, lambda k: False)
    assert v['rows']['poc']['err'] == 'boom' and v['rows']['poc']['state'] == 'page error'


def test_the_recorder_hears_a_page_crash(tmp_path):
    import free_browser as fb
    if not fb.chromium_path():
        return
    errs = []
    asyncio.run(sa.record('<body><script>null.style</script></body>', Path(tmp_path) / 'x.webm', fb.chromium_path(), seconds=1, errs=errs))
    assert errs and 'null' in errs[0]


def test_the_recorder_sees_a_broken_frame(tmp_path):
    import free_browser as fb
    if not fb.chromium_path():
        return
    page = ('<body style="margin:0;background:#000;color:#fff;font:40px sans-serif">'
            '<h1 style="position:absolute;left:1150px;top:10px;margin:0">CUT OFF HEADLINE</h1>'
            '<p style="position:absolute;left:20px;top:300px;margin:0">ONE LINE</p><p style="position:absolute;left:24px;top:304px;margin:0">TWO LINE</p>'
            '<div style="position:absolute;left:300px;top:640px;width:400px;height:200px;background:#333">a card</div>'
            '<i style="position:absolute;left:20px;top:20px">STATE play</i></body>')
    lay = []
    asyncio.run(sa.record(page, Path(tmp_path) / 'x.webm', fb.chromium_path(), seconds=2, lay=lay))
    said = ' | '.join(lay)
    assert 'cut by the frame: "CUT OFF HEADLINE"' in said and 'text on text: "ONE LINE" over "TWO LINE"' in said
    assert 'a panel cut by the frame' in said and 'a debug readout: "STATE play"' in said
    fine = []
    asyncio.run(sa.record('<body style="margin:0;background:#000;color:#fff"><h1 style="margin:200px 100px">FITS</h1></body>', Path(tmp_path) / 'y.webm', fb.chromium_path(), seconds=2, lay=fine))
    assert fine == []
    ask = sa.fix_ask([], lay)
    assert 'breaks the 1280 × 720 frame' in ask and 'CUT OFF HEADLINE' in ask and 'from scratch' in ask and 'no game library' in ask   # a layout fix rebuilds whole (patches never landed)
    assert 'change nothing else' in sa.fix_ask(['boom'])


def test_every_ad_has_its_own_light_and_no_libraries():
    looks = {k: sa.ask_for(k) for k in sa.KINDS}
    assert all(sa.LOOK[k].split(' ')[0] in looks[k] for k in sa.KINDS) and len({sa.LOOK[k] for k in sa.KINDS}) == 6
    assert all('no libraries' in a and 'Not the same green' in a and '{look}' not in a and 'nothing past the edges' in a for a in looks.values())
