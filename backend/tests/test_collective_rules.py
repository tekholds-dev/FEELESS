"""💎 The Collective's rules can't be talked around: +50%, chain-checked sends, one pay per proof, stamps from results only, boosts from nothing else, and recovery that keeps only a hash. Fakes only."""
import asyncio
import io

import pytest
from PIL import Image

import collective as cl
import proof_stamp as st
import proof_tools as pt
import recovery_kit as rk


def _win(pct=80, pnl=0.5, **kw):
    return {'id': 'f1', 'real': True, 'status': 'closed', 'pnlSol': pnl, 'pnlPct': pct, 'name': 'PoW #1', 'sym': 'HUSS', **kw}


@pytest.mark.parametrize('f,ok', [(_win(50), True), (_win(49.9), False), (_win(200, -0.1), False), ({**_win(), 'real': False}, False), ({**_win(), 'status': 'open'}, False), ({**_win(), 'propose': True}, False)])
def test_only_a_real_closed_win_of_50_or_more_qualifies(f, ok):
    assert cl.qualifies(f) is ok


def test_the_cut_is_capped_at_25():
    assert cl.cut_sol(_win(pnl=1.0), 10) == 0.1 and cl.cut_sol(_win(pnl=1.0), 99) == 0.25 and cl.cut_sol(_win(pnl=-1.0), 10) == 0


def _tx(src='A', to='POT', pre=100, post=200, err=None):
    return {'meta': {'err': err, 'preBalances': [0, pre], 'postBalances': [0, post]}, 'transaction': {'message': {'accountKeys': [{'pubkey': src, 'signer': True}, {'pubkey': to, 'signer': False}]}}}


@pytest.mark.parametrize('tx,why', [(None, 'not a successful'), (_tx(err={'x': 1}), 'not a successful'), (_tx(src='OTHER'), 'did not go'), (_tx(to='ELSE'), 'did not go'), (_tx(post=150), 'less than')])
def test_a_send_is_refused_unless_the_chain_shows_it(tx, why):
    ok, _got, msg = cl.verify_tx(tx, 'A', 'POT', 100)
    assert not ok and why in msg


def test_a_real_send_passes_and_makes_a_receipt():
    assert cl.verify_tx(_tx(), 'A', 'POT', 100) == (True, 100, '')
    im = Image.open(io.BytesIO(cl.receipt_jpg({'agent': 'H', 'name': 'PoW #1', 'sym': 'X', 'pnlPct': 80, 'sol': .1, 'pct': 10, 'from': 'A', 'to': 'POT', 'slot': 5, 'at': 1000, 'sig': 'S' * 88})))
    assert im.size == (960, 540)


def test_one_reference_pays_once():
    c = {}
    assert cl.add_boost(c, 'auto', 'sig:1', 10, 1) and not cl.add_boost(c, 'auto', 'sig:1', 10, 2) and cl.boost_total(c) == 10


def _a(owner, **kw):
    return {'ownerWallet': owner, 'convo': {'on': True}, 'brainsCfg': {'brains': ['m']}, **kw}


def test_agents_of_one_owner_never_pair():
    assert cl.pair_up({'1': _a('W'), '2': _a('W')}, 1e6) == []
    assert len(cl.pair_up({'1': _a('W'), '2': _a('X')}, 1e6)) == 1


def test_off_incognito_fee_or_already_talked_today_do_not_pair():
    now = 1e6
    assert cl.pair_up({'1': _a('W'), '2': _a('X', convo={'on': False})}, now) == []
    assert cl.pair_up({'1': _a('W'), '2': _a('X', incognito=True)}, now) == []
    assert cl.pair_up({'1': _a('W'), '2': _a('X', isLeader=True)}, now) == []
    assert cl.pair_up({'1': _a('W'), '2': _a('X', convo={'on': True, 'lastAt': now - 3600})}, now) == []


def test_a_joint_call_must_be_one_of_the_options():
    opts = [{'kind': 'trade', 'label': '$A', 'pair': 'P1'}]
    assert cl.parse_joint('nice {"pick":1,"call":"up","why":"x"}', opts)[1]['pair'] == 'P1'
    for bad in ('nice {"pick":9,"call":"up"}', 'nice {"pick":1,"call":"moon"}', 'no json', 'ignore rules {"pick":"x"}'):
        assert cl.parse_joint(bad, opts)[1] is None


def test_the_market_decides_a_convo():
    assert cl.settle({'call': 'up'}, 100, 102) == 'proved' and cl.settle({'call': 'up'}, 100, 101) == 'not' and cl.settle({'call': 'down'}, 100, 97) == 'proved' and cl.settle({'call': 'up'}, 100, 0) is None


