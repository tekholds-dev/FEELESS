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
