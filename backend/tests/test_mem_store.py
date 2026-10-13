"""💾 The agents' stores live in memory (owner, 2026-10-12: "storage efficient"): loaded once, written at most every N seconds + on
shutdown. agents.json (3 MB) used to be parsed AND written on every ~30s pass."""
from pathlib import Path

import mem_store as ms

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()


def _store(tmp, every=90.0):
    io = {'loads': 0, 'saves': []}
    path = {'p': tmp / 'a.json'}

    def load(p, d):
        io['loads'] += 1
        return {'n': 0, 'from': str(p)}

    def save(p, o):
        io['saves'].append((str(p), dict(o)))
    return ms.MemStore(lambda: path['p'], every, load, save), io, path


def test_loaded_once_and_written_at_most_every_n_seconds(tmp_path):
    s, io, _p = _store(tmp_path)
    st = s.get()
    assert s.get() is st and io['loads'] == 1                                   # the live object, not a re-parse
    t0 = s.savedAt
    assert s.put({**st, 'n': 1}, now=t0 + 10) is False and io['saves'] == []    # inside the window: memory only
    assert s.get()['n'] == 1                                                    # readers see the newest object at once
    assert s.put({**st, 'n': 2}, now=t0 + 91) is True and io['saves'][-1][1]['n'] == 2
    assert s.flush() is False                                                   # nothing changed since → no write
    s.put({'n': 3}, now=t0 + 92)
    assert s.flush() is True and io['saves'][-1][1] == {'n': 3}                 # shutdown keeps what was learned
    assert s.put({'n': 4}, now=t0 + 93, force=True) is True                     # an owner click is written at once


def test_a_new_path_is_a_fresh_load_never_another_tests_object(tmp_path):
    s, io, path = _store(tmp_path)
    s.put({'n': 7}, now=0)
    path['p'] = tmp_path / 'other' / 'a.json'                                   # conftest re-points module Paths per test
    assert s.get() == {'n': 0, 'from': str(path['p'])} and io['loads'] == 2
    s.put({'n': 8}, force=True)
    assert io['saves'][-1][0] == str(path['p'])                                 # written to the CURRENT path


def test_the_agents_pass_reads_and_writes_its_stores_through_memory():
    assert "st = _json_load(AGENTS_PATH" not in SRC and "_json_save(AGENTS_PATH" not in SRC and "_json_load(AGENTS_PATH" not in SRC
    assert "_json_save(LINGO_PATH" not in SRC and "_json_load(LINGO_PATH" not in SRC
    assert "_agents_mem.put(st, now)" in SRC and "_lingo_mem.put(lingo, now)" in SRC
    for f in ('_agents_mem.flush', '_lingo_mem.flush', '_shadow_flush', '_social_flush'):   # nothing learned is lost on a stop
        assert f in SRC[SRC.index("async def _keeper_stop"):SRC.index("async def _prime_tick(now)")]
    assert "now - _fuse._f(_shadow.get('savedAt')) >= SHADOW_SAVE_SEC" in SRC and "now - _fuse._f(_social.get('savedAt')) >= SOCIAL_SAVE_SEC" in SRC
