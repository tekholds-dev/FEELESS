import json
import tg_auth as tg

BOT = '123456:TEST-token-not-real'


def test_genuine_fresh_init_data_names_the_player():
    now = 1_800_000_000
    data = tg.sign({'auth_date': str(now - 60), 'query_id': 'AAE', 'user': json.dumps({'id': 42, 'first_name': 'Sal', 'username': 'salrace'})}, BOT)
    assert tg.verify(data, BOT, now=now) == {'id': 42, 'name': 'Sal', 'username': 'salrace'}


def test_forged_stale_or_unsigned_init_data_is_refused():
    now = 1_800_000_000
    good = tg.sign({'auth_date': str(now), 'user': json.dumps({'id': 7, 'first_name': 'A'})}, BOT)
    assert tg.verify(good, 'another:bot-token', now=now) is None                      # signed by another bot
    assert tg.verify(good.replace('%22id%22%3A+7', '%22id%22%3A+8'), BOT, now=now) is None   # someone edited the user
    assert tg.verify(good, BOT, now=now + 2 * 86400) is None                            # older than a day
    assert tg.verify('user=%7B%22id%22%3A1%7D', BOT, now=now) is None and tg.verify('', BOT) is None and tg.verify(good, '') is None