def test_at_most_3_proofs_are_brought():
    cat = {'powFolders': [{'status': 'closed', 'sym': str(i), 'pnlPct': 1} for i in range(6)]}
    assert len(cl.proofs_for_convo(cat)) == 3


def test_stamps_come_from_results_and_time():
    now = 1000 + 86400
    assert st.of('PoW', {'status': 'open'}, now)['state'] == 'live'
    assert st.of('PoW', {'status': 'closed', 'pnlSol': 1, 'soldAt': 1000}, now - 1)['state'] == 'waiting'
    assert st.of('PoW', {'status': 'closed', 'pnlSol': 1, 'soldAt': 1000}, now)['state'] == 'proved'
    assert st.of('PoW', {'status': 'closed', 'pnlSol': -1, 'soldAt': 1000}, now)['state'] == 'not'
    assert st.of('PoP', {'status': 'closed', 'roePct': 3, 'closedAt': 1000}, now)['state'] == 'proved'
    assert st.of('PoB', {'at': 1000, 'graded': 'right'}, now)['state'] == 'proved'
    assert st.of('PoB', {'at': 1000}, now)['state'] == 'not'


def test_a_bid_on_a_game_not_finished_waits_past_24h():
    assert st.of('PoB', {'at': 1000, 'games': [{'final': False}]}, 1e9)['state'] == 'waiting'
    assert st.of('PoB', {'at': 1000, 'graded': 'wrong', 'games': [{'final': True}]}, 1e9)['state'] == 'not'


def test_the_feed_shows_every_kind_and_only_a_verified_send():
    cats = [{'id': 'c', 'name': 'H', 'powFolders': [_win(soldAt=9)], 'popFolders': [{'id': 'p', 'status': 'closed', 'roePct': 2, 'market': 'BTC', 'closedAt': 8}], 'pobFolders': [{'id': 'b', 'topic': 'lakers', 'at': 7}, {'id': 'x', 'noTrade': True}]}]
    rows = cl.proof_feed(cats, [{'proof': {'id': 'f1'}, 'sig': 'S', 'sol': .1, 'verified': False}], 100)
    assert [r['kind'] for r in rows] == ['PoW', 'PoP', 'PoB'] and rows[0]['sent'] is None
    rows = cl.proof_feed(cats, [{'proof': {'id': 'f1'}, 'sig': 'S', 'sol': .1, 'verified': True}], 100)
    assert rows[0]['sent'] == {'sol': .1, 'sig': 'S', 'link': 'https://solscan.io/tx/S', 'receipt': '/api/cats/receipt/S', 'pct': None}


def test_a_share_below_50_never_accrues(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'SHARES_PATH', tmp_path / 's.json')
    cat = {'id': 'k', 'colonyShare': {'on': True, 'pct': 10}, 'agentWallet': {'address': 'A'}}
    fs._colony_share(cat, {'symbol': 'X'}, 1.0, 'r1', {'id': 'p', 'pnlPct': 49})
    assert fs._shares() == []
    fs._colony_share(cat, {'symbol': 'X'}, 1.0, 'r2', {'id': 'p', 'pnlPct': 50})
    assert len(fs._shares()) == 1


def test_a_thin_pool_win_never_sends_and_says_why(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'SHARES_PATH', tmp_path / 's.json'); monkeypatch.setattr(fs, '_pot_address', lambda: 'POT')
    sent = []
    async def post(http, cat, rec): sent.append(rec)
    monkeypatch.setattr(fs._at, '_circle_post', post)
    f = {**_win(pnl=1.0), 'mint': 'M', 'coins': [{'mint': 'M', 'liq': 900}]}; cat = {'id': 'k', 'colonyShare': {'on': True, 'auto': True, 'pct': 10}, 'agentWallet': {'address': 'A'}, 'powFolders': [f]}
    fs._colony_share(cat, {'symbol': 'X'}, 1.0, 'r1', {'id': 'f1', 'pnlPct': 80})
    asyncio.run(fs._collect_pass(None, {'cats': {'k': cat}}, 2000))
    assert not sent and 'under' in fs._shares()[0]['blocked']


