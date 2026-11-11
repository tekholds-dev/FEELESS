"""🪞 The agent learns how its owner writes and mirrors it only as much as the owner set."""
import voice_mirror as vm
import prompt_studio as ps


def test_it_learns_the_owners_voice_and_scales_with_the_setting():
    p = {}
    for t in ['hurry and lmk my first 2 tasks lol', 'dont stop lol when ur done', 'WOW me wit styling!!', 'make it wide asl lol', 'fix this shit fr', 'ur good bro lol']:
        p = vm.learn(p, t)
    t = vm.traits(p)
    assert 'short, quick messages' in t and 'mostly lowercase' in t and 'swears casually' in t and any(x.startswith('slang like lol') for x in t)
    assert vm.line(p, 0) == '' and vm.line(p, 2).startswith('Match the way your owner writes') and 'never copy insults' in vm.line(p, 3)
    assert vm.line(vm.learn({}, 'hi'), 3) == ''   # under 5 messages it says nothing


def test_the_mirror_is_a_persona_setting_kept_in_range():
    assert ps.clean_persona({'style': 'snappy', 'heat': 4, 'mirror': 9}) == {'style': 'snappy', 'heat': 4, 'mirror': 3}
    assert ps.clean_persona(None)['mirror'] == 0
