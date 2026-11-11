"""🎨 Looks: Plasma by default; the four free looks for anyone; an advanced look's colours never reach a locked wallet."""
import looks as lk


def test_free_looks_for_anyone_and_advanced_palettes_only_when_unlocked():
    locked = {r['id']: r for r in lk.catalog(False)}; open_ = {r['id']: r for r in lk.catalog(True)}
    assert lk.DEFAULT == 'plasma' and set(locked) == set(lk.LOOKS) and len(locked) == 8
    for k in ('plasma', 'molten', 'neon', 'holo'):
        assert not locked[k]['locked'] and locked[k]['tokens']['accent'].startswith('#')
    for k in ('aurora', 'bloodmoon', 'vapor', 'ghost'):
        assert locked[k]['locked'] and 'tokens' not in locked[k] and len(locked[k]['swatch']) == 4   # a name, a line and swatches; no palette
        assert open_[k]['tokens'] and not open_[k]['locked']
    assert lk.wear('aurora', False) is None and lk.wear('aurora', True)['ambient'] == 'aurora' and lk.wear('nope', True) is None


def test_every_look_has_the_whole_token_set_and_no_old_green():
    need = {'bg', 's1', 's2', 'line', 'lineHi', 'text', 'dim', 'accent', 'hi', 'deep', 'tail', 'tint', 'dark', 'ink', 'third'}
    for k, (_n, _t, _l, _a, t) in lk.LOOKS.items():
        assert set(t) == need, k
        assert '#15d16a' not in t.values() and '#45e486' not in t.values()
