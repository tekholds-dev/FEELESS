import pytest
import collective_pool as _pool_mod
_POOL_DEFAULTS = _pool_mod.DEFAULTS
"""🪙 The Pool ledger: the owner's worked example, and the rule that it can never owe more than is really there."""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collective_pool as cp

D = 86400
SOL = 100.0
USDC = cp.UNITS['USDC']


def held(s, t):
    """Everything inside the ledger for one token."""
    return s['books'][t]['keep'] + cp.backed(s, t)


def run(s, start, days, step=3600):
    t = start
    for _ in range(int(days * D / step)):
        t += step
        cp.tick(s, t, SOL)
    return t


@pytest.fixture(autouse=True)
def _old_plans(monkeypatch):
    monkeypatch.setitem(_POOL_DEFAULTS, 'deal', 'plans')


def test_one_key_moves_money_once():
    s = cp.new_state()
    assert cp.income(s, 'dep1', 'USDC', 5 * USDC, 'deposit') is True
    assert cp.income(s, 'dep1', 'USDC', 5 * USDC, 'deposit') is False
    assert cp.send(s, 'sig', 'a', 'o', 'SOL', 10**9, 100, 1)
    assert cp.send(s, 'sig', 'a', 'o', 'SOL', 10**9, 100, 1) is None
    assert s['books']['USDC']['keep'] + s['books']['USDC']['pot'] == 5 * USDC
    assert s['agents']['a']['sent']['SOL'] == 10**9


def test_nobody_locked_means_the_pot_just_waits():
    s = cp.new_state(); s['at'] = 1
    cp.income(s, 'fee', 'USDC', 100 * USDC, 'txn')
    pot0 = s['books']['USDC']['pot']
    run(s, 1, 10)
    assert s['books']['USDC']['pot'] == pot0


def test_owner_cap_holds_once_there_are_enough_owners():
    s = cp.new_state(); s['at'] = 1
    for i in range(200):
        cp.send(s, f'k{i}', f'a{i}', f'o{i}', 'USDC', 10 * USDC, 10, 1)
    cp.send(s, 'whale', 'w', 'whale', 'USDC', 100000 * USDC, 100000, 1)
    part = cp.shares(s, SOL)
    assert abs(sum(part.values()) - 1) < 1e-6
    assert part['w'] <= 0.031


def test_two_agents_of_one_owner_count_as_one():
    s = cp.new_state(); s['at'] = 1
    for i in range(200):
        cp.send(s, f'k{i}', f'a{i}', f'o{i}', 'USDC', 10 * USDC, 10, 1)
    cp.send(s, 'w1', 'x1', 'whale', 'USDC', 50000 * USDC, 50000, 1)
    cp.send(s, 'w2', 'x2', 'whale', 'USDC', 50000 * USDC, 50000, 1)
    part = cp.shares(s, SOL)
    assert part['x1'] + part['x2'] <= 0.031


def test_config_is_bounded_and_keeps_its_order():
    c = cp.clean_cfg({'skimPct': 900, 'boostMode': 'x', 'potPct': 'nope', 'monthDays': 1})
    assert c['skimPct'] == 50 and c['monthDays'] == 14 and c['boostMode'] == 'payout' and c['potPct'] == 50


def test_trade_fee_slides_from_5_to_1_percent():
    c = cp.clean_cfg(None)
    assert cp.txn_fee_usd(c, 5) == (0.25, 5.0)
    assert cp.txn_fee_usd(c, 50) == (1.5, 3.0)
    assert cp.txn_fee_usd(c, 500) == (5.0, 1.0)


def test_chain_shortfall_is_caught():
    s = cp.new_state(); s['at'] = 1
    cp.send(s, 'k', 'a', 'o', 'USDC', 100 * USDC, 100, 1)
    assert cp.check_chain(s, {'USDC': 100 * USDC, 'SOL': 0}, 2)['short'] == []
    assert cp.check_chain(s, {'USDC': 10 * USDC, 'SOL': 0}, 2)['short'] == ['USDC']


