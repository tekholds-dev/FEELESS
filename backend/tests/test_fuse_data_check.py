"""🩺 Slice 34 — Fuse data check + the owner's Restart (owner 2026-11-20: "Fuse cards restart when inaccurate").
A card is flagged when its numbers rest on bad or missing data (each flag says since when); the OWNER restarts its RECORD from what it is
worth now — no coin, cash, payout or round is touched, the old record stays in its history. Network faked; nothing real is read or written."""
import asyncio
import pytest
import arena_prime as ap


def card(**kw):
    base = {'id': 'c1', 'tpl': 'balanced', 'label': 'Balanced', 'at': 100.0, 'startUsd': 20.0, 'dayStartUsd': 20.0, 'roundStartUsd': 20.0, 'dayAt': 100.0,
            'cash': 2.0, 'walletUsd': 1.0, 'lastRotateAt': 900.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0, 'feesUsd': 0.0, 'rounds': 7, 'roundWins': 3, 'putInUsd': 20.0, 'lowPct': -12.0, 'events': [],
            'legs': [{'mint': 'a', 'pairAddress': 'Pa', 'symbol': 'AAA', 'role': 'pool', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0, 'at': 150.0},
                     {'mint': 'b', 'pairAddress': 'Pb', 'symbol': 'BBB', 'role': 'runner', 'entry': 2.0, 'units': 4.0, 'costUsd': 8.0, 'at': 400.0}],
            'days': [{'at': 300.0, 'pct': 4.0}], 'runs': []}
    return {**base, **kw}


def test_a_clean_card_passes():
    out = ap.audit(card(), {'Pa': 1.1, 'Pb': 2.2})
    assert out == {'bad': False, 'since': None, 'flags': []}


def test_a_coin_with_no_live_price_is_flagged_as_missing_now():
    out = ap.audit(card(), {'Pa': 1.1})
    assert out['bad'] and [f['k'] for f in out['flags']] == ['no-price'] and out['since'] is None and '$BBB' in out['flags'][0]['why'] and 'right now' in out['flags'][0]['why']
    # a reserved (placeholder) seat has no coin yet: never flagged
    c = card(); c['legs'][1]['placeholder'] = True
    assert not ap.audit(c, {'Pa': 1.1})['bad']


def test_impossible_record_lines_no_start_and_a_broken_low_are_flagged():
    c = card(startUsd=0, lowPct=-140.0, runs=[{'at': 250.0, 'startUsd': 30.09, 'endUsd': 13032.4, 'pct': 43209.52, 'fixed': True}],
             days=[{'at': 200.0, 'pct': 88173.68}, {'at': 300.0, 'pct': 5.0}, {'at': 350.0, 'pct': -100.0}])
    out = ap.audit(c, {'Pa': 1, 'Pb': 2})
    ks = [f['k'] for f in out['flags']]
    assert ks == ['no-start', 'impossible', 'low'] and out['since'] == 100.0
    imp = out['flags'][1]
    assert imp['since'] == 200.0 and '2 record lines show' in imp['why'] and '+43210%' in imp['why']   # −100% exactly is possible, not flagged


def test_a_real_card_far_from_its_confirmed_book_is_flagged():
    c = card(real=True)
    v = ap.value(c, {'Pa': 1, 'Pb': 2})
    assert not ap.audit(c, {'Pa': 1, 'Pb': 2}, true_usd=v * 1.1)['bad']                 # 10% apart: fine
    out = ap.audit(c, {'Pa': 1, 'Pb': 2}, true_usd=v * 1.5)
    assert [f['k'] for f in out['flags']] == ['book-gap'] and 'apart' in out['flags'][0]['why']


def test_restart_starts_a_fresh_record_and_never_touches_the_money():
    c = card(days=[{'at': 200.0, 'pct': 88173.68}], runs=[{'at': 250.0, 'startUsd': 30.09, 'endUsd': 13032.4, 'pct': 43209.52}])
    out = ap.restart_record(c, 25.0, 1000.0, why='day lines from a broken price feed')
    # the money is exactly where it was
    for k in ('legs', 'cash', 'walletUsd', 'rounds', 'putInUsd'):
        assert out[k] == c[k], k
    assert ap.value(out, {'Pa': 1, 'Pb': 2}) == ap.value(c, {'Pa': 1, 'Pb': 2})
    # the record starts fresh from what it is worth NOW
    assert (out['startUsd'], out['dayStartUsd'], out['roundStartUsd'], out['lowPct'], out['days'], out['roundWins'], out['restartedAt']) == (25.0, 25.0, 25.0, 0.0, [], 0, 1000.0)
    # the old record is kept, and the restart is a closed run + an event
    h = out['history'][-1]
    assert h['restarted'] and h['by'] == 'owner' and h['startUsd'] == 20.0 and h['endUsd'] == 25.0 and h['pct'] == 25.0 and h['days'] == c['days'] and h['lowPct'] == -12.0
    assert out['runs'][-1] == {'at': 1000.0, 'startUsd': 20.0, 'endUsd': 25.0, 'pct': 25.0, 'restarted': True}
    assert out['events'][-1]['kind'] == 'restart' and 'broken price feed' in out['events'][-1]['why']
    assert c['days'] and c['events'] == [] and 'history' not in c                         # the input card is never mutated
    # the lines before the restart are judged no more → the card reads clean
    assert not ap.audit(out, {'Pa': 1, 'Pb': 2})['bad']
    with pytest.raises(ValueError):
        ap.restart_record(c, 0, 1000.0)
    assert 'floorBaseUsd' not in ap.restart_record({**c, 'floorBaseUsd': 30.0}, 20.0, 1000.0)   # the floor follows the new start
    legacy = card(runs=[{'startUsd': 1, 'endUsd': 600, 'pct': 59900.0}])                          # a line with no 'at' is still judged
    assert [f['k'] for f in ap.audit(legacy, {'Pa': 1, 'Pb': 2})['flags']] == ['impossible']
    # a real card's run is measured from the restart, not its first funding
    assert ap.restart_record(card(real=True), 25.0, 1000.0)['realBaselineAt'] == 1000.0 and 'realBaselineAt' not in out


