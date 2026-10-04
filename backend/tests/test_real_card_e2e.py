"""💵 Real card end to end: the tier ENGINE (arena_prime.tick) and the KEEPER (fuse_wallet orders → confirmed fill → book → sync)
run together on a FAKE chain (no network, no funds) with the owner's 5-min config. Every tick the real book must equal the fake chain,
the card must show exactly what the book holds, money may only leave through fills, and every "My cards" option the UI offers must
survive the server unchanged and stay separate from HQ's paper config."""
import json
import random
import re
from pathlib import Path

import pytest

import arena_prime as ap
import fuse_wallet as fw

SOL_PX = 120.0
DEC = 6
RENT = 0.00203928
FEE = 0.000005
HAIRCUT = 0.01   # every fake fill is 1% worse than mid (spread + impact)


def _ui_options():
    src = (Path(__file__).resolve().parents[2] / 'frontend/src/components/ArenaPrime.jsx').read_text()
    body = src[src.index('const EDIT = [') + len('const EDIT = '):]
    body = body[:body.index('\n];') + 3]
    out = {}
    for key, opts in re.findall(r"\['(\w+)', '[^']*', \[(.*?)\], '", body):
        out[key] = [json.loads(v.replace("'", '"')) for v in re.findall(r"\[([^,\[\]]+), '", opts)]
    return out


def test_every_my_cards_option_survives_the_server_unchanged():
    opts = _ui_options()
    assert set(opts) >= {'rotateHours', 'rotateConfirm', 'rotateMinDrop', 'minHoldMins', 'keepWinPct', 'rideAt', 'rideTrail',
                         'cycleEvery', 'slMode', 'rescuePct', 'autoBrain'}
    base = ap.clean_cfg({})
    for key, vals in opts.items():
        for v in vals:
            got = ap.clean_cfg({**base, key: v})[key]
            assert (abs(got - v) < 1e-9 if isinstance(v, (int, float)) and not isinstance(v, bool) else got == v), (key, v, got)
    for cyc in ('safe', 'classic', 'adaptive', 'press', 'rescue', 'auto', 'off'):
        assert ap.clean_cfg({'cycles': {'safe': cyc}})['cycles']['safe'] == cyc
    lim = fw.clean_cfg({'minLiqUsd': 100000, 'arenaMinLiqUsd': 30000, 'maxSwapUsd': 5, 'dailyUsd': 50, 'minOrderUsd': 0.25, 'slippageBps': 300, 'maxImpactPct': 3.5})
    assert (lim['minLiqUsd'], lim['arenaMinLiqUsd'], lim['maxSwapUsd'], lim['dailyUsd'], lim['minOrderUsd'], lim['slippageBps'], lim['maxImpactPct']) == \
        (100000, 30000, 5, 50, 0.25, 300, 3.5)


def test_real_card_edits_and_brain_never_cross_with_hq_paper(monkeypatch):
    import asyncio
    rs = pytest.importorskip('reputation_service')
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {'rotateHours': 1, 'rotateConfirm': 2},
                                              'realCfg': {'rotateHours': 0.08, 'rotateConfirm': 4, 'autoBrain': False},
                                              'cards': {'safe': {'real': True, 'events': []}, 'degen': {'events': []}}}})
    sim = {'s24': {'n': 200, 'avgPct': 1}, 'best': {'confirm': {'value': '3', 'n': 50}}}
    asyncio.run(rs._engine_self_fix(1.0, sim))
    pr = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']
    assert pr['cfg']['rotateConfirm'] == 3                                    # paper tuned
    assert pr['realCfg']['rotateConfirm'] == 4 and pr['realCfg']['rotateHours'] == 0.08   # real card: its 🧠 is off → untouched
    assert not pr['cards']['safe']['events'] and pr['cards']['degen']['events']           # no fake "config changed" on the real card
    pr['realCfg']['autoBrain'] = True
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': pr})
    asyncio.run(rs._engine_self_fix(2.0, {'s24': {'n': 200, 'avgPct': 1}, 'best': {'confirm': {'value': '5', 'n': 50}}}))
    pr = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']
    assert pr['realCfg']['rotateConfirm'] == 5 and pr['cards']['safe']['events']        # its own 🧠 on → tuned on its own config
    assert rs._prime_real_cfg(pr)['rotateHours'] == 0.08                                 # the 5-min clock stays