def test_fuzz_money_in_always_equals_money_held_and_nothing_goes_negative():
    """Thousands of random fees, sends, hours and price swings. Not one unit may appear or vanish."""
    rng = random.Random(7)
    s = cp.new_state(); s['at'] = 1; t = 1; put = {'SOL': 0, 'USDC': 0}
    for i in range(6000):
        roll = rng.random(); tok = rng.choice(cp.TOKENS)
        if roll < 0.3:
            u = rng.randint(1, 5 * cp.UNITS[tok])
            if cp.income(s, f'f{i}', tok, u, rng.choice(('deposit', 'topup', 'txn', 'task', 'gift'))):
                put[tok] += u
        elif roll < 0.5:
            u = rng.randint(1, 3 * cp.UNITS[tok]); ag = rng.randint(0, 40)
            if cp.send(s, f's{i}', f'a{ag}', f'o{ag % 25}', tok, u, u / cp.UNITS[tok] * 100, t, rng.random(), None, rng.choice(cp.PLANS)):
                put[tok] += u
        else:
            t += rng.randint(60, 7200); cp.tick(s, t, rng.uniform(1, 500))
        if i % 97 == 0:
            s['cfg'] = cp.clean_cfg({**s['cfg'], 'potPct': rng.randint(0, 100), 'monthBack': rng.randint(50, 100), 'skimPct': rng.randint(0, 50)})
        for tk in cp.TOKENS:
            assert held(s, tk) == put[tk]
            assert s['books'][tk]['pot'] >= 0 and s['books'][tk]['keep'] >= 0
        assert all(v >= 0 for a in s['agents'].values() for b in ('locked', 'owed', 'vault') for v in a[b].values())


def test_no_new_money_means_the_count_slows_but_stays_covered():
    s = cp.new_state(); s['at'] = 1
    for i in range(50):
        cp.send(s, f'k{i}', f'a{i}', f'o{i}', 'USDC', 20 * USDC, 20, 1)
    cp.income(s, 'fees', 'USDC', 1000 * USDC, 'txn')
    t = run(s, 1, 5, 86400)
    r1 = cp.totals(s, SOL)['ratePerSecUsd']
    run(s, t, 200, 86400)
    assert cp.totals(s, SOL)['ratePerSecUsd'] < r1 / 10
    assert held(s, 'USDC') == 2000 * USDC


def test_file_update_is_atomic_and_a_failed_change_writes_nothing(tmp_path):
    p = tmp_path / 'pool.json'
    cp.update(p, lambda s: cp.income(s, 'a', 'USDC', 100, 'txn'))
    assert cp.load(p)['books']['USDC']['keep'] == 50

    def boom(s):
        cp.income(s, 'b', 'USDC', 100, 'txn')
        raise ValueError('no')
    try:
        cp.update(p, boom)
    except ValueError:
        pass
    assert cp.load(p)['books']['USDC']['keep'] == 50


def test_a_closed_proof_keeps_its_best_two_snapshots_after_14_days():
    import agent_print as ap
    shots = [{'file': f'{i}.jpg', 'site': 'dex' if i < 3 else 'rug', 'mint': 'M' if i else 'X', 'at': i} for i in range(5)]
    f = {'status': 'closed', 'mint': 'M', 'soldAt': 0, 'shots': list(shots)}
    assert ap.clean_shots(f, 13 * D) == [] and len(f['shots']) == 5                       # too soon
    assert ap.clean_shots({**f, 'status': 'open'}, 99 * D) == []                          # an open proof is never touched
    gone = ap.clean_shots(f, 15 * D)
    assert [s['file'] for s in f['shots']] == ['4.jpg', '2.jpg'] and len(gone) == 3       # the picked coin, two different sites


def test_a_pob_with_no_topic_picks_the_strongest_games_of_the_first_sport_that_has_any(monkeypatch):
    import asyncio
    import proof_tools as pt
    async def bids(http, sport):
        return {'legs': [{'pick': 'KC to beat DEN'}, {'pick': 'BUF to beat NYJ'}, {'pick': 'SF to beat SEA'}, {'pick': 'x'}]} if sport == 'nba' else {'legs': []}
    monkeypatch.setattr(pt, 'bids', bids)
    assert asyncio.run(pt.best_topic(None)) == 'best NBA picks: KC to beat DEN, BUF to beat NYJ, SF to beat SEA'
    async def none(http, sport):
        return {'legs': []}
    monkeypatch.setattr(pt, 'bids', none)
    assert asyncio.run(pt.best_topic(None)) == ''


