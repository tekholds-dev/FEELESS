"""🎨 Looks: Obsidian (Feeless Green) by default, with Desk, Pit and Carbon (Slice 34 keeps only these four; a retired look wears Obsidian)."""
import looks as lk


def test_only_obsidian_desk_pit_and_carbon_stay_and_a_retired_look_wears_obsidian():
    """Slice 34 (owner 2026-11-20): keep Obsidian (default), Desk, Pit and Carbon; anyone wearing a retired look falls back to Obsidian."""
    locked = {r['id']: r for r in lk.catalog(False)}
    assert lk.DEFAULT == 'obsidian' and list(locked) == ['obsidian', 'desk', 'pit', 'carbon'] and not any(r['locked'] for r in locked.values())
    for k in ('plasma', 'molten', 'neon', 'holo', 'aurora', 'bloodmoon', 'vapor', 'ghost', 'amber', 'titanium', 'ledger'):
        assert k in lk.RETIRED and k not in lk.LOOKS and lk.wear(k, False)['id'] == 'obsidian' and lk.wear(k, True)['id'] == 'obsidian'
    assert lk.wear('nope', True) is None and lk.wear('carbon', False)['tokens']['accent'] == '#5e6ad2'


def test_every_look_has_the_whole_token_set_and_no_old_green():
    need = {'bg', 's1', 's2', 'line', 'lineHi', 'text', 'dim', 'accent', 'hi', 'deep', 'tail', 'tint', 'dark', 'ink', 'third'}
    for k, (_n, _t, _l, _a, t) in lk.LOOKS.items():
        assert set(t) - {'logoHue', 'logoSat', 'edition', 'layout'} == need and isinstance(t['logoHue'], int), k   # each look carries its measured logo angle
        assert '#15d16a' not in t.values() and '#45e486' not in t.values()


def test_carbon_keeps_its_elite_edition():
    assert lk.wear('carbon', False)['tokens']['edition'] == 'elite' and lk.wear('obsidian', False)['tokens']['edition'] == 'elite'


def test_the_feeless_kit_every_build_reads_is_plasma_with_ready_parts_never_the_banned_green():
    import collective_kits as ck
    t = ck.feeless_row()['text']
    assert '#15d16a' not in t and '#45e486' not in t and '#9b6bff' in t and '#ff3fa4' in t
    assert 'VITALS BAND' in t and 'SEGMENTED CONTROL' in t and 'STORY RINGS' in t and 'prefers-reduced-motion' in t


def test_the_owners_pick_is_one_green_three_layouts_open_to_everyone():
    pick = [l for l in lk.catalog(False) if l['tier'] == 'feeless']
    assert [l['id'] for l in pick] == ['obsidian', 'desk', 'pit', 'carbon'] and all(not l['locked'] for l in pick)
    assert {l['tokens']['accent'] for l in pick[:3]} == {'#19e68c'} and [l['tokens'].get('layout') for l in pick[:3]] == ['obsidian', 'desk', 'pit']
    assert lk.wear('pit', False)['tokens']['layout'] == 'pit'
