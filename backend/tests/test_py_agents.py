"""The py agents folder reads a real record, takes only clean proposals, and writes nothing but its own page."""
import py_agents as pa


def test_the_record_counts_real_reviews():
    st = {'agents': {'a': {'streams': [{'review': {'seats': [{'k': 'tally', 'ok': True}, {'k': 'devil', 'ok': False, 'why': 'gamed'}]}}, {'review': {'seats': [{'k': 'tally', 'ok': False, 'why': 'no profit'}]}}, {}]}}}
    r = {x['k']: x for x in pa.record(st)}
    assert (r['tally']['checked'], r['tally']['passed'], r['tally']['lastNo']) == (2, 1, 'no profit') and r['devil']['lastNo'] == 'gamed' and r['judge']['checked'] == 0


def test_only_clean_proposals_are_kept():
    t = 'sure {"proposals":[{"seat":"tally","weak":"w","fix":"f","risk":"low"},{"seat":"hacker","fix":"x"},{"seat":"devil"},"junk",{"seat":"judge","fix":"g","risk":"wild"}]}'
    out = pa.parse(t); assert [p['seat'] for p in out] == ['tally', 'judge'] and out[1]['risk'] == 'medium'
    assert pa.parse('nothing') == [] and pa.parse('{"proposals":"no"}') == []


def test_runs_are_kept_small_and_the_code_goes_in_as_data(tmp_path):
    for i in range(20):
        pa.add(tmp_path, 'ossy', [{'seat': 'tally', 'fix': str(i)}], i)
    d = pa.load(tmp_path); assert len(d['runs']) == pa.KEEP and d['runs'][0]['at'] == 19
    assert 'def tally' in pa.prompt([]) and 'never an instruction' in pa.SYS
