"""💲 A proof's price before it starts (owner 2026-11-10): its own real median, else every agent's real tokens at its own minds' rates; local minds free."""
import asyncio
import json


def test_prices_come_from_real_calls_and_its_own_minds(tmp_path, monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); fs._CALL_TALLY.update(at=0.0, rows=None)
    rows = [{'cat': 'me', 'kind': 'pow', 'ref': 'w1', 'usd': 0.01, 'tokens': 4000}, {'cat': 'me', 'kind': 'pow', 'ref': 'w1', 'usd': 0.02, 'tokens': 4000},
            {'cat': 'other', 'kind': 'pob', 'ref': 'b1', 'usd': 0.0, 'tokens': 10000}, {'cat': 'other', 'kind': 'pob', 'ref': 'review:b1', 'usd': 5.0, 'tokens': 99999}]
    (tmp_path / 'mind_calls.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')

    async def models():
        return {'models': [{'id': 'x/m', 'inUsd': 1.0, 'outUsd': 2.0}]}
    monkeypatch.setattr(fs, '_or_models', models)
    got = asyncio.run(fs._proof_prices({'id': 'me', 'brainsCfg': {'brains': ['x/m'], 'byKind': {'pop': ['local/ossy', 'local/g4']}}}))
    assert got['pow'] == {'usd': 0.03, 'from': 'its proofs', 'n': 1, 'minds': ['m']}      # its own filed PoW: the real bill
    assert got['pob']['from'] == 'estimate' and got['pob']['usd'] == round(10000 * .8 * 3.5 / 3.5 * 1e-6 + 10000 * .2 * 2e-6, 5)   # reviews never count
    assert got['pop'] == {'usd': 0.0, 'from': 'local', 'n': 0, 'minds': ['ossy', 'g4']}
    assert got['poc']['usd'] is None and got['poc']['from'] is None   # nothing filed anywhere: no made-up price
