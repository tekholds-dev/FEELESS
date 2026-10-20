import ai_rig
import ai_router


def test_rig_keeps_listed_values_only_and_prints_the_load_command():
    r = ai_rig.clean({'lan': {'ctx': 16384, 'parallel': 3, 'timeout': 999}, 'win': {'every': 600}, 'bogus': {'ctx': 1}})
    assert r['lan']['ctx'] == 16384 and r['lan']['parallel'] == 3 and r['lan']['timeout'] == 90   # 999 is not an option
    assert r['win']['every'] == 600 and 'bogus' not in r
    v = ai_rig.view(r, {'lan': 'qwen/qwen3-4b-2507'})
    lan = next(x for x in v['rows'] if x['key'] == 'lan')
    assert '--parallel 3' in lan['cmd'] and '--context-length 49152' in lan['cmd'] and lan['name'] == 'G4'
    assert '-np 1' in next(x for x in v['rows'] if x['key'] == 'win')['cmd']


def test_router_reads_the_rig_live():
    ai_router.RIG.clear()
    ai_router.RIG.update({'local': {'timeout': 120, 'parallel': 2, 'perMin': 8}})
    p = ai_router.provider({'LOCAL_LLM_ENABLED': 'true'}, 'local')
    assert p['timeout'] == 120 and p['conc'] == 2
    assert ai_router.rig('local', 'perMin', 4) == 8 and ai_router.rig('lan', 'perMin', 4) == 4
    ai_router.RIG.clear()
