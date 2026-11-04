"""♻ The close route: only empty accounts of coins not in use, CloseAccount only, through the same checked send. Network faked; nothing is sent."""
import asyncio

import reputation_service as rs

ME = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'
ACC = ['So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB']
BH = '4vJ9JU1bJJE96FWSJKvHsmmFADCg4gpZQff4P3bkLKi1'


def acc(pk, mint, raw):
    return {'pubkey': pk, 'account': {'lamports': 1_513_840, 'data': {'parsed': {'info': {'mint': mint, 'tokenAmount': {'amount': str(raw)}}}}}}


def run(monkeypatch, keep):
    sent = []

    async def krpc(http, method, params):
        if method == 'getLatestBlockhash':
            return {'value': {'blockhash': BH}}
        return {'value': [acc(ACC[0], 'EMPTY', 0), acc(ACC[1], 'HOLDS', 5), acc(ACC[2], 'KEEP', 0)] if params[1]['programId'] == rs._FW_TOKEN_PROGRAMS[0] else []}

    async def send(request, body):
        sent.append(body)
        return {'signature': 'SIG'}
    monkeypatch.setattr(rs, '_krpc', krpc)
    monkeypatch.setattr(rs, 'internal_agent_circle_send', send)
    monkeypatch.setattr(rs, '_internal_ok', lambda r: True)
    return asyncio.run(rs.internal_agent_close_empty(None, {'address': ME, 'walletId': 'w', 'acct': 'agent', 'keep': keep})), sent


def test_it_closes_only_empty_accounts_not_in_use(monkeypatch):
    out, sent = run(monkeypatch, ['KEEP'])
    assert out == {'closed': 1, 'sol': 0.00151384, 'signature': 'SIG'}
    assert len(sent) == 1 and sent[0]['walletId'] == 'w' and sent[0]['key'].startswith('close-')


def test_nothing_empty_sends_nothing(monkeypatch):
    out, sent = run(monkeypatch, ['KEEP', 'EMPTY'])
    assert out == {'closed': 0} and not sent
