"""🙋 PoP: when one mind calls a trade and the other passes, the owner gets a paper card to tap (owner 2026-11-16 proposals). Nothing opens
by itself, nothing is real money. No model or network is called."""
import asyncio
import json

import feecat_service as fs

CALL = json.dumps({'market': 'SOL', 'side': 'long', 'lev': 3, 'tp_pct': 4, 'sl_pct': 2, 'why': 'funding flipped negative while open interest rose 6% in an hour'})


def _fake(monkeypatch, replies):
    async def read(_h, m):
        return {'market': m, 'px': 150.0, 'chgPct': 1.0, 'high': 152.0, 'low': 148.0, 'vol': 1e6} if m == 'SOL' else None

    async def none(*_a, **_k):
        return None

    async def gather(*_a, **_k):
        return {}

    async def sites(*_a, **_k):
        return '', []

    async def round_(*_a, **_k):
        return list(replies)
    filed = []
    monkeypatch.setattr(fs, '_pop_read', read); monkeypatch.setattr(fs, '_pop_chart', none); monkeypatch.setattr(fs, '_pop_gather', gather)
    monkeypatch.setattr(fs, '_site_reads', sites); monkeypatch.setattr(fs, '_recall', lambda *a, **k: ''); monkeypatch.setattr(fs, '_convo', lambda *a, **k: '')
    monkeypatch.setattr(fs, '_pop_round', round_); monkeypatch.setattr(fs, '_pop_file', lambda cat, row, line: filed.append(row))
    return filed


def _cat():
    return {'id': 'c1', 'name': 'Happy', 'brainsCfg': {'brains': ['a/one', 'b/two']}, 'chat': []}


def test_one_mind_calls_and_the_other_passes_makes_a_card_for_his_tap(monkeypatch):
    filed = _fake(monkeypatch, [CALL, '{"pass": "no edge"}']); cat = _cat()
    asyncio.run(fs._pop_open(None, cat, 'file', None, 1000.0))
    c = cat['popCard']
    assert (c['conviction'], c['market'], c['side'], c['state'], c['paper']) == ('lone', 'SOL', 'long', 'waiting', True)
    assert not cat.get('popRun') and not filed   # nothing opened by itself
    assert 'only Mind A called it' in cat['chat'][-1]['text'] and 'Run it on paper' in cat['chat'][-1]['text']


def test_both_pass_is_still_a_no_trade_folder(monkeypatch):
    filed = _fake(monkeypatch, ['', '{"pass": "no edge"}']); cat = _cat()
    asyncio.run(fs._pop_open(None, cat, 'file', None, 1000.0))
    assert not cat.get('popCard') and filed and filed[-1]['noTrade']


def test_he_picked_one_mind_so_its_call_needs_no_card(monkeypatch):
    _fake(monkeypatch, [CALL]); cat = _cat()
    monkeypatch.setattr(fs._cmp, 'check', lambda *a, **k: {'ok': True})
    asyncio.run(fs._pop_open(None, cat, 'file', '0', 1000.0))
    assert not cat.get('popCard') and cat['popRun']['market'] == 'SOL'   # his own pick of one mind runs as he asked
