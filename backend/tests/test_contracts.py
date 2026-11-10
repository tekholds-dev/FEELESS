"""COL-20: every shared record keeps its contract, checked on real shapes made by the code that owns them."""
import json
from pathlib import Path

import collective_parts as cp
import contracts as ct
import mission
import proof_events as pe

FIX = json.loads((Path(__file__).parent / 'fixtures' / 'mission_folders.json').read_text())


def test_every_real_envelope_keeps_its_contract():
    n = 0
    for case, f in FIX['folders'].items():   # case names lead with the kind: pow_real_closed, pob_scoreboard, ...
        for kind in [case.split('_')[0]]:
            e = mission.envelope(kind, f, 10 ** 10, FIX.get('cat'))
            if e:
                assert ct.check('envelope', e) == [], (kind, f.get('id'), ct.check('envelope', e)); n += 1
    assert n >= 5


def test_calls_events_and_parts_keep_theirs(tmp_path):
    assert ct.check('call', mission.call_row('c', 'pos', 'w', 0, 'a/b', {'route': 'openrouter', 'model': 'b'}, 'openrouter', 0.01, 900, True, 1)) == []
    p = tmp_path / 'e.db'; pe.append(p, 'pos', 'w', 'plan', {'by': 'A'}, key=b'k' * 32)
    assert ct.check('event', pe.history(p, 'pos', 'w')[0]) == []
    db = tmp_path / 'parts.db'
    cp.harvest(db, 'c', {'kind': 'pos', 'id': 'p', 'ws': 'w', 'state': 'proved'}, '<section><h2>Hero</h2><p>' + 'x' * 120 + '</p></section>', [], {})
    assert ct.check('part', cp.family(db)[0]) == []
    assert ct.check('envelope', {'v': 2}) and ct.check('event', {**pe.history(p, 'pos', 'w')[0], 'kind': 'nope'})   # a broken row is caught
