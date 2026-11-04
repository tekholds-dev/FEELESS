"""⚡ Free commands, Watch a Wallet and the trader's heads-up. Pure words; nothing is sent."""
import agent_commands as ac


def test_free_commands_are_exact_so_a_normal_ask_still_reaches_the_minds():
    assert ac.quick('price gap') == {'tool': 'gaps', 'q': ''} and ac.quick('/gaps')['tool'] == 'gaps'
    assert ac.quick('Trench')['tool'] == 'trench' and ac.quick('perps')['tool'] == 'perps' and ac.quick('best pools')['tool'] == 'pools'
    assert ac.quick('check $BONK') == {'tool': 'check', 'q': 'BONK'} and ac.quick('rug check WIF?')['q'] == 'WIF'
    assert ac.quick('history $GATO') == {'tool': 'pow', 'q': 'GATO'}
    for ask in ('what is a price gap', 'check the news about solana today', 'find me a trench guide', '', None):
        assert ac.quick(ask) is None


def test_watch_a_wallet_is_a_browser_job_that_buys_nothing():
    g = ac.watch_goal('watch a wallet')
    assert 'pump.fun' in g and '3 top' in g and 'Do not buy' in g
    assert 'only memecoins' in ac.watch_goal('Watch wallets only memecoins')
    assert ac.watch_goal('what wallet should I watch') is None


def test_a_trader_says_when_work_is_outside_its_lane():
    assert ac.off_lane('trading', 'build me a landing page') and ac.off_lane('trading', 'write a poem')
    assert not ac.off_lane('general', 'build me a landing page')                # a general agent is built for it
    assert not ac.off_lane('trading', 'write a script that reads the $BONK chart')   # still about money
    assert not ac.off_lane('trading', 'research this coin')


def test_a_check_says_plainly_whether_it_would_buy():
    assert 'NOT' in ac.verdict(False, 'pool too thin', True, '') and 'pool too thin' in ac.verdict(False, 'pool too thin', True, '')
    assert 'top 10' in ac.verdict(True, '', False, 'top 10 wallets hold 61%')
    assert 'not a call to buy' in ac.verdict(True, '', True, 'top10 20%')


def test_watch_folder_files_each_address_with_its_lines():
    import agent_commands as ac
    a = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'; b = 'DRpbCBMxVnDK7maPM5tGv6MvB3v1sRMC86PZ8okm21hy'
    t = {'status': 'done', 'cost': 0.01, 'answer': f'**Wallet 1: {a}** (pump.fun)\n- bought $X 2 SOL, +30%\n\nWallet 2: `{b}`\n- sold $Y\nI trust wallet 1.\nAgain {a}',
         'windows': [{'steps': [{'action': 'open', 'detail': 'https://pump.fun/board'}, {'action': 'open', 'detail': 'https://www.gmgn.ai/x'}, {'action': 'click', 'detail': 'x'}]}]}
    f = ac.watch_folder(t, 100.0, 3)
    assert [w['address'] for w in f['wallets']] == [a, b] and f['n'] == 3 and f['sites'] == ['gmgn.ai', 'pump.fun'] and not f['checked']
    assert any('+30%' in x for x in f['wallets'][0]['lines'])
    empty = ac.watch_folder({'status': 'done', 'answer': 'pump.fun walled me, I saw no wallets. The word Supercalifragilisticexpialidociousness is no address.'}, 1.0, 1)
    assert empty['wallets'] == [] and empty['checked']


def test_chain_check_files_an_unanswered_check_as_unchecked():
    import asyncio
    import agent_commands as ac

    class R:
        def __init__(self, j): self.j = j
        def json(self): return self.j

    class H:
        def __init__(self, j): self.j = j
        async def post(self, *_a, **_k):
            if self.j is None:
                raise OSError('down')
            return R(self.j)
    assert asyncio.run(ac.chain_check(H({'result': [{'blockTime': 9}, {}]}), 'u', 'a')) == {'txs': 2, 'lastAt': 9}
    assert asyncio.run(ac.chain_check(H({'result': []}), 'u', 'a'))['txs'] == 0
    assert asyncio.run(ac.chain_check(H(None), 'u', 'a')) == {'txs': None}
    assert asyncio.run(ac.chain_check(H({'error': 'x'}), 'u', 'a')) == {'txs': None}
