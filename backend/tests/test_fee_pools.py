import fee_pools as fp

LLAMA = [
    {'chain': 'Solana', 'project': 'raydium-amm', 'symbol': 'SOL-USDC', 'tvlUsd': 9e6, 'apy': 31.2, 'apyBase': 31.2, 'apyPct7D': 4.0, 'poolMeta': 'Concentrated - 0.04%', 'pool': 'r-clmm',
     'underlyingTokens': [fp.SOL, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'], 'ilRisk': 'yes', 'volumeUsd1d': 4e6},
    {'chain': 'Solana', 'project': 'raydium-amm', 'symbol': 'RAY-SOL', 'tvlUsd': 2e6, 'apy': 12, 'apyPct7D': 0.5, 'poolMeta': None, 'pool': 'r-amm', 'underlyingTokens': ['RAYmint', fp.SOL]},
    {'chain': 'Solana', 'project': 'jito-liquid-staking', 'symbol': 'JITOSOL', 'tvlUsd': 1.1e9, 'apy': 4.9, 'apyPct7D': -0.1, 'pool': 'jito', 'underlyingTokens': [fp.SOL]},
    {'chain': 'Solana', 'project': 'kamino-liquidity', 'symbol': 'JLP-USDC', 'tvlUsd': 5e6, 'apy': 22, 'apyPct7D': 9.0, 'pool': 'k-vault', 'underlyingTokens': ['JLPmint', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v']},
    {'chain': 'Solana', 'project': 'jupiter-lend', 'symbol': 'USDC', 'tvlUsd': 4.9e8, 'apy': 5.4, 'pool': 'jl', 'underlyingTokens': ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'], 'stablecoin': True},
    {'chain': 'Solana', 'project': 'some-farm', 'symbol': 'X', 'tvlUsd': 9e6, 'apy': 99, 'pool': 'nope'},                 # a kind we don't show
    {'chain': 'Ethereum', 'project': 'raydium-amm', 'symbol': 'ETH', 'tvlUsd': 9e9, 'pool': 'eth'},                        # not Solana
    {'chain': 'Solana', 'project': 'orca-dex', 'symbol': 'DUST', 'tvlUsd': 1000, 'pool': 'tiny'},                          # under MIN_TVL
]
PAIRS = [
    {'chainId': 'solana', 'dexId': 'meteora', 'pairAddress': 'DLMMpair', 'labels': ['DLMM'], 'liquidity': {'usd': 800000}, 'volume': {'h24': 4e6}, 'priceChange': {'h24': 12},
     'baseToken': {'address': 'WIFmint', 'symbol': 'WIF'}, 'quoteToken': {'address': fp.SOL, 'symbol': 'SOL'}},
    {'chainId': 'solana', 'dexId': 'pumpswap', 'pairAddress': 'PUMPpair', 'liquidity': {'usd': 90000}, 'volume': {'h24': 2e6}, 'baseToken': {'address': 'MEMEmint', 'symbol': 'MEME'}, 'quoteToken': {'address': fp.SOL, 'symbol': 'SOL'}},
    {'chainId': 'solana', 'dexId': 'raydium', 'pairAddress': 'CLMMpair', 'labels': ['CLMM'], 'liquidity': {'usd': 3e6}, 'volume': {'h24': 1e6}, 'baseToken': {'address': 'JUPmint', 'symbol': 'JUP'}, 'quoteToken': {'address': fp.SOL, 'symbol': 'SOL'}},
    {'chainId': 'solana', 'dexId': 'meteora', 'pairAddress': 'thin', 'liquidity': {'usd': 900}, 'baseToken': {}, 'quoteToken': {}},   # too thin
    {'chainId': 'base', 'dexId': 'raydium', 'pairAddress': 'other-chain', 'liquidity': {'usd': 9e6}},
]


def test_every_kind_is_classified_from_the_protocol():
    assert fp.kind_of('raydium-amm', 'Concentrated - 0.01%') == 'v3' and fp.kind_of('raydium-amm', None) == 'v2' and fp.kind_of('orca-dex') == 'v3'
    assert fp.kind_of('jito-liquid-staking') == 'stake' and fp.kind_of('binance-staked-sol') == 'stake' and fp.kind_of('sanctum-infinity') == 'stake'
    assert fp.kind_of('kamino-liquidity') == 'vault' and fp.kind_of('kamino-lend') == 'lend' and fp.kind_of('project-0') == 'lend'
    assert fp.kind_of('gmx-solana') == 'perps' and fp.kind_of('blackrock-buidl') == 'rwa' and fp.kind_of('random-farm') is None


def test_the_hub_keeps_every_kind_with_the_token_you_hold_and_the_exact_deposit_page():
    v = fp.hub(LLAMA, PAIRS, 1000.0)
    by = {r['id']: r for r in v['pools']}
    assert set(by) == {'r-clmm', 'r-amm', 'jito', 'k-vault', 'jl', 'DLMMpair', 'PUMPpair', 'CLMMpair'}
    assert by['r-clmm']['kind'] == 'v3' and by['r-clmm']['hold'] == fp.SOL and by['r-amm']['hold'] == 'RAYmint'   # the non-quote side
    assert by['jito']['hold'] == fp.LST['jito-liquid-staking']                                                     # staking = holding the LST
    assert by['DLMMpair']['kind'] == 'dlmm' and by['DLMMpair']['app'] == 'https://app.meteora.ag/dlmm/DLMMpair' and by['DLMMpair']['pair'] == 'DLMMpair'
    assert by['CLMMpair']['app'].endswith('pool_id=CLMMpair') and by['PUMPpair']['kind'] == 'v2'
    assert by['k-vault']['rise'] == 9.0 and by['DLMMpair']['rise'] == 50.0                                        # APY 7d move · turnover
    assert [r['id'] for r in v['cities']['heights']] == ['r-clmm', 'CLMMpair'] and {r['id'] for r in v['cities']['bay']} == {'jito', 'DLMMpair'}
    assert {r['id'] for r in v['cities']['docks']} == {'k-vault', 'jl'} and {r['id'] for r in v['cities']['harbor']} == {'r-amm', 'PUMPpair'}
    assert v['kinds']['v3'] == 2 and v['at'] == 1000.0
    assert fp.link_row(by['jito']) == {'pool': 'jito', 'sym': 'JITOSOL', 'kind': 'stake', 'proto': 'Jito Liquid Staking'}
