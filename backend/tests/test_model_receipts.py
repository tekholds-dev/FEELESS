"""🧾 Every billed model call leaves a receipt (owner 2026-11-11: $1.66 of Sonnet and the site's GPT-6 Luna fallback billed with no row)."""
import asyncio
import json

import ai_router as air
import feecat_service as fs


class _R:
    def __init__(self, code, body):
        self.status_code, self._b, self.headers, self.text = code, body, {'content-type': 'application/json'}, ''

    def json(self):
        return self._b


def _client(body):
    class H:
        def __init__(self, **_k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_a): return False
        async def post(self, *_a, **_k): return _R(200, body)
    return H


def _rows(path):
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def test_a_direct_openrouter_call_writes_one_receipt_for_its_agent_even_when_cut_off(monkeypatch, tmp_path):
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(fs.httpx, 'AsyncClient', _client({'id': 'gen-1', 'model': 'anthropic/claude-sonnet-5.5',
                                                          'choices': [{'message': {'content': '<html>half'}, 'finish_reason': 'length'}],
                                                          'usage': {'cost': 0.189, 'total_tokens': 30545}}))

    async def go():
        fs._OR_CAT.set('cat-a')
        return await fs._or_call('anthropic/claude-sonnet-5.5', [{'role': 'user', 'content': 'x'}], max_tokens=400, key='sk-agent')
    text, usd = asyncio.run(go())
    rows = _rows(tmp_path / 'model_receipts.jsonl')
    assert usd == 0.189 and len(rows) == 1
    assert rows[0]['cat'] == 'cat-a' and rows[0]['usd'] == 0.189 and rows[0]['funding'] == 'owner key' and rows[0]['finish'] == 'length' and rows[0]['id'] == 'gen-1'


def test_a_free_call_writes_no_receipt(monkeypatch, tmp_path):
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(fs.httpx, 'AsyncClient', _client({'choices': [{'message': {'content': 'hi'}}], 'usage': {'cost': 0}}))
    asyncio.run(fs._or_call('x/free', [{'role': 'user', 'content': 'x'}], max_tokens=50))
    assert _rows(tmp_path / 'model_receipts.jsonl') == []


def test_the_brain_route_does_not_write_a_second_receipt(monkeypatch, tmp_path):
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(fs.httpx, 'AsyncClient', _client({'id': 'gen-2', 'choices': [{'message': {'content': 'BUY'}}], 'usage': {'cost': 0.01}}))
    monkeypatch.setattr(fs, '_pays_itself', lambda _c: False)
    text, usd, via = asyncio.run(fs._think({'id': 'cat-b'}, 'tencent/hy4', [{'role': 'user', 'content': 'x'}], 'sk-agent'))
    rows = _rows(tmp_path / 'model_receipts.jsonl')
    assert via == 'openrouter' and len(rows) == 1 and rows[0]['cat'] == 'cat-b'


def test_the_site_router_receipts_its_paid_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(air, 'RECEIPTS_PATH', tmp_path / 'r.jsonl')
    r = air.Router()
    r._spend_note('openrouter', 0.00045, 1794425000.0, 'openai/gpt-6-luna', 'gen-3')
    r._spend_note('openrouter', 0.0, 1794425001.0, 'nvidia/free', 'gen-4')
    rows = _rows(tmp_path / 'r.jsonl')
    assert len(rows) == 1 and rows[0]['model'] == 'openai/gpt-6-luna' and rows[0]['cat'] == 'site' and rows[0]['funding'] == 'FEELESS key'


def test_an_agent_on_its_own_key_still_works_with_feeless_key_removed(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    monkeypatch.setenv('GENERAL_CAT_LIVE', '1')
    monkeypatch.setattr(fs._ck, 'key_for', lambda cat, prov, **_k: 'sk-own' if cat.get('id') == 'happy' and prov == 'openrouter' else None)
    assert fs._work_live({'id': 'happy'}) is True
    assert fs._work_live({'id': 'other'}) is False and fs._work_live() is False


def test_the_desk_reads_its_real_openrouter_balance_through_its_own_key(monkeypatch):
    class H:
        def __init__(self, **_k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_a): return False
        async def get(self, url, **_k):
            return _R(200, {'data': {'total_credits': 20, 'total_usage': 8.085}} if 'credits' in url else {'data': {'limit': None, 'limit_remaining': None, 'usage': 3.2}})
    monkeypatch.setattr(fs.httpx, 'AsyncClient', H); fs._OR_CREDIT.clear()
    monkeypatch.setattr(fs._ck, 'key_for', lambda cat, prov, **_k: 'sk-own' if cat.get('id') == 'happy' else None)
    row = asyncio.run(fs._or_credit({'id': 'happy'}))
    assert row['left'] == 11.915 and row['keyUsed'] == 3.2
    assert asyncio.run(fs._or_credit({'id': 'other'})) is None
