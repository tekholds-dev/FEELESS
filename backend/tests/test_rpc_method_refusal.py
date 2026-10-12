"""📡 A node that refuses ONE method (a free plan without getTokenLargestAccounts) skips just that method — it stays in the pool for the
rest (it used to rest 30s on every holder scan, all night)."""
import asyncio
import chain_rpc as cr


class _Res:
    def __init__(self, code, body=None):
        self.status_code, self._b, self.text, self.headers = code, body or {}, '', {}

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError('x', request=None, response=None)


class _Http:
    def __init__(self, plan):
        self.plan, self.calls = plan, []

    async def post(self, url, json=None):
        self.calls.append((url, json['method']))
        return self.plan(url, json['method'])


def test_method_refused_reads_403_and_the_plan_error_codes():
    assert cr.method_refused(403) and cr.method_refused(200, {'error': {'code': -32600}}) and cr.method_refused(200, {'error': {'code': -16500}})
    assert not cr.method_refused(429) and not cr.method_refused(200, {'error': {'code': -32005}}) and not cr.method_refused(200, {'result': 1})


def test_a_refused_method_skips_only_that_method_on_that_node(monkeypatch):
    monkeypatch.setattr(cr, 'RPC_POOL', ['A', 'B']); monkeypatch.setattr(cr, 'KEEPER_LANES', ['A', 'B']); monkeypatch.setattr(cr, 'RPC_MAX_RETRIES', 2)
    monkeypatch.setattr(cr, '_dedicated', None); cr._unsupported.clear(); cr._rpc_cooldown_until.clear(); cr._quota_until.clear()
    plan = lambda url, m: _Res(403) if (url == 'A' and m == 'getTokenLargestAccounts') else _Res(200, {'result': url})
    h = _Http(plan)
    assert asyncio.run(cr._rpc(h, 'getTokenLargestAccounts', [], scan=False)) == 'B'
    assert ('A', 'getTokenLargestAccounts') in cr._unsupported and cr._rpc_cooldown_until.get('A', 0) == 0   # the node itself is NOT rested
    h.calls.clear()
    assert asyncio.run(cr._rpc(h, 'getTokenLargestAccounts', [], scan=False)) == 'B' and h.calls == [('B', 'getTokenLargestAccounts')]   # skipped at once next time
    assert asyncio.run(cr._rpc(h, 'getSlot', [], scan=False)) == 'A'                                                                  # … and still serves everything else
