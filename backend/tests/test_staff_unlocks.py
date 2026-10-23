"""0c (owner): the creator wallet unlocks EVERY feature everywhere — feature gates use _is_staff (any linked wallet), never a hand-rolled
`in _admin_wallets()`. Security checks (HQ sign-in, money-move signers) stay strict on purpose."""
import re


def test_feature_gates_use_is_staff():
    import reputation_service as rs
    src = open(rs.__file__).read()
    for fn, needle in (('chat_post', '_is_staff(payload.address)'), ('alpha_rooms', '_is_staff(address)'), ('admin_whoami', '_is_staff(address)'),
                       ('is_verified', '_is_staff(a)')):
        i = src.index(f'def {fn}(')
        assert needle in src[i:src.index('\n\n\n', i)], fn
    hand_rolled = [m.start() for m in re.finditer(r'in \{primary_of\(w\) for w in _admin_wallets\(\)\}', src)]
    assert hand_rolled == [], f'{len(hand_rolled)} feature gates still hand-roll the admin list'


def test_a_linked_creator_wallet_reads_as_admin(monkeypatch):
    import asyncio
    import reputation_service as rs
    monkeypatch.setattr(rs, '_is_staff', lambda a: a == 'LINKED')
    monkeypatch.setattr(rs, '_owner_wallets', lambda: ['OWNER'])
    assert asyncio.run(rs.admin_whoami('LINKED')) == {'isAdmin': True, 'isOwner': False}
    assert asyncio.run(rs.admin_whoami('')) == {'isAdmin': False, 'isOwner': False}
    assert rs.is_verified('LINKED') is True and rs.is_verified('') is False