def test_the_summary_still_carries_the_record_after_a_restart():
    out = ap.restart_record(card(), 25.0, 1000.0)
    sm = ap.summary(out, {'Pa': 1, 'Pb': 2})
    assert sm['lowPct'] == 0.0 and sm['days'] == [] and sm['runs'][-1]['restarted'] and sm['math']['putIn'] == 20.0   # put in never moves


class Rq:
    def __init__(self, b): self.b = b
    async def json(self): return self.b


def test_restart_route_is_owner_only_and_refuses_bad_starts(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    calls = {'owner': 0}
    def owner(r):
        calls['owner'] += 1; return 'OWNER'
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN'); monkeypatch.setattr(rs, '_require_owner', owner)
    async def prices(rows): return {'Pa': 1.0, 'Pb': 2.0}
    async def view(): return []
    monkeypatch.setattr(rs, '_hq_prices', prices); monkeypatch.setattr(rs, '_prime_view', view)
    bad = card(days=[{'at': 200.0, 'pct': 88173.68}])
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {}, 'cards': {'balanced': bad}}})
    out = asyncio.run(rs.fuse_prime_admin(Rq({'restart': {'tpl': 'balanced', 'why': 'broken feed'}})))
    saved = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']['cards']['balanced']
    assert calls['owner'] == 1 and out['ok'] and saved['startUsd'] == ap.value(bad, {'Pa': 1, 'Pb': 2}) and saved['legs'] == bad['legs'] and saved['cash'] == bad['cash']
    assert saved['history'][-1]['why'] == 'broken feed' and not ap.audit(saved, {'Pa': 1, 'Pb': 2})['bad']
    # a paper coin with no live price: refused (restarting from its entry would carry the wrong number into the new record)
    async def half(rows): return {'Pa': 1.0}
    monkeypatch.setattr(rs, '_hq_prices', half)
    with pytest.raises(rs.HTTPException) as e:
        asyncio.run(rs.fuse_prime_admin(Rq({'restart': {'tpl': 'balanced'}})))
    assert '$BBB' in str(e.value.detail)
    # a real card restarts from the wallet's CONFIRMED book — and waits while that book is settling
    monkeypatch.setattr(rs, '_hq_prices', prices)
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {}, 'cards': {'degen': card(tpl='degen', real=True)}}})
    monkeypatch.setattr(rs, '_fw_peek', lambda: {'books': {'degen': {'pending': True}}})
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuse_prime_admin(Rq({'restart': {'tpl': 'degen'}})))
    async def sol(): return 150.0
    monkeypatch.setattr(rs, '_fw_peek', lambda: {'books': {'degen': {'x': 1}}}); monkeypatch.setattr(rs, '_sol_usd_live', sol)
    monkeypatch.setattr(rs._fw, 'book_value', lambda b, px, s: 31.5)
    monkeypatch.setattr(rs._fw, 'held_units', lambda b, m: 5.0)
    monkeypatch.setattr(rs, '_fw_peek', lambda: {'books': {'degen': {'legs': {'mX': {'pair': 'PX', 'symbol': 'GONE'}}}}})
    with pytest.raises(rs.HTTPException) as e2:                                                     # a held book coin with no price: refused
        asyncio.run(rs.fuse_prime_admin(Rq({'restart': {'tpl': 'degen'}})))
    assert '$GONE' in str(e2.value.detail)
    monkeypatch.setattr(rs, '_fw_peek', lambda: {'books': {'degen': {'legs': {'mA': {'pair': 'Pa', 'symbol': 'AAA'}}}}})
    asyncio.run(rs.fuse_prime_admin(Rq({'restart': {'tpl': 'degen'}})))
    r = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']['cards']['degen']
    assert r['startUsd'] == 31.5 and r['realBaselineAt'] == r['restartedAt'] and r['legs'] == card()['legs']
    # not the owner → nothing changes
    def no(r): raise rs.HTTPException(403, 'owner only')
    monkeypatch.setattr(rs, '_require_owner', no)
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuse_prime_admin(Rq({'restart': {'tpl': 'degen'}})))
    assert rs._json_load(rs.FUSE_HQ_PATH, {})['prime']['cards']['degen'] == r