def test_not_a_ponzi_no_members_money_can_ever_reach_the_pot():
    """Deposits, top-ups, sends, what a send keeps and what releases all stay out of the pot. Only fees on real activity go in."""
    s = cp.new_state(); s['at'] = 1
    for i, k in enumerate(('deposit', 'topup', 'proofs', 'release', 'gift', 'pass')):
        cp.income(s, f'k{i}', 'USDC', 100 * USDC, k)
    cp.send(s, 'send', 'a', 'o', 'USDC', 100 * USDC, 100, 1)
    run(s, 1, 100)                                                            # what it does not get back goes round too
    assert s['books']['USDC']['pot'] == 0 and s['agents']['a']['earned']['USDC'] == 0
    cp.income(s, 'real', 'USDC', 100 * USDC, 'txn')
    assert s['books']['USDC']['pot'] == 50 * USDC


def test_with_new_people_stopped_members_still_earn_while_members_trade():
    s = cp.new_state(); s['at'] = 1
    for i in range(10):
        cp.send(s, f's{i}', f'a{i}', f'o{i}', 'USDC', 20 * USDC, 20, 1)
    t = 1
    for d in range(60):
        cp.income(s, f'day{d}', 'USDC', 5 * USDC, 'txn')
        t = run(s, t, 1)
    assert s['agents']['a0']['earned']['USDC'] > 0
    assert held(s, 'USDC') == 200 * USDC + 300 * USDC


def test_an_edited_ledger_refuses_to_load_and_never_resets(tmp_path):
    p = tmp_path / 'pool.json'
    cp.update(p, lambda s: cp.income(s, 'a', 'USDC', 100, 'txn'))
    assert p.read_bytes().startswith(b'FP1:') and b'keep' not in p.read_bytes()    # sealed, nothing readable
    raw = bytearray(p.read_bytes()); raw[20] ^= 1; p.write_bytes(bytes(raw))
    with pytest.raises(cp.Tampered):
        cp.load(p)
    with pytest.raises(cp.Tampered):
        cp.update(p, lambda s: None)


def test_the_chain_counts_every_dollar_and_catches_a_cut_link(tmp_path):
    p = tmp_path / 'pool.json'
    cp.update(p, lambda s: cp.income(s, 'a', 'USDC', 100, 'txn'))
    cp.update(p, lambda s: cp.send(s, 'b', 'x', 'o', 'USDC', 50 * USDC, 50, 1))
    cp.update(p, lambda s: cp.income(s, 'c', 'SOL', 7, 'deposit'))
    cp.update(p, lambda s: (s.update(at=1), cp.tick(s, 90 * D, SOL)))
    r = cp.audit(p)
    assert r['ok'] and r['links'] == 3
    trail = p.with_suffix('.trail'); rows = trail.read_bytes().splitlines()
    trail.write_bytes(b'\n'.join(rows[:1] + rows[2:]) + b'\n')                   # someone removes a dollar
    r = cp.audit(p)
    assert not r['ok'] and 'match' in r['why']


def test_a_print_seed_is_stable_unique_and_cannot_be_chosen():
    a, b = cp.print_seed('agent1'), cp.print_seed('agent2')
    assert a == cp.print_seed('agent1') and a != b and len(a) == 32


def test_a_key_stays_spent_forever_even_after_a_hundred_thousand_more():
    s = cp.new_state()
    assert cp.income(s, 'first', 'USDC', 5, 'txn')
    for i in range(100_000):
        s['seen'][f'x{i}'] = 1
    assert cp.income(s, 'first', 'USDC', 5, 'txn') is False
    legacy = {**cp.new_state(), 'seen': ['old']}
    assert cp.income(legacy, 'old', 'USDC', 5, 'txn') is False and cp.income(legacy, 'new', 'USDC', 5, 'txn') is True


def test_a_plan_says_exactly_how_much_comes_back_and_by_when():
    s = cp.new_state(); s['at'] = 1; s['cfg']['potPct'] = 0
    r = cp.send(s, 'k', 'a', 'o', 'USDC', 10 * USDC, 10, 1, 0, None, 'month')
    assert r['keptUnits'] == 2 * USDC and r['lockedUnits'] == 8 * USDC and r['backUnits'] == int(6.8 * USDC) and r['end'] == 1 + 30 * D
    run(s, 1, 15)
    a = s['agents']['a']
    assert abs(a['owed']['USDC'] / (6.8 * USDC) - 0.5) < 0.01                     # halfway, half back
    run(s, 1 + 15 * D, 16)
    assert a['owed']['USDC'] == int(6.8 * USDC) and a['locked']['USDC'] == 0      # to the unit, on its date
    assert held(s, 'USDC') == 10 * USDC


