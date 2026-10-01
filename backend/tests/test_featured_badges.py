"""Chat badge picker: only badges you earned, capped at the chat limit; nothing else on the profile changes."""
import asyncio

import pytest

rs = pytest.importorskip('reputation_service')
W = 'Aaaa1111111111111111111111111111111111111111'


def test_pick_badges_from_chat(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'PROFILE_PATH', tmp_path / 'profiles.json')
    (tmp_path / 'profiles.json').write_text('{"profiles": {"%s": {"displayName": "degen", "featuredBadges": []}}}' % rs.primary_of(W))
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: rs.primary_of(a))
    async def badges(owner):
        return {'badges': [{'id': 'og'}, {'id': 'whale'}, {'id': 'sniper-hunter'}, {'id': 'fee-holder'}]}
    monkeypatch.setattr(rs, 'wallet_badges', badges)
    monkeypatch.setattr(rs, '_badge_limits', lambda: {'profile': 3, 'chat': 3})
    out = asyncio.run(rs.set_featured_badges(rs.FeaturedBadgesIn(address=W, session='s', badges=['whale', 'not-earned', 'og', 'whale', 'fee-holder', 'sniper-hunter'])))
    assert out == {'featuredBadges': ['whale', 'og', 'fee-holder']}
    saved = rs._json_load(tmp_path / 'profiles.json', {})['profiles'][rs.primary_of(W)]
    assert saved == {'displayName': 'degen', 'featuredBadges': ['whale', 'og', 'fee-holder']}
