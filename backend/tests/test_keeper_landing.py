"""Real buys / sells must LAND: one signed tx is re-sent to every RPC node (idempotent), and the self-fix never flaps a setting."""
import asyncio

import chain_rpc


class _Res:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


class _Http:
    def __init__(self, replies):
        self.replies, self.calls = replies, []

    async def post(self, endpoint, json=None):
        self.calls.append((endpoint, json))
        return self.replies[len(self.calls) - 1]


def test_broadcast_sends_the_same_signed_tx_to_every_node_without_preflight(monkeypatch):
    monkeypatch.setattr(chain_rpc, 'RPC_POOL', ['a', 'b', 'c'])
    http = _Http([_Res(200, {'result': 'sig'}), _Res(429, {}), _Res(200, {'error': {'code': -32002}})])
    assert asyncio.run(chain_rpc.broadcast(http, 'SIGNED')) == 1          # a busy or refusing node never raises
    assert [e for e, _ in http.calls] == ['a', 'b', 'c']
    for _, body in http.calls:
        assert body['method'] == 'sendTransaction' and body['params'][0] == 'SIGNED'
        assert body['params'][1] == {'encoding': 'base64', 'skipPreflight': True, 'maxRetries': 0}


def test_self_fix_only_moves_patience_when_the_same_value_wins_twice():
    import reputation_service as rs
    cfg = {'autoBrain': True, 'strictRunners': False, 'rotateHours': 0.08, 'rotateConfirm': 3, 'rotateMinDrop': 5.0}
    best = {'confirm': {'value': 4, 'n': 60}, 'minDrop': {'value': 5.0, 'n': 60}}
    assert rs._brain_patch(cfg, {}, best, {'confirm': {'value': 3}}) == {}                      # 3 → 4 after one run: wait
    assert rs._brain_patch(cfg, {}, best, {'confirm': {'value': 4}}) == {'rotateConfirm': 4}    # 4 won twice: apply
