import pytest
import street_chat as sc


@pytest.fixture(autouse=True)
def _keep_per_wallet():
    """The service's _crew_cfg() sets the module-global crews.PER_WALLET from the Familia rules — put it back so test_crews (same xdist
    worker, any order) never sees this module's value."""
    import crews
    was = crews.PER_WALLET
    yield
    crews.PER_WALLET = was


def test_room_names_are_strict():
    assert sc.room_of('fee') == 'city-fee' and sc.room_of('Harbor') == 'city-harbor'
    assert sc.room_of('../x') is None and sc.room_of('') is None and sc.room_of('a' * 40) is None


def test_the_block_remembers_who_is_here_for_90s_and_hides_invisible():
    h = {}
    sc.here_beat(h, 'fee', 'A', 1000.0); sc.here_beat(h, 'fee', 'B', 1050.0); sc.here_beat(h, 'harbor', 'C', 1050.0)
    assert sc.here_list(h, 'fee', 1060.0) == ['B', 'A']
    assert sc.here_list(h, 'fee', 1100.0) == ['B']                     # A's beat is 100s old
    assert sc.here_list(h, 'fee', 1060.0, visible=lambda w: w != 'B') == ['A']
    sc.here_beat(h, 'fee', 'D', 2000.0)
    assert 'A' not in h['fee'] and 'B' not in h['fee']                 # stale wallets are pruned on the next beat


def test_lines_are_dressed_for_the_street():
    msgs = [{'id': 'm1', 'ts': 1_000_000, 'text': 'yo @boss $WIF is cooking', 'username': 'kid', 'address': 'W1', 'tokens': [{'symbol': 'WIF', 'pairAddress': 'P1', 'chainId': 'solana', 'pair': {'marketCap': 2e6, 'info': {'imageUrl': 'i.png'}}}]},
            {'id': 'm2', 'ts': 1_100_000, 'text': 'gm', 'username': 'boss', 'address': 'W2'}]
    fams = {'W1': {'id': 'c1', 'tag': 'SIC', 'color': '#d4af37', 'don': False}, 'W2': {'id': 'c1', 'tag': 'SIC', 'color': '#d4af37', 'don': True}}
    calls = {'m1:P1': {'room': 'city-fee', 'messageId': 'm1', 'priceAtCall': 1.0, 'lastPrice': 2.5, 'peakPrice': 3.0, 'symbol': 'WIF', 'pairAddress': 'P1', 'chain': 'solana'},
             'x': {'room': 'feed-sol', 'messageId': 'm1', 'priceAtCall': 1.0, 'lastPrice': 9.0, 'peakPrice': 9.0, 'symbol': 'X'}}
    rec = sc.receipts(calls, 'city-fee')
    assert rec == {'m1': [{'symbol': 'WIF', 'x': 2.5, 'peakX': 3.0, 'mcAtCall': None, 'pairAddress': 'P1', 'chain': 'solana', 'image': None}]}   # another room's call never shows
    lines = sc.dress(msgs, fams.get, rec, {'m2': {'🫡': ['W1', 'W9'], '🚀': ['W1']}}, viewer='W2', handles=['boss'])
    a, b = lines
    assert a['fam']['tag'] == 'SIC' and a['calls'][0]['x'] == 2.5 and a['coins'][0] == {'symbol': 'WIF', 'pairAddress': 'P1', 'chain': 'solana', 'image': 'i.png', 'mc': 2e6}
    assert a['atMe'] is True and a['mine'] is False and b['mine'] is True and b['fam']['don'] is True
    assert b['reacts'] == {'🫡': {'n': 2, 'mine': False}}               # 🚀 is not a street reaction
    v = sc.vitals(lines, 1_200_000)
    assert v['hour'] == 2 and sum(v['spark']) == 2 and v['spark'][-1] == 2 and v['families'] == ['SIC'] and v['hot'] == {'symbol': 'WIF', 'peakX': 3.0, 'x': 2.5, 'by': 'kid', 'fam': 'SIC'}


def test_who_may_pull_a_line():
    assert sc.can_pull(True, None, False, 'c9')                    # staff: any line
    assert sc.can_pull(False, 'c1', True, 'c1')                    # a Don: their own family
    assert not sc.can_pull(False, 'c1', True, 'c2') and not sc.can_pull(False, 'c1', False, 'c1') and not sc.can_pull(False, None, True, None)


