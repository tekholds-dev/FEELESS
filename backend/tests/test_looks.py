"""🎨 Looks: Obsidian (Feeless Green) by default, with Desk and Pit — the owner's pick 2026-11-12; the four free looks for anyone; an advanced look's colours never reach a locked wallet."""
import looks as lk


def test_free_looks_for_anyone_and_advanced_palettes_only_when_unlocked():
    locked = {r['id']: r for r in lk.catalog(False)}; open_ = {r['id']: r for r in lk.catalog(True)}
    assert lk.DEFAULT == 'obsidian' and set(locked) == set(lk.LOOKS) and len(locked) == 15   # 3 pick + 4 free + 4 elite (open) + 4 advanced
    for k in ('plasma', 'molten', 'neon', 'holo'):
        assert not locked[k]['locked'] and locked[k]['tokens']['accent'].startswith('#')
    for k in ('aurora', 'bloodmoon', 'vapor', 'ghost'):
        assert locked[k]['locked'] and 'tokens' not in locked[k] and len(locked[k]['swatch']) == 4   # a name, a line and swatches; no palette
        assert open_[k]['tokens'] and not open_[k]['locked']
    assert lk.wear('aurora', False) is None and lk.wear('aurora', True)['ambient'] == 'aurora' and lk.wear('nope', True) is None


def test_every_look_has_the_whole_token_set_and_no_old_green():
    need = {'bg', 's1', 's2', 'line', 'lineHi', 'text', 'dim', 'accent', 'hi', 'deep', 'tail', 'tint', 'dark', 'ink', 'third'}
    for k, (_n, _t, _l, _a, t) in lk.LOOKS.items():
        assert set(t) - {'logoHue', 'logoSat', 'edition', 'layout'} == need and isinstance(t['logoHue'], int), k   # each look carries its measured logo angle
        assert '#15d16a' not in t.values() and '#45e486' not in t.values()


def test_the_elite_edition_is_open_to_everyone_and_marks_its_edition():
    import looks
    elite = [l for l in looks.catalog(False) if l['tier'] == 'elite']
    assert {l['id'] for l in elite} == {'amber', 'carbon', 'titanium', 'ledger'} and all(not l['locked'] and l['tokens']['edition'] == 'elite' for l in elite)
    assert looks.wear('ledger', False)['tokens']['edition'] == 'elite' and looks.wear('ghost', False) is None   # advanced stays locked


def test_the_feeless_kit_every_build_reads_is_plasma_with_ready_parts_never_the_banned_green():
    import collective_kits as ck
    t = ck.feeless_row()['text']
    assert '#15d16a' not in t and '#45e486' not in t and '#9b6bff' in t and '#ff3fa4' in t
    assert 'VITALS BAND' in t and 'SEGMENTED CONTROL' in t and 'STORY RINGS' in t and 'prefers-reduced-motion' in t


def test_the_owners_pick_is_one_green_three_layouts_open_to_everyone():
    pick = [l for l in lk.catalog(False) if l['tier'] == 'feeless']
    assert [l['id'] for l in pick] == ['obsidian', 'desk', 'pit'] and all(not l['locked'] for l in pick)
    assert {l['tokens']['accent'] for l in pick} == {'#19e68c'} and [l['tokens']['layout'] for l in pick] == ['obsidian', 'desk', 'pit']
    assert lk.wear('pit', False)['tokens']['layout'] == 'pit' and lk.wear('amber', False)['ambient'] == 'amber'   # the old amber Obsidian lives on as Amber
