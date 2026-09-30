from badge_cards import (default_badge_card, default_season_card, clean_edit, merge, key_counts, per_key_each, tier_each, card_money)


def test_defaults_and_edits():
    c = default_badge_card({'id': 'sharp-caller', 'label': 'Sharp Caller', 'icon': '🎯', 'tone': 'gold', 'tier': 3, 'how': '5+ calls'})
    assert c['key'] == 'badge:sharp-caller' and c['rarity'] == 'epic' and c['design'] == 'holo'
    e = clean_edit({'title': 'Sniper', 'design': 'glitch', 'accent': '#FF00AA', 'accent2': 'red', 'art': 'javascript:x', 'lore': 'x' * 900, 'hack': 1})
    assert e == {'title': 'Sniper', 'lore': 'x' * 600, 'design': 'glitch', 'accent': '#ff00aa'}
    m = merge(c, e)
    assert m['title'] == 'Sniper' and m['glyph'] == '🎯' and m['edited']
    assert default_season_card({'id': 's1', 'name': 'Diamond Winter', 'badgeUrl': 'https://x/y.png'})['art'] == 'https://x/y.png'


def test_per_key_each_pct_weight_fixed():
    counts = key_counts({'A': 'Gold', 'B': 'Gold'}, {'A': ['og'], 'C': ['og', 'og']})
    assert counts == {'tier:Gold': 2, 'badge:og': 2}
    each = per_key_each('pct', {'badge:og': 50, 'tier:Gold': 20, 'badge:none': 30}, {'badge:og': 0.1}, counts, 2.0, 0, 0.5)
    assert each == {'badge:og': 0.55, 'tier:Gold': 0.2}
    assert per_key_each('weight', {'badge:og': 3}, {}, counts, 1.0, 6) == {'badge:og': 0.5}


def test_card_money_sums_payouts():
    pools = [{'name': 'OG', 'mode': 'pct', 'weights': {'badge:og': 40}, 'payouts': [{'perKey': {'badge:og': 0.1}}, {'perKey': {'badge:og': 0.05}}]}]
    m = card_money('badge:og', pools, {}, {})
    assert m['earnedEach'] == 0.15 and m['earns'][0]['pct'] == 40
    s = card_money('season:s1', [], {'s1': {'rows': [{'tier': 'Gold', 'sol': 0.2}, {'tier': 'Gold', 'sol': 0.4}, {'tier': 'Bronze', 'sol': 0.1}]}}, {'s1': 10})
    assert s['byTier'] == {'tier:Gold': 0.3, 'tier:Bronze': 0.1} and s['earns'][0]['pct'] == 10
    assert tier_each([]) == {}


def test_motion_edit():
    assert clean_edit({'motion': 'alive'}) == {'motion': 'alive'} and clean_edit({'motion': 'spin'}) == {}
    assert default_season_card({'id': 's1'})['motion'] == 'alive'
