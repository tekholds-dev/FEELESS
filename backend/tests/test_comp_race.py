"""🏁 AGX-6 (owner 2026-11-14): COMP's exam as a race — every finished exam kept once; OSSY + G4 sit it on their own LM Studio only."""
import json

import comp_v2 as cv
import comp_v2_exam as cx


def _exam(at, comp, g4=None):
    ex = [{'id': 'baseline', 'name': 'Always "won"', 'kind': 'baseline', 'score': {'n': 10, 'acc': 0.5}},
          {'id': 'comp', 'name': 'COMP v2', 'kind': 'local', 'score': {'n': 10, 'acc': comp}},
          {'id': 'claude', 'name': 'Claude', 'kind': 'flagship', 'blocked': 'no key'}]
    if g4 is not None:
        ex.append({'id': 'g4', 'name': 'G4 · qwen', 'kind': 'own', 'score': {'n': 10, 'acc': g4}})
    return {'at': at - 5, 'done': at, 'n': 10, 'examinees': ex}


def test_each_finished_exam_joins_the_race_once_and_blocked_ones_are_not_points(tmp_path):
    assert cv.history(tmp_path) == []
    first = _exam(100, 0.6)
    assert cv.history(tmp_path, first)[0]['scores'] == {'baseline': 0.5, 'comp': 0.6}   # an exam from before the history counts
    assert cv.keep_history(tmp_path, first) is True and cv.keep_history(tmp_path, first) is False
    assert cv.keep_history(tmp_path, _exam(200, 0.7, g4=0.65)) is True
    h = cv.history(tmp_path)
    assert [r['at'] for r in h] == [100, 200] and h[1]['scores']['g4'] == 0.65 and 'claude' not in h[1]['scores'] and h[1]['kinds']['g4'] == 'own'
    (tmp_path / 'exam.json').write_text(json.dumps(_exam(200, 0.7)))
    assert len(cv.status(tmp_path)['race']) == 2


def test_ossy_and_g4_use_only_their_own_lm_studio():
    on = cx.own_minds({'LOCAL_LLM_ENABLED': 'true', 'LOCAL_LLM_BASE_URL': 'http://127.0.0.1:1234/v1/', 'LOCAL_LLM_MODEL': 'qwen/q7',
                        'LAN_LLM_BASE_URL': 'http://10.0.0.9:1234/v1', 'LAN_LLM_MODEL': 'qwen/q4', 'LAN_LLM_API_KEY': 'k'})
    assert [(e[0], e[2], e[3], e[4], e[5]) for e in on] == [('ossy', 'http://127.0.0.1:1234/v1', 'qwen/q7', '', None), ('g4', 'http://10.0.0.9:1234/v1', 'qwen/q4', 'k', None)]
    off = cx.own_minds({})
    assert off[0][5].startswith('off') and off[1][5].startswith('off')   # never a fallback model: off is said, not swapped