def test_each_plan_trades_money_back_for_a_bigger_part_of_the_pot():
    c = cp.clean_cfg(None); pl = {n: cp.plan_of(c, n) for n in cp.PLANS}
    assert [pl[n]['backPct'] for n in cp.PLANS] == [70, 85, 95, 0] and [pl[n]['weightX'] for n in cp.PLANS] == [1, 2, 3, 6]
    assert cp.plan_of(c, 'month', 1)['backPct'] == 90 and cp.plan_of(c, 'vault', 1)['backPct'] == 0 and cp.plan_of({**c, 'boostMode': 'rank'}, 'month', 1)['backPct'] == 85


def test_the_vault_never_comes_back_and_never_counts_as_owed():
    s = cp.new_state(); s['at'] = 1; s['cfg']['potPct'] = 0
    cp.send(s, 'k', 'a', 'o', 'USDC', 10 * USDC, 10, 1, 0, None, 'vault')
    run(s, 1, 400, 86400)
    a = s['agents']['a']
    assert a['owed']['USDC'] == 0 and a['locked']['USDC'] == 0 and a['vault']['USDC'] == 8 * USDC and s['books']['USDC']['keep'] == 10 * USDC and cp.backed(s, 'USDC') == 0


def test_a_vault_claim_fades_so_getting_here_first_is_not_the_edge():
    s = cp.new_state(); s['at'] = 1
    cp.send(s, 'old', 'old', 'o1', 'USDC', 10 * USDC, 10, 1, 0, None, 'vault')
    s['at'] = 180 * D
    cp.send(s, 'new', 'new', 'o2', 'USDC', 10 * USDC, 10, 180 * D, 0, None, 'vault')
    part = cp.shares(s, SOL)
    assert part['new'] > part['old'] * 3


def test_fee_share_is_paid_into_earnings_from_real_money_only():
    s = cp.new_state(); s['at'] = 1
    cp.send(s, 'sig', 'a', 'o', 'USDC', 100 * USDC, 100, 1)
    cp.income(s, 'fee', 'USDC', 100 * USDC, 'txn')
    pot0 = s['books']['USDC']['pot']
    run(s, 1, 1)
    a = s['agents']['a']
    assert 0 < a['earned']['USDC'] <= pot0 and a['owed']['USDC'] >= a['earned']['USDC'] and held(s, 'USDC') == 200 * USDC


def test_the_earn_limit_stops_a_small_sender_draining_a_rich_pot():
    s = cp.new_state(); s['at'] = 1
    cp.send(s, 'sig', 'a', 'o', 'USDC', 10 * USDC, 10, 1)
    cp.income(s, 'fee', 'USDC', 100000 * USDC, 'txn')
    run(s, 1, 90)
    assert s['agents']['a']['earned']['USDC'] <= 2 * 10 * USDC + 1


def test_points_scale_with_dollars_and_the_prints_strength():
    c = cp.clean_cfg(None)
    assert cp.points_for(c, 10, 50) == 25 and cp.points_for(c, 10, 100) == 37.5 and cp.points_for(c, 10, 0) == 12.5
    assert cp.points_for(c, 10000, 50) == 60                                       # a limit per send: big money cannot buy the top


def test_a_boost_fades_and_real_strength_grades_it():
    now = 100 * D
    assert cp.boost_of([{'pts': 100, 'at': now}], 100, now) == 1.0 and cp.boost_of([{'pts': 100, 'at': now}], 0, now) == 0.5
    assert abs(cp.boost_of([{'pts': 100, 'at': now - 60 * D}], 100, now) - 0.5) < 0.001
    assert cp.levers(cp.clean_cfg(None), 1) == {'backPlus': 5.0, 'weightX': 2.0} and cp.levers({**cp.clean_cfg(None), 'boostMode': 'rank'}, 1) == {'backPlus': 0.0, 'weightX': 1.0}


