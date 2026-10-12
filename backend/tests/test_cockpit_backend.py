"""Part B backend: market-cap supply, the decision tape, owner coin review. Pure — no network, no money."""
import pytest

import owner_review as owr
import trench_kernel.brain as brain
import trench_kernel.kernel as tk
import trench_kernel.supply as sup
import trench_kernel.tape as tape
from kernel_helpers import row

PUMP = 'So1anaCoinMint1111111111111111111111111pump'
PLAIN = 'So1anaCoinMint11111111111111111111111111zzz'


# ── 📊 supply → market cap ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_supply_is_resolved_in_order_and_never_invented():
    assert sup.resolve(PLAIN, 0.002, 400_000, known=250_000_000) == (250_000_000.0, 'token')          # a reliable token supply wins over the cap
    assert sup.resolve(PUMP, 0.00002, 19_000) == (1e9, 'launchpad')                                   # Pump / Bonk mint exactly 1B
    assert sup.resolve(PLAIN, 0.002, 400_000) == (200_000_000.0, 'market')                            # live cap ÷ live price
    assert sup.resolve(PLAIN, 0.002, None) == (None, None)                                            # nothing known → unavailable, never a guess
    assert sup.resolve(PLAIN, None, 400_000) == (None, None)
    assert sup.resolve(PLAIN, 0.002, 404_000, prev=(200_000_000.0, 'market')) == (200_000_000.0, 'market')   # a 1% wobble keeps the supply (the chart must not jump)
    assert sup.resolve(PLAIN, 0.002, 800_000, prev=(200_000_000.0, 'market'))[0] == 400_000_000.0            # a real change is taken
    assert sup.resolve(PLAIN, 0.002, 999, prev=(1e9, 'launchpad')) == (1e9, 'launchpad')                    # an exact source is never replaced by a ratio
    assert sup.resolve(PLAIN, None, None, prev=(5e8, 'market')) == (5e8, 'market')                           # a blank pass keeps the last good one


def test_market_cap_ohlc_is_the_price_ohlc_times_supply_and_unknown_supply_is_none():
    bar = [1700000000, 0.00002, 0.000025, 0.000018, 0.000024, 1234.5]
    assert sup.mc_bar(bar, 1e9) == [1700000000, 20000.0, 25000.0, 18000.0, 24000.0, 1234.5]            # volume untouched
    assert sup.mc_bar(bar, None) is None and sup.mc_bar(bar, 0) is None                                 # never the raw price
    assert sup.mc(0.0000184, 1e9) == 18400.0 and sup.mc(0.0000184, None) is None and sup.mc(None, 1e9) is None


def test_the_mint_state_carries_the_supply_and_the_kernel_view_speaks_market_cap():
    K = tk.Kernel()
    K.run([row(PUMP, px=0.0000184, mc=18_400), row(PLAIN, px=0.002, mc=None)], 100.0, {})
    assert K.store.mints[PUMP]['market']['supply'] == 1e9 and K.store.mints[PUMP]['market']['supplySrc'] == 'launchpad'
    assert K.store.mints[PLAIN]['market']['supply'] is None
    assert K.mc(PUMP) == 18_400.0 and K.mc(PLAIN) is None
    v = {x['mint']: x for x in K.view(100.0)['candidates']}
    assert PUMP in v and v[PUMP]['supply'] == 1e9 and v[PUMP]['price'] == 0.0000184 and v[PUMP]['supplySrc'] == 'launchpad'
    assert sup.mc(v[PUMP]['price'], v[PUMP]['supply']) == 18_400.0                                      # the page multiplies: price × supply
    if PLAIN in v:
        assert 'supply' not in v[PLAIN] and 'supplySrc' not in v[PLAIN]                                  # unknown = absent (the page says UNAVAILABLE), never 0


# ── 📜 the decision tape ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _dec(status, trig='WAIT', objs=(), size=1.0, rank=100.0, why='w'):
    return {'status': status, 'rank': rank, 'why': why, 'opinions': {'tally': {'fresh': '5–15m', 'vpm': 900, 'sources': 2}, 'trigger': {'state': trig, 'narrative': 'RUNNING', 'why': 'buyers lead'},
                                                                     'devil': {'objections': list(objs)}, 'warden': {'size': size, 'why': 'full size'}}}


