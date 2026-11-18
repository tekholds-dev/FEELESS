"""✅ The LAC bid (owner 2026-11-17): Kalshi filled 2 × YES @ 0.68, but the read-back a split second later answered 404 not_found, so the slip warned
"could not read it back". Kalshi's docs: a just-made order can briefly 404. Network faked; nothing is ever sent from these tests."""
import asyncio

import kalshi_bid as kb


class _R:
    def __init__(self, code, body=None):
        self.status_code, self._b, self.text = code, body or {}, str(body or '')

    def json(self):
        return self._b


class _Http:
    def __init__(self, answers):
        self.answers, self.gets, self.posts = list(answers), [], 0

    async def get(self, url, headers=None):
        self.gets.append(url)
        return self.answers.pop(0)

    async def post(self, *a, **k):   # a read-back must never send anything
        self.posts += 1
        raise AssertionError('no order may be sent from a read')


def test_settle_reads_kalshis_fixed_point_counts():
    o = {'status': 'resting', 'fill_count_fp': '1.00', 'remaining_count_fp': '1.00', 'initial_count_fp': '2.00'}
    assert kb.settle(o, 2, 0.68) == {'status': 'resting', 'filled': 1, 'usd': 1.36, 'kalshiStatus': 'resting'}
    assert kb.settle({'status': 'executed', 'fill_count_fp': '2.00'}, 2, 0.68)['filled'] == 2
    assert kb.settle({'remaining_count_fp': '0.50', 'initial_count_fp': '3.00'}, 3, 0.5)['filled'] == 2
    assert kb.settle({'fill_count': '2.00', 'remaining_count': '0.00'}, 2, 0.68)['status'] == 'filled'   # the create answer (flat, no status)


def test_the_create_answer_alone_can_confirm_a_full_fill():
    assert kb.filled_on_send({'order_id': 'x', 'fill_count': '2.00', 'remaining_count': '0.00'}, 2)
    assert not kb.filled_on_send({'order_id': 'x', 'fill_count': '1.00', 'remaining_count': '1.00'}, 2)
    assert not kb.filled_on_send({}, 2) and not kb.filled_on_send({'fill_count': 'junk'}, 2)


def test_a_fresh_404_is_read_again_and_never_resends(monkeypatch):
    monkeypatch.setattr(kb, 'headers', lambda *a, **k: {})
    naps = []

    async def nap(s):
        naps.append(s)
    h = _Http([_R(404, {'error': {'code': 'not_found'}}), _R(200, {'order': {'status': 'executed', 'fill_count_fp': '2.00'}})])
    o = asyncio.run(kb.order_status(h, 'k', 'pem', 'abc', sleep=nap))
    assert o['status'] == 'executed' and len(h.gets) == 2 and naps == [kb.READ_GAP_S] and h.posts == 0
    h = _Http([_R(404, {'error': {'code': 'not_found'}})] * kb.READ_TRIES)
    try:
        asyncio.run(kb.order_status(h, 'k', 'pem', 'abc', sleep=nap))
        raise AssertionError('should raise after its tries')
    except RuntimeError as e:
        assert 'not_found' in str(e) and len(h.gets) == kb.READ_TRIES and h.posts == 0
    h = _Http([_R(401, {'error': {'code': 'auth'}})])   # anything but a 404 is not retried
    try:
        asyncio.run(kb.order_status(h, 'k', 'pem', 'abc', sleep=nap))
    except RuntimeError:
        pass
    assert len(h.gets) == 1


def test_a_filled_bid_says_confirmed_even_while_kalshis_read_catches_up(monkeypatch):
    import feecat_service as fs

    async def still_404(*a, **k):
        raise RuntimeError('Kalshi said 404 reading the order: {"error":{"code":"not_found"}}')
    monkeypatch.setattr(fs._kb, 'order_status', still_404)
    row = {'orderId': 'o1', 'count': 2, 'price': 0.68, 'title': 'Los Angeles C wins', 'side': 'yes', 'status': 'filled', 'filled': 2, 'sentFilled': True}
    asyncio.run(fs._kalshi_confirm(None, 'k', 'pem', row))
    assert 'confirmErr' not in row and row['status'] == 'filled'
    cat = {'chat': []}
    fs._kalshi_say(cat, row)
    assert cat['chat'][-1]['text'].startswith('✅ Kalshi confirmed my bid') and '2 of 2' in cat['chat'][-1]['text']
    other = {'orderId': 'o2', 'count': 2, 'price': 0.5, 'status': 'sent'}   # not filled on send: the warning stays honest
    asyncio.run(fs._kalshi_confirm(None, 'k', 'pem', other))
    assert 'not_found' in other['confirmErr']


def test_refresh_reads_a_filled_bid_whose_read_back_failed(monkeypatch):
    import feecat_service as fs
    now = fs.time.time()
    seen = []

    async def ok(h, kid, pem, row, tries=None):
        assert tries == 1   # the 5-min pass reads once per row, no waits
        seen.append(row['orderId']); row.update(confirmedAt=1, kalshiStatus='executed'); row.pop('confirmErr', None)
        return row
    monkeypatch.setattr(fs, '_kalshi_confirm', ok)
    tk = {'orderId': 'lac', 'status': 'filled', 'confirmErr': 'Kalshi said 404'}
    cat = {'kalshiBids': [{'orderId': 'lac', 'status': 'filled', 'confirmErr': 'Kalshi said 404', 'at': now - 60},
                          {'orderId': 'done', 'status': 'filled', 'confirmedAt': 5, 'at': now - 60}],
           'pobFolders': [{'id': 'p', 'kalshi': tk}]}
    assert asyncio.run(fs._kalshi_refresh(cat, 'k', 'pem')) == 1
    assert seen == ['lac'] and 'confirmErr' not in tk and tk['confirmedAt'] == 1


def test_a_bid_whose_read_keeps_failing_stops_being_read(monkeypatch):
    import feecat_service as fs
    now = fs.time.time()
    seen = []

    async def nope(h, kid, pem, row, tries=None):
        seen.append(row['orderId']); row['readTries'] = int(row.get('readTries') or 0) + 1
        return row
    monkeypatch.setattr(fs, '_kalshi_confirm', nope)
    cat = {'kalshiBids': [{'orderId': 'x', 'status': 'filled', 'confirmErr': '404', 'at': now - 60, 'readTries': 6}], 'pobFolders': []}
    assert asyncio.run(fs._kalshi_refresh(cat, 'k', 'pem')) == 0 and seen == []
