from money_pulse import parse_accounts, preflight, alerts


def test_parse_accounts_sol_and_token():
    vals = [{'lamports': 2_500_000_000, 'data': ['', 'base64']},
            {'lamports': 2_039_280, 'data': {'parsed': {'info': {'mint': 'M', 'owner': 'O', 'tokenAmount': {'uiAmount': 12.5}}}}}, None]
    p = parse_accounts(['A', 'B', 'C'], vals)
    assert p['A']['sol'] == 2.5 and 'token' not in p['A']
    assert p['B']['token'] == {'mint': 'M', 'owner': 'O', 'amount': 12.5}
    assert p['C'] == {'sol': 0.0, 'exists': False}


def test_preflight_names_every_fix():
    fa = [{'asset': 'wSOL', 'ok': True}, {'asset': 'USDC', 'ok': False}]
    out = preflight({'SOLANA_RPC_URL': 'x', 'JUPITER_API_KEY': '', '_internal_key': True}, {'platformFeeBps': 50, 'engine': 'swap'}, fa, {'configured': True}, 0, 100, {})
    bad = {c['key'] for c in out if not c['ok']}
    assert bad == {'jup', 'feeUsdc'} and all(c['fix'] for c in out if not c['ok'])
    assert next(c for c in out if c['key'] == 'ledger')['detail'] == 'no trades yet'


def test_alerts():
    res = [{'season': {'name': 'S1', 'reserveWallet': 'R'}, 'rows': [1, 2], 'paidSol': 0.5, 'assigned': True, 'potSol': 0.5},
           {'season': {'name': 'S2', 'reserveWallet': 'Q'}, 'rows': [], 'paidSol': 0, 'assigned': True, 'potSol': 0}]
    a = alerts(res, [{'pool': {'name': 'OG'}, 'rows': [1], 'paidSol': 0.1, 'cooldownLeft': 0}], [{'address': 'R'}])
    assert 'pays via Circle' in a[0]['text'] and a[1]['tone'] == 'warn' and 'OG' in a[2]['text']


def test_known_destinations_dedup_and_network():
    from money_pulse import known_destinations, same_network
    out = known_destinations(['O'], ['O', 'A'], ['F'], [('Season reserve · S1', 'R')], [('Badge pool · OG', 'P')],
                             [{'address': 'T', 'label': 'Multisig'}], [{'address': 'C', 'name': 'Ops'}], [{'address': 'X', 'label': 'Cold'}])
    assert [d['address'] for d in out] == ['O', 'A', 'F', 'R', 'P', 'T', 'C', 'X'] and out[0]['kind'] == 'owner'
    assert same_network('SOL', 'Abc') and not same_network('SOL', '0xabc') and same_network('BASE', '0xabc')
