import range_pools as rp

RAY = [{'type': 'Concentrated', 'id': 'RAYPOOL', 'programId': 'CAMM', 'mintA': {'address': 'JUP', 'symbol': 'JUP', 'decimals': 6}, 'mintB': {'address': rp.SOL, 'symbol': 'WSOL', 'decimals': 9},
        'feeRate': 0.0025, 'config': {'tickSpacing': 60}, 'tvl': 200000, 'price': 0.0027, 'day': {'volume': 400000, 'volumeFee': 1000}},
       {'type': 'Standard', 'id': 'AMM'}, {'type': 'Concentrated', 'id': 'TINY', 'tvl': 50, 'mintA': {}, 'mintB': {}, 'day': {}}]
MET = [{'address': 'METPOOL', 'name': 'JUP-USDC', 'token_x': {'address': 'JUP', 'symbol': 'JUP', 'decimals': 6}, 'token_y': {'address': rp.USDC, 'symbol': 'USDC', 'decimals': 6},
        'pool_config': {'bin_step': 20, 'base_fee_pct': 0.2}, 'tvl': 150000, 'current_price': 0.27, 'volume': {'24h': 900000}, 'fees': {'24h': 1800}},
       {'address': 'BAD', 'is_blacklisted': True, 'tvl': 1e9}]


def test_both_venues_normalize_to_one_row_with_the_real_fee_rate():
    r = rp.raydium(RAY); m = rp.meteora(MET)
    assert [x['pool'] for x in r] == ['RAYPOOL'] and r[0]['venue'] == 'raydium' and r[0]['step'] == 60 and r[0]['feePct'] == 0.25 and r[0]['rate'] == 1000 / 200000
    assert [x['pool'] for x in m] == ['METPOOL'] and m[0]['step'] == 20 and m[0]['rate'] == 1800 / 150000 and m[0]['symY'] == 'USDC'
    both = r + m
    assert [x['pool'] for x in rp.for_token(both, 'JUP')] == ['RAYPOOL', 'METPOOL']
    assert [x['pool'] for x in rp.for_token(both, 'JUP', rp.USDC)] == ['METPOOL']
    assert [x['pool'] for x in rp.busiest(both)] == ['METPOOL', 'RAYPOOL']   # 1.2 %/day beats 0.5 %/day


def test_relay_lets_autorange_list_positions_but_never_scan_a_program():
    import reputation_service as rs
    dlmm = 'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo'
    assert rs._rpc_call_ok({'method': 'getBalance', 'params': ['x']})
    assert rs._rpc_call_ok({'method': 'getProgramAccounts', 'params': [dlmm, {'filters': [{'memcmp': {'offset': 8, 'bytes': 'POOL'}}]}]})
    assert not rs._rpc_call_ok({'method': 'getProgramAccounts', 'params': [dlmm]})                                   # unfiltered = a whole-program scan
    assert not rs._rpc_call_ok({'method': 'getProgramAccounts', 'params': [dlmm, {'filters': [{'dataSize': 100}]}]})
    assert not rs._rpc_call_ok({'method': 'getProgramAccounts', 'params': ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', {'filters': [{'memcmp': {}}]}]})
    assert not rs._rpc_call_ok({'method': 'requestAirdrop'}) and not rs._rpc_call_ok('nope')


def test_watcher_pings_only_after_the_wait_once_per_two_hours_and_resets_in_range():
    band = {'lo': 0.9, 'hi': 1.1, 'wait': 15, 'sym': 'JUP-SOL'}
    b, msg = rp.watch_step(band, 1.0, 1000); assert msg is None and 'outSince' not in b
    b, msg = rp.watch_step(b, 1.2, 1000); assert msg is None and b['outSince'] == 1000          # just left: a wick is not a move
    b, msg = rp.watch_step(b, 1.2, 1000 + 16 * 60); assert 'above its range for 16 min' in msg
    b, msg = rp.watch_step(b, 1.25, 1000 + 40 * 60); assert msg is None                          # already pinged
    b, msg = rp.watch_step(b, 1.25, 1000 + 16 * 60 + rp.ALERT_EVERY + 1); assert msg            # 2 h later, still out: once more
    b, msg = rp.watch_step(b, 1.0, 99999); assert msg is None and 'outSince' not in b and 'alertedAt' not in b
    assert rp.watch_step({'lo': 0, 'hi': 1}, 2, 1)[1] is None and rp.watch_step(band, None, 1)[1] is None


def test_support_ideas_reacts_and_comments(monkeypatch):
    import asyncio
    import reputation_service as rs
    monkeypatch.setattr(rs, '_session_or_401', lambda w, s: w)
    run = lambda **k: asyncio.run(rs.support_act(rs.SupportAct(wallet=k.pop('w', 'W1'), **k)))
    b = run(idea=True, text='Add a dark-pool for $FEE holders'); iid = b['ideas'][0]['id']
    b = run(react=iid, v=1); assert b['reacts'][iid] == {'up': 1, 'down': 0, 'mine': 1}
    b = run(react=iid, v=-1, w='W2'); assert b['reacts'][iid]['down'] == 1 and b['reacts'][iid]['mine'] == -1
    b = run(react=iid, v=1); assert b['reacts'][iid]['up'] == 0                          # the same vote again clears it
    b = run(comment=iid, text='yes please'); assert b['comments'][iid][-1]['text'] == 'yes please'
    for bad in (dict(react='nope', v=1), dict(comment=iid, text='x'), dict(idea=True, text='short')):
        try:
            run(**bad); assert False, bad
        except rs.HTTPException:
            pass