def test_a_line_is_written_only_when_something_real_changed():
    ms = {'market': {'pace': 2.0, 'move5m': 4.0, 'volume5m': 5000}, 'chain': {}, 'research': {}}
    assert tape.diff(None, _dec('TRACKING'), ms) == []                                                  # never a candidate: nothing
    first = tape.diff(None, _dec('CONTENDING', 'ARM'), ms)
    assert [x[0] for x in first] == ['tally', 'trigger'] and first[0][1] == 'CANDIDATE' and first[1][1] == 'ARM'
    assert tape.diff(_dec('CONTENDING', 'ARM'), _dec('CONTENDING', 'ARM'), ms) == []                    # unchanged opinions: no line
    up = tape.diff(_dec('CONTENDING', 'ARM'), _dec('READY', 'ENTER', rank=150), ms)
    assert [(a, act) for a, act, _w, _k in up] == [('trigger', 'ENTER'), ('warden', 'SIZE ×1'), ('kernel', 'READY')]
    warn = tape.diff(_dec('READY', 'ENTER'), _dec('READY', 'ENTER', objs=[('identity', 'WARNING', 'no site')]), ms)
    assert [(a, act) for a, act, _w, _k in warn] == [('devil', 'WARNING')]                               # a Devil WARNING is a line, the coin stays READY
    veto = tape.diff(_dec('READY', 'ENTER'), _dec('TRACKING', 'NO', objs=[('wall', 'HARD_VETO', 'collapsing')]), ms)
    assert ('devil', 'HARD VETO') in [(a, act) for a, act, _w, _k in veto] and ('kernel', 'DROPPED TO TRACKING') in [(a, act) for a, act, _w, _k in veto]
    surge = tape.diff(_dec('CONTENDING', 'ARM'), _dec('CONTENDING', 'ARM'), ms, events=('volume',), now=1000.0)
    assert surge[0][:2] == ('tally', 'SURGE')
    assert tape.diff(None, _dec('TRACKING', 'NO'), ms, owner=True)[0][0] == 'trigger'                   # a coin the owner asked about is traced even behind the wall


def test_the_tape_is_ordered_bounded_and_never_repeats_an_unchanged_line():
    T = tape.Tape(keep=5)
    a = T.add('trigger', 'ENTER', 'reclaim', 10.0, mint='M', symbol='ABC', mc=18_700)
    assert a['id'] == 1 and a['mc'] == 18_700 and a['at'] == 10.0
    assert T.add('trigger', 'ENTER', 'reclaim', 11.0, mint='M') is None                                 # the same ruling again: nothing
    assert T.add('trigger', 'WAIT', 'stalling', 12.0, mint='M')['id'] == 2
    assert T.add('trigger', 'ENTER', 'again', 13.0, mint='M')['id'] == 3                                # it changed back: a new line
    for i in range(6):
        T.add('devil', f'WARNING {i}', 'x', 20.0 + i, mint='M')
    assert len(T.rows) == 5 and [r['id'] for r in T.rows] == sorted(r['id'] for r in T.rows)             # bounded, chronological
    assert [r['id'] for r in T.since(T.rows[-2]['id'])] == [T.rows[-1]['id']]
    with pytest.raises(AssertionError):
        T.add('robot', 'THINKS', 'fake', 1.0)                                                           # only the ten roles (+ kernel / owner) can write


def test_the_kernel_writes_the_tape_from_its_own_decisions():
    K = tk.Kernel()
    K.run([row('A')], 100.0, {})                                                                        # a READY coin (kernel_helpers.row)
    acts = [(r['agent'], r['action']) for r in K.tape.rows if r['mint'] == 'A']
    assert ('tally', 'CANDIDATE') in acts and ('trigger', 'ENTER') in acts and ('kernel', 'READY') in acts
    n = len(K.tape.rows)
    K.run([row('A')], 130.0, {})                                                                        # the same numbers again
    assert len(K.tape.rows) == n                                                                        # no event → no line (no fake activity)
    r = K.note('courier', 'FILLED BUY', '$0.16', 140.0, mint='A', result={'state': 'filled'}, key='sig1:FILLED')
    assert r['agent'] == 'courier' and r['symbol'] and K.note('courier', 'FILLED BUY', '$0.16', 141.0, mint='A', key='sig1:FILLED') is None


# ── 👤 owner coin review ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_owner_box_reads_a_mint_or_a_supported_link_and_refuses_everything_else():
    assert owr.parse(PUMP) == {'kind': 'address', 'address': PUMP, 'source': 'ca'}
    assert owr.parse(f'https://pump.fun/coin/{PUMP}') == {'kind': 'mint', 'address': PUMP, 'source': 'pump'}
    assert owr.parse(f'https://pump.fun/{PUMP}?x=1')['address'] == PUMP
    assert owr.parse(f'https://birdeye.so/token/{PUMP}?chain=solana') == {'kind': 'mint', 'address': PUMP, 'source': 'birdeye'}
    assert owr.parse(f'https://dexscreener.com/solana/{PUMP}') == {'kind': 'address', 'address': PUMP, 'source': 'dexscreener'}
    for bad in ('', 'hello', 'https://evil.example/coin/' + PUMP, 'https://dexscreener.com/ethereum/0xabc', f'javascript:{PUMP}', PUMP[:20] + '\n' + PUMP[20:], '0' * 40, 'x' * 400):
        assert owr.parse(bad) is None, bad
    assert owr.parse(f'  {PUMP}\n')['address'] == PUMP                                                  # a paste's surrounding whitespace is trimmed


