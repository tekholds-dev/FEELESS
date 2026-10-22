import ai_rig as rg


def test_presets_save_pick_apply_drop_capped():
    rig = rg.clean({})
    st = rg.preset_save({}, 'local', '  fast   reads ', rig['local'], 100)
    assert [p['name'] for p in st['local']] == ['fast reads']
    st = rg.preset_save(st, 'local', 'fast reads', {**rig['local'], 'load': {**rig['local']['load'], 'ctx': 16384}}, 200)   # same name = replaced
    assert len(st['local']) == 1 and st['local'][0]['at'] == 200
    # applying goes through clean(): listed values only, unknown fields dropped
    row = rg.preset_get(st, 'local', 'fast reads')
    assert rg.clean({'local': row}, rig)['local']['load']['ctx'] == 16384
    assert rg.preset_get(st, 'local', 'nope') is None
    for i in range(12):
        rg.preset_save(st, 'lan', f'p{i}', rig['lan'], i)
    assert len(st['lan']) == rg.PRESETS_MAX and st['lan'][0]['name'] == 'p11'          # newest first, capped
    assert rg.preset_drop(st, 'lan', 'p11')['lan'][0]['name'] == 'p10'
    v = rg.presets_view(st); assert set(v) == set(rg.KEYS) and '16K context' in v['local'][0]['words']
    for bad in (('mars', 'x'), ('local', '   ')):
        try:
            rg.preset_save(st, bad[0], bad[1], rig['local'], 1); assert False
        except ValueError:
            pass
    assert len(rg.preset_name('x' * 99)) == rg.PRESET_NAME_MAX