def test_points_bring_a_date_closer_and_only_points_it_has():
    s = cp.new_state(); s['at'] = 1
    r = cp.send(s, 'k', 'a', 'o', 'USDC', 10 * USDC, 10, 1, 0, None, 'month')
    end0 = r['end']
    out = cp.spend_points(s, 'a', r['id'], 20, 25, 1)                               # 10 points = a day
    assert out['days'] == 2 and out['end'] == end0 - 2 * D and s['agents']['a']['spent'] == 20
    with pytest.raises(ValueError):
        cp.spend_points(s, 'a', r['id'], 20, 25, 1)                                 # only 5 left
    cp.spend_points(s, 'a', r['id'], 5000, 9999, 1)
    row = s['agents']['a']['streams'][0]
    assert row['end'] >= 1 + 10 * D - 1                                             # never under a third of the plan
    v = cp.send(s, 'v', 'a', 'o', 'USDC', 10 * USDC, 10, 1, 0, None, 'vault')
    with pytest.raises(ValueError):
        cp.spend_points(s, 'a', v['id'], 1, 9999, 1)


def test_a_view_shows_the_date_the_amount_and_counts_up():
    s = cp.new_state(); s['at'] = 1000
    cp.send(s, 'k', 'a', 'o', 'USDC', 10 * USDC, 10, 1000, 0, {'name': 'PoW 1'}, 'month')
    a, b = cp.view(s, 'a', 1000, SOL), cp.view(s, 'a', 1030, SOL)
    assert 2.5e-6 < a['ratePerSecUsd'] < 2.7e-6 and b['owedUsd'] > a['owedUsd']
    assert a['streams'][0]['backUsd'] == 6.8 and a['streams'][0]['end'] == 1000 + 30 * D and a['nextEnd'] == 1000 + 30 * D and a['backLeftUsd'] == 6.8
    assert cp.view(s, 'nobody', 1000, SOL)['empty'] is True


def test_print_strength_needs_real_results_and_enough_of_them():
    import agent_print as ap
    f = lambda v: {'status': 'closed', 'pnlPct': v, 'soldAt': 100 * D}
    assert ap.strength({}, 100 * D) == 0
    assert ap.strength({'powFolders': [f(60)]}, 100 * D) == 10                        # one big win proves little
    assert ap.strength({'powFolders': [f(60)] * 10}, 100 * D) == 100
    assert ap.strength({'powFolders': [f(-60)] * 10}, 100 * D) == 0
    assert ap.strength({'pocFolders': [{'graded': 'right', 'at': 100 * D}] * 10}, 100 * D) == 85


def test_the_stash_keeps_everything_once_sealed_and_compressed(tmp_path):
    import collective_stash as st
    import io as _io
    from PIL import Image
    buf = _io.BytesIO(); Image.new('RGB', (1600, 900), (20, 40, 90)).save(buf, 'JPEG', quality=95); raw = buf.getvalue()
    folder = {'id': 'w1', 'status': 'closed', 'sym': 'BONK', 'pnlPct': -12, 'soldAt': 10, 'usedBy': {'M': ['dexscreener.com', 'rugcheck.xyz']}, 'shots': [{'file': 'a.jpg', 'site': 'dexscreener.com'}, {'file': 'sealed.jpg', 'site': 'pump.fun'}], 'email': 'x@y.com'}
    cat = {'id': 'c1', 'powFolders': [folder, {'id': 'open', 'status': 'buy'}], 'pocFolders': [{'id': 'p1', 'status': 'closed', 'graded': 'right', 'topic': 'memes', 'at': 5}]}
    safe = lambda f: {k: v for k, v in f.items() if k != 'email'}
    shot = lambda f, s: raw if s['file'] == 'a.jpg' else None                           # a signed-in site's picture never gets in
    assert st.ingest_cat(tmp_path, cat, safe, shot) >= 4
    assert st.ingest_cat(tmp_path, cat, safe, shot) == 0                                # once
    s = st.stats(tmp_path); w = st.web(tmp_path)
    assert s['outcomes']['lost'] >= 1 and s['categories']['Trades'] >= 1 and s['categories']['Content'] == 1 and s['categories']['Snapshots'] == 1  # losers are kept too
    assert {x['id'] for x in w['sources']} >= {'dexscreener.com', 'rugcheck.xyz'} and 'pump.fun' not in {x['id'] for x in w['sources'] if x['id'] == 'pump.fun' and False}
    body = st.read(tmp_path, 'powFolders:w1')
    assert b'BONK' in body and b'x@y.com' not in body                                    # private fields never stored
    assert st.read(tmp_path, 'shot:w1:sealed.jpg') is None
    img = st.read(tmp_path, 'shot:w1:a.jpg'); assert Image.open(_io.BytesIO(img)).width == 1280 and len(img) < len(raw)
    blobs = list((tmp_path / 'blobs').rglob('*')); assert all(b'BONK' not in b.read_bytes() for b in blobs if b.is_file())  # sealed on disk