def test_review_track_arm_ignore_rules_and_caps():
    b = owr.apply({}, PUMP, 'review', 100.0, 'ABC', 'ca')
    assert owr.modes(b, 100.0) == {PUMP: 'review'} and owr.modes(b, 100.0 + owr.REVIEW_TTL + 1) == {}   # a review lasts 30 minutes
    b = owr.apply(b, PUMP, 'track', 200.0)
    assert owr.modes(b, 9e6) == {PUMP: 'track'} and b[PUMP]['symbol'] == 'ABC'                           # a track stays until IGNORE
    b = owr.apply(b, PUMP, 'arm', 300.0)
    assert owr.armed(b, 300.0) == {PUMP} and owr.modes(b, 300.0 + owr.ARM_TTL + 1) == {PUMP: 'track'}    # an ARM runs out → tracked, never armed forever
    assert owr.apply(b, PUMP, 'ignore', 400.0) == {}
    full = {}
    mints = [('M' * 40 + c + 'abc')[:43] for c in 'ABCDEFG']
    for m in mints[:owr.ARM_MAX]:
        full = owr.apply(full, m, 'arm', 500.0)
    with pytest.raises(ValueError):
        owr.apply(full, mints[owr.ARM_MAX], 'arm', 500.0)                                               # ≤ 4 armed
    with pytest.raises(ValueError):
        owr.apply({}, 'not-a-mint', 'review', 1.0)
    with pytest.raises(ValueError):
        owr.apply({}, PUMP, 'buy', 1.0)                                                                 # there is no buy action


def test_a_review_never_buys_and_arm_never_makes_a_coin_ready():
    """The four boundaries: (1) review / track only → never READY · (2) ARM → READY only when the kernel has it READY on its own ·
    (3) ARM cannot pass the hard wall · (4) ARM cannot pass a bad execution state."""
    K = tk.Kernel()
    good = row('G')                                                # READY on its own numbers (kernel_helpers.row)
    K.run([good], 100.0, {})
    assert K.dec['G']['status'] == 'READY'
    K.owner = {'G': 'review'}
    K.run([{**good, 'px': good['px'] * 1.05}], 110.0, {'watchOnly': {'G'}})                              # on the desk only because the owner asked
    assert K.dec['G']['status'] == 'CONTENDING' and K.dec['G'].get('wouldBeReady') and 'owner review only' in K.dec['G']['why']
    assert K.ready() == []                                                                              # nothing a seat fill can take
    K.owner = {'G': 'arm'}
    K.run([{**good, 'px': good['px'] * 1.1}], 120.0, {'watchOnly': set()})                               # armed: the review-only rule lifts — the kernel's own rules stay
    assert K.dec['G']['status'] == 'READY'
    wall = row('W', mc=5_000_000)                                # outside the universe (the hard wall)
    K.owner = {'G': 'arm', 'W': 'arm'}
    K.run([wall], 130.0, {})
    assert K.dec['W']['status'] == 'TRACKING' and K.dec['W']['opinions']['devil']['hard']                # ARM does not move the wall
    K.run([{**good, 'px': good['px'] * 1.2}], 140.0, {'courier': 'BAD'})
    assert K.dec['G']['status'] != 'READY'                                                              # ARM does not pass a bad execution state
    assert brain.reduce({'devil': {'hard': False, 'objections': []}, 'trigger': {'state': 'WAIT', 'narrative': 'STALLING', 'why': ''}, 'courier': {'ok': True}}, 500.0, None)['status'] == 'CONTENDING'


def test_an_armed_coin_goes_first_only_among_coins_that_are_ready_anyway():
    K = tk.Kernel()
    K.run([row('A'), row('B', v5=9000)], 100.0, {})
    order = [m for m, _d in K.ready()]
    assert set(order) == {'A', 'B'}
    last = order[-1]
    K.owner = {last: 'arm'}
    assert [m for m, _d in K.ready()][0] == last                                                        # owner priority = order only
    K.owner = {'ZZZ': 'arm'}
    assert [m for m, _d in K.ready()] == order                                                          # arming a coin that is not READY changes nothing


def test_the_review_row_says_unknown_instead_of_zero():
    r = owr.result(PUMP, {'mode': 'review', 'at': 1.0}, None, None, 'PENDING', 5.0)
    assert r['state'] == 'RESOLVING' and 'holders' in r['pending'] and 'mc' not in r
    K = tk.Kernel()
    x = row(PUMP)
    x['vitals'] = {**x['vitals'], 'safe': None}
    K.run([x], 100.0, {})
    out = owr.result(PUMP, {'mode': 'track', 'at': 1.0, 'symbol': 'ABC'}, K.store.mints[PUMP], K.dec[PUMP], 'PENDING', 100.0, only=True)
    assert out['holderStatus'] == 'PENDING' and out['holderSafe'] is None and out['top10'] is None      # pending evidence is not a zero
    assert 'holders' in out['pending'] and out['mc'] == round(x['px'] * 1e9, 2) and out['only'] is True
    assert out['trigger']['state'] in ('ENTER', 'ARM', 'WAIT', 'NO') and out['warden']['size'] is not None and out['courier']['ok'] is True