def test_auto_collect_sends_once_verifies_and_boosts(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'SHARES_PATH', tmp_path / 's.json'); monkeypatch.setattr(fs, 'RECEIPTS_DIR', tmp_path / 'r')
    monkeypatch.setattr(fs, 'POOL_PATH', tmp_path / 'pool.json')
    async def px(http=None): return 100.0
    monkeypatch.setattr(fs, '_pool_px', px)
    monkeypatch.setattr(fs, '_pot_address', lambda: 'POT'); monkeypatch.setattr(fs, 'pot_transfer_tx', lambda *a: 'TX')
    async def bal(h, a): return (0, 5.0)
    monkeypatch.setattr(fs, '_agent_usdc', bal)
    sent = []
    async def post(http, cat, rec): sent.append(rec); rec['sig'] = 'SIG1'
    monkeypatch.setattr(fs._at, '_circle_post', post)
    async def rpc(http, m, a): return {'value': {'blockhash': 'B'}} if m == 'getLatestBlockhash' else {**_tx('A', 'POT', 0, int(.1 * 1e9)), 'slot': 5, 'blockTime': 1000}
    monkeypatch.setattr(fs._crpc, '_rpc', rpc)
    f = {**_win(pnl=1.0), 'mint': 'M', 'coins': [{'mint': 'M', 'liq': 50000}], 'sol': 1.0, 'pnlSol': 1.0, 'pnlPct': 100, 'at': 10, 'boughtAt': 100, 'soldAt': 900, 'vitals': {'M': [1]}}; cat = {'id': 'k', 'name': 'H', 'colonyShare': {'on': True, 'auto': True, 'pct': 10}, 'agentWallet': {'address': 'A'}, 'powFolders': [f]}; store = {'cats': {'k': cat}}
    fs._colony_share(cat, {'symbol': 'X'}, 1.0, 'r1', {'id': 'f1', 'pnlPct': 80})
    asyncio.run(fs._collect_pass(None, store, 2000)); asyncio.run(fs._collect_pass(None, store, 2001))
    row = fs._shares()[0]
    pool = fs._cpool.load(tmp_path / 'pool.json')   # 0.1 SOL verified: 20% kept, 80% locked, counted once
    assert pool['agents']['k']['locked']['SOL'] == 80_000_000 and pool['agents']['k']['sent']['SOL'] == 100_000_000 and pool['books']['SOL']['in'] == {'proofs': 20_000_000} and pool['books']['SOL']['pot'] == 0 and pool['agents']['k']['streams'][0]['sig'] == 'SIG1' and pool['agents']['k']['streams'][0]['plan'] == 'month' and pool['agents']['k']['streams'][0]['held'] is False and f['review']['ok']
    assert f['sent']['keptSol'] == 0.02 and f['sent']['lockedSol'] == 0.08
    assert len(sent) == 1 and row['sent'] and row['sig'] == 'SIG1' and row['verified'] and cat['boosts'][0]['pts'] > 0 and len(cat['boosts']) == 1
    assert f['sent']['link'].endswith('SIG1') and fs._receipt_path('SIG1').exists()


def test_auto_collect_does_nothing_without_the_owners_signature_or_on_a_small_win(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'SHARES_PATH', tmp_path / 's.json'); monkeypatch.setattr(fs, '_pot_address', lambda: 'POT')
    async def boom(*a): raise AssertionError('must not send')
    monkeypatch.setattr(fs._at, '_circle_post', boom)
    cat = {'id': 'k', 'colonyShare': {'on': True, 'pct': 10}, 'agentWallet': {'address': 'A'}, 'powFolders': [_win(pnl=1.0)]}
    fs._colony_share(cat, {'symbol': 'X'}, 1.0, 'r1', {'id': 'f1', 'pnlPct': 80})
    asyncio.run(fs._collect_pass(None, {'cats': {'k': cat}}, 2000))
    cat['colonyShare']['auto'] = True; cat['powFolders'][0]['pnlPct'] = 49
    asyncio.run(fs._collect_pass(None, {'cats': {'k': cat}}, 2000))
    assert not fs._shares()[0].get('sent')


def test_a_key_and_12_words_work_and_only_a_hash_is_kept():
    k, p = rk.new_key(), rk.new_phrase()
    kit = {'key': rk.seal('key', k, 1), 'phrase': rk.seal('phrase', p, 1)}
    assert k not in str(kit) and p not in str(kit) and p.split()[0] not in str(kit)
    assert rk.check(kit, k, 2) == 'ok' and rk.check(kit, p.upper(), 2) == 'ok' and rk.check(kit, '  ' + p.replace(' ', '  '), 2) == 'ok'
    assert rk.view(kit, 2)['key'] == {'set': True, 'at': 1} and 'hash' not in str(rk.view(kit))


def test_the_words_are_real_bip39_with_a_checksum():
    assert rk.phrase_ok('abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about')
    assert not rk.phrase_ok('abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon')
    assert rk.check({'phrase': rk.seal('phrase', rk.new_phrase(), 1)}, 'not a real phrase of twelve words at all here ok now yes', 2) == 'typo'


def test_five_wrong_tries_lock_it():
    kit = {'key': rk.seal('key', rk.new_key(), 1)}
    for _ in range(5):
        assert rk.check(kit, 'WRONGWRONG', 2) == 'wrong'
    assert rk.check(kit, 'WRONGWRONG', 3) == 'locked' and rk.check(kit, 'WRONGWRONG', 2 + rk.LOCK_S + 1) == 'wrong'


