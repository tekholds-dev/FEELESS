import pytest
import crews as cr

A, B, C, D = 'A' * 40, 'B' * 40, 'C' * 40, 'D' * 40


def test_member_invites_and_the_wallet_accepts_or_declines():
    st = {}
    c = cr.create(st, A, 'Sicario', 'SIC', 0)
    cr.invite(st, A, B, 10)
    assert cr.invites_for(st, B, 20)[0]['tag'] == 'SIC'
    with pytest.raises(ValueError):
        cr.invite(st, A, B, 11)                       # one invite per family per wallet
    cr.accept(st, B, c['id'], 30)
    assert B in st['crews'][c['id']]['members'] and cr.invites_for(st, B, 40) == []
    cr.invite(st, B, C, 50)                            # any member may invite
    cr.decline(st, C, c['id'], 60)
    with pytest.raises(ValueError):
        cr.accept(st, C, c['id'], 70)


def test_invites_expire_and_full_families_cannot_take_more():
    st = {}
    c = cr.create(st, A, 'Sicario', 'SIC', 0)
    cr.invite(st, A, B, 0)
    assert cr.invites_for(st, B, cr.INVITE_SEC + 1) == []
    st['crews'][c['id']]['seats'] = 1
    cr.invite(st, A, C, cr.INVITE_SEC + 2)
    with pytest.raises(ValueError):
        cr.accept(st, C, c['id'], cr.INVITE_SEC + 3)


def test_creator_adds_directly_and_gets_a_seat_pack_when_full():
    st = {}
    c = cr.create(st, A, 'Sicario', 'SIC', 0)
    st['crews'][c['id']]['seats'] = 1
    cr.add_direct(st, A, D, 5)
    assert D in st['crews'][c['id']]['members'] and st['crews'][c['id']]['seats'] == 1 + cr.PACK_SEATS