def test_a_snapshot_boxes_only_what_is_really_on_the_page():
    import asyncio
    import evidence_marks as em
    import io as _io
    from PIL import Image
    buf = _io.BytesIO(); Image.new('RGB', (400, 300), (255, 255, 255)).save(buf, 'JPEG'); raw = buf.getvalue()
    class P:
        url = 'https://x.dev'
        async def shot(self): return raw
        async def find_private(self, js): return {'rects': [[10, 10, 100, 30]], 'found': {'solana': 1}, 'w': 400, 'h': 300}
    r = asyncio.run(em.marked_shot(P(), ['solana', 'ethereum'], 5))
    assert r['found'] == {'solana': 1} and r['missing'] == ['ethereum'] and r['jpg'] != raw and len(r['sha']) == 32
    px = Image.open(_io.BytesIO(r['jpg'])).convert('RGB').getpixel((10, 20)); assert px[1] > px[0]   # the box is drawn green
    assert em.words_of(['Solana ETF approved today']) == ['approved', 'solana', 'today']


def test_marks_only_whole_words_and_the_free_browser_says_nothing_when_none_is_installed(monkeypatch):
    import asyncio
    import evidence_marks as em
    import free_browser as fb
    assert 'edge(low[i - 1])' in em.FIND_JS
    monkeypatch.setattr(fb, 'chromium_path', lambda: None)
    assert asyncio.run(fb.shots(['https://x.dev'], [], 1)) == []


def test_the_stash_opens_safely_from_many_threads_at_once(tmp_path):
    import collective_stash as st
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda _: st.stats(tmp_path)['items'], range(24)))
    assert rows == [0] * 24


def test_boost_dollars_are_what_the_boost_really_added():
    s = cp.new_state(); s['at'] = 1; s['cfg']['potPct'] = 0
    cp.send(s, 'a', 'x', 'o', 'USDC', 100 * USDC, 100, 1, 0, None, 'month')
    cp.send(s, 'b', 'y', 'p', 'USDC', 100 * USDC, 100, 1, 1, None, 'month')
    run(s, 1, 31, 86400)
    x, y = cp.view(s, 'x', 31 * D, SOL), cp.view(s, 'y', 31 * D, SOL)
    assert x['boostUsd'] == 0 and abs(y['boostUsd'] - 4) < 0.01 and y['owedUsd'] - x['owedUsd'] == pytest.approx(4, abs=0.01)     # 5% of $80


def test_outside_money_all_reaches_the_pot_and_member_money_cannot():
    s = cp.new_state()
    cp.income(s, 'a', 'USDC', 100 * USDC, 'site'); assert s['books']['USDC']['pot'] == 100 * USDC
    assert cp.site_owed(cp.clean_cfg(None), 100, 5) == 15 and cp.site_owed(cp.clean_cfg(None), 100, 50) == 0


def test_a_held_proof_earns_nothing_until_the_owner_clears_it():
    s = cp.new_state(); s['at'] = 1
    r = cp.send(s, 'k', 'a', 'o', 'USDC', 10 * USDC, 10, 1, 0, {'held': True}, 'month')
    cp.send(s, 'k2', 'b', 'p', 'USDC', 10 * USDC, 10, 1, 0, None, 'month')
    assert 'a' not in cp.shares(s, SOL) and 'b' in cp.shares(s, SOL)
    assert cp.clear_review(s, 'a', r['id']) is True and 'a' in cp.shares(s, SOL) and cp.clear_review(s, 'a', r['id']) is False