def test_the_street_routes_are_signed_and_the_mod_rules_hold():
    import reputation_service as rs
    src = open(rs.__file__).read()
    i = src.index('async def familia_street_mod(')
    body = src[i:src.index('\n\n\n', i)]
    assert '_session_or_401(p.address, p.session)' in body and '_stc.can_pull(' in body and "Only FEELESS staff can mute." in body
    assert "startswith(('feed-', 'city-'))" in src                  # a coin pasted on a street gets a receipt


def test_a_street_read_through_the_service():
    import asyncio
    import json
    import reputation_service as rs
    d = rs._chat_load()
    d['rooms']['city-fee'] = [{'id': 'm1', 'ts': 1, 'text': 'gm streets', 'username': 'kid', 'address': 'W1' * 20}]
    rs.CHAT_PATH.write_text(json.dumps(d))
    out = asyncio.run(rs.familia_street('fee', '', ''))
    assert out['room'] == 'city-fee' and out['lines'][0]['text'] == 'gm streets' and out['lines'][0]['fam'] is None
    assert out['hereN'] == 0 and out['me'] is None and out['mod'] == {'staff': False, 'don': False, 'famId': None} and out['reacts'] == list(sc.REACTS)
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        asyncio.run(rs.familia_street('../etc', '', ''))


def test_the_creator_sees_their_family_from_any_linked_or_hq_wallet(monkeypatch):
    import reputation_service as rs
    st = {'by': {'SEATED': 'c1'}, 'crews': {'c1': {'id': 'c1', 'owner': 'SEATED', 'members': ['SEATED']}}}
    links = {'ME': ['ME', 'SEATED'], 'HQ2': ['HQ2'], 'RANDO': ['RANDO'], 'OTHER': ['OTHER']}
    monkeypatch.setattr(rs, 'linked_of', lambda a: links.get(a, [a]))
    monkeypatch.setattr(rs, '_admin_wallets', lambda: ['HQ1', 'SEATED'])
    monkeypatch.setattr(rs, '_is_staff', lambda a: a in ('HQ2', 'HQ1', 'SEATED'))
    assert rs._seat_of(st, 'SEATED') == 'SEATED'                  # seated itself
    assert rs._seat_of(st, 'ME') == 'SEATED'                      # a linked wallet holds the seat
    assert rs._seat_of(st, 'HQ2') == 'SEATED'                     # staff: the creator's account is every HQ wallet
    assert rs._seat_of(st, 'RANDO') == 'RANDO' and rs._seat_of(st, None) is None   # nobody else borrows a seat
    src = open(rs.__file__).read()
    i = src.index('async def familia_world(')
    assert 'me = _seat_of(st, me) if me else None' in src[i:i + 1200]


def test_overwatch_shows_every_family_to_the_owner_only(monkeypatch):
    import asyncio
    import json
    import reputation_service as rs
    st = {'crews': {'c1': {'id': 'c1', 'tag': 'SIC', 'name': 'Sicario', 'owner': 'HQ', 'members': ['HQ', 'M2'], 'seats': 5, 'paid': [{'usd': 25, 'at': 1}]},
                    'c2': {'id': 'c2', 'tag': 'BNK', 'name': 'Bonk Boys', 'owner': 'B1', 'members': ['B1'], 'seats': 5, 'paid': []}},
          'by': {'HQ': 'c1', 'M2': 'c1', 'B1': 'c2'}}
    rs.CREWS_PATH.write_text(json.dumps(st))
    monkeypatch.setattr(rs, '_is_staff', lambda a: a == 'HQ')
    monkeypatch.setattr(rs, '_crew_pieces', lambda ms, now: {'M2': [{'usd': 12.0, 'costUsd': 100.0, 'at': now}]})
    calls = []
    monkeypatch.setattr(rs, '_require_owner', lambda req: calls.append(req) or 'HQ')
    out = asyncio.run(rs.admin_familia_overwatch(object()))
    assert calls and [f['tag'] for f in out['families']] == ['SIC', 'BNK']               # the creator's family first
    sic = out['families'][0]
    assert sic['creator'] and sic['paidUsd'] == 25 and sic['week']['trades'] == 1 and sic['week']['usd'] == 12.0
    assert {m['address']: m['don'] for m in sic['members']} == {'HQ': True, 'M2': False}
    assert out['totals']['families'] == 2 and out['totals']['members'] == 3 and out['pricing']['baseSeats'] == 5 and 'custody' in out


