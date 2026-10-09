import base64
import dust


def acct(mint, raw, ui, lamports=2_039_280):
    return {'pubkey': 'Acct' + mint, 'program': dust.TOKEN_PROGRAMS[0], 'mint': mint, 'raw': raw, 'decimals': 6, 'ui': ui, 'lamports': lamports}


def test_each_coin_gets_the_right_cleanup():
    rows = dust.classify([acct('EMPTY', 0, 0), acct('DUST', 5, 0.000005), acct('NOPX', 10, 10.0), acct('BIG', 9, 9.0)],
                         prices={'DUST': 1.0, 'BIG': 2.0})
    by = {r['mint']: r for r in rows}
    assert by['EMPTY']['best'] == 'close'
    assert by['DUST']['best'] == 'burn' and by['DUST']['usd'] < 0.01
    assert by['NOPX']['best'] == 'burn' and by['NOPX']['usd'] is None
    assert by['BIG']['best'] == 'swap' and by['BIG']['usd'] == 18.0
    s = dust.summary(rows)
    assert s['dust'] == 3 and abs(s['rentBackSol'] - 3 * 0.00203928) < 1e-5 and s['swapUsd'] == 18.0


def test_burn_close_tx_burns_then_closes_to_the_owner():
    owner = '11111111111111111111111111111112'
    mint = 'So11111111111111111111111111111111111111112'
    acc = 'Sysvar1nstructions1111111111111111111111111'
    tx = dust.burn_close_tx(owner, [{'pubkey': acc, 'program': dust.TOKEN_PROGRAMS[0], 'mint': mint, 'raw': 5}], '11111111111111111111111111111111')
    raw = base64.b64decode(tx)
    assert bytes([8]) + (5).to_bytes(8, 'little') in raw and len(raw) > 100


def test_cronos_rows_only_list_held_tokens_with_a_value():
    toks = [{'address': '0xA', 'symbol': 'AAA', 'decimals': 18, 'priceUSD': '2'}, {'address': '0xB', 'symbol': 'BBB', 'decimals': 6, 'priceUSD': '1'}]
    calls = dust.balance_calls('0x' + 'ab' * 20, toks)
    assert calls[1]['params'][0]['data'].startswith('0x70a08231') and len(calls) == 3
    rows = dust.evm_rows(toks, {1: hex(3 * 10 ** 18), 2: '0x0'})
    assert len(rows) == 1 and rows[0]['symbol'] == 'AAA' and rows[0]['usd'] == 6.0 and rows[0]['best'] == 'swap'


def test_close_tx_only_builds_for_accounts_the_wallet_owns(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    owner = '11111111111111111111111111111112'
    mine = {'pubkey': 'Sysvar1nstructions1111111111111111111111111', 'program': dust.TOKEN_PROGRAMS[0], 'mint': 'So11111111111111111111111111111111111111112',
            'owner': owner, 'raw': 5, 'decimals': 6, 'ui': 0.000005, 'lamports': 2_039_280}

    async def accts(http, o):
        return [mine]

    async def rpc(http, method, params, scan=True):
        return {'value': {'blockhash': '11111111111111111111111111111111'}}
    monkeypatch.setattr(rs, '_sol_token_accounts', accts); monkeypatch.setattr(rs, '_rpc', rpc)
    out = asyncio.run(rs.wallet_dust_close_tx(rs.DustCloseIn(address=owner, accounts=[mine['pubkey']])))
    assert len(out['txs']) == 1 and out['txs'][0]['burns'] == 1 and out['txs'][0]['rentSol'] > 0.002
    with pytest.raises(Exception):
        asyncio.run(rs.wallet_dust_close_tx(rs.DustCloseIn(address=owner, accounts=['SysvarRent111111111111111111111111111111111'])))   # not theirs


def test_every_eco_with_a_positive_balance_is_listed_and_native_is_gas():
    doc = {'balances': {'1': [{'address': dust.NATIVE_EVM, 'symbol': 'ETH', 'decimals': 18, 'amount': str(2 * 10 ** 16), 'priceUSD': '2500'},
                              {'address': '0xT', 'symbol': 'PEPE', 'decimals': 18, 'amount': '0', 'priceUSD': '1'}],
                        '56': [{'address': '0xU', 'symbol': 'CAKE', 'decimals': 18, 'amount': str(10 ** 18), 'priceUSD': '2'}],
                        '999999': [{'address': '0xZ', 'symbol': 'X', 'decimals': 18, 'amount': '1', 'priceUSD': '1'}]}}
    rows = dust.lifi_rows(doc)
    assert {(r['chain'], r['symbol'], r['best']) for r in rows} == {('ethereum', 'ETH', 'gas'), ('bsc', 'CAKE', 'swap')}   # 0 balance + unknown chain dropped
    cro = [{'chain': 'cronos', 'chainId': 25, 'address': '0xC', 'symbol': 'WCRO', 'usd': 6.0, 'best': 'swap'}]
    allr = dust.merge_evm(rows, cro)
    assert [c['chain'] for c in dust.by_chain(allr)] == ['ethereum', 'cronos', 'bsc']


def test_cronos_every_coin_candidates_come_from_lists_the_wallet_index_and_pasted_contracts():
    import dust as d
    A, B, C = '0x' + 'a' * 40, '0x' + 'B' * 40, '0x' + 'c' * 40
    assert d.clean_contracts(f'{A}, {B}\n{A} nonsense 0x123 {d.NATIVE_EVM}') == [A, B.lower()]
    idx = d.index_tokens([{'id': A, 'symbol': 'HYDRO', 'decimals': 18, 'price': 0.002, 'logo_url': 'https://x/y.png', 'is_verified': True},
                          {'id': 'cro', 'decimals': 18}, {'id': B, 'decimals': 'x'}, {'id': C, 'symbol': 'SCAM', 'decimals': 9, 'is_suspicious': True, 'logo_url': 'javascript:1'}, 'junk'])
    assert [(t['symbol'], t['decimals'], t['flag'], t['logoURI']) for t in idx] == [('HYDRO', 18, '', 'https://x/y.png'), ('SCAM', 9, 'suspicious', '')]
    merged = d.merge_tokens([{'address': A.upper().replace('0X', '0x'), 'symbol': 'HYD', 'decimals': 18}], idx, [{'address': 'bad'}])
    assert len(merged) == 2 and merged[0]['symbol'] == 'HYD' and merged[0]['priceUSD'] == 0.002   # the first list names it, a later one adds the price
    sym = '0x' + (32).to_bytes(32, 'big').hex() + (4).to_bytes(32, 'big').hex() + b'TEST'.ljust(32, b'\x00').hex()
    assert d.abi_string(sym) == 'TEST' and d.abi_string('0x' + b'MKR'.ljust(32, b'\x00').hex()) == 'MKR' and d.abi_string('0xzz') == ''
    calls = d.meta_calls([A, B])
    assert [c['id'] for c in calls] == [0, 1, 2, 3] and calls[0]['params'][0]['data'] == '0x313ce567'
    toks = d.meta_tokens([A, B], {0: hex(6), 1: sym, 2: '0x'})   # B never answered decimals(): not a token
    assert toks == [{'address': A, 'symbol': 'TEST', 'name': '', 'decimals': 6, 'priceUSD': None, 'logoURI': '', 'flag': 'added by you'}]
    rows = d.evm_rows(toks, {1: hex(5_000_000)})
    assert rows[0]['ui'] == 5.0 and rows[0]['usd'] is None and rows[0]['flag'] == 'added by you' and rows[0]['best'] == 'dust'
