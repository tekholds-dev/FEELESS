import pytest

import collective_kits as ck


def test_a_skill_switch_changes_what_the_agent_is_told_and_only_real_skills_switch():
    cfg = {}
    assert ck.skills_line(cfg) == ''
    ck.set_skill(cfg, 'fl-coin-vet', 'holders', False, ['holders', 'liquidity'])
    line = ck.skills_line(cfg, {'fl-coin-vet': 'Coin Vetter'}); assert 'Coin Vetter: holders' in line and 'do not use' in line
    with pytest.raises(ValueError):
        ck.set_skill(cfg, 'fl-coin-vet', 'wire money', False, ['holders'])
    ck.set_skill(cfg, 'fl-coin-vet', 'holders', True, ['holders']); assert cfg['kitSkillsOff'] == {} and ck.skills_line(cfg) == ''