def test_the_books_tape_every_members_trades_newest_first(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs, '_crew_name', lambda a: a.lower())
    pcs = {'A': [{'symbol': 'WIF', 'mint': 'w', 'ret': 0.5, 'usd': 50.0, 'costUsd': 100.0, 'holdMin': 31, 'at': 100, 'tx': 't1'}],
           'B': [{'symbol': 'BONK', 'mint': 'b', 'ret': -0.2, 'usd': -4.0, 'costUsd': 20.0, 'holdMin': 6, 'at': 200, 'tx': 't2'}]}
    book = rs._crew_book(pcs)
    assert [r['symbol'] for r in book] == ['BONK', 'WIF'] and book[0]['who'] == 'b' and book[1]['usd'] == 50.0
    assert rs._crew_book({}) == [] and len(rs._crew_book({'A': pcs['A'] * 60})) == 40


def test_family_fuse_counts_cards_on_linked_wallets_and_the_creators_prime_cards(monkeypatch):
    import json
    import reputation_service as rs
    leg = lambda p: {'pairAddress': p, 'symbol': p.upper(), 'mint': p}
    rs.FUSES_PATH.write_text(json.dumps({'fuses': {'d1': {'name': 'mine', 'creator': 'LINKED', 'legs': [leg('a'), leg('b')]}, 'd2': {'name': 'theirs', 'creator': 'X', 'legs': [leg('c')]}}}))
    rs.FUSE_HQ_PATH.write_text(json.dumps({'positions': [{'id': 'p1', 'wallet': 'LINKED', 'legs': [leg('d')]}],
                                           'prime': {'cards': {'safe': {'legs': [leg('e'), leg('f')]}, 'degen': {'real': True, 'legs': [leg('g')]}}}}))
    monkeypatch.setattr(rs, 'linked_of', lambda a: ['M', 'LINKED'] if a in ('M', 'LINKED') else [a])
    monkeypatch.setattr(rs, '_is_staff', lambda a: a == 'HQ')
    keys = [x['key'] for x in rs._ffuse_cards({}, {'owner': 'M', 'members': ['M']})]
    assert keys == ['design:d1', 'card:p1']                                 # made / held on the member's linked wallet — was missed before
    keys = [x['key'] for x in rs._ffuse_cards({}, {'owner': 'HQ', 'members': ['HQ']})]
    assert keys[:2] == ['design:d1', 'design:d2'] and keys[2:] == ['prime:degen', 'prime:safe']   # the creator fields every design + the Prime cards, the real one first


def test_a_quiet_world_read_does_not_rewrite_the_crews_store(monkeypatch):
    import asyncio
    import json
    import reputation_service as rs
    rs.CREWS_PATH.write_text(json.dumps({'crews': {}, 'by': {}}))
    monkeypatch.setattr(rs, '_cartels_now', lambda now: [])

    async def no_fuse(now):
        return None
    monkeypatch.setattr(rs, '_ffuse_tick', no_fuse)
    asyncio.run(rs.familia_world('', ''))                       # the first read seeds the world (homes, blank state) → saved
    saves = []
    monkeypatch.setattr(rs, '_json_save', lambda path, d: saves.append(str(path)))
    asyncio.run(rs.familia_world('', ''))
    assert not [p for p in saves if p.endswith('crews.json')]     # nothing moved → nothing written


def test_a_pinned_call_tops_the_street_for_an_hour():
    lines = [{'id': 'm1', 'text': 'CALL $WIF'}, {'id': 'm2', 'text': 'gm'}]
    v = sc.pin_view({'id': 'm1', 'by': '[SIC] Vito', 'at': 1000.0}, lines, 1600.0)
    assert v['text'] == 'CALL $WIF' and v['pinnedBy'] == '[SIC] Vito' and v['left'] == 3000
    assert sc.pin_view({'id': 'm1', 'at': 1000.0}, lines, 1000.0 + sc.PIN_SEC + 1) is None      # expired
    assert sc.pin_view({'id': 'gone', 'at': 1000.0}, lines, 1100.0) is None and sc.pin_view(None, lines, 1.0) is None
    assert sc.can_pin(True, False) and sc.can_pin(False, True) and not sc.can_pin(False, False)