def test_five_validators_catch_what_each_one_is_for():
    import proof_validators as v
    f = {'real': True, 'status': 'closed', 'sol': 1.0, 'pnlSol': 0.8, 'pnlPct': 80, 'at': 10, 'boughtAt': 100, 'soldAt': 4000, 'shots': [{'found': ['x']}]}
    r = v.review(f, 'S', 0.1, '', (), 5000)
    assert r['ok'] and [x['name'] for x in r['seats']] == ['Tally', 'Sherlock', 'Devil', 'Archivist', 'Judge'] and all(x['ok'] for x in r['seats'])
    def says(**kw):
        out = v.review({**f, **{k: w for k, w in kw.items() if k not in ('sent', 'block', 'seen')}}, 'S', kw.get('sent', 0.1), kw.get('block', ''), kw.get('seen', ()), 5000)
        return out['ok'], [x['name'] for x in out['seats'] if not x['ok']]
    assert says(pnlPct=500) == (False, ['Tally', 'Judge'])                 # numbers that do not add up
    assert says(sent=0.5) == (False, ['Tally', 'Judge'])                   # sent more than 25% of its profit
    assert says(shots=[]) == (False, ['Sherlock', 'Judge'])                # nothing to show
    assert says(soldAt=130) == (False, ['Devil', 'Judge'])                 # a 30 second flip
    assert says(block='thin pool') == (False, ['Devil', 'Judge'])
    assert says(seen=('S',)) == (False, ['Archivist', 'Judge'])            # the same transaction twice
    assert says(real=False) == (False, ['Archivist', 'Judge'])


def test_desk_buys_off_is_kept_by_the_card_settings_and_defaults_off():
    import arena_prime as ap
    assert ap.clean_cfg({})['deskBuysOff'] is False and ap.clean_cfg({'deskBuysOff': True})['deskBuysOff'] is True


def test_every_door_the_desk_buys_through_checks_the_switch():
    src = (Path(__file__).resolve().parents[1] / 'reputation_service.py').read_text()
    assert "if (cfg_t.get('agentFeed') or cfg_t.get('agentLearn')) and not cfg_t.get('deskBuysOff'):" in src                         # GO rows into the engine
    assert "if x['action'] == 'swap' and (paper_ or cfg_t.get('deskBuysOff')):" in src                                                # a switch into a new coin
    assert "g4_seat_ = not cfg_t.get('deskBuysOff') and" in src                                                                       # OSSY and G4's seat
    assert "if cfg_t.get('deskBuysOff'):   # ⚖ the last door" in src                                                                  # the seat fills


def test_the_calculator_is_the_real_pool_code():
    """🧮 What a viewer sees is the real send() and tick(), run forward on a throwaway state. Sent money never reads as profit without real fees."""
    import collective_pool as cp
    cfg = cp.clean_cfg(None)
    none = cp.project(cfg, 10, 'month')
    assert none['pot'] == 0 and none['back'] == 6.8 and none['profit'] == -3.2 and none['breakEven'] is None
    some = cp.project(cfg, 10, 'month', fees_day=100, others_usd=10000); more = cp.project(cfg, 10, 'quarter', fees_day=1000, others_usd=10000)
    assert 0 < some['pot'] < more['pot'] and more['profit'] > 0 and more['breakEven'] and more['series'][more['breakEven']]['back'] + more['series'][more['breakEven']]['pot'] >= 10
    crowded = cp.project(cfg, 10, 'month', fees_day=100, others_usd=1000000)
    assert crowded['pot'] < some['pot']   # more people sharing, a smaller part
    vault = cp.project(cfg, 10, 'vault', fees_day=0)
    assert vault['back'] == 0 and vault['profit'] == -10


def test_growth_shows_more_trading_helps_and_more_senders_split_it():
    """🌱 The picture the owner asked for, on the real pool code: swaps fill the pot, senders split it, and no fees means short."""
    import collective_pool as cp
    cfg = cp.clean_cfg(None)
    g = cp.growth(cfg, send=20, plan='month', volume_day=0, sender_pct=100)
    first, last = g['rows'][0], g['rows'][-1]
    assert first['s1000'] == -6.4   # nothing but the plan: $13.60 back on $20
    assert last['s1000'] > first['s1000'] and g['rows'][2]['s100'] >= g['rows'][2]['s10000']   # more swaps help; more senders split them
    assert g['roomX'] == cfg['monthRoom']

