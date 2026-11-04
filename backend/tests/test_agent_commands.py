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