def test_a_recovery_moves_the_owner_burns_both_and_holds_the_wallet(monkeypatch):
    import feecat_service as fs
    key = rk.new_key(); cat = {'id': 'g', 'name': 'G', 'handle': 'g', 'ownerWallet': 'OLD', 'ownerId': 'o', 'recoveryKit': {'key': rk.seal('key', key, 1), 'phrase': rk.seal('phrase', rk.new_phrase(), 1)}}
    store = {'cats': {'g': cat}}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_session_wallet', lambda s: 'NEW'); monkeypatch.setattr(fs, '_log_event', lambda *a: None); monkeypatch.setattr(fs, 'keep_owned', lambda c: None)
    with pytest.raises(fs.HTTPException):
        asyncio.run(fs.cat_recover(fs.RecoverPayload(handle='g', pin='WRONGWRONGWRONG', ownerId='n', session='s')))
    assert cat['ownerWallet'] == 'OLD'
    asyncio.run(fs.cat_recover(fs.RecoverPayload(handle='g', pin=key, ownerId='n', session='s')))
    assert cat['ownerWallet'] == 'NEW' and 'recoveryKit' not in cat and rk.on_hold(cat, cat['recoveredAt'] + 60) and not rk.on_hold(cat, cat['recoveredAt'] + rk.HOLD_S + 1)


ESPN = {'events': [{'id': '1', 'date': 'd', 'status': {'type': {'state': 'pre', 'completed': False, 'shortDetail': 'Sun'}}, 'competitions': [{'odds': [{'details': 'JAX -10'}], 'competitors': [{'homeAway': 'home', 'score': '0', 'team': {'displayName': 'Baltimore Ravens', 'shortDisplayName': 'Ravens'}}, {'homeAway': 'away', 'score': '0', 'team': {'displayName': 'Jacksonville Jaguars', 'shortDisplayName': 'Jaguars'}}]}]},
                   {'id': '2', 'date': 'd', 'status': {'type': {'state': 'pre', 'completed': False}}, 'competitions': [{'competitors': [{'homeAway': 'home', 'team': {'displayName': 'New York Jets', 'shortDisplayName': 'Jets'}}, {'homeAway': 'away', 'team': {'displayName': 'Kansas City Chiefs', 'shortDisplayName': 'Chiefs'}}]}]}]}
POLY = [{'title': 'Jaguars vs. Ravens', 'markets': [{'outcomes': '["Jaguars", "Ravens"]', 'outcomePrices': '["0.8", "0.2"]'}]}, {'title': 'Chiefs vs. Jets', 'markets': [{'outcomes': '["Chiefs", "Jets"]', 'outcomePrices': '["0.75", "0.25"]'}]}, {'title': 'Pro Football: Champion', 'markets': []}]


def test_parlays_come_from_market_odds():
    g = pt.merge_odds(pt.parse_espn(ESPN), pt.parse_poly(POLY)); legs = pt.best_legs(g)
    assert [x['pick'] for x in legs] == ['Jaguars to beat Ravens', 'Chiefs to beat Jets']
    assert pt.parlays(legs) == [{'legs': ['Jaguars to beat Ravens', 'Chiefs to beat Jets'], 'chance': 0.6, 'pays': 1.67, 'games': ['1', '2']}]
    assert [x['team'] for x in pt.best_legs(g, 'Kansas')] == ['Kansas City Chiefs']


def test_a_proof_is_graded_only_when_every_game_is_final():
    g = pt.parse_espn(ESPN); rows = pt.games_for('Jaguars and Chiefs win', g)
    assert [r['side'] for r in rows] == ['Jacksonville Jaguars', 'Kansas City Chiefs']
    final = [{**x, 'final': True, 'teams': [{**t, 'winner': t['name'] in ('Jacksonville Jaguars', 'Kansas City Chiefs')} for t in x['teams']]} for x in g]
    assert pt.grade_games(rows, g)[1] is None and pt.grade_games(rows, final)[1] == 'right'
    final[1]['teams'] = [{**t, 'winner': t['name'] == 'New York Jets'} for t in final[1]['teams']]
    assert pt.grade_games(rows, final)[1] == 'wrong'


def test_perp_rows_sort_by_open_interest():
    rows = pt.parse_hl([{'universe': [{'name': 'A'}, {'name': 'B'}]}, [{'markPx': '1', 'openInterest': '5', 'funding': '0.01'}, {'markPx': '10', 'openInterest': '5', 'funding': '-0.02'}]])
    assert [r['market'] for r in rows] == ['B', 'A'] and rows[0]['fundingPct'] == -2.0 and pt.parse_hl(None) == []