class Chain:
    """The fake chain: what the Fuse wallet REALLY holds for this card + every SOL that left through rent and fees."""
    def __init__(self, sol):
        self.sol, self.atoms, self.rent, self.fees, self.n = sol, {}, 0.0, 0.0, {'buy': 0, 'sell': 0}

    def fill(self, o, px):
        if o['side'] == 'buy':
            spend = int(o['lamports']) / 1e9
            new = not self.atoms.get(o['mint'])
            atoms = int(spend * SOL_PX / px * (1 - HAIRCUT) * 10 ** DEC)
            sol = -spend - (RENT if new else 0.0)   # like fill_from_meta: SOL Δ EXCLUDES the network fee
            self.rent += RENT if new else 0.0
        else:
            atoms = -int(o['atoms'])
            sol = int(o['atoms']) / 10 ** DEC * px / SOL_PX * (1 - HAIRCUT)
        self.atoms[o['mint']] = self.atoms.get(o['mint'], 0) + atoms
        assert self.atoms[o['mint']] >= 0, 'sold more than the wallet held'
        self.fees += FEE; self.n[o['side']] += 1
        return {'atoms': atoms, 'decimals': DEC, 'sol': round(sol, 9), 'feeSol': FEE}


def _market(seed, crash=None):
    rnd = random.Random(seed)
    majors = [{'mint': fw.SOL_MINT, 'pairAddress': 'Psol', 'symbol': 'SOL', 'price': SOL_PX, 'liquidityUsd': 5e7},
              *[{'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'price': 1.0, 'liquidityUsd': 5e7} for m in ('cbBTC', 'WETH', 'JitoSOL')]]
    runners = [{'mint': f'r{i}', 'pairAddress': f'Pr{i}', 'symbol': f'R{i}', 'price': 1.0, 'score': 90 - i, 'liq': 2e5, 'vol1h': 5e4, 'buyShare': 60}
               for i in range(8)]
    runners += [{'mint': 'arena1', 'pairAddress': 'Parena1', 'symbol': 'ARN', 'price': 1.0, 'score': 95, 'liq': 5e4, 'arena': True},
                {'mint': 'thin1', 'pairAddress': 'Pthin1', 'symbol': 'THN', 'price': 1.0, 'score': 99, 'liq': 5e4}]
    px = {x['pairAddress']: x['price'] for x in majors + runners}

    def step(t):
        for k in px:
            if k == 'Psol':
                continue
            px[k] = max(1e-6, px[k] * (1 + rnd.gauss(0, 0.004)))
            if crash and k == crash and t > 20:
                px[k] *= 0.97
        for x in majors + runners:
            x['price'] = px[x['pairAddress']]
        return px
    return majors, runners, px, step


def _run(seed, ticks=240, crash=None, cfg_patch=None, refuse_sells=0.0):
    majors, runners, px, step = _market(seed, crash)
    cfg = ap.clean_cfg({'rotateHours': 0.08, 'rotateConfirm': 2, 'rotateMinDrop': 10, 'minHoldMins': 0, 'cycleEvery': 3,
                        'cycles': {'safe': 'press'}, 'compound': True, 'paperFeeUsd': 0.0, 'floorPct': 60, **(cfg_patch or {})})
    wcfg = fw.clean_cfg({'armed': True, 'walletId': 'w', 'address': 'A', 'maxSwapUsd': 5, 'dailyUsd': 50, 'minOrderUsd': 0.25,
                         'minLiqUsd': 100000, 'arenaMinLiqUsd': 20000})
    floor_ok = lambda x: _liq(x) >= fw.liq_floor(wcfg, x.get('arena'))   # the service's real-card candidate floor
    now = 1000.0
    card = ap.deal('safe', [], [r for r in runners if floor_ok(r)], cfg, now, majors)
    book = fw.new_book(6.0, SOL_PX, now)
    card = fw.topup_card(card, 6.0, px, now, first=True)
    chain = Chain(book['sol'])
    liqs = {x['pairAddress']: _liq(x) for x in majors + runners}
    ledger, seen = [], set()
    refuse_rnd = random.Random(seed * 7)
    for t in range(ticks):
        now += 60
        step(t)
        before = card
        r_t = [r for r in runners if floor_ok(r)]
        cool = ap.cooling(card, now, cfg['rotateHours'], px) - {l['mint'] for l in card['legs']}
        r_c = [r for r in r_t if r['mint'] not in cool]
        card = ap.tick(card, px, [], r_c if len(r_c) >= 3 else r_t, cfg, now, majors, None, liqs)
        card = ap.note_dropped(before, card, now, cfg['rotateHours'], px)
        book = fw.bank(book, card.get('walletUsd'), SOL_PX)
        for side in ('sell', 'buy'):
            for o in [x for x in fw.orders('safe', card, book, px, SOL_PX, wcfg, now, count_sells=side == 'sell') if x['side'] == side]:
                held = int(((book.get('legs') or {}).get(o['mint']) or {}).get('atoms') or 0)
                assert side == 'buy' or 0 < o['atoms'] <= held                       # never sells what the book doesn't hold
                if side == 'buy':
                    assert int(o['lamports']) / 1e9 <= book['sol'] + 1e-9            # never spends SOL the card doesn't have
                ok, why = fw.check({**o, 'liq': liqs.get(o['pair'])}, wcfg, ledger, now)
                if ok and side == 'sell' and refuse_rnd.random() < refuse_sells:
                    continue   # a sell route refused (sell_safety: pays too far under market) — retried next tick
                if not ok:
                    assert 'thin' in why or 'cap' in why, why
                    assert o['mint'] != 'arena1'                                      # 🏟 Arena coin passes its own floor
                    continue
                fill = chain.fill(o, px[o['pair']])
                assert fw.fill_error(o, fill, book) == ''
                book, _ = fw.apply_fill(book, o, fill, SOL_PX)
                ledger.append({**o, 'status': 'filled'})
                seen.add(o['mint'])
            book = fw.bank(book, card.get('walletUsd'), SOL_PX)
        card = fw.sync_card(card, book, px, SOL_PX)
        # 🔒 the book IS the chain; the card IS the book
        for m in set(chain.atoms) | set(book.get('legs') or {}):
            assert int(((book.get('legs') or {}).get(m) or {}).get('atoms') or 0) == chain.atoms.get(m, 0), (t, m)
        assert book['sol'] >= -1e-9
        for l in card['legs']:
            if l['mint'] != fw.SOL_MINT and not l.get('buying'):
                assert abs(l['units'] - fw.held_units(book, l['mint'])) < 1e-6, (t, l['symbol'])
    return card, book, chain, ledger, px, seen


def _liq(x):
    return x.get('liquidityUsd') or x.get('liq') or 0


@pytest.mark.parametrize('seed', [1, 2, 3])
def test_real_card_5min_book_matches_chain_and_money_only_leaves_through_fills(seed):
    card, book, chain, ledger, px, seen = _run(seed)
    # card SOL never pays rent / network fees (the wallet reserve fronts them for the first 5 rounds; rent is always reserve)
    swaps_in = sum(int(o['lamports']) for o in ledger if o['side'] == 'buy') / 1e9
    fills_back = book['sol'] + book.get('bankSol', 0) - (6.0 / SOL_PX - swaps_in)
    assert fills_back >= -1e-6
    assert abs(chain.rent - book.get('rentSol', 0)) < 1e-9                       # every rent lamport is on the record
    # what the card is worth = the chain at market, the haircut on what was actually traded is the only other cost
    v = fw.book_value(book, px, SOL_PX)
    chain_v = (book['sol'] + book.get('bankSol', 0)) * SOL_PX + sum(a / 10 ** DEC * px[next(x['pair'] for x in ledger if x['mint'] == m)]
                                                                   for m, a in chain.atoms.items() if a)
    assert abs(v - chain_v) < 1e-6
    assert int(card.get('rounds') or 0) >= 40                                   # 5-min rounds really ran (4h / 5 min)


def test_real_card_5min_flat_market_has_no_pointless_churn_and_loses_only_the_haircut():
    card, book, chain, ledger, px, seen = _run(9, ticks=240)
    traded = sum(o['usd'] for o in ledger)
    assert chain.n['buy'] + chain.n['sell'] <= 60, chain.n                      # ≤ 1 swap per 4 min on a $6 card (was ~10/hour live)
    v = fw.book_value(book, px, SOL_PX)
    assert v > 6.0 * 0.85                                                       # no hidden leak on a calm market
    assert traded * HAIRCUT < 6.0 * 0.15                                        # the trading cost stays a small slice of the card


def test_real_card_crashing_coin_is_cut_and_book_stays_true():
    card, book, chain, ledger, px, seen = _run(4, ticks=200, crash='Pr0')
    assert 'r0' not in {l['mint'] for l in card['legs']} and not chain.atoms.get('r0')   # the crashing coin is gone (stop / rotation)
    buys = [o for o in ledger if o['mint'] == 'r0' and o['side'] == 'buy']
    sells = [o for o in ledger if o['mint'] == 'r0' and o['side'] == 'sell']
    assert len(buys) <= 2 and sells, (len(buys), len(sells))                    # 🩸 never re-bought into its own crash


def test_arena_coin_reaches_the_real_card_and_a_thin_non_arena_coin_never_does():
    card, book, chain, ledger, px, seen = _run(5, ticks=120)
    assert 'thin1' not in seen                                                  # $50K pool, not Arena → under the $100K real floor
    floor = fw.liq_floor(fw.clean_cfg({'minLiqUsd': 100000, 'arenaMinLiqUsd': 20000}), True)
    assert floor == 20000
    ok, _ = fw.check({'side': 'buy', 'usd': 1, 'liq': 5e4, 'arena': True}, {'armed': True, 'walletId': 'w', 'address': 'A',
                                                                              'minLiqUsd': 100000, 'arenaMinLiqUsd': 20000}, [], 0)
    assert ok


@pytest.mark.parametrize('seed', [1, 2, 3, 4])
def test_refused_sells_never_let_a_buy_spend_sol_the_card_does_not_have(seed):
    _run(seed, ticks=200, refuse_sells=0.5)   # the run asserts book SOL ≥ 0 and every buy ≤ the card's SOL, every tick


def test_real_card_floor_judges_the_true_book_not_the_engine_estimate():
    majors, runners, px, step = _market(11)
    cfg = ap.clean_cfg({'rotateHours': 0.08, 'floorPct': 15, 'cycleEvery': 0, 'paperFeeUsd': 0.0})
    card = ap.deal('safe', [], runners[:8], cfg, 0, majors)
    card.update(startUsd=6.0, dayStartUsd=6.0, roundStartUsd=6.0)
    for l in card['legs']:
        if l['role'] != 'anchor':
            l.update(units=0.0, costUsd=0.0, buying=True, wantUnits=1.0)   # buys not landed: the engine estimate reads ~ −75%
    out = ap.tick(card, px, [], runners, cfg, 400, majors, None, {}, true_usd=5.4)   # the real book: −10%
    assert not out.get('flooredAt') and not any(e.get('kind') == 'floor' for e in out['events'])
    out2 = ap.tick(card, px, [], runners, cfg, 400, majors, None, {}, true_usd=4.8)  # really −20% → the floor still protects
    assert out2.get('flooredAt') or any(e.get('kind') == 'floor' for e in out2['events'])


def test_hand_swap_of_a_coin_still_buying_moves_its_waiting_money():
    majors, runners, px, step = _market(12)
    cfg = ap.clean_cfg({'paperFeeUsd': 0.0})
    card = ap.deal('safe', [], runners[:3], cfg, 0, majors)
    leg = next(l for l in card['legs'] if l['role'] == 'runner')
    leg.update(units=0.0, buying=True, wantUnits=1.5)
    out = ap.replace_leg(card, leg['pairAddress'], px, [], runners, majors, cfg, 10)
    new = next(l for l in out['legs'] if l['mint'] not in {x['mint'] for x in card['legs']})
    assert abs(new['costUsd'] - 1.5 * px[leg['pairAddress']]) < 1e-6 and new.get('picked')   # its waiting $, not $0
    assert out['events'][-1]['why'] == '⇄ swapped by hand'
    leg.update(wantUnits=0.0, buying=False)
    with pytest.raises(ValueError):
        ap.replace_leg(card, leg['pairAddress'], px, [], runners, majors, cfg, 10)   # nothing on it → nothing to swap
